"""One flight deck: the armed state lives on the flight, every window reads it.

Two player reports, one cause, again. "The pilot window, flight control, conn
and gunnery systems were not properly integrated … contradictory displays in
the different viewers" and "the autopilot systems were disjointed and their
actions not always correctly displayed". The `Conn` object moved to the game a
cycle ago (#147) — but the *armed state* never moved with it: which autopilot
mode is flying, whether the main drive is selected, and whether the clock runs
were still private attributes of whichever window you happened to press, so
three windows could hold three different answers about one ship.

These checks pin the join: one field on the flight for each fact, one clock on
the main window, and the settling rule that no path may replace a live flight
without billing what it burned.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import anchorage as anchorage_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import freeflight as free_sim
from ..sim import track as track_sim
from .harness import Suite


#: Held at module scope: when the reference to the QApplication dies, Qt
#: tears down every widget it owns — the same lesson `test_pilot_screen`
#: records at its own top.
_APP = None


def _qt():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _APP
    _APP = QApplication.instance() or QApplication([])
    return _APP


def _moored(seed: str):
    game = new_game(seed)
    places = anchorage_sim.in_system(game)
    if not places:
        return None, None
    game.orbit_body = game.system.bodies[places[0].body_index].id
    return game, places[0]


def _window(game):
    from ..ui.window import MainWindow
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    win.dialog = lambda *a, **k: None
    return win


def run(suite: Suite) -> bool:
    check = suite.check

    @check("the flight window sees the game's flight, conn window or no")
    def _():
        _qt()
        from ..ui.flight_window import FlightWindow
        game = new_game("deck-a")
        win = _window(game)
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        win.conn = conn
        assert getattr(win, "conn_window", None) is None
        panel = FlightWindow(win)
        # It read `win.conn_window.conn` with a fallback nothing ever wrote,
        # so a flight taken on the Pilot screen showed here as "nothing in
        # reach" with every axis greyed.
        assert panel.conn is conn, (
            "the flight window is blind to a flight the game is holding")
        panel.close()
        return "a free flight on the game, read without the conn window open"

    @check("a hand-over from alongside does not open inside the structure")
    def _():
        # Measured before the floor: moored to the Fleet Hub, the bridge's
        # free flight sat at the hub's own position; opening the Conn window
        # handed it over with pos [0,0,0] — range 0.000 km — and the first
        # press logged "Struck Fleet Hub coming in".
        checked = 0
        for seed in range(8):
            game, quay = _moored(f"deck-b{seed}")
            if game is None:
                continue
            free, why = free_sim.begin(game)
            assert free is not None, why
            contact = next((c for c in track_sim.contacts(game)
                            if c.name == quay.name), None)
            if contact is None:
                continue
            handed, why = free_sim.hand_over(game, free, contact)
            if handed is None:
                continue
            floor = handed.target.radius_km + conn_sim.ALONGSIDE_KM
            assert handed.range_km > floor, (
                f"handed over {handed.range_km:.3f} km out on a structure "
                f"{handed.target.radius_km:.3f} km across — inside it")
            checked += 1
        assert checked >= 3, f"only {checked} hand-overs measured"
        return f"{checked} moored hand-overs, all opening clear of the skin"

    @check("retargeting the conn bills the flight it abandons")
    def _():
        # `_pick_target` and `_free_flight` used to replace `game.conn`
        # after a `_settle()` that returns early for a live approach — so
        # the mass already burned went back into the tank.
        _qt()
        from ..ui.conn_window import ConnWindow
        game, quay = _moored("deck-c")
        assert game is not None
        win = _window(game)
        window = ConnWindow(win)
        assert win.conn is not None
        held = float(game.ship.cargo.get("volatiles", 0.0))
        for _ in range(4):
            window._burn("forward")
        burned = held - float(game.ship.cargo.get("volatiles", 0.0))
        assert burned > 0, "four burns billed nothing"
        window._free_flight()
        now = float(game.ship.cargo.get("volatiles", 0.0))
        assert held - now >= burned - 1e-6, (
            f"burned {burned:.3f} t and the tank shows {held - now:.3f} "
            "gone — the abandoned approach was refunded")
        # And the fresh flight opens on the billed tank, not the old one.
        assert win.conn.opening_rcs <= now + 1e-6, (
            f"fresh conn opened on {win.conn.opening_rcs:.3f} t against "
            f"{now:.3f} in the hold")
        win.set_conn_clock(False)
        window.close()
        return f"{burned:.3f} t burned, still gone after Fly free"

    @check("one clock: every window's run button drives the same beat")
    def _():
        _qt()
        from ..ui.flight_window import FlightWindow
        game = new_game("deck-d")
        win = _window(game)
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        win.conn = conn
        pilot = win.views["pilot"]
        panel = FlightWindow(win)
        pilot.set_running(True)
        assert conn.clock_on, "the pilot's clock is not the flight's clock"
        panel.refresh()
        assert "Stop" in panel.run_btn.text(), panel.run_btn.text()
        panel._toggle_clock()
        assert not conn.clock_on, "stopping from the panel did not stop it"
        assert not pilot.running, "the bridge still thinks time is passing"
        panel.close()
        return "armed on the bridge, read and stopped from the flight panel"

    @check("one beat is one minute, however many windows watch")
    def _():
        _qt()
        from ..ui.flight_window import FlightWindow
        from ..ui.conn_window import ConnWindow
        game = new_game("deck-e")
        win = _window(game)
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        win.conn = conn
        panel = FlightWindow(win)
        window = ConnWindow(win)
        live = win.conn                      # the window may have handed over
        was = live.elapsed
        win.fly_beat()
        assert live.elapsed - was == conn_sim.TICK, (
            f"one beat advanced {live.elapsed - was:.0f}s — "
            "two timers are flying one ship")
        win.set_conn_clock(False)
        panel.close()
        window.close()
        return "three windows open, one beat, sixty seconds"

    @check("the armed mode is the flight's, and the panel reports it")
    def _():
        _qt()
        from ..ui.conn_window import ConnWindow
        from ..sim import instruments as panel_sim
        game, quay = _moored("deck-f")
        assert game is not None
        win = _window(game)
        window = ConnWindow(win)
        conn = win.conn
        assert conn is not None
        window._auto("close")
        assert conn.auto == "close", "arming did not reach the flight"
        rows = {name: value for name, value, _k in panel_sim.readout(conn)}
        assert "Computer" in rows, "the panel does not say who has the conn"
        assert "closing" in rows["Computer"], rows["Computer"]
        window._auto("close")           # pressing the lit mode disarms
        assert conn.auto == "", conn.auto
        win.set_conn_clock(False)
        window.close()
        return f"armed close; the panel read {rows['Computer']!r}"

    @check("reaction mass is billed as it burns, and exactly (#148, #149)")
    def _():
        game = new_game("deck-g")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        held = float(game.ship.cargo.get("volatiles", 0.0))
        for _ in range(7):
            conn_sim.apply(conn, "forward", ticks=1)
        berth_sim.charge_flown(game, conn)
        mid = float(game.ship.cargo.get("volatiles", 0.0))
        assert held - mid > 0, "seven burns billed nothing before commit"
        berth_sim.commit(game, conn)
        after = float(game.ship.cargo.get("volatiles", 0.0))
        assert abs((held - after) - berth_sim.spent(conn)) < 1e-9, (
            f"spent {berth_sim.spent(conn):.4f} t, billed {held - after:.4f}"
            " — securing rounds the bill")
        return (f"{berth_sim.spent(conn):.4f} t spent, {held - mid:.4f} "
                f"billed in flight, remainder at commit, exact")

    @check("a transfer settles the flight instead of teleporting under it")
    def _():
        game = new_game("deck-h")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        game.conn = conn
        for _ in range(5):
            conn_sim.apply(conn, "forward", ticks=1)
        from ..sim import flight as flight_sim
        target = next(i for i, b in enumerate(game.system.bodies)
                      if b.id != game.orbit_body)
        out = flight_sim.travel_to(game, target, "coast")
        assert out.get("ok"), out
        assert game.conn is None, (
            "the transfer left a live conn to re-apply its old offset on "
            "top of the new position")
        return "flew a leg mid-flight; the conn was secured and billed first"

    @check("a structure's patience runs on the tick, not the substep")
    def _():
        # Near a body `conn_step._substeps` cuts a minute into up to 120
        # slices, and the approach-control ladder used to climb once per
        # slice: point defence bit 120x harder at a world than at a quay.
        from ..sim import control as control_sim
        game = new_game("deck-i")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        told = []
        real = control_sim.step

        def counting(c, closing):
            told.append(1)
            return real(c, closing)

        control_sim.step = counting
        try:
            conn.vel = [0.0, 40.0, 0.0]
            conn_sim.apply(conn, None, ticks=1)
        finally:
            control_sim.step = real
        assert len(told) == 1, (
            f"the ladder ran {len(told)} times in one tick")
        return "one tick, one rung of patience"

    @check("the descent order is a button, and it can be belayed")
    def _():
        # `sim/landing.py` decides down vs ditched vs aground, and the order
        # that makes "ditched" possible was reachable only from a check —
        # no screen offered it.
        _qt()
        from ..ui.conn_window import ConnWindow
        game = new_game("deck-j")
        game.orbit_body = game.system.bodies[1].id
        body = next(c for c in track_sim.contacts(game)
                    if c.kind == "body"
                    and berth_sim.can_conn(game, c)[0])
        win = _window(game)
        window = ConnWindow(win, body)
        conn = win.conn
        assert conn is not None and conn.target.kind == "body"
        btn = window.controls.ditch_btn
        assert btn.isVisibleTo(window), "no descent order on a world"
        window.controls._ditch()
        assert conn.ditching, "the order did not reach the flight"
        assert "Belay" in btn.text(), btn.text()
        window.controls._ditch()
        assert not conn.ditching, "the order cannot be taken back"
        window.close()
        return "ordered, said out loud, and belayed"

    return True
