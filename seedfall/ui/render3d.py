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

#: How much light a face gets with the star behind it. Not zero: a hull in a
#: system is lit by the star, by the planet it is over, and by its own running
#: lights, and a pure black silhouette reads as a hole in the picture.
AMBIENT = 0.40

#: How far a face's brightness can be lifted by facing the star squarely.
DIFFUSE = 1.05

#: A rim of light along the edge facing away from the camera, which is what
#: separates a dark hull from dark space at a glance.
RIM = 0.34


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


def draw(painter, camera: Camera, mesh, at, scale: float, light,
         spin: float = 0.0, tilt: float = 0.0, outline: bool = False,
         glare: float = 1.0) -> int:
    """Paint one model. Returns how many faces actually landed on screen.

    `mesh` is `(verts, faces)` where a face is `(indices, colour)`. `at` is
    where the model's centre sits in the camera's frame, `scale` is its
    radius in the same units, and `light` is the direction the starlight
    travels *from*.
    """
    verts, faces = mesh
    cs, sn = math.cos(spin), math.sin(spin)
    ct, st = math.cos(tilt), math.sin(tilt)
    placed = []
    for vx, vy, vz in verts:
        # spin about the model's own pole, then tilt it over
        x, y = vx * cs - vy * sn, vx * sn + vy * cs
        y, z = y * ct - vz * st, y * st + vz * ct
        placed.append((at[0] + x * scale, at[1] + y * scale,
                       at[2] + z * scale))

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
