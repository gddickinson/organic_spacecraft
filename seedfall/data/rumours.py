"""Word going round — leads that point at a system before you have seen it.

A rumour is not a contract. Nobody is paying you and nobody is checking, and
some of what you hear at a bar in a fleet hub is wrong. What a rumour buys is a
reason to go *there* rather than to the next star along, and something specific
to look for when you arrive.

Each kind knows how to phrase itself, what it claims, and what counts as it
having been right.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RumourKind:
    id: str
    name: str
    tint: str
    #: {system} is filled with the system's name.
    claim: str
    #: What it feels like when it turns out to be true.
    confirmed: str
    #: What it feels like when it does not.
    denied: str
    #: How often this kind is simply wrong, 0..1.
    unreliable: float
    #: Credits it costs to be told, if anyone is selling.
    price: int


KINDS: list[RumourKind] = [
    RumourKind(
        "relic", "Buried relic", "xeno",
        "Somebody set down on {system} years ago and came back with something "
        "they would not show anybody. The site is supposed to still be there.",
        "There is a dig site here, exactly where the story put it.",
        "Nothing here but rock. Whoever told that story told it well.",
        unreliable=0.35, price=1800),

    RumourKind(
        "rich", "Rich seam", "osteo",
        "A prospector working {system} filed nothing and retired anyway. The "
        "assay office has been curious ever since.",
        "The bodies here assay well above the catalogue.",
        "The catalogue was right and the prospector was lucky elsewhere.",
        unreliable=0.30, price=1500),

    RumourKind(
        "bloom", "Unlicensed growth", "warn",
        "A hauler came back from {system} talking about the colour of the "
        "light and has not taken a run out that way since.",
        "There is growth here, and more of it than anyone has filed.",
        "Clean. Whatever they saw, it was not here.",
        unreliable=0.25, price=900),

    RumourKind(
        "wreck", "Lost hull", "steel",
        "A hull went quiet somewhere around {system} and the underwriters "
        "paid out rather than send anyone to look.",
        "There is a wreck here worth pulling apart.",
        "No wreck, no beacon, nothing. The underwriters were right to settle.",
        unreliable=0.40, price=2200),

    RumourKind(
        "quiet", "Nobody goes there", "dim",
        "Nobody will take a charter to {system} and nobody will say why. The "
        "charts for it are older than the registry that sells them.",
        "The charts were badly wrong. This system is not what was filed.",
        "It is a perfectly ordinary system that people are odd about.",
        unreliable=0.20, price=700),
]

KINDS_BY_ID = {k.id: k for k in KINDS}

#: How many rumours a port will have going round at once.
PER_PORT = 3


# ── provenance ─────────────────────────────────────────────────────────────
#
# **`Rumour.heard_at` was written and read by nobody.** Truth was
# `not rng.chance(kind.unreliable)` — a per-kind coin flip. A story about the
# far side of the sector, told at a lonely outpost by somebody who has never
# been within forty light-years of it, was exactly as good as one about the next
# star over told at a Fleet Hub where a dozen hulls a week put in.
#
# Word travels by ship, so the numbers below are about distance and traffic.

#: Within this many light-years of where you are told it, a story is somebody's
#: own business — they have been, or they know who has.
#:
#: **Both marks are taken off the sector's actual geography** rather than picked
#: for how they read. Measured over 4,264 port-to-system distances in five
#: sectors: median 27 ly, 80th percentile 40, longest 69. The first draft used 12
#: and 55, which put the near mark at the 12th percentile and the far one at the
#: 96th — so the far end of the scale was reached by 3% of stories and the whole
#: top of the range was decoration. 11 is the 10th percentile, which is what
#: "next door" should be; 42 is about the 85th, which is what "the far side of
#: the sector" should be.
LOCAL_LY = 11.0

#: Beyond this, it has come through too many hands to be worth much.
FAR_LY = 42.0

#: What a story's unreliability multiplies by at the far end of that.
FAR_UNRELIABLE = 2.3

#: What each level of the quay is worth against it. A Fleet Hub hears from
#: everybody; an outpost hears from whoever last docked.
QUAY_TRUST = 0.055

#: A rumour never gets better than this or worse than that, whatever the
#: geography says. Certainty is not on sale in a bar.
BEST_ODDS = 0.94
WORST_ODDS = 0.30

#: What a well-sourced story costs against a badly-sourced one. The price
#: follows the provenance, so paying more is paying for a better source rather
#: than for a louder one.
PRICE_FLOOR = 0.55
PRICE_RANGE = 0.90
