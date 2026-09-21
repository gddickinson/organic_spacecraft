"""The gunner's window: the sky, the glass over it, and the boards beside it.

One widget, and it holds no state — everything it paints is a read of the
`sim/skirmish.Skirmish` it is handed. The three layers are three modules and
they stack in this order every frame:

1. `ui/turret_scene` — the world out of the blister, from a camera at the
   muzzle looking down the bore.
2. `ui/turret_hud` — the marks *on* the world: the reticle, the lead pip, a
   bracket round everything the sight holds.
3. `ui/turret_panels` — the boards beside it: the target monitor, the contact
   ball, and the directive list when there is a drill running.

**Nothing here decides anything and nothing here keeps a clock.** The window
around it (`ui/turret_window.py`) owns the beat; this is asked to paint
whatever the action says is true at the moment it is asked.
"""

from __future__ import annotations

from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtWidgets import QSizePolicy, QWidget

from . import painting, theme, turret_hud, turret_panels, turret_scene


class TurretGlass(painting.Painted, QWidget):
    """What a gunner sees. Point it at an action and call `update`."""

    def __init__(self, action=None, drill=None):
        super().__init__()
        self.action = action
        self.drill = drill
        self.setMinimumSize(560, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setAutoFillBackground(False)

    def draw(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        action = self.action
        if action is None:
            p.fillRect(0, 0, w, h, QColor("#03070a"))
            p.setPen(QColor(theme.INK3))
            p.setFont(QFont(theme.mono_family(), 10))
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter,
                       "The seat is empty.")
            return
        spots = turret_scene.draw(p, action, w, h)
        turret_hud.draw(p, action, spots, w, h)
        turret_panels.draw(p, action, w, h, self.drill)
        turret_panels.clock(p, action, w, h, self.drill)
        if action.over:
            self._called(p, action, w, h)

    def _called(self, p: QPainter, action, w: int, h: int) -> None:
        """The action is finished with, and the glass says so.

        Over the picture rather than instead of it: a gunner should see the
        sky they left behind while they read what it came to.
        """
        p.fillRect(QRectF(0, h * 0.38, w, 74), QColor(3, 7, 10, 205))
        won = action.outcome == "won"
        ink = QColor(theme.tint("chloro" if won else "bad"))
        p.setPen(ink)
        p.setFont(QFont(theme.mono_family(), 16, QFont.Weight.Bold))
        p.drawText(QRectF(0, h * 0.38 + 8, w, 26),
                   Qt.AlignmentFlag.AlignHCenter,
                   "EXERCISE COMPLETE" if won else "EXERCISE CALLED")
        p.setPen(QColor(theme.INK2))
        p.setFont(QFont(theme.mono_family(), 9))
        p.drawText(QRectF(0, h * 0.38 + 40, w, 20),
                   Qt.AlignmentFlag.AlignHCenter,
                   action.log[-1] if action.log else "")
