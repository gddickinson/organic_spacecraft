"""What is in a dig, layer by layer.

Excavating was one call: spend twelve days, receive a number of points, and
occasionally read that the face collapsed. Everything the setting says about
Abyssal work — that it is layered, that it is fragile, that the interesting
part is always underneath the part that is easy to reach — was in the codex and
nowhere in the game.

A site now has four strata. Each one holds something different, each is more
fragile than the one above it, and how you work a layer is a real choice: the
careful method takes a fortnight and gets everything, the quick one takes four
days and may take the find apart on the way out.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Stratum:
    id: str
    name: str
    tint: str
    text: str
    #: Share of the site's total understanding held at this depth.
    share: float
    #: How easily the find here is spoiled, 0..1.
    fragility: float
    #: Xenolith recovered when the layer comes out intact.
    relics: float = 0.0


STRATA: list[Stratum] = [
    Stratum("spoil", "Spoil and overburden", "dim",
            "Regolith, ejecta and whatever has fallen in since. Nothing here "
            "was ever made; it is only in the way.",
            share=0.08, fragility=0.02),

    Stratum("casing", "The casing", "steel",
            "A shell of something that was poured rather than built, still "
            "holding its shape after a length of time nobody will commit to "
            "in writing.",
            share=0.22, fragility=0.18, relics=1.0),

    Stratum("works", "The works", "xeno",
            "Under the casing it stops looking like geology. Channels, "
            "junctions, and a great deal of surface area for something that "
            "was supposed to sit still.",
            share=0.34, fragility=0.42, relics=1.6),

    Stratum("core", "Whatever it was for", "chloro",
            "The thing the rest of it was built around. It is intact, which "
            "after this long is the part nobody can explain.",
            share=0.36, fragility=0.66, relics=2.4),
]

STRATA_BY_ID = {s.id: s for s in STRATA}


@dataclass(frozen=True)
class Method:
    id: str
    name: str
    blurb: str
    days: int
    #: Multiplies what the layer yields.
    yield_mul: float
    #: Multiplies the layer's fragility when deciding whether it spoils.
    care: float
    #: Chance of the face coming in on the party.
    collapse: float = 0.0


METHODS: list[Method] = [
    Method("careful", "Work it properly",
           "Brushes, shoring and a grid. A fortnight a layer and nothing lost "
           "that did not want to be lost.",
           days=14, yield_mul=1.0, care=0.35),

    Method("brisk", "Work it briskly",
           "Proper method, fewer photographs. A week, and the odd thing comes "
           "up in more pieces than it went down in.",
           days=7, yield_mul=0.92, care=1.0, collapse=0.05),

    Method("cut", "Cut straight down",
           "Charges and a grab. Four days to the next layer and no promises "
           "about what is in this one when you get there.",
           days=4, yield_mul=0.7, care=2.4, collapse=0.16),
]

METHODS_BY_ID = {m.id: m for m in METHODS}

#: Named finds, drawn when a layer comes up intact. Flavour with a number on it.
FINDS: dict[str, tuple[tuple[str, str], ...]] = {
    "casing": (
        ("A seam of poured shell",
         "It was poured in one piece around something. There is no joint "
         "anywhere on it and no sign of a mould."),
        ("A hatch that is not a hatch",
         "It opens. It has never been hinged, and closing it again is not "
         "something anybody has managed."),
    ),
    "works": (
        ("A junction of forty-one channels",
         "Forty-one is not a number anything with two hands would choose, and "
         "every channel is the same length to within a micron."),
        ("A length of standing wave",
         "The instruments insist there is a wave in it. There is nothing in "
         "it. The instruments go on insisting."),
        ("Something that is still warm",
         "Ambient here is eleven kelvin. This is at three hundred and has been "
         "for a period the isotopes put at forty thousand years."),
    ),
    "core": (
        ("The reading itself",
         "Whatever the structure was built to hold, it is still holding it, "
         "and it has begun holding it slightly differently since you arrived."),
        ("A lattice with a grain",
         "It is a crystal and it is not. Cut it any way you like and the grain "
         "runs toward the same point, which is not inside the sample."),
    ),
}

#: What happens when a layer is spoiled.
SPOILS: tuple[tuple[str, str], ...] = (
    ("The face comes away wrong",
     "It parts along a plane nobody expected and takes most of what was in it."),
    ("Contamination",
     "Something in the lander's exhaust has got into the trench. Whatever the "
     "layer was going to tell you, it is now telling you about the lander."),
    ("It does not survive the lift",
     "It came out of the ground intact and did not survive being moved, which "
     "is a distinction the crew are finding hard to take comfort in."),
)
