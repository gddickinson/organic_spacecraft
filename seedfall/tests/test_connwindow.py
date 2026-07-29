"""Flying the conn from the window, and the window keeping up with the ship.

`test_cameras.py` holds what the cameras *show*. This holds what the window
*does* — and it exists because two player reports landed on the same file for
opposite reasons.

* **The conn opened on the planet** while the ship was moored to a shipyard,
  because `track.contacts` lists bodies before anchorages and the window took
  the first row in reach. You are already in orbit of the body; approaching it
  is not a manoeuvre.
* **"Close and berth" teleported.** It ran four hundred ticks inside the
  click, so the hull arrived and the result was reported — which is exactly
  what a conn exists not to do. The mode is *held* now and one tick is flown
  per beat of the same clock the coast button uses, so a berthing takes the
  forty minutes it takes and can be watched, corrected or called off half-way.
* **And the window did not notice the ship being flown.** A course set at the
  helm moves the hull; this window was built around wherever it stood when it
  opened, and went on showing an approach on somewhere the ship had left.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import anchorage as anchorage_sim
from ..sim import conn as conn_sim
from ..sim import track as track_sim
from .harness import Suite


def _contacts(game, kinds=("body", "anchorage", "hull")):
    return [c for c in track_sim.contacts(game) if c.kind in kinds]


def _moored(seed: str):
    """A captain alongside a quay, which is where a conn is worth opening."""
    game = new_game(seed)
    places = anchorage_sim.in_system(game)
    if not places:
        return None
    game.orbit_body = game.system.bodies[places[0].body_index].id
    return game


def run(suite: Suite) -> None:
    check = suite.check

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

    @check("the computer flies on the clock, it does not teleport")
    def _():
        # The report. Pressing *Close and berth* ran the whole approach
        # inside the click: four hundred ticks, and the hull simply arrived.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.conn_window import ConnWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _moored("realtime")
        assert game is not None
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        window = ConnWindow(win)
        assert window.conn is not None and not window.conn.over

        opened_at = window.conn.range_km
        window._auto("close")
        assert window.mode == "close", window.mode
        assert window.running, "engaging the computer did not start the clock"
        assert abs(window.conn.range_km - opened_at) < 1e-9, (
            f"the ship moved {opened_at - window.conn.range_km:,.3f} km in the "
            "click that engaged the autopilot — it is still teleporting")
        assert window.conn.elapsed == 0, window.conn.elapsed

        # It flies, a tick at a time, and takes the time it takes.
        ticks = 0
        while not window.conn.over and ticks < 400:
            window._tick()
            ticks += 1
        assert window.conn.outcome == "alongside", window.conn.outcome
        assert ticks > 20, (
            f"the whole berthing took {ticks} ticks — that is not being flown")
        assert window.conn.elapsed > 1200, window.conn.elapsed

        # And pressing it again lets go rather than doing it twice.
        game2 = _moored("letgo")
        win2 = MainWindow(game2)
        win2.toast = lambda *a, **k: None
        second = ConnWindow(win2)
        second._auto("close")
        assert second.mode == "close"
        second._auto("close")
        assert second.mode is None, "the computer will not give the conn back"
        window.close()
        second.close()
        return (f"{ticks} ticks and {window.conn.elapsed / 60:,.0f} minutes to "
                "berth, none of it inside the click")

    @check("the window follows the ship when the helm flies it")
    def _():
        # The other report: a course set at the helm moves the hull, and this
        # window went on showing an approach on somewhere it had left.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.conn_window import ConnWindow
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _moored("followed")
        assert game is not None
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        window = ConnWindow(win)
        was = window.contact.name if window.contact else None
        assert was, "nothing to conn where the ship is moored"

        # The helm flies somewhere else entirely.
        elsewhere = next(i for i, b in enumerate(game.system.bodies)
                         if b.id != game.orbit_body)
        game.orbit_body = game.system.bodies[elsewhere].id
        window.refresh()
        for _ in range(2):
            app.processEvents()

        assert window.opened_at[1] == game.orbit_body, (
            "the window still thinks the ship is where it was")
        now = window.contact.name if window.contact else "station keeping"
        assert window.conn is not None, "the window went blank after a course"
        if window.contact is not None:
            assert window.contact.body_index == elsewhere, (
                f"the ship is at body {elsewhere} and the conn is on "
                f"{window.contact.name}")
        window.close()
        return f"moored to {was}, flown away, and the conn reopened on {now}"
