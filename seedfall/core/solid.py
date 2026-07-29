"""A very small 3D kit: build solids out of primitives, project them to 2D.

The game ships with PyQt6 and nothing else, so this is a software renderer:
polygons, a painter's-algorithm depth sort and flat shading, handed to whoever
wants to draw them. No OpenGL, no numpy, no scene graph — a few hundred faces
at thirty frames is well inside what QPainter does comfortably, and it renders
identically offscreen, which is the only way the suite can look at it.

`models3d/` builds the same designs properly with trimesh for export. That is a
tool, not part of the game: it needs dependencies the game refuses to take. The
shapes here follow its vocabulary — prolate hull, equatorial ridge, phototropic
cap, radiator bloom — so the two read as the same ship.

Nothing here knows what a ship is. Faces in, faces out.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

#: A face is a ring of points plus the tint key it should be drawn in.
Point = tuple[float, float, float]


@dataclass
class Face:
    points: list          # world-space, wound counter-clockwise seen from outside
    tint: str
    tag: str = ""         # which part of the ship this belongs to
    #: 0 sound .. 1 dead. A grown hull does not dim uniformly when it is hurt,
    #: it necroses in patches, and the painter tints by this.
    hurt: float = 0.0


@dataclass
class Solid:
    """One named piece of a machine, and the faces that draw it."""
    tag: str
    name: str
    faces: list = field(default_factory=list)
    detail: str = ""      # a line about it, for whatever is showing the model


# ── vector arithmetic ──────────────────────────────────────────────────────

def sub(a, b) -> Point:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add(a, b) -> Point:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def scale(a, k: float) -> Point:
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b) -> Point:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def length(a) -> float:
    return math.sqrt(dot(a, a)) or 1e-9


def unit(a) -> Point:
    return scale(a, 1.0 / length(a))


def normal_of(points) -> Point:
    """Newell's method: stable for polygons that are not quite planar."""
    nx = ny = nz = 0.0
    count = len(points)
    for index in range(count):
        current, following = points[index], points[(index + 1) % count]
        nx += (current[1] - following[1]) * (current[2] + following[2])
        ny += (current[2] - following[2]) * (current[0] + following[0])
        nz += (current[0] - following[0]) * (current[1] + following[1])
    return unit((nx, ny, nz))


def centre_of(points) -> Point:
    count = len(points) or 1
    return (sum(p[0] for p in points) / count,
            sum(p[1] for p in points) / count,
            sum(p[2] for p in points) / count)


# ── building blocks ────────────────────────────────────────────────────────

def _quad(a, b, c, d, tint, tag) -> Face:
    return Face([a, b, c, d], tint, tag)


def ellipsoid(rx, ry, rz, tint, at=(0, 0, 0), tag="", rings=10, segments=16,
              taper=0.0) -> list:
    """A uv-sphere, scaled. `taper` narrows it toward +z, as a hull does."""
    faces = []
    for ring in range(rings):
        phi0 = math.pi * ring / rings
        phi1 = math.pi * (ring + 1) / rings
        for seg in range(segments):
            th0 = 2 * math.pi * seg / segments
            th1 = 2 * math.pi * (seg + 1) / segments
            corners = []
            # Wound so the normal points *out*. The other order looks equally
            # reasonable and is wrong in a way that reads as a feature: the
            # near half of every hull was culled as back-facing, so the ship
            # drew as an x-ray of its own far wall with the hold floating in
            # front of it.
            for phi, th in ((phi0, th0), (phi1, th0), (phi1, th1), (phi0, th1)):
                z = math.cos(phi)
                k = 1.0 - taper * z
                corners.append(add(at, (rx * k * math.sin(phi) * math.cos(th),
                                        ry * k * math.sin(phi) * math.sin(th),
                                        rz * z)))
            faces.append(Face(corners, tint, tag))
    return faces


