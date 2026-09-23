"""The landing zone, drawn: fogged tiles, terrain tint, feature marks.

Split out of `ui/expedition_view.py` when that file reached five hundred
lines, along the seam the walking layer already has between
`ui/afoot_canvas.py` and the screen that holds it: this is the picture, and
the screen next door is the panel, the odds and the buttons.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data.expedition import FEATURES, TERRAIN
from ..sim import expedition as exp_sim
from . import painting, theme


CELL = 62

#: **A letter in every feature's ring.** Ten features share six colours —
#: three of them the same green — so on the map a sealed cache, an
#: aggregation and cultivated ground were one mark, and under deuteranopia
#: most of the rest joined them. The letter carries the difference; the
#: legend under the map says which is which.
MARK = {"ruin": "R", "seam": "S", "vent_field": "V", "wreck": "W",
        "cache": "C", "nest": "N", "monolith": "M", "shaft": "I",
        "bloomscar": "B", "garden": "G"}


def feature_mark(fid: str) -> str:
    return MARK.get(fid, fid[:1].upper())


class ZoneMap(QWidget):
    """The landing zone: fogged tiles, terrain tint, feature marks."""

    picked = pyqtSignal(int, int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.setFixedSize(CELL * exp_sim.W + 2, CELL * exp_sim.H + 2)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, ev):  # noqa: N802
        x = int(ev.position().x() // CELL)
        y = int(ev.position().y() // CELL)
        if 0 <= x < exp_sim.W and 0 <= y < exp_sim.H:
            self.picked.emit(x, y)

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        exp = self.win.game.expedition
        if exp is None:
            return
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))

        for t in exp.tiles:
            r = QRectF(t.x * CELL + 1, t.y * CELL + 1, CELL - 2, CELL - 2)
            if not t.seen:
                p.fillRect(r, QColor("#0b1512"))
                p.setPen(QPen(QColor(theme.LINE), 1))
                p.drawRect(r)
                continue

            terrain = TERRAIN[t.terrain]
            base = QColor(theme.tint(terrain.tint))
            base.setAlpha(38 if t.visited else 22)
            p.fillRect(r, base)
            p.setPen(QPen(QColor(theme.LINE2 if t.visited else theme.LINE), 1))
            p.drawRect(r)

            if t.feature and not t.resolved:
                f = FEATURES[t.feature]
                p.setPen(QPen(QColor(theme.tint(f.tint)), 1.6))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(r.center(), 9, 9)
                bold = QFont(theme.mono_family(), 8)
                bold.setBold(True)
                p.setFont(bold)
                p.drawText(QRectF(r.center().x() - 9, r.center().y() - 9, 18, 18),
                           Qt.AlignmentFlag.AlignCenter, feature_mark(t.feature))
            elif t.feature and t.resolved:
                p.setPen(QPen(QColor(theme.INK3), 1))
                c = r.center()
                p.drawLine(int(c.x() - 5), int(c.y() - 5),
                           int(c.x() + 5), int(c.y() + 5))
                p.drawLine(int(c.x() - 5), int(c.y() + 5),
                           int(c.x() + 5), int(c.y() - 5))

            if (t.x, t.y) == exp_sim.LANDER:
                p.setPen(QPen(QColor(theme.tint("chloro")), 1.4))
                p.drawRect(r.adjusted(9, 9, -9, -9))

            p.setFont(QFont(theme.mono_family(), 7))
            p.setPen(QColor(theme.INK3))
            p.drawText(r.adjusted(4, 2, -2, 0), Qt.AlignmentFlag.AlignLeft,
                       terrain.name.split()[0][:6].upper())

        # the party
        pr = QRectF(exp.x * CELL + 1, exp.y * CELL + 1, CELL - 2, CELL - 2)
        p.setPen(QPen(QColor(theme.tint("lumen")), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(pr.center(), 15, 15)
        p.end()
