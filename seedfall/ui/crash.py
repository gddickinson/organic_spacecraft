"""What happens when something goes wrong inside the running window.

**Without this, any exception in a Qt slot killed the game.** PyQt aborts
the process on an unhandled exception unless `sys.excepthook` has been
replaced — and only the test harness ever replaced it. So a slip anywhere
in a click handler (measured: two keys queued in the Help search box) ended
the chronicle with exit 134, no message and nothing saved since the last
autosave.

Now the hook writes the traceback to ``crash.log`` beside the save, writes
the chronicle to a separate ``recovery.json`` (never over the real save —
a game that just raised may be in a state nobody should resume blindly),
and tells the player where both went. The window stays up.
"""

from __future__ import annotations

import sys
import time
import traceback

from ..core import save as save_mod

_installed = False


def paths() -> tuple:
    """Where the crash log and the recovery save go: beside the real save."""
    here = save_mod.save_path().parent
    return here / "crash.log", here / "recovery.json"


def record(exc_type, exc, tb, game=None) -> dict:
    """Write the log and, if there is a game, a recovery save. Never raises."""
    log_path, recovery = paths()
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    out = {"log": None, "recovery": None, "text": text}
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{text}")
        out["log"] = log_path
    except OSError:
        pass
    if game is not None:
        strict, save_mod.STRICT = save_mod.STRICT, False
        try:
            if save_mod.write(game.to_save(), recovery):
                out["recovery"] = recovery
        except Exception:                                      # noqa: BLE001
            pass
        finally:
            save_mod.STRICT = strict
    return out


def install(get_game) -> None:
    """Replace `sys.excepthook` for the running app. `get_game` returns the
    live Game or None; it is asked at the moment of the crash."""
    global _installed
    if _installed:
        return
    _installed = True

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        try:
            game = get_game()
        except Exception:                                      # noqa: BLE001
            game = None
        out = record(exc_type, exc, tb, game)
        sys.stderr.write(out["text"])
        _tell(exc, out)

    sys.excepthook = hook


def _tell(exc, out) -> None:
    """Say so, in the window, without blocking a headless run."""
    try:
        from PyQt6.QtGui import QGuiApplication
        from PyQt6.QtWidgets import QMessageBox
        if QGuiApplication.platformName() in ("offscreen", "minimal"):
            return
        where = []
        if out.get("recovery"):
            where.append(f"The chronicle was saved to {out['recovery']}.")
        if out.get("log"):
            where.append(f"Details are in {out['log']}.")
        QMessageBox.warning(
            None, "Something went wrong",
            f"The game hit an error and carried on: {exc!r}\n\n"
            + " ".join(where) + "\n\nYour own save has not been touched.")
    except Exception:                                          # noqa: BLE001
        pass
