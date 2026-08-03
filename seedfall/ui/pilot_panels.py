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

from ..sim import conn as conn_sim
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


# ── the labels that change while the clock runs ────────────────────────────
#
# **One door each, because a beat no longer rebuilds these buttons.** They are
# built once and their text is updated in place, so `build` and the beat both
# have to say the same thing — and #137 already caught the version of this bug
# where two places formatted the throttle and the button read 50% above a panel
# reading 100%. Formatting lives here; both callers ask.


def main_label(view) -> str:
    return f"Main drive: {'on' if view.use_main else 'off'}"


def throttle_label(view) -> str:
    return f"Throttle: {view.conn.throttle:.0%}"


def clock_label(view) -> str:
    return "Stop clock" if view.running else "Run clock"


def aim_feed(view, rows) -> None:
    """Point the viewport, and name what is out there.

    Ringing the mark and labelling the traffic are two facts the screen hands
    the viewport; the beat has to refresh them without rebuilding the feed, so
    they live in one place that `build` and the beat both call.
    """
    laid = view.marked()
    view.feed.mark = ((free_sim.toward(view.game, view.conn, laid), laid.name)
                      if laid is not None else None)
    # **Name the quays and the hulls out there.** The Conn draws its target
    # inside a reticle reading "Fleet Hub · 12.0 km"; a free flight has no
    # target, so the same Hub was a 1.6-pixel speck among the stars. The sky
    # data was never missing — measured, a free flight's `sky` holds *more*
    # than an approach's — only the drawing was.
    view.feed.sights = [
        (free_sim.toward(view.game, view.conn, c), c.name,
         km <= engage_sim.reach_km())
        for km, c in rows[:8]
        if c.kind in ("anchorage", "hull")]


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
    board.add_row("Autopilot", _computer_says(view))
    aim = view.marked()
    if aim is None:
        board.add_row("Course", "none laid — the six axes fly her frame")
        return board
    km = engage_sim.range_km(view.game, view.conn, aim)
    board.add_row("Course", f"{aim.name}, {km:,.0f} km, nose "
                            f"{free_sim.off_course(view.game, view.conn, aim):.0f}° off")
    # **Closing on the mark, not on the place she left.** `conn.closing` is
    # measured against the conn's origin, which out here is where she was let
    # go — so a ship braking onto a contact reads as opening, which is true
    # and useless.
    rate = free_sim.closing_on(view.game, view.conn, aim)
    if rate > 0.1:
        minutes = km * 1000.0 / rate / 60.0
        board.add_row("Closing", f"{rate:,.0f} m/s — about "
                                 + (f"{minutes / 60:,.1f} h" if minutes > 90
                                    else f"{minutes:,.0f} min") + " to go")
    elif rate < -0.1:
        board.add_row("Closing", f"opening at {-rate:,.0f} m/s", "warn")
    else:
        board.add_row("Closing", "holding the range")
    return board


def _computer_says(view) -> str:
    """What the flight computer is doing, in the words a pilot would use.

    **It used to say six words the whole way in.** Measured on one run to a
    contact 5,137 km off: the computer went `forward` on the torch, then
    `back` on the thrusters to brake, then `None` to coast the last stretch —
    and the screen read "running for Held Breath" at every one of those, so a
    pilot could not tell accelerating from braking from arriving.
    """
    if view.auto == "":
        return "off — she flies as you fly her"
    if view.auto == "hold":
        return "holding station, killing what drift there is"
    aim = view.marked()
    if aim is None:
        return "running for nothing"
    # **The name is on the Course row already.** Repeating it here cost 29 px
    # of width the bridge did not have, and the layout check said so.
    axis, main, throttle = free_sim.run_for(view.game, view.conn, aim)
    if axis is None:
        return "running her in — coasting"
    which = conn_sim.AXES_BY_ID[axis][1].lower()
    return (f"running her in — {which} on "
            f"{'the torch' if main else 'thrusters'} at {throttle:.0%}")


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
