"""Application entry point: build the Qt app, show the title screen, run."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from ..core import state as state_mod
from ..data.lore import TITLE
from . import theme
from .title import ask_for_game, opening_briefing
from .window import MainWindow


def build_app(argv=None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(TITLE)
    app.setApplicationDisplayName(TITLE)
    app.setStyleSheet(theme.stylesheet())
    return app


def main(argv=None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    app = build_app([sys.argv[0] if sys.argv else TITLE])

    seed = None
    if "--seed" in args:
        i = args.index("--seed")
        if i + 1 < len(args):
            seed = args[i + 1]

    if "--new" in args or seed:
        state_mod.clear_save()
        game = state_mod.new_game(seed)
        fresh = True
    else:
        game = ask_for_game()
        fresh = game is not None and game.day == 0
        if game is None:
            return 0

    win = MainWindow(game)
    win.show()
    QGuiApplication.processEvents()
    if fresh:
        opening_briefing(win)
    return app.exec()
