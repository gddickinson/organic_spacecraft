"""Somewhere people are: the quay, the drum, the holding and the ground.

A concourse used to be a fact about a **starport**. Everything a crew could
do that was not flying — eat, drink, sleep, be treated, be paid, be hired,
be robbed — was gated on `system.port`, so an ARCA Habitat with a *million
people living in it* offered a captain nothing at all, and neither did any
of the powers' settlements, or any holding of your own.

This is the missing noun. A **place** is anywhere in a system with people in
it that a hull can be alongside, whatever built it:

- a **starport**, from the system's own quay;
- a **habitat** — a drum, a reef, a free port: somebody's people living in
  orbit, including yours;
- a **holding** — your own colony, whether or not anybody lives there;
- **downside** — a settlement a power has put on the ground.

Every one of them answers the same four questions, because everything built
on top only ever asks those four: *how many people, how good is it, how
advanced is it, and how hard is the law here.* A venue, a clinic, a hiring
hall and a customs desk all read exactly that, so all of them work at all
four kinds of place the moment the place exists.

**Derived, never stored** — the project's usual bargain. A place is read off
the port, the colony list, the settlement list and the world's own profile,
so an old save has a concourse in its habitats the moment it is loaded, and
a place can never disagree with the thing it describes.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..data.colonies import COLONIES_BY_ID
from ..data.factions import FACTIONS_BY_ID
from . import profile as profile_sim

#: The kinds of place, and what each one is. The order is the order a chart
#: lists them: the quay first, because that is where a hull usually is.
KINDS = (
    ("port", "Starport", "the quay, the desk, and whatever grew round them"),
    ("habitat", "Habitat", "people living in a drum, a reef or a hollow rock"),
    ("holding", "Your holding", "your own ground, and whoever works it"),
    ("downside", "Settlement", "somebody's people on the ground, at work"),
    ("station", "Station", "somebody's business in orbit: a yard, a hotel, "
                           "a wheel"),
    ("base", "Base", "somebody's ground: a mine, a garrison, a den"),
    ("ship", "Aboard", "your own hull, and whatever is open on it"),
)
KIND_NAME = {kid: name for kid, name, _note in KINDS}

#: How good a place is at *being a place*, on the starport scale, so one
#: number gates a venue whether it stands on a quay or in a drum. A class-A
#: port and a million-person habitat are both a 5; a picket is a 1.
AMENITY_BY_POP = ((1_000_000, 5), (100_000, 4), (10_000, 3),
                  (1_000, 2), (100, 1))

#: How many people live and work aboard a quay, by starport class — the
#: harbour, the concourse, the yards and whoever lives over the shop — and
#: how many times that a capital's Fleet Hub carries. **Not the world's
#: population**, which is who the quay serves: a quay over ten million
#: people is not a station of ten million people.
QUAY_HEADS = {5: 9_000, 4: 3_000, 3: 900, 2: 250, 1: 60, 0: 20}
CAPITAL_HEADS = 4

#: What a settlement on the ground is worth as a place. A power founds these
#: to work one commodity; there is a bar and a bunkhouse and that is the lot.
DOWNSIDE_AMENITY = 2
DOWNSIDE_HEADS = 900

#: Where a place gets its law from when there is no world under it to ask.
#: Your own ground is as lawful as you make it, which is not very.
OWN_LAW = 2
DEFAULT_TECH = 9

#: How advanced your own hull is, as a tech level: the Verge's own baseline,
#: and a level for every twelve nodes of the tree you have opened. Rough on
#: purpose — it decides what your surgeon can attempt, not what anything
#: costs — and it is the one number that makes researching the tree show up
#: on the sickbay's list.
SHIP_TECH_BASE = 9
SHIP_TECH_PER = 12
SHIP_TECH_MOST = 4


@dataclass(frozen=True)
class Place:
    """Somewhere with people in it."""

    id: str
    name: str
    #: One of `KINDS`.
    kind: str
    what: str
    system_id: int
    body_id: str
    #: The people who live and work in it — aboard a quay, the quay's own.
    heads: int
    #: The population digit of whoever it serves, which is what every venue
    #: gate reads: for a quay, the world under it; anywhere else, its own.
    people: int
    #: How much of a place it is, on the starport scale (0-5).
    amenity: int
    tech: int
    law: int
    faction: str = ""
    #: True when the hull is at the body this place stands on.
    here: bool = False
    #: Set on a holding of your own.
    mine: bool = False
    #: **What it looks like**, which is not the same as what kind it is: an
    #: ARCA drum and a STACK arcology are both habitats and are not the same
    #: structure. The colony class id where there is one, else the kind —
    #: the same bargain `sim/anchorage.Anchorage.look` keeps, for the same
    #: reason, and `ui/place_scene.py` is the reader.
    look: str = ""
    #: The people it trades with, when that is more than live in it: the
    #: world a quay stands over. Zero for a place that serves only itself.
    #: A Fleet Hub has tens of thousands aboard and serves ten million.
    served: int = 0

    def __post_init__(self) -> None:
        if not self.look:
            object.__setattr__(self, "look", self.kind)

    @property
    def kind_name(self) -> str:
        return KIND_NAME.get(self.kind, self.kind.title())


def digit(heads: int) -> int:
    """A headcount as Traveller's population digit: the power of ten."""
    if heads <= 0:
        return 0
    step, out = 10, 1
    while heads >= step and out < 12:
        step *= 10
        out += 1
    return out - 1


