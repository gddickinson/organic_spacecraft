"""Putting the crew under, and what each way of doing it costs them.

The time system gave a crossing a price in people: a wet crew ages a year per
year and eats a tonne a head per year, and a two-hundred-day run is seven
months of a life that has about fifty working ones in it. It gave exactly one
answer — fly harder, at 1× to 11× dilation and up to five times the reaction
mass. That is an engineering answer to a biological problem, and it was the
only one on the table.

This is the biological answer. `trehalose` has been in the commodity tables
since the beginning, described as *"vitrified sugar with CAHS proteins;
replaces the water in a cell and holds it, unbreathing"* — the real sugar real
tardigrades use to survive desiccation — and nothing in the game ever consumed
a gram of it. Now the deepest sleep does.

Four things separate these methods, and every one of them is a reason to pick
a different one:

- **What it saves.** Ageing and upkeep, as a share of what being awake costs.
- **What it risks.** Somebody may not come back up. Stated as odds per sleeper
  per hundred days, because a risk quoted per crossing is a risk nobody can
  compare.
- **What it costs to run.** Trehalose for the deep methods; power for the dry.
- **Who it works on.** A Dry Choir recording does not freeze; it idles. A wet
  crew cannot idle; it has to be cooled. Nothing works on everybody.

**Somebody has to stay awake.** `MIN_WATCH` is the floor, and it is why
dormancy never becomes an off switch for the whole problem: the hull still
needs a watch, and the watch still ages.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Method:
    id: str
    name: str
    blurb: str
    #: Ageing and upkeep a sleeper still incurs, as a share of being awake.
    ageing: float
    upkeep: float
    #: Chance per sleeper of not waking, per hundred days under.
    risk: float
    #: Consumed per sleeper per hundred days.
    cost: dict = field(default_factory=dict)
    #: Which lineages this works on at all. Empty means all of them.
    lineages: tuple = ()
    #: Technology required, if any.
    needs_tech: str | None = None
    #: Levels of skill a sleeper loses per year under. Coming back is not
    #: free even when it works.
    atrophy: float = 0.0
    #: What the player should weigh.
    gives: str = ""
    costs: str = ""


METHODS = [
    Method("watch", "Stand the watch",
           "Nobody sleeps. The hull is fully crewed, everything aboard runs "
           "at its proper rate, and everyone lives every day of the crossing.",
           ageing=1.0, upkeep=1.0, risk=0.0,
           gives="Full watches, full bench, full workshop. No risk at all.",
           costs="Every day of the crossing is a day out of every life "
                 "aboard, and a day's rations for all of them."),

    Method("cold", "Cold sleep",
           "Core temperature down, metabolism to a crawl, waking every few "
           "weeks whether they need to or not. Old, well understood, and "
           "nobody has ever pretended it is comfortable.",
           ageing=0.35, upkeep=0.30, risk=0.6,
           cost={"biomass": 0.08},
           lineages=("wet", "grafted"),
           atrophy=0.10,
           gives="Two thirds of the ageing and seven tenths of the rations, "
                 "for very little risk.",
           costs="They come up slower than they went down, and it shows."),

    Method("vitrify", "Trehalose vitrification",
           "The water in the cell is replaced with sugar glass and the cell "
           "is simply stopped. The Verge learned it from something that had "
           "been doing it for four hundred million years.",
           ageing=0.04, upkeep=0.05, risk=2.4,
           # 0.55 put ninety-nine tonnes of a six-hundred-credit sugar into
           # one crossing — a third of the hold and sixty thousand credits,
           # which is not an expensive option, it is a closed door.
           cost={"trehalose": 0.18},
           lineages=("wet", "grafted", "xeno"),
           needs_tech="trehalose",
           atrophy=0.22,
           gives="A crossing that costs a wet crew almost nothing of their "
                 "span, and almost nothing to feed.",
           costs="Two and a half per cent a head per hundred days do not come "
                 "back up, and those who do have lost a step."),

    Method("idle", "Low-power idle",
           "Not sleep. The lineage drops to a maintenance loop, keeps a "
           "thread on the hull, and afterwards describes the crossing as "
           "having been brief.",
           ageing=0.15, upkeep=0.22, risk=0.05,
           lineages=("dry",),
           atrophy=0.0,
           gives="Nearly free, nearly safe, and nothing is lost on the way "
                 "back up. The advantage of not being made of meat.",
           costs="Only a Dry Choir lineage can do it, and even they leave a "
                 "gap in the canon."),
]
METHODS_BY_ID = {m.id: m for m in METHODS}

#: Fraction of the complement that must stay awake, whatever the method. The
#: hull needs a watch; the watch ages. This is why dormancy is a way of paying
#: less for a crossing and never a way of paying nothing.
MIN_WATCH = 0.18

#: How much of the ship's own work still gets done, at a given awake share.
#: A skeleton watch keeps the hull alive and does not run a research
#: programme — which is the brake that stops dormancy and hard burns from
#: being a free stack: both cost you the same thing, and doing both costs it
#: twice.
def work_share(awake: float) -> float:
    """Research, repair and refining, as a share of a full watch."""
    return max(0.08, min(1.0, awake ** 0.7))


#: Days under before waking is worth logging at all.
NOTICEABLE = 20
