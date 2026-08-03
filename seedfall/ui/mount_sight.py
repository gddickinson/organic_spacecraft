"""A sight down one mount: its arc, and where the target sits in it.

The battle screen has told a gunner "the Fusion Lance will not train that far —
34° outside its broadside arc" in a log line for as long as the arcs have
existed. That is the right fact and the wrong medium: a number in a paragraph is
something to be believed, and an arc with the target outside it is something to
be *seen*, and then argued with by coming about.

So this is a boresight. The mount's arc is the lit wedge, the bore is up the
middle, and the target is a mark at its true relative bearing. When the mark is
inside the wedge the mount bears; when it is outside, the gap the hull must turn
is the arc between them, drawn as the thing it is.

Geometry only — `sim/firing.arc_span` for the wedge and `Shot.gap` for the miss,
both of which already existed and neither of which had ever been drawn.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..sim import firing
from . import theme
from . import painting

#: How much of the widget the arc's outer edge uses.
REACH = 0.86

#: Tints per state, matching `Shot.blocked_by` so the sight and the board agree.
STATE = {
    "ready": "lumen",
    "marginal": "amber",
    "arc": "rust",
    "dry": "rust",
    "range": "amber",
}


class MountSight(QWidget):
    """One mount's arc with the target marked in it."""

    def __init__(self, shot=None, bearing: float = 0.0, parent=None):
        super().__init__(parent)
        self.shot = shot
        self.bearing = bearing
        self.setMinimumSize(132, 132)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def show_mount(self, shot, bearing: float) -> None:
        self.shot = shot
        self.bearing = bearing
        self.update()

    # ── painting ───────────────────────────────────────────────────────────

    @painting.safe_paint
    def paintEvent(self, _event) -> None:      # noqa: N802
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor(theme.PANEL2))
        shot = self.shot
        if shot is None:
            p.setPen(QPen(QColor(theme.INK3)))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                       "no mount")
            return

        mid = QPointF(w / 2.0, h / 2.0)
        reach = min(w, h) * 0.5 * REACH
        tint = QColor(theme.tint(STATE.get(shot.blocked_by, "amber")))

        self._rings(p, mid, reach)
        self._wedge(p, mid, reach, shot, tint)
        self._target(p, mid, reach, shot, tint)
        self._caption(p, w, h, shot, tint)
        p.end()

    def _rings(self, p: QPainter, mid: QPointF, reach: float) -> None:
        """The hull at the middle, and a bearing circle round it."""
        p.setPen(QPen(QColor(theme.LINE), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(mid, reach, reach)
        p.drawEllipse(mid, reach * 0.5, reach * 0.5)
        # The nose, so "outside the arc" has a side to be outside of.
        p.setPen(QPen(QColor(theme.INK3), 1.0, Qt.PenStyle.DashLine))
        p.drawLine(mid, QPointF(mid.x(), mid.y() - reach))

    def _wedge(self, p: QPainter, mid: QPointF, reach: float, shot,
               tint: QColor) -> None:
        """The arc this mount can train through, both sides of the bow.

        **`arc_span` returns half-angles**, which its own docstring says and my
        first draft ignored: `fore` is (0, 60) meaning sixty degrees either side,
        and `broad` is (60, 120) meaning *both* beams. Drawing one wedge from 0
        to 60 put a fore arc entirely to starboard. `ui/tactical_plot.py` had
        already been fixed for the same thing and left the reason behind it —
        "drawing only one of them is a lie about the ship" — which is what this
        widget was doing while looking plausible, because the target happened to
        be near dead ahead when I looked at it.
        """
        low, high = firing.arc_span(shot.arc)
        box = QRectF(mid.x() - reach, mid.y() - reach, reach * 2, reach * 2)
        fill = QColor(tint)
        fill.setAlpha(46)
        if high - low >= 180:
            # An all-round mount traverses everywhere. A wedge covering the
            # whole circle says nothing; a ring says "this one always bears".
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(tint, 1.4, Qt.PenStyle.DashLine))
            p.drawEllipse(mid, reach, reach)
            return
        p.setBrush(fill)
        p.setPen(QPen(tint, 1.4))
        # Qt measures anticlockwise from three o'clock in sixteenths; the game
        # measures degrees off the bow, mirrored.
        for sign in (1, -1):
            start = int((90.0 - sign * low) * 16)
            p.drawPie(box, start, int(-sign * (high - low) * 16))

    def _target(self, p: QPainter, mid: QPointF, reach: float, shot,
                tint: QColor) -> None:
        """Where the other hull actually is, at its signed relative bearing."""
        rad = math.radians(self.bearing)
        at = QPointF(mid.x() + math.sin(rad) * reach * 0.78,
                     mid.y() - math.cos(rad) * reach * 0.78)
        mark = QColor(theme.tint("lumen" if shot.in_arc else "rust"))
        p.setPen(QPen(mark, 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(at, 5.5, 5.5)
        p.drawLine(QPointF(at.x() - 9, at.y()), QPointF(at.x() - 3, at.y()))
        p.drawLine(QPointF(at.x() + 3, at.y()), QPointF(at.x() + 9, at.y()))

        # The turn that would fix it, swept from the target back toward the arc
        # — which is the whole argument for coming about. `Shot.gap` is the sim's
        # own answer to how far, so the picture cannot disagree with the log
        # line beside it.
        if not shot.in_arc and shot.gap > 0.5:
            p.setPen(QPen(QColor(theme.tint("rust")), 1.0,
                          Qt.PenStyle.DotLine))
            box = QRectF(mid.x() - reach * 0.62, mid.y() - reach * 0.62,
                         reach * 1.24, reach * 1.24)
            # Toward the bow if the target is abaft the arc, away if forward of
            # it; the sign of the bearing says which side it is on.
            toward = -1.0 if self.bearing >= 0 else 1.0
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawArc(box, int((90.0 - self.bearing) * 16),
                      int(toward * -shot.gap * 16))

    def _caption(self, p: QPainter, w: int, h: int, shot,
                 tint: QColor) -> None:
        p.setFont(QFont(theme.mono_family(), 8))
        p.setPen(QPen(QColor(theme.INK3)))
        p.drawText(QRectF(2, 2, w - 4, 14),
                   Qt.AlignmentFlag.AlignLeft, shot.name[:22])
        p.setPen(QPen(tint))
        said = (f"{shot.arc_name} · bears" if shot.in_arc
                else f"{shot.arc_name} · {round(shot.gap)}° off")
        p.drawText(QRectF(2, h - 16, w - 4, 14),
                   Qt.AlignmentFlag.AlignLeft, said)
