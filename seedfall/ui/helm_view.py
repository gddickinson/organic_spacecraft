"""The helm — plotting a transfer inside a system.

A jump drops you at the system edge. Everything worth looking at is somewhere
else and moving, so getting alongside it is a decision: how much reaction mass
are you willing to spend to save how many days.

The chart itself lives in `ui/orbit_chart.py`. It moved out when this file went
past five hundred lines carrying both the plot and the screen around it.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..core.util import duration
from ..data.starclasses import mu_of
from ..sim import anchorage as anchorage_sim
from ..sim import flight
from ..sim import transit as transit_sim
from ..world.planets import BODY_KINDS
from .orbit_chart import OrbitChart
from .widgets import (Panel, Pill, TabBar, View, button, label, mono_label,
                      note, spacer)


class HelmView(View):
    def __init__(self, win):
        super().__init__(win)
        self.target = 0
        #: The quay the captain picked, if any. Held on the view rather than
        #: the chart because the chart is rebuilt on every refresh.
        self.place = None
        self.burn = "standard"

    def build(self) -> None:
        g = self.game
        here = flight.current_body(g)
        # `where_am_i` rather than the body name: a captain could not tell
        # they had launched from a fleet hub except by opening the shipyard
        # window, which is not an answer to "where am I".
        self.head(f"Helm — {g.system.name}", anchorage_sim.where_am_i(g))

        if self.target >= len(g.system.bodies):
            self.target = 0

        chart = OrbitChart(self.win)
        chart.target = self.target
        chart.place = self.place
        chart.burn = self.burn
        chart.picked.connect(self._pick)
        self.chart = chart
        # Chart and the places you can put in share the left column: three
        # columns fits a wide desktop and silently drops the third one at any
        # ordinary window size, which is how it was first written.
        left = QWidget()
        stack = QVBoxLayout(left)
        stack.setContentsMargins(0, 0, 0, 0)
        stack.setSpacing(10)
        stack.addWidget(chart, 1)
        stack.addWidget(self._where(g))
        stack.addWidget(self._who(g))
        self.row(left, self._plot(g))
        self.buttons(
            button("System overview", lambda: self.win.go("system")),
            button("Sector chart", lambda: self.win.go("map")),
            button("Plotting board…", self._plotting_board),
            button("Take the conn…", self._take_conn),
            button("Tactical…", self._tactical),
            button("Flight controls…", self._flying))
        # **The one clock, from this screen too.** The flight keeps running
        # while the captain reads the burn board — walking here no longer
        # stops it — so the helm carries the same Run/Stop and time-scale
        # controls as the bridge, reading `Conn.clock_on` like everything.
        # `beat_sync` keeps their labels honest without a rebuild eating the
        # button under the finger (#150).
        conn = self.win.conn
        self._clock_btn = None      # a rebuild with no flight must not leave
        if conn is not None and not conn.landed:    # a stale widget behind
            self._clock_btn = button(
                "Stop clock" if conn.clock_on else "Run clock",
                self._toggle_clock, kind="primary")
            self._scale_btn = button(
                f"Time ×{int(getattr(self.win, 'time_scale', 1))}",
                self._cycle_scale, kind="flat")
            quay = self._dockable(g)
            self.buttons(self._clock_btn, self._scale_btn,
                         *([button(f"Dock at {quay.name} — computer",
                                   lambda _=False, c=quay: self._dock(c),
                                   kind="flat",
                                   tip="Open the conn on the quay and hand "
                                       "it to the flight computer.")]
                           if quay is not None else []))

    def beat_sync(self) -> None:
        """What a beat changes on this screen: the two clock labels."""
        conn = self.win.conn
        if conn is None or getattr(self, "_clock_btn", None) is None:
            return
        self._clock_btn.setText("Stop clock" if conn.clock_on
                                else "Run clock")
        self._scale_btn.setText(
            f"Time ×{int(getattr(self.win, 'time_scale', 1))}")

    def _toggle_clock(self) -> None:
        conn = self.win.conn
        self.win.set_conn_clock(not (conn is not None and conn.clock_on))
        self.beat_sync()

    def _cycle_scale(self) -> None:
        from . import flight_clock
        flight_clock.cycle_scale(self.win)
        self.beat_sync()

    def _dockable(self, g):
        """The quay the computer could take her into from here, if any."""
        from ..sim import berthing as berth_sim
        from ..sim import track as track_sim
        for c in track_sim.contacts(g):
            if c.kind == "anchorage" and berth_sim.can_conn(g, c)[0]:
                return c
        return None

    def _dock(self, contact) -> None:
        """One button: the conn on the quay, the computer on the conn."""
        from .conn_window import open_conn
        window = open_conn(self.win, contact)
        window._auto("close")

    def _plotting_board(self) -> None:
        """The system in its own window, with time and a zoom on it."""
        from .plot3d_window import open_plot
        open_plot(self.win)

    def _take_conn(self) -> None:
        """Fly by hand, at the range where a metre a second matters."""
        from .conn_window import open_conn
        open_conn(self.win)

    def _tactical(self) -> None:
        """What a fight here would be, before there is one."""
        from .tactical_window import open_tactical
        open_tactical(self.win)

    def _flying(self) -> None:
        """Fly the approach by hand, on the instruments."""
        from .flight_window import open_flight
        open_flight(self.win)

    def _pick(self, index: int) -> None:
        # The chart decides whether a quay or a bare body was hit; the view
        # only has to remember which.
        #
        # From the *sender*, not from `self.chart`: `refresh()` builds a new
        # chart every time, so reading the attribute off the view's current
        # one gave the answer from a widget that had not been clicked. It
        # only ever showed up once a system held two berths — which it did
        # the day Weave anchors got a place of their own.
        chart = self.sender() or getattr(self, "chart", None)
        self.place = getattr(chart, "place", None)
        self.target = index
        self.refresh()

    def course_to(self, body_index: int) -> None:
        """Aim at a body by index.

        A quay's position *is* its body's position, so setting course for one
        is setting course for the other — no special case anywhere in flight.
        """
        self.place = None
        self.target = body_index
        self.refresh()

    def fly_to_place(self, place) -> None:
        """Take the ship to a quay. What its `Set course` button does.

        It used to call `course_to`, which only *aimed* the helm — and a
        quay's body is very often the body already targeted, so the button
        set what was already set and a captain clicking "Set course — 4 d,
        2 t" on the Fleet Hub saw nothing happen at all. The label quotes
        days and tonnes and the tooltip says "Fly to"; so it flies.
        """
        self.place = place.id
        self.target = place.body_index
        res = transit_sim.begin(self.game, self.target, self.burn)
        if not res.get("ok"):
            self.win.toast(res.get("why", "That course cannot be flown."),
                           "warn")
            self.refresh()
            return
        self.win.transit = res["transit"]
        self.win.go("transit")

    def _who(self, g):
        from .traffic_panel import who_else
        return who_else(self, g)

    def _where(self, g):
        from .anchorage_panel import where_to_put_in
        return where_to_put_in(self, g)

    def _plot(self, g) -> Panel:
        body = g.system.bodies[self.target]
        at = body.id == g.orbit_body
        picked = next((a for a in anchorage_sim.in_system(g)
                       if a.id == self.place), None)
        p = Panel(f"Transfer to {picked.name}" if picked is not None
                  else f"Transfer to {body.name}")
        if picked is not None:
            p.add(note(f"In orbit of {body.name}. Flying to the one is "
                       "flying to the other."))
        p.add(note(BODY_KINDS[body.kind][0] + " · "
                   + f"{flight.orbit_radius(body):.1f} AU orbit · "
                   + f"period {duration(flight.period_days(body, mu_of(g.system)))}"))
        p.add_row("Range now", f"{flight.distance_to(g, body):.2f} AU")
        p.add_row("Reaction mass aboard",
                  f"{round(g.ship.cargo.get('volatiles', 0))} t")
        cap = g.ship_stats.heat_cap
        p.add_row("Hull heat", f"{round(g.ship.heat)} / {round(cap)}",
                  "warn" if g.ship.heat > cap else
                  ("osteo" if g.ship.heat > cap * 0.5 else ""))

        if at:
            p.add(spacer(4))
            p.add(Pill("alongside", "chloro"))
            p.add(note("You are already there. Survey, extract, dig or land from "
                       "the system screen."))
            return p

        q = flight.intercept(g, body, self.burn)
        p.add_row("Aim point", f"{q['au']:.2f} AU ahead of the mark")
        p.add_row("Target moves", f"{q['lead']:.2f} AU while you are under way")
        p.add_row("Arrives", f"day {q['arrival_day']} · {duration(q['days'])}")
        hazard = flight.path_note(g, body, self.burn)
        if hazard:
            p.add(note(hazard))

        p.add(spacer(4), mono_label("Plot"))
        tabs = TabBar([(b.id, b.name) for b in flight.BURNS], self.burn)
        tabs.changed.connect(self._plot_burn)
        p.add(tabs)

        # What the crossing is actually made of. The lump the helm quotes is
        # a turn, a burn, a long coast, a flip and a braking burn — and the
        # turns take the time *this* hull's attitude clusters need.
        from ..sim import burnplan
        p.add(spacer(4), mono_label("The crossing"))
        p.add(note(burnplan.note(g, body, self.burn)))
        for phase, when, detail in burnplan.rows(g, body, self.burn):
            p.add_row(f"{phase} · {when}", detail)

        p.add(spacer(4), mono_label("Burn profiles"))
        for q in flight.options(g, body):
            burn = q["burn"]
            afford = g.ship.cargo.get("volatiles", 0) >= q["fuel"]
            p.add(spacer(3))
            p.add(label(burn.name, "h3", "chloro" if afford else "dim"))
            p.add(note(burn.blurb))
            p.add_row(f"{q['days']} days · {q['fuel']:g} t",
                      f"risk {q['risk']:.0%}",
                      "warn" if q["risk"] > 0.15 else "")
            arriving = g.ship.heat + flight.burn_heat(burn, g.ship_stats)
            if burn.heat:
                p.add_row("Arrives at",
                          f"{round(arriving)} / {round(g.ship_stats.heat_cap)} heat",
                          "warn" if arriving > g.ship_stats.heat_cap else "")
            p.add_buttons(button(f"Burn — {q['days']} d",
                                 lambda _=False, bid=burn.id: self._burn(bid),
                                 kind="primary" if burn.id == "standard" else "",
                                 enabled=afford))
        p.add(spacer(4))
        p.add(note("Bodies move while you fly, so the helm aims at where the "
                   "target will be, not where it is. The crosshair on the chart "
                   "is the aim point; the amber arc is the ground it covers "
                   "while you are under way."))
        p.add(note("A hard burn arrives hot, and a hot hull is a worse thing to "
                   "burn again in. Over the cap the radiators stop keeping up "
                   "and the hull cooks. Sitting still sheds it."))
        return p

    def _plot_burn(self, burn_id: str) -> None:
        self.burn = burn_id
        self.refresh()

    def _burn(self, burn_id: str) -> None:
        # Committing to a burn puts you in the pilot's seat for the crossing
        # rather than skipping to the far end of it.
        res = transit_sim.begin(self.game, self.target, burn_id)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.transit = res["transit"]
        self.win.go("transit")