def amenity_for(heads: int) -> int:
    """How much of a place a crowd of this size can support."""
    for least, rating in AMENITY_BY_POP:
        if heads >= least:
            return rating
    return 0


def in_system(game, system=None) -> list:
    """Every place in this system, best first.

    The order is by what a crew would rather walk into: the most of a place
    first, the emptiest last.
    """
    system = system or getattr(game, "system", None)
    if system is None:
        return []
    here_id = getattr(game, "orbit_body", None)
    out = [p for p in (_port(game, system, here_id),) if p is not None]
    out.extend(_holdings(game, system, here_id))
    out.extend(_downside(game, system, here_id))
    out.extend(_establishments(game, system, here_id))
    aboard = ship(game)
    if aboard is not None:
        out.append(aboard)
    return sorted(out, key=lambda p: (-p.amenity, -p.heads, p.name))


def ship(game):
    """Your own hull as a place, when there are enough people on it.

    **A LAZARET is a hospital with a drive**, and until this existed it could
    not offer anybody a check-up: the clinic asks a place, and a ship was not
    one. What is open aboard is `data/venues_aboard.py`, gated on the tier
    printed on the hull's card rather than on its tonnage.

    The law aboard is your own, which is why it is zero — a captain's hull is
    the one place in the Verge where nobody asks what the crew is carrying.
    """
    from ..data.chassis import CHASSIS_BY_ID
    from ..data.venues_aboard import rating
    from . import lifespan
    vessel = getattr(game, "ship", None)
    if vessel is None:
        return None
    heads = (max(0, int(getattr(vessel, "crew", 0)))
             + len(lifespan.active(getattr(game, "officers", []) or [])))
    chassis = CHASSIS_BY_ID.get(getattr(vessel, "chassis", ""))
    tier = getattr(chassis, "tier", "") if chassis is not None else ""
    amenity = rating(tier, heads)
    if amenity <= 0:
        return None
    opened = len(getattr(getattr(game, "research", None), "unlocked", ()) or ())
    tech = SHIP_TECH_BASE + min(SHIP_TECH_MOST, opened // SHIP_TECH_PER)
    return Place(
        id="ship", name=getattr(vessel, "name", "the ship"), kind="ship",
        what=f"{chassis.name if chassis else 'Your hull'} — "
             f"{tier.lower() or 'a working ship'}, {heads} aboard.",
        system_id=getattr(game, "location_id", -1),
        body_id=str(getattr(game, "orbit_body", "") or ""),
        heads=heads, people=digit(heads), amenity=amenity, tech=tech,
        law=0, faction="", here=True, mine=True)


def here(game) -> list:
    """The places the crew could actually walk into from where the hull is."""
    return [p for p in in_system(game) if p.here]


def by_id(game, place_id: str, system=None):
    """One place by id, in this system or in the one named."""
    return next((p for p in in_system(game, system) if p.id == place_id),
                None)


def current(game):
    """The place a concourse should open on.

    Where the hull actually is, and **not your own hull** unless there is
    nothing else: a ship is always `here`, so it won every tie and the
    Concourse opened on the slop chest while you were docked at a Fleet Hub.
    """
    rows = in_system(game)
    if not rows:
        return None
    ashore = [p for p in rows if p.here and p.kind != "ship"]
    if ashore:
        return ashore[0]
    return next((p for p in rows if p.here), rows[0])


def _port(game, system, here_id):
    """The starport, if this system has one."""
    port = getattr(system, "port", None)
    if port is None:
        return None
    world = profile_sim.port_world(system)
    if world is None:
        return None
    got = profile_sim.profile(game, system, world)
    faction = FACTIONS_BY_ID.get(port.faction)
    served = 10 ** max(0, got.population)
    aboard = QUAY_HEADS.get(got.starport, 20) * (
        CAPITAL_HEADS if getattr(port, "capital", False) else 1)
    # A quay cannot be staffed by more people than the world has to spare.
    aboard = min(aboard, max(20, served // 3))
    return Place(
        id=f"port-{system.id}", name=port.name, kind="port",
        what=(f"{faction.short if faction else 'Independent'} "
              f"{'Fleet Hub' if getattr(port, 'capital', False) else 'quay'}"
              f" over {world.name}."),
        system_id=system.id, body_id=world.id, heads=aboard,
        people=got.population, amenity=got.starport, tech=got.tech,
        law=got.law, faction=port.faction or "",
        here=(here_id == world.id), served=served)


def _holdings(game, system, here_id) -> list:
    """Your own ground, and the drums on it.

    A colony class carries a population — an ARCA Habitat a million, a
    Fabricator Yard four hundred, a picket nobody — and until now that number
    was read by the upkeep model and by nothing a person could walk into.
    """
    out = []
    for colony in getattr(game, "colonies", []) or []:
        if colony.system_id != system.id or not getattr(colony, "online", False):
            continue
        klass = COLONIES_BY_ID.get(colony.class_id)
        heads = int(getattr(klass, "pop", 0) or 0)
        body = next((b for b in system.bodies if b.id == colony.body_id), None)
        if body is None:
            continue
        # A drum full of people is a habitat; a rig with nobody on it is a
        # holding, and the difference is whether there is anywhere to eat.
        kind = "habitat" if heads >= 1_000 else "holding"
        got = profile_sim.profile(game, system, body)
        out.append(Place(
            id=f"holding-{colony.id}", name=colony.name, kind=kind,
            what=(f"{klass.name if klass else 'A holding'} of yours over "
                  f"{body.name}."),
            system_id=system.id, body_id=body.id, heads=heads,
            people=digit(heads), amenity=amenity_for(heads),
            tech=max(DEFAULT_TECH, got.tech), law=OWN_LAW,
            faction="", here=(here_id == body.id), mine=True,
            look=colony.class_id))
    return out


def _downside(game, system, here_id) -> list:
    """The powers' settlements: somebody's people, working one thing."""
    from . import settlement as settlement_sim
    out = []
    for got in settlement_sim.in_system(game, system.id):
        body = next((b for b in system.bodies if b.id == got.body_id), None)
        if body is None:
            continue
        read = profile_sim.profile(game, system, body)
        faction = FACTIONS_BY_ID.get(got.power)
        out.append(Place(
            id=f"downside-{got.id}", name=f"{body.name} Works",
            kind="downside",
            what=(f"{faction.short if faction else 'Somebody'}'s people on "
                  f"{body.name}, working {got.good}."),
            system_id=system.id, body_id=body.id, heads=DOWNSIDE_HEADS,
            people=digit(DOWNSIDE_HEADS), amenity=DOWNSIDE_AMENITY,
            tech=read.tech, law=read.law, faction=got.power,
            here=(here_id == body.id)))
    return out


def _establishments(game, system, here_id) -> list:
    """The yards, hotels, wheels and dens the trade has built here
    (`sim/establishments.py`). Each keeps its own law if it has one — a
    garrison is strict, a den is not — and otherwise the world's."""
    from . import establishments as est_sim
    port = getattr(system, "port", None)
    out = []
    for got in est_sim.here(game, system):
        body = next((b for b in system.bodies if b.id == got.body_id), None)
        if body is None:
            continue
        read = profile_sim.profile(game, system, body)
        kind = got.kind
        where = "over" if kind.kind == "station" else "on"
        out.append(Place(
            id=f"est-{system.id}-{kind.id}", name=got.name, kind=kind.kind,
            what=f"{kind.name} {where} {got.body_name}. {kind.what}",
            system_id=system.id, body_id=body.id, heads=kind.heads,
            people=digit(kind.heads), amenity=kind.amenity,
            tech=max(DEFAULT_TECH, read.tech, kind.tech),
            law=read.law if kind.law is None else kind.law,
            faction=getattr(port, "faction", "") or "",
            here=(here_id == body.id), look=kind.id))
    return out


# ── what the screens ask ───────────────────────────────────────────────────

def says(place: Place) -> list:
    """A place in the words a concourse board would use."""
    from ..data import uwp
    star = uwp.STARPORTS.get(place.amenity, uwp.STARPORTS[0])
    said = [place.what,
            f"{place.kind_name} · {star[1].lower()} ({star[0]}) · "
            f"{population(place)} · tech level {place.tech} · law level "
            f"{place.law}."]
    if place.heads <= 0:
        said.append("Nobody lives here. There is nothing to walk into.")
    return said


def population(place) -> str:
    """How many people, in words: who is aboard, and — for a quay — the
    world it serves. **One door**, so the Concourse's heading, its board and
    the Afoot screen cannot print two different numbers for one place. Takes
    a `Place` or anything carrying its `heads` and `served` (an Afoot site)."""
    if getattr(place, "served", 0) > place.heads:
        return f"{place.heads:,} aboard, serving {place.served:,} below"
    return f"{place.heads:,} people"


def livable(place: Place) -> bool:
    """Whether anybody is here to sell a crew anything at all."""
    return place.heads > 0 and place.amenity > 0
