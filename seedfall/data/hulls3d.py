"""A ship's silhouette, from the family it was built in.

`data/hullforms.py` opens by saying "Five families, five silhouettes. A grown
hull is a prolate organism with an equatorial docking ridge and a radiator bloom
aft; a Yards hull is a welded spine with a slab bow; a hybrid is a grown body in
a fabricated cradle; a Dry Choir frame is a crewless lattice around an
instrument core; a xeno hull is not symmetrical and does not explain itself."

`sim/plans.py` builds the captain's *own* ship from those numbers, for the
cutaway on the plans panel. Nothing else did. `ui/battle3d.py` drew both
combatants with one mesh:

    pairs = [(b.enemy, models3d.HULL, "warn"),
             (b.player, models3d.HULL, "lumen")]

— the same shape at the same `HULL_SIZE`, so a SPORE and a LEVIATHAN were the
same object, and so were you and whatever was shooting at you. Thirty-five
chassis in five families, and the tactical plot showed one ship.

This is the silhouette layer: light meshes built from each `HullForm`'s own
length, beam, taper and **facet count** — a grown hull is smooth because it was
gestated, a Yards hull coarse because it was welded out of plate, and that
difference is already written down. Detail belongs to `sim/plans.py`; what
matters at plot scale is the outline and the furniture that breaks it.
"""

from __future__ import annotations

import math

from .hullforms import FORMS, LIVING, ROCK, STRUCT, SYSTEM, VOID, WARM
from .models3d import _box, _build, _cap, _ring, _shift, _tube

#: The skins, in the same colours the plans panel paints them, so a hull on
#: the tactical plot and the same hull in its own cutaway are the same ship.
SKIN = {
    LIVING: ("#54cf7c", "#2f7d4a"),
    SYSTEM: ("#4fd6d0", "#2b7d79"),
    STRUCT: ("#e6ac6d", "#8a6440"),
    WARM: ("#d68c60", "#7d4f34"),
    ROCK: ("#8a8072", "#4d4740"),
    VOID: ("#2b3a36", "#1a2422"),
}

#: What a radiator bloom and a drive glow are, whatever the skin.
GLOW = "#ffb46b"
DEEP = "#6b3a22"


def _skin(key: str) -> tuple:
    return SKIN.get(key, SKIN[STRUCT])


#: How far a family's spine wanders off true, as a share of its beam.
#:
#: Only the xeno hull does. `hullforms` says it "is not asymmetrical and does
#: not explain itself" — and it was built as a body of revolution like the other
#: four, so in profile on the tactical plot it shared **83%** of its outline
#: with a grown hull. Shards hung on a symmetric spindle are still a symmetric
#: spindle. A spine that bends is the cheapest thing that is genuinely not
#: symmetrical, and it changes the silhouette rather than the trim.
BEND = {"xeno": 0.55}

#: How far a hybrid's cradle stands off the body it holds, in beams.
#:
#: A hybrid *is* a grown body in a fabricated cradle, so the two families share
#: a hull by design — and at 1.14 beams the cradle sat close enough to the skin
#: that the pair shared **79%** of its outline on the plot, which is a design
#: intention rendered as an indistinguishable picture. Standing it further off
#: is what makes the cradle the silhouette rather than a stripe on one.
CRADLE_OUT = 1.62


