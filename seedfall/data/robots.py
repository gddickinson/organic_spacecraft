"""Hands that are not people.

The game already says a crew member is a **substrate** — `data/lineages.py`
opens with it, and one of the four is a Dry Choir *recording*, which is a mind
in a machine that eats silicon and magnetite and does not breathe. It already
says a hull family can be "crewless Dry Choir work". What it did not have was
anything you could buy, post somewhere, and leave.

So: twenty classes of machine, across the same five technologies the hulls and
the holdings use, and one number that decides what each is worth — **how
autonomous it is**, on the ECSS ladder that real spacecraft are rated against:

    E1  teleoperated       somebody drives it, in real time
    E2  preplanned         it executes what it was given, and no more
    E3  adaptive           it replans locally and reports back
    E4  goal-directed      you give it an objective and leave

That ladder is the whole design, because the other half of it is distance. A
teleoperated rigger is superb alongside and worthless at one AU, where the
round trip is sixteen and a half minutes; a Choir servitor does not care where
it is. So the question "which robot" is really "how far from you will it be
working, and for how long" — see `sim/robots.grip`, which is where the two
meet.

Nothing here is a bonus with a name. Every class either stands a watch — a
`stat` the bridge already reads — or holds a `duty` a holding already needs
doing, and it is paid for daily in commodities the market already trades.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The ladder, in the words a captain would use. Keys are what `RobotClass`
#: carries; the third entry is the line a screen shows.
AUTONOMY = {
    1: ("Teleoperated", "warn",
        "Somebody has to fly it. Every command is a round trip."),
    2: ("Preplanned", "steel",
        "Runs the plan it was given, and stops when the plan runs out."),
    3: ("Adaptive", "lumen",
        "Replans on the spot and tells you afterwards."),
    4: ("Goal-directed", "chloro",
        "Give it the objective. It will not ask again."),
}

#: What a machine can be set to do away from the bridge. Each one names work
#: the game already simulates, because a duty nothing consumes is scenery.
DUTIES = {
    "works": ("Works", "Keeps a holding's plant running, and its yield up."),
    "mine": ("Mining", "Cuts and hauls at a rig."),
    "survey": ("Survey", "Reads a body properly, and writes it down."),
    "repair": ("Repair", "Patches a hull, a frame or a gantry."),
    "cargo": ("Cargo", "Loads, stows and shifts."),
    "ground": ("Ground", "Goes down where a person would rather not."),
}


@dataclass(frozen=True)
class RobotClass:
    """One class of machine: what it is, what it can do, and what it costs."""

    id: str
    name: str
    #: grown | fabricated | hybrid | synthetic | xeno — the same five the
    #: hulls and the holdings are built in.
    family: str
    #: 1..4 on the ECSS ladder above.
    autonomy: int
    #: The bridge station it can stand, in `crew`'s vocabulary, or "" for a
    #: machine with no place on a bridge.
    stat: str
    #: What it works at, in the same units as an officer's level.
    level: int
    #: What it weighs in the hold. A frame you cannot lift is a frame you
    #: cannot carry to where the work is.
    mass_t: float
    #: To build one. Credits and materials, the same keys the market trades.
    cost: dict
    #: Per day, whatever it is doing. A machine that costs nothing to keep is
    #: a machine with no decision attached to it.
    upkeep: dict
    #: The technology that lets you build one at all.
    tech: str | None
    blurb: str
    #: Grown and xeno ones have a species name, like the hulls do.
    binomial: str = ""
    duties: tuple = field(default_factory=tuple)


def _r(rid, name, family, autonomy, stat, level, mass_t, cost, upkeep, tech,
       blurb, binomial="", duties=()):
    return RobotClass(rid, name, family, autonomy, stat, level, mass_t,
                      cost, upkeep, tech, blurb, binomial, tuple(duties))


ROBOTS: list[RobotClass] = [
    # ── the Yards: welded, cheap, obedient, and it never mends itself ──────
    _r("stevedore", "Stevedore Frame", "fabricated", 2, "", 2, 3.5,
       {"credits": 2200, "alloy": 4}, {"credits": 3},
       "aicore",
       "Six arms on a track and nothing above the neck. It will shift a hold "
       "in an afternoon and will not be told anything clever.",
       duties=("cargo", "works")),
    _r("hullwright", "Hullwright Drone", "fabricated", 2, "engineering", 2, 2.0,
       {"credits": 3400, "alloy": 5}, {"credits": 4, "alloy": 0.01},
       "aicore",
       "A welder, a scanner and a cold-gas pack. Goes outside so nobody else "
       "has to, and patches what it is pointed at.",
       duties=("repair",)),
    _r("rigger", "Spar Rigger", "fabricated", 1, "", 4, 9.0,
       {"credits": 5200, "alloy": 12}, {"credits": 6, "alloy": 0.02},
       "monocoque",
       "Heavy structural work under a pilot's hands, and the hands must be "
       "close. Superb at a berth; a statue at any distance.",
       duties=("works", "repair")),
    _r("loader", "Loader Exoframe", "fabricated", 1, "", 3, 1.2,
       {"credits": 1800, "alloy": 3}, {"credits": 2},
       None,
       "Worn, not sent. A powered frame that makes one pair of hands worth "
       "eight, and it is only ever as far away as the person inside it.",
       duties=("cargo", "ground")),
    _r("magazine", "Magazine Servitor", "fabricated", 2, "tactical", 2, 2.6,
       {"credits": 3000, "alloy": 6}, {"credits": 4},
       "dronework",
       "Feeds the racks. It does not aim and it does not flinch, and a gun "
       "crew that never tires is worth a grade of accuracy.",
       duties=()),
    _r("interlock", "Helm Interlock", "fabricated", 2, "nav", 2, 1.0,
       {"credits": 2800, "alloy": 4}, {"credits": 3},
       "aicore",
       "A box wired across the helm that holds a course better than a tired "
       "navigator and worse than an awake one.",
       duties=()),

    # ── the Dry Choir: recordings. Superb instruments, no self-repair ──────
    _r("servitor", "Choir Servitor", "synthetic", 4, "science", 3, 1.6,
       {"credits": 9000, "silicon": 6, "magnetite": 4},
       {"silicon": 0.004, "magnetite": 0.002},
       "synthmind",
       "A recording in a walking frame. It will hold a watch, go down a hole, "
       "and come back with the numbers written properly.",
       duties=("survey", "ground")),
    _r("lamplighter", "Lamplighter Probe", "synthetic", 3, "", 3, 0.8,
       {"credits": 6500, "silicon": 4, "magnetite": 2},
       {"silicon": 0.002, "magnetite": 0.001},
       "dronework",
       "Thrown at a body and left to read it. Replans its own passes and "
       "sends the sheet when it is done.",
       duties=("survey",)),
    _r("verger", "Verger", "synthetic", 3, "", 3, 2.2,
       {"credits": 7200, "silicon": 5, "magnetite": 4},
       {"silicon": 0.003, "magnetite": 0.002},
       "synthmind",
       "Walks a holding's plant end to end, day after day, and fixes what it "
       "finds before anybody has noticed it broke.",
       duties=("works", "repair")),
    _r("anchorite", "Anchorite", "synthetic", 4, "comms", 3, 0.4,
       {"credits": 11000, "silicon": 8, "magnetite": 5},
       {"silicon": 0.005, "magnetite": 0.002},
       "consensus",
       "A mind with no body at all, racked in a holding and left to run it. "
       "Nobody has ever agreed whether this counts as company.",
       duties=("works",)),
    _r("precentor", "Precentor", "synthetic", 4, "engineering", 4, 2.8,
       {"credits": 15000, "silicon": 11, "magnetite": 8},
       {"silicon": 0.007, "magnetite": 0.004},
       "consensus",
       "A senior recording, expensive and unhurried, that has kept more hulls "
       "alive than most yards have built.",
       duties=("repair", "works")),

    # ── grown: gestated, self-mending, slow, and it eats ───────────────────
    _r("myrmidon", "Myrmidon", "grown", 2, "", 2, 4.0,
       {"credits": 1600, "biomass": 8, "phosphate": 1},
       {"biomass": 0.004},
       "morphogen",
       "Grown to a shape and no further. Cheap by the dozen, mends its own "
       "tears overnight, and will never be told anything new.",
       "Myrmidon operarius", duties=("works", "ground")),
    _r("scarab", "Scarab Crawler", "grown", 2, "", 3, 6.5,
       {"credits": 2400, "biomass": 10, "phosphate": 2},
       {"biomass": 0.006},
       "bioleach",
       "Chews rock and sweats concentrate. Where one works a seam, the seam "
       "keeps giving after the crew have gone to bed.",
       "Scarabaeus edax", duties=("mine",)),
    _r("tender", "Coral Tender", "grown", 3, "medicine", 2, 3.0,
       {"credits": 3800, "biomass": 12, "phosphate": 2},
       {"biomass": 0.005},
       "intima",
       "Husbandry, for a holding that is alive. Reads a reef the way a "
       "physician reads a patient, and is one when it has to be.",
       "Anthozoa curans", duties=("works",)),
    _r("ossuary", "Ossuary Frame", "grown", 1, "", 5, 14.0,
       {"credits": 4200, "biomass": 16, "phosphate": 4},
       {"biomass": 0.008},
       "osteoid",
       "Four tonnes of grown bone that lifts what nothing else aboard can. "
       "Somebody has to be at the other end of it, close.",
       "Osteon ferens", duties=("works", "cargo")),

    # ── hybrid: a person and a machine, and both bills ─────────────────────
    _r("graftpilot", "Graft-Pilot", "hybrid", 3, "nav", 4, 0.6,
       {"credits": 8800, "biomass": 5, "silicon": 3},
       {"credits": 6, "biomass": 0.002, "silicon": 0.001},
       "mea",
       "A navigator wired into the helm at the spine. Flies as well asleep as "
       "most bridges do awake, and cannot be unplugged in a hurry.",
       duties=()),
    _r("wetgunner", "Wet-wired Gunner", "hybrid", 3, "tactical", 4, 0.6,
       {"credits": 9200, "biomass": 5, "silicon": 3},
       {"credits": 6, "biomass": 0.002, "silicon": 0.001},
       "mea",
       "Direct bioelectric interface to the mounts. Lays a gun by wanting to, "
       "and dreams about it afterwards.",
       duties=()),
    _r("chorusgraft", "Chorus Graft", "hybrid", 4, "medicine", 3, 1.0,
       {"credits": 10500, "biomass": 6, "silicon": 5, "magnetite": 2},
       {"credits": 4, "biomass": 0.002, "silicon": 0.002},
       "neuromorphic",
       "A recording carried in living tissue: the Choir's patience with a "
       "pulse. The Charter has never decided which licence it needs.",
       "Chorus incarnatus", duties=("ground",)),

    # ── xeno: recovered, working, and unexplained ─────────────────────────
    _r("attendant", "Weave Attendant", "xeno", 4, "comms", 5, 1.8,
       {"credits": 0, "xenolith": 3},
       {"volatiles": 0.003},
       "xenoalloy",
       "Found standing at a gate, doing something. It has continued doing it "
       "since, and now does it near you.",
       "Custos viae", duties=("works", "survey")),
    _r("shardling", "Shardling Swarm", "xeno", 3, "", 4, 2.4,
       {"credits": 0, "xenolith": 2},
       {"volatiles": 0.002},
       "xenoalloy",
       "Forty-odd pieces that behave as one and will not be counted twice. "
       "They mend things. Nobody asked them to.",
       "Fragmentum gregis", duties=("mine", "survey", "repair")),
]

ROBOTS_BY_ID: dict[str, RobotClass] = {r.id: r for r in ROBOTS}

#: Which families read as machines with no person in them. A hybrid has
#: somebody inside it, which is why it is charged wages as well as parts.
CREWED_FAMILIES = ("hybrid",)


def by_family(family: str) -> list[RobotClass]:
    return [r for r in ROBOTS if r.family == family]


def with_duty(duty: str) -> list[RobotClass]:
    return [r for r in ROBOTS if duty in r.duties]


def autonomy_name(level: int) -> str:
    return AUTONOMY.get(level, AUTONOMY[2])[0]


def autonomy_tint(level: int) -> str:
    return AUTONOMY.get(level, AUTONOMY[2])[1]


def autonomy_note(level: int) -> str:
    return AUTONOMY.get(level, AUTONOMY[2])[2]
