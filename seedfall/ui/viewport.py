"""What a camera on the hull sees.

Six of them, bolted where you would expect: nose, tail, both beams, the back
and the belly. Each is a perspective projection out of the ship along its own
axis, and what is out there to see is the target, the star, and whatever else
is in the system.

Three things this has to get right or the pilot cannot fly on it:

* **The target grows.** Angular size is `2·asin(radius / range)`, so a quay a
  hundred metres across is a speck at ten kilometres and fills the screen at
  three hundred metres. That growth *is* the range instrument, read the way a
  pilot reads a window.
* **The stars do not move.** They are at infinity, so they turn with the
  heading and ignore the position. They are also fixed at import: a starfield
  drawn from `game.rng()` would shimmer, and would advance the save's seed
  every repaint.
* **Which camera sees it.** Something dead astern is in the aft camera and
  nowhere else, so the row of six is a genuine instrument rather than six
  copies of the same picture.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QWidget

from ..core.rng import RNG
from ..data import models3d, worlds3d
from ..sim import conn as conn_sim
from . import render3d, theme

#: Half the field of view, in radians. A wide-ish lens: enough to keep a
#: target in frame while manoeuvring, tight enough that motion reads.
#: The floor and ceiling on how bright a star may make the picture, and the
#: root that compresses the raw luminosity into them. A fourth root turns a
#: five-hundred-fold range into about four and a half, which is what a screen
#: can actually show; the floor keeps a red dwarf's worlds readable and the
#: ceiling keeps an A-type's from being a white rectangle.
GLARE_FLOOR, GLARE_CEILING, GLARE_ROOT = 0.55, 1.45, 0.25

HALF_FOV = math.radians(31.0)


def _starfield(count: int = 260) -> list:
    """Fixed directions on the unit sphere, drawn once and never again.

    Deliberately not from `game.rng()`: that advances the save's seed, so a
    starfield drawn from it would both shimmer between repaints and quietly
    reshuffle the chronicle every time a window was open. This project has
    already been bitten by exactly that in the docking instrument.
    """
    rng = RNG("viewport:stars")
    out = []
    for _ in range(count):
        z = rng.float(-1.0, 1.0)
        theta = rng.float(0.0, math.tau)
        r = math.sqrt(max(0.0, 1.0 - z * z))
        out.append((r * math.cos(theta), r * math.sin(theta), z,
                    rng.float(0.25, 1.0)))
    return out


def _field_at(seed) -> list:
    """A starfield from an arbitrary seed. Only the mutation harness calls
    this: it exists so a check that the sky holds still can be proved to bite,
    which two badly-built mutations failed to do."""
    rng = RNG(f"viewport:stars:{seed}")
    out = []
    for _ in range(len(STARS)):
        z = rng.float(-1.0, 1.0)
        theta = rng.float(0.0, math.tau)
        r = math.sqrt(max(0.0, 1.0 - z * z))
        out.append((r * math.cos(theta), r * math.sin(theta), z,
                    rng.float(0.25, 1.0)))
    return out


STARS = _starfield()


def hull_frame(conn) -> tuple:
    """The ship's own axes in the target's frame: nose, starboard, dorsal.

    The cameras used to be built from `conn.heading`, a bare yaw angle that
    **nothing ever wrote to** — while the drive was steered by `conn.nose`, a
    3D vector. So the nose camera did not look where the ship was pointing,
    and swinging the hull round with the thrusters changed nothing out of the
    windows. They are one thing now.

    The hull's roll is chosen rather than tracked: it keeps its belly toward
    whatever it is approaching, which is what a pilot would do and what makes
    the ventral camera worth having in orbit.
    """
    # A window can be opened with no approach running at all — the conn
    # offers nothing when the ship is not alongside anything — so this has to
    # answer for `None`. The control sweep caught it doing otherwise.
    if conn is None:
        return (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)
    nose = _unit(getattr(conn, "nose", None) or (0.0, 1.0, 0.0))
    # Belly-down toward the target, unless we are pointing straight at it.
    down = _unit([-c for c in conn.pos]) if conn.range_km > 1e-9 else (0, 0, -1)
    side = _cross(nose, down)
    if sum(c * c for c in side) < 1e-9:
        side = _cross(nose, (0.0, 0.0, 1.0))
        if sum(c * c for c in side) < 1e-9:
            side = _cross(nose, (0.0, 1.0, 0.0))
    right = _unit(side)
    # `cross(nose, right)`, not `cross(right, nose)`: the other way round put
    # the planet you are orbiting in the *dorsal* camera, which is the one
    # pointing at the sky.
    dorsal = _unit(_cross(nose, right))
    return nose, right, dorsal


def basis(view_vec, conn) -> tuple:
    """Camera axes in the target's frame: forward, right, up."""
    nose, right, dorsal = hull_frame(conn)
    vx, vy, vz = view_vec
    fwd = _unit((right[0] * vx + nose[0] * vy + dorsal[0] * vz,
                 right[1] * vx + nose[1] * vy + dorsal[1] * vz,
                 right[2] * vx + nose[2] * vy + dorsal[2] * vz))
    ref = dorsal if abs(sum(a * b for a, b in zip(fwd, dorsal))) < 0.95 else nose
    cam_right = _unit(_cross(fwd, ref))
    up = _unit(_cross(cam_right, fwd))
    return fwd, cam_right, up


