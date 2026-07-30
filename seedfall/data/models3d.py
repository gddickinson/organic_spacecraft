"""Meshes for the things a pilot actually looks at out of the window.

Authored at radius 1 and scaled by whatever the object really is, so one
shipyard mesh serves a four-hundred-metre quay and a two-kilometre fleet hub
without a second set of numbers.

Kept deliberately coarse. A few dozen faces reads as a structure at a
kilometre and costs nothing to fill; the thing that makes it convincing is
not polygon count but having a lit face, a dark face and a recognisable
silhouette — which is why the shipyard has a spine, rings, and arms that
stick out, and the hull has a nose you can tell from its tail.

Colours are the theme's, given as plain hex so this file imports nothing.
"""

from __future__ import annotations

import math

#: The palette of a **built** thing: bone white, and near enough to it that
#: the shading has somewhere to go.
#:
#: `_shade` multiplies a base colour, so a dark base can never reach white
#: however hard the sun is: at #8ba39a a fully lit face came out middle grey
#: and the whole structure sat in the bottom fifth of the range with no sign
#: of where the star was. Dropping the fill light did nothing on its own —
#: measured, a median tone of 47 went to 42 — because the paint was the limit,
#: not the light.
#:
#: White also draws the line the game's fiction has always claimed and never
#: shown: a quay is *built* and a hull is *grown*. Stations are pale geometry;
#: the grown hulls in `data/hulls3d.py` keep their organic skins, and the two
#: no longer look like the same material.
PLATE = "#d9d6cd"
PLATE_DARK = "#8f8c84"
LUMEN = "#7fe3d2"
WARN = "#e0685f"
CHLORO = "#54cf7c"
ROCK = "#7a6d5e"
ROCK_DARK = "#584f45"
GOLD = "#e2ba60"


def _ring(radius: float, z: float, count: int, start: int) -> tuple:
    """A circle of vertices at a height, and the indices they take."""
    verts = [(radius * math.cos(math.tau * i / count),
              radius * math.sin(math.tau * i / count), z)
             for i in range(count)]
    return verts, list(range(start, start + count))


def _tube(r_a, z_a, r_b, z_b, count, start, colour, dark) -> tuple:
    """A band of quads between two rings, alternating shade for readability."""
    verts_a, idx_a = _ring(r_a, z_a, count, start)
    verts_b, idx_b = _ring(r_b, z_b, count, start + count)
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.append(((idx_a[i], idx_a[j], idx_b[j], idx_b[i]),
                      colour if i % 2 else dark))
    return verts_a + verts_b, faces


def _cap(radius, z, count, start, colour, up: bool) -> tuple:
    verts, idx = _ring(radius, z, count, start)
    verts.append((0.0, 0.0, z))
    tip = start + count
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.append(((idx[i], idx[j], tip) if up else (idx[j], idx[i], tip),
                      colour))
    return verts, faces


def _build(parts) -> tuple:
    """Stitch (verts, faces) fragments into one mesh, fixing up indices."""
    verts: list = []
    faces: list = []
    for piece_verts, piece_faces in parts:
        offset = len(verts)
        verts.extend(piece_verts)
        for indices, colour in piece_faces:
            faces.append((tuple(i + offset for i in indices), colour))
    return tuple(verts), tuple(faces)


def _shift(mesh, dx=0.0, dy=0.0, dz=0.0, scale=1.0) -> tuple:
    verts, faces = mesh
    return ([(x * scale + dx, y * scale + dy, z * scale + dz)
             for x, y, z in verts], faces)


def _box(hx, hy, hz, colour, dark, dx=0.0, dy=0.0, dz=0.0) -> tuple:
    v = [(dx - hx, dy - hy, dz - hz), (dx + hx, dy - hy, dz - hz),
         (dx + hx, dy + hy, dz - hz), (dx - hx, dy + hy, dz - hz),
         (dx - hx, dy - hy, dz + hz), (dx + hx, dy - hy, dz + hz),
         (dx + hx, dy + hy, dz + hz), (dx - hx, dy + hy, dz + hz)]
    f = [((0, 3, 2, 1), dark), ((4, 5, 6, 7), colour),
         ((0, 1, 5, 4), colour), ((2, 3, 7, 6), dark),
         ((1, 2, 6, 5), colour), ((3, 0, 4, 7), dark)]
    return v, f


