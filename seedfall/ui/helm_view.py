"""The helm — plotting a transfer inside a system.

A jump drops you at the system edge. Everything worth looking at is somewhere
else and moving, so getting alongside it is a decision: how much reaction mass
are you willing to spend to save how many days.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.util import duration, num
from ..sim import flight
from ..world.planets import BODY_KINDS
from . import theme
from .widgets import Panel, Pill, View, button, label, mono_label, note, spacer


class OrbitChart(QWidget):
    """The system from above: orbits, bodies where they are today, the ship."""

    picked = pyqtSignal(int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setMinimumSize(460, 460)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _scale(self):
        span = flight.R_OUTER + 2.5
        side = min(self.width(), self.height())
        return (side / 2 - 16) / span, self.width() / 2, self.height() / 2

    def _to_screen(self, x: float, y: float) -> QPointF:
        s, cx, cy = self._scale()
        return QPointF(cx + x * s, cy + y * s)

    def mousePressEvent(self, ev):  # noqa: N802
        g = self.win.game
        best, bd = None, 18.0
        for i, b in enumerate(g.system.bodies):
            p = self._to_screen(*flight.position(b, g.day))
            d = math.hypot(p.x() - ev.position().x(), p.y() - ev.position().y())
            if d < bd:
                best, bd = i, d
        if best is not None:
            self.picked.emit(best)

    def paintEvent(self, _ev):  # noqa: N802
        g = self.win.game
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        s, cx, cy = self._scale()

        # the star
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(g.system.tint))
        p.drawEllipse(QPointF(cx, cy), 7, 7)

        for i, b in enumerate(g.system.bodies):
            r = flight.orbit_radius(b) * s
            p.setPen(QPen(QColor(150, 196, 176, 40), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

            pos = self._to_screen(*flight.position(b, g.day))
            tint = QColor(theme.tint(BODY_KINDS[b.kind][1]))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tint)
            p.drawEllipse(pos, 5, 5)
            if b.id == g.orbit_body:
                p.setPen(QPen(QColor(theme.tint("chloro")), 1.6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(pos, 12, 12)

            p.setFont(QFont(theme.mono_family(), 7))
            p.setPen(QColor(169, 194, 182, 190))
            p.drawText(QRectF(pos.x() - 55, pos.y() + 7, 110, 13),
                       Qt.AlignmentFlag.AlignHCenter, b.name.split()[-1])

        # the ship
        sx, sy = flight.ship_position(g)
        sp = self._to_screen(sx, sy)
        p.setPen(QPen(QColor(theme.tint("lumen")), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.drawLine(QPointF(sp.x() + dx * 9, sp.y() + dy * 5),
                       QPointF(sp.x() + dx * 9, sp.y() + dy * 9))
            p.drawLine(QPointF(sp.x() + dx * 9, sp.y() + dy * 9),
                       QPointF(sp.x() + dx * 5, sp.y() + dy * 9))
        p.end()


class HelmView(View):
    def __init__(self, win):
        super().__init__(win)
        self.target = 0

    def build(self) -> None:
        g = self.game
        here = flight.current_body(g)
        self.head(f"Helm — {g.system.name}",
                  f"Holding at {here.name}" if here
                  else "Holding at the system edge, under no acceleration")

        if self.target >= len(g.system.bodies):
            self.target = 0

        chart = OrbitChart(self.win)
        chart.picked.connect(self._pick)
        self.row(chart, self._plot(g))
        self.buttons(
            button("System overview", lambda: self.win.go("system")),
            button("Sector chart", lambda: self.win.go("map")))

    def _pick(self, index: int) -> None:
        self.target = index
        self.refresh()

    def _plot(self, g) -> Panel:
        body = g.system.bodies[self.target]
        at = body.id == g.orbit_body
        p = Panel(f"Transfer to {body.name}")
        p.add(note(BODY_KINDS[body.kind][0] + " · "
                   + f"{flight.orbit_radius(body):.1f} AU orbit · "
                   + f"period {duration(flight.period_days(body))}"))
        p.add_row("Range now", f"{flight.distance_to(g, body):.2f} AU")
        p.add_row("Reaction mass aboard",
                  f"{round(g.ship.cargo.get('volatiles', 0))} t")

        if at:
            p.add(spacer(4))
            p.add(Pill("alongside", "chloro"))
            p.add(note("You are already there. Survey, extract, dig or land from "
                       "the system screen."))
            return p

        p.add(spacer(4), mono_label("Burn profiles"))
        for q in flight.options(g, body):
            burn = q["burn"]
            afford = g.ship.cargo.get("volatiles", 0) >= q["fuel"]
            p.add(spacer(3))
            p.add(label(burn.name, "h3", "chloro" if afford else "dim"))
            p.add(note(burn.blurb))
            p.add_row(f"{q['days']} days · {q['fuel']:g} t",
                      f"risk {q['risk']:.0%}",
                      "warn" if q["risk"] > 0.15 else "")
            p.add_buttons(button(f"Burn — {q['days']} d",
                                 lambda _=False, bid=burn.id: self._burn(bid),
                                 kind="primary" if burn.id == "standard" else "",
                                 enabled=afford))
        p.add(spacer(4))
        p.add(note("Bodies move while you fly. A cheap transfer today may be a "
                   "dear one next season."))
        return p

    def _burn(self, burn_id: str) -> None:
        res = flight.travel_to(self.game, self.target, burn_id)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        if res.get("incident"):
            inc = res["incident"]
            self.win.dialog(inc["name"], [inc["text"], note(inc["detail"])],
                            [("Carry on", None)])
        self.win.refresh()
