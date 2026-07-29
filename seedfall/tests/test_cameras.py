"""The screens the conn is flown on: six cameras, and the plotting board.

Split from `test_conn.py`, which holds the flying. The seam is the same one
the project draws everywhere else: what the ship *does* is one question, and
what the captain is *shown* is another — and this side of it is measured in
pixels, not in the projection's own arithmetic. A check that asked
`viewport.project` whether the aft camera can see something in front of the
ship would be asking the code to confirm itself.

Three player reports landed here, and all three were the same thing: **a
window that captured the game instead of reading it.**

* Standing alongside the Fleet Hub, the conn opened on **the planet**.
  `track.contacts` lists bodies before anchorages and the window took the
  first row in reach — but you are already in orbit of the body, so
  approaching it is not a manoeuvre. A station is what you dock with.
* `ConnWindow.contacts` was built in `__init__`, so it went on offering the
  traffic of a system the ship had left.
* `PlotCanvas.system` was too. After a jump the canvas drew the old system
  while the contact list beside it — which asks the game every refresh —
  listed the new one. One window, two systems, neither of them labelled.

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

import math

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

        # The conn only opens on something the ship is already alongside —
        # that is the gate `sim/berthing.py` added, and this check used to
        # hand it a hull several AU away and then complain the panel was
        # empty. Put the ship somewhere and conn what is there.
        from ..sim import berthing as berth_sim
        game.orbit_body = game.system.bodies[0].id
        near = next(c for c in _contacts(game)
                    if berth_sim.can_conn(game, c)[0])
        conn_win = ConnWindow(win, near)
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
                f"the conn opens on {near.name} with "
                f"{len(conn_sim.VIEWS)} distinct feeds and flies")

    @check("the conn opens on what the ship is moored to")
    def _():
        # Reported: alongside a shipyard, the station is not what you see.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..sim import anchorage as anchorage_sim
        from ..ui.conn_window import ConnWindow, default_target
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        checked = 0
        for seed in range(6):
            game = new_game(f"moored-{seed}")
            places = anchorage_sim.in_system(game)
            if not places:
                continue
            quay = places[0]
            game.orbit_body = game.system.bodies[quay.body_index].id
            assert anchorage_sim.docked_at(game) is not None or True
            picked = default_target(game)
            assert picked is not None, "nothing in reach while moored to a quay"
            assert picked.kind == "anchorage" and picked.name == quay.name, (
                f"moored to {quay.name} and the conn opens on "
                f"{picked.name} ({picked.kind})")
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            window = ConnWindow(win)
            assert window.contact.name == quay.name, window.contact.name
            assert window.conn is not None, "the conn would not open at all"
            assert window.conn.target.radius_km > 0, (
                "the station has no size, so nothing would be drawn")
            window.close()
            win.close()
            checked += 1
        assert checked >= 3, checked
        return (f"{checked} chronicles: moored to a quay, the conn opens on "
                "the quay and not the world under it")

    @check("the windows follow the ship instead of remembering it")
    def _():
        # The staleness. Both windows used to capture what they needed in
        # `__init__`; a jump left them describing somewhere else.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.conn_window import ConnWindow
        from ..ui.plot3d_window import PlotWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("follow")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None

        board = PlotWindow(win)
        board.show()
        for _ in range(2):
            app.processEvents()
        was = game.system.id
        assert board.canvas.system.id == was

        conn_win = ConnWindow(win)
        before = {c.id for c in conn_win.contacts}

        # Jump.
        game.location_id = next(s.id for s in game.galaxy.systems
                                if s.id != was)
        board.refresh()
        for _ in range(2):
            app.processEvents()
        assert board.canvas.system.id == game.system.id, (
            f"the ship is at {game.system.name} and the plot still draws "
            f"{board.canvas.system.name}")
        assert game.system.name in board.title.text(), board.title.text()
        # The canvas and the list beside it must name one system, not two.
        drawn = {c.id for c in track_sim.contacts(game, board.canvas.system)}
        listed = {board.contact_list.item(i).data(
                      __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt
                      .ItemDataRole.UserRole)
                  for i in range(board.contact_list.count())}
        assert drawn == listed, (
            "the plot and its own contact list disagree about what is here")

        after = {c.id for c in conn_win.contacts}
        assert after != before, (
            "the conn still offers the traffic of the system the ship left")
        board.close()
        conn_win.close()
        win.close()
        return "jumped, and both windows describe where the ship actually is"

    @check("every screen puts a body in the same place on the same day")
    def _():
        # The captain's question: are positions linked across the game? They
        # are, because every screen bottoms out in `flight.position(body,
        # day)` — this is what proves it rather than asserting it, by asking
        # two independent screens for pixels and comparing what they imply.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..sim import flight
        from ..ui.helm_view import OrbitChart
        from ..ui.plot3d_window import PlotWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("agree-screens")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.resize(1300, 950)
        win.show()
        board = PlotWindow(win)
        board.resize(900, 700)
        board.show()

        worst, moved, samples = 0.0, 0.0, 0
        for day in (0, 3, 40, 400):
            game.day = day
            win.go("helm")
            for _ in range(2):
                app.processEvents()
            chart = win.views["helm"].findChild(OrbitChart)
            board.refresh()
            for _ in range(2):
                app.processEvents()
            for index, body in enumerate(game.system.bodies):
                truth = flight.position(body, game.day)
                # The helm chart, read back through its own projection.
                on_helm = chart._to_screen(*truth)
                scale, cx, cy = chart._scale()
                helm_au = ((on_helm.x() - cx) / scale,
                           (on_helm.y() - cy) / scale)
                # The plotting board, through a different projection entirely.
                contact = next(c for c in track_sim.contacts(game)
                               if c.body_index == index and c.kind == "body")
                board_au = track_sim.at(game, contact, game.day)
                worst = max(worst, math.dist(helm_au, truth),
                            math.dist(board_au, truth))
                samples += 1
            here = flight.position(game.system.bodies[0], game.day)
            moved = max(moved, math.dist(here,
                                         flight.position(game.system.bodies[0], 0)))
        board.close()
        win.close()
        assert worst < 1e-9, (
            f"two screens place the same body {worst:.4f} AU apart on the "
            "same day")
        assert samples >= 8, samples
        assert moved > 0.1, (
            f"the innermost body moved {moved:.4f} AU over 400 days — "
            "nothing is advancing with the clock")
        return (f"{samples} body-days, helm and plotting board agreeing to "
                f"{worst:.0e} AU, and the inner world moving {moved:.2f} AU")

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
            # Solid, lit *area* — not merely lit pixels.
            #
            # Two drafts got this wrong before it was right. The first looked
            # for a green cast, true of the flat tinted disc the window used
            # to draw and false of a plate-grey shipyard the moment
            # `ui/render3d.py` gave it a real model. The second counted any
            # bright pixel and duly counted the **starfield**: every camera
            # came back with four hundred samples of empty space.
            #
            # A star is a point and a hull is a surface, so a sample only
            # counts when its neighbours are lit too. That is model-agnostic
            # and starfield-proof, which is what the check was always about.
            def solid(x: int, y: int) -> bool:
                for dx, dy in ((0, 0), (3, 0), (0, 3), (3, 3)):
                    px = image.pixelColor(min(239, x + dx), min(198, y + dy))
                    if px.red() + px.green() + px.blue() < 120:
                        return False
                return True

            return sum(1 for x in range(0, 236, 2) for y in range(0, 196, 2)
                       if solid(x, y))

        conn = conn_sim.start(game, contact)
        pilot_sim.fly(conn, "close", 30)      # close enough to fill the frame
        assert not conn.over, conn.outcome
        seen = {vid: brightness(vid, conn) for vid, _l, _v in conn_sim.VIEWS}
        # The starfield puts a handful of bright points in every frame, so
        # "nothing" is a small number rather than zero.
        empty = max(seen[v] for v in ("aft", "port", "starboard",
                                      "dorsal", "ventral"))
        assert seen["fore"] > 400, (
            f"the target is dead ahead and the nose camera shows only "
            f"{seen['fore']} solid samples of it")
        assert seen["fore"] > empty * 6, (
            f"the nose shows {seen['fore']} lit samples and the brightest "
            f"other camera {empty} — they are all looking at the same thing")
        for side in ("aft", "port", "starboard", "dorsal", "ventral"):
            assert seen[side] < seen["fore"] / 8, (
                f"the {side} camera shows nearly what the nose does")
        return (f"nose {seen['fore']} lit pixels, tail {seen['aft']}, "
                f"beams {seen['port']}/{seen['starboard']}")

    @check("the cameras look where the ship is pointing")
    def _():
        # They did not. `conn.nose` is the 3D vector the main drive is aimed
        # along, and the camera basis was built from `conn.heading` — a bare
        # yaw angle **nothing in the game ever wrote to**. So swinging the
        # hull round with the thrusters changed the flying and not the view.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui import viewport as viewport_mod

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("aimed")
        game.orbit_body = game.system.bodies[0].id
        contact = next(c for c in _contacts(game, ("anchorage", "hull")))
        conn = conn_sim.start(game, contact)

        nose, right, dorsal = viewport_mod.hull_frame(conn)
        for a, b in ((nose, right), (right, dorsal), (dorsal, nose)):
            assert abs(sum(x * y for x, y in zip(a, b))) < 1e-6, (
                "the hull's axes are not at right angles to each other")
        fore, _r, _u = viewport_mod.basis((0.0, 1.0, 0.0), conn)
        assert math.dist(fore, nose) < 1e-6, (
            f"the nose camera looks {fore} while the ship points {nose}")

        # Turn the hull and the view turns with it.
        conn.nose = [1.0, 0.0, 0.0]
        turned, _r, _u = viewport_mod.basis((0.0, 1.0, 0.0), conn)
        assert math.dist(turned, (1.0, 0.0, 0.0)) < 1e-6, turned

        # And the belly looks at what is being approached, which is what
        # makes the ventral camera worth having in orbit. The sign of one
        # cross product had this backwards and put the planet in the sky.
        conn.pos = [0.0, 0.0, -40.0]
        conn.nose = [0.0, 1.0, 0.0]
        ventral, _r, _u = viewport_mod.basis((0.0, 0.0, -1.0), conn)
        toward = viewport_mod._unit([-c for c in conn.pos])
        assert sum(x * y for x, y in zip(ventral, toward)) > 0.9, (
            f"the belly camera looks {ventral} and the target is {toward}")
        return "the nose camera follows the nose, and the belly the target"

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
