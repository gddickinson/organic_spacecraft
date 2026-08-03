"""The engagement from above: hulls, headings, range bands and firing arcs.

Lifted out of `battle_view.py` when the arcs went on and that file crossed five
hundred lines.

The plot drew rings and two triangles. It never drew the one thing the whole
geometry exists for — what bears — so a captain choosing between *come about*
and *present the broadside* chose blind and was told afterwards, in the log,
which had been right. `sim/firing.py` answers that; this draws the answer.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..sim import firing, tactical as tac
from . import theme
from . import painting


class TacticalPlot(QWidget):
    """The engagement from above: two hulls, their headings, and the arcs.

    Range bands are drawn as rings around your ship so the abstract numbers the
    weapons are specified in have somewhere to live on the picture.
    """

    SIZE = 380

    def __init__(self, battle):
        super().__init__()
        self.b = battle
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _scale(self):
        span = max(tac.BAND_UNITS * 5.2, self.b.range_units * 2.3)
        for consort in self.b.consorts:
            if not consort.out:
                span = max(span, tac.separation(self.b.player.body,
                                                consort.body) * 2.4)
        return (self.SIZE / 2 - 14) / (span / 2)

    def _pt(self, body, origin, s) -> QPointF:
        return QPointF(self.SIZE / 2 + (body.x - origin.x) * s,
                       self.SIZE / 2 + (body.y - origin.y) * s)

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        b = self.b
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        s = self._scale()
        mid = b.player.body

        # range rings, one per band
        for band in range(1, 5):
            r = tac.BAND_UNITS * band * s
            p.setPen(QPen(QColor(150, 196, 176, 34), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(self.SIZE / 2, self.SIZE / 2), r, r)

        # Firing arcs, before the hulls so the triangles sit on top. Yours in
        # full, theirs faintly — sitting in an enemy's forward arc is a
        # decision and the plot never said you were in one.
        self._draw_arcs(p, b.enemy, b.player, mid, s, theme.tint("warn"), 0.30)
        self._draw_arcs(p, b.player, b.enemy, mid, s, theme.tint("chloro"), 1.0)

        for consort in b.consorts:
            if consort.out:
                continue
            self._draw_ship(p, consort, mid, s, theme.tint("lumen"), True)
        self._draw_ship(p, b.player, mid, s, theme.tint("chloro"), True)
        self._draw_ship(p, b.enemy, mid, s, theme.tint("warn"), False)

        # the line of sight, labelled with the range
        a = self._pt(b.player.body, mid, s)
        c = self._pt(b.enemy.body, mid, s)
        p.setPen(QPen(QColor(150, 196, 176, 60), 1, Qt.PenStyle.DashLine))
        p.drawLine(a, c)
        p.setFont(QFont(theme.mono_family(), 8))
        p.setPen(QColor(theme.INK3))
        p.drawText(QRectF((a.x() + c.x()) / 2 - 40, (a.y() + c.y()) / 2 - 14, 80, 14),
                   Qt.AlignmentFlag.AlignHCenter, f"{round(b.range_units)}")
        p.end()

    def _draw_ship(self, p, side, origin, s, colour, mine: bool) -> None:
        pos = self._pt(side.body, origin, s)
        rad = math.radians(side.body.heading)
        nose = QPointF(pos.x() + math.sin(rad) * 13, pos.y() - math.cos(rad) * 13)
        left = QPointF(pos.x() + math.sin(rad + 2.5) * 9,
                       pos.y() - math.cos(rad + 2.5) * 9)
        right = QPointF(pos.x() + math.sin(rad - 2.5) * 9,
                        pos.y() - math.cos(rad - 2.5) * 9)
        p.setPen(QPen(QColor(colour), 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPolygon(QPolygonF([nose, left, right]))

        # The forward-arc sketch that used to live here is gone: `_draw_arcs`
        # draws every arc the hull actually has mounts in, which is the thing
        # the sketch was standing in for.

    def _draw_arcs(self, p, side, other, origin, s, colour, alpha: float) -> None:
        """One wedge per arc this hull has mounts in, lit if anything bears.

        One wedge per *arc*, not per mount: five broadside guns drew five
        identical wedges on top of each other and looked like one thick line.
        """
        arcs = firing.arcs_in_use(side)
        if not arcs:
            return
        pos = self._pt(side.body, origin, s)
        shots = firing.solution(side, other)
        reach = tac.BAND_UNITS * 1.5 * s

        for arc in arcs:
            live = any(x.in_arc and x.can_fire for x in shots if x.arc == arc)
            low, high = firing.arc_span(arc)
            if high - low >= 180:
                # An all-round mount traverses everywhere, so its "wedge" is
                # the whole circle — drawn as one it swallowed the plot and
                # said nothing. A ring reads as "this one always bears".
                tint = QColor(colour)
                tint.setAlphaF(alpha * (0.42 if live else 0.16))
                p.setPen(QPen(tint, 1.0, Qt.PenStyle.DashLine))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(pos, reach, reach)
                continue
            tint = QColor(colour)
            tint.setAlphaF(alpha * (0.55 if live else 0.20))
            p.setPen(QPen(tint, 1.4 if live else 1.0,
                          Qt.PenStyle.SolidLine if live else Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            # Mirrored either side of the bow: an arc of 60–120° means both
            # beams, and drawing only one of them is a lie about the ship.
            for sign in (1, -1):
                start = side.body.heading + sign * low
                span = sign * (high - low)
                box = QRectF(pos.x() - reach, pos.y() - reach, reach * 2, reach * 2)
                # Qt measures from three o'clock, anticlockwise, in 1/16ths;
                # the game measures from the bow, clockwise.
                p.drawArc(box, int((90 - start - span) * 16) if sign > 0
                          else int((90 - start) * 16),
                          int(abs(span) * 16))
                for edge in (start, start + span):
                    rad = math.radians(edge)
                    p.drawLine(pos, QPointF(pos.x() + math.sin(rad) * reach,
                                            pos.y() - math.cos(rad) * reach))
