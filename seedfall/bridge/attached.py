"""A bridge attached to the *running window*, so a caller drives what you see.

`bridge/server.py` on its own holds a headless `Game`: fine for scripting and
for tests, useless for watching. This attaches the same protocol to a live
`MainWindow`, so a command sent over the socket moves the ship on screen.

The thing that makes it safe is marshalling. Qt owns the main thread and the
whole interface reads the `Game` from it; the bridge's socket runs on another.
Mutating the game from the socket thread while the window paints it is a data
race that shows up as a corrupted screen or a crash, so **every command is
posted to the Qt event loop and the socket thread waits for the result.**
Nothing touches the game off the main thread.

Adds the verbs a watcher needs — moving between screens, and reading back what
is on the one you are looking at.
"""

from __future__ import annotations

import queue

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal

from .protocol import verb
from .server import Bridge

#: How long a command may wait for the main thread before giving up.
PATIENCE = 15.0


class _Pump(QObject):
    """Runs work on the Qt thread on behalf of whoever asked."""

    wanted = pyqtSignal(object)

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.wanted.connect(self._do, Qt.ConnectionType.QueuedConnection)

    def _do(self, job) -> None:
        box, fn = job
        try:
            box.put(("ok", fn()))
        except Exception as err:                  # noqa: BLE001 - boundary
            box.put(("no", err))

    def run(self, fn):
        """Called from the socket thread. Blocks until Qt has done the work."""
        box: queue.Queue = queue.Queue(maxsize=1)
        self.wanted.emit((box, fn))
        try:
            kind, value = box.get(timeout=PATIENCE)
        except queue.Empty:
            raise TimeoutError("the window did not answer in time")
        if kind == "no":
            raise value
        return value


class AttachedBridge(Bridge):
    """The protocol, over the game the window is actually showing."""

    def __init__(self, win, host: str = "127.0.0.1", port: int = 0):
        super().__init__(win.game, host, port)
        self.win = win
        self.pump = _Pump(win)

    def handle(self, command: dict) -> dict:
        # The game the window holds can be replaced — beginning again, or
        # carrying past an ending — so read it fresh rather than caching.
        self.game = self.win.game
        reply = self.pump.run(lambda: super(AttachedBridge, self).handle(command))
        # Anything that moves the world should be visible before the caller is
        # told it happened.
        if isinstance(reply, dict) and reply.get("ok"):
            self.pump.run(self.win.refresh)
        return reply


# ── verbs a watcher needs ──────────────────────────────────────────────────

@verb("go", "Open a screen, so somebody watching can see where you are.")
def go(game, screen: str) -> dict:
    win = _window_of(game)
    if win is None:
        return {"ok": False, "why": "No window attached."}
    from ..data.screens import KEY_FOR
    if screen not in KEY_FOR:
        return {"ok": False, "why": f"No such screen: {screen}.",
                "screens": sorted(KEY_FOR)}
    win.go(screen)
    return {"ok": True, "screen": win.current}


@verb("screen", "What screen is open, and what the window is showing.")
def screen(game) -> dict:
    win = _window_of(game)
    if win is None:
        return {"ok": False, "why": "No window attached."}
    view = win.views.get(win.current)
    return {"ok": True, "screen": win.current,
            "tab": getattr(view, "tab", None),
            "title": win.windowTitle(),
            "log": [text for _day, text, _kind in list(game.log)[-6:]]}


@verb("tab", "Switch tabs on a screen that has them.")
def tab(game, name: str) -> dict:
    win = _window_of(game)
    if win is None:
        return {"ok": False, "why": "No window attached."}
    view = win.views.get(win.current)
    if view is None or not hasattr(view, "tab"):
        return {"ok": False, "why": f"{win.current} has no tabs."}
    view.tab = name
    win.go(win.current)
    return {"ok": True, "screen": win.current, "tab": view.tab}


@verb("shot", "Save a picture of the window, so the caller can see it too.")
def shot(game, path: str = "") -> dict:
    win = _window_of(game)
    if win is None:
        return {"ok": False, "why": "No window attached."}
    import os
    import tempfile
    target = path or os.path.join(tempfile.gettempdir(),
                                  f"seedfall-{win.current}.png")
    ok = win.grab().save(target)
    return {"ok": bool(ok), "path": target, "screen": win.current}


#: Set when a bridge attaches, so the verbs above can find the window.
_ATTACHED = {}


def _window_of(game):
    return _ATTACHED.get(id(game)) or _ATTACHED.get("any")


def attach(win, port: int = 0) -> AttachedBridge:
    """Put a bridge in front of a live window and start serving."""
    bridge = AttachedBridge(win, port=port)
    _ATTACHED["any"] = win
    _ATTACHED[id(win.game)] = win
    bridge.start()
    return bridge

