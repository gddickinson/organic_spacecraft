"""Worlds that look like the worlds they are.

`models3d.sphere` gives a ball of one colour, which is the right shape and
tells you nothing. Every body in the Verge — a 12 km comet, a 7,000 km ocean,
a 71,000 km gas giant — came out as the same ball with a different tint on it.

The cheapest thing that fixes it is **latitude**. Colour a sphere's bands by
how far up them you are and you get polar caps for nothing; vary the bands and
you get a gas giant; put a flat annulus round it and you get rings. None of it
costs more than the sphere already cost, and all of it is the difference
between a body and a marble.

Everything is authored at radius 1 and scaled by what the body actually is,
the same as the rest of `data/models3d.py`.
"""

from __future__ import annotations

import math

from .models3d import sphere as _plain_sphere

#: How many bands of latitude a world is cut into, and how many segments
#: round. Enough that a cap has a curved edge and a giant has stripes.
RINGS, SEGMENTS = 22, 30


def _lerp(a: str, b: str, t: float) -> str:
    """Blend two hex colours."""
    t = max(0.0, min(1.0, t))
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return "#%02x%02x%02x" % (round(ar + (br - ar) * t),
                              round(ag + (bg - ag) * t),
                              round(ab + (bb - ab) * t))


def by_latitude(paint, rings: int = RINGS, segments: int = SEGMENTS) -> tuple:
    """A sphere whose faces are coloured by how far up the world they sit.

    `paint(lat)` takes -1 at the south pole through +1 at the north and hands
    back a colour. That one hook is the whole vocabulary: caps, bands, a
    weathered equator and a cloud deck are all functions of latitude.
    """
    verts = [(0.0, 0.0, 1.0)]
    for r in range(1, rings):
        phi = math.pi * r / rings
        for s in range(segments):
            theta = math.tau * s / segments
            verts.append((math.sin(phi) * math.cos(theta),
                          math.sin(phi) * math.sin(theta), math.cos(phi)))
    verts.append((0.0, 0.0, -1.0))
    bottom = len(verts) - 1

    faces = []
    for s in range(segments):
        faces.append(((0, 1 + s, 1 + (s + 1) % segments), paint(1.0)))
    for r in range(rings - 2):
        base = 1 + r * segments
        nxt = base + segments
        lat = math.cos(math.pi * (r + 1.5) / rings)
        colour = paint(lat)
        for s in range(segments):
            t = (s + 1) % segments
            faces.append(((base + s, nxt + s, nxt + t, base + t), colour))
    last = 1 + (rings - 2) * segments
    for s in range(segments):
        faces.append(((bottom, last + (s + 1) % segments, last + s),
                      paint(-1.0)))
    return tuple(verts), tuple(faces)


def cap_paint(ground: str, cap: str, cap_from: float = 0.62,
              mottle: str | None = None):
    """A world with polar caps, and optionally a blotched surface.

    `mottle` is what the low latitudes are streaked with — maria on a moon,
    dust seas on a rocky world. It is there to give a surface regions rather
    than one flat coat; it is *not* what keeps two worlds apart. That job
    belongs to the ground colours, and a sweep with every mottle removed
    still leaves the closest pair of worlds well clear of the bar. Said
    plainly because the first draft of this line claimed the opposite.
    """
    def paint(lat: float) -> str:
        edge = abs(lat)
        if edge >= cap_from:
            return _lerp(ground, cap,
                         min(1.0, (edge - cap_from) / (1 - cap_from)))
        if mottle is None:
            return ground
        # A slow wave across the middle latitudes, so the surface has
        # regions rather than being one flat coat.
        blend = (math.sin(lat * 7.3) + math.sin(lat * 3.1)) / 2
        return _lerp(ground, mottle, max(0.0, blend))
    return paint


def band_paint(base: str, light: str, dark: str, bands: int = 6):
    """A gas giant: belts and zones, and a brighter equator.

    The contrast is deliberately high. Flat shading already darkens a sphere
    toward its limb, and a subtle band disappears under that entirely — the
    first draft's giant read as a plain ball with a faint grid on it.
    """
    def paint(lat: float) -> str:
        wave = math.sin(lat * math.pi * bands)
        tint = _lerp(dark, light, (wave + 1) / 2)
        # A brighter equatorial zone, and poles that fall away.
        return _lerp(tint, base, min(1.0, abs(lat) * 1.1))
    return paint


#: The radial structure of a ring system: (from, to, colour), in body radii.
#: Concentric, with a gap — which is what a ring system actually looks like,
#: and what the first draft got wrong by alternating colour **per segment**
#: and producing a cartwheel of spokes.
RING_BANDS = (
    (1.36, 1.62, "#8d8069"),
    (1.62, 1.70, "#5d5445"),      # a division
    (1.70, 2.10, "#cbb894"),
    (2.10, 2.16, "#4f4839"),      # another
    (2.16, 2.44, "#a2937a"),
    (2.44, 2.62, "#6f6555"),
)


