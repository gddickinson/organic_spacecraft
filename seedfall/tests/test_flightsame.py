"""The flying windows say one thing one way, and fly the ship once a beat.

Three screens fly the one `game.conn` — the bridge, the conn window and the
flight controls — and the review that opened this file found them disagreeing
about everything that was the same:

- **three thrust pads, three layouts** — a row of six, and two grids of which
  only one printed what a press would do;
- **the tank three ways** — "19.4" with no unit, "19.42 t", "19 t";
- **the computer twice** on the bridge, one row apart, in two sets of words;
- **"Kill relative motion"** flying a minute of its own outside the one clock;
- **the conn's side panel** wrapping "100% — 2.65 m/s" onto two lines.

And the cameras flew the ship too: the heads-up path is a 48-tick dry run, and
all seven feeds on the Conn window flew it inside their own `paintEvent` —
measured at 143 ms of every 250 ms beat, thirteen dry runs a beat.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()


def run(suite) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication, QLabel
    except ImportError as err:
        print(f"── flying windows ───\n  skipped: PyQt6 not available "
              f"({err})\n")
        return False

    from ..core.state import new_game
    from ..core.util import reaction_mass
    from ..sim import anchorage as anchorage_sim
    from ..sim import conn as conn_sim
    from ..sim import instruments as panel_sim
    from ..ui import theme, viewport_hud
    from ..ui.conn_window import open_conn
    from ..ui.flight_window import open_flight
    from ..ui.thrust_pad import LAYOUT, ThrustPad
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = new_game("same-seed")
    places = anchorage_sim.in_system(game)
    assert places, "the fixture seed has no quay to fly at"
    game.orbit_body = game.system.bodies[places[0].body_index].id
    win = MainWindow(game)
    win.resize(1360, 880)
    win.toast = lambda *a, **k: None
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    win.show()
    conn_win = open_conn(win)
    conn_win.resize(1080, 760)
    panel = open_flight(win)
    for _ in range(4):
        app.processEvents()

    def feeds():
        return list(conn_win.feeds.values()) + [conn_win.screen]

    @check("seven cameras in one beat fly the path once, not seven times")
    def _():
        conn_win._auto("close")
        runs = []
        for _ in range(3):
            before = viewport_hud.FLOWN[0]
            win.fly_beat()
            for feed in feeds():
                feed.repaint()
            runs.append(viewport_hud.FLOWN[0] - before)
        assert runs == [1, 1, 1], f"dry runs per beat of seven feeds: {runs}"
        # With the clock held, a repaint flies nothing at all.
        before = viewport_hud.FLOWN[0]
        for feed in feeds():
            feed.repaint()
        assert viewport_hud.FLOWN[0] == before, "a repaint flew the ship"
        win.set_conn_clock(False)
        return f"{len(feeds())} feeds, 1 dry run a beat, none on a repaint"

    @check("the remembered path is the path, and a change of mode is seen")
    def _():
        conn = win.conn
        kept = viewport_hud.world(conn)
        viewport_hud._LAST[0] = None            # forget, and fly it fresh
        fresh = viewport_hud.world(conn)
        assert kept["path"] == fresh["path"], "the cache drew a stale path"
        # Arming the computer passes no tick, and must still redraw the line.
        before = viewport_hud.FLOWN[0]
        conn.auto = "null" if conn.auto != "null" else "brake"
        viewport_hud.world(conn)
        assert viewport_hud.FLOWN[0] == before + 1, (
            "a new mode drew the old mode's path")
        conn.auto = ""
        return f"{len(fresh['path'])} points, identical either way"

    @check("one thrust pad on every flying screen, saying the same thing")
    def _():
        win.go("pilot")
        for _ in range(3):
            app.processEvents()
        bridge = win.views["pilot"]
        pads = {"bridge": bridge._pad, "conn": conn_win.controls.pad,
                "flight": panel.pad}
        for name, pad in pads.items():
            assert isinstance(pad, ThrustPad), f"the {name} has its own pad"
        conn_win.refresh()
        panel.refresh()
        bridge.refresh()
        where = {}
        for name, pad in pads.items():
            grid = pad.layout()
            where[name] = tuple(
                (btn.objectName(), grid.getItemPosition(grid.indexOf(btn))[:2])
                for btn in pad.buttons.values())
            said = {b.objectName(): b.text() for b in pad.buttons.values()}
            where[name + ":text"] = tuple(sorted(said.items()))
        assert where["bridge"] == where["conn"] == where["flight"], where
        assert (where["bridge:text"] == where["conn:text"]
                == where["flight:text"]), "three pads, three promises"
        wanted = tuple((f"thr_{a}", (r, c)) for a, r, c in LAYOUT)
        assert where["bridge"] == wanted, where["bridge"]
        return "bridge, conn and flight controls: one layout, one label"

    @check("the tank reads one way, and the computer is said once")
    def _():
        bridge = win.views["pilot"]
        conn = win.conn
        want = reaction_mass(conn.rcs)
        rows = {k: v for k, v, _t in panel_sim.readout(conn)}
        assert rows.get("Reaction mass") == want, rows
        assert "Thruster mass" not in rows, sorted(rows)
        dials = [lab.text() for lab in panel.dials.findChildren(QLabel)]
        assert any(t.startswith("Reaction mass") and t.endswith(want)
                   for t in dials), dials
        board = [lab.text() for lab
                 in bridge._boards["ship"].findChildren(QLabel)]
        assert "Autopilot" not in board, (
            "the bridge says who has the conn twice")
        assert board.count("Computer") == 1, board
        return f"Reaction mass {want} on the panel, the controls and the bridge"

    @check("Kill relative motion is one tick through the clock's door")
    def _():
        conn = win.conn
        win.set_conn_clock(False)
        conn.auto = ""
        before = conn.elapsed
        panel._null()
        assert abs(conn.elapsed - before - conn_sim.TICK) < 1e-6, (
            f"held clock: {conn.elapsed - before:.0f} s flown, not one tick")
        # With the clock running the beat flies every minute; the press
        # hands the computer the null rather than flying one of its own.
        win.set_conn_clock(True)
        before = conn.elapsed
        panel._null()
        assert conn.elapsed == before, "a minute flown between beats"
        assert conn.auto == "null", conn.auto
        win.set_conn_clock(False)
        conn.auto = ""
        return "one tick held; armed, not flown, with the clock running"

    @check("a reading on the conn's side panel stays on one line")
    def _():
        conn_win.show()
        conn_win.refresh()
        for _ in range(4):
            app.processEvents()
        from ..ui import conn_panel
        said = conn_panel.content(conn_win, win.conn)
        rows = [made for entry, made in zip(said, conn_win._side_made)
                if entry[0] == "row"]
        assert rows, "the side panel shows no readings"
        line = max(lab.fontMetrics().lineSpacing() for lab in rows)
        tall = {lab.text(): lab.height() for lab in rows
                if lab.text() and lab.height() > line * 1.5
                and len(lab.text()) <= 24}
        assert not tall, f"short readings wrapped: {tall}"
        return f"{len(rows)} readings, none under 25 characters wrapped"

    panel.close()
    conn_win.close()
    win.close()
    return True
