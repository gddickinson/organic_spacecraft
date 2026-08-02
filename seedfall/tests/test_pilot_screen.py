"""The Pilot screen: the view from the bridge, with the clock running.

The Conn is for a situation — an approach, an orbit. This is the general case,
always available, never with a destination. What makes it different from every
other screen is that time passes while you look at it.

That is only safe because the clock is honest: `core/clock.MAX_STEP` is 1, so a
jump of N days is N jumps of one (#116), and billing in pieces is exactly
billing once. `sim/berthing.charge_flown` is the one door either way, so a
pilot who flies here and then secures does not pay twice for the same hour.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.screens import SCREENS
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import instruments as panel_sim
from .harness import Suite


#: The application and every window built here, held for the life of the
#: module.
#:
#: **Not a tidiness habit — the first draft was wrong without it.** `app` was a
#: local inside the builder below, so when it returned, the last Python
#: reference to the `QApplication` died, Qt tore down every widget it owned,
#: and the view that had just been built came back as "wrapped C/C++ object of
#: type PilotView has been deleted". The window is held for the same reason:
#: dropping it deletes the view it owns.
_LIVE: list = []


def _bridge(seed: str = "pilot"):
    """A window sitting on the Pilot screen, painted."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    from ..ui import theme
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    game = new_game(seed)
    win = MainWindow(game)
    _LIVE.extend([app, win])
    win.resize(1360, 880)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    win.toast = lambda *a, **k: None
    win.go("pilot")
    for _ in range(4):
        app.processEvents()
    return game, win, win.views["pilot"]


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── pilot screen ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

    @check("the Pilot is on the rail, and it paints with the ship in hand")
    def _():
        from PyQt6.QtWidgets import QPushButton
        ids = [sid for sid, _label, _key in SCREENS]
        assert "pilot" in ids, f"the rail offers {ids}"
        keys = [key for _sid, _label, key in SCREENS]
        assert len(set(keys)) == len(keys), f"two screens share a key: {keys}"

        game, _win, view = _bridge()
        assert view.conn is not None, "the Pilot screen opened with no conn"
        assert view.conn.target.kind == "open", (
            "the Pilot screen opened on a destination; it never has one")
        view.grab()
        labels = [b.text() for b in view.findChildren(QPushButton)]
        for camera in ("Fore", "Aft"):
            assert camera in labels, f"no {camera} camera: {labels}"
        assert any("clock" in t.lower() for t in labels), labels
        assert any("Secure" in t for t in labels), labels
        # **Six cameras and no hand on the stick** is what the first draft
        # was: the pilot could look anywhere and fly nowhere. Every axis
        # `conn.AXES` offers has a button, and the drive and throttle the
        # console has taken since it was written are reachable.
        for _aid, axis_label, _vec in conn_sim.AXES:
            assert axis_label in labels, f"no {axis_label!r} thrust: {labels}"
        assert any("Main drive" in t for t in labels), labels
        assert any("Throttle" in t for t in labels), labels
        assert any("coast" in t.lower() for t in labels), labels
        return (f"{len(labels)} controls: six cameras, "
                f"{len(conn_sim.AXES)} axes, drive and throttle")

    @check("the console and the ship panel agree about the throttle")
    def _():
        # **Found by rendering the screen and looking at it.** The button read
        # "THROTTLE: 50%" and the panel one row below it read "Throttle 100%",
        # because the view kept its own copy and passed it to `apply` as a
        # keyword while `instruments.readout` read `conn.throttle`, which
        # nothing had written. Same fact, two answers.
        from PyQt6.QtWidgets import QPushButton
        from ..sim import pilot as pilot_sim
        _game, _win, view = _bridge()
        seen = []
        for _ in range(len(pilot_sim.THROTTLE_STEPS)):
            view._cycle_throttle()
            labels = [b.text() for b in view.findChildren(QPushButton)]
            button_says = next(t for t in labels if t.startswith("Throttle"))
            panel_says = next(v for k, v, _kind
                              in panel_sim.readout(view.conn)
                              if k == "Throttle")
            shown = f"{view.conn.throttle:.0%}"
            assert shown in button_says, (button_says, shown)
            assert panel_says.startswith(shown), (
                f"the button says {button_says!r} and the panel says "
                f"{panel_says!r}")
            seen.append(view.conn.throttle)
        # **`set(seen) <= THROTTLE_STEPS` was worthless** and a mutation said
        # so: `set_throttle` snaps to the nearest rung, so a cycle over
        # nonsense values still lands on the ladder and the assertion cannot
        # fail. Every rung must be *reachable*, which is what a pilot needs
        # and what snapping cannot fake.
        assert set(seen) == set(pilot_sim.THROTTLE_STEPS), (
            f"cycling visits {sorted(seen)} of "
            f"{sorted(pilot_sim.THROTTLE_STEPS)}")

        # And the setting has to reach the burn. **A second mutation walked
        # straight through this check**: pinning `apply(throttle=1.0)` left
        # the button, the panel and the ladder all correct while every burn
        # went out at full power — a console that shows a tenth and fires the
        # lot. Reaction mass is the witness `sim/pilot.burn_cost` spends.
        spent = {}
        for rung in (min(seen), max(seen)):
            _g, _w, fresh = _bridge()
            pilot_sim.set_throttle(fresh.conn, rung)
            was = fresh.conn.rcs
            fresh.use_main = True
            for _ in range(10):
                fresh.burn("forward")
            spent[rung] = was - fresh.conn.rcs
        assert spent[min(seen)] < spent[max(seen)], (
            f"ten burns cost {spent[min(seen)]:,.4f} t at {min(seen):.0%} and "
            f"{spent[max(seen)]:,.4f} t at {max(seen):.0%} — the throttle the "
            f"console shows is not the throttle that fires")
        return ("console and panel agree at "
                + ", ".join(f"{v:.0%}" for v in seen)
                + f"; ten burns cost {spent[min(seen)]:,.4f} t at "
                f"{min(seen):.0%} against {spent[max(seen)]:,.4f} t at "
                f"{max(seen):.0%}")

    @check("a day at the bridge costs a day, and is billed exactly once")
    def _():
        # 1,440 beats is one ship day — `conn.TICK` is 60 s against
        # `DAY_SECONDS` of 86,400 — and the screen bills as it goes rather
        # than at the end, which for an honest clock is the same thing.
        game, _win, view = _bridge()
        was_day, was_credits = game.day, game.credits
        for _ in range(1440):
            view.tick()
        assert game.day == was_day + 1, (
            f"1,440 beats moved the chronicle {game.day - was_day} days")
        assert game.credits < was_credits, (
            "a day passed at the bridge and nobody was paid")
        assert abs(view.conn.elapsed - view.conn.charged) < 1e-6, (
            f"flew {view.conn.elapsed:,.0f} s and billed "
            f"{view.conn.charged:,.0f}")
        # Securing settles the flight and must not bill the day again.
        after = game.day
        view.secure()
        assert game.day == after, (
            f"securing re-billed time already paid for: day {after} -> "
            f"{game.day}")
        return (f"1,440 beats = 1 day, purse {was_credits:,.0f} -> "
                f"{game.credits:,.0f}, and securing adds nothing")

    @check("what the pilot can see is ranged, and says what may be fired on")
    def _():
        # The list is the same reading `sim/engage` makes, not a second one —
        # and there is something at a flyable distance to see, which is only
        # true since `traffic.STATION_KM` gave station-keeping hulls a place.
        game, _win, view = _bridge()
        seen = view.in_view()
        assert seen, "nothing at all is in view"
        ranges = [engage_sim.range_km(game, view.conn, c) for c in seen]
        assert ranges == sorted(ranges), "the view is not ordered by range"
        near = [c for c, km in zip(seen, ranges) if km < 50_000]
        assert near, f"nothing within 50,000 km: {[round(r) for r in ranges[:3]]}"
        hulls = [c for c in near if c.kind == "hull"]
        assert hulls, "no hull close enough to do anything about"
        for hull in hulls:
            ok, why = engage_sim.may_engage(game, view.conn, hull)
            assert ok, f"a hull in view cannot be engaged: {why}"
        worlds = [c for c in seen if c.kind == "body"]
        if worlds:
            ok, why = engage_sim.may_engage(game, view.conn, worlds[0])
            assert not ok and "world" in why, why
        return (f"{len(seen)} in view, nearest {min(ranges):,.0f} km; "
                f"{len(hulls)} hull(s) may be engaged")

    @check("a course laid on something in view actually closes the range")
    def _():
        # **The defect this exists for (#139).** Measured before it: a hull
        # 5,952 km off, main drive, full throttle, 500 burns on Ahead — the
        # range went to 22,695 km. You could see it and you could not go to
        # it, because "Ahead" was +y for every hull in every flight for ever:
        # `conn.apply` derives the drive's direction from the axis button
        # rotated by `Conn.heading`, and nothing had ever written the heading.
        from PyQt6.QtWidgets import QPushButton
        game, _win, view = _bridge("flighttest")

        labels = [b.text() for b in view.findChildren(QPushButton)]
        offered = [t for t in labels if t.startswith("Fly at ")]
        assert offered, f"nothing in view can be flown at: {labels}"

        target = next(c for c in view.in_view() if c.kind == "hull"
                      and 100 < engage_sim.range_km(game, view.conn, c) < 200_000)
        assert f"Fly at {target.name}" in offered, offered
        km0 = engage_sim.range_km(game, view.conn, target)

        was_heading = view.conn.heading
        view.fly_at(target)
        assert view.mark == target.name, view.mark
        assert view.conn.heading != was_heading, (
            "a course was laid and the heading did not move")

        view.use_main = True
        best, turning = km0, 0
        for _ in range(500):
            said = view.burn("forward")
            turning += bool(said.get("turning"))
            best = min(best, engage_sim.range_km(game, view.conn, target))
        assert best < km0 / 10.0, (
            f"flew at {target.name} from {km0:,.0f} km and got no closer than "
            f"{best:,.0f} km")
        # And the turn was paid for, in ticks — `sim/attitude` prices a hard
        # burn as turn, burn, turn again, and had never once been called.
        assert turning > 0, (
            "the hull came about without spending a single tick turning")
        return (f"{km0:,.0f} km -> {best:,.0f} km closest, "
                f"{turning} ticks spent coming about")

    @check("the course keeps pointing at a contact that has moved")
    def _():
        # A hull holding station rides its body round the star. A course laid
        # once and left alone stops pointing at it, so every beat lays it
        # again — which is what makes "Ahead" mean "at that" for a whole
        # flight rather than for the first minute.
        from ..sim import freeflight
        game, _win, view = _bridge("drift")
        target = next(c for c in view.in_view() if c.kind == "hull")
        view.fly_at(target)
        view.hold_course()
        # Laid, and the nose has somewhere to swing to. Not `or True`.
        assert freeflight.off_course(game, view.conn, target) >= 0.0
        laid = view.conn.heading
        # Move the chronicle on a season and let the sky turn under her.
        game.advance_days(90)
        moved = engage_sim.range_km(game, view.conn, view.marked())
        view.hold_course()
        assert view.conn.heading != laid, (
            f"ninety days passed, {target.name} moved to {moved:,.0f} km, and "
            f"the course never followed it")
        # Breaking off and securing both end the course.
        view.break_off()
        assert view.mark == "" and view.marked() is None
        view.fly_at(target)
        view.secure()
        assert view.mark == "", "securing left a course laid on nothing"
        return (f"course followed {target.name} across 90 days "
                f"({moved:,.0f} km off), and both exits clear it")

    @check("flying from the bridge moves the ship on every other screen")
    def _():
        # `flight.stand_off` is the one writer of where a hull is when it is
        # not alongside (#103). A flight that did not land there would be a
        # second position, which is the fault this project has been bitten by
        # more than any other.
        from ..sim import flight
        game, _win, view = _bridge()
        was = flight.ship_position(game)
        # **"fore" is a camera, not an axis.** The first draft burned along
        # `conn.VIEWS` ids and `thrust_axis` raised KeyError('fore') — which is
        # how the screen was found to have six cameras and no hand on the
        # stick at all. `conn.AXES` is forward/back/left/right/up/down.
        mass = view.conn.rcs
        for _ in range(120):
            view.burn("forward")
        flown = max(abs(v) for v in view.conn.pos)
        assert flown > 1.0, f"two hours of burning moved {flown:.3f} km"
        spent = mass - view.conn.rcs
        assert spent > 0.0, (
            f"burned {flown:,.0f} km on no reaction mass at all "
            f"({mass:,.3f} t still aboard)")
        view.secure()
        now = flight.ship_position(game)
        assert now != was, (
            f"burned {flown:,.0f} km and the sector chart still has her at "
            f"{was}")
        return (f"burned {flown:,.0f} km on {spent:,.3f} t, "
                f"and the chart followed")

    return True
