"""A small solid-3D renderer: meshes, a light, and something worth looking at.

The conn's windows drew a flat coloured circle with a radial gradient behind
it. At twelve kilometres that reads as a distant object and at six hundred
metres it reads as a flat coloured circle, which is a poor thing to be
watching while you berth a hull against a shipyard.

This is the substrate. It is deliberately small — a few hundred faces a frame,
filled with `QPainter`, no textures and no shaders — because the alternative
is a dependency and a build step for a game that is otherwise pure PyQt.
What it does have is the four things that make a solid read as solid:

* **Perspective.** The same lens the starfield goes through, so a hull's
  angular size *is* the range instrument.
* **A light.** The system's own star, in the right direction, which is what
  gives a planet a terminator and a station a lit face and a dark one.
* **Depth.** Painter's algorithm on face centroids, which is wrong for
  interpenetrating geometry and perfectly adequate for convex-ish hulls.
* **Back-face culling**, so a closed mesh costs half what it looks like.

Everything is in the target's frame, in kilometres, exactly as `sim/conn.py`
keeps it. A model is authored at radius 1 and scaled by whatever it is.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPen, QPolygonF
from PyQt6.QtCore import Qt

from ..data import models3d

#: How much light a face gets with the star behind it.
#:
#: **Near nothing, because in vacuum there is near nothing.** This was 0.40,
#: which is a studio fill light and not a star: it lifted every shadowed face
#: to the same grey and left a Fleet Hub at 943 m reading as a flat cutout —
#: measured, the whole structure sat between 20 and 215 with a median of 47,
#: the bottom fifth of the range, and nothing in the frame said where the sun
#: was.
#:
#: Not zero either. A hull is lit by the world it is over and by its own
#: running lights, and a face at pure black is a hole in the picture rather
#: than a shadow. Six per cent is the least that still reads as a surface.
AMBIENT = 0.06

#: How far a face's brightness can be lifted by facing the star squarely.
#:
#: **The sum with `AMBIENT` is what full day comes to, and it has a ceiling.**
#: `ui/spheres.py` paints a world by this same law, and a surface of 154 at
#: `AMBIENT + DIFFUSE` must land under 255 or the sub-stellar point clips and
#: the whole lit half goes flat — the exact defect `test_lighting` was written
#: for after it hid for a cycle. That caps the sum at about 1.65; it was 1.45
#: and stays there.
#:
#: So the change is not more light, it is **light in one place**. Full day is
#: what it always was and the shadow is a sixth of what it was, which is the
#: whole of the difference between a lit object and a studio model.
DIFFUSE = 1.40

#: A rim of light along the edge facing away from the camera, which is what
#: separates a dark hull from dark space at a glance — and the only thing that
#: does, now the shadow side is genuinely dark.
RIM = 0.42


def unit(v) -> tuple:
    n = math.sqrt(sum(c * c for c in v))
    if n < 1e-12:
        return (0.0, 0.0, 1.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b) -> float:
    return sum(x * y for x, y in zip(a, b))


class Camera:
    """Where the eye is and which way it looks, plus the lens."""

    def __init__(self, at, forward, up, width: int, height: int,
                 half_fov: float):
        self.at = tuple(at)
        self.fwd = unit(forward)
        right = cross(self.fwd, up)
        if sum(c * c for c in right) < 1e-12:
            right = cross(self.fwd, (0.0, 1.0, 0.0))
        self.right = unit(right)
        self.up = unit(cross(self.right, self.fwd))
        self.w, self.h = width, height
        self.focal = (min(width, height) * 0.5) / math.tan(half_fov)

    def to_view(self, point) -> tuple:
        """World point to camera space: (right, up, ahead)."""
        rel = (point[0] - self.at[0], point[1] - self.at[1],
               point[2] - self.at[2])
        return (dot(rel, self.right), dot(rel, self.up), dot(rel, self.fwd))

    def project(self, point):
        """A world point to the screen, or None if it is behind the lens."""
        x, y, ahead = self.to_view(point)
        if ahead <= 1e-9:
            return None
        return QPointF(self.w * 0.5 + x / ahead * self.focal,
                       self.h * 0.5 - y / ahead * self.focal), ahead


def _shade(base: QColor, lit: float, rim: float, glare: float = 1.0) -> QColor:
    level = max(0.0, min(1.6, AMBIENT + DIFFUSE * lit * glare + RIM * rim))
    return QColor(min(255, int(base.red() * level)),
                  min(255, int(base.green() * level)),
                  min(255, int(base.blue() * level)))



#: One point through a model's own rotation: spin, then tilt, then yaw.
#:
#: **Split out of `draw` so a thing drawn *on* a model lands on it**, and then
#: moved down into `data/models3d.py` so a thing *flown at* lands on it too.
#: The flight panel marks each engine where `data/mounts.py` says it sits, and
#: `sim/moorings` puts a berth where the mesh draws the fitting: three callers,
#: one rotation, because this project has been bitten every time a number was
#: written twice. It is re-exported here because this is where the renderer's
#: callers look for it.
place = models3d.place


#: How far outside a window a projected vertex may land and still be worth
#: handing to the rasteriser, in pixels. Generous — a face can legitimately
#: run well off the edge — but finite, because the alternative is a number
#: with no upper bound at all.
FAR_OFF = 100_000.0


def draw(painter, camera: Camera, mesh, at, scale: float, light,
         spin: float = 0.0, tilt: float = 0.0, outline: bool = False,
         glare: float = 1.0, yaw: float = 0.0) -> int:
    """Paint one model. Returns how many faces actually landed on screen.

    `mesh` is `(verts, faces)` where a face is `(indices, colour)`. `at` is
    where the model's centre sits in the camera's frame, `scale` is its
    radius in the same units, and `light` is the direction the starlight
    travels *from*.

    Three rotations, in this order: `spin` about the model's own pole, `tilt`
    over onto its side, then `yaw` about the world's vertical.

    **`yaw` is why there are three.** Every model in this package is authored
    nose along +z, and spin-then-tilt can lay that nose down but not then point
    it anywhere: the tilt fixes which way it falls. On a tactical plot, where
    hulls sit in a plane and each one is heading somewhere, that left every
    ship standing on its tail — which is what `ui/battle3d.py` drew until this
    was added, and why a heading could not be read off the picture at all.
    """
    verts, faces = mesh
    placed = [tuple(a + c * scale for a, c in zip(at, place(v, spin, tilt, yaw)))
              for v in verts]

    lit_from = unit(light)
    drawn = []
    for indices, colour in faces:
        if len(indices) < 3:
            continue
        a, b, c = (placed[indices[0]], placed[indices[1]], placed[indices[2]])
        normal = unit(cross((b[0] - a[0], b[1] - a[1], b[2] - a[2]),
                            (c[0] - a[0], c[1] - a[1], c[2] - a[2])))
        centre = [sum(placed[i][k] for i in indices) / len(indices)
                  for k in range(3)]
        to_eye = unit((camera.at[0] - centre[0], camera.at[1] - centre[1],
                       camera.at[2] - centre[2]))
        facing = dot(normal, to_eye)
        if facing <= 0.0:
            continue                       # back face
        points = []
        depth = 0.0
        for index in indices:
            got = camera.project(placed[index])
            if got is None:
                points = []
                break
            point, ahead = got
            # **A face straddling the lens is not drawable, and asking for it
            # anyway takes the process down.** `project` divides by depth, so
            # a vertex a hair in front of the camera comes back at a
            # coordinate in the billions; hand that to the rasteriser and it
            # segfaults — no traceback, no failing check, exit 139. Measured
            # by `faulthandler` after a run died here two times in four, in
            # the middle of a suite that had nothing to do with the one that
            # made the window. A hull you are *inside* is the everyday way to
            # produce it, which quays orbiting their worlds made reachable.
            if not (-FAR_OFF <= point.x() <= FAR_OFF
                    and -FAR_OFF <= point.y() <= FAR_OFF):
                points = []
                break
            points.append(point)
            depth = max(depth, ahead)
        if len(points) < 3:
            continue
        lit = max(0.0, dot(normal, [-c for c in lit_from]))
        rim = (1.0 - facing) ** 2
        drawn.append((depth, points,
                      _shade(QColor(colour), lit, rim, glare)))

    drawn.sort(key=lambda row: -row[0])
    for _depth, points, colour in drawn:
        painter.setBrush(colour)
        if outline:
            painter.setPen(QPen(colour.darker(150), 1))
        else:
            # Stroked in the face's *own* colour rather than left unpenned.
            # Two adjacent antialiased polygons each cover about half of the
            # pixel on the edge they share, and each blends its half with
            # whatever is behind — so a solid hull came out with a hairline
            # of background at every seam and every sphere in the game wore
            # a faint wireframe. Half a pixel of overspill closes it.
            painter.setPen(QPen(colour, 1))
        painter.drawPolygon(QPolygonF(points))
    return len(drawn)


def angular_radius(distance_km: float, radius_km: float) -> float:
    """How wide a thing looks, in radians, at a range."""
    if distance_km <= 1e-9:
        return math.pi / 2
    return math.asin(min(0.999, radius_km / distance_km))


def screen_radius(camera: Camera, distance_km: float,
                  radius_km: float) -> float:
    """How wide a thing looks, in pixels, at a range."""
    return math.tan(angular_radius(distance_km, radius_km)) * camera.focal
