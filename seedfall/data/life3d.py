"""What a xenoform looks like, from the three things it is made of.

The Life tab was the last catalogue page in the game with no picture on it — a
list of everything a captain has ever catalogued, grouped by biochemistry, in
words. `works3d` and `robots3d` fixed the same complaint for holdings and
machines, and the same argument applies here with an extra edge: **an organism
in this game is already generative.** `world/planets.make_life` picks a body
plan from `FORMS`, a metabolism from `METABOLISMS` and up to two traits from
`TRAITS`, so there is no fixed bestiary to illustrate — there is a grammar, and
a picture has to be built the same way the creature was.

So it is, and from the record itself rather than from a second table:

- **The body plan is the silhouette.** `Lifeform.name` *is* the form — a
  "drifting bell" and a "plated crawler" are different animals and come out
  different shapes.
- **The metabolism is the colour.** A photoautotroph is green because it runs on
  the local star; a radiotroph is not.
- **A trait is a feature you can see.** Silaffin lattice grows its own glass, a
  calcifier lays down plates, a bioluminescent thing is lit.

Which means a world's biota is as varied on the page as it is in the fiction,
and an organism nobody has drawn still arrives with a body.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .lifeforms import FORMS, METABOLISMS, TRAITS
from .models3d import (CHLORO, GOLD, LUMEN, PLATE, PLATE_DARK, ROCK,
                       ROCK_DARK, WARN, _box, _build, _cap, _tube)

#: Two tints the structural palette has no word for, because a metabolism is
#: not a material. Brine is the pale crust a halophile leaves; abyss is what
#: something folded to hold at pressure looks like when you finally see it.
BRINE = "#cfd8dc"
ABYSS = "#3f5d78"

#: What a creature runs on, in colour. Every one is the biochemistry the card
#: already names, so the picture and the text cannot disagree.
LIVERY = {
    "photo": (CHLORO, "#2f7d4a"),      # runs on the local star
    "chemo": (ROCK, ROCK_DARK),        # oxidises reduced minerals
    "thermo": (WARN, "#7d3a30"),       # lives off vent heat
    "halo": (BRINE, PLATE_DARK),       # thrives in brine
    "radio": (GOLD, "#7d6430"),        # harvests ionising flux
    "crypto": (LUMEN, "#2b7d79"),      # vitrifies between rains
    "methano": ("#b9c46a", "#6b7333"), # exhales methane
    "piezo": (ABYSS, "#22364a"),       # folded to hold at abyssal pressure
}
DEFAULT_LIVERY = (PLATE, PLATE_DARK)

# ── the five ways of being alive that this package can draw ────────────────
#
# Sixteen body plans, five silhouettes, and the proportions per plan. Not one
# builder each: a mat and a reef are the same idea at different scales, and
# saying so in numbers is what keeps this file short enough to read.

#: plan -> (silhouette, spread, height, count)
PLAN = {
    "filamentous mat":    ("mat", 0.78, 0.10, 7),
    "encrusting reef":    ("mat", 0.68, 0.26, 9),
    "colonial raft":      ("mat", 0.86, 0.14, 5),
    "drifting bell":      ("bell", 0.46, 0.62, 6),
    "vesicular bloom":    ("bell", 0.54, 0.44, 9),
    "motile spore-cloud": ("bell", 0.62, 0.30, 12),
    "sail-borne float":   ("bell", 0.40, 0.78, 4),
    "burrowing tube":     ("tube", 0.20, 0.82, 3),
    "anchored siphon":    ("tube", 0.26, 0.66, 5),
    "crystalline frond":  ("frond", 0.44, 0.80, 5),
    "branching thallus":  ("frond", 0.58, 0.62, 7),
    "sessile calcifier":  ("frond", 0.34, 0.50, 4),
    "armoured grazer":    ("body", 0.50, 0.30, 5),
    "jointed swimmer":    ("body", 0.66, 0.22, 7),
    "plated crawler":     ("body", 0.44, 0.24, 6),
    "luminous shoal":     ("body", 0.72, 0.18, 9),
}
DEFAULT_PLAN = ("mat", 0.6, 0.2, 6)


def _mat(light, dark, spread, height, count) -> list:
    """A sheet that spreads. What most life on most worlds actually is."""
    out = []
    for i in range(count):
        turn = math.tau * i / count
        reach = spread * (0.45 + 0.55 * ((i * 0.37) % 1.0))
        out.append(_box(reach * 0.5, reach * 0.22, height * 0.5, light, dark,
                        dx=reach * 0.5 * math.cos(turn),
                        dy=reach * 0.5 * math.sin(turn), dz=0.0))
    out.append(_tube(spread * 0.22, -height * 0.5, spread * 0.30, height * 0.5,
                     10, 0, light, dark))
    return out


def _bell(light, dark, spread, height, count) -> list:
    """A dome that drifts, and whatever hangs off it."""
    rows = [(spread * 0.30, height * 0.5), (spread * 0.86, height * 0.1),
            (spread * 0.94, -height * 0.12)]
    out = [_tube(a[0], a[1], b[0], b[1], 14, 0, light, dark)
           for a, b in zip(rows, rows[1:])]
    out.append(_cap(spread * 0.30, height * 0.5, 14, 0, light, True))
    for i in range(count):
        turn = math.tau * i / count
        drop = height * (0.5 + 0.55 * ((i * 0.53) % 1.0))
        out.append(_box(0.018, 0.018, drop * 0.5, dark, dark,
                        dx=spread * 0.72 * math.cos(turn),
                        dy=spread * 0.72 * math.sin(turn),
                        dz=-height * 0.12 - drop * 0.5))
    return out


def _tube_form(light, dark, spread, height, count) -> list:
    """Anchored, and mostly below whatever it is anchored in."""
    out = [_tube(spread, -height * 0.5, spread * 0.62, height * 0.5, 10, 0,
                 light, dark),
           _cap(spread * 0.62, height * 0.5, 10, 0, light, True)]
    for i in range(count):
        turn = math.tau * i / count
        out.append(_box(spread * 0.62, 0.02, 0.02, light, dark,
                        dx=spread * 0.9 * math.cos(turn),
                        dy=spread * 0.9 * math.sin(turn), dz=height * 0.46))
    out.append(_tube(spread * 1.25, -height * 0.5, spread * 0.7,
                     -height * 0.34, 10, 0, dark, dark))
    return out


def _frond(light, dark, spread, height, count) -> list:
    """Upright blades on a holdfast. Rigid, and reaching for something."""
    out = [_tube(spread * 0.30, -height * 0.5, spread * 0.16, -height * 0.2,
                 8, 0, dark, dark)]
    for i in range(count):
        turn = math.tau * i / count + 0.4
        lean = spread * (0.35 + 0.4 * ((i * 0.43) % 1.0))
        tall = height * (0.55 + 0.45 * ((i * 0.61) % 1.0))
        out.append(_box(lean * 0.28, 0.022, tall * 0.5, light, dark,
                        dx=lean * math.cos(turn), dy=lean * math.sin(turn),
                        dz=-height * 0.2 + tall * 0.5))
    return out


def _body(light, dark, spread, height, count) -> list:
    """Something that moves: a segmented body, and the limbs to do it with."""
    out = []
    for i in range(count):
        along = -spread + 2 * spread * i / max(1, count - 1)
        fat = height * (1.0 - 0.55 * abs(along / max(1e-6, spread)) ** 2)
        out.append(_box(spread / count, fat, fat, light, dark, dx=along))
        if i % 2 == 0:
            for side in (-1.0, 1.0):
                out.append(_box(0.02, height * 0.7, 0.02, dark, dark,
                                dx=along, dy=side * height * 1.2))
    out.append(_box(height * 0.5, height * 0.55, height * 0.55, light, dark,
                    dx=spread * 1.05))
    return out


SHAPES = {"mat": _mat, "bell": _bell, "tube": _tube_form, "frond": _frond,
          "body": _body}


# ── what a trait looks like ────────────────────────────────────────────────

def _silica(light, dark, spread, height) -> list:
    """Silaffin lattice: it grows its own glass, so it has spines."""
    out = []
    for i in range(6):
        turn = 2.399 * i
        out.append(_box(0.014, 0.014, height * 0.42, LUMEN, PLATE,
                        dx=spread * 0.62 * math.cos(turn),
                        dy=spread * 0.62 * math.sin(turn),
                        dz=height * 0.5))
    return out


def _lumin(light, dark, spread, height) -> list:
    """Bioluminescent: lit nodes, in a band nobody expected."""
    # Held clear of the body. A long low animal's envelope swallowed these at
    # `spread * 0.78`, so a bioluminescent grazer lit up fifteen pixels.
    return [_box(0.055, 0.055, 0.055, LUMEN, CHLORO,
                 dx=spread * 1.05 * math.cos(math.tau * i / 4),
                 dy=spread * 1.05 * math.sin(math.tau * i / 4),
                 dz=height * 0.55)
            for i in range(4)]


def _calcify(light, dark, spread, height) -> list:
    """Calcifying: carbonate plates, laid down on command."""
    # Above the animal, for the same reason the lights are: a plate laid on a
    # body's own midline is a plate nobody sees.
    return [_box(spread * 0.36, spread * 0.32, 0.022, PLATE, PLATE_DARK,
                 dx=spread * 0.58 * math.cos(math.tau * i / 3 + 0.5),
                 dy=spread * 0.58 * math.sin(math.tau * i / 3 + 0.5),
                 dz=height * 0.72)
            for i in range(3)]


def _magneto(light, dark, spread, height) -> list:
    """Magnetotactic: aligned magnetite chains, all pointing one way.

    Drawn *past* the body. At half the spread and tucked inside it the chains
    changed **zero pixels** — measured, the whole trait was invisible — because
    a dome is wider than they were. The one thing this trait means is that
    everything in the animal lines up, and you can only see that if the line
    leaves the animal.
    """
    return [_box(spread * 1.30, 0.014, 0.014, ROCK_DARK, ROCK,
                 dy=(i - 1) * spread * 0.34, dz=height * 0.30)
            for i in range(3)]


def _silk(light, dark, spread, height) -> list:
    """Fibre-spinning: a tough cable, drawn out and anchored."""
    return [_box(spread * 0.9, 0.012, 0.012, PLATE, PLATE_DARK,
                 dx=spread * 0.6, dy=side * spread * 0.18, dz=-height * 0.3)
            for side in (-1.0, 1.0)]


#: The traits that change the picture. The rest — quorum-signalling, obligate
#: symbiosis, damage-suppressed chromatin — are real and invisible, which is
#: the honest answer: you cannot see a repaired chromosome from a lander.
MARKS = {"silica": _silica, "lumin": _lumin, "calcify": _calcify,
         "magneto": _magneto, "silk": _silk}


@dataclass(frozen=True)
class Shape:
    """One organism's body: its mesh, and what it was built from."""

    mesh: tuple
    plan: str
    #: Which of this organism's traits the picture actually shows. Not all of
    #: them can be: damage-suppressed chromatin and obligate symbiosis are real
    #: and invisible, which is the honest answer — you cannot see a repaired
    #: chromosome from a lander. The catalogue says which is which.
    marks: tuple


