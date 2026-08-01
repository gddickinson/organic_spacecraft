"""What a xenotech relic looks like, from the culture that made it.

The last catalogue in the game that was words only, and the one with the best
excuse for a picture: twelve artefacts left by four cultures that are not human
and are mostly not alive. The codex had ten tabs and none of them was this one,
so a captain could carry a Pressure Song for a whole chronicle and never see it.

The claim a picture makes here is narrower than a hull's and wider than a
fitting's, and it is worth saying plainly so the shapes are not asked to do
more than they can:

- **Which culture left it** — the silhouette *and* the colour. This is the
  strong claim, and the one the checks pin: four makers, four ways of building,
  and the four are meant to be told apart across a room.
- **How much there is to learn** — `study` runs 120 to 340 across the twelve,
  three per culture, and that is the bulk.
- **Whether it does anything to a ship** — eight of the twelve carry a `bonus`
  and get a mark; the other four grant a technology instead and read as inert,
  which is true of them.

Not "which of the three Abyssal relics is this". Three artefacts of one dead
culture cannot be three pictures without inventing distinctions the cards do
not make — the same honesty `parts3d` settled on for eighteen armour plates.

The four languages come straight off the culture blurbs, which already describe
physical things:

- **abyssal** — still living, twenty kilometres down, at a hundred and fifty
  atmospheres. Pressure vessels: lobed, swollen, nothing flat, nothing sharp.
- **ossuary** — a lineage that ended and spent its last centuries writing
  itself down. Bone: struts, sockets, a thing built of the parts left over.
- **weft** — worked matter at nanometre pitch. Woven: interlaced bands with
  gaps you can see through, and no solid middle at all.
- **tessellate** — crystalline, geometric, fond of standing waves. Facets:
  flat plates at repeating angles, stacked into a standing form.
"""

from __future__ import annotations

import math

from .models3d import (GOLD, LUMEN, PLATE, PLATE_DARK, ROCK, ROCK_DARK, WARN,
                       _box, _build, _cap, _tube)
from .xenotech import CULTURES, XENOTECH

#: Whose hands, in colour. The ids are the culture tints the codex already
#: uses — `lumen`, `osteo`, `xeno`, `steel` — resolved to the palette here so
#: a relic's card and its portrait cannot drift apart.
HANDS = {
    "abyssal": (LUMEN, "#2b7d79"),
    "ossuary": (PLATE, PLATE_DARK),
    "weft": (WARN, "#7d3a30"),
    "tessellate": ("#9fb6c9", "#4d5f70"),
}
DEFAULT_HANDS = (ROCK, ROCK_DARK)

#: The study cost a relic is authored at — the median of the twelve.
TYPICAL_STUDY = 195.0

#: What a relic's depth of study does to its build, as a share either way.
#: The shallowest is 120 and the deepest 340; drawn at one size they would be
#: twelve objects of identical bulk in four colours.
BULK_SPREAD = 0.42


def bulk_of(relic) -> float:
    """How big this reads, from how much there is in it to learn."""
    study = max(1.0, float(getattr(relic, "study", TYPICAL_STUDY)))
    off = (study / TYPICAL_STUDY) ** (1.0 / 3.0) - 1.0
    return 1.0 + max(-BULK_SPREAD, min(BULK_SPREAD, off))


# ── one language per culture ───────────────────────────────────────────────

def _abyssal(light, dark, bulk) -> list:
    """Pressure vessels. Lobed, swollen, and nothing on it is flat."""
    out = []
    for index, (radius, at) in enumerate(
            ((0.30, -0.30), (0.40, -0.06), (0.34, 0.20), (0.20, 0.40))):
        out.append(_tube(radius * bulk, at * bulk,
                         radius * bulk * 0.86, (at + 0.16) * bulk,
                         14, 0, light if index % 2 else dark, dark))
    out.append(_cap(0.20 * bulk, 0.56 * bulk, 14, 0, light, True))
    out.append(_cap(0.30 * bulk, -0.30 * bulk, 14, 0, dark, False))
    # The lobes: a pressure hull grows outward wherever it can.
    for index in range(5):
        turn = math.tau * index / 5
        out.append(_tube(0.13 * bulk, 0.0, 0.05 * bulk, 0.17 * bulk, 9, 0,
                         light, dark))
        out[-1] = tuple(out[-1])
        out[-1] = _shifted(out[-1], 0.44 * bulk * math.cos(turn),
                           0.44 * bulk * math.sin(turn), -0.04 * bulk)
    return out


def _ossuary(light, dark, bulk) -> list:
    """Bone. Struts and sockets, built of what a body leaves behind."""
    out = [_tube(0.09 * bulk, -0.46 * bulk, 0.07 * bulk, 0.46 * bulk, 7, 0,
                 light, dark),
           _cap(0.09 * bulk, -0.46 * bulk, 7, 0, dark, False)]
    # Sockets at each end: the swellings a joint needs.
    for end in (-0.46, 0.46):
        out.append(_tube(0.11 * bulk, end * bulk,
                         0.17 * bulk, (end + (0.10 if end < 0 else -0.10)) * bulk,
                         9, 0, light, dark))
    # Ribs off the shaft, paired and swept, the way ribs are.
    for index in range(4):
        along = -0.30 + index * 0.20
        for side in (-1.0, 1.0):
            out.append(_shifted(
                _box(0.02, 0.26 * bulk, 0.02, light, dark),
                side * 0.24 * bulk, 0.0, along * bulk))
            out.append(_shifted(
                _box(0.22 * bulk, 0.02, 0.02, dark, dark),
                side * 0.13 * bulk, 0.24 * bulk, along * bulk))
    return out


