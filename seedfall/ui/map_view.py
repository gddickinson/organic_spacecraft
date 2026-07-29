"""The sector chart. Forty-odd stars, a jump circle, and a growing red stain in
one corner of it."""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core.util import credits as cr
from ..core.util import duration, num
from ..data.factions import FACTIONS_BY_ID
from ..sim import intel as intel_sim
from . import orders_panel
from ..sim import rumours as rumour_sim
from ..sim import reach as reach_sim
from ..sim import anchorage as anchorage_sim
from ..sim.actions import distress_call, is_stranded, jump_quote, jump_to
from ..world.galaxy import distance
from . import theme
from .widgets import Panel, View, button, label, mono_label, note, spacer

FACTION_COLOUR = {k: theme.tint(v) for k, v in theme.FACTION_TINT.items()}


class StarChart(QWidget):
    picked = pyqtSignal(int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.selected: int | None = None
        self.setMinimumHeight(420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # geometry -------------------------------------------------------------

    def _projection(self):
        g = self.win.game.galaxy
        pad = 30
        w, h = self.width(), self.height()
        scale = min((w - pad * 2) / g.w, (h - pad * 2) / g.h)
        ox = (w - g.w * scale) / 2
        oy = (h - g.h * scale) / 2
        return scale, ox, oy

    def _to_screen(self, sys) -> QPointF:
        s, ox, oy = self._projection()
        return QPointF(ox + sys.x * s, oy + sys.y * s)

    def _pick(self, pos) -> int | None:
        best, bd = None, 16.0
        for sys in self.win.game.galaxy.systems:
            p = self._to_screen(sys)
            d = math.hypot(p.x() - pos.x(), p.y() - pos.y())
            if d < bd:
                best, bd = sys.id, d
        return best

    def mousePressEvent(self, ev):  # noqa: N802
        sid = self._pick(ev.position())
        if sid is not None:
            self.selected = sid
            self.picked.emit(sid)
            self.update()

    def mouseMoveEvent(self, ev):  # noqa: N802
        hit = self._pick(ev.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if hit
                       else Qt.CursorShape.CrossCursor)

    # painting -------------------------------------------------------------

    def paintEvent(self, _ev):  # noqa: N802
        g = self.win.game
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))

        scale, _ox, _oy = self._projection()
        here = g.system
        hs = self._to_screen(here)
        reach = g.ship_stats.jump

        # jump envelope
        pen = QPen(QColor(84, 207, 124, 90), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(hs, reach * scale, reach * scale)

        # reachable lanes
        p.setPen(QPen(QColor(150, 196, 176, 38), 1))
        for sys in g.galaxy.systems:
            if sys.id != here.id and distance(sys, here) <= reach:
                p.drawLine(hs, self._to_screen(sys))

        # Which stars are reachable *at all*, by hopping. The dashed ring
        # only ever said what is one jump away, so a star behind a gap no
        # amount of hopping closes was drawn exactly like the one next door.
        within = reach_sim.component(g)
        for sys in g.galaxy.systems:
            self._draw_system(p, sys, here, reach, sys.id in within)

        self._draw_marker(p, hs, QColor(theme.tint("chloro")), 13)
        if self.selected is not None:
            self._draw_marker(p, self._to_screen(g.galaxy.systems[self.selected]),
                              QColor(theme.tint("lumen")), 10)
        p.end()

    def _draw_system(self, p: QPainter, sys, here, reach,
                     reachable: bool = True) -> None:
        g = self.win.game
        pt = self._to_screen(sys)
        rank = intel_sim.level(g, sys)
        known = rank >= 1 or any(c.system_id == sys.id for c in g.colonies)

        if sys.bloom > 0.02 and intel_sim.sees_bloom(g, sys):
            radius = 9 + sys.bloom * 24
            grad = QRadialGradient(pt, radius)
            grad.setColorAt(0.0, QColor(224, 104, 95, int(70 * sys.bloom + 30)))
            grad.setColorAt(1.0, QColor(224, 104, 95, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawEllipse(pt, radius, radius)

        r = 2.6 + len(sys.bodies) * 0.3
        # How well a system is known reads off the marker: an outline for a
        # name in a registry, a filled disc once you have been, and a ring
        # around anything charted to the last body.
        if rank >= 2:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(sys.tint))
            p.drawEllipse(pt, r, r)
        elif rank == 1:
            faded = QColor(sys.tint)
            faded.setAlpha(120)
            p.setPen(QPen(QColor(150, 196, 176, 110), 1))
            p.setBrush(faded)
            p.drawEllipse(pt, r, r)
        else:
            p.setPen(QPen(QColor(150, 196, 176, 70), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r, r)

        if rank >= 3:
            p.setPen(QPen(QColor(theme.tint("chloro")), 1.0, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 5.5, r + 5.5)

        # Anything anybody has told you about sits on the chart as a caret.
        if rumour_sim.about(g, sys.id):
            p.setPen(QPen(QColor(theme.tint("xeno")), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            top = QPointF(pt.x(), pt.y() - r - 9)
            p.drawLine(QPointF(top.x() - 4, top.y() + 5), top)
            p.drawLine(top, QPointF(top.x() + 4, top.y() + 5))

        if sys.port and known:
            colour = QColor(FACTION_COLOUR.get(sys.faction, theme.INK3))
            p.setPen(QPen(colour, 1.6 if sys.port.capital else 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 3.6, r + 3.6)

        if any(c.system_id == sys.id for c in g.colonies):
            pen = QPen(QColor(84, 207, 124, 150), 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 6.8, r + 6.8)

        if not reachable:
            # A bar through the star: this one is not far, it is walled off.
            p.setPen(QPen(QColor(224, 104, 95, 130), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(pt.x() - r - 4, pt.y() - r - 4),
                       QPointF(pt.x() + r + 4, pt.y() + r + 4))

        if known:
            f = QFont(theme.mono_family(), 8)
            p.setFont(f)
            p.setPen(QColor(169, 194, 182, 190 if reachable else 90))
            rect = QRectF(pt.x() - 70, pt.y() + r + 3, 140, 14)
            p.drawText(rect, Qt.AlignmentFlag.AlignHCenter, sys.name)

    def _draw_marker(self, p: QPainter, pt: QPointF, colour: QColor, size: float):
        p.setPen(QPen(colour, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.drawLine(QPointF(pt.x() + dx * size, pt.y() + dy * size * 0.55),
                       QPointF(pt.x() + dx * size, pt.y() + dy * size))
            p.drawLine(QPointF(pt.x() + dx * size, pt.y() + dy * size),
                       QPointF(pt.x() + dx * size * 0.55, pt.y() + dy * size))


class MapView(View):
    def __init__(self, win):
        super().__init__(win)
        self.chart = StarChart(win)
        self.chart.picked.connect(self._on_pick)
        self.selected: int | None = None

    def _on_pick(self, sid: int) -> None:
        self.selected = sid
        self.refresh()

    def build(self) -> None:
        g = self.game
        known = intel_sim.summary(g)
        leads = rumour_sim.summary(g)
        self.head("Sector Chart",
                  f"The Verge · {known['total']} stars · "
                  f"{known['counts'][0]} names only · "
                  f"{known['counts'][1]} scanned · "
                  f"{known['counts'][2]} visited · "
                  f"{known['charted']} charted"
                  + (f" · {leads['held']} lead(s) to follow" if leads["held"] else ""))

        self.col.addWidget(orders_panel.build(self, g))

        if self.selected is None:
            self.selected = g.location_id
        self.chart.selected = self.selected
        self.chart.setParent(None)
        self.col.addWidget(self.chart, 1)
        self.chart.show()
        self.chart.update()

        legend = " · ".join([
            "Charter", "Concordat", "Freeholds", "Dry Choir", "Bloom",
            "○ catalogued", "◍ scanned", "● visited", "◌ charted",
            "◎ port", "∧ something said about it",
            "dashed ring = jump range", "╲ beyond reach",
        ])
        self.col.addWidget(note(legend))
        # What the ring never said: how much of the sector this drive can
        # actually get to, and what the next one would open.
        self.col.addWidget(note(reach_sim.note(self.game)))
        wall = self._way_out()
        if wall is not None:
            self.col.addWidget(wall)
        self.col.addWidget(self._info())

    def _way_out(self):
        """What getting past the wall would actually take, item by item.

        Naming a drive and stopping there is the same defect as a contract fee
        with no cargo cost beside it. Measured, the way out of a small pocket
        is twelve technologies, five thousand research points, seventy-eight
        thousand credits and twenty tonnes of magnetite — a project, not a
        purchase — and whether the ports you *can* reach sell those materials
        is the thing that decides whether it is a project at all.
        """
        from ..core.util import credits as cr
        from ..data.tech import TECH_BY_ID
        plan = reach_sim.plan(self.game)
        if not plan or plan["step"]["gain"] <= 0:
            return None
        step = plan["step"]
        p = Panel(f"Getting past the wall — {step['part'].name}")
        p.add(self.hint(
            "It opens the rest of the sector. This is what it takes, and "
            "whether the ports you can already reach can supply it."))
        p.add_row("Opens", f"{step['gain']} more systems "
                           f"({plan['within']} → {step['within']})")
        if plan["tech"]:
            done = len(plan["tech"])
            p.add_row("Still to research",
                      f"{done} technolog{'y' if done == 1 else 'ies'} · "
                      f"{plan['points']:,} points",
                      "osteo")
            p.add(note(", ".join(
                TECH_BY_ID[t].name for t in plan["tech"][:6]
                if t in TECH_BY_ID) + (" …" if done > 6 else "")))
        short = plan["have_credits"] - plan["credits"]
        p.add_row("Credits", f"{cr(plan['credits'])} "
                             f"({'have it' if short >= 0 else f'{cr(-short)} short'})",
                  "chloro" if short >= 0 else "osteo")
        for material in plan["materials"]:
            where = ", ".join(material["sold_at"][:2]) or "nowhere you can reach"
            p.add_row(f"{material['need']:g} t {material['id']}",
                      f"have {material['have']:g} · sold at {where}",
                      "warn" if material["short"] else "")
        p.add_row("Yard", ", ".join(plan["yards"][:2]) or "none in reach",
                  "warn" if not plan["yards"] else "")
        if plan["reachable"]:
            p.add(label("Everything it needs can be had from where you are. "
                        "It is a long project and it is not a trap.", "",
                        "chloro", wrap=True))
        else:
            p.add(label("Something it needs is not for sale anywhere you can "
                        "reach. Mine it, or take it off somebody.", "",
                        "warn", wrap=True))
        return p

    def _info(self) -> Panel:
        g = self.game
        sys = g.galaxy.systems[self.selected]
        q = jump_quote(g, sys)
        here = sys.id == g.location_id
        fac = FACTIONS_BY_ID.get(sys.faction) if sys.faction else None

        panel = Panel(sys.name + ("   ·   you are here" if here else ""))
        panel.add(note(f"{sys.star_name} · {len(sys.bodies)} catalogued bodies"))
        rank = intel_sim.level(g, sys)
        if fac and rank >= 1:
            panel.add(label(f"{fac.name}. {fac.creed}", "", wrap=True))
        elif rank >= 1:
            panel.add(label("Unclaimed space.", "dim"))
        else:
            panel.add(label("Whose space this is, nobody here has said.", "dim"))
        if sys.note:
            panel.add(label(sys.note, "", "warn", wrap=True))
        # What has grown there, and only where somebody of yours can see it.
        if intel_sim.sees_bloom(g, sys):
            if sys.bloom > 0.02:
                panel.add(label(f"Bloom mass: {round(sys.bloom * 100)}% of this "
                                "system converted.", "", "warn", wrap=True))
        else:
            panel.add(label("Nothing of yours is watching it, so what has "
                            "grown there since anybody looked is not known.",
                            "", "dim", wrap=True))
        name, tint = intel_sim.label(g, sys)
        panel.add_row("Knowledge", name, tint)
        panel.add(note(intel_sim.blurb(g, sys)))
        if rank >= 1 and rank < 3:
            done = intel_sim.survey_fraction(sys)
            panel.add_row("Bodies surveyed",
                          f"{round(done * len(sys.bodies))}/{len(sys.bodies)}")
            panel.add_bar(done, "lumen")
        if rank == 0:
            price = intel_sim.chart_price(g, sys)
            panel.add_buttons(button(f"Buy the chart — {cr(price)}",
                                     lambda _=False, sid=sys.id: self._buy_chart(sid),
                                     enabled=g.credits >= price))
        for rumour in rumour_sim.about(g, sys.id):
            kind = rumour.definition
            panel.add(label(kind.name, "", kind.tint))
            panel.add(note(kind.claim.format(system=sys.name)))

        panel.add(mono_label("Passage"))
        panel.add_row("Distance", f"{q['ly']:.1f} ly")
        panel.add_row("Jump range", f"{g.ship_stats.jump:.1f} ly")
        panel.add_row("Transit", "—" if here else duration(q["days"]))
        panel.add_row("Reaction mass", "—" if here else f"{q['fuel']} t",
                      "warn" if (not here and
                                 g.ship.cargo.get("volatiles", 0) < q["fuel"]) else "")
        panel.add_row("Port", (sys.port.name + (" (capital)" if sys.port.capital else ""))
                      if sys.port else "none")
        # What the berth actually offers. "How would I navigate back to a
        # shipyard" is unanswerable if the chart will not say which systems
        # have one.
        if sys.port:
            panel.add_row("Offers", ", ".join(
                anchorage_sim.SERVICE_NAMES.get(x, x)
                for x in sys.port.services))
        panel.add_row("Your holdings",
                      num(len([c for c in g.colonies if c.system_id == sys.id])))

        if here:
            panel.add_buttons(
                button("Enter system", lambda: self.win.go("system"), kind="primary"),
                button("Dock", lambda: self.win.go("port")) if sys.port else None)
        else:
            # The four ways to fly it, each stating what it costs on both
            # clocks. A bare "Set course" could not say that a hard burn buys
            # the crew four years of their lives back.
            from .crossing_panel import how_to_fly
            panel.add(how_to_fly(self, g, sys))

        if is_stranded(g):
            panel.add(spacer(4))
            panel.add(label(
                "You cannot reach anywhere, cannot buy reaction mass and cannot "
                "make any here. Somebody will come if you ask — and they will "
                "remember that you asked.", "", "warn", wrap=True))
            panel.add_buttons(button("Broadcast distress", self._distress,
                                     kind="danger"))
        return panel

    def _distress(self) -> None:
        res = distress_call(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.dialog(
            "Answered",
            [f"A {res['faction']} tender reached you after {res['days']} days and "
             f"towed you to {res['port'].name}. They took two thousand credits, "
             "left twenty tonnes of reaction mass, and logged the whole thing."],
            [("Log it", None)])
        self.selected = self.game.location_id
        self.win.refresh()

    def _buy_chart(self, system_id: int) -> None:
        res = intel_sim.buy_chart(self.game, self.game.galaxy.systems[system_id])
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _jump(self, crossing: str = "steady") -> None:
        self.crossing = crossing
        res = jump_to(self.game, self.selected, crossing)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        if res.get("event"):
            ev = res["event"]
            texts = [ev["text"]]
            if ev["effect"].get("note"):
                texts.append(note(ev["effect"]["note"]))
            self.win.dialog("In transit", texts, [("Carry on", None)])
        if res.get("encounter"):
            self.win.begin_combat(res["encounter"], "system")
            return
        self.selected = self.game.location_id
        self.win.go("system")
