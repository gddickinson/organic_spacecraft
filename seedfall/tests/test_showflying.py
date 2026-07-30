"""Showing the autopilot fly, and where the approach is going.

The computer has flown the ship since it was written and nothing on any screen
said so. A captain watching the conn saw six identical buttons and no sign of
which thruster was firing, no indication the autopilot was even on, and no
picture of the two objects together at all.

Four things, and the claims each has to meet:

- **What the ship fired is recorded**, by `conn.apply`, and it is the burn
  that happened rather than a fresh ask of the computer — which would be a
  forecast, and would disagree the moment anything moved.
- **Both consoles light it.** Read off the buttons, because a light nobody can
  see is not a light.
- **The engines are drawn where they are, and glow when they fire** — and a
  thruster fires *opposite* to the way the ship goes, so *Ahead* lights the
  **aft** cluster. That fact has been in `data/mounts.py` since it was written
  and no screen had ever used it.
- **The predicted course is a dry run of the act.** `preview.track` flies a
  throwaway twin with the real `apply` under the real computer, so the line on
  the plot is the flying — checked by flying the real approach the same
  distance and comparing.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import preview as preview_sim
from ..sim import thrusters
from .harness import Suite

_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    assert _HELD is not None
    return _HELD


def _shut(win, *windows) -> None:
    """Close the pop-outs, then the window that parented them.

    Closing only the parent leaves Qt to destroy the children, and a child
    with a repaint still queued is destroyed *while it is being painted* —
    which is a segfault, not an exception, and takes the suite with it before
    it can say anything.
    """
    keep = _app()
    for window in windows:
        if window is not None:
            window.close()
    keep.processEvents()
    win.close()
    keep.processEvents()


def _bridge(seed: str = "showing"):
    """A chronicle with the conn, the flight panel and the approach view up."""
    from ..ui.approach_window import open_approach
    from ..ui.conn_window import open_conn
    from ..ui.flight_window import open_flight
    from ..ui.window import MainWindow

    keep = _app()
    assert keep is not None
    game = new_game(seed)
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    return win, open_conn(win), open_flight(win), open_approach(win)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the ship records the burn it actually made")
    def _():
        # Not what the computer would ask for now — what was fired. The two
        # differ the moment anything moves, which is every tick.
        win, conn_win, panel, view = _bridge()
        conn = panel.conn
        seen, matched = [], 0
        for _ in range(8):
            if conn.over:
                break
            axis, main, throttle = pilot_sim.autopilot(conn, "close")
            conn_sim.apply(conn, axis, main=main, throttle=throttle)
            seen.append((axis, conn.fired_axis, conn.fired_main,
                         round(conn.fired_share, 2)))
            if axis is not None and conn.fired_axis == axis:
                matched += 1
        # Coasting records nothing, which is how a screen knows to go dark.
        conn_sim.apply(conn, None)
        assert conn.fired_axis is None and conn.fired_share == 0.0, conn.fired_axis
        for row in seen:
            if row[0] is None:
                assert row[1] is None, row
        assert matched >= 4, seen
        # And the throttle recorded is the one that was *usable*, not the one
        # asked for: the computer opens a drive to 62% and then to 25%.
        shares = {row[3] for row in seen if row[1] and row[2]}
        assert shares and shares != {1.0}, shares
        _shut(win, panel, view, conn_win)
        return (f"{len(seen)} ticks recorded, {matched} of them a burn; "
                f"drive shares seen: {sorted(shares)}")

    @check("both consoles light the control that is firing")
    def _():
        win, conn_win, panel, view = _bridge()
        conn = panel.conn
        panel._auto("close")
        for _ in range(3):
            panel._tick()
        conn_win.refresh()
        panel.refresh()
        pad = {axis: bool(btn.styleSheet())
               for axis, btn in panel.axis_buttons.items()}
        console = {axis: bool(btn.styleSheet())
                   for axis, btn in conn_win.controls.axis_buttons.items()}
        fired = conn.fired_axis
        assert fired, "nothing fired to light"
        assert [a for a, on in pad.items() if on] == [fired], (fired, pad)
        assert [a for a, on in console.items() if on] == [fired], (fired,
                                                                   console)
        # And the drive, when it is the drive doing it.
        assert bool(panel.main_btn.styleSheet()) == bool(conn.fired_main)
        # And **how far the drive is open**, on the screen. The computer runs
        # it at 62% and then 25% within four ticks; a light with no number on
        # it cannot tell those apart, and `fired_share` was written and read by
        # nothing until the declared-field guard said so.
        if conn.fired_main:
            assert f"{conn.fired_share:.0%}" in panel.main_btn.text(), (
                panel.main_btn.text(), conn.fired_share)
        _shut(win, panel, view, conn_win)
        return (f"{fired} lit on the pad and on the console; the drive "
                f"{'lit' if conn.fired_main else 'dark'}")

    @check("the autopilot has one obvious switch, and both windows share it")
    def _():
        win, conn_win, panel, view = _bridge()
        assert panel.mode is None and conn_win.mode is None
        panel._auto("close")
        assert conn_win.mode == "close", "arming the panel did not arm the ship"
        assert panel.mode == "close"
        assert bool(panel.auto_buttons["close"].styleSheet()), "not lit"
        # Pressing the running mode again turns it off, and so does the
        # off switch — there is no way to be uncertain whether it is on.
        panel._auto("close")
        assert conn_win.mode is None, conn_win.mode
        panel._auto("null")
        assert conn_win.mode == "null"
        panel._auto(None)
        assert conn_win.mode is None
        assert bool(panel.off_btn.styleSheet()), "the off switch is not lit"
        _shut(win, panel, view, conn_win)
        return "armed from the panel, shared with the conn, and off two ways"

    @check("a thruster fires opposite to the way the ship goes")
    def _():
        # The fact the diagram exists to show, asked of the sim: pressing
        # *Ahead* lights the **aft** cluster, because that is the one pushing.
        game = new_game("engines")
        rows = thrusters.firing(game.ship, "forward", False)
        lit = [name for _at, _push, name, _kn, on in rows if on]
        assert lit == ["Aft cluster"], lit
        assert [n for _a, _p, n, _k, on in
                thrusters.firing(game.ship, "up", False) if on] \
            == ["Ventral cluster"]
        # The drive is the drive, and coasting lights nothing.
        drive = [n for _a, _p, n, _k, on in
                 thrusters.firing(game.ship, "forward", True) if on]
        assert drive and "cluster" not in drive[0].lower(), drive
        assert not [n for _a, _p, n, _k, on in
                    thrusters.firing(game.ship, None, False) if on]
        # Every mount the hull carries is in the list, lit or not.
        assert len(rows) == len(thrusters.drives(game.ship)) + 6, len(rows)
        return (f"{len(rows)} mounts; ahead lights {lit[0]}, up lights the "
                "ventral cluster, the drive lights itself")

    @check("the ship diagram lights up where the engine is")
    def _():
        # Pixels: the same frame with the burn and without it, and the light
        # has to appear near where `data/mounts.py` says that engine sits.
        from PyQt6.QtGui import QColor
        from ..ui import render3d, shipdiagram

        keep = _app()
        assert keep is not None
        game = new_game("engines")
        panel = shipdiagram.ShipDiagram(game)
        panel.resize(340, 200)

        class _Conn:
            fired_axis = None
            fired_main = False

        panel.conn = _Conn()
        dark = panel.grab().toImage()
        lit_conn = _Conn()
        lit_conn.fired_axis, lit_conn.fired_main = "forward", False
        panel.conn = lit_conn
        bright = panel.grab().toImage()

        def lit_pixels(image):
            return {(x, y) for y in range(0, image.height(), 2)
                    for x in range(0, image.width(), 2)
                    if image.pixelColor(x, y).green() > 120
                    and image.pixelColor(x, y).red() < 160}

        gained = lit_pixels(bright) - lit_pixels(dark)
        assert len(gained) > 20, (
            f"firing a thruster added {len(gained)} lit samples")
        # And it is *where the engine is*: the aft cluster, projected the same
        # way the hull is drawn.
        at = next(a for a, _p, n, _k, _o in
                  thrusters.firing(game.ship, "forward", False)
                  if n == "Aft cluster")
        placed = render3d.place(at, shipdiagram.SPIN, shipdiagram.TILT)
        camera = render3d.Camera(at=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0),
                                 up=(0.0, 1.0, 0.0), width=340, height=200,
                                 half_fov=shipdiagram.HALF_FOV)
        spot = camera.project((placed[0], placed[1],
                               placed[2] + shipdiagram.SUBJECT_AT))
        assert spot is not None
        want = (spot[0].x(), spot[0].y())
        near = [p for p in gained if math.dist(p, want) < 40]
        assert len(near) > len(gained) * 0.5, (
            f"only {len(near)} of {len(gained)} new lit samples are near the "
            f"cluster that fired")
        return (f"{len(gained)} samples lit by one thruster, {len(near)} of "
                "them on the mount that fired")

    @check("the predicted course is the flying, not a formula")
    def _():
        # The one-door claim, and the strongest form of it: fly the *real*
        # approach as far as the prediction goes and compare. Same code, so
        # the answer is exact rather than close.
        win, conn_win, panel, view = _bridge("predicting")
        conn = panel.conn
        rows = preview_sim.track(conn, "close", ticks=30, every=5)
        assert len(rows) >= 5, rows
        held = (conn.range_km, conn.elapsed, conn.rcs)
        for _ in range(30):
            if conn.over:
                break
            axis, main, throttle = pilot_sim.autopilot(conn, "close")
            conn_sim.apply(conn, axis, main=main, throttle=throttle)
        said = rows[-1]
        assert abs(said[2] - conn.range_km) < 1e-9, (
            f"the plot predicted {said[2]:.4f} km and the flying gave "
            f"{conn.range_km:.4f}")
        assert all(abs(a - b) < 1e-9 for a, b in zip(said[1], conn.pos))
        # The flying moved the ship, which is the point of comparing.
        assert (conn.range_km, conn.elapsed, conn.rcs) != held, held
        # And the prediction itself costs the real approach nothing: predicting
        # is a dry run, so doing it twice more must leave the ship where it is.
        after = (conn.range_km, conn.elapsed, conn.rcs)
        preview_sim.track(conn, "close", ticks=30, every=5)
        preview_sim.track(conn, None, ticks=30, every=5)
        assert (conn.range_km, conn.elapsed, conn.rcs) == after, (
            "predicting a course flew the ship along it")
        _shut(win, panel, view, conn_win)
        return (f"{len(rows)} marks: predicted {said[2] * 1000:,.0f} m at "
                f"{said[0] / 60:.0f} min, flown {conn.range_km * 1000:,.0f} m")

    @check("the approach view frames both, and the camera answers to the pilot")
    def _():
        win, conn_win, panel, view = _bridge()
        conn = view.conn
        view.resize(600, 460)
        view._frame()
        # The pair is in frame: both the ship and the target project inside it.
        camera = view.camera(600, 460, view.span_km())
        seen = []
        for at in (tuple(conn.pos), (0.0, 0.0, 0.0)):
            spot = camera.project(at)
            assert spot is not None, at
            assert 0 <= spot[0].x() <= 600 and 0 <= spot[0].y() <= 460, (
                at, spot[0].x(), spot[0].y())
            seen.append((spot[0].x(), spot[0].y()))
        # **And they straddle the middle.** Two weaker forms of this claim
        # failed to bite, and the reasons are worth keeping. A bounding box
        # cannot say it: centring on the target puts the ship 111 px off and
        # the target dead centre, and both are still *inside* the frame. Nor
        # can the 2D midpoint: perspective puts the near object further from
        # the centre than the far one, so even correct centring lands it
        # 20–31 px out against 55 for the fault — a gap too narrow to write a
        # bar across.
        #
        # What is crisp is *which side of the centre each is on*. Centred on
        # the pair they are on opposite sides; centred on the target it sits
        # exactly on the centre and nothing straddles anything. Asked at three
        # camera angles, because one is a coincidence.
        for turn, tilt in ((0.6, 0.5), (0.15, 0.8), (0.9, 0.2)):
            view.turn, view.tilt = turn, tilt
            view._frame()
            look = view.camera(600, 460, view.span_km())
            spots = [look.project(at) for at in (tuple(conn.pos),
                                                 (0.0, 0.0, 0.0))]
            assert all(s is not None for s in spots), (turn, tilt)
            xs = [s[0].x() - 300.0 for s in spots]
            ys = [s[0].y() - 230.0 for s in spots]
            apart = max(abs(xs[0] - xs[1]), abs(ys[0] - ys[1]))
            assert apart > 40.0, (turn, tilt, xs, ys)
            assert (xs[0] * xs[1] < 0 or ys[0] * ys[1] < 0), (
                f"at pan {turn} tilt {tilt} the ship and the target are on the "
                f"same side of the frame's centre — the view is centred on "
                f"one of them, not on both: {xs}, {ys}")
        # And the sliders move the picture rather than decorating it.
        wide = view.span_km()
        view._set("zoom", 0.05)
        assert view.span_km() < wide * 0.5, (wide, view.span_km())
        before = view.camera(600, 460, view.span_km()).at
        view._set("turn", (view.turn + 0.25) % 1.0)
        assert view.camera(600, 460, view.span_km()).at != before
        before = view.camera(600, 460, view.span_km()).at
        view._set("tilt", 0.95)
        assert view.camera(600, 460, view.span_km()).at != before
        _shut(win, panel, view, conn_win)
        return (f"framed at {wide:,.1f} km with both in it; zoom, pan and tilt "
                "all move the camera")