def plan_of(name: str) -> tuple:
    """The silhouette and proportions of a body plan."""
    return PLAN.get(name, DEFAULT_PLAN)


def build(form: str, metabolism: str, traits=()) -> Shape:
    """One organism, from its plan, its biochemistry and what it can do."""
    silhouette, spread, height, count = plan_of(form)
    light, dark = LIVERY.get(metabolism, DEFAULT_LIVERY)
    maker = SHAPES.get(silhouette, _mat)
    parts = list(maker(light, dark, spread, height, count))
    # A mark is sized to the *creature*, not to one of its axes. Measured: with
    # the marks scaled by `height`, every trait on a long low animal came out
    # between 3 and 16 pixels — an armoured grazer's glass spines were three
    # pixels of glass. A plan's largest dimension is what "as big as the animal"
    # means, whichever axis it happens to lie along.
    size = max(spread, height)
    marks = []
    for trait in traits:
        key = trait[0] if isinstance(trait, (list, tuple)) else trait
        mark = MARKS.get(key)
        if mark is not None:
            parts.extend(mark(light, dark, size, size))
            marks.append(key)
    return Shape(mesh=_build([(v, f) for v, f in parts]), plan=silhouette,
                 marks=tuple(marks))


def for_lifeform(life) -> Shape:
    """The body of one catalogued organism, off its own record.

    `Lifeform.name` **is** the body plan — `world/planets.make_life` passes
    `rng.pick(FORMS)` straight into it — so nothing has to be stored twice or
    parsed back out of prose.
    """
    return build(getattr(life, "name", ""), getattr(life, "metabolism", ""),
                 getattr(life, "traits", ()) or ())


#: Every plan drawn once, for the catalogue and for a check that walks them.
SHAPES_BY_PLAN: dict = {form: build(form, "photo") for form in FORMS}

#: Every biochemistry drawn once on the same plan, so the livery can be
#: compared without the silhouette getting in the way.
LIVERY_SAMPLES: dict = {met[0]: build("drifting bell", met[0])
                        for met in METABOLISMS}

#: Which trait ids the picture can actually show.
VISIBLE_TRAITS = tuple(t[0] for t in TRAITS if t[0] in MARKS)
