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


def run(suite: Suite) -> bool:
    try:
        import PyQt6  # noqa: F401
    except ImportError as err:
        print(f"── bridge ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    check = suite.check

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
            before = view.feed.grab().toImage()
            view.fly_at(target)
            view.refresh()
            for _ in range(4):
                app.processEvents()
            after = view.feed.grab().toImage()
            assert after != before, (
                f"a course was laid on {target.name} and the view out of the "
                f"window is pixel for pixel what it was")
            assert view.feed.mark is not None, "the window was told nothing"
            assert view.feed.mark[1] == target.name, view.feed.mark[1]

            # Breaking off takes the ring away again.
            view.break_off()
            view.refresh()
            for _ in range(4):
                app.processEvents()
            assert view.feed.mark is None, "the ring outlived the course"
            assert view.feed.grab().toImage() == before, (
                "breaking off left something drawn on the window")
        finally:
            win.hide()
        return f"{target.name} ringed, and the ring goes when the course does"

    @check("a mark behind the camera is not drawn in front of it")
    def _():
        # `project` returns None for anything at or behind the lens, and the
        # ring must respect that or a contact astern would be painted over
        # the stars ahead. Asked directly, because a picture cannot easily
        # prove the *absence* of a ring in the right place.
        from ..ui import viewport_mark
        from ..ui.viewport_math import project

        cam = ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        drawn = []

        class Fake:
            def setPen(self, *a): pass
            def setBrush(self, *a): pass
            def setFont(self, *a): pass
            def drawEllipse(self, *a): drawn.append("ring")
            def drawLine(self, *a): pass
            def drawText(self, *a): drawn.append("name")
            def fontMetrics(self):
                class M:
                    def horizontalAdvance(self, _t): return 60
                return M()

        assert viewport_mark.draw(Fake(), ((0.0, 5.0, 0.0), "ahead"),
                                  project, cam, 400, 300) is True
        assert "ring" in drawn and "name" in drawn, drawn
        drawn.clear()
        assert viewport_mark.draw(Fake(), ((0.0, -5.0, 0.0), "astern"),
                                  project, cam, 400, 300) is False
        assert not drawn, "a mark behind the camera was drawn anyway"
        assert viewport_mark.draw(Fake(), None, project, cam, 400, 300) is False
        assert viewport_mark.draw(Fake(), ((0.0, 0.0, 0.0), "here"),
                                  project, cam, 400, 300) is False
        return "ahead is ringed; astern, nothing, and a zero bearing are not"

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
