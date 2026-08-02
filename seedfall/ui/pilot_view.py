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

    def __init__(self, win):
        super().__init__(win)
        self.conn = None
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
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.tick)

    # ── the flight ─────────────────────────────────────────────────────────

    def ensure_conn(self) -> str:
        """Take the conn on open space if we are not already flying.

        Through `freeflight.begin`, which is the one door: the gate is
        reaction mass and nothing else, because there is nobody to clear you
        to fly around your own system.
        """
        if self.conn is not None and not self.conn.landed:
            return ""
        self.conn, why = free_sim.begin(self.game)
        return why

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

    def build(self) -> None:
        why = self.ensure_conn()
        self.head("Pilot", "The view from the bridge, and the ship in your hands.")
        if self.conn is None:
            self.col.addWidget(note(why or "The ship cannot be flown."))
            return

        self.feed = Viewport(self.conn, self.camera)
        self.col.addWidget(self.feed)

        cams = [button(row[1], lambda _=False, v=row[0]: self._look(v),
                       kind="flat") for row in conn_sim.VIEWS]
        self.buttons(*cams)

        # The hand on the stick. Laid out the way a pilot's hand sits on it,
        # the same order `ui/conn_controls` uses — six axes, a coast, and the
        # torch for a long burn. Every one of them goes through `burn`, which
        # is the same pair of calls a beat of the clock makes.
        self.buttons(*[
            button(conn_sim.AXES_BY_ID[a][1], lambda _=False, x=a: self.burn(x))
            for a in ("left", "forward", "right", "down", "back", "up")])
        self.buttons(
            button("Hold (coast)", lambda: self.burn(None), kind="flat"),
            button(f"Main drive: {'on' if self.use_main else 'off'}",
                   self._toggle_main, kind="flat"),
            button(f"Throttle: {self.conn.throttle:.0%}",
                   self._cycle_throttle, kind="flat"))

        board = Panel("The ship")
        for key, value, kind in panel_sim.readout(self.conn):
            board.add_row(key, value, kind)
        board.add_row("Clock", "running" if self.running else "held")
        # **What the last press did**, because three of the six thrust
        # buttons can look dead. The main drive only pushes along the nose, so
        # a press whose axis is not under it spends the whole tick swinging
        # the hull instead of burning — correct, documented in `sim/attitude`,
        # and until now completely silent. Flown through the buttons: with the
        # drive lit, Ahead moved her and Port, Starboard and Astern each moved
        # her nothing at all with no word said.
        if self.last.get("turning"):
            board.add_row("Drive", "swinging the hull round to bear — the "
                                   "torch did not fire", "warn")
        elif self.last.get("burned"):
            board.add_row("Drive", "fired", "")
        board.add_row("Autopilot", {
            "": "off — she flies as you fly her",
            "hold": "holding station, killing what drift there is",
            "run": f"running for {self.mark or 'nothing'}",
        }[self.auto])
        aim = self.marked()
        if aim is None:
            board.add_row("Course", "none laid — the six axes fly her frame")
        else:
            board.add_row(
                "Course",
                f"{aim.name}, {engage_sim.range_km(self.game, self.conn, aim):,.0f}"
                f" km, nose {free_sim.off_course(self.game, self.conn, aim):.0f}° off")
        self.col.addWidget(board)

        rows = self.ranged()
        near = Panel("In view")
        seen = [c for _km, c in rows][:6]
        for km, contact in rows[:6]:
            ok, _why = engage_sim.may_engage(self.game, self.conn, contact, km)
            marks = "  · on course" if contact.name == self.mark else ""
            near.add_row(contact.name,
                         f"{km:,.0f} km"
                         + ("  · may be engaged" if ok else "") + marks)
        if not seen:
            near.add(note("Nothing within reach of the cameras."))
        self.col.addWidget(near)

        # **Fly at it.** One button per thing in view, which is the whole
        # point of the screen: what you can see, you can go to. `steer` lays
        # the course; `conn.apply` swings the hull onto it and pays for the
        # swing in ticks and in mass, then the main drive closes the range.
        if seen:
            self.buttons(*[
                button(f"Fly at {c.name}", lambda _=False, k=c: self.fly_at(k),
                       kind="flat")
                for c in seen[:4]])

        # **The guns.** One door, `ui/fire_panel`, shared with any other screen
        # that grows a fire control — the board says what firing would mean at
        # the range the flying earned, and the button prints its refusal
        # instead of going grey.
        self.col.addWidget(fire_panel.board(self.game, self.conn, rows))
        guns = fire_panel.buttons(self.win, self.game, self.conn, rows)
        if guns:
            self.buttons(*guns)
        flags = fire_panel.marks(self.win, self.game, rows)
        if flags:
            self.buttons(*flags)

        aim = self.marked()
        self.buttons(
            button(("Stop holding station" if self.auto == "hold"
                    else "Hold station"),
                   lambda: self.set_auto("hold"), kind="flat"),
            *([button(("Stop running for it" if self.auto == "run"
                       else f"Run for {aim.name}"),
                      lambda: self.set_auto("run"), kind="flat")]
              if aim is not None else []))

        self.buttons(
            button("Stop clock" if self.running else "Run clock",
                   self._toggle, kind="primary"),
            button("Break off the course", self.break_off, kind="flat"),
            button("Secure from the conn", self.secure, kind="flat"),
            button("Take the conn on something…", self._to_conn, kind="flat"))

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
