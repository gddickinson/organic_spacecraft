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
        # "Look fore", not "Fore" (#153): cameras and thrusters shared names.
        for camera in ("Look fore", "Look aft"):
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
        # act immediately, and often don't respond at all."** The beat was
        # `View.refresh` — the screen rebuilt four times a second. Measured:
        # **0 of 25 buttons survived one beat**, and a press spanning one was
        # swallowed whole, a QPushButton emitting `clicked` only if the
        # release reaches the object that took the press.
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

        # The press survives too: a player lets go over the button they
        # aimed at, by label. The pad is press-and-hold: the beat consumes
        # the order, and the release must not fire a second one.
        def ahead():
            return next(b for b in live() if b.text() == "Ahead")
        took = ahead()
        QTest.mousePress(took, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         took.rect().center())
        view.tick()
        burned = view.conn.fired_axis
        let_go = ahead()
        assert let_go is took, "the button under the finger was replaced"
        QTest.mouseRelease(let_go, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier,
                           let_go.rect().center())
        assert burned == "forward", (
            "a press held across a beat never reached the ship")
        assert _win.burn_order is None, "the order outlived the finger"
        return (f"{len(was)} controls, all still there after a beat, and a "
                f"click held across one still burns")

    @check("a beat still moves the readings, and a new situation still rebuilds")
    def _():
        from PyQt6.QtWidgets import QLabel, QPushButton

        _game, _win, view = _bridge("shape")
        view.use_main = True
        live = lambda: [b for b in view.findChildren(QPushButton)
                        if b.parent() is not None]

        def board():
            return " ".join(l.text() for l
                            in view._boards["ship"].findChildren(QLabel))

        before, ids = board(), {id(b) for b in live()}
        # A beat swaps the readouts whole and must put each back where it
        # came from: a `_swap` remembering one column walks the fire control
        # across to the boards on the first tick.
        column = view._boards["fire"].parentWidget()
        for _ in range(5):
            view.tick()
        assert view._boards["fire"].parentWidget() is column, (
            "a beat moved the fire control into the other column")
        assert board() != before, "five beats, and the readout is unchanged"
        assert {id(b) for b in live()} == ids, "the readings moved the controls"

        was = {b.text() for b in live()}
        view.fly_at(view.in_view()[0])
        fresh = {b.text() for b in live()} - was
        assert any(t.startswith("Run for") for t in fresh), (
            f"laying a course grew no autopilot button: {sorted(fresh)}")

        view.secure()
        assert [b.text() for b in live()] == ["Take the conn"], (
            f"securing left {[b.text() for b in live()]}")
        return (f"readings move, controls hold, and a course laid grew "
                f"{len(fresh)} new controls")

    @check("the bridge fits the window it is shown in")
    def _():
        # **Measured on a *shown* window: one never shown reports a scroll
        # range of zero and answers every layout question "fine".** At
        # 1360x880 the bridge was 1,444 px in a 782 px view — 662 px, 46%,
        # below the fold, hiding the fire control, autopilot and clock.
        #
        # Two columns fixed the height and broke the width: four "Fly at"
        # buttons wanted 660 px and a fire-control row carrying `engage.note`
        # wanted 802, so content came to 1,348 px in an 891 px viewport and
        # every right-hand reading was clipped mid-number.
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

            # **Every control, not most.** At a 199 px fold the two still
            # under it were "Open fire on Patient Ledger" and "Mark Patient
            # Ledger hostile" — a pilot scrolling to reach the trigger,
            # because the left column carried 173 px and the right 777.
            fold = view.verticalScrollBar().maximum()
            btns = view.findChildren(QPushButton)
            off = [b.text() for b in btns
                   if b.visibleRegion().boundingRect().height() == 0]
            assert not off, f"{fold} px below the fold, and under it: {off}"

            at = lambda w: w.mapTo(view.widget(), w.rect().topLeft()).x()
            gun = next((b for b in btns if b.text().startswith("Open fire")),
                       None)
            if gun is not None:
                assert at(gun) < at(view._boards["ship"]), (
                    "the fire control is over with the boards again")
        finally:
            win.hide()
        return (f"{wide} px in {room}, {fold} px below the fold (was 662, "
                f"then 199), all {len(btns)} controls on screen")


    return True
