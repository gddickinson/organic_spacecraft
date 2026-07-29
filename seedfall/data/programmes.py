"""Standing programmes: what a bench does once it has learned everything.

The tech tree is finite — sixty-two nodes, 28,790 points end to end — and the
game is explicitly built to carry on after every one of its ten endings. So
there is a day, and not a rare one, when the last node lights and the bench has
nothing left to do. Measured on a generous rate the tree closed on day 2,014
and the ship then accrued **146,040 research points over ten years that bought
nothing at all**: every laboratory, every CHORUS node, the `research` bonus on
eight technologies and the whole survey economy behind them feeding a number
`ui/tech_view.py` *displayed* and no code could ever spend.

A programme is the answer, and it is deliberately not another tech tree. It
never finishes; it completes a **round**, each dearer than the last, and each
round yields a **finding** — a result you own and have to decide what to do
with. Findings buy no hull points and no stat, on purpose: what they buy is
standing, or money, and choosing which is the interesting part. An endgame
bench that fed the ship would only inflate it.

Programmes open per branch, when every technology in that branch is unlocked.
That is deliberate too. A captain who drives one branch hard is running a
programme in it long before the tree is exhausted, so this is the same
machinery arriving late rather than a separate mode bolted onto the end.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Programme:
    """One standing line of inquiry, opened by exhausting a branch."""

    id: str
    name: str
    #: The tech branch that must be complete before this opens.
    branch: str
    #: Points for the first round. Later rounds cost more — `ROUND_GROWTH`.
    base_cost: float
    #: What the resulting paper is about, for the powers that care.
    subject: str
    blurb: str


PROGRAMMES: list[Programme] = [
    Programme("pathology", "Bloom pathology", "xenology", 900,
              "the Bloom",
              "What the husk does to a hull at the cellular level, written "
              "down properly for once. Everybody wants this and nobody wants "
              "to be seen paying for it."),
    Programme("cognition", "Wet cognition", "cognition", 1100,
              "thinking tissue",
              "Recordings of a grown mind doing arithmetic no dry stack can. "
              "The Choir has never explained why it pays so well."),
    Programme("morphology", "Directed morphogenesis", "morphogenesis", 1000,
              "growing to order",
              "Making a hull grow the shape you asked for rather than the "
              "shape it fancies. The Charter regards this as doctrine and the "
              "Yards as an admission."),
    Programme("metallurgy", "Grown-metal interfaces", "fabrication", 850,
              "bone and plate",
              "Where bone meets rolled plate, and why the join fails. Of "
              "enormous interest to anyone building hybrids and of none "
              "whatever to purists."),
    Programme("metabolics", "Closed-loop metabolics", "metabolism", 800,
              "the phosphorus problem",
              "Getting a hull's phosphorus back out of its own waste. The "
              "bottleneck the whole sector is built around."),
    Programme("frames", "Load paths in living frames", "structure", 750,
              "grown structure",
              "How a bone frame carries a load it was never grown for, up to "
              "the point where it stops."),
    Programme("drives", "Reaction-mass economy", "propulsion", 950,
              "getting there",
              "Squeezing another few per cent out of a drive nobody has "
              "improved in a century."),
    Programme("husbandry", "Long-haul husbandry", "survival", 700,
              "keeping people alive",
              "What a decade in a hull does to a crew, and which of it can be "
              "prevented. Unglamorous and quietly priceless."),
    Programme("yields", "Extraction yields", "industry", 700,
              "getting it out of the ground",
              "Why a seam assays better than it digs, and what to do about "
              "it."),
    Programme("statecraft", "Comparative statecraft", "governance", 900,
              "how the powers work",
              "An honest account of how the four powers actually make "
              "decisions. Nobody involved will enjoy reading it."),
]

PROGRAMMES_BY_ID = {p.id: p for p in PROGRAMMES}

#: How much dearer each round is than the one before.
#:
#: This is what stops a finished tree becoming a points fountain. At 1.4 the
#: tenth round of a programme costs twenty times the first, so a bench running
#: one line for ever turns out findings ever more slowly rather than printing
#: them. It has to exceed 1: at 1.0 a mature bench produces a finding every few
#: weeks indefinitely, which is exactly the free lunch this design avoids.
ROUND_GROWTH = 1.4

#: What a finding is worth, per point the round that made it cost.
#:
#: Derived from the round cost and nowhere else, so a later and dearer round
#: yields a better paper without a second table to drift out of step with the
#: first. This project has watched a second table drift three times.
WORTH_PER_POINT = 0.011

#: How much a power cares about each subject, as a multiplier on a finding
#: filed with them. 1.0 is polite interest.
#:
#: Every power has an opinion about every subject — there are no zeroes,
#: because a finding nobody would take is a finding that cannot be spent, and
#: an unspendable finding is the fault this file exists to fix.
INTEREST: dict[str, dict[str, float]] = {
    "pathology":  {"charter": 1.5, "concordat": 0.9, "freeholds": 0.8,
                   "sanhedrin": 1.3},
    "cognition":  {"charter": 1.1, "concordat": 0.7, "freeholds": 0.8,
                   "sanhedrin": 2.0},
    "morphology": {"charter": 1.9, "concordat": 0.6, "freeholds": 1.0,
                   "sanhedrin": 0.9},
    "metallurgy": {"charter": 0.6, "concordat": 1.4, "freeholds": 1.8,
                   "sanhedrin": 0.8},
    "metabolics": {"charter": 1.7, "concordat": 1.0, "freeholds": 1.1,
                   "sanhedrin": 0.7},
    "frames":     {"charter": 1.5, "concordat": 1.2, "freeholds": 1.0,
                   "sanhedrin": 0.6},
    "drives":     {"charter": 0.9, "concordat": 1.8, "freeholds": 1.3,
                   "sanhedrin": 0.7},
    "husbandry":  {"charter": 1.2, "concordat": 1.0, "freeholds": 1.5,
                   "sanhedrin": 0.8},
    "yields":     {"charter": 0.8, "concordat": 1.7, "freeholds": 1.4,
                   "sanhedrin": 0.6},
    "statecraft": {"charter": 1.0, "concordat": 1.0, "freeholds": 1.2,
                   "sanhedrin": 1.6},
}

#: Standing per point of worth, filing a finding with one power.
FILE_RATE = 1.0

#: Publishing openly gives every power this share of what filing would have
#: given them — through the same interest table, so a paper the Choir wants is
#: worth more to the Choir either way.
#:
#: Below a quarter, publishing is dominated by filing under every arrangement
#: of the interest table and the option is decoration. Above it, publishing
#: beats filing summed across the sector and there is never a reason to file.
#: At 0.45 the choice is real: filing wins with the power you file with, and
#: publishing wins everywhere else.
PUBLISH_SHARE = 0.45

#: And filing is a visibly partisan act, so the filed-with power's rivals mind
#: — the rule `sim/allegiance.py` has applied to every other public act since
#: it was written.
FILE_RIVAL_COST = 0.30

#: What a finding fetches on the open market, in credits per point of worth.
#: Selling is the door that buys nothing political at all.
SELL_RATE = 460.0
