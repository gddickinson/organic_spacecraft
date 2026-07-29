"""The docking approach, drawn: where the collar is and where you are.

The approach was three numbers and six buttons. Everything the mini-game
models — an error per axis, a drift per axis, a readout blurred by how good
your sensors are, a precision set by the hull and the navigator — reached the
player as `Closing range: -45`, and the drift reached them not at all.

So this draws it. Two of the axes are a position: closing range up the plot,
attitude across it, with the tolerance box at the centre — get inside the box
on both and those two are done. Roll is the third, drawn as the tilt of the
hull against the collar, because a roll error is not a position and pretending
it is would be a prettier lie than the numbers were.

The ghost is where the next correction leaves you, drift included. That is the
part the numbers could not show at all: firing on one axis lets the other two
walk, and a pilot who fixed the worst reading three times running could watch
the other two slide out of tolerance without ever being told why.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..sim import minigames as mg
from . import theme

#: Units of error that fill the plot from centre to edge.
SPAN = 52.0


class ApproachPlot(QWidget):
    """The collar, the hull, the tolerance box, and where the next burn lands."""

    SIZE = 320

    def __init__(self, docking, preview=None):
        super().__init__()
        self.d = docking
        #: (axis, amount) the player is hovering, or None.
        self.preview = preview
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def _at(self, error: dict) -> QPointF:
        half = self.SIZE / 2
        scale = (half - 26) / SPAN
        return QPointF(half + error.get("attitude", 0) * scale,
                       half + error.get("range", 0) * scale)

    def paintEvent(self, _ev):  # noqa: N802
        d = self.d
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        half = self.SIZE / 2
        scale = (half - 26) / SPAN

        # The collar: rings at each tolerance multiple, so "how far out" has a
        # shape rather than a number.
        for ring in (1, 2, 3):
            radius = mg.TOLERANCE * ring * scale
            p.setPen(QPen(QColor(150, 196, 176, 46 if ring > 1 else 96), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(half, half), radius, radius)

        # The tolerance box itself — inside this on both axes and they are in.
        box = mg.TOLERANCE * scale
        p.setPen(QPen(QColor(theme.tint("chloro")), 1.2, Qt.PenStyle.DashLine))
        p.drawRect(QRectF(half - box, half - box, box * 2, box * 2))

        # Cross-hairs, labelled, so the axes are not a guess.
        p.setPen(QPen(QColor(150, 196, 176, 40), 1))
        p.drawLine(QPointF(half, 8), QPointF(half, self.SIZE - 8))
        p.drawLine(QPointF(8, half), QPointF(self.SIZE - 8, half))
        p.setFont(QFont(theme.mono_family(), 7))
        p.setPen(QColor(169, 194, 182, 150))
        p.drawText(QRectF(half + 4, 6, 120, 12),
                   Qt.AlignmentFlag.AlignLeft, "range")
        p.drawText(QRectF(self.SIZE - 84, half - 14, 78, 12),
                   Qt.AlignmentFlag.AlignRight, "attitude")

        # Where the next correction leaves you, drift and all.
        if self.preview:
            axis, amount = self.preview
            plan = mg.forecast(d, axis, amount)
            ghost = self._at(plan["after"])
            tint = QColor(theme.tint("lumen"))
            tint.setAlphaF(0.45)
            p.setPen(QPen(tint, 1.0, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(self._at(d.error), ghost)
            self._hull(p, ghost, plan["after"].get("roll", 0), tint, 0.5)

        self._hull(p, self._at(d.error), d.error.get("roll", 0),
                   QColor(theme.tint("warn" if not d.aligned else "chloro")),
                   1.0)
        p.end()

    def _hull(self, p, at: QPointF, roll: int, colour: QColor, weight: float):
        """The hull, tilted by its roll error against the collar."""
        rad = math.radians(roll * 2.2)
        p.setPen(QPen(colour, 1.6 * weight))
        p.setBrush(Qt.BrushStyle.NoBrush)
        nose = QPointF(at.x() + math.sin(rad) * 12,
                       at.y() - math.cos(rad) * 12)
        left = QPointF(at.x() + math.sin(rad + 2.5) * 9,
                       at.y() - math.cos(rad + 2.5) * 9)
        right = QPointF(at.x() + math.sin(rad - 2.5) * 9,
                        at.y() - math.cos(rad - 2.5) * 9)
        p.drawPolygon(QPolygonF([nose, left, right]))
        # The roll bar: a level line through the hull, so a tilt reads as a
        # tilt rather than as a number called "roll".
        p.setPen(QPen(colour, 1.0 * weight, Qt.PenStyle.DotLine))
        p.drawLine(QPointF(at.x() - math.cos(rad) * 14,
                           at.y() - math.sin(rad) * 14),
                   QPointF(at.x() + math.cos(rad) * 14,
                           at.y() + math.sin(rad) * 14))
