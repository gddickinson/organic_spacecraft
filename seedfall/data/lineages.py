"""What a crew member is made of, and what that costs per day and per decade.

The game had one kind of person. Everyone aboard breathed the same air, ate
nothing in particular, and never got a day older however long the crossing —
while the opening screen offered you a **Dry Choir** lineage and promised "no
air to run out of", and the daily tick killed your recordings by asphyxiation
exactly as fast as it killed anybody else.

So: a lineage is a substrate. It decides three things that used to be uniform.

**How long you last.** A wet crew has a working life measured in decades and a
hard stop after it. A Dry Choir recording does not age at all — it *drifts*,
losing fidelity every time it is rewritten, which is slower but not kinder. A
grafted crew splits the difference and pays for it in maintenance.

**What you burn.** Wet people want atmosphere and something to eat, which the
intima and the hold provide. Recordings want power and the metals they repair
themselves with, and would not notice a breach. Grafts want a little of both.
All of it comes out of commodities the economy already trades, deliberately:
an upkeep bill payable in a currency nobody sells is not a decision.

**How the crossing feels.** A hundred days is a season to a wet crew, an
inconvenience to a graft, and very nearly nothing to a lineage that measures
its life in centuries. `time_sense` is the line each one says about a long
transit, and `boredom` is what that costs in morale.

Figures are years and tonnes-per-person-per-day. They are small numbers; a
crew of thirty over a two-hundred-day crossing turns them into real cargo.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Lineage:
    id: str
    name: str
    #: One line for a screen.
    what: str

    # ── time ───────────────────────────────────────────────────────────────
    #: Years before decline sets in, and the age past which almost none work.
    prime: float
    span: float
    #: Years of ageing per year of clock. A graft runs slow; a recording
    #: barely runs at all. This is the number hibernation later reduces.
    ageing: float
    #: What decline actually does: fraction of a level lost per year past
    #: `prime`. Recordings lose fidelity rather than strength, but it reads
    #: on the same dial.
    decline: float

    # ── upkeep ─────────────────────────────────────────────────────────────
    #: Tonnes per person per day, by commodity. Drawn from the hold, then
    #: from stores.
    upkeep: dict = field(default_factory=dict)
    #: Does the atmosphere plant matter to them? A recording does not care
    #: that the intima has stopped, and saying so was the whole point.
    breathes: bool = True
    #: Kilowatts per person, against the ship's power budget.
    draw: float = 0.0

    # ── temperament ────────────────────────────────────────────────────────
    #: What a long crossing does to them, and what it costs in morale a day.
    time_sense: str = ""
    boredom: float = 0.0
    #: What to call the end, when it comes.
    ending: str = "died of old age"
    #: Where you can recruit one: which port cultures produce this lineage.
    common: bool = True


#: One tonne of biomass feeds one person for one year — about 2.7 kg a day of
#: make-up into a closed loop that recycles most of it. Deliberately a figure
#: a captain can hold in their head: a year is a tonne a head.
_FOOD = 1.0 / 365.0

LINEAGES = [
    Lineage(
        "wet", "Wet", "Ordinary human stock. Breathes, eats, ages, and "
        "notices things nothing else aboard notices.",
        prime=52.0, span=96.0, ageing=1.0, decline=0.06,
        upkeep={"biomass": _FOOD}, breathes=True, draw=0.10,
        time_sense="A long crossing is a season out of a life that has a "
                   "number of them.",
        boredom=0.012, ending="died of old age"),

    Lineage(
        "grafted", "Grafted", "Wet where it helps, dry where it does not. "
        "Two maintenance bills and a longer run to spend them on.",
        prime=88.0, span=164.0, ageing=0.58, decline=0.045,
        upkeep={"biomass": _FOOD * 0.6, "magnetite": 0.00035},
        breathes=True, draw=0.35,
        time_sense="Long enough to be tedious, not long enough to matter.",
        boredom=0.006, ending="failed at the seams"),

    Lineage(
        "dry", "Dry Choir", "A lineage of recordings. Does not breathe, does "
        "not eat, and does not get older — it gets less certain.",
        # Not ageless: every rewrite loses something. A recording that has
        # run six centuries is a copy of a copy and knows it.
        prime=240.0, span=620.0, ageing=0.14, decline=0.02,
        upkeep={"silicon": 0.0009, "magnetite": 0.0006},
        breathes=False, draw=1.6,
        time_sense="Two hundred days is a gap in the canon, and gaps are "
                   "filled in later by whoever is still running.",
        boredom=0.0, ending="drifted past recovery", common=False),

    Lineage(
        "xeno", "Xenoform", "Something the Verge did not grow. It keeps its "
        "own hours and will not say what it is for.",
        prime=380.0, span=900.0, ageing=0.07, decline=0.015,
        upkeep={"volatiles": 0.002, "xenolith": 0.00002},
        breathes=False, draw=0.4,
        time_sense="It does not appear to distinguish between a crossing and "
                   "a berth.",
        boredom=0.0, ending="went quiet", common=False),
]
LINEAGES_BY_ID = {lineage.id: lineage for lineage in LINEAGES}

#: The opening screen's stocks map onto lineages. `grafted` and `wet` share
#: their names with a stock; the Choir's stock id is `dry`.
STOCK_LINEAGE = {"wet": "wet", "dry": "dry", "grafted": "grafted"}

#: What a chronicle defaults to when nothing said otherwise — including every
#: save written before lineages existed.
DEFAULT = "wet"


def of_stock(stock_id: str | None) -> str:
    """Which lineage a captain of this stock crews their hull with."""
    return STOCK_LINEAGE.get(stock_id or "", DEFAULT)


def recruitable() -> list:
    """Lineages a port will actually offer you."""
    return [lineage for lineage in LINEAGES if lineage.common]
