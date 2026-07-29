"""The Weave: what the gates are, who built them, and what they cost.

A hull's jump range is ten light years. The sector is sixty-eight across, and
the median pair of stars is twenty-nine apart — so a fresh captain can reach
**three systems out of forty-one**, and everything else is a matter of
crawling outward one crossing at a time. That is the shape of the game and it
is a fine shape for the early hours, but it makes half the Verge scenery.

The Weave is the answer, and it is older than anyone flying it.

**Ancient gates.** Nobody built them who is still around to say so. They stand
in a handful of systems, they are paired to each other in a ring with a few
chords across it, and the ones the powers found first are the reason those
systems have ports at all. Most are dark. Waking one takes a great deal of
knowing what you are looking at.

**Modern gates.** The Charter has worked out enough of the principle to lay
new anchors, at ruinous cost, and only ever onto a ring that is already lit.
They are shorter-ranged and fussier and they are the only kind you can build
yourself.

**What a gate costs.** Transit is instant — that is the whole point, and it is
the only thing in the game that does not spend the calendar. What it spends
instead is a toll to whoever holds the far end, which is why the Weave is a
political object and not merely a convenience.

**What it costs the sector.** The Bloom travels the Weave. A lit link is a
road for anything that wants to use it, and growth crosses one in a season
regardless of the light years involved. Every gate you wake is a gate it can
walk through — which is the decision the whole system exists to pose.
"""

from __future__ import annotations

#: How many ancient gate sites a sector holds. Enough that the network
#: genuinely spans it, few enough that each one is a landmark.
ANCIENT_SITES = 9

#: How many of them are already lit when the chronicle opens. The powers
#: found these long ago and built their capitals around them.
ANCIENT_LIT = 3

#: Chords across the ring, beyond the ring itself. Without them the Weave is
#: a circle and every route is forced; with them there are choices, and
#: chokepoints worth holding.
ANCIENT_CHORDS = 3

#: A gate's toll, in credits: a flat fee plus a rate on the light years
#: saved. Crossing the sector on the Weave is expensive and instant, which is
#: exactly the trade a courier wants and a bulk hauler does not.
TOLL_BASE = 900.0
TOLL_PER_LY = 140.0

#: How much standing with the holder moves the toll. At Kin it is halved; at
#: the bottom it is nearly doubled, if they let you through at all.
TOLL_STANDING_SWING = 0.5

#: Below this standing with the power holding the far end, they will not open
#: for you at all.
TOLL_REFUSED_BELOW = -40.0

#: Waking an ancient gate: what it takes and what it gives.
WAKE_TECH = "weavecraft"
WAKE_CREDITS = 240_000.0
WAKE_GOODS = {"xenolith": 12, "alloy": 90, "silicon": 40}
WAKE_DAYS = 45

#: Laying a new anchor of your own. Dearer than waking one that is already
#: standing, because you are building the thing rather than remembering how
#: it works.
BUILD_TECH = "weavecraft"
BUILD_CREDITS = 520_000.0
BUILD_GOODS = {"alloy": 260, "silicon": 140, "magnetite": 60}
BUILD_DAYS = 120

#: How far a new anchor can reach to find a lit ring to hang off.
BUILD_REACH_LY = 34.0

#: What a lit link does for the Bloom, per growth tick, as a share of the
#: source system's infestation handed to the far end — before `threat.tick`
#: scales it by the Bloom's stage and how far it has been provoked, like
#: everything else it does.
#:
#: Small on purpose, and smaller than the first draft. A single link is not a
#: catastrophe; a fully-woken Weave with a bad neighbour on it is.
#:
#: It applies only to rings the *captain* lit — see `gates.bloom_links`. The
#: anchors burning at dawn are part of the sector as it already is, and
#: charging the world for them every tick perturbed a Bloom balance a dozen
#: long-running checks are calibrated against. What changes the Verge is what
#: you wake.
BLOOM_CARRY = 0.06

#: A link only carries growth once the source is properly infested. Below
#: this the spores do not survive the crossing.
BLOOM_CARRY_FLOOR = 0.25

#: What each kind of gate is, for the panels.
GATE_KINDS = {
    "ancient": (
        "Ancient anchor",
        "Older than the Charter, older than the Reach. It does not appear to "
        "be made of anything. Whatever it is waiting for, it is not us."),
    "charter": (
        "Charter anchor",
        "Rolled plate and licensed physics, hung off a ring somebody else "
        "made. It works. It is not the same thing at all."),
    "yours": (
        "Your anchor",
        "Laid at your own expense, onto a ring you did not make and do not "
        "understand. The invoice is the part you understand."),
}

#: Names for the ancient sites, in the order they are found.
ANCIENT_NAMES = [
    "the Verge Anchor", "the Pale Ring", "Second Silence", "the Long Chord",
    "the Drowned Anchor", "Kessel's Ring", "the Unasked", "Third Silence",
    "the Far Chord", "the Quiet Anchor", "the Turned Ring",
]
