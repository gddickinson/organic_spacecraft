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
