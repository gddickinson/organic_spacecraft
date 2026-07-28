"""Weather on the ground.

Terrain is fixed the moment you land; weather is not. A front rolls in over a
few days, makes every tile dearer and more dangerous to cross, and then rolls
out again. It is what turns "how far dare we push" into a question with a
second half — because the answer changes while you are out there, and the walk
home is longer than the walk out when you are doing it in a whiteout.

Sitting a bad front out costs a day of supply and nothing else. That is often
the right answer, and it is always a decision.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Weather:
    id: str
    name: str
    tint: str
    blurb: str
    #: Added to the cost of entering any tile.
    cost: int
    #: Multiplies a tile's chance of springing a hazard.
    danger: float
    #: How far the party can see, in tiles. Clear weather is 2.
    sight: int
    #: Refuses movement entirely — you sit it out or you lose people.
    pinned: bool = False
    #: Which biomes it can occur on; empty means anywhere. These must be real
    #: biome ids from world/planets — a gate on a name that does not exist
    #: makes the whole condition unreachable, which is how the first draft of
    #: this file lost its whiteout and its downpour.
    biomes: tuple[str, ...] = ()
    weight: float = 1.0


CLEAR = Weather("clear", "Clear", "dim",
                "Flat light, hard shadows, and nothing moving that you did "
                "not bring with you.",
                cost=0, danger=1.0, sight=2, weight=6)

WEATHERS: list[Weather] = [
    CLEAR,

    Weather("dust", "Dust storm", "osteo",
            "The horizon closes to arm's length and the static builds until "
            "the rover's instruments are guessing.",
            cost=1, danger=1.8, sight=1, weight=3),

    Weather("whiteout", "Whiteout", "warn",
            "Ice crystals in suspension. There is no up, no horizon and no "
            "way to hold a bearing without the inertial set.",
            cost=2, danger=2.2, sight=0, biomes=("cryo", "subsurface"),
            weight=2),

    Weather("squall", "Radiation squall", "warn",
            "The star has thrown something and the magnetosphere, such as it "
            "is, is not stopping it. Suits are counting.",
            cost=1, danger=2.0, sight=2, weight=2),

    Weather("downpour", "Downpour", "lumen",
            "Whatever passes for rain here, coming down hard enough to move "
            "the regolith under the tracks.",
            cost=1, danger=1.6, sight=1,
            biomes=("verdant", "microbial", "sulfuric"), weight=2),

    Weather("tremor", "Ground tremors", "warn",
            "The whole plain is ringing. Something large is settling a long "
            "way down and everything above it is arguing about it.",
            cost=1, danger=2.4, sight=2, weight=1),

    Weather("gale", "Katabatic gale", "warn",
            "Cold air falling off the high ground at a hundred and forty "
            "knots. Nothing walks in this and the rover will not hold a line.",
            cost=3, danger=2.6, sight=1, pinned=True, weight=1),
]

WEATHERS_BY_ID = {w.id: w for w in WEATHERS}

#: A front lasts this many days, low and high.
FRONT_DAYS = (2, 6)
#: Chance per day that the weather turns over.
TURNOVER = 0.16