def tube(p0, p1, radius, tint, tag="", segments=10, radius1=None,
         caps=True) -> list:
    """A cylinder — or a cone, with `radius1` — from p0 to p1."""
    axis = sub(p1, p0)
    up = (0.0, 0.0, 1.0) if abs(unit(axis)[2]) < 0.94 else (1.0, 0.0, 0.0)
    side = unit(cross(axis, up))
    other = unit(cross(axis, side))
    r1 = radius if radius1 is None else radius1

    def rim(centre, r, index):
        angle = 2 * math.pi * index / segments
        return add(centre, add(scale(side, r * math.cos(angle)),
                               scale(other, r * math.sin(angle))))

    faces = []
    for index in range(segments):
        faces.append(Face([rim(p0, radius, index), rim(p0, radius, index + 1),
                           rim(p1, r1, index + 1), rim(p1, r1, index)],
                          tint, tag))
    if caps:
        faces.append(Face([rim(p1, r1, i) for i in range(segments)], tint, tag))
        faces.append(Face([rim(p0, radius, i)
                           for i in range(segments - 1, -1, -1)], tint, tag))
    return faces


def ring_of(radius, thickness, tint, at=(0, 0, 0), tag="", segments=20,
            sides=6) -> list:
    """A torus lying in the xy plane — the hull's equatorial ridge."""
    faces = []
    for index in range(segments):
        for side in range(sides):
            corners = []
            for di, ds in ((0, 0), (1, 0), (1, 1), (0, 1)):
                major = 2 * math.pi * (index + di) / segments
                minor = 2 * math.pi * (side + ds) / sides
                r = radius + thickness * math.cos(minor)
                corners.append(add(at, (r * math.cos(major),
                                        r * math.sin(major),
                                        thickness * math.sin(minor))))
            faces.append(Face(corners, tint, tag))
    return faces


def box(sx, sy, sz, tint, at=(0, 0, 0), tag="") -> list:
    """An axis-aligned box, centred on `at`. Holds, bays, racks."""
    x, y, z = sx / 2, sy / 2, sz / 2
    v = [add(at, p) for p in
         ((-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
          (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z))]
    order = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
             (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))
    return [Face([v[i] for i in quad], tint, tag) for quad in order]


def petal(direction, length_, width, tint, at=(0, 0, 0), tag="") -> list:
    """A flattened vane: one radiator petal, one fin, one sail."""
    axis = unit(direction)
    up = (0.0, 0.0, 1.0) if abs(axis[2]) < 0.94 else (1.0, 0.0, 0.0)
    side = scale(unit(cross(axis, up)), width / 2)
    tip = add(at, scale(axis, length_))
    root_a, root_b = add(at, side), sub(at, side)
    mid_a = add(add(at, scale(axis, length_ * 0.55)), scale(side, 0.75))
    mid_b = sub(add(at, scale(axis, length_ * 0.55)), scale(side, 0.75))
    return [Face([root_a, mid_a, tip, mid_b, root_b], tint, tag),
            Face([root_b, mid_b, tip, mid_a, root_a], tint, tag)]


def orient(faces, direction, at) -> list:
    """Rotate faces built around +z so that +z points along `direction`."""
    target = unit(direction)
    z = (0.0, 0.0, 1.0)
    axis = cross(z, target)
    sin_a, cos_a = length(axis), dot(z, target)
    if sin_a < 1e-8:
        moved = faces if cos_a > 0 else [
            Face([(p[0], -p[1], -p[2]) for p in f.points], f.tint, f.tag)
            for f in faces]
        return [Face([add(at, p) for p in f.points], f.tint, f.tag)
                for f in moved]
    k = unit(axis)
    out = []
    for face in faces:                      # Rodrigues, per point
        points = []
        for p in face.points:
            term = add(add(scale(p, cos_a), scale(cross(k, p), sin_a)),
                       scale(k, dot(k, p) * (1 - cos_a)))
            points.append(add(at, term))
        out.append(Face(points, face.tint, face.tag))
    return out


# ── projection ─────────────────────────────────────────────────────────────

