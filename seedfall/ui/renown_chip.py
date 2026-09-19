"""The renown chip: the moment a milestone is reached.

It sits in the menu bar's corner beside the mute chip, not on the heading
bar: on the bar, at 1,040 px, it squeezed the meters until their captions
ran under the bars (screenshot, 2026-09-18). Shown only while there are
milestones the captain has not yet looked at; pressing it opens the Voyage,
which is what clears it (`sim/renown.seen`). A button, not a pill: a count
you cannot press is a taunt (the despatch button's rule).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..sim import renown
from . import theme
from .widgets import button


def corner(win, other):
    """The menu bar's corner: this chip, then whatever sat there before."""
    host = QWidget()
    h = QHBoxLayout(host)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    h.addWidget(build(win))
    h.addWidget(other)
    return host


def build(win):
    chip = button("★", lambda: open_voyage(win), kind="flat",
                  tip="Milestones reached — the Voyage")
    chip.setAccessibleName("Renown")
    chip.setObjectName("renown_chip")
    chip.setFixedHeight(20)            # the menu bar's own height, as the
    chip.hide()                        # mute chip beside it is held
    win.renown_chip = chip
    return chip


def sync(win) -> None:
    chip = getattr(win, "renown_chip", None)
    if chip is None:
        return
    st = renown.state(win.game)
    fresh = [renown.BY_ID[m] for m in (st.fresh if st else [])
             if m in renown.BY_ID and renown.BY_ID[m].renown]
    if not fresh:
        if chip.isVisibleTo(chip.parentWidget()):
            chip.hide()
            _relayout(win)
        return
    chip.setText(f"★ +{sum(m.renown for m in fresh)}")
    chip.setToolTip(f"{renown.rank(win.game)['name']} — "
                    + "; ".join(m.name for m in fresh[-4:]))
    chip.setStyleSheet(
        f"QPushButton {{ padding: 0 8px; color: {theme.tint('chloro')};"
        f" font-family: '{theme.mono_family()}'; border-color: {theme.LINE2}; }}")
    chip.show()
    _relayout(win)


def _relayout(win) -> None:
    """Give the corner the room its chip now wants.

    A menu bar sizes its corner widget only when that widget itself shows or
    hides, or the bar is resized — not when something inside it grows. So the
    chip, shown later, was squeezed into the 42 px the speaker had left: an
    empty box, with the speaker pushed half off the edge (2026-09-18)."""
    from PyQt6.QtGui import QResizeEvent
    from PyQt6.QtWidgets import QApplication
    bar = win.menuBar()
    host = bar.cornerWidget()
    if host is not None and host.layout() is not None:
        host.layout().activate()
    QApplication.sendEvent(bar, QResizeEvent(bar.size(), bar.size()))


def open_voyage(win) -> None:
    view = win.views.get("empire")
    if view is not None:
        view.tab = "voyage"
    win.go("empire")
