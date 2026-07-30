"""The flight controls, in a window a pilot can actually berth from.

The conn has a console, and it is a console: a compact row of buttons under a
3D view, built to be *watched*. This is the other thing — a panel to be
*flown*, with the instruments a docking pilot reads and nothing else on the
screen competing for the space.

What a berthing actually needs, and what the conn never spelled out:

- **Closing rate and lateral rate as separate numbers.** Together they are the
  whole velocity, and a pilot has to null both. Closing gets you there;
  lateral is the one that slides you past the mast at a metre a second while
  every other reading says you are on profile. `sim/autopilot.lateral` has
  taken that reading since the computer was written and no screen showed it.
- **Which berth, and how far off it.** `sim/moorings.py` knows; the pilot is
  flying to a mast, not to a bounding sphere.
- **The gate, in the units the readouts are in** — a berthing is under so
  many metres and under so many metres a second, and those two numbers were
  in `sim/conn.py` where nobody flying could see them.
- **What each press will do before it is pressed**, off `sim/pilot.quote` —
  the same door the console uses, so the promise and the act are one thing.

The window owns no rules. Every button is `conn.apply` and every figure is a
sim reading, so this and the conn cannot disagree about the ship: they are
laid out differently on purpose and answer to the same model.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QVBoxLayout,
                             QWidget)

from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import moorings
from ..sim import thrusters
from ..sim import pilot as quote_sim
from . import theme
from .widgets import button, label, light, mono_label, note

def win_game(win):
    """The chronicle a window is on. One line, so the diagram is not handed a
    window and left to reach through it for the ship."""
    return win.game


#: How often the clock ticks while it is running, in ms. The conn's own beat,
#: so a berthing takes the same time flown from either window.
TICK_MS = 700

#: The pad, laid out the way a pilot's hand sits on it rather than
#: alphabetically — translation left/right and up/down around the two along
#: the line of flight.
PAD = (("left", 0, 0), ("forward", 0, 1), ("right", 0, 2),
       ("down", 1, 0), ("back", 1, 1), ("up", 1, 2))


class FlightWindow(QDialog):
    """Hands on: fly the approach yourself, on the instruments."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Flight controls — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(560, 620)
        self.use_main = False
        self.running = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._build()
        self.refresh()

    @property
    def conn(self):
        """The approach being flown — the conn window's, if one is open.

        Deliberately *the same object*: two windows on one approach, not two
        approaches. A pilot who takes the controls here and looks up at the
        conn is looking at the ship they are flying.
        """
        window = getattr(self.win, "conn_window", None)
        if window is not None and getattr(window, "conn", None) is not None:
            return window.conn
        return getattr(self.win, "_flight_conn", None)

    # ── building ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(8)

        head = QHBoxLayout()
        self.title = label("Flight controls", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        self.gate = note("")
        column.addWidget(self.gate)

        from .shipdiagram import ShipDiagram
        self.ship = ShipDiagram(win_game(self.win))
        column.addWidget(self.ship)

        self.dials = QWidget()
        self.dial_box = QVBoxLayout(self.dials)
        self.dial_box.setContentsMargins(0, 0, 0, 0)
        self.dial_box.setSpacing(2)
        column.addWidget(self.dials)

        column.addWidget(label("Thrusters", "h3"))
        pad = QGridLayout()
        pad.setHorizontalSpacing(6)
        pad.setVerticalSpacing(4)
        self.axis_buttons = {}
        for axis_id, row, col in PAD:
            _aid, name, _vec = conn_sim.AXES_BY_ID[axis_id]
            btn = button(name, lambda a=axis_id: self._burn(a))
            pad.addWidget(btn, row, col)
            self.axis_buttons[axis_id] = btn
        self.main_btn = button("Main drive: off", self._toggle_main,
                               kind="flat")
        pad.addWidget(self.main_btn, 0, 3)
        pad.addWidget(button("Hold (coast)", lambda: self._burn(None)), 1, 3)
        column.addLayout(pad)

        column.addWidget(label("Throttle", "h3"))
        row = QHBoxLayout()
        self.throttle_buttons = {}
        for share in (0.1, 0.25, 0.5, 1.0):
            btn = button(f"{share:.0%}", lambda s=share: self._throttle(s),
                         kind="flat")
            row.addWidget(btn)
            self.throttle_buttons[share] = btn
        column.addLayout(row)

        column.addWidget(label("Autopilot", "h3"))
        row = QHBoxLayout()
        self.auto_buttons = {}
        for mode, text in (("close", "Close and berth"), ("null", "Hold still"),
                           ("orbit", "Make orbit")):
            btn = button(text, lambda m=mode: self._auto(m), kind="flat")
            row.addWidget(btn)
            self.auto_buttons[mode] = btn
        self.off_btn = button("Autopilot off", lambda: self._auto(None))
        row.addWidget(self.off_btn)
        column.addLayout(row)

        row = QHBoxLayout()
        self.run_btn = button("Run clock", self._toggle_clock, kind="primary")
        row.addWidget(self.run_btn)
        row.addWidget(button("Kill relative motion", self._null, kind="flat"))
        row.addWidget(button("Conn…", self._conn, kind="flat"))
        row.addWidget(button("Approach view…", self._approach, kind="flat"))
        column.addLayout(row)
        column.addStretch(1)

    # ── flying ─────────────────────────────────────────────────────────────

    def _burn(self, axis_id) -> None:
        conn = self.conn
        if conn is None or conn.over:
            return
        conn_sim.apply(conn, axis_id, main=self.use_main,
                       ticks=conn.coast_min, throttle=conn.throttle)
        self._settle()

    def _null(self) -> None:
        """One tick of the computer's own null, by hand.

        Through `autopilot` rather than a rule of this window's: killing the
        relative motion is a thing the flight computer knows how to do, and a
        pilot pressing this is asking it for one tick of that and no more.
        """
        conn = self.conn
        if conn is None or conn.over:
            return
        axis, main, throttle = pilot_sim.autopilot(conn, "null")
        conn_sim.apply(conn, axis, main=main, throttle=throttle)
        self._settle()

    def _auto(self, mode) -> None:
        """Hand the ship to the computer, or take it back.

        The conn holds the mode, because there is one approach and one
        computer flying it — a pilot who arms the autopilot here and looks at
        the conn must see it armed there. Pressing the mode that is already
        running turns it off, and so does *Autopilot off*, so there is no way
        to be uncertain whether it is on.
        """
        window = getattr(self.win, "conn_window", None)
        if window is not None:
            if mode is not None and window.mode == mode:
                mode = None
            window.mode = mode
            if mode is not None and not window.running:
                window._toggle_clock()
        self.win.refresh()
        self.refresh()

    @property
    def mode(self):
        """Which autopilot mode is running, if any — the conn's."""
        window = getattr(self.win, "conn_window", None)
        return getattr(window, "mode", None)

    def _toggle_main(self) -> None:
        self.use_main = not self.use_main
        self.refresh()

    def _throttle(self, share: float) -> None:
        conn = self.conn
        if conn is not None:
            conn.throttle = share
        self.refresh()

    def _toggle_clock(self) -> None:
        self.running = not self.running
        if self.running:
            self.timer.start(TICK_MS)
        else:
            self.timer.stop()
        self.refresh()

    def _tick(self) -> None:
        """One beat of the clock — flown by the computer if it has the ship.

        The panel used to coast on every tick regardless, so arming the
        autopilot and running the clock *here* did nothing while the same act
        on the conn flew the approach. One computer, one ship, either window.
        """
        conn = self.conn
        if conn is None or conn.over:
            self.running = False
            self.timer.stop()
        elif self.mode:
            axis, main, throttle = pilot_sim.autopilot(conn, self.mode)
            conn_sim.apply(conn, axis, main=main, throttle=throttle)
        else:
            conn_sim.apply(conn, None)
        self._settle()

    def _settle(self) -> None:
        """Land whatever the approach has come to on the chronicle."""
        conn = self.conn
        if conn is not None and conn.over:
            from ..sim import berthing as berth_sim
            berth_sim.commit(self.win.game, conn)
            self.running = False
            self.timer.stop()
        self.win.refresh()
        self.refresh()

    def _conn(self) -> None:
        from .conn_window import open_conn
        open_conn(self.win)

    def _approach(self) -> None:
        """Ship and target together, from outside."""
        from .approach_window import open_approach
        open_approach(self.win)

    # ── reading ────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        conn = self.conn
        self.ship.conn = conn
        self.ship.update()
        while self.dial_box.count():
            old = self.dial_box.takeAt(0).widget()
            if old is not None:
                # **Detached, not merely scheduled.** `deleteLater` defers to
                # the event loop, so a widget taken out of the layout is still
                # a child of the window until then — and a check reading the
                # window's labels sees six copies of a line the panel shows
                # once. Parenting to None takes it out now.
                old.setParent(None)
                old.deleteLater()
        # The label is the *pilot's* selection; the light is what the ship
        # fired. Those can differ — the computer opens the drive while the
        # pad is set to clusters — and a button reading "off" with a light on
        # it is a screen arguing with itself, so the firing case says so.
        firing = conn is not None and conn.fired_main and conn.fired_axis
        self.main_btn.setText(
            f"Main drive: FIRING {conn.fired_share:.0%}" if firing else
            f"Main drive: {'armed' if self.use_main else 'off'}")
        self.run_btn.setText("Stop clock" if self.running else "Run clock")
        if conn is None:
            self.title.setText("Flight controls — nothing in reach")
            self.gate.setText("Take the conn on something first.")
            for btn in self.axis_buttons.values():
                btn.setEnabled(False)
            return
        for btn in self.axis_buttons.values():
            btn.setEnabled(not conn.over)

        self.title.setText(f"Flight controls — {conn.target.name}")
        self.gate.setText(
            f"Berths at {conn_sim.ALONGSIDE_KM * 1000:,.0f} m or less and "
            f"{conn_sim.ALONGSIDE_RATE:.1f} m/s or less, at a berth.")

        across = math.dist(pilot_sim.lateral(conn), (0.0, 0.0, 0.0))
        # **The rate you are allowed**, beside the rate you have. Without it
        # the panel is unflyable in the way that matters: measured by hand,
        # three chronicles all hit the structure at 9.2 m/s with nineteen of
        # twenty tonnes of thruster mass unspent, because nothing on the
        # screen said when to start braking. `autopilot.safe_rate` has known
        # since the computer was written — it is what the computer holds to —
        # and no screen had ever shown it.
        limit = pilot_sim.safe_rate(conn)
        rows = [
            ("Range", f"{conn.range_km * 1000:,.0f} m"
                      if conn.range_km < 2 else f"{conn.range_km:,.2f} km"),
            ("Closing", f"{conn.closing:+.2f} of {limit:.2f} m/s"),
            ("Lateral", f"{across:.2f} m/s"),
            ("Speed", f"{conn.speed:.2f} m/s"),
            ("Thruster mass", f"{conn.rcs:.2f} t"),
            ("Elapsed", f"{conn.elapsed / 60:.0f} min"),
        ]
        berth = moorings.nearest(conn)
        if berth is not None:
            rows.append(("Berth", f"{berth['name']} · "
                                  f"{berth['km'] * 1000:,.0f} m"))
            # **Relative to the berth, because the berth is moving.** The two
            # readings above are measured against the structure's *centre*,
            # which is the right frame for something that sits still and the
            # wrong one for a fitting going round: a hull perfectly matched to
            # a turning berth still reads lateral drift against the centre,
            # and a pilot nulling that fights the rotation instead of joining
            # it. Measured: a hand-flown approach did exactly that and
            # arrived 482 m from the fitting with its tanks spent.
            on_berth = moorings.rates(conn)
            if on_berth["berth_speed"] > 0.01:
                rows.append(("On the berth",
                             f"{on_berth['closing']:+.2f} closing · "
                             f"{on_berth['cross']:.2f} across"))
                rows.append(("Berth travels",
                             f"{on_berth['berth_speed']:.2f} m/s"))
        for name, value in rows:
            self.dial_box.addWidget(mono_label(f"{name:<15}{value}"))
        if berth is not None:
            self.dial_box.addWidget(note(moorings.line(conn)))
        if conn.over:
            self.dial_box.addWidget(label(
                f"Approach over: {conn.outcome}.", "", tint="warn"))

        # What each press would do, on the button itself — off `pilot.quote`,
        # which is the same door the conn's console reads.
        # …and **whether it takes the ship toward the berth**, off
        # `moorings.steer`, which reads the same `conn.thrust_axis` the burn
        # does and points at the same `moorings.aim` the computer flies to.
        #
        # Without this the panel is not flyable: the pad is in the ship's
        # frame and the berth is somewhere off the bow, so a pilot pressing
        # *ahead* flies at the middle of the structure. Measured by hand,
        # into the skin 477 m from the mast.
        helps = moorings.steer(conn)
        for axis_id, btn in self.axis_buttons.items():
            _aid, name, _vec = conn_sim.AXES_BY_ID[axis_id]
            said = quote_sim.quote(conn, axis_id, main=self.use_main)
            toward = helps.get(axis_id, 0.0)
            arrow = "▲" if toward > 0.25 else ("▼" if toward < -0.25 else "·")
            btn.setText(f"{arrow} {name}\n{said['dv']:.2f} m/s")
            # **Lit when it is the one firing**, so a pilot watching the
            # computer work can see which thruster it is using. Off
            # `conn.fired_axis`, which is what the ship *did* rather than what
            # the computer would ask for if asked again.
            light(btn, conn.fired_axis == axis_id)
        light(self.main_btn, bool(conn.fired_axis) and conn.fired_main)
        for mode, btn in self.auto_buttons.items():
            light(btn, self.mode == mode)
        light(self.off_btn, not self.mode, "warn")
        # Which engine is doing the work, in words, under the diagram.
        alight = [row[2] for row in thrusters.firing(
            self.win.game.ship, conn.fired_axis, conn.fired_main) if row[4]]
        if alight:
            # **How far it is open**, not merely that it is. The computer runs
            # a drive at 62% and then at 25% within four ticks, and a pilot
            # watching a light with no number on it cannot tell those apart.
            # Clusters are pulsed rather than throttled, so the share is only
            # worth printing for the drive.
            share = (f" at {conn.fired_share:.0%}"
                     if conn.fired_main and conn.fired_share < 0.999 else "")
            self.dial_box.addWidget(
                note("Firing: " + ", ".join(alight) + share + "."))
        if conn.fired_turning:
            self.dial_box.addWidget(note(
                "Swinging the hull round — the drive only pushes along the "
                "nose, so this tick is spent turning."))

    def closeEvent(self, event) -> None:      # noqa: N802
        self.timer.stop()
        if getattr(self.win, "flight_window", None) is self:
            self.win.flight_window = None
        super().closeEvent(event)


def open_flight(win) -> FlightWindow:
    """Open the flight controls, or raise the ones already open."""
    existing = getattr(win, "flight_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = FlightWindow(win)
    win.flight_window = window
    window.show()
    return window
