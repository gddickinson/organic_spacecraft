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

    @check("the computer can be given the conn, and hands it back on arrival")
    def _():
        # The request: "Toggle auto-pilot and watch the view … then engage
        # the auto-pilot to come alongside the asteroid." The screen decides
        # only *whether* the computer has the conn; what flying is stays in
        # `sim/autopilot` and `sim/freeflight.run_for`.
        from PyQt6.QtWidgets import QPushButton
        from ..sim import freeflight
        game, _win, view = _bridge("auto")

        labels = [b.text() for b in view.findChildren(QPushButton)]
        assert any("Hold station" in t for t in labels), labels
        assert not any(t.startswith("Run for") for t in labels), (
            "offered to run for something with no course laid")

        hull = next(c for c in view.in_view() if c.kind == "hull"
                    and 100 < engage_sim.range_km(game, view.conn, c) < 200_000)
        view.fly_at(hull)
        labels = [b.text() for b in view.findChildren(QPushButton)]
        assert f"Run for {hull.name}" in labels, labels

        km0 = engage_sim.range_km(game, view.conn, hull)
        view.set_auto("run")
        assert view.auto == "run"
        beats = None
        for beat in range(2500):
            view.tick()
            if view.auto != "run":
                beats = beat + 1
                break
        assert beats, (
            f"ran for {beats} beats and is still "
            f"{engage_sim.range_km(game, view.conn, hull):,.0f} km off")
        km = engage_sim.range_km(game, view.conn, hull)
        assert km <= freeflight.ALONGSIDE_KM + 1.0, f"{km:,.0f} km off"
        # Handed back, and said so — a computer that stops without a word
        # leaves the pilot watching a still picture wondering.
        assert view.auto == "hold", view.auto
        assert any("Alongside" in str(row) for row in game.log[-4:]), (
            "arrived without a word in the log")
        return (f"{km0:,.0f} km -> {km:,.0f} km in {beats} beats "
                f"({beats / 60:.1f} h), then holding station")

    @check("letting go of the course or the conn stops the computer too")
    def _():
        # A computer left running for a mark that is no longer laid would
        # burn on toward wherever the pilot last looked.
        game, _win, view = _bridge("auto")
        hull = next(c for c in view.in_view() if c.kind == "hull")
        view.fly_at(hull)
        view.set_auto("run")
        view.break_off()
        assert view.auto == "" and view.mark == "", (view.auto, view.mark)

        view.fly_at(hull)
        view.set_auto("run")
        view.secure()
        assert view.auto == "" and view.mark == "", (view.auto, view.mark)

        # Holding station survives breaking off, because it is about the ship
        # and not about the mark.
        game, _win, view = _bridge("auto")
        view.set_auto("hold")
        view.break_off()
        assert view.auto == "hold", view.auto
        # And the toggle is a toggle.
        view.set_auto("hold")
        assert view.auto == "", view.auto
        return "both exits clear a run; holding station is not a course"

    @check("a press that only swings the hull says so, instead of looking dead")
    def _():
        # **Found by flying the screen through its own buttons.** With the
        # main drive lit, three of the six thrust buttons moved the ship
        # nowhere: the torch only pushes along the nose, so a press whose axis
        # is not under it spends the whole tick turning. That is right, and
        # `sim/attitude` documents it — but the screen said nothing at all, so
        # a pilot pressing Port got a dead button and no reason.
        from PyQt6.QtWidgets import QLabel
        game, _win, view = _bridge("flygui")
        view.use_main = True

        # Ahead is under the nose to begin with: it fires.
        was = list(view.conn.pos)
        view.burn("forward")
        assert view.last.get("burned"), view.last
        assert not view.last.get("turning"), view.last
        assert view.conn.pos != was, "the drive fired and she did not move"
        said = [l.text() for l in view.findChildren(QLabel)]
        assert "fired" in said, "a burn that fired said nothing"

        # Port is not: the tick goes into the swing, and the panel says so.
        # **The velocity, not the position.** A turning tick still lets the
        # minute pass, so a ship already moving keeps coasting through it —
        # asserting `pos` was unchanged failed for that reason, and the claim
        # worth making is that the swing bought no *speed*.
        was = list(view.conn.vel)
        view.burn("left")
        assert view.last.get("turning"), (
            f"the fixture no longer turns for an off-axis press: {view.last}")
        assert not view.last.get("burned"), view.last
        assert view.conn.vel == was, (
            f"a tick spent turning still changed the velocity: {was} -> "
            f"{view.conn.vel}")
        said = [l.text() for l in view.findChildren(QLabel)]
        swung = [t for t in said if "swinging" in t]
        assert swung, (
            "a press spent the whole tick turning and the panel said nothing "
            "— which is a dead button as far as the pilot can tell")
        assert "did not fire" in swung[0], swung[0]

        # On the clusters there is nothing to swing: every axis fires.
        view.use_main = False
        for axis in ("forward", "left", "up"):
            was = list(view.conn.vel)
            view.burn(axis)
            assert view.last.get("burned"), (axis, view.last)
            assert view.conn.vel != was, (
                f"{axis} on the clusters bought no speed at all")
        return ("the torch fires along the nose and says so; off-axis it says "
                "it is swinging; the clusters always fire")

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
