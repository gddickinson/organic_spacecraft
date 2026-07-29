"""The plotting board's canvas: a system seen obliquely, with tracks on it.

The helm's system view is a flat overhead chart at a fixed scale. This is the
same system with the controls a navigator actually wants — zoom, pan, and a
tilt that lays the orbital plane over so the geometry reads as a place rather
than a diagram — plus the thing a flat chart cannot show at all: **time**.

Every contact here has a position that is a function of the day, so each can
be drawn as three things at once:

* where it **has been**, back along its track;
* where it **is**;
* where it **will be**, out to the horizon, and specifically where it will be
  on the arrival date being considered.

That last one is the whole point. Plotting an intercept against where a hull
is *now* aims at empty space; against where it will be on the day you get
there, it aims at the hull.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from ..sim import flight
from ..sim import track as track_sim
from . import theme

#: Zoom limits, in pixels per AU.
MIN_SCALE, MAX_SCALE = 3.0, 900.0

#: How far the plane can be laid over, in radians. Face-on to nearly edge-on.
MAX_TILT = math.radians(82.0)

GLYPH = {"star": "★", "body": "●", "anchorage": "▣", "hull": "◆", "point": "✛"}


class PlotCanvas(QWidget):
    """A system, drawn obliquely, with history and prediction on it."""

    picked = pyqtSignal(str)

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.system = game.system
        self.scale = 46.0
        self.centre = [0.0, 0.0]
        self.tilt = math.radians(34.0)
        self.spin = 0.0
        self.selected: str | None = None
        self.tracked: set = set()
        self.arrive_day: float | None = None
        self.plotted: dict | None = None
        self.show_orbits = True
        self._drag = None
        self._hits: list = []
        self.setMinimumSize(420, 360)
        self.setMouseTracking(True)

    # ── the projection ─────────────────────────────────────────────────────

    def to_screen(self, x: float, y: float, z: float = 0.0) -> QPointF:
        """AU in the system's plane to a point on the widget.

        Spin about the pole, then lay the plane over by the tilt. The z axis
        is kept because the orbits are flat but the *tracks* need somewhere to
        stand up out of the plane when a contact is above or below it.
        """
        dx, dy = x - self.centre[0], y - self.centre[1]
        c, s = math.cos(self.spin), math.sin(self.spin)
        rx, ry = dx * c - dy * s, dx * s + dy * c
        ct, st = math.cos(self.tilt), math.sin(self.tilt)
        sx = rx * self.scale
        sy = (ry * ct - z * st) * self.scale
        return QPointF(self.width() / 2 + sx, self.height() / 2 + sy)

    def from_screen(self, px: float, py: float) -> tuple[float, float]:
        """Back the other way, onto the orbital plane (z = 0)."""
        sx = (px - self.width() / 2) / self.scale
        sy = (py - self.height() / 2) / self.scale
        ct = math.cos(self.tilt) or 1e-6
        rx, ry = sx, sy / ct
        c, s = math.cos(-self.spin), math.sin(-self.spin)
        return (rx * c - ry * s + self.centre[0],
                rx * s + ry * c + self.centre[1])

    # ── controls ───────────────────────────────────────────────────────────

    def wheelEvent(self, event) -> None:
        step = 1.0015 ** event.angleDelta().y()
        self.set_scale(self.scale * step)

    def set_scale(self, value: float) -> None:
        self.scale = max(MIN_SCALE, min(MAX_SCALE, value))
        self.update()

    def set_tilt(self, radians: float) -> None:
        self.tilt = max(0.0, min(MAX_TILT, radians))
        self.update()

    def set_spin(self, radians: float) -> None:
        self.spin = radians % math.tau
        self.update()

    def frame_all(self) -> None:
        """Zoom and centre so the whole system fits."""
        radii = [flight.orbit_radius(b) for b in self.system.bodies] or [1.0]
        span = max(radii) * 1.25
        self.centre = [0.0, 0.0]
        smallest = min(self.width(), self.height()) or 400
        self.set_scale(smallest * 0.5 / max(0.2, span))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._drag = (event.position().x(), event.position().y())
            return
        where = event.position()
        best, gap = None, 15.0
        for cid, at in self._hits:
            d = math.dist((at.x(), at.y()), (where.x(), where.y()))
            if d < gap:
                best, gap = cid, d
        if best is not None:
            self.selected = best
            self.picked.emit(best)
        else:
            # Empty space is a destination too: the captain asked to be able
            # to name a position in the system and go to it.
            x, y = self.from_screen(where.x(), where.y())
            self.selected = f"point:{x:.4f}:{y:.4f}"
            self.picked.emit(self.selected)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self._drag is None:
            return
        px, py = event.position().x(), event.position().y()
        ox, oy = self._drag
        ax, ay = self.from_screen(ox, oy)
        bx, by = self.from_screen(px, py)
        self.centre[0] -= bx - ax
        self.centre[1] -= by - ay
        self._drag = (px, py)
        self.update()

    def mouseReleaseEvent(self, _event) -> None:
        self._drag = None

    # ── painting ───────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#050d0b"))
        self._hits = []

        contacts = {c.id: c for c in track_sim.contacts(self.game, self.system)}
        if self.show_orbits:
            self._orbits(p)
        self._tracks(p, contacts)
        self._plot(p)
        self._marks(p, contacts)
        self._ship(p)
        self._scalebar(p)
        p.end()

    def _orbits(self, p: QPainter) -> None:
        p.setPen(QPen(QColor(38, 62, 52), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for body in self.system.bodies:
            r = flight.orbit_radius(body)
            ring = QPolygonF([
                self.to_screen(r * math.cos(t * math.tau / 72),
                               r * math.sin(t * math.tau / 72))
                for t in range(73)])
            p.drawPolygon(ring)

    def _tracks(self, p: QPainter, contacts: dict) -> None:
        """Where the tracked things have been and where they are going."""
        for cid in sorted(self.tracked | ({self.selected} if self.selected
                                          else set())):
            contact = contacts.get(cid) or self._point(cid)
            if contact is None or contact.kind == "point":
                continue
            tint = QColor(theme.tint(contact.tint) if contact.tint in theme.TINTS
                          else theme.INK2)

            past = track_sim.history(self.game, contact, 120, 26, self.system)
            pen = QPen(QColor(tint.red(), tint.green(), tint.blue(), 90), 1.1)
            pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPolyline(QPolygonF([self.to_screen(x, y) for x, y in past]))

            ahead = track_sim.forecast(self.game, contact, track_sim.HORIZON,
                                       30, self.system)
            faded = int(70 + 110 * track_sim.confidence(
                self.game, contact, self.game.day + track_sim.HORIZON,
                self.system))
            pen = QPen(QColor(tint.red(), tint.green(), tint.blue(), faded), 1.3)
            pen.setStyle(Qt.PenStyle.DotLine)
            p.setPen(pen)
            p.drawPolyline(QPolygonF([self.to_screen(x, y) for x, y in ahead]))

            # Ticks along the forecast, so the track carries dates and not
            # merely a direction.
            p.setPen(QPen(QColor(tint.red(), tint.green(), tint.blue(), 150), 1))
            for step in range(1, 7):
                day = self.game.day + track_sim.HORIZON * step / 6
                x, y = track_sim.at(self.game, contact, day, self.system)
                at = self.to_screen(x, y)
                p.drawLine(QPointF(at.x() - 2, at.y()),
                           QPointF(at.x() + 2, at.y()))

            if self.arrive_day is not None:
                x, y = track_sim.at(self.game, contact, self.arrive_day,
                                    self.system)
                at = self.to_screen(x, y)
                p.setPen(QPen(QColor(theme.tint("warn")), 1.4))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(at, 7, 7)
                p.setFont(QFont(theme.mono_family(), 8))
                text = f"day {self.arrive_day:,.0f}"
                # The interesting dates are often near the edge of the plot,
                # which is exactly where a label hung off the right runs out
                # of canvas — so it goes on whichever side has room.
                wide = 8 + 6 * len(text)
                left = (at.x() + 10 if at.x() + 10 + wide < self.width()
                        else at.x() - 10 - wide)
                p.drawText(QPointF(left, at.y() - 6), text)

    def _plot(self, p: QPainter) -> None:
        """The leg itself, bent round the star exactly as `flight` bends it."""
        if not self.plotted or not self.plotted.get("legs"):
            return
        sx, sy = flight.ship_position(self.game)
        points = [self.to_screen(sx, sy)]
        for leg in self.plotted["legs"]:
            points.append(self.to_screen(leg[0], leg[1]))
        pen = QPen(QColor(theme.tint("warn")), 1.6)
        if not self.plotted.get("feasible", True):
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolyline(QPolygonF(points))

    def _marks(self, p: QPainter, contacts: dict) -> None:
        p.setFont(QFont(theme.mono_family(), 9))
        for cid, contact in contacts.items():
            x, y = track_sim.at(self.game, contact, self.game.day, self.system)
            at = self.to_screen(x, y)
            self._hits.append((cid, at))
            tint = QColor(theme.tint(contact.tint) if contact.tint in theme.TINTS
                          else theme.INK2)
            chosen = cid == self.selected
            size = {"star": 7.0, "body": 4.5, "anchorage": 3.6,
                    "hull": 3.0}.get(contact.kind, 3.0)
            p.setBrush(tint)
            p.setPen(QPen(QColor(theme.INK if chosen else theme.LINE), 1))
            p.drawEllipse(at, size, size)
            if chosen:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(theme.INK), 1.3))
                p.drawEllipse(at, size + 6, size + 6)
            if cid in self.tracked:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(theme.tint("lumen")), 1))
                p.drawRect(int(at.x() - size - 4), int(at.y() - size - 4),
                           int(size * 2 + 8), int(size * 2 + 8))
            if chosen or contact.kind in ("star", "body", "anchorage") \
                    or cid in self.tracked:
                p.setPen(QColor(theme.INK2 if chosen else theme.INK3))
                p.drawText(QPointF(at.x() + size + 5, at.y() + 4), contact.name)

        if self.selected and self.selected.startswith("point:"):
            contact = self._point(self.selected)
            if contact is not None:
                at = self.to_screen(*contact.at_xy)
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(QColor(theme.tint("warn")), 1.3))
                p.drawLine(QPointF(at.x() - 7, at.y()),
                           QPointF(at.x() + 7, at.y()))
                p.drawLine(QPointF(at.x(), at.y() - 7),
                           QPointF(at.x(), at.y() + 7))

    def _ship(self, p: QPainter) -> None:
        x, y = flight.ship_position(self.game)
        at = self.to_screen(x, y)
        p.setBrush(QColor(theme.INK))
        p.setPen(QPen(QColor(theme.tint("lumen")), 1.4))
        p.drawEllipse(at, 4, 4)
        p.setFont(QFont(theme.mono_family(), 9))
        p.setPen(QColor(theme.INK2))
        p.drawText(QPointF(at.x() + 8, at.y() - 6), self.game.ship.name)

    def _scalebar(self, p: QPainter) -> None:
        """A bar and its length, because a zoom with no scale is a picture."""
        want = self.width() * 0.18
        au = 10.0 ** math.floor(math.log10(max(1e-6, want / self.scale)))
        for step in (5.0, 2.0, 1.0):
            if au * step * self.scale <= want:
                au *= step
                break
        px = au * self.scale
        y = self.height() - 18
        p.setPen(QPen(QColor(theme.INK3), 1))
        p.drawLine(QPointF(16, y), QPointF(16 + px, y))
        p.drawLine(QPointF(16, y - 3), QPointF(16, y + 3))
        p.drawLine(QPointF(16 + px, y - 3), QPointF(16 + px, y + 3))
        p.setFont(QFont(theme.mono_family(), 8))
        text = f"{au:g} AU" if au >= 0.01 else f"{au:.3f} AU"
        p.drawText(QPointF(16, y - 6), text)
        p.drawText(QPointF(16, 16),
                   f"day {self.game.day:,}  ·  tilt "
                   f"{math.degrees(self.tilt):.0f}°  ·  "
                   f"{self.scale:.0f} px/AU")

    # ── helpers ────────────────────────────────────────────────────────────

    def _point(self, cid: str | None):
        """The bare position contact encoded in a `point:x:y` id."""
        if not cid or not cid.startswith("point:"):
            return None
        try:
            _tag, x, y = cid.split(":")
            return track_sim.Contact(id=cid, name="Plotted position",
                                     kind="point", tint="warn",
                                     detail="A position in the system.",
                                     at_xy=(float(x), float(y)))
        except ValueError:
            return None

    def contact_for(self, cid: str | None):
        if cid is None:
            return None
        if cid.startswith("point:"):
            return self._point(cid)
        for c in track_sim.contacts(self.game, self.system):
            if c.id == cid:
                return c
        return None
