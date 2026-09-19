"""The first officer's counsel, as a card on the Sector Chart.

Three rows — what, why — each with "Take me there", which opens the screen
the move is made on with the thing selected: the right tab, the right star.
It never makes the move itself; the screen it opens does, through its own
button. Dismissed, it keeps quiet for a month; Help → "The first officer's
counsel" brings it back at once. Every word is `sim/counsel`'s.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..sim import counsel, renown
from .widgets import Panel, button, label, note


def build(view, game) -> QWidget:
    """The card, or an empty widget while the first officer keeps quiet."""
    if renown.counsel_quiet(game):
        empty = QWidget()
        empty.hide()
        return empty
    moves = counsel.advise(game)
    p = Panel("First officer suggests…", "lumen")
    p.setObjectName("counsel")
    if not moves:
        p.add(note("Nothing needs you this minute. The chart is yours."))
    for i, move in enumerate(moves):
        p.add(_row(view, move, i))
    p.add_buttons(button("Not now", lambda: _dismiss(view), kind="flat",
                         tip="Quiet for a month; Help brings it back"))
    return p


def _row(view, move: dict, index: int) -> QWidget:
    row = QWidget()
    h = QHBoxLayout(row)
    h.setContentsMargins(0, 2, 0, 2)
    h.setSpacing(8)
    words = QWidget()
    v = QVBoxLayout(words)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(1)
    v.addWidget(label(move["title"], "",
                      "warn" if move["weight"] >= 96 else "chloro", wrap=True))
    v.addWidget(label(move["blocked"] or move["why"], "", "dim", wrap=True))
    h.addWidget(words, 1)
    go = button("Take me there", lambda _=False, m=move: take(view.win, m),
                kind="primary" if index == 0 else "")
    go.setObjectName(f"counsel:{index}")
    h.addWidget(go)
    return row


def take(win, move: dict) -> str:
    """Open the screen a move is made on, with its thing selected. Returns
    the screen it opened, so the suite can hold it to the move."""
    screen = move["screen"]
    view = win.views.get(screen)
    if view is None:
        win.toast(f"No such screen: {screen}.", "warn")
        return ""
    if move.get("tab"):
        if screen == "law":
            view.hunts_tab = move["tab"]
        else:
            view.tab = move["tab"]
    if move.get("system") is not None and hasattr(view, "selected") \
            and screen == "map":
        view.selected = move["system"]
    win.go(screen)
    return screen


def _dismiss(view) -> None:
    renown.dismiss_counsel(view.game)
    view.win.refresh()


def recall(win) -> None:
    """The menu's door: the counsel back, and the chart it lives on."""
    renown.recall_counsel(win.game)
    win.go("map")
