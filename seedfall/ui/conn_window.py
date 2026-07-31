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

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QVBoxLayout,
                             QWidget)

from ..sim import autopilot as pilot_sim
from ..sim import berthing as berth_sim
from ..sim import orbits
from ..sim import pilot as console_sim
from ..sim import conn as conn_sim
from ..sim import instruments as panel_sim
from ..sim import track as track_sim
from . import theme
from .conn_controls import ConnControls
from .viewport import Viewport
from .widgets import button, label, note

#: How often the window re-reads the approach while the clock is running.
TICK_MS = 700


class ConnWindow(QDialog):
    """Hand-flying, in its own window so the game stays behind it."""

    def __init__(self, win, contact=None):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.setWindowTitle("Conn — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1080, 760)

        if contact is None:
            contact = default_target(self.game)
        self.contact = contact
        if contact is not None:
            self.conn, self.refused = berth_sim.begin(self.game, contact)
        else:
            # Nothing alongside is not nothing to see.
            self.conn, self.refused = conn_sim.observe(self.game), ""
        self.main_view = "fore"
        self.running = False
        #: Which autopilot mode is flying, if any. Held rather than run to
        #: completion inside a click.
        self.mode = None
        #: Where the ship was when this approach opened, so the window can
        #: notice it being flown somewhere else.
        self.opened_at = (self.game.location_id,
                          getattr(self.game, "orbit_body", None))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._build()
        self.refresh()

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
            box.addWidget(button(view_label,
                                 lambda v=view_id: self._show_view(v),
                                 kind="flat"))
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
                self._auto("orbit")
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
        self._settle()
        self.refresh()

    def _auto(self, mode: str) -> None:
        """Hand the conn to the flight computer, and let it fly on the clock.

        It used to run four hundred ticks inside the click — so pressing
        *Close and berth* teleported the hull to the target and reported the
        result, which is exactly what the conn exists not to do. The mode is
        held now and one tick is flown per beat of the same clock the coast
        button uses, so a berthing takes the forty minutes it takes and can
        be watched, corrected or called off half-way.
        """
        if self.conn is None or self.conn.over:
            return
        if self.mode == mode:
            self.mode = None                 # pressing it again lets go
            self.refresh()
            return
        self.mode = mode
        if not self.running:
            self._toggle_clock()
        else:
            self.refresh()

    def _fly_one(self) -> bool:
        """One tick under the computer. False when it has nothing to add."""
        axis, main, throttle = pilot_sim.autopilot(self.conn, self.mode)
        if axis is None and self.mode == "null":
            return False
        conn_sim.apply(self.conn, axis, main=main, throttle=throttle)
        return True

    def _toggle_clock(self) -> None:
        self.running = not self.running
        if self.running:
            self.timer.start(TICK_MS)
        else:
            self.timer.stop()
        self.refresh()

    def _tick(self) -> None:
        if self.conn is None or self.conn.over:
            self.running = False
            self.timer.stop()
        elif self.mode:
            if not self._fly_one():
                self.mode = None
                self.win.toast("The computer has nothing to add.", "warn")
        else:
            conn_sim.apply(self.conn, None)
        self._settle()
        self.refresh()

    def _reopen(self) -> None:
        """Rebuild the approach after the ship has been flown somewhere."""
        self._settle()
        self.mode = None
        self.running = False
        self.timer.stop()
        contact = default_target(self.game)
        self.contact = contact
        if contact is None:
            self.conn, self.refused = conn_sim.observe(self.game), ""
        else:
            self.conn, self.refused = berth_sim.begin(self.game, contact)
            if self.conn is None:
                self.conn = conn_sim.observe(self.game)
        for feed in self.feeds.values():
            feed.conn = self.conn
        self.screen.conn = self.conn

    def _pick_target(self) -> None:
        """Only what the ship is actually alongside. Everything else is a burn.

        The list used to offer every contact in the system, so a captain could
        open the conn on a hull eight AU away and fly the last ten kilometres
        of a journey they had not made.
        """
        self._settle()
        near = [c for c in self.contacts if berth_sim.can_conn(self.game, c)[0]]
        # **Flying for its own sake is one of the choices.** With nothing in
        # reach this used to be a dead end — "plot a transfer first" — which
        # is true about *berthing* and was being said about *flying*. A
        # captain may take the conn whenever they like; there is nobody to
        # ask permission of to move your own ship.
        rows = [f"{c.name} — {c.detail}" for c in near[:12]]
        picked = self.win.dialog(
            "Approach which?",
            (["The conn is the last few kilometres. These are what the ship "
              "is already alongside."] if near else
             ["Nothing is within reach of the thrusters — but the ship is "
              "yours to fly."]) + rows,
            [(c.name, index) for index, c in enumerate(near[:6])]
            + [("Fly free — no destination", "free"), ("Cancel", None)])
        if picked is None:
            return
        if picked == "free":
            self._free_flight()
            return
        self.contact = near[picked]
        self.mode = None
        self.conn, self.refused = berth_sim.begin(self.game, self.contact)
        for feed in self.feeds.values():
            feed.conn = self.conn
        self.screen.conn = self.conn
        self.refresh()

    def _free_flight(self) -> None:
        """Take the conn on open space: fly the ship because you want to.

        The same pad, the same cameras, the same tank — with no target and
        nothing to arrive at. It ends when the pilot secures.
        """
        from ..sim import freeflight as free_sim
        self._settle()
        conn, why = free_sim.begin(self.game)
        if conn is None:
            self.win.toast(why, "warn")
            return
        self.contact = None
        self.mode = None
        self.conn, self.refused = conn, ""
        # The window watches for the ship being moved out from under it; a
        # free flight *is* the ship being moved, so what it opened at has to
        # be brought up to date or the next refresh throws the flight away.
        self.opened_at = (self.game.location_id,
                          getattr(self.game, "orbit_body", None))
        for feed in self.feeds.values():
            feed.conn = self.conn
        self.screen.conn = self.conn
        self.win.toast("The conn is yours. No destination set.")
        self.refresh()

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
            self.running = False
            self.timer.stop()
            self._settle()
            self.win.toast(said)
            self._reopen()
            self.refresh()
            return
        if self.conn is not None and not self.conn.over:
            self.conn.outcome = "broken off"
            self.conn.log.append("Approach broken off.")
        self.running = False
        self.timer.stop()
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
        if conn is None:
            self.title.setText("Nothing in range to approach")
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

        while self.side.count():
            item = self.side.takeAt(0)
            if item.widget():
                # Now, not when the event loop next idles: a deferred delete
                # leaves the old readout painted under the new one.
                item.widget().setParent(None)
        for name, value, kind in panel_sim.readout(conn):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            left = QLabel(name)
            left.setStyleSheet(f"color: {theme.INK3}; font-size: 12px;")
            right = QLabel(value)
            right.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK};"
                f"font-family: '{theme.mono_family()}'; font-size: 12.5px;")
            line.addWidget(left)
            line.addStretch(1)
            line.addWidget(right)
            self.side.addWidget(row)
        hint = conn_sim.orbit_note(conn)
        if hint:
            self.side.addWidget(note(hint))
        # Where the nose is, and what is pushing. Until the engines had
        # places and the hull had an orientation, neither of these existed.
        from ..sim import attitude as attitude_sim
        from ..sim import thrusters
        self.side.addWidget(note(attitude_sim.heading_note(conn)))
        self.side.addWidget(label("Engines", "h3"))
        for what, howmuch, where in thrusters.board(self.game.ship):
            self.side.addWidget(note(f"{what} — {howmuch}, {where}"))
        self.side.addStretch(1)

        if conn.over:
            self.status.setText(f"{conn.outcome.upper()} — "
                                + (conn.log[-1] if conn.log else ""))
        else:
            self.status.setText(conn.log[-1] if conn.log else "")

        for feed in self.feeds.values():
            feed.update()
        self.screen.update()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        # Closing the window is not a way to un-burn the fuel.
        if self.conn is not None and not self.conn.over:
            self.conn.outcome = "broken off"
        self._settle()
        if getattr(self.win, "conn_window", None) is self:
            self.win.conn_window = None
        super().closeEvent(event)


