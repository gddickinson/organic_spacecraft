"""Application entry point: build the Qt app, show the title screen, run."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication

from ..core import state as state_mod
from ..data.lore import TITLE
from . import theme
from .title import ask_for_game, offer_tutorial, opening_briefing
from .window import MainWindow


def build_app(argv=None) -> QApplication:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(TITLE)
    app.setApplicationDisplayName(TITLE)
    app.setStyleSheet(theme.stylesheet())
    return app


def main(argv=None) -> int:
    """Run the game. `argv` is a list of flags or already-parsed options
    (`core/cli`); `python -m seedfall` parses before Qt is imported."""
    from ..core import cli
    options = (argv if argv is not None and not isinstance(argv, list)
               else cli.parse(argv if argv is not None else sys.argv[1:]))
    app = build_app([sys.argv[0] if sys.argv else TITLE])

    if options.new:
        game = state_mod.begin_new(options.seed)
        fresh = True
    else:
        game = ask_for_game()
        fresh = game is not None and game.day == 0
        if game is None:
            return 0

    win = MainWindow(game)
    # Installed once the window exists, so a crash can save what it holds.
    from . import crash
    crash.install(lambda: getattr(win, "game", None))
    win.show()
    QGuiApplication.processEvents()

    if options.bridge:
        # A bridge over the *running* window, so somebody outside can drive
        # what is on screen. Loopback only, token required, and every command
        # is marshalled onto this thread before it touches the game.
        import json
        from ..bridge.attached import attach
        bridge = attach(win, port=options.port)
        print("BRIDGE " + json.dumps(bridge.address()), flush=True)
    if fresh and not options.bridge:
        opening_briefing(win)
        offer_tutorial(win)
    elif fresh:
        # A driven session must not open behind a modal dialog. The briefing
        # and the tutorial offer both block on `exec()`, and a watcher sees a
        # pop-up while the bridge quietly plays the game underneath it —
        # which is exactly what happened the first time this was demonstrated.
        win.game.add_log("Opened under a bridge: briefing skipped so the "
                         "window is not blocked.", "")
        win.refresh()
    return app.exec()
