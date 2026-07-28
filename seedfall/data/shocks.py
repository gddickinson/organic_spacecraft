"""Things that happen to a market.

Prices used to drift and nothing ever *happened*. A shock is a named event with
a cause, a direction and a life: a blight that halves a farm world's output for
a season, a convoy lost that leaves a port short of alloy, a seam that comes in
and floods the sector with ore. They are what makes a trade route worth
watching rather than memorising.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShockKind:
    id: str
    name: str
    tint: str
    #: {commodity} and {place} are filled in.
    text: str
    #: Which commodities it can strike. Empty means any.
    goods: tuple[str, ...]
    #: Multiplies local supply: below one is a shortage, above one a glut.
    supply: float
    #: Days it lasts, low and high.
    days: tuple[int, int]
    #: Relative frequency.
    weight: float


SHOCKS: list[ShockKind] = [
    ShockKind("blight", "Blight", "warn",
              "A blight has gone through the growing stacks at {place}. "
              "{commodity} is not coming out of here this season.",
              goods=("biomass", "protein", "spidroin"), supply=0.35,
              days=(90, 220), weight=3),

    ShockKind("strike", "The yards have stopped", "osteo",
              "The fitters at {place} have downed tools over the licence "
              "terms. Nothing is being made and {commodity} is short.",
              goods=("alloy", "components", "ceramic"), supply=0.45,
              days=(60, 160), weight=3),

    ShockKind("convoy", "A convoy did not arrive", "warn",
              "The quarterly run into {place} never made it. Whatever "
              "happened to it, there is no {commodity} on the quay.",
              goods=(), supply=0.40, days=(50, 140), weight=4),

    ShockKind("strikeit", "A seam came in", "chloro",
              "Somebody at {place} hit something enormous. {commodity} is "
              "piled on the quay and the price has fallen out of it.",
              goods=("ore", "phosphate", "volatiles"), supply=2.2,
              days=(80, 200), weight=3),

    ShockKind("dumping", "The Concordat is dumping", "chloro",
              "Concordat yards are clearing a stockpile through {place}. "
              "{commodity} is cheaper here than it is to make.",
              goods=("alloy", "components", "ceramic", "reactor"), supply=1.9,
              days=(70, 170), weight=2),

    ShockKind("quarantine", "Quarantine", "warn",
              "{place} is closed to organic cargo pending an inspection "
              "nobody expects to end soon. {commodity} cannot move.",
              goods=("biomass", "protein", "seedstock"), supply=0.5,
              days=(80, 200), weight=2),

    ShockKind("rearm", "Somebody is rearming", "osteo",
              "Buyers at {place} are taking every {commodity} on offer and "
              "not saying what for.",
              goods=("alloy", "components", "reactor", "ordnance"),
              supply=0.5, days=(60, 150), weight=3),
]

SHOCKS_BY_ID = {s.id: s for s in SHOCKS}

#: Chance per system per 30 days that something happens somewhere.
ONSET_PER_MONTH = 0.020

#: A system holds at most this many at once.
MAX_PER_SYSTEM = 2

#: A price you noted this long ago is worth very little.
STALE_DAYS = 400