def ring_disc(bands=RING_BANDS, segments: int = 56) -> tuple:
    """A flat ring system, in concentric bands. Drawn both sides.

    Scaled in the *body's* radii, so 1.36 is a third again the world's own
    width out from its centre, which is roughly where a real ring begins.
    """
    verts, faces = [], []
    for inner, outer, colour in bands:
        base = len(verts)
        for i in range(segments):
            a = math.tau * i / segments
            verts.append((inner * math.cos(a), inner * math.sin(a), 0.0))
            verts.append((outer * math.cos(a), outer * math.sin(a), 0.0))
        for i in range(segments):
            j = (i + 1) % segments
            ai, ao = base + i * 2, base + i * 2 + 1
            bi, bo = base + j * 2, base + j * 2 + 1
            faces.append(((ai, ao, bo, bi), colour))
            faces.append(((bi, bo, ao, ai), colour))    # the other face
    return tuple(verts), tuple(faces)


#: One mesh per kind of world. Built once at import; a sphere per frame is
#: what turns a smooth window into a slideshow.
#: One mesh per kind. The palette is chosen for *separation* as much as for
#: plausibility: a rocky world and a moon are both grey-brown rock and came
#: out seventeen points apart, which is not a catalogue. A rocky world is
#: warm and dusty with ice at the poles; a moon is cold grey with dark maria
#: and barely any cap at all.
WORLD_PAINTS = {
    "rocky": cap_paint("#b07a4e", "#eef4f8", 0.66, mottle="#7d4f2e"),
    "ocean": cap_paint("#2f6fae", "#eaf4ff", 0.72),
    "ice": cap_paint("#c2e2f0", "#ffffff", 0.24),
    "moon": cap_paint("#9a9aa2", "#b4b8be", 0.86, mottle="#4a4a52"),
    "asteroid": cap_paint("#6b5942", "#7d6c55", 0.88, mottle="#3f3428"),
    "comet": cap_paint("#8fd3d8", "#eaffff", 0.34),
    "gas": band_paint("#d8b478", "#f6e6b8", "#7a5c30"),
}

#: How finely a world is cut, coarse and fine. **This is what makes a world look
#: round, and nothing else did.**
#:
#: Flat shading gives each face one colour, so a sphere reads as the polyhedron it
#: is — at 22 by 30 you can count the quads across the terminator. Four attempts
#: at smoothing the *shading* went in the bin: a `QLinearGradient` per face is
#: constant perpendicular to its own axis where real Gouraud varies, and that
#: error alternates with a quad's orientation, so every one of them put a
#: checkerboard on the sphere instead of a smooth curve. It was not the rim term
#: either — forcing that to zero left the pattern exactly as it was.
#:
#: Geometry is what worked. Rendered side by side, 22x30 is plainly faceted and
#: 44x58 is smooth. The cost is real and it is in *faces*, not pixels: 6.7 ms
#: against 25 ms for the same world at any size on screen. Hence two levels, and
#: `ui/viewport.py` spending the fine one only on something big enough to show it.
#: Where the faces go matters as much as how many. Rendered at equal cost —
#: about 2,550 faces and 20 ms — 44x58 still bands horizontally, because the
#: colour runs with latitude and rings are what sample it; 70x36 and 96x26 kill
#: that banding and put vertical stripes on instead, because segments are what
#: round the silhouette. 60x44 is the pair that reads smooth in both.
COARSE = (22, 30)
FINE = (60, 44)

WORLD_MESHES = {kind: by_latitude(paint, *COARSE)
                for kind, paint in WORLD_PAINTS.items()}

#: The same worlds cut fine, for when one fills the window.
WORLD_MESHES_FINE = {kind: by_latitude(paint, *FINE)
                     for kind, paint in WORLD_PAINTS.items()}

#: Rings, for the giants that carry them. Which do is decided per body by
#: `sim/sky.py`, deterministically, so a ringed world is always ringed.
#:
#: Two halves. A flat annulus interpenetrates the sphere it goes round, and
#: painter's algorithm has no answer to that — so the far arc is laid down
#: before the world and the near arc after it, and the world occludes the
#: part of the ring that passes behind it. Cheaper than sorting, and right.
RINGS_MESH = ring_disc()
RINGS_FRONT = ring_disc(tuple((a, b, _lerp(c, "#ffffff", 0.12))
                              for a, b, c in RING_BANDS))

#: The share of gas giants that carry a ring system.
RINGED_SHARE = 0.45


def mesh_for(kind: str, fine: bool = False) -> tuple:
    """The mesh for a kind of body, falling back to a plain grey ball.

    `fine` asks for the finely cut version, which is what stops a world that
    fills the window looking like a polyhedron. It costs about four times the
    faces, so `ui/viewport.py` asks for it only when the thing is big enough on
    screen to show the difference.
    """
    table = WORLD_MESHES_FINE if fine else WORLD_MESHES
    return table.get(kind) or _plain_sphere(14, 20, "#8ba39a")
