"""A strip along the top saying what to try next. Not a cage.

It never blocks a screen and never opens a dialog. A tutorial that stops you
doing the thing it is describing is worse than none, and this game is
explicitly about there being no track — so the strip suggests, points at the
screen, and gets out of the way when the thing has been done.

It shows nothing at all once the tutorial is finished or skipped.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..sim import tutorial as tutorial_sim
from . import theme
from .widgets import button, label


class TutorialBar(QWidget):
    """One line of instruction, a place to go, and a way out."""

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.box = QVBoxLayout(self)
        self.box.setContentsMargins(16, 6, 16, 6)
        self.box.setSpacing(2)
        self.refresh()

    def refresh(self) -> None:
        while self.box.count():
            item = self.box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                # Unparent *now*, then schedule deletion. `deleteLater` alone
                # leaves the old widget painted until the event loop gets
                # round to it, which shows as the previous lesson's text
                # ghosting under the new one.
                widget.setParent(None)
                widget.deleteLater()

        standing = tutorial_sim.state(self.win.game)
        if not standing.get("running"):
            self.setVisible(False)
            return
        self.setVisible(True)
        explaining = standing["explaining"]
        tint = "lumen" if explaining else "chloro"
        self.setStyleSheet(
            f"background: {theme.PANEL2};"
            f"border-bottom: 1px solid {theme.tint(tint)};")

        head = QWidget()
        row = QHBoxLayout(head)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)
        # `known` is steps stepped over because the captain had already done
        # them — the tutorial is startable from the Help screen at any time, so a
        # veteran restarting it opens at step three of eight. Saying so is the
        # difference between that and looking broken.
        done = standing.get("known") or 0
        row.addWidget(label(
            f"{standing['step']} of {standing['of']} · "
            + ("What just happened" if explaining
               else standing["lesson"].title)
            + (f" · {done} you had already done" if done else ""),
            "label", tint))
        row.addStretch(1)
        if explaining:
            row.addWidget(button("Got it", self._next, kind="primary"))
        elif standing["screen"] and self.win.current != standing["screen"]:
            row.addWidget(button(f"Take me there",
                                 lambda s=standing["screen"]: self.win.go(s)))
        row.addWidget(button("Skip the tutorial", self._skip, kind="flat"))
        self.box.addWidget(head)

        body = label(standing["text"], "", wrap=True)
        body.setMaximumHeight(72)
        self.box.addWidget(body)

    def _next(self) -> None:
        tutorial_sim.acknowledge(self.win.game)
        self.win.save()
        self.win.refresh()

    def _skip(self) -> None:
        if not self.win.confirm(
                "Skip the tutorial",
                "It can be started again from the Help screen at any time."):
            return
        tutorial_sim.skip(self.win.game)
        self.win.save()
        self.win.refresh()
