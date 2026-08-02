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
from ..data import models3d, surfaces, worlds3d
from ..sim import conn as conn_sim
from . import painting, render3d, spheres, stars3d, theme, viewport_mark
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


def _rotate(vec, heading: float) -> tuple:
    c, s = math.cos(heading), math.sin(heading)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def _cross(a, b) -> tuple:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])




def _detail(look: str, name: str):
    """The ground-texture hook for one body, or None where there is no kind.

    A closure rather than a list, because the lattice `surfaces.detail_near`
    walks depends on where the camera is looking and how much ground the frame
    holds — neither of which this module knows until the world is projected.
    """
    if not look:
        return None
    return lambda lat, lon, span: surfaces.detail_near(look, name, lat, lon,
                                                       span)


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

        self._stars(p, cam, w, h)
        if conn is not None:
            self._sky(p, conn, cam, w, h)
            self._target(p, conn, cam, w, h)
        viewport_mark.draw_sights(p, self.sights, project, cam, w, h)
        viewport_mark.draw(p, self.mark, project, cam, w, h)
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

    def _model_for(self, conn, across: float = 0.0):
        """Which mesh, and how it is oriented, for what is out there.

        `None` for a world, which is painted rather than built: see
        `ui/spheres.py`. `across` is kept because callers pass it and a future
        model may want to know how big it will be.
        """
        kind = conn.target.kind
        if kind == "body":
            # A world is not drawn from a mesh any more — `_target` sends it to
            # `ui/spheres.py`. The spin is still wanted, because the surface has
            # to turn, and a world keeps the shallow tilt it always had.
            return None, conn.elapsed / 5400.0, 0.35
        # Through the same door the sky uses, so the shape you picked out at
        # range is the shape — and the attitude — you come alongside.
        if kind == "anchorage":
            # The angle the *docking* is using, so the fitting a pilot is
            # flying at is under the fitting they can see.
            from ..sim import moorings
            shown = models3d.present("anchorage",
                                     getattr(conn.target, "berth", ""),
                                     conn.elapsed,
                                     spin=moorings.spin_at(conn.target,
                                                           conn.elapsed))
        elif kind == "hull":
            shown = models3d.present("hull",
                                     getattr(conn.target, "errand", ""),
                                     conn.elapsed)
        else:
            shown = models3d.present("anchorage", "gate", conn.elapsed)
        return shown["mesh"], shown["spin"], shown["tilt"]

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
        mesh, spin, tilt = self._model_for(conn, radius)

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
                              spin=spin, tilt=tilt, glare=hard)
            if conn.target.kind == "body":
                look = getattr(conn.target, "look", "") or "rocky"
                spheres.draw(p, camera, worlds3d.paint_for(look),
                    (0.0, 0.0, 0.0), conn.target.radius_km, self.light(conn),
                    spin=spin, tilt=tilt, glare=hard,
                    features=surfaces.features_for(
                        look, getattr(conn.target, "name", "")),
                    stretch=surfaces.stretch_for(look),
                    detail=_detail(look, getattr(conn.target, "name", "")))
            else:
                render3d.draw(p, camera, mesh, (0.0, 0.0, 0.0),
                              conn.target.radius_km, self.light(conn),
                              spin=spin, tilt=tilt, glare=hard)
                self._boom(p, camera, conn)
            if ringed:
                render3d.draw(p, camera, worlds3d.RINGS_FRONT, (0.0, 0.0, 0.0),
                              conn.target.radius_km, self.light(conn),
                              spin=spin, tilt=tilt, glare=hard)

        if self.compact:
            return
        # **Only on the camera that can actually see it.** `project` returns
        # None for a direction behind the lens, and this used to fall back to
        # the centre of the frame — so berthing a hull at 998 m drew a dashed
        # bracket labelled "Fleet Hub · 998 m" in the middle of *all six*
        # feeds, with the hub visible in exactly one of them. On the dorsal
        # camera the bracket sat on top of a planet and named it as the quay.
        #
        # Found by rendering the six feeds as a contact sheet and looking at
        # it. No figure could have shown it: every number on every feed was
        # right, and five of the six pictures were a lie about where the thing
        # was. A reticle is a claim about direction, so it may only be drawn
        # where the direction lands.
        toward = project(_unit([-c for c in conn.pos]), cam, w, h)
        if toward is None:
            return
        sx, sy = toward[0], toward[1]
        # A bracket and the range, so the main screen is readable on its own.
        # **Capped to the frame**: at a standoff berth the hull holds station
        # a few tens of metres off a structure that fills the view, and a
        # bracket sized to its screen radius came out wider than the window —
        # a dashed line straight across the picture, marking nothing.
        box = max(min(radius + 14, min(w, h) * 0.42), 18)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.tint("warn")), 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(sx - box, sy - box, box * 2, box * 2))
        p.setPen(QColor(theme.INK2))
        p.setFont(QFont(theme.mono_family(), 9))
        span = (f"{r_km * 1000:,.0f} m" if r_km < 2 else f"{r_km:,.1f} km")
        p.drawText(QPointF(sx - box, sy - box - 6),
                   f"{conn.target.name} · {span}")

    def _boom(self, p: QPainter, camera, conn) -> None:
        """The arm coming out to take the ship, at a standoff berth.

        **Drawn because it is real.** `sim/moorings.boom_step` runs it out
        while the hull holds station and back in when it drifts, and a
        manoeuvre whose whole content is *hold still while this happens*
        cannot be flown off a percentage in a table. It reaches from the
        gantry it is hinged on toward the berth, as far as it has got.
        """
        from ..data.berths3d import hinge_points
        from ..sim import moorings

        # Belt and braces, knowingly: `moorings.boom_step` already zeroes the
        # boom at anything that is not a standoff, so removing this line draws
        # nothing anywhere and no check moves. Kept because the window should
        # not depend on the sim's housekeeping to avoid drawing a gantry arm
        # on a quay that has none.
        if moorings.sort_of(conn.target) != "standoff":
            return
        out = float(getattr(conn, "boom", 0.0) or 0.0)
        if out <= 0.0:
            return
        want = getattr(conn, "berth", "")
        sort = getattr(conn.target, "berth", "") or ""
        scale = float(conn.target.radius_km or 0.0)
        spin = moorings.spin_at(conn.target, conn.elapsed)
        # Through the model's *whole* rotation, the same door the mesh and the
        # berths go through. Rotating the hinge by spin alone put the arm's
        # root off the structure it is bolted to by the tilt, which is the
        # fault `models3d.place` exists to make impossible.
        tilt = models3d.attitude_of("anchorage", sort)[1]
        berths = dict(moorings.points(conn.target, spin))
        for name, at in hinge_points(sort):
            if name != want or name not in berths:
                continue
            hinge = render3d.place(tuple(c * scale for c in at), spin, tilt)
            far = berths[name]
            tip = tuple(h + (f - h) * out for h, f in zip(hinge, far))
            here, there = camera.project(hinge), camera.project(tip)
            if here is None or there is None:
                return
            tint = QColor(theme.tint("lumen" if out >= 1.0 else "amber"))
            p.setPen(QPen(tint, 2.4 if out >= 1.0 else 1.8))
            p.drawLine(here[0], there[0])
            p.setBrush(tint)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(there[0], 3.2, 3.2)
            return

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