@dataclass
class View:
    """Where the eye is. Angles in radians, distance in model units."""
    yaw: float = 0.7
    pitch: float = 0.35
    distance: float = 5.2
    zoom: float = 1.0
    light: Point = (-0.45, -0.55, 0.70)


def _turn(p, view: View) -> Point:
    cy, sy = math.cos(view.yaw), math.sin(view.yaw)
    x = p[0] * cy - p[1] * sy
    y = p[0] * sy + p[1] * cy
    cp, sp = math.cos(view.pitch), math.sin(view.pitch)
    return (x, y * cp - p[2] * sp, y * sp + p[2] * cp)


@dataclass
class Painted:
    """One face, ready to draw: screen points, its shading and its depth."""
    points: list          # (x, y) in [-1, 1], y down
    shade: float          # 0 dark .. 1 lit — the key light
    depth: float          # larger is further away
    tint: str
    tag: str
    #: A rim term: how edge-on the face is to the viewer. A grown hull read as
    #: a flat green egg under one lambert light because nothing separated its
    #: silhouette from the void behind it.
    rim: float = 0.0
    #: A specular term. The painter decides how much of it to use — a
    #: fabricated plate is glossy, a photosynthetic membrane is not — which is
    #: the only thing that made the materials look like different substances.
    spec: float = 0.0
    #: 0 at the nearest face, 1 at the furthest. Used to fade distance back
    #: toward the void so a deep model does not read as a flat sticker.
    far: float = 0.0
    #: Carried through from the face: how dead this patch of hull is.
    hurt: float = 0.0


def project(faces, view: View, cull=True) -> list:
    """Faces to draw, furthest first. Back faces dropped, flat-shaded.

    Painter's algorithm on face centroids. It gets long thin solids that
    interpenetrate slightly wrong, which for a cutaway of a ship is a fair
    trade against the cost of a depth buffer in Python.
    """
    eye = (0.0, -view.distance, 0.0)
    light = unit(view.light)
    # A fill from the opposite quarter, weaker and colder, so the unlit side
    # is modelled rather than merely dark.
    fill = unit((-light[0] * 0.8, -light[1] * 0.5, -light[2] * 0.35 - 0.3))
    towards = unit((0.0, -1.0, 0.0))
    half = unit((light[0] + towards[0], light[1] + towards[1],
                 light[2] + towards[2]))
    out = []
    for face in faces:
        turned = [_turn(p, view) for p in face.points]
        normal = normal_of(turned)
        centre = centre_of(turned)
        if cull and dot(normal, sub(centre, eye)) > 0:
            continue
        depth = length(sub(centre, eye))
        points = []
        for p in turned:
            behind = p[1] + view.distance
            if behind < 0.05:
                behind = 0.05
            k = view.zoom * 1.6 / behind
            points.append((p[0] * k, -p[2] * k))
        key = max(0.0, dot(normal, light))
        bounce = max(0.0, dot(normal, fill))
        shade = max(0.0, min(1.0, 0.22 + 0.62 * key + 0.20 * bounce))
        facing = abs(dot(normal, towards))
        rim = max(0.0, 1.0 - facing) ** 2.2
        spec = max(0.0, dot(normal, half)) ** 24
        out.append(Painted(points, shade, depth, face.tint, face.tag,
                           rim=rim, spec=spec, hurt=face.hurt))
    out.sort(key=lambda f: -f.depth)
    if out:
        near, far = out[-1].depth, out[0].depth
        span = max(1e-6, far - near)
        for face in out:
            face.far = max(0.0, min(1.0, (face.depth - near) / span))
    return out


def bounds(faces) -> tuple:
    """(min, max) corners — for framing a model that has grown a mast."""
    points = [p for f in faces for p in f.points]
    if not points:
        return ((0, 0, 0), (0, 0, 0))
    return (tuple(min(p[i] for p in points) for i in range(3)),
            tuple(max(p[i] for p in points) for i in range(3)))
