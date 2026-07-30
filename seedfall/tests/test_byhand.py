"""The flight controls: can a player actually berth by hand?

The conn's console is built to be watched — a compact row of buttons under a
3D view. `ui/flight_window.py` is the other thing, a panel to be *flown*. The
question a check has to answer is not whether it renders but whether a pilot
can get a hull onto a mast with it, so that is what this does: hands on the
buttons, and look where the ship ends up.

Two faults were found by trying, and neither would have shown up any other
way:

- **It berthed 477 m from the mast.** There are two roads to "alongside" and
  only one had been gated on being at a berth, so a hull that bumped the
  structure anywhere at walking pace was moored. Flying by hand found the
  second road.
- **Nothing on the panel said when to start braking.** Three chronicles all
  hit the structure at 9.2 m/s with nineteen of twenty tonnes of thruster
  mass unspent. `autopilot.safe_rate` is what the computer holds to and had
  never been on a screen; the closing rate reads against its limit now.

The claims:

- **A pilot can berth by hand from the corridor**, which is what a docking
  panel is for. The long approach is the computer's job: from twelve
  kilometres the hold point and the middle of the structure are 2.6° apart,
  and a six-axis pad cannot tell them apart.
- **The panel's guidance is the computer's course**, off the same `moorings.aim`.
- **Both windows are one approach**, not two.
- **What a button promises is what it does.**
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import moorings
from ..sim import pilot as quote_sim
from .harness import Suite

#: Held at module scope: a local reference dies when its helper returns, and
#: Qt takes the application down with it.
_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    assert _HELD is not None
    return _HELD


def _panel(seed: str = "byhand"):
    """A game with the conn open and the flight controls on the same approach."""
    from ..ui.conn_window import open_conn
    from ..ui.flight_window import open_flight
    from ..ui.window import MainWindow

    keep = _app()
    assert keep is not None
    game = new_game(seed)
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    open_conn(win)
    return win, open_flight(win)


def _to_corridor(conn) -> None:
    """Let the computer bring it to the corridor, and hand over there.

    Hand-over on **the gap to the berth**, at four times the reach — measured,
    that is seven ticks before the computer would berth, which is the last
    part of the approach and what a manual panel is for.

    Two conditions were tried and neither works, both for the same reason: a
    berth is off to one side, so the ship's *range to the centre* and its
    distance to the fitting are different questions. `range_km <= corridor`
    never fires — this approach berths at 0.576 km from the centre with the
    corridor at 0.555, because the mast is not on the line to the middle. And
    `dist(pos, aim) <= reach * 1.2` never fires either, because the ship
    closes on the berth along its own line rather than through the hold point.
    """
    reach = moorings.reach_km(conn.target)
    for _ in range(3000):
        if conn.over:
            return
        found = moorings.nearest(conn)
        if found is not None and found["km"] <= reach * 4.0:
            return
        axis, main, throttle = pilot_sim.autopilot(conn, "close")
        conn_sim.apply(conn, axis, main=main, throttle=throttle)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the panel reads out what a berthing actually needs")
    def _():
        from PyQt6.QtWidgets import QLabel
        win, panel = _panel()
        said = " ".join(lab.text() for lab in panel.findChildren(QLabel)
                        if lab.text())
        conn = panel.conn
        assert conn is not None
        want = ("Range", "Closing", "Lateral", "Berth")
        missing = [n for n in want if n.upper() not in said.upper()]
        limit = pilot_sim.safe_rate(conn)
        assert not missing, f"the panel does not show {missing}"
        assert f"{limit:.2f}" in said, (
            "the closing rate is shown without the limit it has to be under, "
            "which is the number that says when to brake")
        assert f"{conn_sim.ALONGSIDE_RATE:.1f}" in said, said[:200]
        # **And the guidance is on the buttons**, not merely available from
        # the sim. It was lost from the labels once and nothing noticed,
        # because every other check here calls `moorings.steer` directly —
        # so this one reads the pad.
        marks = {axis: panel.axis_buttons[axis].text()[0]
                 for axis in panel.axis_buttons}
        assert set(marks.values()) <= {"▲", "▼", "·"}, marks
        assert "▲" in marks.values(), (
            f"no button is marked as taking the ship toward the berth: "
            f"{marks}")
        assert "▼" in marks.values(), (
            f"no button is marked as taking it away: {marks}")
        # And the marks agree with the sim, rather than being decoration.
        steer = moorings.steer(conn)
        for axis, mark in marks.items():
            if mark == "▲":
                assert steer[axis] > 0.25, (axis, steer[axis])
            elif mark == "▼":
                assert steer[axis] < -0.25, (axis, steer[axis])
        win.close()
        panel.close()
        return (f"range, closing against {limit:.2f} m/s, lateral, berth, the "
                f"gate, and {sum(1 for m in marks.values() if m != '·')} of "
                f"{len(marks)} pad buttons marked with where the berth is")

    @check("a pilot can berth by hand from the corridor")
    def _():
        # Flown: the computer hands over at the hold point and the pilot puts
        # the hull on the mast with pad presses. The answer is *where it ended
        # up*, not what it said.
        rows = []
        for seed in ("byhand", "hands2", "hands3"):
            win, panel = _panel(seed)
            conn = panel.conn
            assert conn is not None, "nothing in reach to fly to"
            _to_corridor(conn)
            assert not conn.over, conn.outcome
            presses = 0
            for _ in range(2000):
                if conn.over:
                    break
                presses += 1
                across = math.dist(pilot_sim.lateral(conn), (0.0, 0.0, 0.0))
                gap = math.dist(conn.pos, moorings.aim(conn))
                if (conn.closing > pilot_sim.safe_rate(conn)
                        or across > 0.4 or conn.closing < -0.2):
                    panel._null()
                elif gap > 0.02:
                    steer = moorings.steer(conn)
                    panel._burn(max(steer, key=lambda a: steer[a]))
                else:
                    panel._tick()
            found = moorings.nearest(conn)
            rows.append((seed, conn.outcome, found, presses))
            win.close()
            panel.close()
        bad = [r for r in rows if r[1] != "alongside" or not r[2]["at_it"]]
        assert not bad, f"hand-flown approaches that did not berth: {bad}"
        return " · ".join(
            f"{s}: {f['name']} in {p} presses, {f['km'] * 1000:.0f} m off"
            for s, _o, f, p in rows)

    @check("the panel's guidance is the course the computer flies")
    def _():
        # One door, asked numerically: `moorings.steer` points at
        # `moorings.aim`, and `autopilot` flies to the same place.
        win, panel = _panel()
        conn = panel.conn
        seen = 0
        for _ in range(40):
            if conn.over:
                break
            aim = moorings.aim(conn)
            steer = moorings.steer(conn)
            want = [a - p for a, p in zip(aim, conn.pos)]
            span = math.dist(want, (0.0, 0.0, 0.0)) or 1.0
            want = [c / span for c in want]
            for axis_id, toward in steer.items():
                push = conn_sim.thrust_axis(conn, axis_id, False)
                assert abs(toward
                           - sum(w * p for w, p in zip(want, push))) < 1e-9
            law = pilot_sim.target_velocity(conn, "close")
            if law and math.dist(law, (0.0, 0.0, 0.0)) > 1e-6:
                length = math.dist(law, (0.0, 0.0, 0.0))
                agree = sum(w * c / length for w, c in zip(want, law))
                assert agree > 0.99, (agree, conn.range_km)
                seen += 1
            axis, main, throttle = pilot_sim.autopilot(conn, "close")
            conn_sim.apply(conn, axis, main=main, throttle=throttle)
        win.close()
        panel.close()
        assert seen >= 20, seen
        return f"{seen} ticks: the arrows and the computer point the same way"

    @check("both windows are one approach, and a promise is what happens")
    def _():
        win, panel = _panel()
        conn = panel.conn
        assert conn is win.conn_window.conn, (
            "the flight controls are flying a different ship from the conn")
        said = quote_sim.quote(conn, "forward", main=False)
        # **Off the button's own label**, because the promise is the thing
        # printed on it. Comparing the quote against the burn leaves the label
        # free to say anything: the mutation that doubled the figure on the
        # pad passed, since the quote and the act still agreed with each
        # other perfectly and neither was what the pilot could read.
        panel.refresh()
        printed = panel.axis_buttons["forward"].text().split("\n")[-1]
        shown = float(printed.split()[0])
        assert abs(shown - said["dv"]) < 0.005, (
            f"the pad says {printed!r} and the quote says {said['dv']:.2f}")
        before = list(conn.vel)
        conn_sim.apply(conn, "forward", main=False, ticks=conn.coast_min,
                       throttle=conn.throttle)
        moved = math.dist([v - b for v, b in zip(conn.vel, before)],
                          (0.0, 0.0, 0.0))
        win.close()
        panel.close()
        assert abs(moved - said["dv"]) < max(0.02, said["dv"] * 0.05), (
            f"the button promised {said['dv']:.3f} m/s and the burn gave "
            f"{moved:.3f}")
        return (f"one approach in two windows; the pad reads {shown:.2f} m/s, "
                f"the quote says {said['dv']:.2f} and the burn gave {moved:.2f}")
