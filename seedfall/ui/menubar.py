"""The menu bar: everything the window can do, in one place you can find.

The rail reaches the screens and the HUD has two buttons, which leaves a
handful of things — options, the instruments, saving, starting again — with no
obvious home. This is that home.

Built from the same tables as everything else: the screens and their keys come
from `data/screens.py`, the instruments from `ui/monitors.SHAPES`, so a screen
or an instrument added tomorrow appears here without anybody editing a list.
"""

from __future__ import annotations

from PyQt6.QtGui import QAction, QKeySequence

from ..data.screens import SCREENS
from . import monitors


def _act(parent, text: str, on_go, shortcut: str = "", tip: str = "") -> QAction:
    action = QAction(text, parent)
    if shortcut:
        action.setShortcut(QKeySequence(shortcut))
    if tip:
        action.setStatusTip(tip)
    action.triggered.connect(lambda _checked=False: on_go())
    return action


def build(win) -> None:
    """Hang a menu bar on the window. Called once, from `MainWindow`."""
    bar = win.menuBar()
    bar.setNativeMenuBar(False)      # keep it in the window, where the theme is
    bar.clear()

    chronicle = bar.addMenu("&Chronicle")
    chronicle.addAction(_act(win, "Save now", win.save, "Ctrl+S",
                             "The chronicle also saves itself as time passes"))
    chronicle.addAction(_act(win, "Options…", win.open_options, "Ctrl+,",
                             "Everything you can set"))
    chronicle.addSeparator()
    chronicle.addAction(_act(win, "Begin again…", win.begin_again,
                             tip="Abandon this chronicle and start another"))
    chronicle.addAction(_act(win, "Quit", win.close, "Ctrl+Q"))

    screens = bar.addMenu("&Screens")
    for sid, text, key in SCREENS:
        name = text.split("  ", 1)[-1]
        screens.addAction(_act(win, name, lambda s=sid: win.go(s), key))

    instruments = bar.addMenu("&Instruments")
    for name, (title, _cls, _size) in monitors.SHAPES.items():
        instruments.addAction(_act(
            win, title, lambda i=name: monitors.toggle(win, i),
            tip="Opens in its own window and stays on top"))
    instruments.addSeparator()
    instruments.addAction(_act(win, "Open them all",
                               lambda: monitors.open_all(win)))
    instruments.addAction(_act(win, "Close them all",
                               lambda: monitors.close_all(win)))

    help_menu = bar.addMenu("&Help")
    help_menu.addAction(_act(win, "Help on this screen", win.help_here, "F1"))
    help_menu.addAction(_act(win, "Manual", lambda: win.open_help("manual")))
    help_menu.addAction(_act(win, "Keys", lambda: win.open_help("keys")))
    help_menu.addAction(_act(win, "Options…", win.open_options))
    return bar
