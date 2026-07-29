"""The screens the conn is flown on: six cameras, and the plotting board.

Split from `test_conn.py`, which holds the flying. The seam is the same one
the project draws everywhere else: what the ship *does* is one question, and
what the captain is *shown* is another — and this side of it is measured in
pixels, not in the projection's own arithmetic. A check that asked
`viewport.project` whether the aft camera can see something in front of the
ship would be asking the code to confirm itself.

Two faults these hold shut:

* **A camera row that is six copies of one picture** is not an instrument. So
  the target is flown up close and every feed is counted for lit pixels: the
  nose must be full of it and the tail must have none.
* **A starfield that shimmers.** It is fixed at import rather than drawn from
  `game.rng()` — which advances the save's seed, so a field drawn from it
  would both flicker between repaints and quietly reshuffle the chronicle
  every time a window was open. The docking instrument was bitten by exactly
  that, which is why the check exists at all.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import track as track_sim
from .harness import Suite


def _contacts(game, kinds=("body", "anchorage", "hull")):
    return [c for c in track_sim.contacts(game) if c.kind in kinds]


def run(suite: Suite) -> None:
    check = suite.check

    @check("the conn and the plotting board paint, and answer")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.conn_window import ConnWindow
        from ..ui.plot3d_window import PlotWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("windows-ui")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None

        board = PlotWindow(win)
        board.resize(1100, 760)
        board.show()
        for _ in range(3):
            app.processEvents()
        hull = next(c for c in _contacts(game, ("hull",)))
        board.canvas.selected = hull.id
        board.canvas.tracked.add(hull.id)
        board.when.setValue(60)
        board.refresh()
        for _ in range(3):
            app.processEvents()
        text = " ".join(lab.text() for lab in board.findChildren(QLabel)
                        if lab.text())
        assert hull.name in text, "the board does not name what is selected"
        solved = board.canvas.plotted
        assert solved and solved["arrive_day"] > game.day, solved
        assert f"day {solved['arrive_day']:,.0f}" in text, (
            "the board does not print the arrival day it has plotted")
        # The picture is not blank.
        image = board.canvas.grab().toImage()
        lit = sum(1 for x in range(0, image.width(), 4)
                  for y in range(0, image.height(), 4)
                  if image.pixelColor(x, y).green() > 60)
        assert lit > 40, f"the plot is empty: only {lit} lit samples"
        board.close()

        conn_win = ConnWindow(win, hull)
        conn_win.resize(1000, 720)
        conn_win.show()
        for _ in range(3):
            app.processEvents()
        assert len(conn_win.feeds) == len(conn_sim.VIEWS), conn_win.feeds
        rows = " ".join(lab.text() for lab in conn_win.findChildren(QLabel)
                        if lab.text())
        assert "m/s" in rows, "the conn shows no rates"
        before = conn_win.conn.speed
        conn_win._burn("forward")
        for _ in range(3):
            app.processEvents()
        assert conn_win.conn.speed != before, "a thruster did nothing"

        # The camera row is six different pictures, not six of the same one.
        shots = {vid: feed.grab().toImage()
                 for vid, feed in conn_win.feeds.items()}
        fore = shots["fore"]
        others = [vid for vid, img in shots.items()
                  if vid != "fore" and img == fore]
        assert not others, (
            f"these cameras show exactly what the nose does: {others}")
        conn_win.close()
        return (f"the board plots day {solved['arrive_day']:,.0f} and paints; "
                f"the conn shows {len(conn_sim.VIEWS)} distinct feeds and flies")

    @check("a camera shows what is in front of it and nothing else")
    def _():
        # The row is an instrument only if the target appears in the camera
        # that is pointing at it. Measured in pixels, not asserted from the
        # projection's own arithmetic.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.viewport import Viewport

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("cameras")
        contact = next(c for c in _contacts(game, ("anchorage", "hull")))

        def brightness(view_id: str, conn) -> int:
            feed = Viewport(conn, view_id)
            feed.resize(240, 200)
            image = feed.grab().toImage()
            # The target is drawn in a strong tint; the starfield is grey.
            return sum(1 for x in range(240) for y in range(0, 200, 2)
                       if image.pixelColor(x, y).green()
                       > image.pixelColor(x, y).red() + 40)

        conn = conn_sim.start(game, contact)
        pilot_sim.fly(conn, "close", 30)      # get close so it is a big disc
        assert not conn.over, conn.outcome
        seen = {vid: brightness(vid, conn) for vid, _l, _v in conn_sim.VIEWS}
        assert seen["fore"] > 200, (
            f"the target is dead ahead and the nose camera shows "
            f"{seen['fore']} lit pixels of it")
        assert seen["aft"] == 0, (
            f"the aft camera is showing {seen['aft']} pixels of something "
            "that is in front of the ship")
        for side in ("port", "starboard", "dorsal", "ventral"):
            assert seen[side] < seen["fore"] / 4, (
                f"the {side} camera shows nearly what the nose does")
        return (f"nose {seen['fore']} lit pixels, tail {seen['aft']}, "
                f"beams {seen['port']}/{seen['starboard']}")

    @check("the starfield does not shimmer, and does not touch the save")
    def _():
        # This project has already been bitten by an instrument drawn from
        # `game.rng()`: it re-rolled every repaint and advanced the chronicle's
        # seed doing it. The stars are fixed at import.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.viewport import Viewport

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("stars")
        contact = next(c for c in _contacts(game, ("hull",)))
        conn = conn_sim.start(game, contact)

        seed_before = game.seed_state if hasattr(game, "seed_state") else None
        feed = Viewport(conn, "port")
        feed.resize(200, 160)
        first = feed.grab().toImage()
        for _ in range(4):
            again = feed.grab().toImage()
            assert again == first, (
                "the view out of the same window changed with nothing moving")
        if seed_before is not None:
            assert game.seed_state == seed_before, (
                "painting a camera advanced the save's seed")
        return "five repaints of a still ship, one picture"
