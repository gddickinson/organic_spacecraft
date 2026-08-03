"""The Pilot's screen: what is out there, all the time, with the clock running.

The Conn is for a *situation* — an approach to a berth, an orbit to make. This
is the general case: the ship, open space, and a live view out of whichever
camera the pilot is looking through. It is always available and it never has a
destination.

**The clock runs here, and that is the whole difference.** An approach tells
the chronicle once, at the end. This tells it as it goes, through
`sim/berthing.charge_flown` — the one door, which bills only the minutes nobody
has billed yet and remembers them on `Conn.charged`, so a pilot who flies here
and then breaks off does not pay twice for the same hour.

That is only safe because the clock is honest. `core/clock.MAX_STEP` is 1, so a
jump of N days is N jumps of one (#116), and charging in pieces is *exactly*
charging once — measured, three days billed in one call and in 4,320 leave the
same day and the same purse to the cent. Before that landed, a live screen
would have quietly drifted away from a played one.

Nothing here is a rule. The flying is `sim/conn`, the computer is
`sim/autopilot`, where the ship ends up is `sim/flight.stand_off`, what may be
fired on is `sim/engage`, and what is worth looking at is `ui/conn_targets`.
"""

from __future__ import annotations

from PyQt6.QtCore import QTimer

from ..sim import autopilot as auto_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import freeflight as free_sim
from ..sim import instruments as panel_sim
from ..sim import pilot as pilot_sim
from ..sim import track as track_sim
from . import fire_panel
from . import pilot_panels as panels
from .viewport import Viewport
from .widgets import Panel, View, button, note

#: Real milliseconds between ticks while the clock is running.
#:
#: One `conn.TICK` is a minute of ship time, so at 250 ms a pilot watching for
#: a real minute spends four hours of the chronicle — fast enough that a burn
#: reads as motion, slow enough that a distracted captain does not lose a week.
BEAT_MS = 250


