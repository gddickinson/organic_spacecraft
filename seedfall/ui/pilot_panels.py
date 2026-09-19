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

from ..core.util import reaction_mass
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import freeflight as free_sim
from ..sim import instruments as panel_sim
from . import sights
from . import sky_strip
from .widgets import Panel, note

#: How the width is split. The view wants room to be a view; the boards are
#: text and read better narrow than wide.
LEFT_SHARE, RIGHT_SHARE = 3, 2


def two_columns() -> tuple:
    """`(holder, left, right)` — a row of two vertical columns.

    A `WrapRow`: side by side whenever both columns fit, and the boards under
    the view when they do not — rather than the right-hand column running off
    the edge of a narrow window, which is what a fixed row did at 1040 px.
    """
    from .view_base import WrapRow
    holder = WrapRow(16)
    made = []
    for share in (LEFT_SHARE, RIGHT_SHARE):
        side = QWidget()
        down = QVBoxLayout(side)
        down.setContentsMargins(0, 0, 0, 0)
        down.setSpacing(8)
        holder.add(side, share)
        made.append(down)
    return holder, made[0], made[1]


def camera_row(view) -> QWidget:
    """The six "Look …" buttons, three to a line.

    Three to a line because six across demanded 486 px and set the left
    column's minimum — 56 px more than the bridge had to give. **"Look
    port", not "Port"** (#153): the camera row and the thruster row both
    said Port and Starboard, a few pixels apart, so a probe finding a
    control by its text clicked the camera and reported two dead thrusters
    — and a pilot could do the same with a finger. Every control wears an
    objectName, so a check can address exactly one.
    """
    from .widgets import button
    looks = []
    for view_id, view_label, _vec in conn_sim.VIEWS:
        btn = button(f"Look {view_label.lower()}",
                     lambda _=False, v=view_id: view._look(v), kind="flat")
        btn.setObjectName(f"cam_{view_id}")
        looks.append(btn)
    return stack_of(looks, per_row=3)


def axis_pad(view):
    """The one thrust pad (`ui/thrust_pad.py`), wired to this screen's doors.

    **Held, not clicked.** A click was one instantaneous impulse — the
    engines worked in steps, with the speed jumping between frames. Pressed
    and released wire through `flight_clock.hold_wire`: hold a thruster
    with the clock running and the burn *builds*, minute after minute,
    until the hand comes off; a quick press is still one precise tick.

    It was a single row of six here, two by three on the conn and on the
    flight controls: three layouts for one hand. It is the same widget on all
    three now, with the drive and the coast in its fourth column.
    """
    from .thrust_pad import ThrustPad
    return ThrustPad(view.win, view._toggle_main, lambda: view.burn(None))


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
    from .thrust_pad import drive_label
    return drive_label(view.conn)


def throttle_label(view) -> str:
    return f"Throttle: {view.conn.throttle:.0%}"


def clock_label(view) -> str:
    return "Stop clock" if view.running else "Run clock"


def scale_label(view) -> str:
    return f"Time ×{int(getattr(view.win, 'time_scale', 1))}"


def aim_feed(view, rows) -> None:
    """Point the viewport, and name what is out there.

    Ringing the mark and labelling the traffic are two facts the screen hands
    the viewport; the beat has to refresh them without rebuilding the feed, so
    they live in one place that `build` and the beat both call.
    """
    laid = view.marked()
    tag = None
    if laid is not None:
        name = laid.name
        # **The band on the mark** — the combat fact a pilot closing on a
        # hull actually needs: whether the guns can speak, and at which band
        # this range opens. Off `engage`, the same doors the trigger uses.
        km = next((k for k, c in rows if c.name == laid.name), None)
        if km is not None and engage_sim.may_engage(
                view.game, view.conn, laid, km)[0]:
            from ..sim import combat as combat_sim
            band = engage_sim.band_for(view.game, view.conn, laid)
            name += f" · {combat_sim.BANDS[band]} band"
        tag = (free_sim.toward(view.game, view.conn, laid), name)
    view.feed.mark = tag
    # **Name the quays and the hulls out there**, through `ui/sights`, which
    # the Conn window asks the same question of. The mark is passed as already
    # named: it is drawn as a ring with its name on it, and a sight label
    # beside that is the same word twice.
    view.feed.sights = sights.out_there(view.game, view.conn, rows,
                                        skip=(laid,))


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
    # No "Autopilot" row: the readout above already carries "Computer", off
    # `instruments.computer_note`, and this board printed the same fact
    # twice, one row apart, in two sets of words ("closing to berth" and
    # "closing to berth"; "holding —" and "holding station,").
    sky_strip.shelter_row(board, view.game)       # a flare: out of it?
    aim = view.marked()
    if aim is None:
        board.add_row("Course", "none laid — the six axes fly her frame")
        return board
    km = engage_sim.range_km(view.game, view.conn, aim)
    board.add_row("Course", f"{aim.name}, {km:,.0f} km, nose "
                            f"{free_sim.off_course(view.game, view.conn, aim):.0f}° off")
    # **What the run would cost, before it is flown.** Found by playing:
    # "Run for" a contact 4,834 km off — well inside reach — quietly burned
    # 19.8 of 20 t, and the first the pilot heard of it was arriving *dry*.
    # A run is a fuel decision, the same rule as the climb rungs, and it is
    # on the board every beat because the price falls as the range does.
    bill = free_sim.run_quote(view.game, view.conn, aim)
    if bill["dv"] > 0:
        board.add_row("Run bill",
                      f"~{reaction_mass(bill['mass'])} of "
                      f"{reaction_mass(bill['tank'])} aboard",
                      "" if bill["afford"] else "warn")
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


def _hail(view, contact) -> None:
    """Open the channel. With no contact, the window picks one to start on."""
    from .comms_window import open_comms
    if contact is None:
        rows = view.ranged()
        contact = rows[0][1] if rows else None
    if contact is None:
        view.win.toast("Nothing within reach of the array.", "warn")
        return
    open_comms(view.win, contact)
