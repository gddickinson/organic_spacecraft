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
from ..sim import conn as conn_sim
from . import theme

#: Half the field of view, in radians. A wide-ish lens: enough to keep a
#: target in frame while manoeuvring, tight enough that motion reads.
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


def basis(view_vec, heading: float) -> tuple:
    """Camera axes in the target's frame: forward, right, up."""
    fwd = _unit(_rotate(view_vec, heading))
    # Any vector not parallel to forward will do for the up reference; the
    # world's z only fails for the dorsal and ventral cameras, which then
    # take the ship's nose instead.
    ref = (0.0, 0.0, 1.0)
    if abs(fwd[2]) > 0.95:
        ref = _rotate((0.0, 1.0, 0.0), heading)
    right = _unit(_cross(fwd, ref))
    up = _unit(_cross(right, fwd))
    return fwd, right, up


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
        cam = basis(vec, getattr(conn, "heading", 0.0))

        self._stars(p, cam, w, h)
        if conn is not None:
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

    def _target(self, p: QPainter, conn, cam, w: int, h: int) -> None:
        """The thing being approached, at the angular size it really has."""
        r_km = conn.range_km
        if r_km <= 1e-9:
            return
        # From the ship to the target is the negative of the ship's position.
        toward = _unit([-c for c in conn.pos])
        at = project(toward, cam, w, h)
        if at is None:
            return
        sx, sy, _ahead = at
        focal = (min(w, h) * 0.5) / math.tan(HALF_FOV)
        # Angular radius, and the same lens the stars went through.
        ratio = min(0.999, conn.target.radius_km / max(r_km, 1e-9))
        radius = max(1.2, math.tan(math.asin(ratio)) * focal)

        tint = QColor(theme.tint("chloro") if conn.target.kind == "body"
                      else theme.tint("lumen"))
        if radius > 3:
            glow = QRadialGradient(QPointF(sx, sy), radius * 1.7)
            glow.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), 200))
            glow.setColorAt(0.55, QColor(tint.red(), tint.green(), tint.blue(), 90))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(sx, sy), radius * 1.7, radius * 1.7)
        p.setBrush(tint)
        p.setPen(QPen(QColor(theme.INK), 1))
        p.drawEllipse(QPointF(sx, sy), radius, radius)

        if self.compact:
            return
        # A bracket and the range, so the main screen is readable on its own.
        box = max(radius + 12, 18)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.tint("warn")), 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(sx - box, sy - box, box * 2, box * 2))
        p.setPen(QColor(theme.INK2))
        p.setFont(QFont(theme.mono_family(), 9))
        span = (f"{r_km * 1000:,.0f} m" if r_km < 2 else f"{r_km:,.1f} km")
        p.drawText(QPointF(sx - box, sy - box - 6),
                   f"{conn.target.name} · {span}")

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