def _rotate(vec, heading: float) -> tuple:
    c, s = math.cos(heading), math.sin(heading)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def _cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _unit(v) -> tuple:
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def project(vec, cam, width: int, height: int):
    """A direction in the target frame to a point on screen, or None.

    Returns `(x, y, distance_along_axis)`. Anything at or behind the lens is
    not in this camera's picture at all.
    """
    fwd, right, up = cam
    ahead = sum(a * b for a, b in zip(vec, fwd))
    if ahead <= 1e-9:
        return None
    focal = (min(width, height) * 0.5) / math.tan(HALF_FOV)
    x = sum(a * b for a, b in zip(vec, right)) / ahead * focal
    y = sum(a * b for a, b in zip(vec, up)) / ahead * focal
    return (width * 0.5 + x, height * 0.5 - y, ahead)


class Viewport(QWidget):
    """One camera's picture, live off a `Conn`."""

    def __init__(self, conn, view_id: str = "fore", compact: bool = False):
        super().__init__()
        self.conn = conn
        self.view_id = view_id
        self.compact = compact
        self.setMinimumSize(120, 92) if compact else self.setMinimumSize(360, 260)
        self.setAutoFillBackground(False)

    @property
    def view(self) -> tuple:
        for row in conn_sim.VIEWS:
            if row[0] == self.view_id:
                return row
        return conn_sim.VIEWS[0]

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#04080b"))

        conn = self.conn
        _vid, label_text, vec = self.view
        cam = basis(vec, conn)

        self._stars(p, cam, w, h)
        if conn is not None:
            self._sky(p, conn, cam, w, h)
            self._target(p, conn, cam, w, h)
        self._frame(p, label_text, w, h)
        p.end()

    # ── the picture ────────────────────────────────────────────────────────

    def _stars(self, p: QPainter, cam, w: int, h: int) -> None:
        for x, y, z, bright in STARS:
            at = project((x, y, z), cam, w, h)
            if at is None:
                continue
            sx, sy, _ahead = at
            if not (0 <= sx < w and 0 <= sy < h):
                continue
            shade = int(90 + 150 * bright)
            p.setPen(QPen(QColor(shade, shade, min(255, shade + 18)),
                          1.4 if bright > 0.8 else 1.0))
            p.drawPoint(QPointF(sx, sy))

    def _sky(self, p: QPainter, conn, cam, w: int, h: int) -> None:
        """The rest of the system: the star, and anything big enough to see.

        The windows used to draw the approach target and a fixed field of
        stars, and nothing else — so taking the conn with nothing in reach
        gave a black rectangle. Standing off a body at 0.40 AU the system's
        own star is **1.34° across**, which is two and a half Suns, and it
        was not being drawn.
        """
        from ..sim import sky as sky_sim

        seen = getattr(conn, "sky", None)
        if not seen:
            return
        fwd, right, up = cam
        camera = render3d.Camera(at=conn.pos, forward=fwd, up=up,
                                 width=w, height=h, half_fov=HALF_FOV)
        # The star always, whatever its angular size. From the system edge
        # it is a tenth of a degree — a quarter of the Sun from Earth — and
        # still by orders of magnitude the brightest thing in the sky. It has
        # no business being a background dot, which is what treating it like
        # every other object made it.
        for sight in seen:
            if sight.kind == "star":
                self._star(p, camera, sight)

        for sight in sky_sim.points(seen):
            if sight.kind == "star":
                continue
            at = camera.project(sight.at)
            if at is None:
                continue
            point, _ahead = at
            if not (0 <= point.x() < w and 0 <= point.y() < h):
                continue
            # Brighter than the field behind it, and its own colour, so a
            # world reads as a world rather than as another star.
            tint = QColor(theme.tint(sight.tint)
                          if sight.tint in theme.TINTS else theme.INK)
            size = 2.6 if sight.kind == "body" else 1.6
            p.setBrush(tint)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(point, size, size)

        hard = self.glare(conn)
        for sight in sky_sim.shapes(seen):
            if sight.kind == "star":
                continue
            if sight.kind == "body":
                mesh = worlds3d.mesh_for(sight.look)
            else:
                mesh = models3d.SHIPYARD
            # Rings first when they are behind, so the world occludes them,
            # then again in front. Two passes is cheaper than sorting a flat
            # annulus against a sphere it interpenetrates.
            if sight.ringed:
                render3d.draw(p, camera, worlds3d.RINGS_MESH, sight.at,
                              sight.radius_km, self.light(conn), tilt=0.42,
                              glare=hard)
            render3d.draw(p, camera, mesh, sight.at, sight.radius_km,
                          self.light(conn), tilt=0.42, glare=hard)
            if sight.ringed:
                render3d.draw(p, camera, worlds3d.RINGS_FRONT, sight.at,
                              sight.radius_km, self.light(conn), tilt=0.42,
                              glare=hard)

    def _star(self, p: QPainter, camera, sight) -> None:
        """The star: a disc that is its own light, and a corona."""
        at = camera.project(sight.at)
        if at is None:
            return
        point, _ahead = at
        # Never smaller than a bright point: a star at four AU is a tenth of
        # a degree and would round to nothing.
        radius = max(2.4, render3d.screen_radius(camera, sight.range_km,
                                                 sight.radius_km))
        # The disc is `tint` — the core — and the corona is `halo`. Two
        # colours per class have been in `data/starclasses.py` since it was
        # written and the corona was being drawn in the core's colour, so the
        # second one did nothing: an A-type's blue-white corona and an M
        # dwarf's dull red one were each just their own disc, blurred.
        tint = QColor(sight.tint if sight.tint.startswith("#") else "#ffd9a0")
        crown = QColor(sight.halo if sight.halo.startswith("#") else sight.tint
                       if sight.tint.startswith("#") else "#e07a5f")
        glow = QRadialGradient(point, radius * 5.0)
        glow.setColorAt(0.0, QColor(255, 255, 240, 210))
        glow.setColorAt(0.18, QColor(crown.red(), crown.green(), crown.blue(),
                                     150))
        glow.setColorAt(1.0, QColor(crown.red(), crown.green(), crown.blue(),
                                    0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(point, radius * 5.0, radius * 5.0)
        p.setBrush(QColor(255, 253, 244))
        p.drawEllipse(point, radius, radius)

    def _model_for(self, conn):
        """Which mesh, and how it is oriented, for what is out there."""
        kind = conn.target.kind
        if kind == "body":
            # Its own kind: an ice moon, an ocean and a gas giant should not
            # be the same grey ball with different labels over them.
            look = getattr(conn.target, "look", "") or "rocky"
            return worlds3d.mesh_for(look), conn.elapsed / 5400.0
        if kind == "anchorage":
            if getattr(conn.target, "berth", "") == "gate":
                return models3d.GATE, conn.elapsed / 2600.0
            return models3d.SHIPYARD, conn.elapsed / 900.0
        if kind == "hull":
            return models3d.HULL, 0.0
        return models3d.GATE, conn.elapsed / 1400.0

    def _target(self, p: QPainter, conn, cam, w: int, h: int) -> None:
        """The thing being approached, as a lit solid at its real size.

        It used to be a flat disc with a gradient behind it, which reads as a
        distant object at twelve kilometres and as a flat disc at six hundred
        metres — a poor thing to watch while berthing a hull against a yard.
        """
        r_km = conn.range_km
        if r_km <= 1e-9 or conn.target.radius_km <= 0:
            return          # station keeping: there is no target, only sky
        fwd, right, up = cam
        # The renderer works in the target's own frame, where the ship is at
        # `conn.pos` and the thing being approached is at the origin.
        camera = render3d.Camera(at=conn.pos, forward=fwd, up=up,
                                 width=w, height=h, half_fov=HALF_FOV)
        radius = render3d.screen_radius(camera, r_km, conn.target.radius_km)
        mesh, spin = self._model_for(conn)

        # Far enough off to be a point of light rather than a shape.
        if radius < 2.2:
            at = project(_unit([-c for c in conn.pos]), cam, w, h)
            if at is None:
                return
            tint = QColor(theme.tint("chloro") if conn.target.kind == "body"
                          else theme.tint("lumen"))
            glow = QRadialGradient(QPointF(at[0], at[1]), 6.0)
            glow.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), 220))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(at[0], at[1]), 6.0, 6.0)
        else:
            # A ringed world in two halves, the same as the sky does it: the
            # far arc before the world and the near arc after, so the world
            # occludes the part of the ring passing behind it. Painter's
            # algorithm has no other answer to a flat annulus that
            # interpenetrates the sphere it circles.
            ringed = getattr(conn.target, "ringed", False)
            hard = self.glare(conn)
            if ringed:
                render3d.draw(p, camera, worlds3d.RINGS_MESH, (0.0, 0.0, 0.0),
                              conn.target.radius_km, self.light(conn),
                              spin=spin, tilt=0.35, glare=hard)
            render3d.draw(p, camera, mesh, (0.0, 0.0, 0.0),
                          conn.target.radius_km, self.light(conn), spin=spin,
                          tilt=0.35, glare=hard)
            if ringed:
                render3d.draw(p, camera, worlds3d.RINGS_FRONT, (0.0, 0.0, 0.0),
                              conn.target.radius_km, self.light(conn),
                              spin=spin, tilt=0.35, glare=hard)

        if self.compact:
            return
        sx, sy = w * 0.5, h * 0.5
        toward = project(_unit([-c for c in conn.pos]), cam, w, h)
        if toward is not None:
            sx, sy = toward[0], toward[1]
        # A bracket and the range, so the main screen is readable on its own.
        box = max(radius + 14, 18)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.tint("warn")), 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(sx - box, sy - box, box * 2, box * 2))
        p.setPen(QColor(theme.INK2))
        p.setFont(QFont(theme.mono_family(), 9))
        span = (f"{r_km * 1000:,.0f} m" if r_km < 2 else f"{r_km:,.1f} km")
        p.drawText(QPointF(sx - box, sy - box - 6),
                   f"{conn.target.name} · {span}")

    def glare(self, conn) -> float:
        """How hard this star lights everything, against the Sun.

        The *fact* is `conn.star_lum`, recorded when the approach opens the
        same way `star_dir` is. How much of it a screen can show is this
        window's decision, and the answer is not "all of it": the raw range is
        five hundred to one — 0.04 for an M dwarf against 22 for an A-type —
        and a display has about four stops before everything is either black
        or white. A fourth root puts that into a factor of about four and a
        half, which reads as a real difference and still leaves a red dwarf's
        worlds legible.
        """
        lum = max(1e-4, float(getattr(conn, "star_lum", 1.0) or 1.0))
        return max(GLARE_FLOOR, min(GLARE_CEILING, lum ** GLARE_ROOT))

    def light(self, conn) -> tuple:
        """Which way the starlight travels, in the target's frame.

        The star is at the system's centre and the target is somewhere out
        from it, so light falls along the target's own position vector. That
        one line is what gives a world a terminator on the correct side.
        """
        aim = getattr(conn, "star_dir", None)
        if aim:
            return render3d.unit(aim)
        return render3d.unit((-0.45, -0.8, -0.35))

    def _frame(self, p: QPainter, name: str, w: int, h: int) -> None:
        """The camera's own furniture: a border, its name, and a reticle."""
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.LINE), 1))
        p.drawRect(0, 0, w - 1, h - 1)

        cx, cy = w / 2, h / 2
        arm = 7 if self.compact else 12
        p.setPen(QPen(QColor(90, 130, 112, 170), 1))
        p.drawLine(QPointF(cx - arm, cy), QPointF(cx - arm * 0.35, cy))
        p.drawLine(QPointF(cx + arm * 0.35, cy), QPointF(cx + arm, cy))
        p.drawLine(QPointF(cx, cy - arm), QPointF(cx, cy - arm * 0.35))
        p.drawLine(QPointF(cx, cy + arm * 0.35), QPointF(cx, cy + arm))

        p.setPen(QColor(theme.INK3))
        p.setFont(QFont(theme.mono_family(), 8 if self.compact else 9))
        p.drawText(QPointF(6, 13), name.upper())
