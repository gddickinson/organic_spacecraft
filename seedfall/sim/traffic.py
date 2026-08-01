"""Other hulls, where they are, and what they are doing there.

The helm plotted the star, the planets, and — since anchorages — the quays. It
did not plot a single other ship, because no other ship had anywhere to be.
Encounters were rolled the moment you arrived in a system and thrown away
afterwards; consorts followed you implicitly; faction ventures were a number
in a ledger. Nothing in the game gave another hull a *position*.

So the Verge looked empty in the one view where it should look busiest, and
"a Concordat patrol jumped me at Loam Span" arrived with no warning it could
possibly have given.

**Derived, not stored** — the same choice `sim/anchorage.py` makes, for the
same reason. A system's traffic is a pure function of the system, the day and
the state of the sector. That buys persistent identity (the *Kestrel* you saw
last week is the same *Kestrel*) with no save migration, no drift between a
stored hull and the faction it belongs to, and no hundreds of ships to tick.
The price is that derivation must not touch `game.rng()`, because that
advances with the save and would make traffic reshuffle on every reload.

Each hull runs an **errand** between two points, and its position is a
triangle wave along that leg. That is not a flight model; it is enough to give
it a place, a heading and a reason to be there, which is what the chart needs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.rng import RNG
from ..data.lore import HULL_NAMES
from ..data.factions import FACTIONS_BY_ID
from . import anchorage as anchorage_sim
from ..data.starclasses import mu_of
from . import flight

#: What a hull is out here doing. Each carries how it reads on a chart and
#: whether meeting it is anybody's idea of a good time.
ERRANDS = {
    "trader": ("Trader", "running cargo", False),
    "patrol": ("Patrol", "on station", False),
    "prospector": ("Prospector", "working a body", False),
    "courier": ("Courier", "carrying despatches", False),
    "raider": ("Unmarked hull", "no transponder", True),
}

#: Glyph per errand, kept beside the anchorage glyphs so every view that plots
#: a system agrees about what things look like.
GLYPHS = {"trader": "▸", "patrol": "◂", "prospector": "◆", "courier": "▹",
          "raider": "✖"}

#: Days a hull takes to run its leg end to end. Long enough that traffic is
#: recognisably in the same place across a few days of play.
LEG_DAYS = 46.0


@dataclass
class Hull:
    id: str
    #: Which system it works. A hull must carry this: `position` used to
    #: default to `game.system`, so asking about traffic anywhere else
    #: indexed one system's body list with another system's indices and
    #: raised `IndexError` — on the very call `hostiles` makes to sort.
    system_id: int
    name: str
    faction: str | None
    errand: str
    #: The two body indices it works between. Equal means it holds station.
    from_body: int
    to_body: int
    #: 0..1 along the leg, right now.
    along: float = 0.0
    hostile: bool = False

    @property
    def glyph(self) -> str:
        return GLYPHS.get(self.errand, "▫")

    @property
    def kind_name(self) -> str:
        return ERRANDS.get(self.errand, ("Hull", "", False))[0]

    @property
    def doing(self) -> str:
        return ERRANDS.get(self.errand, ("", "about its business", False))[1]


def _busyness(game, system) -> int:
    """How many hulls work this system.

    A capital is busy, an outpost is not, and a system the Bloom has eaten is
    emptier than either — the traffic left, which is itself worth seeing on a
    chart before you commit to going there.
    """
    port = getattr(system, "port", None)
    base = 0 if port is None else 1 + port.level
    if port is not None and port.capital:
        base += 1
    if getattr(system, "bloom", 0) > 0.2:
        base = max(0, base - 1)
    # Somebody is always prospecting where there is something to prospect.
    if not base and any(getattr(b, "resources", None) for b in system.bodies):
        base = 1
    # A lit Weave anchor is the busiest thing in a system. Everything that
    # can afford the toll comes through it, which is the whole reason the
    # powers built their capitals on the ones they found first.
    from . import weave as weave_sim
    anchor = weave_sim.gate_at(game, system.id)
    if anchor is not None and anchor.lit:
        base += 2
    return min(6, base)


def _errand_for(rng, system, slot: int, raider_odds: float) -> str:
    """What this hull is out here doing.

    **How likely a raider is scales with the law**, rather than being a flat
    chance behind a yes/no gate. The old line was `0.18 + bloom * 0.5` — and
    the Bloom is already inside `piracy.lawlessness`, so a bloomed system was
    counted twice for the same reason.

    A cliff also placed piracy badly: gating on lawlessness alone dropped
    raiders from 26 systems in 252 to 9, because the least policed systems are
    the portless ones and those carry about one hull each. Scaling means the
    worst places carry more of them and the merely quiet places carry a few,
    which is what "where the law is not" should actually look like.
    """
    port = getattr(system, "port", None)
    if raider_odds > 0.0 and rng.chance(raider_odds):
        return "raider"
    if port is None:
        return "prospector"
    if slot == 0:
        return "patrol"
    return rng.weighted([(5, "trader"), (2, "prospector"), (2, "courier")])


def in_system(game, system=None) -> list:
    """Every hull working this system right now.

    Pure in `(system, day, sector state)`. It must never draw on `game.rng()`:
    that advances with the save, so traffic would reshuffle on every reload
    and the *Kestrel* you hailed yesterday would be somebody else.
    """
    system = system or game.system
    bodies = system.bodies
    if not bodies:
        return []

    count = _busyness(game, system)
    if not count:
        return []

    quay_body, quay_index = anchorage_sim.anchor_body(system)
    # **Whether raiders can work here is a question about the law**, and it
    # used to be a question about `port`. See `sim/piracy.lawlessness`: a
    # squadron on station, a dock, a claim, the distance from the nearest
    # capital and the Bloom, in one number that `sim/encounters` reads too —
    # so a system cannot be lawful enough to keep raiders out and dangerous
    # enough to jump you at the same time.
    from . import piracy as piracy_sim
    raider_odds = piracy_sim.raider_chance(game, system)
    out = []
    taken: set = set()
    for slot in range(count):
        # Seeded on the system and the slot only, so identity is stable for
        # the life of the chronicle.
        rng = RNG(f"traffic:{system.id}:{slot}")
        errand = _errand_for(rng, system, slot, raider_odds)

        faction = None
        if errand == "patrol":
            faction = getattr(system, "faction", None)
        elif errand != "raider":
            faction = getattr(system, "faction", None) if rng.chance(0.5) \
                else rng.pick(["freeholds", "charter", "concordat"])

        # Unique within the system. The pools hold four or five names each
        # and a capital works five hulls, so two of them turned up on the
        # chart with the same name — which makes "the hull you plotted"
        # meaningless the moment it matters.
        pool = HULL_NAMES.get(faction or "freeholds", HULL_NAMES["freeholds"])
        start = rng.int(0, len(pool) - 1)
        name = next((pool[(start + n) % len(pool)] for n in range(len(pool))
                     if pool[(start + n) % len(pool)] not in taken),
                    f"{pool[start]} II")
        taken.add(name)

        if errand == "patrol" and quay_index >= 0:
            here = there = quay_index
        elif errand == "prospector":
            here = there = rng.int(0, len(bodies) - 1)
        else:
            here = rng.int(0, len(bodies) - 1)
            there = quay_index if quay_index >= 0 else rng.int(0, len(bodies) - 1)
            if there == here:
                there = (here + 1) % len(bodies)

        # A triangle wave along the leg, offset per hull so they are not all
        # in step. Position is a function of the day and nothing else.
        offset = rng.float(0, 1)
        phase = ((game.day / LEG_DAYS) + offset) % 1.0
        along = phase * 2 if phase < 0.5 else (1 - phase) * 2

        out.append(Hull(
            id=f"{system.id}:{slot}", system_id=system.id,
            name=name, faction=faction,
            errand=errand, from_body=here, to_body=there,
            along=along, hostile=ERRANDS[errand][2]))
    return out


def _home(game, hull, system=None):
    """The system a hull actually works, never merely the one you are in."""
    if system is not None:
        return system
    return game.galaxy.systems[hull.system_id]


def position(game, hull, system=None) -> tuple[float, float]:
    """Where a hull is, in AU, right now."""
    system = _home(game, hull, system)
    bodies = system.bodies
    start = flight.position(bodies[hull.from_body], game.day,
                            mu_of(system))
    if hull.from_body == hull.to_body:
        return start
    end = flight.position(bodies[hull.to_body], game.day,
                          mu_of(system))
    return (start[0] + (end[0] - start[0]) * hull.along,
            start[1] + (end[1] - start[1]) * hull.along)


def reach_to(game, hull) -> float:
    """AU between the ship and a hull."""
    hx, hy = position(game, hull)
    sx, sy = flight.ship_position(game)
    return math.hypot(hx - sx, hy - sy)


def bearing_to(game, hull) -> float:
    """Degrees clockwise from the star-ward direction. For a chart, later."""
    hx, hy = position(game, hull)
    sx, sy = flight.ship_position(game)
    return math.degrees(math.atan2(hy - sy, hx - sx)) % 360


def note(game, hull, system=None) -> str:
    """One line: who it is, what it is doing, and how far off."""
    system = _home(game, hull, system)
    who = FACTIONS_BY_ID.get(hull.faction) if hull.faction else None
    flag = who.short if who else "No colours"
    span = reach_to(game, hull)
    if hull.from_body == hull.to_body:
        where = f"holding at {system.bodies[hull.from_body].name}"
    else:
        where = (f"{system.bodies[hull.from_body].name} → "
                 f"{system.bodies[hull.to_body].name}")
    return f"{flag} · {hull.doing}, {where} · {span:.2f} AU off"


#: **The dead effect this revived.** Two guards were
#: excusing each other over it: `test_grants` asks whether every colony effect is
#: read *by name* somewhere, and found `"drift"` in `sim/ship.py` — where the only
#: thing it did was set `Stats.has_drift`, which `test_declared` had on its
#: allowed list as a flag that gated nothing. So the colony effect was counted as
#: consumed because a dead ship stat mentioned it, and the ship stat was excused
#: because somebody would get round to it. Between them, **the entire `drift`
#: effect did nothing at all** — on a 21,000-credit module and an 18,000-credit
#: colony, both of whose descriptions promise it plainly.


def mesh_reaches(game, system) -> bool:
    """Does the picket mesh report from this system?

    Three ways to have eyes somewhere, and the module and colony descriptions
    are the specification:

    * you are standing in it;
    * a CHORUS Node is aboard (`Stats.has_drift`) and you have been there, so
      the mesh has something of yours to reconcile against;
    * or one of your colonies in that system holds the `drift` effect, which
      keeps its own system plotted whether or not the node is aboard.
    """
    if system is None:
        return False
    if system.id == game.location_id:
        return True
    from . import colony as colony_sim
    if colony_sim.drifting(game, system.id):
        return True
    return bool(getattr(game.ship_stats, "has_drift", False)
                and getattr(system, "visited", False))


def plotted(game, system=None) -> list:
    """The hulls you can actually see in a system, which is not always all of
    them.

    `in_system` derives the traffic of *any* system from the sector and the day
    — it always could, and nothing ever asked it about anywhere but here. So the
    chart could not tell a captain that two raiders were working the system they
    were about to jump into, which is the exact complaint this module opens with:
    "a Concordat patrol jumped me at Loam Span" arrived with no warning it could
    possibly have given.

    Being able to see it is what a CHORUS Node buys. Where the mesh does not
    reach, this is empty and the screens say so rather than showing nothing and
    letting the captain assume it is quiet.
    """
    system = system or game.system
    if not mesh_reaches(game, system):
        return []
    return in_system(game, system)


def watched(game) -> list:
    """Every system the mesh is reporting from, with what is in it.

    What the sector chart draws. Sorted by how much trouble is in each, because
    that is the order a captain wants to read it in.
    """
    out = []
    for system in game.galaxy.systems:
        if not mesh_reaches(game, system):
            continue
        hulls = in_system(game, system)
        if not hulls:
            continue
        out.append({"system": system, "hulls": hulls,
                    "hostile": sum(1 for h in hulls if h.hostile),
                    "here": system.id == game.location_id})
    out.sort(key=lambda row: (-row["hostile"], -len(row["hulls"]),
                              row["system"].name))
    return out


def hostiles(game, system=None) -> list:
    """Hulls here that are nobody's friend, nearest first."""
    system = system or game.system
    bad = [h for h in in_system(game, system) if h.hostile]
    return sorted(bad, key=lambda h: reach_to(game, h))


def present_factions(game, system=None) -> list:
    """Which powers actually have a hull in this system.

    `roll_encounter` asks, so that the patrol which jumps you is one you could
    have seen on the chart before you committed to arriving.
    """
    system = system or game.system
    return sorted({h.faction for h in in_system(game, system)
                   if h.faction and not h.hostile})


def summary(game, system=None) -> str:
    """One line for a screen: how busy this system is."""
    here = in_system(game, system)
    if not here:
        return "Nothing else is moving out here."
    bad = sum(1 for h in here if h.hostile)
    line = f"{len(here)} hull{'' if len(here) == 1 else 's'} working the system"
    if bad:
        line += f", {bad} of them running dark"
    return line + "."
