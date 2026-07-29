"""The helm — plotting a transfer inside a system.

A jump drops you at the system edge. Everything worth looking at is somewhere
else and moving, so getting alongside it is a decision: how much reaction mass
are you willing to spend to save how many days.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QPainter, QPainterPath, QPen)
from PyQt6.QtWidgets import QVBoxLayout, QSizePolicy, QWidget

from ..core.util import duration, num
from ..sim import anchorage as anchorage_sim
from ..sim import flight
from ..sim import traffic as traffic_sim
from ..sim import transit as transit_sim
from ..world.planets import BODY_KINDS
from . import theme
from .widgets import (Panel, Pill, TabBar, View, button, label, mono_label,
                      note, spacer)


class OrbitChart(QWidget):
    """The system from above: orbits, bodies where they are today, the ship."""

    picked = pyqtSignal(int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.target = 0
        self.burn = "standard"
        self.setMinimumSize(460, 460)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def _scale(self):
        """Fit whatever the system actually holds — comets orbit well outside
        the planets, and a chart that crops them is a chart that lies."""
        g = self.win.game
        span = max([flight.orbit_radius(b) for b in g.system.bodies]
                   + [flight.ARRIVAL_RADIUS]) * 1.08 + 0.4
        side = min(self.width(), self.height())
        return (side / 2 - 22) / span, self.width() / 2, self.height() / 2

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

    def _draw_course(self, p, g, s, cx, cy) -> None:
        """The leg you are about to fly, and where the target will be when you
        arrive. The gap between a body's mark and its aim point is the whole
        argument for burning hard rather than coasting."""
        if not (0 <= self.target < len(g.system.bodies)):
            return
        body = g.system.bodies[self.target]
        if body.id == g.orbit_body:
            return
        q = flight.intercept(g, body, self.burn)
        ship = self._to_screen(*flight.ship_position(g))
        aim = self._to_screen(*q["aim"])
        now = self._to_screen(*flight.position(body, g.day))

        # the star's heat zone, if the leg goes anywhere near it
        if q["risk"] > q["burn"].risk + 0.005:
            p.setPen(QPen(QColor(214, 138, 92, 70), 1, Qt.PenStyle.DotLine))
            p.setBrush(QColor(214, 138, 92, 16))
            p.drawEllipse(QPointF(cx, cy), 1.2 * s, 1.2 * s)

        # where the target travels while you are in flight
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(230, 172, 109, 150), 2.0))
        arc = QPainterPath()
        for step in range(13):
            day = g.day + q["days"] * step / 12
            pt = self._to_screen(*flight.position(body, day))
            arc.moveTo(pt) if step == 0 else arc.lineTo(pt)
        p.drawPath(arc)

        # the course as actually flown — bent around the star if need be
        p.setPen(QPen(QColor(theme.tint("lumen")), 1.5, Qt.PenStyle.DashLine))
        course = QPainterPath()
        for step, (lx, ly) in enumerate(q["legs"]):
            pt = self._to_screen(lx, ly)
            course.moveTo(pt) if step == 0 else course.lineTo(pt)
        p.drawPath(course)
        p.setPen(QPen(QColor(theme.tint("lumen")), 1.6))
        p.drawEllipse(aim, 8, 8)
        p.drawLine(QPointF(aim.x() - 12, aim.y()), QPointF(aim.x() + 12, aim.y()))
        p.drawLine(QPointF(aim.x(), aim.y() - 12), QPointF(aim.x(), aim.y() + 12))

        mid = QPointF((ship.x() + aim.x()) / 2, (ship.y() + aim.y()) / 2)
        p.setFont(QFont(theme.mono_family(), 7))
        p.setPen(QColor(theme.tint("lumen")))
        p.drawText(QRectF(mid.x() - 60, mid.y() - 16, 120, 13),
                   Qt.AlignmentFlag.AlignHCenter,
                   f"{q['days']} d · {q['au']:.2f} AU")

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

        # Quays, hubs and your own holdings. They sit at the body they orbit,
        # so they are drawn just outside its marker rather than on top of it —
        # a chart that showed only the sun and the planets was the whole
        # complaint that started this.
        for place in anchorage_sim.in_system(g):
            if place.body_index >= len(g.system.bodies):
                continue
            body = g.system.bodies[place.body_index]
            at = self._to_screen(*flight.position(body, g.day))
            mark = QPointF(at.x() + 11, at.y() - 11)
            tint = QColor(theme.tint("lumen" if place.kind == "holding"
                                     else "chloro"))
            p.setPen(QPen(tint, 1.3))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if place.kind == "holding":
                p.drawEllipse(mark, 4.5, 4.5)
            else:
                p.drawRect(QRectF(mark.x() - 4, mark.y() - 4, 8, 8))
            if place.kind == "hub":                    # a capital gets a pip
                p.setBrush(tint)
                p.drawEllipse(mark, 1.6, 1.6)
                p.setBrush(Qt.BrushStyle.NoBrush)
            if place.here:
                p.setPen(QPen(tint, 1.0, Qt.PenStyle.DashLine))
                p.drawEllipse(mark, 8, 8)
            p.setFont(QFont(theme.mono_family(), 7))
            p.setPen(tint)
            p.drawText(QRectF(mark.x() + 7, mark.y() - 7, 120, 13),
                       Qt.AlignmentFlag.AlignLeft, place.name)

        # Other hulls. The Verge looked empty in the one view where it should
        # look busiest — nothing else had a position to draw.
        labelled: list = []
        for hull in traffic_sim.in_system(g):
            at = self._to_screen(*traffic_sim.position(g, hull))
            tint = QColor(theme.tint("warn" if hull.hostile else "lumen"))
            p.setPen(QPen(tint, 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if hull.hostile:                       # a cross, and no label
                p.drawLine(QPointF(at.x() - 3.5, at.y() - 3.5),
                           QPointF(at.x() + 3.5, at.y() + 3.5))
                p.drawLine(QPointF(at.x() - 3.5, at.y() + 3.5),
                           QPointF(at.x() + 3.5, at.y() - 3.5))
            else:
                p.drawEllipse(at, 2.6, 2.6)
                # Traffic converges on the quay, so labels piled on top of one
                # another and read as one illegible smear. Name a hull only
                # where there is room; the panel below names them all.
                room = all(abs(at.x() - x) > 58 or abs(at.y() - y) > 11
                           for x, y in labelled)
                if room:
                    labelled.append((at.x(), at.y()))
                    p.setFont(QFont(theme.mono_family(), 6))
                    p.setPen(QColor(169, 194, 182, 150))
                    p.drawText(QRectF(at.x() + 5, at.y() - 6, 110, 12),
                               Qt.AlignmentFlag.AlignLeft, hull.name)

        self._draw_course(p, g, s, cx, cy)

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
        self.burn = "standard"

    def build(self) -> None:
        g = self.game
        here = flight.current_body(g)
        # `where_am_i` rather than the body name: a captain could not tell
        # they had launched from a fleet hub except by opening the shipyard
        # window, which is not an answer to "where am I".
        self.head(f"Helm — {g.system.name}", anchorage_sim.where_am_i(g))

        if self.target >= len(g.system.bodies):
            self.target = 0

        chart = OrbitChart(self.win)
        chart.target = self.target
        chart.burn = self.burn
        chart.picked.connect(self._pick)
        # Chart and the places you can put in share the left column: three
        # columns fits a wide desktop and silently drops the third one at any
        # ordinary window size, which is how it was first written.
        left = QWidget()
        stack = QVBoxLayout(left)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(10)
        stack.addWidget(chart, 1)
        stack.addWidget(self._where(g))
        stack.addWidget(self._who(g))
        self.row(left, self._plot(g))
        self.buttons(
            button("System overview", lambda: self.win.go("system")),
            button("Sector chart", lambda: self.win.go("map")),
            button("Plotting board…", self._plotting_board),
            button("Take the conn…", self._take_conn))

    def _plotting_board(self) -> None:
        """The system in its own window, with time and a zoom on it."""
        from .plot3d_window import open_plot
        open_plot(self.win)

    def _take_conn(self) -> None:
        """Fly by hand, at the range where a metre a second matters."""
        from .conn_window import open_conn
        open_conn(self.win)

    def _pick(self, index: int) -> None:
        self.target = index
        self.refresh()

    def course_to(self, body_index: int) -> None:
        """Aim at a body by index. What a quay's `Set course` calls.

        A quay's position *is* its body's position, so setting course for one
        is setting course for the other — no special case anywhere in flight.
        """
        self.target = body_index
        self.refresh()

    def _who(self, g):
        from .traffic_panel import who_else
        return who_else(self, g)

    def _where(self, g):
        from .anchorage_panel import where_to_put_in
        return where_to_put_in(self, g)

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
        cap = g.ship_stats.heat_cap
        p.add_row("Hull heat", f"{round(g.ship.heat)} / {round(cap)}",
                  "warn" if g.ship.heat > cap else
                  ("osteo" if g.ship.heat > cap * 0.5 else ""))

        if at:
            p.add(spacer(4))
            p.add(Pill("alongside", "chloro"))
            p.add(note("You are already there. Survey, extract, dig or land from "
                       "the system screen."))
            return p

        q = flight.intercept(g, body, self.burn)
        p.add_row("Aim point", f"{q['au']:.2f} AU ahead of the mark")
        p.add_row("Target moves", f"{q['lead']:.2f} AU while you are under way")
        p.add_row("Arrives", f"day {q['arrival_day']} · {duration(q['days'])}")
        hazard = flight.path_note(g, body, self.burn)
        if hazard:
            p.add(note(hazard))

        p.add(spacer(4), mono_label("Plot"))
        tabs = TabBar([(b.id, b.name) for b in flight.BURNS], self.burn)
        tabs.changed.connect(self._plot_burn)
        p.add(tabs)

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
            arriving = g.ship.heat + flight.burn_heat(burn, g.ship_stats)
            if burn.heat:
                p.add_row("Arrives at",
                          f"{round(arriving)} / {round(g.ship_stats.heat_cap)} heat",
                          "warn" if arriving > g.ship_stats.heat_cap else "")
            p.add_buttons(button(f"Burn — {q['days']} d",
                                 lambda _=False, bid=burn.id: self._burn(bid),
                                 kind="primary" if burn.id == "standard" else "",
                                 enabled=afford))
        p.add(spacer(4))
        p.add(note("Bodies move while you fly, so the helm aims at where the "
                   "target will be, not where it is. The crosshair on the chart "
                   "is the aim point; the amber arc is the ground it covers "
                   "while you are under way."))
        p.add(note("A hard burn arrives hot, and a hot hull is a worse thing to "
                   "burn again in. Over the cap the radiators stop keeping up "
                   "and the hull cooks. Sitting still sheds it."))
        return p

    def _plot_burn(self, burn_id: str) -> None:
        self.burn = burn_id
        self.refresh()

    def _burn(self, burn_id: str) -> None:
        # Committing to a burn puts you in the pilot's seat for the crossing
        # rather than skipping to the far end of it.
        res = transit_sim.begin(self.game, self.target, burn_id)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.transit = res["transit"]
        self.win.go("transit")