def _body(form) -> list:
    """The hull proper: a body of revolution, at the family's own coarseness.

    `taper` is the drawings' beam law — positive narrows the bow, negative
    flares it into the slab a Yards hull carries. `BEND` takes one family off
    the axis of revolution entirely.
    """
    rings, segments = form.facets
    segments = max(5, min(segments, 14))
    light, dark = _skin(form.skin)
    bend = BEND.get(form.id, 0.0)
    parts = []
    steps = max(3, rings // 2)

    def offset(z: float) -> tuple:
        if not bend:
            return (0.0, 0.0)
        along = max(-1.0, min(1.0, z / max(1e-6, form.length)))
        return (form.beam * bend * (along ** 2 - 0.35),
                form.beam * bend * 0.35 * along)

    for i in range(steps):
        z_a = form.length * (1.0 - 2.0 * i / steps)
        z_b = form.length * (1.0 - 2.0 * (i + 1) / steps)
        piece = _tube(_beam(form, z_a), z_a, _beam(form, z_b), z_b,
                      segments, 0, light, dark)
        if bend:
            # The two rings a tube is built from, shifted apart: a straight
            # segment between two offset stations, which is what a bent hull
            # is made of.
            verts, faces = piece
            half = len(verts) // 2
            ax, ay = offset(z_a)
            bx, by = offset(z_b)
            verts = ([(x + ax, y + ay, z) for x, y, z in verts[:half]]
                     + [(x + bx, y + by, z) for x, y, z in verts[half:]])
            piece = (verts, faces)
        parts.append(piece)
    nose = _cap(_beam(form, form.length * 0.999), form.length * 0.999,
                segments, 0, light, True)
    tail = _cap(_beam(form, -form.length * 0.999), -form.length * 0.999,
                segments, 0, dark, False)
    if bend:
        nx, ny = offset(form.length)
        tx, ty = offset(-form.length)
        nose = ([(x + nx, y + ny, z) for x, y, z in nose[0]], nose[1])
        tail = ([(x + tx, y + ty, z) for x, y, z in tail[0]], tail[1])
    parts.append(nose)
    parts.append(tail)
    return parts


def _beam(form, z: float) -> float:
    """How wide the hull is at this height, never quite zero."""
    along = max(-1.0, min(1.0, z / max(1e-6, form.length)))
    # Fore narrows by `taper`, aft is full. A negative taper flares the bow.
    shape = 1.0 - form.taper * max(0.0, along) ** 1.4
    return max(0.03, form.beam * shape * math.sqrt(max(0.04, 1.0 - along ** 6)))


# ── furniture, by the names `hullforms` gives it ───────────────────────────

def _ridge(form, count: int) -> list:
    """An equatorial docking ridge: what a grown hull berths against."""
    light, dark = _skin(form.skin)
    out = []
    for i in range(max(3, count)):
        angle = math.tau * i / max(3, count)
        out.append(_box(form.beam * 0.30, form.beam * 0.07, form.beam * 0.10,
                        light, dark,
                        dx=form.beam * 1.02 * math.cos(angle),
                        dy=form.beam * 1.02 * math.sin(angle), dz=0.0))
    return out


def _bloom(form, count: int) -> list:
    """A radiator bloom aft — the one part of a hull that is meant to glow."""
    out = []
    for i in range(max(3, count)):
        angle = math.tau * i / max(3, count) + 0.4
        out.append(_box(form.beam * 0.72, form.beam * 0.04, form.beam * 0.16,
                        GLOW, DEEP,
                        dx=form.beam * 0.95 * math.cos(angle),
                        dy=form.beam * 0.95 * math.sin(angle),
                        dz=-form.length * 0.72))
    return out


def _spine(form, _count: int) -> list:
    """A welded spine running the length of it."""
    light, dark = _skin(form.skin)
    return [_box(form.beam * 0.12, form.beam * 0.12, form.length * 1.12,
                 light, dark)]


def _slab(form, _count: int) -> list:
    """The slab bow of a Yards hull: flat, and unmistakable in outline."""
    light, dark = _skin(form.skin)
    return [_box(form.beam * 0.94, form.beam * 0.22, form.beam * 0.24,
                 light, dark, dz=form.length * 0.86)]


def _fins(form, count: int) -> list:
    light, dark = _skin(form.skin)
    out = []
    for i in range(max(2, count)):
        angle = math.tau * i / max(2, count)
        out.append(_box(form.beam * 0.90, form.beam * 0.05, form.beam * 0.30,
                        dark, light,
                        dx=form.beam * 0.80 * math.cos(angle),
                        dy=form.beam * 0.80 * math.sin(angle),
                        dz=-form.length * 0.40))
    return out


def _cradle(form, count: int) -> list:
    """A fabricated cradle round a grown body — the hybrid's whole idea."""
    light, dark = _skin(STRUCT)
    out = []
    for i in range(max(2, count)):
        angle = math.tau * i / max(2, count)
        out.append(_box(form.beam * 0.13, form.beam * 0.13, form.length * 0.94,
                        light, dark,
                        dx=form.beam * CRADLE_OUT * math.cos(angle),
                        dy=form.beam * CRADLE_OUT * math.sin(angle)))
    for z in (form.length * 0.62, 0.0, -form.length * 0.62):
        out.append(_tube(form.beam * (CRADLE_OUT + 0.10), z - form.beam * 0.07,
                         form.beam * (CRADLE_OUT + 0.10), z + form.beam * 0.07,
                         10, 0, light, dark))
    return out


def _lattice(form, count: int) -> list:
    """A crewless frame: struts and nothing to pressurise."""
    light, dark = _skin(SYSTEM)
    out = []
    for i in range(max(3, count)):
        angle = math.tau * i / max(3, count)
        out.append(_box(form.beam * 0.06, form.beam * 0.06, form.length * 1.0,
                        light, dark,
                        dx=form.beam * 1.30 * math.cos(angle),
                        dy=form.beam * 1.30 * math.sin(angle)))
    return out


def _core(form, _count: int) -> list:
    """The instrument at the middle of a Dry Choir frame."""
    light, dark = _skin(SYSTEM)
    return [_tube(form.beam * 0.52, -form.length * 0.20,
                  form.beam * 0.52, form.length * 0.20, 8, 0, light, dark)]


def _shards(form, count: int) -> list:
    """A xeno hull does not explain itself, and is not symmetrical."""
    light, dark = _skin(form.skin)
    out = []
    for i in range(max(3, count)):
        turn = 2.399 * i          # the golden angle: never a repeating pattern
        rise = form.length * (0.62 - 1.24 * ((i * 0.37) % 1.0))
        size = form.beam * (0.16 + 0.14 * ((i * 0.53) % 1.0))
        out.append(_box(size, size * 0.45, size * 1.7, light, dark,
                        dx=form.beam * 1.05 * math.cos(turn),
                        dy=form.beam * 1.05 * math.sin(turn), dz=rise))
    return out


def _cap_piece(form, _count: int) -> list:
    light, _dark = _skin(SYSTEM)
    return [_tube(form.beam * 0.22, form.length * 0.92,
                  form.beam * 0.10, form.length * 1.14, 7, 0, light, light)]


def _root(form, _count: int) -> list:
    """Where the drive is anchored into the body."""
    return [_tube(form.beam * 0.34, -form.length * 1.02,
                  form.beam * 0.46, -form.length * 0.78, 8, 0, GLOW, DEEP)]


FURNITURE = {
    "ridge": _ridge, "bloom": _bloom, "spine": _spine, "slab": _slab,
    "fins": _fins, "cradle": _cradle, "lattice": _lattice, "core": _core,
    "shards": _shards, "cap": _cap_piece, "root": _root,
}


def mesh_for_family(family: str) -> tuple:
    """The silhouette of one family, built from its own numbers."""
    form = FORMS.get(family) or FORMS["fabricated"]
    parts = _body(form)
    for kind, count in form.furniture:
        maker = FURNITURE.get(kind)
        if maker is not None:
            parts.extend(maker(form, count))
    return _build([(v, f) for v, f in parts])


#: One mesh per family, built once. A mesh per frame is what turns a plot into
#: a slideshow, and there are only five of them.
HULLS = {family: mesh_for_family(family) for family in FORMS}

#: Every family `data/chassis.py` uses must be in `FORMS`, or a ship falls back
#: to a Yards hull and quietly stops being itself. `tests/test_hullshapes.py`
#: refuses that.
DEFAULT_FAMILY = "fabricated"


def mesh_for(family: str) -> tuple:
    return HULLS.get(family) or HULLS[DEFAULT_FAMILY]
