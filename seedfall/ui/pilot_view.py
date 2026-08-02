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

from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import freeflight as free_sim
from ..sim import instruments as panel_sim
from ..sim import pilot as pilot_sim
from ..sim import track as track_sim
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
        # No axis: a coast. The pilot's burns come from the console;
        # a beat with nothing pressed is a minute of drifting, which is
        # what a live view mostly is.
        conn_sim.apply(self.conn, None, ticks=1)
        # **Pay as we go.** The same door `berthing.commit` settles through,
        # so neither can bill a minute the other already has.
        berth_sim.charge_flown(self.game, self.conn)
        if self.win.check_ending():
            self.set_running(False)
            return
        self.refresh()

    def burn(self, axis_id: str | None) -> dict:
        """Fire along an axis, or coast with `None`, and pay for the minute.

        The same two calls `tick` makes, in the same order, because a burn is
        a beat with the pilot's hand on it — not a second way for time to pass.
        """
        if self.conn is None or self.conn.landed:
            return {}
        # At the throttle and the coast the console is showing, which is the
        # call `ui/conn_window._burn` makes and the one `pilot.quote`
        # promises. Both read `conn`, so neither can promise what the other
        # will not do.
        said = conn_sim.apply(self.conn, axis_id, main=self.use_main,
                              ticks=self.conn.coast_min,
                              throttle=self.conn.throttle)
        berth_sim.charge_flown(self.game, self.conn)
        self.refresh()
        return said

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
        self.conn = None
        self.win.refresh()

    # ── what is out there ──────────────────────────────────────────────────

    def in_view(self) -> list:
        """Contacts worth naming, nearest first."""
        if self.conn is None:
            return []
        out = []
        for contact in track_sim.contacts(self.game):
            if contact.kind == "star":
                continue
            out.append((engage_sim.range_km(self.game, self.conn, contact),
                        contact))
        return [c for _km, c in sorted(out, key=lambda row: row[0])]

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
        self.col.addWidget(board)

        near = Panel("In view")
        for contact in self.in_view()[:6]:
            km = engage_sim.range_km(self.game, self.conn, contact)
            ok, _why = engage_sim.may_engage(self.game, self.conn, contact)
            near.add_row(contact.name,
                         f"{km:,.0f} km" + ("  · may be engaged" if ok else ""))
        if not self.in_view():
            near.add(note("Nothing within reach of the cameras."))
        self.col.addWidget(near)

        self.buttons(
            button("Stop clock" if self.running else "Run clock",
                   self._toggle, kind="primary"),
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