def _weft(light, dark, bulk) -> list:
    """Woven. Interlaced bands with daylight through them, no solid middle."""
    out = []
    bands = 7
    for index in range(bands):
        turn = math.pi * index / bands
        # Each band is a thin plate on its edge, rotated about the long axis.
        out.append(_shifted(
            _box(0.46 * bulk, 0.018, 0.10 * bulk,
                 light if index % 2 else dark, dark),
            0.0, 0.0, 0.0, spin=turn))
    # And the two hoops that hold the weave to its shape.
    for at in (-0.26, 0.26):
        out.append(_tube(0.44 * bulk, at * bulk, 0.44 * bulk,
                         (at + 0.03) * bulk, 18, 0, light, dark))
    return out


def _tessellate(light, dark, bulk) -> list:
    """Facets. Flat plates at repeating angles, stacked into a standing form."""
    out = []
    tiers = 4
    for index in range(tiers):
        at = (index - (tiers - 1) / 2.0) * 0.24
        radius = (0.42 - abs(index - 1.2) * 0.09) * bulk
        # A prism per tier, each turned against the one below it — the
        # repetition is the whole point, so the offset must be visible.
        out.append(_tube(radius, at * bulk, radius, (at + 0.20) * bulk,
                         6, index % 2, light if index % 2 else dark, dark))
        out.append(_cap(radius, (at + 0.20) * bulk, 6, index % 2, dark, True))
    out.append(_cap(0.42 * bulk, -0.36 * bulk, 6, 0, dark, False))
    return out


def _shifted(part, dx=0.0, dy=0.0, dz=0.0, spin=0.0) -> tuple:
    """One mesh part moved, and optionally turned about the long axis."""
    verts, faces = part
    moved = []
    for x, y, z in verts:
        if spin:
            x, y = (x * math.cos(spin) - y * math.sin(spin),
                    x * math.sin(spin) + y * math.cos(spin))
        moved.append((x + dx, y + dy, z + dz))
    return (tuple(moved), faces)


LANGUAGES = {"abyssal": _abyssal, "ossuary": _ossuary,
             "weft": _weft, "tessellate": _tessellate}
DEFAULT_LANGUAGE = "tessellate"


# ── what it does, on top of who made it ────────────────────────────────────

#: How far out the "it does something" mark sits, as a share of the build.
#:
#: **Outside every language's widest point**, and the first draft was not: a
#: lit core at 0.10 sat inside a tessellate prism stack of radius 0.42 and a
#: relic drew *pixel for pixel identical* with and without its bonus. The
#: widest thing any of the four puts out is about 0.46 — abyssal's lobes and
#: weft's hoops — so the mark clears all of them and is visible on all four.
#: A difference that is drawn and cannot be seen is not a difference.
MARK_AT = 0.58

#: How many lit nodes the mark is made of. Three, so the ring reads as
#: deliberate from any angle without closing into a solid band.
MARK_NODES = 3


def _live(light, dark, bulk) -> list:
    """It does something to a ship: lit nodes standing off the form."""
    out = []
    for index in range(MARK_NODES):
        turn = math.tau * index / MARK_NODES + 0.4
        out.append(_shifted(
            _tube(0.09 * bulk, -0.07 * bulk, 0.05 * bulk, 0.07 * bulk, 8, 0,
                  GOLD, "#7d6430"),
            MARK_AT * bulk * math.cos(turn),
            MARK_AT * bulk * math.sin(turn), 0.0))
        out.append(_shifted(
            _cap(0.09 * bulk, -0.07 * bulk, 8, 0, GOLD, False),
            MARK_AT * bulk * math.cos(turn),
            MARK_AT * bulk * math.sin(turn), 0.0))
    return out


def marks_of(relic) -> tuple:
    """What this relic's picture says about it beyond who made it."""
    return ("live",) if getattr(relic, "bonus", None) else ()


def build(relic) -> tuple:
    """One relic's mesh, from its culture, its depth of study and its bonus."""
    culture = getattr(relic, "culture", "") or DEFAULT_LANGUAGE
    light, dark = HANDS.get(culture, DEFAULT_HANDS)
    bulk = bulk_of(relic)
    maker = LANGUAGES.get(culture, LANGUAGES[DEFAULT_LANGUAGE])
    pieces = list(maker(light, dark, bulk))
    if "live" in marks_of(relic):
        pieces.extend(_live(light, dark, bulk))
    return _build([(v, f) for v, f in pieces])


def mesh_for(look):
    """The mesh for a relic or its id, or None if it is not one.

    **Handed a relic, it draws that relic.** The first version looked the
    object up by id and returned the cached mesh, so a relic whose fields had
    been changed still drew the canonical one — which meant a check comparing
    a relic with and without its bonus compared one picture with itself and
    passed on a mark that was never drawn. The cache is a fast path for ids,
    not a substitute for what you were given.
    """
    if hasattr(look, "culture"):
        return build(look)
    got = RELICS_BY_ID.get(look)
    return None if got is None else MESHES.get(got.id)


def is_relic(look) -> bool:
    """Is this id one of the twelve?"""
    return getattr(look, "id", look) in RELICS_BY_ID


#: Every relic, keyed by id, and every mesh built once at import.
RELICS_BY_ID: dict = {r.id: r for r in XENOTECH}
MESHES: dict = {r.id: build(r) for r in XENOTECH}

#: One of each culture at a standard build, for comparing the four languages
#: without a depth of study or a bonus mark getting in the way.
BY_CULTURE: dict = {
    c.id: _build([(v, f) for v, f in
                  LANGUAGES.get(c.id, LANGUAGES[DEFAULT_LANGUAGE])(
                      *HANDS.get(c.id, DEFAULT_HANDS), 1.0)])
    for c in CULTURES}
