"""Flying the operations: every goal the computer and the hand can fly.

`test_flightdeck.py` holds the *authority* checks — one armed state, one
clock, one bill, one dispatcher. This holds the *operations*: taking the
conn on a world, moving away from one, ordering a descent, and the heads-up
aids that say what the flying is doing. They were one file until it went
past five hundred lines, and the seam was already there.

Every one of these was written from a defect found by flying the game
rather than by reading it.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import anchorage as anchorage_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import freeflight as free_sim
from ..sim import track as track_sim
from .harness import Suite

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


#: Every window a hand can fly or fight from, and how it opens. `test_verbs`
#: presses every control on the thirteen *standing* screens and has never
#: touched one of these — which is exactly where the flying lives.
POPOUTS = (("conn", "..ui.conn_window", "open_conn"),
           ("flight", "..ui.flight_window", "open_flight"),
           ("approach", "..ui.approach_window", "open_approach"),
           ("plotting board", "..ui.plot3d_window", "open_plot"),
           ("tactical", "..ui.tactical_window", "open_tactical"),
           ("gunnery", "..ui.gunner_window", "open_gunnery"))

#: Presses that end the session rather than testing it.
AVOID = ("close", "quit", "abandon", "begin again")


def _flight_for(game, state: str):
    """A flight in the state named, or None if this sector cannot show it."""
    from ..sim import berthing as berth
    if state == "none":
        return None
    if state == "free":
        return free_sim.begin(game)[0]
    want = {"quay": "anchorage", "body": "body", "hull": "hull"}[state]
    got = next((c for c in track_sim.contacts(game)
                if c.kind == want and berth.can_conn(game, c)[0]), None)
    return berth.begin(game, got)[0] if got is not None else None


def run(suite: Suite) -> bool:
    check = suite.check

    @check("every control in every flying window runs, in every state")
    def _():
        # The gap this closes: `test_verbs` clicks all 173 controls on the
        # standing screens and **no pop-out window has ever been swept** —
        # the conn, the flight panel, the approach view, the plotting board,
        # the tactical station and the gunner's seat. Each is opened on a
        # flight of every kind (none, free, quay, body, hull), every enabled
        # control pressed, then a beat and a redraw on whatever the presses
        # left behind.
        app = _qt()
        from PyQt6.QtWidgets import QPushButton
        import importlib
        pressed = swept = 0
        for state in ("none", "free", "quay", "body", "hull"):
            for label, mod, opener in POPOUTS:
                game = new_game(f"ops-{state}-{label}")
                places = anchorage_sim.in_system(game)
                if places:
                    game.orbit_body = \
                        game.system.bodies[places[0].body_index].id
                win = _window(game)
                flight = _flight_for(game, state)
                if flight is None and state != "none":
                    continue
                win.conn = flight
                module = importlib.import_module(mod, package=__package__)
                window = getattr(module, opener)(win)
                for btn in list(window.findChildren(QPushButton)):
                    if (not btn.isEnabled() or btn.parent() is None
                            or not (btn.text() or "").strip()):
                        continue
                    if any(a in btn.text().lower() for a in AVOID):
                        continue
                    btn.click()
                    app.processEvents()
                    pressed += 1
                win.fly_beat()
                window.refresh()
                swept += 1
                # **Every window this sweep opened is closed**, including the
                # ones a control opened behind it. A pop-out outliving its
                # window is Qt destroying a widget mid-paint, and it kills
                # the process rather than failing a check.
                for name in ("conn_window", "flight_window", "approach_window",
                             "plot_window", "tactical_window",
                             "gunner_window"):
                    other = getattr(win, name, None)
                    if other is not None:
                        other.close()
                win.set_conn_clock(False)
        assert swept >= 24, f"only {swept} window-states swept"
        return (f"{pressed} controls pressed across {swept} window-states, "
                "each followed by a beat and a redraw")

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

    @check("the window shows the path, the way she is going, and the way in")
    def _():
        # The heads-up aids — `ui/viewport_hud.points`, the computing half
        # of what every camera draws, asked directly so no pixel-reading is
        # needed. A moving approach shows a predicted path, a prograde mark
        # and the aim point; a bay shows the ring of its mouth.
        _qt()
        from ..ui import viewport_hud
        from ..ui.viewport import basis
        game, quay = _moored("deck-k")
        assert game is not None
        contact = next(c for c in track_sim.contacts(game)
                       if c.name == quay.name)
        conn, why = berth_sim.begin(game, contact)
        assert conn is not None, why
        conn.vel = [0.0, 4.0, 0.0]
        cam = basis((0.0, 1.0, 0.0), conn)
        got = viewport_hud.points(conn, cam, 464, 320)
        assert len(got["path"]) >= 4, "no predicted path in the window"
        assert got["prograde"] is not None, "no prograde mark"
        assert got["aim"] is not None, "the aim point is not shown"
        from .test_bay import _at
        game2, target = _at("arca_drum", seed="deck-k2")
        conn2 = conn_sim.start(game2, target)
        cam2 = basis((0.0, 1.0, 0.0), conn2)
        ring = viewport_hud.points(conn2, cam2, 464, 320)["mouth"]
        assert len(ring) >= 6, f"the way in drew {len(ring)} points"
        return (f"{len(got['path'])} path dots, prograde, aim, and a "
                f"{len(ring)}-point mouth on a drum")

    @check("the same computer moves her away, and hands back when clear")
    def _():
        # "Depart" is a verb of the one flight computer — leaving used to be
        # manual or a transfer, the one operation with no mode.
        _qt()
        game, quay = _moored("deck-l")
        assert game is not None
        win = _window(game)
        contact = next(c for c in track_sim.contacts(game)
                       if c.name == quay.name)
        conn, why = berth_sim.begin(game, contact)
        assert conn is not None, why
        win.conn = conn
        from ..ui import flight_clock
        flight_clock.arm_mode(win, "depart")
        assert conn.auto == "depart" and conn.clock_on
        opened = conn.range_km
        for _ in range(600):
            if conn.auto != "depart":
                break
            win.fly_beat()
        assert conn.auto == "", "the computer never handed back"
        assert conn.range_km > opened, (
            f"never moved away: {opened:.1f} -> {conn.range_km:.1f} km")
        assert conn.speed < 1.0, f"handed back still moving {conn.speed:.1f}"
        return (f"{opened:.1f} -> {conn.range_km:.1f} km, stopped, "
                "conn handed back")

    @check("the autopilot bar is on every flying screen, with one Manual")
    def _():
        _qt()
        from PyQt6.QtWidgets import QPushButton
        from ..ui.approach_window import ApproachWindow
        from ..ui.flight_window import FlightWindow
        game, quay = _moored("deck-m")
        assert game is not None
        win = _window(game)
        contact = next(c for c in track_sim.contacts(game)
                       if c.name == quay.name)
        conn, why = berth_sim.begin(game, contact)
        win.conn = conn
        win.go("pilot")
        win.go("helm")
        surfaces = {"pilot": win.views["pilot"], "helm": win.views["helm"],
                    "flight": FlightWindow(win), "approach":
                    ApproachWindow(win)}
        for name, widget in surfaces.items():
            names = {b.objectName() for b in
                     widget.findChildren(QPushButton)}
            assert "auto_off" in names, f"{name} has no Manual"
            assert "auto_close" in names, f"{name} cannot arm close"
        surfaces["flight"].close()
        surfaces["approach"].close()
        return f"{len(surfaces)} surfaces, each with the bar and a Manual"

    @check("taking the conn on a world you are orbiting is a flight")
    def _():
        # **Measured: 8 of 11 body approaches opened already finished.**
        # `outcome.resolve` wrote "orbit" on the first tick because the hull
        # was parked in one, so the pad was dead, every mode was dead, and
        # there was no way to change height, descend or depart. An outcome
        # is what a flight achieves, not the state it began in.
        flyable = 0
        for seed in range(9):
            game = new_game(f"deck-n{seed}")
            places = anchorage_sim.in_system(game)
            if places:
                game.orbit_body = game.system.bodies[places[0].body_index].id
            body = next((c for c in track_sim.contacts(game)
                         if c.kind == "body"
                         and berth_sim.can_conn(game, c)[0]), None)
            if body is None:
                continue
            conn, why = berth_sim.begin(game, body)
            if conn is None:
                continue
            conn_sim.apply(conn, None, ticks=1)
            assert not conn.over, (
                f"seed {seed}: the conn opened finished ({conn.outcome!r})")
            flyable += 1
        assert flyable >= 6, f"only {flyable} body conns measured"
        # And flying *into* orbit still ends the approach, as it always did.
        game = new_game("deck-n-into")
        body = next(c for c in track_sim.contacts(game)
                    if c.kind == "body" and berth_sim.can_conn(game, c)[0])
        conn, _why = berth_sim.begin(game, body)
        conn.opened_orbiting = False        # arrived from outside
        conn.rcs = 999
        from ..sim import autopilot as auto_sim
        assert auto_sim.fly(conn, "orbit", 6000).outcome == "orbit", (
            "flying into orbit no longer resolves")
        return f"{flyable} body conns flyable; a flown orbit still resolves"

    @check("moving away from a world climbs, and never flies into it")
    def _():
        # The first draft demanded a *radial* velocity, which in a gravity
        # well asks the drive to cancel the whole orbit — measured at a
        # world, 2,779 m/s of it — so the hull decayed and went **aground**.
        from ..sim import flightdeck as deck_sim
        from ..sim import orbits
        grounded = flown = refused = 0
        for seed in range(6):
            game = new_game(f"deck-o{seed}")
            places = anchorage_sim.in_system(game)
            if places:
                game.orbit_body = game.system.bodies[places[0].body_index].id
            body = next((c for c in track_sim.contacts(game)
                         if c.kind == "body"
                         and berth_sim.can_conn(game, c)[0]), None)
            if body is None:
                continue
            conn, _why = berth_sim.begin(game, body)
            if conn is None:
                continue
            game.conn = conn
            ok, why = deck_sim.can_arm(game, conn, "depart")
            if not ok:
                assert why, "refused a departure without saying why"
                refused += 1
                continue
            conn.auto = "depart"
            for _ in range(9000):
                axis, main, thr = deck_sim.computer(game, conn)
                conn_sim.apply(conn, axis, main=main, throttle=thr)
                if conn.over or conn.auto != "depart":
                    break
            if conn.outcome == "aground":
                grounded += 1
            else:
                flown += 1
        assert grounded == 0, f"{grounded} departures flew into the world"
        assert refused + flown >= 4, "nothing was measured"
        return (f"{flown} departures flown, {refused} refused with a reason, "
                f"none aground")

    @check("a hand taken off the stick by anything stops the burn")
    def _():
        # Qt sends no `released` to a widget that no longer exists, so a
        # rebuild mid-hold — or walking off the screen with a key down —
        # left a standing order and *the ship burned with nobody holding
        # it*. Every door that can take the control away closes the order.
        _qt()
        from PyQt6.QtCore import QEvent, Qt
        from PyQt6.QtGui import QKeyEvent
        from ..ui import flight_clock
        game = new_game("deck-p")
        win = _window(game)
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        win.conn = conn
        win.go("pilot")
        pilot = win.views["pilot"]
        win.set_conn_clock(True)
        flight_clock.start_burn(win, "forward")
        win.fly_beat()
        pilot._shape = None                 # force a full rebuild
        pilot.refresh()
        assert win.burn_order is None, (
            "a rebuild orphaned the burn: nobody is holding it and it fires")
        # and a key held while the captain walks away
        win.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_W,
                                    Qt.KeyboardModifier.NoModifier))
        assert win.burn_order == "forward"
        win.go("helm")
        assert win.burn_order is None, "leaving the bridge left a key burning"
        return "a rebuild and a screen change both close a standing order"


    return True
