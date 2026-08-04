"""What a gate will pass, how often, and who is already in the queue.

**Transit was free of everything but money.** `sim/gates` says so in as many
words — instant, and what it spends is credits, standing and the Bloom — and
that was the right call when the Weave was scenery being made usable. It
leaves two things unsaid that a busy anchor makes you care about: a gate has
a **bore**, and it has a **cycle**. A hull too big does not fit. A hull
arriving at a gate that is already working a queue waits its turn.

Both matter far more once signals travel this way, because **nothing is
broadcast through a gate.** A ring does not carry radio; it moves mass from
one place to another. So a despatch crosses the Weave the only way anything
crosses it — aboard something — and a courier competes for the same slots as
every freighter in the system. A busy anchor is slow news as well as a slow
crossing, which is the honest consequence and a much better one than a flat
delay per hop.

**The three kinds are not the same machine.** An ancient ring is enormous and
nobody knows how to hurry it: anything fits, and it cycles when it cycles. A
Charter gate is engineered to a specification — a working bore and a brisk
cycle, because it was built to move trade. One you laid yourself is neither:
small, slow, and yours.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ring:
    """One kind of anchor, as a thing with a throat and a clock."""

    kind: str
    name: str
    #: The largest hull it will take, in tonnes. A hull over this does not
    #: pass — not for a fee, not with standing, not at all.
    bore_t: float
    #: Transits it can clear in a day when nothing is in the way.
    slots_per_day: float
    #: The share of those slots the harbour keeps for despatch traffic.
    #: Couriers are small and jump the queue, which is what a mail service
    #: *is*; without a reserve, news from a busy system would be the slowest
    #: news in the sector rather than the fastest.
    courier_share: float
    blurb: str


#: Older than the Charter and bigger than anything that uses it. Nobody has
#: ever made one cycle faster.
ANCIENT = Ring(
    "ancient", "ancient ring", 240_000.0, 6.0, 0.25,
    "Wide enough for anything anyone has ever built, and it takes its time.")

#: Built to move trade, to a specification, by people who wanted throughput.
CHARTER = Ring(
    "charter", "Charter gate", 42_000.0, 22.0, 0.35,
    "Engineered for tonnage per day. It will not take the largest hulls and "
    "it does not keep the ones it takes waiting.")

#: Yours. It works.
YOURS = Ring(
    "yours", "laid anchor", 9_000.0, 4.0, 0.30,
    "A throat you paid for, sized to what you could afford.")

BY_KIND = {"ancient": ANCIENT, "charter": CHARTER, "yours": YOURS}


def of(kind: str) -> Ring:
    return BY_KIND.get(kind or "", ANCIENT)


#: How much traffic a system generates against its port level, in transits a
#: day. A portless system offers a hull or two a week; somewhere a fleet lives
#: is working the ring most of the day.
#: Measured against the rings rather than guessed: the first numbers put a
#: level-3 port at 16.8 transits a day against an ancient ring's six, so
#: *every* crossing hit the cap and the queue stopped being information. A
#: middling harbour should work a ring hard without a wait worth mentioning;
#: a fleet base on an ancient ring should cost you an afternoon.
DEMAND_PER_LEVEL = 1.6
DEMAND_BASE = 0.4

#: What each hull standing in the system adds. `sim/traffic` already decides
#: how many there are and why, so the queue is read off the sector rather
#: than invented for the gate.
DEMAND_PER_HULL = 0.35

#: What share of the transits a busy ring is asked for are despatches.
#:
#: This is the other half of `courier_share` and the first draft was missing
#: it, which made a despatch wait *longer* than a freighter — 3.35 days
#: against 3.00, with the reserve doing nothing but adding handling. A
#: reserve only helps if the traffic it is reserved for is a *smaller* share
#: of the demand than of the slots: a Charter gate sets aside a third of its
#: cycle for a tenth of its traffic, and that ratio is the whole service.
COURIER_DEMAND_SHARE = 0.10

#: How long a courier waits for its own slot on top of the queue, in days.
#: A despatch boat is small and expected; it is not instant.
COURIER_HANDLING_DAYS = 0.35

#: The most a queue will ever be quoted as, in days. A gate does not actually
#: stop working, and a wait that ran to weeks would be a wall rather than a
#: cost — the interesting range is "an afternoon" to "come back tomorrow".
MAX_WAIT_DAYS = 3.0
