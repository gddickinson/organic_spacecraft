"""Officers.

Six bridge roles, straight out of the old survey-ship convention: science,
navigation, engineering, medicine, communications, tactical.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..core import ids
from ..core.rng import RNG
from ..data import convictions
from ..data import lineages
from . import loyalty
from ..data.lore import CREW_FIRST, CREW_LAST, CREW_ROLES
from ..data.milestones import RECRUIT_FLOOR


#: (id, name, note, effect key, magnitude)
TRAITS = [
    ("charter", "Charter-raised", "Grew up under the licence regime", "diplomacy", 0.04),
    ("yards", "Yards-trained", "Learned on fabricated hulls", "repair", 0.05),
    ("freehold", "Freehold-born", "Knows what things are really worth", "trade", 0.05),
    ("veteran", "Bloom veteran", "Was at Kessel's Reach and came back", "tactical", 0.05),
    ("wetwired", "Wet-wired", "Runs a direct bioelectric interface", "accuracy", 0.03),
    ("quiet", "Quiet", "Says little; misses less", "scan", 0.04),
    ("reckless", "Reckless", "Fast, and expensive about it", "evade", 0.04),
]


#: By id, so a trait can be looked up from an officer who carries one.
TRAITS_BY_ID = {t[0]: t for t in TRAITS}


def trait_effects(officers) -> dict[str, float]:
    """What the bridge's traits add, summed by effect key.

    **Every trait in `TRAITS` declares an effect and a magnitude, and nothing
    anywhere applied one.** `Officer.trait_id` was written when a candidate was
    generated and read by nobody: `trait_name` and `trait_note` went to the crew
    screen, so a Bloom veteran said "Was at Kessel's Reach and came back" and
    fought exactly like anybody else. It is not free, either — `make_officer`
    charges 25 a month for a trait, so a captain has been paying for seven
    different effects that did not exist.

    The keys are the names `ship.stats` already computes from officer levels —
    `accuracy`, `evade`, `scan`, `repair`, `trade`, `diplomacy` — plus
    `tactical`, which is the *skill* the other combat numbers are derived from
    rather than a stat of its own. Summed across the bridge, because two
    yards-trained officers are better than one.
    """
    out: dict[str, float] = {}
    for officer in officers or []:
        trait = TRAITS_BY_ID.get(getattr(officer, "trait_id", None) or "")
        if trait is None or getattr(officer, "retired", False):
            continue
        out[trait[3]] = out.get(trait[3], 0.0) + trait[4]
    return out


@register
@dataclass
class Officer:
    id: int
    name: str
    role: str
    role_name: str
    stat: str
    note: str
    level: int
    wage: int
    xp: int = 0
    trait_id: str | None = None
    trait_name: str = ""
    trait_note: str = ""
    conviction: str | None = None
    loyalty: float = convictions.START
    #: What they are made of, and how far through their run they are. See
    #: `data/lineages.py` — everyone used to be the same thing and immortal.
    lineage: str | None = None
    #: **Two clocks, and they are not the same clock.** `age` is what the
    #: years did to this body — it runs at the lineage's rate, slows in a
    #: cold berth and slows again on anagathics — and `born` is the day of
    #: the chronicle they came into the world on, which nothing slows. See
    #: `sim/lifespan.py` and `data/stages.py`; `born` may be negative, and
    #: for every save written before this existed it is derived once.
    age: float | None = None
    born: float | None = None
    #: Fractional levels shed to decline, carried so it is a slope not a step.
    wear: float = 0.0
    retired: bool = False
    #: Whether this officer has already said their piece about the way the
    #: ship is run (`sim/loyalty.py`), so they warn once, not every day.
    warned: bool = False
    # Innovation 8, officer arcs (`sim/arcs.py`): their own story, how far
    # through it they are (beats resolved, 0-3), its clocks and answers, and
    # the signature a story well finished left them. Dealt on the first tick
    # from their own key, so an officer from an older save gets theirs too.
    arc: str | None = None
    arc_beat: int = 0
    arc_state: dict = field(default_factory=dict)
    signature: str | None = None

    @property
    def label(self) -> str:
        return f"{self.name} — {self.role_name}"


def make_officer(rng, role_id: str | None = None, min_level: int = 1) -> Officer:
    # `role_id=None` asks for anybody; a name that matches nothing is a
    # mistake, and answering it with a random officer is how a stat name in
    # `CREW_CHOICES` went unnoticed for as long as it did.
    role = None
    if role_id is not None:
        role = next((r for r in CREW_ROLES if r[0] == role_id), None)
        if role is None:
            raise ValueError(f"no station called {role_id!r}")
    role = role or rng.pick(CREW_ROLES)
    level = rng.weighted([(5, min_level), (4, min_level + 1),
                          (2, min_level + 2), (1, min_level + 3)])
    trait = rng.pick(TRAITS) if rng.chance(0.55) else None
    officer = Officer(
        id=ids.next_id("officer"),
        name=f"{rng.pick(CREW_FIRST)} {rng.pick(CREW_LAST)}",
        role=role[0], role_name=role[1], stat=role[2], note=role[3],
        level=level, wage=40 + level * 55 + (25 if trait else 0),
        trait_id=trait[0] if trait else None,
        trait_name=trait[1] if trait else "",
        trait_note=trait[2] if trait else "",
    )
    loyalty.assign(rng, officer)
    return officer


def starting_crew(rng) -> list[Officer]:
    """A starting bridge: three core roles, modest experience.

    Names are made distinct: drawing three at random from a list of this size
    puts two Mareks on the same bridge about one game in ten, which reads as a
    bug even though it is only chance.
    """
    crew = [make_officer(rng, "science", 2),
            make_officer(rng, "nav", 2),
            make_officer(rng, "engineer", 2)]
    seen: set[str] = set()
    for officer in crew:
        first = officer.name.split()[0]
        guard = 0
        while first in seen and guard < 20:
            first = rng.pick(CREW_FIRST)
            guard += 1
        seen.add(first)
        officer.name = f"{first} {officer.name.split(' ', 1)[1]}"
    return crew


def hiring_lineage(rng, game=None, place=None) -> str:
    """What a quay's next candidate is made of.

    Mostly wet, because most of the Verge is — but **what a hull draws and
    what a gate admits both decide it now** (`sim/kindred.py`). A fabricated
    hull draws frames, a synthetic one draws minds, and a Charter capital
    that refuses aliens ashore does not put one on its board. Called without
    a game it falls back to the old weighting, which is what the opening
    crew and a few checks want.
    """
    if game is not None:
        from . import kindred
        return kindred.pick(game, place, rng)
    pool = lineages.recruitable()
    return rng.weighted([(6 if l.id == "wet" else 2, l.id) for l in pool])


def recruit_pool(rng, port_level: int, floor: int = 0, game=None,
                 place=None) -> list[Officer]:
    """Candidates on offer. Bigger ports attract better officers; `floor`
    lifts every one of them (a Commodore's perk, `sim/renown`).

    `game` and `place` decide what the candidates are *made of*: what the
    hull draws and what the gate will admit (`sim/kindred.py`).
    """
    out = []
    for _ in range(2 + port_level):
        officer = make_officer(rng, None, port_level + floor)
        # Left unset an officer is assumed to be of the captain's own stock,
        # which is right for the crew you launched with and wrong for a quay.
        officer.lineage = hiring_lineage(rng, game, place)
        # An empty substrate means this gate would admit nobody at all, so
        # there is no board rather than a board of people who cannot land.
        if not officer.lineage:
            continue
        out.append(officer)
    return out


def grant_xp(officers, stat: str, amount: float, game=None) -> list[Officer]:
    """Experience from doing the job. Levels cap at 6.

    Pass `game` and a promotion reports itself. Every officer in the game
    values `promoted` at +5 — it is in `UNIVERSAL`, so it applies whatever
    they believe — and nothing ever recorded it: this returned the list of
    people who had just been promoted and all eight call sites threw it away.
    So a career built over a decade moved nobody at all, and the crew screen
    never mentioned it.
    """
    from . import lifespan          # lazily: lifespan reads the crew list
    gained = []
    for o in officers:
        if stat != "*" and o.stat != stat:
            continue
        # How quickly somebody picks the job up is their stage's, not a
        # constant: the green learn half again as fast as anybody aboard and
        # the declining at half the rate (`data/stages.py`).
        o.xp += amount * lifespan.stage_of(o, game).learns
        need = o.level * 100
        if o.xp >= need and o.level < 6:
            o.xp -= need
            o.level += 1
            gained.append(o)
    if gained and game is not None:
        for officer in gained:
            game.add_log(f"{officer.name} is made {officer.role_name} "
                         f"{officer.level}.", "good")
            # Their own career, on top of the news everybody hears.
            loyalty.shift(officer, convictions.PROMOTION_OWN)
        # And once for the ship, not once per person promoted: `record`
        # already walks every officer aboard.
        loyalty.record(game, "promoted")
    return gained


def daily_wages(officers) -> float:
    return sum(o.wage for o in officers) / 30


#: Below this many days a crossing is a hop, and nobody philosophises about
#: the nature of time over a fortnight.
#:
#: Measured rather than picked. Across eight sectors and 354 crossings the
#: median is nine days and the ninetieth percentile twenty-three, with the very
#: longest at thirty-four — so a floor of thirty, which a first draft used,
#: means the line almost never appears at all: the longest crossing in the
#: system it was first tried in was twenty-nine days. Twenty puts it on roughly
#: the top eighth of voyages, which is what "long enough to remark on" should
#: mean.
TEDIUM_WORTH_SAYING = 20


def tedium(officers, days: float) -> float:
    """What a long crossing costs in morale, decided by who is aboard.

    `data/lineages.py` has declared a `boredom` per lineage since it was
    written — 0.012 a day for a wet crew, 0.006 for a graft, and its own
    docstring said "`boredom` is what that costs in morale". Nothing read it:
    `morale_tick` had no lineage term at all, so a hundred days in a hull was
    the same to a wet crew as to a lineage of recordings that measures its life
    in centuries.

    Averaged over the bridge, because a bridge is a mix. A Choir navigator does
    not stop a wet engineer from climbing the walls, but it does dilute it.
    """
    if days <= 0:
        return 0.0
    rates = [lineages.LINEAGES_BY_ID[
                 o.lineage if o.lineage in lineages.LINEAGES_BY_ID
                 else lineages.DEFAULT].boredom
             for o in (officers or [])]
    if not rates:
        rates = [lineages.LINEAGES_BY_ID[lineages.DEFAULT].boredom]
    return (sum(rates) / len(rates)) * days


def how_it_feels(game, days: float) -> str:
    """What the bridge says about a crossing of this length, or nothing.

    The line comes from whichever lineage most of the bridge is, because a
    mixed bridge cannot have one opinion and the majority's is the one said out
    loud. Only for crossings long enough to be worth remarking on — a
    fortnight's hop does not get a line about the nature of time.
    """
    if days < TEDIUM_WORTH_SAYING:
        return ""
    aboard = [o.lineage if o.lineage in lineages.LINEAGES_BY_ID
              else lineages.DEFAULT
              for o in (getattr(game, "officers", None) or [])]
    if not aboard:
        aboard = [lineages.DEFAULT]
    most = max(set(aboard), key=aboard.count)
    return lineages.LINEAGES_BY_ID[most].time_sense


def bear_tedium(game, days: float) -> float:
    """Wear a crossing's tedium into the crew's morale. Returns what it cost."""
    lost = tedium(getattr(game, "officers", None), days)
    if lost <= 0:
        return 0.0
    before = game.ship.morale
    game.ship.morale = max(0.0, game.ship.morale - lost)
    return before - game.ship.morale


def morale_tick(ship, days: float, paid: bool, breached: bool,
                morale_fx: float = 0.0) -> float:
    """Morale drifts toward a target set by pay, air and recent disasters."""
    target = 0.72 + morale_fx * 0.4
    if not paid:
        target -= 0.35
    if breached:
        target -= 0.30
    if ship.o2 < 0.5:
        target -= 0.25
    ship.morale += (target - ship.morale) * min(1.0, 0.08 * days)
    ship.morale = max(0.0, min(1.0, ship.morale))
    return ship.morale


# ── the berths ─────────────────────────────────────────────────────────────
# Signing somebody on and paying the bridge both spent credits from inside
# `berths_panel.py`, so neither could be done or measured without a screen.

def bonus_cost(officers) -> int:
    """What it costs to put a bonus round the bridge."""
    return int(sum(o.wage for o in officers) * 0.6)


def can_hire(game, officer) -> tuple[bool, str]:
    """Whether this hand can be signed, and what stops it.

    The berths board drew a live "Sign on" under every candidate and let the
    refusal arrive as a toast. Measured over sixty ports, **49% of candidates
    could not be signed** — a fresh bridge already holds science, engineering
    and nav, and the pool draws evenly from all six roles — so half the board
    was buttons that did nothing. Fifty-five of sixty boards had at least one.
    """
    held = next((x for x in game.officers if x.stat == officer.stat), None)
    if held is not None:
        return False, (f"{held.name} already holds {officer.role_name.lower()}. "
                       "Pay them off first.")
    if game.credits < officer.wage:
        return False, (f"The signing fee is {round(officer.wage):,} and the "
                       f"treasury holds {round(game.credits):,}.")
    return True, ""


def hire(game, officer) -> dict:
    """Sign an officer on. One station, one incumbent."""
    ok, why = can_hire(game, officer)
    if not ok:
        return {"ok": False, "why": why}
    game.credits -= officer.wage
    game.officers.append(officer)
    game.add_log(f"{officer.name} signed on as {officer.role_name}.", "good")
    return {"ok": True, "officer": officer, "fee": officer.wage}


def pay_bonus(game) -> dict:
    """Money over the odds, and the bridge remembers it."""
    cost = bonus_cost(game.officers)
    if game.credits < cost:
        return {"ok": False, "why": "Not enough in the treasury for that."}
    game.credits -= cost
    loyalty.record(game, "bonus_paid")
    game.add_log("A bonus went round the bridge.", "good")
    return {"ok": True, "cost": cost}


def pool_at(game, system) -> list[Officer]:
    """Who is looking for a berth at this quay this month.

    **Seeded from its own key.** The berths tab drew `game.rng("recruit")` the
    first time it was opened and kept the answer on the screen, so the hands
    on offer depended on *when* you first looked — and, because `game.rng`
    advances the save's seed, looking moved the luck of everything rolled
    after it. Measured: 20 ports of 20 offered a different board on a second
    ask. Seed, port and month make it a fact about the quay instead.

    Anybody already on your bridge is not still looking, so a hand signed on
    this month drops off the board rather than being offered twice.
    """
    if not getattr(system, "port", None):
        return []
    rng = RNG(f"{game.seed}:recruit:{system.id}:{game.day // 30}")
    aboard = {(o.name, o.role) for o in game.officers}
    from . import renown
    floor = RECRUIT_FLOOR if renown.perk(game, "recruits") else 0
    from . import places as places_sim
    here = next((p for p in places_sim.in_system(game, system)
                 if p.kind == "port"), None)
    return [o for o in recruit_pool(rng, system.port.level, floor, game, here)
            if (o.name, o.role) not in aboard]


def pool_here(game, place) -> list:
    """Who is looking for a berth at *this place* this month.

    `pool_at` asks a quay, which was the only place in the Verge anybody
    stood about hoping for work. A hiring hall, a crewing agency, a factor's
    rooms and a hiring stone all carry the `hire` tag (`data/venues.py`) and
    none of them did anything — so a habitat of a million people had four
    doors offering berths and nobody behind any of them.

    Seeded on the place and the month, like the quay's board and for the
    same reason: looking must not move the chronicle's luck, and the answer
    must be the same on the second ask.
    """
    from . import shore
    if not shore.selling(game, place, "hire"):
        return []
    rng = RNG(f"{game.seed}:hire:{place.id}:{game.day // 30}")
    aboard = {(o.name, o.role) for o in game.officers}
    from . import renown
    floor = RECRUIT_FLOOR if renown.perk(game, "recruits") else 0
    return [o for o in recruit_pool(rng, max(1, place.amenity), floor,
                                    game, place)
            if (o.name, o.role) not in aboard]


#: How long shore leave keeps the ship alongside, in days.
SHORE_LEAVE_DAYS = 7


def shore_leave(game) -> dict:
    """A week alongside: the calendar moves and the bridge mends.

    It lived in `ui/berths_panel.py` — a loyalty event, seven days off the
    clock and a line in the log, performed by a button handler — so nothing
    but a screen could grant it and no check could measure what it cost.
    """
    if not game.officers:
        return {"ok": False, "why": "Nobody on the bridge to send ashore.",
                "text": ""}
    loyalty.record(game, "shore_leave")
    game.advance_days(SHORE_LEAVE_DAYS)
    text = "Seven days alongside. The bridge came back better company."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text, "days": SHORE_LEAVE_DAYS}


def pay_off(game, officer) -> dict:
    """Let an officer go. The station is empty until somebody signs on.

    The berths tab assigned `game.officers` itself, and said nothing — an
    officer could leave the bridge without the chronicle noticing.
    """
    if not any(o is officer for o in game.officers):
        return {"ok": False, "why": f"{officer.name} is not on your bridge.",
                "text": ""}
    game.officers = [o for o in game.officers if o is not officer]
    text = f"{officer.name} was paid off and went ashore."
    game.add_log(text, "")
    return {"ok": True, "why": "", "text": text, "officer": officer}
