"""The bridge's two columns, and the boards that go in the right-hand one.

Split out of `ui/pilot_view.py` when the screen was measured rather than
glanced at. Shown at 1360x880 the Pilot screen was **1,444 pixels tall in a
782-pixel window — 662 px, 46% of the bridge, below the fold.** Everything
after the ship's readout was out of sight: what is in view, the fly-at
buttons, the fire control, the guns, the marks, the autopilot and the clock.
A pilot had to scroll past the instrument panel to reach the trigger.

The cause was that a `View` gives one column and the screen used it for
everything, stacking a 260-pixel window onto a nine-row table onto four rows of
buttons. The window is 1360 wide and the content column 900, so the room was
sideways and nobody was using it.

So the bridge is two columns now: **the view and the hands that fly her** on
the left, **the boards that tell you what is out there** on the right. Nothing
about what is shown changed — this is where it is shown, and the panels moved
here so `ui/pilot_view` keeps to the flying.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (QGridLayout, QHBoxLayout, QVBoxLayout,
                             QWidget)

from ..sim import engage as engage_sim
from ..sim import freeflight as free_sim
from ..sim import instruments as panel_sim
from .widgets import Panel, note

#: How the width is split. The view wants room to be a view; the boards are
#: text and read better narrow than wide.
LEFT_SHARE, RIGHT_SHARE = 3, 2


def two_columns() -> tuple:
    """`(holder, left, right)` — a row of two vertical columns."""
    holder = QWidget()
    across = QHBoxLayout(holder)
    across.setContentsMargins(0, 0, 0, 0)
    across.setSpacing(16)
    made = []
    for share in (LEFT_SHARE, RIGHT_SHARE):
        side = QWidget()
        down = QVBoxLayout(side)
        down.setContentsMargins(0, 0, 0, 0)
        down.setSpacing(8)
        across.addWidget(side, share)
        made.append(down)
    return holder, made[0], made[1]


def row_of(*btns) -> QWidget:
    """A line of buttons that can go into either column.

    `View.buttons` puts its row into `self.col` and returns it, which is no
    use once there are two columns to put things in.
    """
    holder = QWidget()
    across = QHBoxLayout(holder)
    across.setContentsMargins(0, 2, 0, 2)
    across.setSpacing(7)
    for b in btns:
        if b is not None:
            across.addWidget(b)
    across.addStretch(1)
    return holder


def stack_of(btns, per_row: int = 2) -> QWidget:
    """Buttons in a grid that wraps, for the narrow column.

    **A single row of them does not fit and does not wrap.** Measured on a
    shown window: four "Fly at <name>" buttons side by side demanded 660 px,
    which set the right column's minimum and pushed the bridge's content to
    1,206 px inside an 891 px viewport — so every reading in that column was
    clipped. Two to a line fits, and the labels stay whole.
    """
    holder = QWidget()
    grid = QGridLayout(holder)
    grid.setContentsMargins(0, 2, 0, 2)
    grid.setHorizontalSpacing(7)
    grid.setVerticalSpacing(4)
    for index, b in enumerate([x for x in btns if x is not None]):
        grid.addWidget(b, index // per_row, index % per_row)
    return holder


def ship_board(view) -> Panel:
    """What the instruments say, plus what the last press and the computer did."""
    board = Panel("The ship")
    for key, value, kind in panel_sim.readout(view.conn):
        board.add_row(key, value, kind)
    board.add_row("Clock", "running" if view.running else "held")
    # **What the last press did**, because three of the six thrust buttons can
    # look dead: the torch only pushes along the nose, so a press whose axis is
    # not under it spends the whole tick swinging the hull and burns nothing.
    if view.last.get("turning"):
        board.add_row("Drive", "swinging the hull round to bear — the torch "
                               "did not fire", "warn")
    elif view.last.get("burned"):
        board.add_row("Drive", "fired", "")
    board.add_row("Autopilot", {
        "": "off — she flies as you fly her",
        "hold": "holding station, killing what drift there is",
        "run": f"running for {view.mark or 'nothing'}",
    }[view.auto])
    aim = view.marked()
    if aim is None:
        board.add_row("Course", "none laid — the six axes fly her frame")
    else:
        board.add_row(
            "Course",
            f"{aim.name}, "
            f"{engage_sim.range_km(view.game, view.conn, aim):,.0f} km, nose "
            f"{free_sim.off_course(view.game, view.conn, aim):.0f}° off")
    return board


def in_view_board(view, rows) -> Panel:
    """Everything the cameras can see, nearest first, with what it means."""
    near = Panel("In view")
    if not rows:
        near.add(note("Nothing within reach of the cameras."))
        return near
    for km, contact in rows[:6]:
        ok, _why = engage_sim.may_engage(view.game, view.conn, contact, km)
        near.add_row(contact.name,
                     f"{km:,.0f} km"
                     + ("  · may be engaged" if ok else "")
                     + ("  · on course" if contact.name == view.mark else ""))
    return near
