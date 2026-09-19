"""The Qt set-up every interface check needs, written once.

Not a suite. Before this, `def _app()` was written out in eighteen check
files (eleven byte-for-byte the same), four more copied `_overlap`, and 89
files built their own `QApplication` inline. The copies had already drifted
in the one way that matters: some held the application in a module global
and some did not, and **a `QApplication` nobody holds a reference to can be
collected while its widgets are still alive** — which is a segfault in a
later suite, not a failure in this one.

Everything here imports Qt lazily, so importing `qtkit` costs nothing on a
machine without PyQt6; only calling it does.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

#: The one application object for the process, held so it is never collected.
_HELD: list = []


def use_offscreen() -> None:
    """Point Qt at its bundled plugins and render without a display."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
        try:
            import PyQt6
        except ImportError:
            return
        plugins = Path(PyQt6.__file__).parent / "Qt6" / "plugins" / "platforms"
        if plugins.is_dir():
            os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins)


def app():
    """The process's `QApplication`, made offscreen if it is not made yet."""
    use_offscreen()
    from PyQt6.QtWidgets import QApplication
    instance = QApplication.instance() or QApplication([])
    assert instance is not None
    if not _HELD:
        _HELD.append(instance)
    return instance


def overlap(a: set, b: set) -> float:
    """How alike two silhouettes are: 0 (nothing shared) to 1 (identical).

    Jaccard over the sets of lit cells. Empty against anything is 0, not a
    division by zero: a picture that drew nothing resembles nothing.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def redirect_save() -> Path:
    """Make sure a window built here cannot autosave over the player.

    `tests/__init__.py` sets `SEEDFALL_SAVE` on import, and `core.save`
    already sends a headless process to a scratch file — but a probe that
    imports `ui.window` directly, with a display, has neither. A window
    autosaves the moment its calendar moves, and on 2026-09-17 one built
    without a redirect wrote over the player's chronicle. Checked here, per
    window, rather than trusted.
    """
    from ..core import save as save_mod
    if not os.environ.get(save_mod.SAVE_ENV):
        os.environ[save_mod.SAVE_ENV] = str(
            Path(tempfile.gettempdir()) / f"seedfall-test-{os.getpid()}.json")
    where = save_mod.save_path()
    assert where != save_mod.SAVE_DIR / save_mod.SAVE_NAME, (
        f"a test window would save to the player's own file, {where}")
    return where


def main_window(game, size: tuple | None = (1360, 880), *,
                confirm: bool = False, quiet: bool = True):
    """A `MainWindow` over `game` that cannot block, and cannot save on you.

    Dialogs return at once (`confirm` answers every yes/no), toasts are
    swallowed when `quiet`, and the save is redirected before the window
    exists — the order matters, because construction can already autosave.
    """
    app()
    redirect_save()
    from ..ui.window import MainWindow
    win = MainWindow(game)
    if size:
        win.resize(*size)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: confirm
    if quiet:
        win.toast = lambda *a, **k: None
    return win
