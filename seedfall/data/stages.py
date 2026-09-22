"""The stages of a working life, and what each one is worth.

A person had **one** number for age and it did two jobs badly. `officer.age`
advances at the lineage's own rate, slowed by a cold berth and slowed again by
anagathics — so it was never years-since-birth, it was *wear on the body*
wearing a name that said otherwise. Nothing anywhere asked how long somebody
had actually been alive, which is why a recording could be signed on at forty
and have been running since before the Verge was settled without a single
screen noticing.

Two clocks now (`sim/lifespan.py`):

- **Lived** — years since they were born, at one year a year, for everybody.
  Nothing slows it. A century in a rack is still a century.
- **Aged** — what those years did to *this* substrate, at the lineage's rate,
  less whatever was paid to slow it. This is the old `officer.age`, and it is
  the one that decides what they can still do.

And the gap between them is a fact about a person in its own right. Somebody
who has lived two hundred years and aged thirty has read everything and knows
nobody; the table at the bottom of this file is what that is worth and what
it costs.

**Stages are measured against the lineage's own prime**, not against a number
of years, so a Dry Choir recording is green for its first ninety years and a
vatborn is green for fifteen — and both of them are green in the same way.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stage:
    """One stretch of a working life."""

    id: str
    name: str
    #: Where it ends, in units of the lineage's prime. `None` runs to the
    #: span, and the terminal stage runs past it.
    upto: float | None
    #: What the body and the head are worth here, as characteristic deltas
    #: folded onto the derived record (`sim/lifepath.py`).
    gives: dict = field(default_factory=dict)
    #: How fast they pick things up, against the middle of a career.
    learns: float = 1.0
    #: How fast the years take a level off them, against `lineage.decline`.
    wears: float = 1.0
    #: What it feels like, for a screen.
    note: str = ""


#: The stages, youngest first. The thresholds are shares of the lineage's
#: prime; `upto=None` on `declining` means "as far as the span reaches".
#:
#: The shape is deliberate and is not a straight decline: the young are
#: quick and strong and nobody listens to them, the middle is the best of
#: both, and the old are worth having for exactly the reasons a hard watch
#: does not want them. A crew of one age is a crew missing something.
STAGES: tuple = (
    Stage("green", "Green", 0.40,
          gives={"str": 1, "dex": 1, "edu": -1, "soc": -1},
          learns=1.45, wears=0.55,
          note="Fast, strong, and nobody has listened to them yet. Learns "
               "half again as quickly as anybody else aboard."),
    Stage("coming", "Coming up", 0.72,
          gives={"dex": 1},
          learns=1.20, wears=0.75,
          note="Knows the job and has not yet been slowed by it."),
    Stage("prime", "Prime", 1.00,
          gives={},
          learns=1.00, wears=1.00,
          note="Everything works, and everything they know is current. It "
               "does not last."),
    Stage("seasoned", "Seasoned", 1.20,
          gives={"int": 1, "edu": 1, "str": -1},
          learns=0.80, wears=1.10,
          note="Past their best and better at the job for it. Slower to "
               "learn something new and rarely needs to."),
    Stage("declining", "Declining", None,
          gives={"edu": 1, "soc": 1, "str": -2, "dex": -2, "end": -1},
          learns=0.50, wears=1.35,
          note="The body is going and the judgment is not. Worth a berth "
               "for what is in their head."),
    Stage("past their span", "Past their span", None,
          gives={"edu": 2, "soc": 1, "str": -3, "dex": -3, "end": -2},
          learns=0.30, wears=1.80,
          note="Working past what the lineage manages. Every year is "
               "borrowed and they know it."),
)
STAGE_BY_ID = {s.id: s for s in STAGES}

#: The two ids `ui/ship_view.py` warns on. Named here so the warning and the
#: table cannot drift apart.
FAILING = ("declining", "past their span")


@dataclass(frozen=True)
class Gap:
    """What the distance between the two clocks is worth."""

    id: str
    name: str
    #: Years of lived-minus-aged at or above which this band applies.
    years: float
    gives: dict = field(default_factory=dict)
    note: str = ""


#: Lived years minus aged years, and what that does to somebody.
#:
#: This is the whole reason for keeping two clocks. A graft of eighty who has
#: aged fifty has seen thirty more years than their body has; a recording that
#: has been running for three centuries has forgotten more than the rest of
#: the bridge has learned and cannot hold a conversation about any of it.
#: Both are *worth something*, and both cost something, and until there were
#: two clocks neither could be said at all.
GAPS: tuple = (
    Gap("instep", "In step", 0.0,
        note="Their years and their body agree."),
    Gap("longlived", "Long-lived", 12.0,
        gives={"edu": 1},
        note="Has had more time to read than their body suggests."),
    Gap("outofstep", "Out of step", 60.0,
        gives={"edu": 1, "soc": -1},
        note="Everybody they trained with is dead. They are still working, "
             "and it shows in the way a room goes quiet."),
    Gap("another_age", "From another age", 200.0,
        gives={"edu": 2, "soc": -2},
        note="Remembers the Verge before it was this. Nobody aboard can "
             "check any of it, and nobody aboard quite believes it either."),
)


def stage_for(aged: float, prime: float, span: float) -> Stage:
    """Which stretch of a life this is, against that lineage's own clock."""
    if aged >= span:
        return STAGE_BY_ID["past their span"]
    share = aged / max(1.0, prime)
    for stage in STAGES:
        if stage.upto is not None and share < stage.upto:
            return stage
    return STAGE_BY_ID["declining"]


def gap_for(lived: float, aged: float) -> Gap:
    """Which band the distance between the two clocks falls in."""
    over = max(0.0, lived - aged)
    got = GAPS[0]
    for band in GAPS:
        if over >= band.years:
            got = band
    return got
