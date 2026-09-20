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

This file draws the sky; the target itself — its solid, its bracket and the
boom coming out to take the ship — is `ui/viewport_target.py`, and the aids on
the glass are `ui/viewport_hud.py`.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ..core.rng import RNG
from ..data import models3d, surfaces, worlds3d
from ..sim import conn as conn_sim
from . import (effect_paint, effects, painting, render3d, spheres, stars3d,
               theme, viewport_hud, viewport_mark, viewport_target)
from .viewport_target import _detail
from .viewport_math import HALF_FOV, _unit, project

#: Half the field of view, in radians. A wide-ish lens: enough to keep a
#: target in frame while manoeuvring, tight enough that motion reads.
#: The floor and ceiling on how bright a star may make the picture, and the
#: root that compresses the raw luminosity into them. A fourth root turns a
#: five-hundred-fold range into about four and a half, which is what a screen
#: can actually show; the floor keeps a red dwarf's worlds readable and the
#: ceiling keeps an A-type's from being a white rectangle.
GLARE_FLOOR, GLARE_CEILING, GLARE_ROOT = 0.55, 1.45, 0.25



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


def best_view(conn, bearing) -> str:
    """Which of the six cameras a given bearing is most nearly down.

    The answer to "which window did that happen in", which the conn needs and
    nothing could answer: a hull struck a Fleet Hub at 55 m/s with the nose
    180° off, so the *aft* camera held the whole event and the main screen —
    which is what the player was looking at — showed a starfield.

    The most-forward camera, by the dot product with each one's axis. Never
    empty: the six axes cover the sphere, so something is always best.
    """
    best, score = conn_sim.VIEWS[0][0], -2.0
    for view_id, _label, vec in conn_sim.VIEWS:
        fwd, _right, _up = basis(vec, conn)
        ahead = sum(a * b for a, b in zip(bearing, fwd))
        if ahead > score:
            best, score = view_id, ahead
    return best


def _rotate(vec, heading: float) -> tuple:
    c, s = math.cos(heading), math.sin(heading)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def _cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


class Viewport(painting.Painted, QWidget):
    #: `(vector, name)` a course is laid on — see `ui/viewport_mark`.
    mark = None
    #: `(vector, name, near)` for quays and hulls worth naming out there.
    sights = ()

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

    def draw(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#04080b"))

        conn = self.conn
        _vid, label_text, vec = self.view
        cam = basis(vec, conn)

        # **The blow moves the camera, not the furniture.** A shake applied
        # to the whole widget would throw the label and the border about with
        # it, which reads as the *window* being broken rather than the ship
        # being struck. Everything out of the window rides on the offset;
        # the frame, the effects and the words are painted true.
        shift_x, shift_y = effects.shake()
        p.save()
        if shift_x or shift_y:
            p.translate(shift_x, shift_y)
        self._stars(p, cam, w, h)
        taken = []
        if conn is not None:
            self._sky(p, conn, cam, w, h)
            viewport_hud.draw(p, conn, cam, w, h)
            spot = viewport_target.draw(self, p, conn, cam, w, h)
            if spot is not None:
                taken.append(spot)
        viewport_mark.draw_sights(p, self.sights, project, cam, w, h, taken)
        viewport_mark.draw(p, self.mark, project, cam, w, h)
        p.restore()
        effect_paint.over(p, conn, cam, w, h)
        self._frame(p, label_text, w, h)

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
                # A world is drawn as a lit disc rather than as a mesh — see
                # `ui/spheres.py`. No faces, so no facets at any size, and about
                # a quarter of the cost of the fine mesh it replaces.
                if sight.ringed:
                    render3d.draw(p, camera, worlds3d.RINGS_MESH, sight.at,
                                  sight.radius_km, self.light(conn), tilt=0.42,
                                  glare=hard)
                spheres.draw(p, camera, worlds3d.paint_for(sight.look),
                             sight.at, sight.radius_km, self.light(conn),
                             tilt=0.42, glare=hard,
                             features=surfaces.features_for(sight.look,
                                                            sight.name),
                             stretch=surfaces.stretch_for(sight.look),
                             detail=_detail(sight.look, sight.name))
                if sight.ringed:
                    render3d.draw(p, camera, worlds3d.RINGS_FRONT, sight.at,
                                  sight.radius_km, self.light(conn), tilt=0.42,
                                  glare=hard)
                continue
            # Anything that is not a world is a mesh: it is not a sphere, and
            # the disc trick says nothing useful about a box with a spine
            # through it. *Which* mesh comes from what the thing is — a quay,
            # a Fleet Hub, a gate, a courier, a hull with no transponder —
            # rather than from one shipyard standing in for all of them.
            shown = models3d.present(sight.kind, sight.look)
            render3d.draw(p, camera, shown["mesh"], sight.at,
                          sight.radius_km, self.light(conn),
                          spin=shown["spin"], tilt=shown["tilt"], glare=hard)

    def _star(self, p: QPainter, camera, sight) -> None:
        """The star: its own class's disc, its own corona, and its own kind.

        `ui/stars3d.py` holds it. It was nine lines here that drew every one of
        the nine classes as the same off-white circle — the `tint` worked out
        from the class was assigned and never used — so a black hole came out
        brighter than an A-type.
        """
        stars3d.draw(p, camera, sight)

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