class PilotView(View):
    """The bridge view. Holds its own free flight; never an approach."""

    heading = "Pilot"

    #: **The flight belongs to the chronicle, not to this screen.** It used
    #: to be `self.conn`, so flying here and then opening the Conn window
    #: showed a different ship — measured, 290.9 km and 60 minutes here
    #: against 12.0 km and full tanks there. `ui/window.conn` is the one door;
    #: both screens are views of the same `sim/conn.Conn`.
    conn = property(lambda self: self.win.conn,
                    lambda self, value: setattr(self.win, "conn", value))

    def __init__(self, win):
        super().__init__(win)
        self.camera = "fore"
        self.running = False
        self.feed = None
        #: The main drive rather than the attitude clusters. The clusters trim;
        #: the torch is what gets you across a system, and it only ever pushes
        #: along the nose — see `conn.thrust_axis`.
        self.use_main = False
        #: The contact the course is laid on, by name, or "".
        #:
        #: The *name*, not the object: `sim/track` rebuilds its contacts on
        #: every call, so holding one would be holding yesterday's position of
        #: a thing that has since moved.
        self.mark = ""
        #: What the flight computer is doing: "", "hold" or "run".
        self.auto = ""
        #: What the last press actually did, for the screen to say.
        self.last = {}
        #: Has the pilot secured? Not a second answer to "are we flying" —
        #: `game.conn` is that — but to "should the bridge hand her back".
        self.stood_down = False
        #: What the controls on screen were built for; None until they are.
        self._shape = None
        self._boards: dict = {}
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)

    # ── the flight ─────────────────────────────────────────────────────────

    def ensure_conn(self) -> str:
        """Take the conn on open space if we are not already flying.

        Through `freeflight.begin`, which is the one door: the gate is
        reaction mass and nothing else, because there is nobody to clear you
        to fly around your own system.

        **Unless the pilot has stood down.** `secure` ends the flight and then
        asks the window to redraw, which comes back through here — so pressing
        "Secure from the conn" used to write the leg down, settle the bill and
        hand her straight back: measured, 30 minutes flown became a fresh conn
        on the same breath, a different object at 0 minutes. The button read
        as doing nothing. Standing down is a thing the pilot decides, so it is
        remembered until she asks for the ship again.
        """
        if self.conn is not None and not self.conn.landed:
            return ""       # already flying — the Conn window's flight, if any
        if self.stood_down:
            return ("You have secured from the conn. The ship holds where you "
                    "left her.")
        self.conn, why = free_sim.begin(self.game)
        return why

    def take_conn(self) -> None:
        """The pilot asks for the ship back after standing down."""
        self.stood_down = False
        self.win.refresh()

    def tick(self) -> None:
        """One beat: fly, then pay for it."""
        if self.conn is None or self.conn.landed:
            return
        self.hold_course()
        # A coast, unless the computer has the conn. The pilot's own burns
        # come from the console; a beat with nothing pressed and no autopilot
        # is a minute of drifting, which is what a live view mostly is.
        axis, main, throttle = self.computer()
        self.last = conn_sim.apply(self.conn, axis, main=main, ticks=1,
                                   throttle=throttle)
        # **Pay as we go.** The same door `berthing.commit` settles through,
        # so neither can bill a minute the other already has.
        berth_sim.charge_flown(self.game, self.conn)
        if self.win.check_ending():
            self.set_running(False)
            return
        self.refresh()

    def marked(self):
        """The contact the course is laid on, re-read from the sim."""
        if not self.mark or self.conn is None:
            return None
        for contact in track_sim.contacts(self.game):
            if contact.name == self.mark:
                return contact
        return None

    def hold_course(self) -> None:
        """Keep the course on the mark. Called every beat and every burn.

        A contact is not standing still — a hull holding station rides its
        body round the star — so a course laid once and left alone stops
        pointing at it. Laying it again each beat is what makes "Ahead" mean
        "at that" for the whole flight rather than for the first minute.
        """
        contact = self.marked()
        if contact is not None:
            free_sim.steer(self.game, self.conn, contact)

    def computer(self) -> tuple:
        """What the flight computer would do this beat.

        `(axis, main, throttle)`, exactly what `sim/autopilot` returns,
        because it is what `sim/autopilot` returned. The screen decides
        *whether* the computer has the conn; it never decides what flying is.
        """
        if not self.auto or self.conn is None:
            return None, False, 1.0
        if self.auto == "run":
            aim = self.marked()
            if aim is None:
                return None, False, 1.0
            if free_sim.alongside(self.game, self.conn, aim):
                # Arrived. Say so once and give the conn back.
                self.auto = "hold"
                self.game.add_log(f"Alongside {aim.name}, "
                                  f"{free_sim.ALONGSIDE_KM:,.0f} km off.", "")
                return auto_sim.autopilot(self.conn, "null")
            return free_sim.run_for(self.game, self.conn, aim)
        return auto_sim.autopilot(self.conn, "null")

    def set_auto(self, mode: str) -> None:
        self.auto = "" if self.auto == mode else mode
        self.refresh()

    def fly_at(self, contact) -> None:
        """Lay the course on something in view. The hull comes about itself."""
        self.mark = contact.name
        self.hold_course()
        self.game.add_log(
            f"Course laid on {contact.name}, "
            f"{engage_sim.range_km(self.game, self.conn, contact):,.0f} km off.",
            "")
        self.refresh()

    def break_off(self) -> None:
        self.mark = ""
        if self.auto == "run":
            self.auto = ""
        self.refresh()

    def burn(self, axis_id: str | None) -> dict:
        """Fire along an axis, or coast with `None`, and pay for the minute.

        The same two calls `tick` makes, in the same order, because a burn is
        a beat with the pilot's hand on it — not a second way for time to pass.
        """
        if self.conn is None or self.conn.landed:
            return {}
        self.hold_course()
        # At the throttle and the coast the console is showing, which is the
        # call `ui/conn_window._burn` makes and the one `pilot.quote`
        # promises. Both read `conn`, so neither can promise what the other
        # will not do.
        said = conn_sim.apply(self.conn, axis_id, main=self.use_main,
                              ticks=self.conn.coast_min,
                              throttle=self.conn.throttle)
        self.last = said
        berth_sim.charge_flown(self.game, self.conn)
        self.refresh()
        return said

    def leaving(self) -> None:
        """Walking off the bridge stops the clock, however you left.

        **Not a callback passed by whoever navigated away.** The first version
        had `fire_panel` take an `after` hook so opening fire could stop the
        beat, and a mutation showed exactly what that is worth: the guarantee
        held only for the one button that remembered to pass it. Time not
        passing while you are being shot at is a rule about the game, not
        about a button — and the same goes for walking to the Shipyard with
        the clock running.

        `hideEvent` was the second attempt and is not the door either: Qt
        posts no hide event for a widget that was never really shown, so it
        held in a played window and not in a built one. `ui/window.go` calls
        this on every route out.
        """
        self.set_running(False)

    def set_running(self, on: bool) -> None:
        self.running = bool(on) and self.conn is not None
        if self.running:
            self._timer.start(BEAT_MS)
        else:
            self._timer.stop()

    def secure(self) -> None:
        """Stop flying and write down where the ship ended up."""
        self.set_running(False)
        if self.conn is None:
            return
        said = free_sim.secure(self.game, self.conn)
        berth_sim.commit(self.game, self.conn)
        self.game.add_log(said, "")
        self.mark = ""
        self.auto = ""
        self.conn = None
        self.stood_down = True
        self.win.refresh()

    # ── what is out there ──────────────────────────────────────────────────

    def ranged(self) -> list:
        """`(km, contact)` for everything but the star, nearest first.

        Measured once and handed down. Asking per widget cost 27 rebuilds of
        the system's traffic per button press — see `ui/fire_panel.ranged`.
        """
        if self.conn is None:
            return []
        here = [c for c in track_sim.contacts(self.game) if c.kind != "star"]
        return fire_panel.ranged(self.game, self.conn, here)

    def in_view(self) -> list:
        """Contacts worth naming, nearest first."""
        return [c for _km, c in self.ranged()]

    # ── painting ───────────────────────────────────────────────────────────

    # ── the beat ───────────────────────────────────────────────────────────

    def shape(self, rows) -> tuple:
        """What decides *which* controls exist, as against what they read.

        Not a second copy of `build`'s rules: every entry is asked of the same
        door `build` asks — `ranged`, `marked`, `fire_panel.shape`.
        """
        return (self.conn is None, self.stood_down, self.mark, self.auto,
                self.marked() is not None,
                tuple(c.name for _km, c in rows[:4]),
                fire_panel.shape(self.game, rows))

    def refresh(self) -> None:
        """A beat changes readings. Only a change of situation changes controls.

        **The player's report: "when the clock is running the buttons do not
        act immediately, and often don't respond at all."** This used to be
        `View.refresh` — the whole screen taken apart and built again, four
        times a second at `BEAT_MS` 250. Measured: **0 of 25 buttons survived
        one beat.** A `QPushButton` emits `clicked` only if the release reaches
        the object that took the press, and a click is held down 80-150 ms, so
        a beat landing in the middle swallowed it whole. Measured through the
        buttons: press "Ahead", one beat, let go over "Ahead" — *the burn did
        not happen*; with no beat in between, it did.

        **It was never about speed**, which is where the first guess went. A
        whole beat costs 13.4 ms against a 250 ms budget — 12.4 of it the
        rebuild, 0.6 the flying. The screen was not too slow to keep up; it
        was throwing away the button under the pilot's finger.

        So the controls are built once and stay built. `sync` updates what a
        beat actually changes, and a full rebuild happens only when `shape`
        says the situation itself changed — a contact in or out of the list, a
        course laid, a hull come into reach.
        """
        if self.conn is None or self._shape is None:
            self._shape = None
            super().refresh()
            return
        rows = self.ranged()
        if self.shape(rows) != self._shape:
            super().refresh()
            return
        self.sync(rows)

    def sync(self, rows) -> None:
        """Update the readings in place, touching no control."""
        self.feed.conn = self.conn
        self.feed.view_id = self.camera
        panels.aim_feed(self, rows)
        self.feed.update()
        self._btn_main.setText(panels.main_label(self))
        self._btn_throttle.setText(panels.throttle_label(self))
        self._btn_clock.setText(panels.clock_label(self))
        self._swap("ship", panels.ship_board(self))
        self._swap("view", panels.in_view_board(self, rows))
        self._swap("fire", fire_panel.board(self.game, self.conn, rows))

    def _swap(self, key: str, fresh) -> None:
        """Put a newer readout where the old one stood.

        Through `View.park`, so the outgoing widget outlives the event we may
        be inside — the same rule `View.refresh` keeps, for one widget.
        """
        old = self._boards[key]
        # Its own column, asked of the widget: the boards no longer all live
        # in one, and a remembered layout would put the fire control back in
        # the column it was moved out of.
        box = old.parentWidget().layout()
        at = box.indexOf(old)
        box.removeWidget(old)
        self.park(old)
        box.insertWidget(at, fresh)
        self._boards[key] = fresh

    def build(self) -> None:
        why = self.ensure_conn()
        self.head("Pilot", "The view from the bridge, and the ship in your hands.")
        if self.conn is None:
            self.col.addWidget(note(why or "The ship cannot be flown."))
            if self.stood_down:
                self.col.addWidget(panels.row_of(
                    button("Take the conn", self.take_conn, kind="primary")))
            return

        # **Two columns, because one was 662 pixels too tall.** Measured on a
        # shown window at 1360x880: the bridge came to 1,444 px in a 782 px
        # view, so the fire control, the autopilot and the clock were all
        # below the fold and the pilot had to scroll past the instruments to
        # reach a trigger. The room was sideways and nobody was using it.
        holder, left, right = panels.two_columns()
        self.col.addWidget(holder)
        rows = self.ranged()
        # **Emptied here, before either column fills it.** The fire control is
        # built into the left column, which happens first; a `self._boards =
        # {...}` further down then threw that entry away and the next beat
        # died on `KeyError: 'fire'`. Found by flying it.
        self._boards = {}

        self.feed = Viewport(self.conn, self.camera)
        # **Ring the thing the course is laid on, and name the traffic.** One
        # door, shared with the beat, which refreshes both without rebuilding
        # the feed. Handed bearings from `freeflight.toward` — the window
        # looks nothing up itself.
        panels.aim_feed(self, rows)
        left.addWidget(self.feed)
        # Three to a line: six across demanded 486 px and set the left
        # column's minimum, which is 56 px more than the bridge had to give.
        left.addWidget(panels.stack_of([
            button(row[1], lambda _=False, v=row[0]: self._look(v), kind="flat")
            for row in conn_sim.VIEWS], per_row=3))
        # The hand on the stick, in the order a pilot's hand sits on it — the
        # same order `ui/conn_controls` uses.
        left.addWidget(panels.row_of(*[
            button(conn_sim.AXES_BY_ID[a][1], lambda _=False, x=a: self.burn(x))
            for a in ("left", "forward", "right", "down", "back", "up")]))
        # Held, because a beat updates their text rather than replacing them.
        self._btn_main = button(panels.main_label(self), self._toggle_main,
                                kind="flat")
        self._btn_throttle = button(panels.throttle_label(self),
                                    self._cycle_throttle, kind="flat")
        self._btn_clock = button(panels.clock_label(self), self._toggle,
                                 kind="primary")
        left.addWidget(panels.row_of(
            button("Hold (coast)", lambda: self.burn(None), kind="flat"),
            self._btn_main, self._btn_throttle))
        left.addWidget(panels.stack_of([
            self._btn_clock,
            button("Secure from the conn", self.secure, kind="flat"),
            button("Take the conn on something…", self._to_conn, kind="flat")],
            per_row=2))
        # **The guns go with the hands, not with the boards.** This file's own
        # rule is that the left column is the view and what flies her and the
        # right is what tells you where you are — and a trigger is a hand.
        # Measured shown at 1360x880: the left column carried 173 px of
        # controls and the right 777, so the right alone set the height, and
        # the two controls pushed off the bottom were "Open fire on Patient
        # Ledger" and "Mark Patient Ledger hostile". A pilot in a fight had to
        # scroll to shoot.
        self._boards["fire"] = fire_panel.board(self.game, self.conn, rows)
        left.addWidget(self._boards["fire"])
        guns = fire_panel.buttons(self.win, self.game, self.conn, rows)
        if guns:
            left.addWidget(panels.stack_of(guns))
        flags = fire_panel.marks(self.win, self.game, rows)
        if flags:
            left.addWidget(panels.stack_of(flags))
        left.addStretch(1)

        # The readouts are swapped whole on a beat: they are labels, so
        # nothing the pilot can be pressing lives in them.
        self._boards["ship"] = panels.ship_board(self)
        self._boards["view"] = panels.in_view_board(self, rows)
        right.addWidget(self._boards["ship"])
        right.addWidget(self._boards["view"])
        seen = [c for _km, c in rows][:4]
        if seen:
            # What you can see, you can go to: the whole point of the screen.
            right.addWidget(panels.stack_of([
                button(f"Fly at {c.name}", lambda _=False, k=c: self.fly_at(k),
                       kind="flat") for c in seen]))
        aim = self.marked()
        right.addWidget(panels.stack_of([
            button(("Stop holding station" if self.auto == "hold"
                    else "Hold station"),
                   lambda: self.set_auto("hold"), kind="flat"),
            *([button(("Stop running for it" if self.auto == "run"
                       else f"Run for {aim.name}"),
                      lambda: self.set_auto("run"), kind="flat")]
              if aim is not None else []),
            *([button("Break off the course", self.break_off, kind="flat")]
              if aim is not None else [])]))

        # **The guns.** One door, `ui/fire_panel`, shared with any screen that
        # grows a fire control.
        right.addStretch(1)
        self._shape = self.shape(rows)

    def _look(self, view_id: str) -> None:
        self.camera = view_id
        self.refresh()

    def _toggle_main(self) -> None:
        self.use_main = not self.use_main
        self.refresh()

    def _cycle_throttle(self) -> None:
        """Step round `pilot.THROTTLE_STEPS`, through the one door that sets it.

        **The first draft kept its own `self.throttle`** and passed it to
        `apply` as a keyword. Rendered and looked at, the button read
        "THROTTLE: 50%" and the ship panel one row below it read "Throttle
        100%" — the same fact, two answers, because `instruments.readout`
        reads `conn.throttle` and nothing had written it. The throttle lives
        on the conn; `pilot.set_throttle` is its only writer.
        """
        steps = list(pilot_sim.THROTTLE_STEPS)
        here = min(range(len(steps)),
                   key=lambda i: abs(steps[i] - self.conn.throttle))
        pilot_sim.set_throttle(self.conn, steps[(here + 1) % len(steps)])
        self.refresh()

    def _toggle(self) -> None:
        self.set_running(not self.running)
        self.refresh()

    def _to_conn(self) -> None:
        """Hand this flight to an approach, carrying the way already on."""
        from .conn_window import open_conn
        self.set_running(False)
        open_conn(self.win)