def sphere(rings: int = 14, segments: int = 20, colour: str = PLATE,
           dark: str | None = None) -> tuple:
    """A UV sphere. Worlds, moons, and anything else that is round.

    **One colour, deliberately.** Every other mesh here alternates shade
    face-by-face so a flat-lit structure still reads as having parts; do that
    to a sphere and you get a chessboard, and the chessboard eats the one
    thing that makes a planet look like a planet — the terminator. Lit from
    the side, the shading across a single-coloured sphere *is* the day/night
    line, and it costs nothing.
    """
    dark = dark or colour
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
        faces.append(((0, 1 + s, 1 + (s + 1) % segments), colour))
    for r in range(rings - 2):
        base = 1 + r * segments
        nxt = base + segments
        for s in range(segments):
            t = (s + 1) % segments
            faces.append(((base + s, nxt + s, nxt + t, base + t), colour))
    last = 1 + (rings - 2) * segments
    for s in range(segments):
        faces.append(((bottom, last + (s + 1) % segments, last + s), dark))
    return tuple(verts), tuple(faces)


def shipyard() -> tuple:
    """A working yard: a spine, two habitation rings, and four docking arms.

    The silhouette is the point. A captain coming up on this from ten
    kilometres should be able to tell which way it is facing and where the
    berths are before any label loads.
    """
    parts = [
        # the spine
        _tube(0.16, -0.95, 0.16, 0.95, 8, 0, PLATE, PLATE_DARK),
        _cap(0.16, 0.95, 8, 0, PLATE, True),
        _cap(0.16, -0.95, 8, 0, PLATE_DARK, False),
        # two habitation rings
        _tube(0.72, -0.44, 0.72, -0.26, 16, 0, PLATE, PLATE_DARK),
        _tube(0.60, 0.30, 0.60, 0.46, 16, 0, PLATE, PLATE_DARK),
    ]
    mesh = _build([(v, f) for v, f in parts])
    verts, faces = mesh
    extra = [(list(verts), list(faces))]
    # four docking arms, and a lit berth at the end of each
    for i in range(4):
        angle = math.tau * i / 4
        cx, cy = math.cos(angle) * 0.62, math.sin(angle) * 0.62
        extra.append(_box(0.44 if i % 2 == 0 else 0.10,
                          0.10 if i % 2 == 0 else 0.44,
                          0.07, PLATE, PLATE_DARK, cx, cy, -0.02))
        extra.append(_box(0.10, 0.10, 0.10, LUMEN, CHLORO,
                          math.cos(angle) * 1.02, math.sin(angle) * 1.02,
                          -0.02))
    return _build(extra)


def hull() -> tuple:
    """Another ship: a blunt nose, a body, and an engine bell aft."""
    parts = [
        _cap(0.30, 0.98, 8, 0, PLATE, True),
        _tube(0.30, 0.98, 0.42, 0.30, 8, 0, PLATE, PLATE_DARK),
        _tube(0.42, 0.30, 0.40, -0.55, 8, 0, PLATE, PLATE_DARK),
        _tube(0.40, -0.55, 0.26, -0.78, 8, 0, PLATE_DARK, PLATE_DARK),
        _tube(0.26, -0.78, 0.36, -0.98, 8, 0, WARN, WARN),
        _cap(0.36, -0.98, 8, 0, WARN, False),
    ]
    pieces = [(v, f) for v, f in parts]
    # a pair of radiator fins, which is what a grown hull actually has
    pieces.append(_box(0.86, 0.03, 0.22, PLATE_DARK, PLATE, 0.0, 0.0, -0.10))
    return _build(pieces)


def anchor_gate() -> tuple:
    """A Weave anchor: a torus of something that is not made of anything."""
    count, tube = 18, 6
    verts, faces = [], []
    for i in range(count):
        a = math.tau * i / count
        for j in range(tube):
            b = math.tau * j / tube
            r = 0.78 + 0.16 * math.cos(b)
            verts.append((r * math.cos(a), r * math.sin(a),
                          0.16 * math.sin(b)))
    for i in range(count):
        ni = (i + 1) % count
        for j in range(tube):
            nj = (j + 1) % tube
            faces.append(((i * tube + j, ni * tube + j,
                           ni * tube + nj, i * tube + nj),
                          GOLD if (i + j) % 2 else "#8a6f2e"))
    return tuple(verts), tuple(faces)


