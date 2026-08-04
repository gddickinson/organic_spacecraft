"""The main window's modal surfaces — the toast, the panel, the question.

Split from `ui/window.py` when the 2026-08-04 review pushed it past five
hundred lines, along the seam the file's own section header already marked.
Bound as methods on `MainWindow` the same way `ui/flight_clock.py`'s are, so
every `win.dialog(...)` call site is untouched.

One law lives here rather than in any caller: **dismissing a dialog is a
refusal, never a choice.** `dialog` returns None on Escape or the window's
close button, and a caller that treats None as one of its buttons has taken a
decision the player deliberately did not — `ui/endings.py` destroyed a save
that way once.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout, QWidget

from . import theme
from .widgets import button, label


def _paragraph_or(w):
    """A paragraph of text becomes a label; a widget passes through.

    Deliberately not `widgets.body_or`, which shares the name and does a
    different job (None → an invisible spacer). The split out of
    `ui/window.py` picked that one up as if it were this one, and the
    opening briefing — plain strings — crashed the first fresh launch of
    the game before the title.
    """
    if isinstance(w, str):
        return label(w, "", wrap=True)
    return w


def toast(self, text: str, kind: str = "") -> None:
    self.statusBar().setStyleSheet(
        f"color: {theme.tint(kind) if kind else theme.INK3};"
        f"font-family: '{theme.mono_family()}'; font-size: 10px;")
    self.statusBar().showMessage(text, 6000)


def dialog(self, heading: str, widgets, buttons=(("Close", None),),
           width: int = 620):
    """A modal panel. ``buttons`` is a list of (label, value).

    Returns the pressed button's value, or **None if the dialog was
    dismissed** — Escape, or the title bar's close. None is not a button.
    """
    dlg = QDialog(self)
    dlg.setWindowTitle(heading)
    dlg.setMinimumWidth(width)
    v = QVBoxLayout(dlg)
    v.setContentsMargins(22, 20, 22, 18)
    v.setSpacing(10)
    v.addWidget(label(heading, "h2"))
    for w in widgets:
        v.addWidget(_paragraph_or(w))
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 8, 0, 0)
    h.addStretch(1)
    result = {"value": None}

    def choose(val):
        result["value"] = val
        dlg.accept()

    for i, (text, val) in enumerate(buttons):
        kind = "primary" if i == 0 else "flat"
        h.addWidget(button(text, lambda v_=val: choose(v_), kind=kind))
    v.addWidget(row)
    dlg.exec()
    return result["value"]


def confirm(self, heading: str, text: str,
            yes: str = "Do it", no: str = "Belay that") -> bool:
    """Ask, unless the player has said not to be asked."""
    from ..sim import options as options_sim
    if not options_sim.get(self.game, "confirm"):
        return True
    return bool(self.dialog(heading, [text], [(yes, True), (no, False)]))
