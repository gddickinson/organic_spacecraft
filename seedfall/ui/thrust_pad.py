"""The thrust pad: six thrusters, the drive switch and the coast — one widget.

There were three pads for one hand. The bridge laid the six axes in a single
row with the drive and the coast on a line below; the conn console put them two
by three with the drive beside them and said nothing on the buttons; the flight
controls used the same grid and printed the promise on each one. A pilot going
from window to window had to find *Astern* again every time, and only one of
the three said what a press would do before it was pressed.

So there is one. The six axes two by three, the way a hand sits on them —
across and up-and-down round the line of flight — with the drive switch and
the coast in a fourth column, and on every button the same three things: the
arrow toward the berth when there is one (`moorings.steer`), the name, and
what a press is worth (`pilot.quote`, the door the burn itself spends through).
Held, not clicked: every thruster wires through `flight_clock.hold_wire`.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QWidget

from ..core.util import reaction_mass
from ..sim import conn as conn_sim
from ..sim import instruments
from ..sim import moorings
from ..sim import pilot as pilot_sim
from .widgets import button, light

#: `(axis, row, column)`: the hand's layout, not the alphabet's.
LAYOUT = (("left", 0, 0), ("forward", 0, 1), ("right", 0, 2),
          ("down", 1, 0), ("back", 1, 1), ("up", 1, 2))


def drive_label(conn) -> str:
    """The drive switch's words — armed, off, or firing and how hard."""
    return f"Main drive: {instruments.drive_note(conn)}"


def arrow(toward: float) -> str:
    """Whether a push along this axis takes her toward the berth."""
    return "▲" if toward > 0.25 else ("▼" if toward < -0.25 else "·")


class ThrustPad(QWidget):
    """The six axes, the drive and the coast. `sync` relabels them in place.

    `win` is the main window, whose `burn_order` the held buttons set;
    `on_drive` toggles the drive and `on_coast` lets the clock run a press
    with nothing lit — each screen keeps its own door for those two.
    """

    def __init__(self, win, on_drive, on_coast):
        super().__init__()
        from . import flight_clock
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 2, 0, 2)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        self.buttons = {}
        for axis_id, row, col in LAYOUT:
            btn = button(conn_sim.AXES_BY_ID[axis_id][1], None)
            btn.setObjectName(f"thr_{axis_id}")
            flight_clock.hold_wire(win, btn, axis_id)
            grid.addWidget(btn, row, col)
            self.buttons[axis_id] = btn
        self.drive = button("Main drive: off", on_drive, kind="flat")
        self.drive.setObjectName("thr_drive")
        grid.addWidget(self.drive, 0, 3)
        self.coast = button("Hold (coast)", on_coast)
        self.coast.setObjectName("thr_coast")
        grid.addWidget(self.coast, 1, 3)
        for col in range(4):
            grid.setColumnStretch(col, 1)
        # **Two lines in the height of one and a bit.** The promise under
        # each name doubled the pad's height at the theme's padding, and on
        # the bridge that pushed the last two fire-control buttons under the
        # fold at 1360x880 — measured, 73 px against 59. Tighter vertical
        # padding brings the pad back to the two rows it replaced; the floor
        # keeps the one-line drive and coast buttons as tall as the rest, and
        # tall enough for the theme's rounded ends (a box shorter than twice
        # its radius is drawn square).
        self.setStyleSheet(
            "QPushButton { padding: 2px 10px; min-height: 24px; }")

    def sync(self, conn, main: bool) -> None:
        """Every label, lock and light from the live flight. Touches no
        control's identity, so a beat can call it under a held finger."""
        self.drive.setText(drive_label(conn))
        if conn is None:
            for btn in self.buttons.values():
                btn.setEnabled(False)
                light(btn, False)
            light(self.drive, False)
            return
        live = not conn.over
        ok, why = conn_sim.can_burn(conn, main)
        helps = moorings.steer(conn)
        # The coast on the button: a press is one minute of thrust and up to
        # fifteen of clock, and a bare figure implied the burn lasted the lot.
        coast = f" · {conn.coast_min} min" if conn.coast_min > 1 else ""
        for axis_id, btn in self.buttons.items():
            name = conn_sim.AXES_BY_ID[axis_id][1]
            said = pilot_sim.quote(conn, axis_id, main=main)
            mark = f"{arrow(helps.get(axis_id, 0.0))} " if helps else ""
            btn.setText(f"{mark}{name}\n{said['dv']:.2f} m/s{coast}")
            btn.setEnabled(live and ok)
            btn.setToolTip(
                why if not live else
                f"{name} at {said['dv']:,.2f} m/s, {said['minutes']} min: "
                f"range {said['range_km'] * 1000:,.0f} m, closing "
                f"{said['closing']:+,.1f} m/s, "
                f"{reaction_mass(said['rcs'])} left"
                + ("" if ok else f" — {why}"))
            # **Lit when it is the one firing**, off `conn.fired_axis` — what
            # the ship *did*, not what the computer would ask for next.
            light(btn, conn.fired_axis == axis_id)
        light(self.drive, bool(conn.fired_axis) and conn.fired_main)
