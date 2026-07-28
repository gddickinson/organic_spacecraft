"""Drive real drop-down clicks, in a process that is allowed to die.

A player segfaulted the game choosing from a combo box. The stack named
`QComboBoxPrivateContainer::eventFilter`: the popup was still delivering the
mouse release that dismissed it when the handler rebuilt the screen and freed
the combo underneath it.

Five hundred checks had missed it, because every driver in the suite chooses
from a combo by calling `setCurrentIndex` or emitting `activated`. Neither
opens a popup, and the crash lives entirely inside the popup's event filter.

So this sends **real mouse events to the popup's viewport** — the actual path
— and the invariant is the one that matters: *the combo must still be alive at
the instant Qt returns from delivering the event.* Not afterwards; a rebuild
on the next turn of the loop is allowed to free it, and does.

It runs as its own process because the failure mode is a signal, not an
exception. A check that asserts this in-process does not fail — it takes the
whole suite down with it. `test_verbs` spawns this and reads the exit code:

    0  every drop-down survived its own click
    1  a combo was freed mid-event (the bug, caught cleanly)
  139  the bug, caught the way the player found it
"""

from __future__ import annotations

import sys


def main() -> int:
    from .test_ui import _use_offscreen
    _use_offscreen()

    from PyQt6 import sip
    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QApplication, QComboBox

    from ..core.state import new_game
    from ..ui.window import MainWindow, NAV

    app = QApplication.instance() or QApplication([])
    checked, bad = 0, []

    for screen, *_rest in NAV:
        # A fresh window per combo: the first rebuild frees the others, so a
        # list gathered once is a list of corpses by the second click.
        game = new_game(f"popup-{screen}")
        game.credits = 400000
        probe = MainWindow(game)
        probe.toast = lambda *a, **k: None
        probe.go(screen)
        for _ in range(3):
            app.processEvents()
        count = len(probe.views[screen].findChildren(QComboBox))
        probe.close()

        for index in range(count):
            game = new_game(f"popup-{screen}-{index}")
            game.credits = 400000
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.resize(1300, 800)
            win.show()
            win.go(screen)
            for _ in range(3):
                app.processEvents()
            combos = win.views[screen].findChildren(QComboBox)
            if index >= len(combos) or combos[index].count() < 2:
                win.close()
                continue
            combo = combos[index]

            combo.showPopup()
            for _ in range(3):
                app.processEvents()
            view = combo.view()
            rect = view.visualRect(combo.model().index(1, 0))
            where = QPointF(rect.center())
            for kind in (QEvent.Type.MouseButtonPress,
                         QEvent.Type.MouseButtonRelease):
                QApplication.sendEvent(view.viewport(), QMouseEvent(
                    kind, where, where, Qt.MouseButton.LeftButton,
                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
            # The instant that matters: Qt has just returned from delivering
            # the click that dismissed the popup.
            if sip.isdeleted(combo):
                bad.append(f"{screen}[{index}]")
            checked += 1
            for _ in range(4):
                app.processEvents()
            win.close()

    if bad:
        print(f"combos freed mid-click: {', '.join(bad)}")
        return 1
    print(f"{checked} drop-downs clicked for real, every one alive on return")
    return 0


if __name__ == "__main__":
    sys.exit(main())
