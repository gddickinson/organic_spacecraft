"""What the bridge looks like, and what a press of it costs.

Split out of `tests/test_pilot_screen.py` when that reached 534 lines and the
ratchet said so. The other file is about *flying* — a course closing, the
computer handing back, a day billed once. This one is about the screen: that
it paints, that it fits the window it is shown in, that its controls say the
same numbers the sim does, and that a press does a bounded amount of work.

**Everything here is measured on a window that has been `show()`n.** An
offscreen widget that was never shown reports a scroll range of zero and
answers every layout question "fine" — the first probe of the fold did exactly
that and was worthless.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.screens import SCREENS
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import instruments as panel_sim
from .harness import Suite
from .test_pilot_screen import _bridge
from .test_sights import _Blind


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── bridge ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

    @check("the quays and hulls out there are named, as the conn names its own")
    def _():
        # **A player reported this**: standing off the Fleet Hub, the conn
        # draws it inside a dashed reticle reading "Fleet Hub · 12.0 km", and
        # the Pilot window showed nothing at all. The sky data was never
        # missing — measured, a free flight's `sky` holds *more* than an
        # approach's, ten entries against nine, including the anchorages the
        # approach leaves out. `Viewport._target` gives a target its real size
        # and a free flight has no target, so the Hub was one 1.6-pixel speck
        # among the stars.
        from PyQt6.QtWidgets import QApplication
        from ..sim import track as track_sim
        game, win, view = _bridge("cmp")
        app = QApplication.instance()

        # Moored, a quay is at *exactly* the ship's position — there is no
        # bearing to it and nothing to draw. That is right, not a gap.
        view.refresh()
        hub = next(c for c in view.in_view() if c.kind == "anchorage")
        assert any(n == hub.name for _v, n, _near in view.feed.sights), (
            "the window was not told about the quay at all")
        assert engage_sim.range_km(game, view.conn, hub) < 1.0, (
            "the fixture is not moored; the zero-bearing case is untested")

        # Fly out, and it must become something you can find.
        view.use_main = True
        for _ in range(90):
            view.burn("forward")
        view.refresh()
        for _ in range(3):
            app.processEvents()
        km = engage_sim.range_km(game, view.conn, hub)
        assert km > 100.0, f"the fixture never left: {km:,.0f} km"

        named = {n for _v, n, _near in view.feed.sights}
        assert hub.name in named, named
        assert any(c.kind == "hull" and c.name in named
                   for c in track_sim.contacts(game)), (
            f"no hull is named out of the window: {named}")
        # Worlds are not named: `_sky` draws those as lit discs and nobody
        # loses a planet.
        worlds = {c.name for c in track_sim.contacts(game) if c.kind == "body"}
        assert not (named & worlds), f"worlds are being labelled too: {named & worlds}"

        # **And the window actually paints them.** Comparing two grabs of the
        # same widget — one with sights, one without — proved nothing: the
        # images differed either way, so the check passed with the drawing
        # deleted. Ask the drawing itself instead, through the same `project`
        # and camera the window uses.
        from ..ui import viewport_mark
        from ..ui.viewport import basis
        from ..ui.viewport_math import project

        drew = 0
        for _vid, _label, vec in conn_sim.VIEWS:
            cam = basis(vec, view.conn)
            drew += viewport_mark.draw_sights(
                _Blind(), view.feed.sights, project, cam, 460, 260)
        assert drew, (
            "the window is told what is out there and paints none of it, in "
            "any of the six cameras")

        # **And the window calls it.** Asking the drawing directly proved only
        # that the drawing works — deleting the call from `Viewport.draw` left
        # this check green, because it was never testing the wiring.
        # Read the wiring rather than paint it: `Painted` declines to draw at
        # all when the platform refuses a backing store, and a check that
        # depends on a successful paint goes red on correct code.
        import inspect
        body = inspect.getsource(view.feed.draw)
        assert "viewport_mark.draw_sights(" in body, (
            "Viewport.draw never asks for the sights to be drawn")
        assert "self.sights" in body, (
            "it asks for sights to be drawn without handing them over")
        return (f"{len(named)} named at {km:,.0f} km off the quay, "
                f"{drew} of them landing in one of the six cameras")

    @check("the computer says what it is doing, and it changes as it does it")
    def _():
        # **It used to say six words the whole way in.** Measured on one run
        # to a contact 5,137 km off, the computer went `forward` on the torch,
        # then `back` on the thrusters to brake, then `None` to coast — and
        # the screen read "running for Held Breath" at every one of them, so a
        # pilot could not tell accelerating from braking from arriving.
        from ..sim import freeflight as free_sim
        from ..ui import pilot_panels as panels
        game, _win, view = _bridge("auto")
        target = next(c for c in view.in_view() if c.kind == "hull"
                      and 100 < engage_sim.range_km(game, view.conn, c)
                      < 200_000)
        assert panels._computer_says(view) == "off — she flies as you fly her"

        view.fly_at(target)
        view.set_auto("run")
        said = []
        for beats in (0, 200, 400, 600):
            for _ in range(beats):
                view.tick()
            said.append(panels._computer_says(view))

        # The words have to move with the flying. Not a fixed phrase.
        assert len(set(said)) > 1, (
            f"the computer said the same thing the whole way in: {said[0]!r}")
        # It burns to begin with and brakes before it arrives — the axis it
        # names is the axis `run_for` asked for.
        assert "ahead" in said[0], said[0]
        assert any("astern" in t for t in said[1:]), (
            f"it never said it was braking: {said}")
        for phrase in said[:-1]:
            assert "running her in" in phrase, phrase
        # Arrived: it hands the conn back and says that instead.
        assert view.auto == "hold", view.auto
        assert "holding station" in said[-1], said[-1]

        # Holding station is not a course, and says its own thing.
        view.break_off()
        assert "holding station" in panels._computer_says(view)
        view.set_auto("hold")
        assert panels._computer_says(view).startswith("off"), (
            panels._computer_says(view))
        return " → ".join(t.split(" — ")[-1] for t in said)

    @check("the thing you are flying at is ringed out of the window")
    def _():
        # **Measured before this existed: the picture did not change at all.**
        # A free flight has no `conn.target`, so `Viewport._target` returns at
        # once — "station keeping: there is no target, only sky" — and laying
        # a course rendered byte-identical. Out there everything is a point of
        # light and they all look alike, so "fly at that one" was a row of
        # text to cross-reference against a starfield.
        from PyQt6.QtWidgets import QApplication
        game, win, view = _bridge("mark")
        app = QApplication.instance()
        win.show()
        for _ in range(8):
            app.processEvents()
        try:
            target = next(c for c in view.in_view() if c.kind == "hull"
                          and 100 < engage_sim.range_km(game, view.conn, c)
                          < 200_000)
            # **Not by comparing two grabs.** Twice this cycle an image diff
            # of the same widget proved nothing — it differed with the
            # drawing deleted, and it matched with the drawing present when
            # other checks had run first. What the window is *told*, and
            # whether it *asks* for the ring, are both exact.
            from ..ui import viewport_mark
            assert view.feed.mark is None, "a ring before any course was laid"

            view.fly_at(target)
            view.refresh()
            for _ in range(4):
                app.processEvents()
            assert view.feed.mark is not None, "the window was told nothing"
            assert view.feed.mark[1] == target.name, view.feed.mark[1]

            # **And the window asks for it.** Not by painting: `Painted`
            # returns early when the platform refuses a backing store, so a
            # grab-based check goes red on correct code late in a long run —
            # it did, once. The wiring is in the source and can be read.
            import inspect
            body = inspect.getsource(view.feed.draw)
            assert "viewport_mark.draw(" in body, (
                "Viewport.draw never asks for the ring to be drawn")
            assert "self.mark" in body, (
                "Viewport.draw asks for a ring without handing it the mark")

            # And it lands somewhere in the picture, in some camera.
            from ..ui.viewport import basis
            from ..ui.viewport_math import project
            drawn = sum(1 for _v, _l, vec in conn_sim.VIEWS
                        if viewport_mark.draw(_Blind(), view.feed.mark,
                                              project, basis(vec, view.conn),
                                              460, 260))
            assert drawn, f"{target.name} is ringed in none of the six cameras"

            # Breaking off takes the ring away again.
            view.break_off()
            view.refresh()
            for _ in range(4):
                app.processEvents()
            assert view.feed.mark is None, "the ring outlived the course"
        finally:
            win.hide()
        return f"{target.name} ringed, and the ring goes when the course does"

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


    @check("a button press rebuilds the sky a bounded number of times")
    def _():
        # **The lag the pilot could feel.** Profiled, one press of Ahead took
        # 48.7 ms and ran `world.galaxy.distance` 151,728 times: every range
        # on the screen was measured on demand, each measurement walked
        # `track.at` -> `traffic.in_system`, and that rebuilt the Weave from
        # scratch — `weave.sites` is a farthest-point sample over the whole
        # sector and is pure in the galaxy alone.
        #
        # A stopwatch is not a check; it measures the machine. Counting the
        # work is. `traffic.in_system` is the rebuild, and one press must not
        # need many of them.
        from ..sim import traffic as traffic_sim
        from ..sim import weave as weave_sim
        from ..world import galaxy as galaxy_mod
        game, _win, view = _bridge("lag")
        view.burn("forward")                       # warm every one-off cache

        # **Counting calls to `sites` proved nothing** — the memo makes it
        # return early, so it is called just as often and costs nothing. What
        # has to be counted is the work it used to do: `galaxy.distance`, the
        # O(sites x systems) sweep, 151,728 of them per press before the fix.
        real_in_system = traffic_sim.in_system
        real_distance = galaxy_mod.distance
        real_weave_distance = weave_sim.distance
        tally = {"traffic": 0, "distance": 0}
        try:
            def counted_traffic(*a, **k):
                tally["traffic"] += 1
                return real_in_system(*a, **k)

            def counted_distance(*a, **k):
                tally["distance"] += 1
                return real_distance(*a, **k)

            traffic_sim.in_system = counted_traffic
            galaxy_mod.distance = counted_distance
            weave_sim.distance = counted_distance
            view.burn("forward")
        finally:
            traffic_sim.in_system = real_in_system
            galaxy_mod.distance = real_distance
            weave_sim.distance = real_weave_distance

        # Measured after the fix: 13 traffic rebuilds a press, from 27, and
        # the sector shape is never resampled at all. The bounds are loose
        # enough to survive a new panel and tight enough that going back to
        # measuring per widget fails.
        assert tally["traffic"] <= 20, (
            f"one button press rebuilt the system's traffic "
            f"{tally['traffic']} times")
        assert tally["distance"] < 2000, (
            f"one button press ran galaxy.distance {tally['distance']:,} "
            f"times; the sector shape is pure in the galaxy and is sampled "
            f"once, not on every question about where a hull is")
        return (f"{tally['traffic']} traffic rebuilds and "
                f"{tally['distance']:,} galaxy distances per press "
                f"(was 27 and 151,728)")


    @check("a beat does not take the button out from under the pilot")
    def _():
        # **The player's report: "when the clock is running the buttons do not
        # act immediately, and often don't respond at all."** The beat used to
        # be `View.refresh` — the screen taken apart and built again, four
        # times a second. Measured before the fix: **0 of 25 buttons survived
        # one beat**, and a press spanning one was swallowed whole — a
        # QPushButton emits `clicked` only if the release reaches the object
        # that took the press.
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QPushButton

        _game, _win, view = _bridge("beat")
        live = lambda: [b for b in view.findChildren(QPushButton)
                        if b.parent() is not None]
        was = {id(b) for b in live()}
        assert len(was) > 10, f"the fixture has almost no controls: {len(was)}"
        view.tick()
        now = {id(b) for b in live()}
        assert now == was, (
            f"a beat replaced the controls: {len(was - now)} of {len(was)} "
            f"buttons went away")

        # And the press survives with them. A player lets go over the button
        # they aimed at — found by its label, not by a stale reference.
        fired = []
        real, view.burn = view.burn, lambda a: fired.append(a)
        try:
            def ahead():
                return next(b for b in live() if b.text() == "Ahead")
            took = ahead()
            QTest.mousePress(took, Qt.MouseButton.LeftButton,
                             Qt.KeyboardModifier.NoModifier,
                             took.rect().center())
            view.tick()
            let_go = ahead()
            assert let_go is took, "the button under the finger was replaced"
            QTest.mouseRelease(let_go, Qt.MouseButton.LeftButton,
                               Qt.KeyboardModifier.NoModifier,
                               let_go.rect().center())
            assert fired, "a press held across a beat never reached the ship"
        finally:
            view.burn = real
        return (f"{len(was)} controls, all still there after a beat, and a "
                f"click held across one still burns")

    @check("a beat still moves the readings, and a new situation still rebuilds")
    def _():
        # The other half: never rebuilding is worse than rebuilding too much.
        from PyQt6.QtWidgets import QLabel, QPushButton

        _game, _win, view = _bridge("shape")
        view.use_main = True
        live = lambda: [b for b in view.findChildren(QPushButton)
                        if b.parent() is not None]

        def board():
            return " ".join(l.text() for l
                            in view._boards["ship"].findChildren(QLabel))

        before, ids = board(), {id(b) for b in live()}
        for _ in range(5):
            view.tick()
        assert board() != before, "five beats, and the readout is unchanged"
        assert {id(b) for b in live()} == ids, "the readings moved the controls"

        # A course laid is a change of situation, not of reading.
        was = {b.text() for b in live()}
        view.fly_at(view.in_view()[0])
        fresh = {b.text() for b in live()} - was
        assert any(t.startswith("Run for") for t in fresh), (
            f"laying a course grew no autopilot button: {sorted(fresh)}")

        # So is securing: it takes the controls away entirely.
        view.secure()
        assert [b.text() for b in live()] == ["Take the conn"], (
            f"securing left {[b.text() for b in live()]}")
        return (f"readings move, controls hold, and a course laid grew "
                f"{len(fresh)} new controls")

    @check("the bridge fits the window it is shown in")
    def _():
        # **Measured on a *shown* window, because an offscreen widget that was
        # never shown reports a scroll range of zero and every layout question
        # answers "fine".** Shown at 1360x880 the bridge was 1,444 px tall in
        # a 782 px view — 662 px, 46% of it, below the fold — so the fire
        # control, the autopilot and the clock were all out of sight and the
        # pilot scrolled past the instruments to reach a trigger.
        #
        # Two columns fixed the height and broke the width: a row of four
        # "Fly at <name>" buttons wanted 660 px and a fire-control row
        # carrying the whole of `engage.note` wanted 802, so the content came
        # to 1,348 px inside an 891 px viewport and every reading in the
        # right-hand column was clipped mid-number.
        from PyQt6.QtWidgets import QApplication, QPushButton
        game, win, view = _bridge("look")
        app = QApplication.instance()
        win.show()
        for _ in range(10):
            app.processEvents()
        try:
            wide = view.widget().width()
            room = view.viewport().width()
            assert wide <= room, (
                f"the bridge is {wide} px wide in a {room} px view — "
                f"{wide - room} px of every right-hand reading is cut off")

            fold = view.verticalScrollBar().maximum()
            assert fold < 400, (
                f"{fold} px of the bridge is below the fold; the guns and the "
                f"clock are meant to be within a short scroll, not a long one")

            # And the controls are actually reachable without hunting.
            btns = view.findChildren(QPushButton)
            here = [b for b in btns
                    if b.visibleRegion().boundingRect().height() > 0]
            assert len(here) >= 20, (
                f"only {len(here)} of {len(btns)} controls are on screen")
            assert any("Run clock" in b.text() or "Stop clock" in b.text()
                       for b in here), "the clock is not reachable"
            assert any(b.text().startswith("Fly at") for b in here), (
                "nothing can be flown at without scrolling")
        finally:
            win.hide()
        return (f"{wide} px in {room}, {fold} px below the fold (was 662), "
                f"{len(here)} of {len(btns)} controls on screen")


    return True
