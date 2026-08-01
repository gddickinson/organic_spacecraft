"""The orrery: the system drawn as a chart you can click.

Lifted out of `ui/helm_view.py`, which had grown past five hundred lines
carrying both the plot and the screen around it. They are different jobs — this
one is a widget that paints bodies, quays, traffic and the leg you are about to
fly, and answers a click with whatever you hit.

**One door for every label on it.** The plot has three families of name — the
bodies, the quays and the other hulls — and only the last of them used to
de-clutter, against a list that collected hull names and nothing else. Measured
over ten seeds, 83 labels: three pairs printed across each other and every one
was a quay name under a hull name.

**And one door for where a quay's mark goes.** `place_mark` serves the painter
and the hit test alike, which is right, but it offset from the *planet* — so
two quays at one body landed on the same point, drew as one square, and the
second could not be clicked at all.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (QColor, QFont, QFontMetricsF, QPainter, QPainterPath,
                         QPen)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data.starclasses import mu_of
from ..sim import anchorage as anchorage_sim
from ..sim import flight
from ..sim import traffic as traffic_sim
from ..world.planets import BODY_KINDS
from . import theme


#: How far a quay's mark sits from the body it orbits, in pixels.
#:
#: It has to be offset or it would be hidden under the planet — and it has to
#: be *one* number, because the painter drew at +11/-11 while the hit test
#: only ever checked bodies. The Fleet Hub was therefore drawn, labelled, and
#: unclickable: a click on it landed inside the planet's 18 px radius and
#: selected the planet instead, which was usually already the target, so
#: nothing whatever appeared to happen.
QUAY_OFFSET = 11.0

#: How many quays can share a body before the fan has to tighten.
#:
#: Four, at a quarter-turn each, because a fixed step means a newly founded
#: quay does not shuffle the ones already drawn — a captain's muscle memory for
#: where the shipyard sits is worth more than an even spread. Measured across
#: 22 seeds only one body carries even two (`lab8`: Fleet Hub and Third
#: Silence), so the tightening is a guard rather than a common case. At four
#: seats the marks sit 31 px apart against a 13 px hit radius; at eight they
#: would be 12 px apart and start tying again, which is the bug this fixes.
QUAY_SEATS = 4

#: How near a click has to land to count as hitting a quay's mark, in pixels.
#:
#: Named because the fan above has to clear it: two quays whose marks sit
#: closer than this share one neighbourhood, so a click a few pixels off the
#: one you meant lands on the other. At four seats the marks are 31 px apart,
#: comfortably outside it. It was a bare 13.0 in the hit test and nowhere
#: else, so nothing could check the fan against the thing the fan exists to
#: clear — and a mutation shrinking the fan to 4 px passed.
QUAY_HIT = 13.0


class OrbitChart(QWidget):
    """The system from above: orbits, bodies where they are today, the ship."""

    picked = pyqtSignal(int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.target = 0
        #: Which quay is selected, if the captain picked one rather than a
        #: bare body. Only affects what the chart rings and what the panel
        #: calls the destination — a quay's position *is* its body's.
        self.place = None
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

    def _quay_seat(self, g, place) -> tuple[int, int]:
        """Which seat around its body this quay takes, and how many there are.

        Sorted by id so the seat a captain clicked yesterday is the same seat
        today — the discipline `sim/traffic` already uses for hull slots, and
        for the same reason.
        """
        here = sorted(p.id for p in anchorage_sim.in_system(g)
                      if p.body_index == place.body_index)
        return here.index(place.id), len(here)

    def place_mark(self, g, place) -> QPointF:
        """Where a quay's mark is drawn. The painter and the hit test agree
        because they both come here.

        **They agreed, and were both wrong.** This offset from the *planet*
        rather than from the quay, so every anchorage sharing a `body_index`
        landed on exactly the same point. Measured: seed "lab8" puts `Fleet
        Hub` and `Third Silence` both at body 0 of Marrow Fall, and the chart
        drew one square where there are two stations. Worse than cosmetic —
        `mousePressEvent` takes the nearest mark under 13 px with a strict
        `d < pd`, so the second quay tied and lost every time: clicking `Third
        Silence`'s own mark selected `Fleet Hub`, and it could not be picked
        from the chart at all.

        Seat 0 sits exactly where the single offset used to, so every body
        with one quay — which is nearly all of them — draws unchanged.
        """
        body = g.system.bodies[place.body_index]
        at = self._to_screen(*flight.position(body, g.day, mu_of(g.system)))
        seat, seats = self._quay_seat(g, place)
        # A fixed quarter-turn step while there is room for one, so adding a
        # quay does not shuffle the ones already there; only a fifth at the
        # same body makes everybody budge.
        step = math.tau / max(QUAY_SEATS, seats)
        ang = -math.pi / 4 + seat * step
        far = QUAY_OFFSET * math.sqrt(2)
        return QPointF(at.x() + far * math.cos(ang),
                       at.y() + far * math.sin(ang))

    def mousePressEvent(self, ev):  # noqa: N802
        g = self.win.game
        where = ev.position()

        # Quays first. They are the smaller mark and they sit inside the
        # planet's hit radius, so testing bodies first meant a click on a
        # station could only ever select the station's planet.
        near, pd = None, QUAY_HIT
        for place in anchorage_sim.in_system(g):
            if place.body_index >= len(g.system.bodies):
                continue
            mark = self.place_mark(g, place)
            d = math.hypot(mark.x() - where.x(), mark.y() - where.y())
            if d < pd:
                near, pd = place, d
        if near is not None:
            self.place = near.id
            self.picked.emit(near.body_index)
            return

        best, bd = None, 18.0
        for i, b in enumerate(g.system.bodies):
            p = self._to_screen(*flight.position(b, g.day, mu_of(g.system)))
            d = math.hypot(p.x() - ev.position().x(), p.y() - ev.position().y())
            if d < bd:
                best, bd = i, d
        if best is not None:
            self.place = None
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
        now = self._to_screen(*flight.position(body, g.day, mu_of(g.system)))

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
            pt = self._to_screen(*flight.position(body, day, mu_of(g.system)))
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

    #: Clear space demanded around a label's ink, in pixels.
    #:
    #: This replaced a pair of point-distance thresholds (58 across, 11 down)
    #: that the traffic loop used against other traffic. Those compared *draw
    #: anchors* while the ink runs some hundred pixels to the right of its
    #: anchor, so a neighbour just outside 58 still printed straight across:
    #: measured over twenty seeds, that left `III` under a hull name twice
    #: even after the three lists were merged.
    #:
    #: **It costs hull names, and the count says so.** Over the same ten
    #: seeds: 83 labels with 3 overlapping pairs before, 78 with the merged
    #: point rule, 71 with this and none overlapping. Twelve names went, three
    #: of which were illegible anyway. That is the trade the traffic loop
    #: already chose when it first refused to name a crowded hull — the panel
    #: below the chart lists every one of them.
    LABEL_PAD = 2.0

    def _ink(self, p, x: float, y: float, box: float, text: str,
             centred: bool) -> QRectF:
        """The rectangle a label's glyphs will actually occupy."""
        fm = QFontMetricsF(p.font())
        w = fm.horizontalAdvance(text)
        return QRectF(x + (box - w) / 2 if centred else x, y, w, fm.height())

    def _room_for(self, ink: QRectF) -> bool:
        """Is this label's ink clear of everything already drawn?

        **One door for every label on the plot, and it used to serve one.**
        The rule lived inline in the traffic loop and tested against a list
        that only ever collected hull names, so a hull could not see the quay
        label it was about to print across. Measured over ten seeds, 83 labels
        drawn: three pairs overlapped and every one was `Fleet Hub` under a
        hull name, one of them covering it completely.
        """
        pad = self.LABEL_PAD
        grown = ink.adjusted(-pad, -pad, pad, pad)
        return not any(grown.intersects(other) for other in self._labels)

    def paintEvent(self, _ev):  # noqa: N802
        g = self.win.game
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        s, cx, cy = self._scale()
        #: Where a label has already been put this repaint, as (x, y) of its
        #: ink. Rebuilt every paint because the plot is redrawn from scratch.
        self._labels: list = []

        # the star
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(g.system.tint))
        p.drawEllipse(QPointF(cx, cy), 7, 7)

        for i, b in enumerate(g.system.bodies):
            r = flight.orbit_radius(b) * s
            p.setPen(QPen(QColor(150, 196, 176, 40), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

            pos = self._to_screen(*flight.position(b, g.day, mu_of(g.system)))
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
            name = b.name.split()[-1]
            p.drawText(QRectF(pos.x() - 55, pos.y() + 7, 110, 13),
                       Qt.AlignmentFlag.AlignHCenter, name)
            # A body is what the chart is *of*, so its name is never refused —
            # it only claims the space, and the crowd yields to it.
            self._labels.append(
                self._ink(p, pos.x() - 55, pos.y() + 7, 110, name, True))

        # Quays, hubs and your own holdings. They sit at the body they orbit,
        # so they are drawn just outside its marker rather than on top of it —
        # a chart that showed only the sun and the planets was the whole
        # complaint that started this.
        for place in anchorage_sim.in_system(g):
            if place.body_index >= len(g.system.bodies):
                continue
            mark = self.place_mark(g, place)
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
            if place.id == getattr(self, "place", None):
                p.setPen(QPen(QColor(theme.INK), 1.4))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(mark, 10, 10)
            p.setFont(QFont(theme.mono_family(), 7))
            p.setPen(tint)
            # A quay's name cannot simply be dropped, so it is stacked clear
            # instead. Two quays at one body get the *same* mark — `place_mark`
            # offsets from the planet, not from the quay — so on seed "lab8"
            # `Fleet Hub` and `Third Silence` printed exactly on top of one
            # another. The last candidate is used regardless: a crowded label
            # beats a quay with no name at all.
            lx, ly = mark.x() + 7, mark.y() - 7
            ink = self._ink(p, lx, ly, 120, place.name, False)
            for dy in (0, 15, -15, 30, -30):
                moved = ink.translated(0, dy)
                if self._room_for(moved):
                    ink = moved
                    break
            p.drawText(QRectF(lx, ink.y(), 120, 13),
                       Qt.AlignmentFlag.AlignLeft, place.name)
            self._labels.append(ink)

        # Other hulls. The Verge looked empty in the one view where it should
        # look busiest — nothing else had a position to draw.
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
                # where there is room; the panel below names them all. The
                # room is asked of `_room_for`, which knows about the bodies
                # and the quays as well — asking a list that held only hulls
                # is what put `Fleet Hub` under a hull name on three of ten
                # measured seeds.
                p.setFont(QFont(theme.mono_family(), 6))
                ink = self._ink(p, at.x() + 5, at.y() - 6, 110,
                                hull.name, False)
                if self._room_for(ink):
                    self._labels.append(ink)
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