def asteroid(seed: int = 0) -> tuple:
    """A lumpy rock. Deterministic in the seed, so a belt is not a blur."""
    base_verts, faces = sphere(6, 8, ROCK, ROCK_DARK)
    verts = []
    for index, (x, y, z) in enumerate(base_verts):
        # A cheap repeatable hash, so rock 7 is rock 7 in every frame.
        h = math.sin((index + 1) * 12.9898 + seed * 78.233) * 43758.5453
        jitter = 0.72 + 0.5 * (h - math.floor(h))
        verts.append((x * jitter, y * jitter, z * jitter))
    return tuple(verts), faces


def recoloured(mesh, colour: str) -> tuple:
    """The same geometry in a different paint. Cheap, and cached by caller."""
    verts, faces = mesh
    return verts, tuple((indices, colour) for indices, _old in faces)


#: Built once. Meshes never change, and rebuilding a sphere per frame is the
#: sort of thing that turns a smooth window into a slideshow.
SHIPYARD = shipyard()
HULL = hull()
GATE = anchor_gate()
WORLD = sphere(16, 22, PLATE)
MOON = sphere(8, 12, PLATE_DARK)
ASTEROIDS = tuple(asteroid(i) for i in range(6))

#: A world's paint, by what kind of place it is.
BODY_TINT = {
    "rocky": "#9a8b74", "asteroid": "#7a6d5e", "moon": "#8e8e86",
    "ice": "#a9c6d6", "ocean": "#4f86b8", "gas": "#c2a06a",
    "comet": "#9fb6c0", "star": "#e8c98a",
}

#: One world mesh per kind, built once at import.
WORLDS = {kind: recoloured(WORLD, tint) for kind, tint in BODY_TINT.items()}


#: How each sort of thing is presented, as (spin per second, tilt). A tilt
#: near zero puts the model's +z axis down the camera's line of sight.
#:
#: **Which is why this table exists.** Every ship in this package is authored
#: nose along +z, and the sky drew hulls at a tilt of 0.42 — twenty-four
#: degrees off dead ahead. Rendered and looked at, all five errands were the
#: same foreshortened blob: the silhouettes were real and none of them was
#: visible. A hull is shown broadside because a ship is a profile; a berth
#: keeps the shallow tilt that lets its rings and arms read as rings and arms.
#: How each sort of thing is held up, as (turns per second, tilt).
#:
#: **A berth's rate is not here any more.** It was `1/900` — a decorative
#: number, and a station drawn turning at a rate the docking model knew
#: nothing about is a picture arguing with the game: the mesh came round every
#: fifteen minutes while the berths on it never moved at all. A structure's
#: real rate is `sim/moorings.turn_seconds`, derived from the pace its berths
#: are meant to travel at, and callers who have the sim to hand pass it in.
#: This module is `data/` and may not reach into `sim/`, so the fallback here
#: is *still*: a berth nobody has told about the clock does not turn, which is
#: wrong in a small and visible way rather than in a large and invisible one.
ATTITUDE = {
    "hull": (0.0, 1.28),
    "gate": (1.0 / 2600.0, 0.52),
    "berth": (0.0, 0.42),
}


def present(kind: str, look: str, elapsed: float = 0.0,
            spin: float | None = None) -> dict:
    """The mesh for one thing in the sky, and how to hold it up.

    One call, so the shape and the angle it is shown at cannot disagree — and
    so the thing you pick out at forty kilometres is the same shape, at the
    same attitude, that you come alongside.

    `spin` overrides the table when the caller knows better, which for a berth
    it does: `sim/moorings.spin_at` is the one door for which way round a
    structure is, and the berths it hands the flight computer are turned by
    exactly that angle.
    """
    mesh = for_sight(kind, look)
    if kind == "hull":
        rate, tilt = ATTITUDE["hull"]
    elif look == "gate":
        rate, tilt = ATTITUDE["gate"]
    else:
        rate, tilt = ATTITUDE["berth"]
    turned = elapsed * rate if spin is None else float(spin)
    return {"mesh": mesh, "spin": turned, "tilt": tilt}


def for_sight(kind: str, look: str) -> tuple:
    """The mesh for one thing in the sky, by what it actually is.

    The one door. `ui/viewport` asks it for the things in the sky and for the
    thing being approached, so what you pick out at forty kilometres is the
    same shape you come alongside — which it was not before: the sky drew every
    berth and every hull with `SHIPYARD`, and only the approach target got so
    much as a gate.
    """
    from .berths3d import berth_mesh
    from .ships3d import ship_mesh
    if kind == "anchorage":
        return berth_mesh(look)
    if kind == "hull":
        return ship_mesh(look)
    return berth_mesh("quay")
