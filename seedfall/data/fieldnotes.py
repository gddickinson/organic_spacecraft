"""What a landing party brings back that is not cargo.

These were a bare list of strings in `data/expedition.py`, described in their
own comment as "the reason anyone reads an expedition report twice" — and you
could not read the report twice. A recovered note was printed once in the
report dialog and thrown away with the expedition object: never stored on the
`Game`, never in the codex, and worth nothing, since `REWARD_SCALE["lore"]` is
(0, 0). Three feature options across two features existed only to show you a
sentence and then lose it.

They have identity now, so they can be kept and looked up again, and each one
is evidence of something, so bringing one home counts.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    text: str
    #: Which inquiry track this is evidence for.
    evidence: str
    #: Points of it, for a party that reads the room properly.
    worth: float


NOTES: list[Note] = [
    Note("manifest", "A manifest that does not add up",
         "The recorder's last entry is a cargo manifest. The cargo was seed "
         "husks, and the count does not match what the Charter says it issued "
         "that year.",
         "hardware", 22),

    Note("tally", "Four hundred and eleven",
         "Someone scratched a tally into the bulkhead — four hundred and "
         "eleven marks — and then stopped, neatly, mid-stroke.",
         "hardware", 18),

    Note("furrows", "The line nothing crosses",
         "The rows run north-south for eleven kilometres and then stop at a "
         "line as straight as a ruler. Nothing grows past it. Nothing has "
         "tried.",
         "specimen", 26),

    Note("emission", "Something with the structure of speech",
         "The array's emission resolves, when slowed by a factor of nine "
         "hundred, into something with the statistical structure of speech.",
         "reading", 30),

    Note("tiles", "A path worn to a window",
         "Under the dust the floor is tiled, and the tiles are worn deepest "
         "along a path from the doorway to a window that faces nothing in "
         "particular.",
         "reading", 24),

    Note("breach", "From the inside",
         "The hull is Concordat, forty years old, and the breach is from the "
         "inside.",
         "hardware", 28),

    Note("doorway", "The second doorway",
         "There is a second doorway behind the first, sized for something much "
         "larger, and it has been bricked up from this side.",
         "reading", 26),

    Note("vent", "A library that should not match",
         "The vent chemistry is a nine-to-one match for the Abyssal sample "
         "library. This world has no ocean and has never had one.",
         "specimen", 32),
]

NOTES_BY_ID = {n.id: n for n in NOTES}
