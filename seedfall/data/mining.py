"""How you work a body, not just for how long.

Extraction used to be a rate: park, wait, tonnage. What was missing was the
decision every mining operation actually turns on — how hard to push. Skimming
the surface costs nothing and gets you very little. A deep bore reaches grades
nothing else can and eats the hull doing it. Leaching recovers more of what is
there than any of them, and takes a season.

Depth is the other half. A seam nobody can reach is not an asset, so what your
rig can get to is as much a part of a body's worth as what is in it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Seams sit at one of three depths. A method reaches down to its own limit.
DEPTH_NAMES = ["Surface", "Shallow", "Deep"]


@dataclass(frozen=True)
class Method:
    id: str
    name: str
    blurb: str
    #: Deepest seam this method can work, indexing DEPTH_NAMES.
    reach: int
    #: Multiplies tonnes per day.
    yield_mul: float
    #: Multiplies how fast the body is worked out.
    depletion_mul: float
    #: Hull damage per day, as a fraction of the outermost layer.
    wear: float
    #: Chance per spell of something going wrong.
    risk: float
    #: Reaction mass or biomass burned per day.
    upkeep: dict[str, float] = field(default_factory=dict)
    #: A ship stat that must be greater than zero to use this at all.
    needs: str | None = None


METHODS: list[Method] = [
    Method("skim", "Skim the surface",
           "Regolith and loose float, swept up and sorted. It costs nothing "
           "and it takes nothing out of the body worth mentioning.",
           reach=0, yield_mul=0.55, depletion_mul=0.25, wear=0.0, risk=0.0),

    Method("cut", "Open cut",
           "Strip the overburden and work the seam you can see. The way "
           "everybody does it, for the reasons everybody does it.",
           reach=1, yield_mul=1.0, depletion_mul=1.0, wear=0.0012, risk=0.06),

    Method("bore", "Deep bore",
           "Sink a shaft and go after what the survey says is down there. "
           "Hard on the rig, hard on the hull, and the only way to reach it.",
           reach=2, yield_mul=1.75, depletion_mul=2.1, wear=0.0045, risk=0.20,
           upkeep={"volatiles": 0.6}),

    Method("leach", "Bioleach",
           "Flood the workings with something hungry and come back later. "
           "Slow, gentle, and it recovers what a bore would leave behind.",
           reach=2, yield_mul=0.8, depletion_mul=0.35, wear=0.0, risk=0.02,
           upkeep={"biomass": 0.35}, needs="drink"),
]

METHODS_BY_ID = {m.id: m for m in METHODS}
DEFAULT_METHOD = "cut"


@dataclass(frozen=True)
class Mishap:
    id: str
    name: str
    text: str
    #: Fraction of the outermost hull layer lost.
    damage: float = 0.0
    #: Tonnes of the spell's yield lost.
    spoil: float = 0.0
    #: Extra depletion inflicted.
    collapse: float = 0.0


MISHAPS: list[Mishap] = [
    Mishap("bind", "The bore binds",
           "The string seizes two hundred metres down and comes up in pieces. "
           "A day lost and a rig to rebuild.", damage=0.05, spoil=0.15),
    Mishap("collapse", "The workings collapse",
           "The face comes in overnight. Nobody was under it, which is luck "
           "rather than planning, and the seam is buried.", collapse=0.12),
    Mishap("pocket", "A gas pocket",
           "Something under pressure that the survey did not mention. The "
           "hull took the worst of it.", damage=0.09, spoil=0.10),
    Mishap("spoil", "The load is contaminated",
           "Half the spoil heap is worthless and it was not obvious until it "
           "was aboard.", spoil=0.35),
]

#: A rich strike is the other tail of the same distribution.
STRIKE_CHANCE = 0.10
STRIKE_BONUS = 0.45
