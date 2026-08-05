"""The conn: a pop-out window for flying the ship by hand.

A row of six camera feeds across the top, whichever one you pick blown up as
the main screen, an instrument panel down the side, and the controls: six
translation axes on thrusters or the main drive, three autopilot modes, and a
clock you can let run.

The window owns no rules. Every number on it comes from `sim/conn.py` and
every button calls into it — including the tooltips, which quote `pilot.quote`
so what the panel promises is what the burn does. The console itself is
`ui/conn_controls.py`; this file owns the cameras, the panel and the clock.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout,
                             QWidget)

from ..sim import autopilot as pilot_sim
from ..sim import berthing as berth_sim
from ..sim import freeflight as free_sim
from ..sim import orbits
from ..sim import pilot as console_sim
from ..sim import conn as conn_sim
from ..sim import track as track_sim
from .conn_targets import (default_target,  # re-exported: two checks import it here
                           same_place as _same_place)
from . import fire_panel, sights, theme
from . import conn_moves, conn_panel
from .conn_controls import ConnControls
from .viewport import Viewport
from .widgets import button, label, note

#: The window no longer keeps a clock of its own: `MainWindow.flight_timer`
#: is the one beat, at `pilot_view.BEAT_MS`, and `Conn.clock_on` is the one
#: answer to whether it is running.


class ConnWindow(QDialog):
    """Hand-flying, in its own window so the game stays behind it."""

    #: The chronicle's flight, not this window's. See `__init__`.
    conn = property(lambda self: self.win.conn,
                    lambda self, value: setattr(self.win, "conn", value))

    def __init__(self, win, contact=None):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.setWindowTitle("Conn — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1080, 760)

        live = self.win.conn
        # **The default target is measured from where she actually is.** A
        # free flight has flown somewhere; `default_target` ranks from the
        # ship's *recorded* position, which is wherever she was let go —
        # measured, a pilot who ran 4,800 km to stand alongside a hull
        # opened this window and was handed the Fleet Hub they had left.
        # Nearest first, out there; nothing in reach keeps the flight free.
        flying_free = (live is not None and not live.landed
                       and free_sim.is_free(live))
        if contact is None:
            if flying_free:
                import math as _math
                # Clearance to the *skin*, not range to the centre: a ship
                # in orbit of a world reads 290 km from a centre 6,000 km
                # deep, and the thing you are standing at is not a
                # manoeuvre — the `default_target` lesson, at altitude.
                near = []
                for c in track_sim.contacts(self.game):
                    if c.kind == "star" \
                            or not berth_sim.can_conn(self.game, c)[0]:
                        continue
                    km = _math.dist(free_sim.toward(self.game, live, c),
                                    (0.0, 0.0, 0.0))
                    from ..sim import targets as targets_sim
                    skin = targets_sim.target_from_contact(
                        self.game, c).radius_km or 0.0
                    if km > skin + conn_sim.ALONGSIDE_KM:
                        near.append((km - skin, c))
                near.sort(key=lambda row: row[0])
                contact = near[0][1] if near else None
            elif live is not None:
                # **A flight under way names its own target.** Asking
                # `default_target` instead handed the window whatever was
                # nearest the ship's recorded position — so opening the conn
                # while established in an orbit switched the target to a
                # quay and threw the orbit away: photographed, "Conn — Fleet
                # Hub, approach begun, 12.0 km" over a hull that was
                # circling a world under the computer. Which flight you are
                # on is not the window's to decide.
                #
                # `landed` is not part of the test: it means *arrived* —
                # secured at a quay, established in an orbit, set down on a
                # surface — and every one of those is still a flight whose
                # target this window should be showing.
                contact = next(
                    (c for c in track_sim.contacts(self.game)
                     if _same_place(self.game, live.target, c)),
                    None) or default_target(self.game)
            else:
                contact = default_target(self.game)
        self.contact = contact
        # **One flight, whichever window you look through.** This built its
        # own `Conn` while the Pilot screen kept another: measured, 290.9 km
        # and 60 minutes there showed as 12.0 km and full tanks here.
        self.refused = ""
        if contact is None:
            if live is None:
                # Nothing alongside is not nothing to see.
                self.win.conn = conn_sim.observe(self.game)
        elif live is not None and not live.landed and free_sim.is_free(live):
            # **Carry the way she has on.** `freeflight.hand_over` turns a
            # free flight into an approach without throwing away the
            # velocity, the nose or the mass already spent — which is the
            # whole reason it exists. A refusal leaves the free flight alone.
            handed, why = free_sim.hand_over(self.game, live, contact)
            if handed is not None:
                self.win.conn = handed
            else:
                self.refused = why
        elif live is not None and _same_place(self.game, live.target, contact):
            # **Already on this flight: leave it alone.** `landed` used to
            # send it down the branch below, and `landed` means *arrived* —
            # secured at a quay, established in an orbit, set down on a
            # surface. So opening the conn after berthing threw the flight
            # away and began a fresh one at the arrival range: moored at
            # Fleet Hub, `anchorage.docked_at` still naming the berth, and
            # the instruments reading 12,000 m. Precisely the fault this
            # window's own note says it exists to prevent. Taking the conn
            # again is a control the pilot presses, not a side effect of
            # opening a window.
            pass
        elif live is None or live.landed \
                or not _same_place(self.game, live.target, contact):
            fresh, why = berth_sim.begin(self.game, contact)
            if fresh is not None:
                self.win.conn = fresh
            self.refused = why
        self.main_view = "fore"
        #: Where the ship was when this approach opened, so the window can
        #: notice it being flown somewhere else.
        self.opened_at = (self.game.location_id,
                          getattr(self.game, "orbit_body", None))
        self._build()
        self.refresh()

    #: **The armed mode and the clock are the flight's, not this window's.**
    #: `Conn.auto` and `Conn.clock_on` — the same one-authority rule as `conn`
    #: itself, because this window holding its own `mode` is exactly how the
    #: bridge and the console came to give different answers about one ship.
    #: `mode` reads as None when nothing is armed, which is what its callers
    #: and checks have always expected.
    mode = property(
        lambda self: (getattr(self.conn, "auto", "") or None),
        lambda self, value: setattr(self.conn, "auto", value or "")
        if self.conn is not None else None)
    running = property(
        lambda self: bool(getattr(self.conn, "clock_on", False)))

    @property
    def contacts(self) -> list:
        """Everything in the system the ship is *now* in.

        Captured in `__init__` at first, so the window went on offering the
        traffic of a system the ship had left.
        """
        return [c for c in track_sim.contacts(self.game) if c.kind != "star"]

    # ── layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(9)

        head = QHBoxLayout()
        self.title = label("", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        # The camera row. Clicking one puts it on the main screen.
        strip = QHBoxLayout()
        strip.setSpacing(6)
        self.feeds = {}
        for view_id, view_label, _vec in conn_sim.VIEWS:
            cell = QWidget()
            box = QVBoxLayout(cell)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            feed = Viewport(self.conn, view_id, compact=True)
            feed.mousePressEvent = (
                lambda _e, v=view_id: self._show_view(v))
            box.addWidget(feed)
            # "Look port", not "Port" (#153): the console's thruster row says
            # Port and Starboard too, and one word wearing two controls is
            # how a probe — or a finger — presses the wrong one.
            look = button(f"Look {view_label.lower()}",
                          lambda v=view_id: self._show_view(v),
                          kind="flat")
            look.setObjectName(f"cam_{view_id}")
            box.addWidget(look)
            self.feeds[view_id] = feed
            strip.addWidget(cell, 1)
        column.addLayout(strip)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        self.screen = Viewport(self.conn, self.main_view)
        middle.addWidget(self.screen, 3)

        side = QWidget()
        self.side = QVBoxLayout(side)
        self.side.setContentsMargins(0, 0, 0, 0)
        self.side.setSpacing(4)
        side.setMinimumWidth(260)
        middle.addWidget(side, 1)
        column.addLayout(middle, 1)

        self.status = note("")
        self.status.setWordWrap(True)
        column.addWidget(self.status)

        self.controls = ConnControls(self)
        column.addWidget(self.controls)

    # ── acts ───────────────────────────────────────────────────────────────

    def _show_view(self, view_id: str) -> None:
        self.main_view = view_id
        self.screen.view_id = view_id
        self.refresh()

    def _climbs(self) -> list:
        """Every rung here, priced, and whether the tank can buy it.

        `pilot.climb_options` is the one door: it asks `orbits.heights_for` what
        the thrusters can hold and `orbits.climb_dv` what each rung costs, and
        the picker draws what comes back. The window works nothing out itself —
        a screen doing its own arithmetic about a number the sim already knows is
        how a forecast comes to disagree with the act.
        """
        if self.conn is None or self.conn.target.kind != "body":
            return []
        return console_sim.climb_options(self.conn)

    def _heights(self) -> list:
        """The rungs this hull can actually reach, as (id, label, radius)."""
        return [(row["id"], row["label"], row["radius"])
                for row in self._climbs() if row["afford"]]

    def _set_height(self, height_id: str) -> None:
        """Ask for an orbit at a named height, and fly to it."""
        if self.conn is None:
            return
        for hid, label, radius in self._heights():
            if hid == height_id:
                self.conn.orbit_want_km = radius
                up = radius - self.conn.target.radius_km
                self.win.toast(f"{label} orbit: {up:,.0f} km up.")
                # **Armed, not toggled.** Through `_auto` this disarmed the
                # computer whenever the mode was already `orbit` — so picking
                # a second rung mid-climb switched the autopilot off while
                # the rung picker put `▶` on the new height: the screen said
                # "climbing to High" and nothing was at the controls.
                self.mode = "orbit"
                if not self.running:
                    self.win.set_conn_clock(True)
                self.refresh()
                return

    def _toggle_drive(self) -> None:
        self.controls.use_main = not self.controls.use_main
        self.refresh()

    def _settle(self) -> None:
        """Charge the chronicle for the approach, once it is finished with.

        Reaction mass, the hours, the damage and where the hull ends up all
        land here. `berthing.commit` is idempotent, so calling it whenever
        the approach might be over is safe and means nothing is ever flown
        for free.
        """
        if self.conn is None or not self.conn.over or self.conn.landed:
            return
        out = berth_sim.commit(self.game, self.conn)
        if out.get("lost"):
            self.win.toast("The hull is gone.", "bad")
        elif out.get("moved"):
            self.win.toast(f"{self.conn.outcome.title()} at {out['moved']}. "
                           f"{out['fuel']:.2f} t spent.", "good")
        self.win.refresh()

    def _burn(self, axis_id) -> None:
        if self.conn is None or self.conn.over:
            return
        # At the throttle and the coast the console is showing, not at full
        # power for one minute. `pilot.quote` promises exactly this call.
        self.conn.apply_result = conn_sim.apply(
            self.conn, axis_id, main=self.controls.use_main,
            ticks=self.conn.coast_min, throttle=self.conn.throttle)
        # Pay as we go — the bridge always did, and a burn from this window
        # used to leave the stardate and the hold untouched until settling.
        berth_sim.charge_flown(self.game, self.conn)
        self._settle()
        self.win.beat_refresh()

    def _auto(self, mode: str) -> None:
        """Hand the conn to the flight computer, and let it fly on the clock.

        It used to run four hundred ticks inside the click — so pressing
        *Close and berth* teleported the hull to the target and reported the
        result, which is exactly what the conn exists not to do. The mode is
        held on the flight now and one tick is flown per beat of the one
        clock, so a berthing takes the forty minutes it takes and can be
        watched, corrected or called off half-way — from any window.
        """
        from . import flight_clock
        flight_clock.arm_mode(self.win, mode)
        self.refresh()

    def _toggle_clock(self) -> None:
        self.win.set_conn_clock(not self.running)
        self.refresh()

    def _tick(self) -> None:
        """One beat — `MainWindow.fly_beat`, the one clock. Kept as the name
        the checks drive a beat by hand through."""
        self.win.fly_beat()

    # ── swapping the flight — `ui/conn_moves.py`, bound as methods ─────────

    _leave_flight = conn_moves._leave_flight
    _reopen = conn_moves._reopen
    _pick_target = conn_moves._pick_target
    _free_flight = conn_moves._free_flight

    def _break_off(self) -> None:
        """Stop. Give up an approach, or secure from a free flight.

        Two acts behind one button, told apart by what is being flown rather
        than by a flag on the window. Breaking off abandons a berth and the
        mass already burned is not coming back; securing writes down where the
        ship has actually got to, which is the whole point of having flown.
        """
        from ..sim import freeflight as free_sim
        if self.conn is not None and free_sim.is_free(self.conn):
            said = free_sim.secure(self.game, self.conn)
            self.win.set_conn_clock(False)
            self._settle()
            self.win.toast(said)
            self._reopen()
            self.refresh()
            return
        if self.conn is not None and not self.conn.over:
            self.conn.outcome = "broken off"
            self.conn.log.append("Approach broken off.")
        self.win.set_conn_clock(False)
        self._settle()
        self.refresh()

    # ── painting ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        # A course set at the helm moves the ship, and this window was built
        # around wherever it was standing when it opened — so it went on
        # showing an approach on somewhere the hull had left. If the ship has
        # moved, the approach is reopened on whatever is alongside now.
        here = (self.game.location_id, getattr(self.game, "orbit_body", None))
        if here != self.opened_at:
            self.opened_at = here
            self._reopen()

        conn = self.conn
        # **The cameras follow the live flight, including to None.** Securing
        # from the bridge nulls `game.conn`; the feeds used to keep painting
        # the destroyed object because nothing re-pointed them, and the early
        # return below never reached the update loop at the bottom.
        for feed in self.feeds.values():
            feed.conn = conn
        self.screen.conn = conn
        if conn is None:
            self.title.setText("Nothing is being flown")
            self.status.setText(self.refused
                                or "Take the conn with New approach…")
            for feed in self.feeds.values():
                feed.update()
            self.screen.update()
            return
        from ..sim import freeflight as free_sim
        if free_sim.is_free(conn):
            # Not "Conn — open space": the title is where a captain looks to
            # know what the ship is doing, and what it is doing is flying.
            self.title.setText(
                f"Conn — under way, {free_sim.standing(self.game, conn)}")
        else:
            self.title.setText(
                f"Conn — {conn.target.name}" if conn.outcome != "watching"
                else f"Conn — station keeping at {self.game.system.name}")
        self.controls.sync(conn)
        # **Name what is out there.** Measured at 130.3 km off the Fleet Hub:
        # `sights` was `()`, a starfield and an unnamed crosshair — the
        # player's report wearing the other window's hat. The thumbnails stay
        # bare on purpose; 120 px has no room for a name.
        self.screen.sights = sights.out_there(
            self.game, conn, fire_panel.ranged(self.game, conn, self.contacts))

        # The side panel — `ui/conn_panel.py`: updated in place on a beat,
        # rebuilt only when the set of things it says changes. This window
        # tore the whole column down four times a second, the same churn the
        # Pilot screen was fixed for (#150).
        conn_panel.apply(self, conn)

        if conn.over:
            self.status.setText(f"{conn.outcome.upper()} — "
                                + (conn.log[-1] if conn.log else ""))
        else:
            self.status.setText(conn.log[-1] if conn.log else "")

        for feed in self.feeds.values():
            feed.update()
        self.screen.update()

    def keyPressEvent(self, event) -> None:      # noqa: N802
        from . import flying_keys
        if not flying_keys.press(self.win, event):
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:    # noqa: N802
        from . import flying_keys
        if not flying_keys.release(self.win, event):
            super().keyReleaseEvent(event)

    def closeEvent(self, event) -> None:
        from . import flight_clock
        flight_clock.end_burn(self.win, quiet=True)   # no release is coming
        # **Closing this window is leaving the room, not stopping the ship.**
        # It used to write `outcome = "broken off"` and settle on the way out,
        # ending an approach under a pilot still flying it from the bridge.
        # `_break_off` is the one door onto giving up. Nothing is flown for
        # free: `berthing.commit` still runs when the approach resolves, on
        # break-off, and when she secures. (A flight nobody ends: task #149.)
        self._settle()
        if getattr(self.win, "conn_window", None) is self:
            self.win.conn_window = None
        super().closeEvent(event)


def open_conn(win, contact=None) -> ConnWindow:
    """Open the conn, or raise the one already open."""
    existing = getattr(win, "conn_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = ConnWindow(win, contact)
    win.conn_window = window
    window.show()
    return window
