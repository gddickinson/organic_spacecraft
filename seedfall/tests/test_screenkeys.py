"""Every screen key reaches its screen — pressed, not looked up.

`test_manual` has long checked that the key *table* is unique, and every one
of the fifteen keys was dead anyway: the rail button and the Screens menu
both bound the same key, and Qt answers two shortcuts on one key by firing
neither ("Ambiguous shortcut overload"). A table can be right while the
keyboard is wrong, so this sends real key events to a real window.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()


def run(suite) -> bool:
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication
    except ImportError as err:
        print(f"── screen keys ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.state import new_game
    from ..data.screens import SCREENS
    from ..ui import theme
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    game = new_game("keys-test-seed")
    win = MainWindow(game)
    win.resize(1360, 880)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    win.show()
    win.activateWindow()
    app.processEvents()

    special = {"-": Qt.Key.Key_Minus, "?": Qt.Key.Key_Question}

    @suite.check("every screen key opens its screen when pressed")
    def _():
        reached, missed = [], []
        for sid, _label, key in SCREENS:
            if sid not in win.views:
                continue
            win.go("map" if sid != "map" else "system")
            app.processEvents()
            code = special.get(key) or Qt.Key(ord(key.upper()))
            # A symbol is sent as itself: Qt's shortcut map matches "?" on
            # the key, and a real keyboard's Shift is folded in by Qt.
            QTest.keyClick(win, code, Qt.KeyboardModifier.NoModifier)
            app.processEvents()
            (reached if win.current == sid else missed).append(f"{key}→{sid}")
        assert not missed, f"dead keys: {missed}"
        return f"{len(reached)} of {len(reached)} keys reach their screen"

    @suite.check("no key is bound twice anywhere in the window")
    def _():
        from PyQt6.QtGui import QAction
        seen: dict[str, str] = {}
        twice = []
        for act in win.findChildren(QAction):
            for seq in act.shortcuts():
                text = seq.toString()
                if text and text in seen and seen[text] != act.text():
                    twice.append(f"{text}: {seen[text]!r} and {act.text()!r}")
                seen.setdefault(text, act.text())
        from PyQt6.QtWidgets import QAbstractButton
        for b in win.findChildren(QAbstractButton):
            text = b.shortcut().toString()
            if text and text in seen:
                twice.append(f"{text}: {seen[text]!r} and button {b.text()!r}")
        assert not twice, twice
        return f"{len(seen)} distinct shortcuts"

    win.close()
    return True
