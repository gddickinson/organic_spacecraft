"""The ship's log down the right of the window: built once, then appended to.

Lifted out of `ui/window.py`, which was at its five-hundred-line limit, and
rewritten on the way.

**It rebuilt all sixty entries on every refresh.** `MainWindow.refresh` runs
after every button in the game, and the log threw away sixty stardate-and-
text widgets and made sixty new ones each time — measured at 46 ms a refresh
when *nothing* had been logged, a third of a Port purchase. Now it keys on
the newest entry it has drawn: when that is still the newest, a refresh costs
nothing; when entries were added it puts only those at the top and lets the
oldest go off the bottom; only a different chronicle (a load, a new game)
rebuilds the column.

**It also folds away when the window is narrow.** At the enforced minimum of
1040 px, a 300 px log beside a 158 px rail left the screens 580 px, and eleven
of fifteen of them were wider than that. Below `FOLD_BELOW` the log folds to a
strip with a button; the player can open it again, and their choice holds
until the window crosses the line again.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QHBoxLayout, QScrollArea, QVBoxLayout, QWidget)

from ..core.util import stardate
from . import theme
from . import soundmap
from .widgets import button, hrule, label, mono_label

#: How many entries the column shows. The game keeps three hundred.
SHOWN = 60

#: The open log's width, and the strip it folds to.
WIDE, FOLDED = 300, 34

#: Below this window width the log folds. The screens' own content wants
#: about 900 px (the Shipyard, the widest, measured 938); the rail is 158 and
#: the open log 300, so the line is where 900 still fits beside both.
FOLD_BELOW = 1300

#: **Good and bad are not only a colour.** Under deuteranopia the log's green
#: and red measured ΔE 12 apart — near enough the same grey — so a completed
#: contract and a lost colony read alike. A glyph carries the difference in
#: shape as well.
GLYPH = {"good": "✓", "bad": "✕", "warn": "!"}


def marked(text: str, kind: str) -> str:
    """A log line with its good/bad/warning glyph in front, when it has one."""
    mark = GLYPH.get(kind)
    return f"{mark} {text}" if mark else text


def build(win) -> QWidget:
    """The panel. Keeps its parts on the window, where the checks read them."""
    panel = QWidget()
    panel.setFixedWidth(WIDE)
    v = QVBoxLayout(panel)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)

    top = QWidget()
    h = QHBoxLayout(top)
    h.setContentsMargins(12, 8, 6, 6)
    h.setSpacing(4)
    win.log_caption = mono_label("Ship's Log")
    h.addWidget(win.log_caption, 1)
    win.log_toggle = button("›", lambda: toggle(win), kind="flat",
                            tip="Fold the log away (it opens again from here)")
    win.log_toggle.setObjectName("log_toggle")
    win.log_toggle.setAccessibleName("Fold or open the ship's log")
    win.log_toggle.setFixedWidth(26)
    h.addWidget(win.log_toggle)
    win.log_top = top
    v.addWidget(top)
    v.addWidget(hrule())

    win.log_area = QScrollArea()
    win.log_area.setWidgetResizable(True)
    win.log_area.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    win.log_inner = QWidget()
    win.log_col = QVBoxLayout(win.log_inner)
    win.log_col.setContentsMargins(12, 8, 12, 20)
    win.log_col.setSpacing(6)
    win.log_col.setAlignment(Qt.AlignmentFlag.AlignTop)
    win.log_area.setWidget(win.log_inner)
    v.addWidget(win.log_area, 1)
    v.addStretch(0)        # holds the button at the top once the log folds

    win.log_panel = panel
    win.log_newest = None          # the newest entry drawn, by identity
    win.log_folded = False
    win.log_wide_window = None     # which side of FOLD_BELOW we were last
    win.log_unseen = 0
    return panel


def _entry(day: int, text: str, kind: str) -> QWidget:
    entry = QWidget()
    v = QVBoxLayout(entry)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(1)
    v.addWidget(mono_label(stardate(day)))
    tinted = kind in theme.TINTS
    lb = label(marked(text, kind), "", kind if tinted else "", wrap=True)
    lb.setStyleSheet(
        f"color: {theme.tint(kind) if tinted else theme.INK2};"
        "font-size: 12.5px;")
    v.addWidget(lb)
    return entry


def _drop(win, index: int) -> None:
    item = win.log_col.takeAt(index)
    w = item.widget() if item is not None else None
    if w is not None:
        # An entry emits nothing, so nothing is mid-signal on it: it can go
        # at once, and `deleteLater` makes sure it does go.
        w.setParent(None)
        w.deleteLater()


def refresh(win) -> None:
    """Bring the column up to date with `game.log`, drawing only what is new."""
    log = win.game.log
    newest = log[-1] if log else None
    if newest is win.log_newest and (newest is not None
                                     or win.log_col.count() == 0):
        return                      # nothing logged since the last refresh
    fresh = _since(log, win.log_newest)
    soundmap.logged(win, fresh)         # one chime per kind in the burst
    if fresh is None or len(fresh) >= SHOWN:
        while win.log_col.count():
            _drop(win, 0)
        fresh = log[-SHOWN:]
    for day, text, kind in fresh:
        win.log_col.insertWidget(0, _entry(day, text, kind))
    while win.log_col.count() > SHOWN:
        _drop(win, win.log_col.count() - 1)
    win.log_newest = newest
    if win.log_folded:
        win.log_unseen += len(fresh)
        _show_fold(win)
    _sync(win)


def _since(log: list, last) -> list | None:
    """The entries after `last`, or None when `last` is not in this log —
    a different chronicle, or one that has moved on by more than it keeps."""
    if last is None:
        return None
    for i in range(len(log) - 1, max(-1, len(log) - 1 - 300), -1):
        if log[i] is last:
            return log[i + 1:]
    return None


def _sync(win) -> None:
    """**Tell the scroll area its contents changed size.** The same fault
    `View._sync_scroll` exists for: a column of wrapping labels changed inside
    a scroll area does not update the inner widget's minimum, so once the log
    held more than a screenful every entry was squeezed into a few pixels —
    found by playing to day 569."""
    win.log_col.invalidate()
    win.log_col.activate()
    win.log_inner.setMinimumHeight(win.log_col.minimumSize().height())
    QTimer.singleShot(0, lambda: _settle(win))


def _settle(win) -> None:
    """The true minimum is not known until the new labels are polished."""
    try:
        win.log_col.activate()
    except RuntimeError:
        return          # the window went down before the loop came back
    need = win.log_col.minimumSize().height()
    if need != win.log_inner.minimumHeight():
        win.log_inner.setMinimumHeight(need)


# ── folding ────────────────────────────────────────────────────────────────

def fit(win, width: int) -> None:
    """Fold or open the log when the window crosses `FOLD_BELOW`.

    Only on the crossing: a player who opened the log on a narrow window
    keeps it open until the window is resized past the line and back.
    """
    if getattr(win, "log_panel", None) is None:
        return              # a resize delivered before the log was built
    wide = width >= FOLD_BELOW
    if wide == win.log_wide_window:
        return
    win.log_wide_window = wide
    set_folded(win, not wide)


def toggle(win) -> None:
    set_folded(win, not win.log_folded)


def set_folded(win, folded: bool) -> None:
    win.log_folded = folded
    if not folded:
        win.log_unseen = 0
    win.log_area.setVisible(not folded)
    win.log_caption.setVisible(not folded)
    win.log_top.layout().setContentsMargins(
        *((3, 8, 3, 6) if folded else (12, 8, 6, 6)))
    win.log_panel.setFixedWidth(FOLDED if folded else WIDE)
    _show_fold(win)


def _show_fold(win) -> None:
    if win.log_folded:
        count = f"{win.log_unseen}" if win.log_unseen else ""
        win.log_toggle.setText(f"‹{count}")
        win.log_toggle.setFixedWidth(26 if not count else 30)
        win.log_toggle.setToolTip(
            "Open the ship's log" + (f" — {win.log_unseen} new "
                                     "since it was folded" if count else ""))
    else:
        win.log_toggle.setText("›")
        win.log_toggle.setFixedWidth(26)
        win.log_toggle.setToolTip(
            "Fold the log away (it opens again from here)")
