"""Works — what a colony becomes after it is planted.

A seed put down on a rock is the beginning of a settlement, not the end of one.
A work is a commitment of material and time that changes what a colony *is*:
what it produces, what it costs to keep, and what it can do for you. They are
the reason to fly ore somewhere rather than sell it, and the reason two RADIX
mines twenty years apart are not the same place.

Each colony runs one work at a time and keeps every work it finishes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: A colony may hold no more works than this; after that it is what it is.
MAX_WORKS = 4

#: What each colony past the first adds to the daily bill of running *every*
#: colony you hold, in credits: the Nth costs `ADMIN_STEP × (N − 1)`.
#:
#: An empire used to be free to administer. A POMONA Grove pays itself back
#: in 45 days and yields for ever, there are about 125 plantable sites in a
#: sector, and nothing capped how many you held — so colony spam was the
#: strategy and the game had no late-game credit sink at all. At twelve the
#: bill is nothing at five holdings (120 a day against about a thousand
#: earned), real at fifteen (1,260), and past twenty-five it eats the
#: margin — which is a ceiling a player meets rather than one the code
#: imposes.
ADMIN_STEP = 12.0


@dataclass(frozen=True)
class Work:
    id: str
    name: str
    blurb: str
    days: int
    cost: dict[str, float]
    #: Which colony families may undertake it; empty means any.
    families: tuple[str, ...] = ()
    #: Only offered to colonies that already yield these materials.
    needs_yield: tuple[str, ...] = ()
    #: Research that must be in hand first.
    tech: str | None = None
    #: Multiplies the colony's own yields.
    yield_mul: dict[str, float] = field(default_factory=dict)
    #: Adds flat production per day.
    yield_add: dict[str, float] = field(default_factory=dict)
    #: Adds to what the colony costs to run, per day.
    upkeep_add: dict[str, float] = field(default_factory=dict)
    #: Folded into the colony's effects, using the same vocabulary as a class.
    effects: dict = field(default_factory=dict)
    #: Multiplies the settlement's population ceiling.
    pop_mul: float = 1.0


WORKS: list[Work] = [
    Work("deepen", "Deepen the workings",
         "Follow the seam down. The first hundred metres were the easy ones, "
         "and everything below them pays better.",
         days=90, cost={"credits": 6000, "alloy": 18},
         needs_yield=("ore", "volatiles", "phosphate", "biomass"),
         yield_mul={"ore": 1.7, "volatiles": 1.7, "phosphate": 1.7,
                    "biomass": 1.45},
         upkeep_add={"biomass": 0.06}),

    Work("garrison", "Raise a garrison",
         "Guns, a watch rota, and somewhere to put both. A settlement that can "
         "shoot back is a settlement the Bloom learns to go around.",
         days=70, cost={"credits": 7500, "alloy": 24, "ore": 20},
         effects={"ward": 0.28, "watch": 1}),

    Work("slipway", "Lay a slipway",
         "Berths, gantries and a hard vacuum dock. Hulls can be laid down here "
         "instead of being flown in from somewhere civilised.",
         days=140, cost={"credits": 14000, "alloy": 40, "ore": 30},
         effects={"build_here": 1, "drydock": 1}),

    Work("mast", "Erect a sensor mast",
         "A long baseline and something quiet to hang it on. You will see who "
         "is coming across this system a long time before they arrive.",
         days=60, cost={"credits": 5000, "alloy": 14},
         effects={"sensor": 2}),

    Work("habitat", "Ring the habitat",
         "Housing, hydroponics and a reason for families to stay. Population "
         "is not sentiment — it is the labour that everything else needs.",
         days=110, cost={"credits": 9000, "biomass": 30, "alloy": 16},
         yield_add={"credits": 55},
         upkeep_add={"biomass": 0.12}, pop_mul=1.9),

    Work("annex", "Build a xenology annex",
         "Benches, a clean room and somewhere to put things nobody understands "
         "yet. Findings go up the chain to your own people first.",
         days=100, cost={"credits": 11000, "alloy": 22},
         # Was "xenolinguistics", which is in neither the research tree nor the
         # xenotechnologies — so no colony in the game could ever build this,
         # measured at 0 of 19 classes with everything unlocked.
         tech="xenobiology",
         yield_add={"research": 0.5}, effects={"diplomacy": 0.04}),

    Work("harbour", "Open a free harbour",
         "Bond the warehouses, licence the brokers and let anyone tie up. The "
         "traffic is worth more than the tariffs.",
         days=120, cost={"credits": 13000, "alloy": 26},
         yield_add={"credits": 70}, effects={"port": 1, "diplomacy": 0.05}),

    Work("vault", "Sink a lineage vault",
         "Deep, cold, and stocked with the canon of everything you have grown. "
         "If the worst happens somewhere else, it does not happen here.",
         days=130, cost={"credits": 12000, "biomass": 40},
         families=("grown",), effects={"vault": 1}),
]

WORKS_BY_ID = {w.id: w for w in WORKS}