#: What to conn when the captain has not said. Ordered by what a pilot at
#: close quarters would actually be looking at.
#:
#: A station is what you dock with, and it is the thing worth watching come
#: up in the windows. Standing alongside the Fleet Hub, the first draft of
#: this opened the conn on **the planet** — because `track.contacts` lists
#: bodies before anchorages and the window took the first row in reach. You
#: are already in orbit of the body; approaching it is not a manoeuvre.
#:
#: The body came last on the reasoning that approaching what you are already
#: orbiting is not a manoeuvre. That was true when an orbit had no height.
#: It is not true now — see `orbits.ORBIT_HEIGHTS` — so a world you are
#: standing at is something a captain can act on, and it outranks a stranger's
#: hull that happens to be passing.
DEFAULT_ORDER = ("anchorage", "body", "hull")


def default_target(game):
    """The most useful thing in reach to open an approach on.

    **Where the ship actually is comes first.** Traffic drifts, and once
    bodies moved onto their real orbits a passing freighter could easily be
    the nearest thing in the system — so the conn opened on `Patient Ledger`
    while the hull sat in orbit around a world it was not being shown. Anything
    co-located with the ship wins, in the order above; only then does the rest
    of the system get a look in.
    """
    reachable = [c for c in track_sim.contacts(game)
                 if c.kind != "star" and berth_sim.can_conn(game, c)[0]]
    here_id = getattr(game, "orbit_body", None)
    index = next((i for i, b in enumerate(game.system.bodies)
                  if b.id == here_id), None) if here_id else None

    def at_the_ship(contact) -> bool:
        return index is not None and contact.body_index == index

    for group in (True, False):
        pool = [c for c in reachable if at_the_ship(c) is group]
        for kind in DEFAULT_ORDER:
            found = [c for c in pool if c.kind == kind]
            if found:
                return found[0]
    return None


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
