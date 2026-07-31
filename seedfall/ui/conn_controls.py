"""The conn's console: everything the pilot can press, and what it promises.

Split out of `ui/conn_window.py` when that file went past five hundred lines,
along a seam that was already there — the window owns the cameras, the panel and
the clock; this owns the controls. It holds no rules either. Every label and
every tooltip comes from `sim/pilot.quote`, which is the same door `apply`
spends through, so a button cannot promise what the burn will not do.

**What was missing.** `sim/conn.apply` has taken a `throttle` since the drive
learned to throttle and a `ticks` since it was written, and the console could
reach neither: it fired one full-power minute or nothing. See `sim/pilot.py` for
what that cost — a SPORE under a Fusion Torch moves 41.9 m/s per press, so a ten
metre a second correction was not askable. There is a throttle now, and a coast.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QWidget

from ..sim import conn as conn_sim
from ..sim import orbits
from ..sim import pilot as pilot_sim
from .widgets import button, light


class ConnControls(QWidget):
    """The button console. `sync` re-reads the live approach every refresh."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        #: Whether the main drive is selected rather than the clusters.
        self.use_main = False
        self._build()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)
        win = self.window

        # Two rows of three: the six axes, laid out the way a pilot's hand
        # sits on them rather than alphabetically.
        order = [("left", 0, 0), ("forward", 0, 1), ("right", 0, 2),
                 ("down", 1, 0), ("back", 1, 1), ("up", 1, 2)]
        self.axis_buttons = {}
        for axis_id, row, col in order:
            _aid, axis_label, _vec = conn_sim.AXES_BY_ID[axis_id]
            btn = button(axis_label, lambda a=axis_id: win._burn(a))
            grid.addWidget(btn, row, col)
            self.axis_buttons[axis_id] = btn

        self.main_btn = button("Main drive: off", self._toggle_drive,
                               kind="flat")
        grid.addWidget(self.main_btn, 0, 3)
        grid.addWidget(button("Hold (coast)", lambda: win._burn(None)), 1, 3)

        self.mode_buttons = {}
        for index, (mode, text) in enumerate(
                (("null", "Kill relative motion"),
                 ("close", "Close and berth"),
                 ("orbit", "Make orbit"))):
            btn = button(text, lambda m=mode: win._auto(m), kind="flat")
            grid.addWidget(btn, index // 2, 4 + index % 2)
            self.mode_buttons[mode] = (btn, text)

        # Which orbit, not merely whether. Only the heights this hull can
        # actually hold at this body are offered — see `orbits.heights_for`,
        # because a four-kilometre comet cannot be orbited to order by a ship
        # whose thrusters move it half a metre a second at a time.
        # One button per rung of the ladder, always built; `sync` hides the ones
        # this hull cannot hold at whatever it is looking at now.
        self.height_buttons = {}
        for index, (hid, label, _lift, _share) in enumerate(
                orbits.ORBIT_HEIGHTS):
            btn = button(label, lambda h=hid: win._set_height(h), kind="flat")
            grid.addWidget(btn, index // 2, 7 + index % 2)
            self.height_buttons[hid] = (btn, label)

        self.run_btn = button("Run clock", win._toggle_clock, kind="primary")
        grid.addWidget(self.run_btn, 1, 5)
        grid.addWidget(button("New approach…", win._pick_target, kind="flat"),
                       0, 6)
        # One button for *stop what you are doing*, and it says which. Giving
        # up on a berth and securing from a free flight are different acts:
        # the first abandons an approach, the second simply stops flying and
        # writes down where the ship ended up.
        self.free_btn = button("Break off", win._break_off, kind="flat")
        grid.addWidget(self.free_btn, 1, 6)

        # ── the throttle and the coast ─────────────────────────────────────
        # A third row, because these govern every button above them rather than
        # being one more thing to press. The throttle is the main drive's: the
        # clusters are pulsed, not throttled, which is why the row says so.
        self.throttle_buttons = {}
        for index, step in enumerate(pilot_sim.THROTTLE_STEPS):
            btn = button(f"{step * 100:.0f}%",
                         lambda v=step: self._set_throttle(v), kind="flat")
            grid.addWidget(btn, 2, index)
            self.throttle_buttons[step] = btn

        self.coast_buttons = {}
        for index, minutes in enumerate(pilot_sim.COAST_MINUTES):
            btn = button(f"{minutes} min",
                         lambda m=minutes: self._set_coast(m), kind="flat")
            grid.addWidget(btn, 2, 4 + index)
            self.coast_buttons[minutes] = btn

    # ── acts ───────────────────────────────────────────────────────────────

    def _toggle_drive(self) -> None:
        self.use_main = not self.use_main
        self.window.refresh()

    def _set_throttle(self, value: float) -> None:
        conn = self.window.conn
        if conn is None:
            return
        pilot_sim.set_throttle(conn, value)
        self.window.refresh()

    def _set_coast(self, minutes: int) -> None:
        conn = self.window.conn
        if conn is None:
            return
        pilot_sim.set_coast(conn, minutes)
        self.window.refresh()

    # ── what it says ───────────────────────────────────────────────────────

    def sync(self, conn) -> None:
        """Relabel every control from the live approach."""
        live = not conn.over
        self.main_btn.setText(
            f"Main drive: {'ON' if self.use_main else 'off'}")
        self.run_btn.setText(
            "Stop clock" if self.window.running else "Run clock")
        # The one button that changes what it *is*: with an approach running it
        # gives that approach up, and on a free flight it stops flying and
        # writes down where the ship ended up. Reading the approach rather
        # than a flag on the window, so it cannot say one thing while the pad
        # is doing the other.
        from ..sim import freeflight as free_sim
        free = free_sim.is_free(conn)
        self.free_btn.setText("Secure from the conn" if free else "Break off")
        for mode, (btn, text) in self.mode_buttons.items():
            btn.setText(f"▶ {text}" if self.window.mode == mode else text)

        # **Lit where the ship is actually firing.** The computer flies this
        # console as much as the pilot does, and until now a captain watching
        # it work saw six identical buttons and no sign of which one the
        # autopilot was using. `conn.fired_axis` is what the ship did last
        # tick — not what the computer would ask for if asked again, which is
        # a fresh forecast and disagrees the moment anything moves.
        for axis_id, btn in self.axis_buttons.items():
            light(btn, conn.fired_axis == axis_id)
        light(self.main_btn, bool(conn.fired_axis) and conn.fired_main)
        for mode, (btn, _text) in self.mode_buttons.items():
            light(btn, self.window.mode == mode)

        self._sync_heights(conn, live)
        self._sync_throttle(conn, live)
        self._sync_axes(conn, live)

    def _sync_heights(self, conn, live: bool) -> None:
        # The target changes when the ship is flown somewhere, so the row is
        # relabelled from the live conn rather than from whatever was alongside
        # when the window was built. That is the same
        # window-holding-a-copy-of-the-world fault this file has been fixed for
        # twice.
        # Priced, and the ones the tank cannot buy are shown *refused* rather
        # than hidden. The tank is volatiles in the hold, so a high orbit is a
        # fuel decision — measured, the high rung at a 4,179 km world wants 64 t
        # and a captain opens with 20 — and hiding the rung would hide the
        # decision along with it. The figures all come from
        # `pilot.climb_options`; nothing here works anything out.
        rungs = {row["id"]: row for row in self.window._climbs()}
        for hid, (btn, text) in self.height_buttons.items():
            row = rungs.get(hid)
            btn.setVisible(row is not None)
            if row is None:
                continue
            chosen = abs(conn.orbit_want_km - row["radius"]) < 1.0
            label = row["label"] if row["afford"] else f"{row['label']} ✕"
            btn.setText(f"▶ {label}" if chosen else label)
            btn.setEnabled(live and row["afford"])
            price = (f"{row['dv']:,.0f} m/s — allow about {row['mass']:,.0f} t "
                     f"of mass, and you have {row['tank']:,.0f}."
                     if row["dv"] > 0 else "You are already at this height.")
            btn.setToolTip(
                f"{row['label']} orbit — {row['up']:,.0f} km up. {price} "
                f"Leaving costs "
                f"x{orbits.departure_factor(conn.target.radius_km, row['radius']):.2f}; "
                f"a survey resolves "
                f"x{orbits.look_factor(conn.target.radius_km, row['radius']):.2f}."
                + ("" if row["afford"] else
                   " Not on this tank: take on more volatiles."))

    def _sync_throttle(self, conn, live: bool) -> None:
        """Mark what is set, and say what each rung is worth on this hull."""
        for step, btn in self.throttle_buttons.items():
            chosen = abs(conn.throttle - step) < 1e-9
            btn.setText(f"▶ {step * 100:.0f}%" if chosen
                        else f"{step * 100:.0f}%")
            btn.setEnabled(live)
            # Quoted in m/s, because a percentage of a number the pilot cannot
            # see is not information. The cap from a lopsided hull is included,
            # so the tooltip and the burn agree even when they disagree with
            # what was asked for.
            got = pilot_sim.usable_throttle(conn, True, step)
            worth = pilot_sim.dv_of(conn, True, step)
            capped = ("" if abs(got - step) < 1e-9
                      else f" — held to {got * 100:.0f}% by the trim")
            btn.setToolTip(f"Main drive at {step * 100:.0f}%: {worth:,.2f} m/s "
                           f"a press, {pilot_sim.burn_cost(conn, True, step):.3f}"
                           f" t{capped}")
        for minutes, btn in self.coast_buttons.items():
            chosen = conn.coast_min == minutes
            btn.setText(f"▶ {minutes} min" if chosen else f"{minutes} min")
            btn.setEnabled(live)
            btn.setToolTip(f"Every press lets {minutes} minute"
                           f"{'' if minutes == 1 else 's'} of flight run "
                           "afterwards.")

    def _sync_axes(self, conn, live: bool) -> None:
        ok, why = conn_sim.can_burn(conn, self.use_main)
        for axis_id, btn in self.axis_buttons.items():
            btn.setEnabled(live and ok)
            if not live:
                btn.setToolTip(why)
                continue
            # `pilot.quote` reads the throttle and the coast the pilot has set,
            # so the promise is the act. Before this the tooltip was computed at
            # full power for one minute whatever the console said.
            said = pilot_sim.quote(conn, axis_id, main=self.use_main)
            btn.setToolTip(
                f"{conn_sim.AXES_BY_ID[axis_id][1]} at {said['dv']:,.2f} m/s, "
                f"{said['minutes']} min: range "
                f"{said['range_km'] * 1000:,.0f} m, closing "
                f"{said['closing']:+,.1f} m/s, "
                f"{said['rcs']:,.2f} mass left"
                + ("" if ok else f" — {why}"))
