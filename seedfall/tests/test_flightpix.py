"""The flying windows as *pictures*: can the pilot read what is in front of them?

`tests/test_flightops.py` asks whether every control in these windows works.
These ask whether the window can be *read* — which is a different question,
and the reason all four defects below survived a green suite. Each was found
by flying a hull through the real interface and photographing the result:

- a finished approach thrown away by opening the conn, so the instruments
  read twelve kilometres from a quay the ship was moored to;
- two controls drawn in one grid cell, an unreadable smear of two labels
  with both of them clickable;
- an instrument value cut off mid-word by the column it sits in;
- a plot that wrote four names in the same place.

None of them stopped anything working, which is exactly why pressing every
button found none of them.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import anchorage as anchorage_sim
from ..sim import berthing as berth_sim
from ..sim import track as track_sim
from .harness import Suite
from .test_flightops import POPOUTS, _qt, _window

def run(suite: Suite) -> bool:
    """Claims about the flying windows as *pictures*, added after a deep
    play-test drove them by hand and photographed every instrument.

    Kept apart from `run` above because these ask a different question. That
    one asks whether every control *works*; these ask whether what the pilot
    is looking at can be read — which is how all four of the defects below
    survived a green suite for months.
    """
    check = suite.check
    app = _qt()
    from PyQt6.QtGui import QFontMetrics
    from PyQt6.QtWidgets import QLabel, QPushButton

    def _at_a_quay(seed: str):
        game = new_game(seed)
        places = anchorage_sim.in_system(game)
        if places:
            game.orbit_body = game.system.bodies[places[0].body_index].id
        game.recompute()
        win = _window(game)
        win.confirm = lambda *a, **k: True
        win.resize(1360, 880)
        win.show()
        quay = next((c for c in track_sim.contacts(game)
                     if c.kind == "anchorage"
                     and berth_sim.can_conn(game, c)[0]), None)
        if quay is None:
            return None, None
        win.conn = berth_sim.begin(game, quay)[0]
        return win, quay

    @check("a finished approach is not thrown away by opening the conn")
    def _():
        # Found by flying one: berthed at Fleet Hub, moored, `docked_at`
        # naming the berth — and opening the Conn window began a *fresh*
        # approach at the arrival range, so the instruments read 12,000 m
        # from a quay the ship was tied to. Precisely the fault that
        # window's own note says it exists to prevent.
        from ..ui.conn_window import open_conn
        from ..ui.flight_window import open_flight
        win, _quay = _at_a_quay("finished-conn")
        assert win is not None, "no quay to fly to in this sector"
        flight_win = open_flight(win)
        app.processEvents()
        for btn in flight_win.findChildren(QPushButton):
            if btn.isEnabled() and "close and berth" in btn.text().lower():
                btn.click()
                break
        app.processEvents()
        for _ in range(240):
            win.fly_beat()
        app.processEvents()
        done = win.game.conn
        assert done is not None and done.over, (
            "the computer never finished the approach, so this measures "
            "nothing")
        was_km = done.range_km
        open_conn(win)
        app.processEvents()
        assert win.game.conn is done, (
            f"opening the conn replaced the finished flight — "
            f"{was_km * 1000:,.0f} m became "
            f"{win.game.conn.range_km * 1000:,.0f} m")
        assert anchorage_sim.docked_at(win.game) is not None, (
            "and the ship is no longer berthed")
        return (f"berthed at {was_km * 1000:,.0f} m, and still berthed "
                f"after the conn was opened")

    @check("no two controls in a flying window are drawn on top of each other")
    def _():
        # The conn console put "Cut in" and the 100% throttle in one grid
        # cell: two labels drawn over each other into an unreadable smear,
        # both of them clickable. Every control *worked*, which is why
        # pressing them all found nothing.
        import importlib
        stacked = []
        for label, module_name, opener in POPOUTS:
            win, _quay = _at_a_quay(f"stack-{label}")
            if win is None:
                continue
            module = importlib.import_module(module_name, package=__package__)
            window = getattr(module, opener)(win)
            app.processEvents()
            app.processEvents()
            seen = {}
            for btn in window.findChildren(QPushButton):
                if not btn.isVisible():
                    continue
                spot = (btn.parent(), btn.geometry().x(), btn.geometry().y())
                seen.setdefault(spot, []).append(btn.text())
            for texts in seen.values():
                if len(texts) > 1:
                    stacked.append(f"{label}: {texts}")
        assert not stacked, f"controls sharing a place: {stacked}"
        return f"{len(POPOUTS)} windows, every control in a place of its own"

    @check("no instrument reading is clipped by the panel it sits in")
    def _():
        # "Computer — off — she flies as you fly her" was drawn unwrapped in
        # a fixed-width column and cut mid-word: the pilot read "she flies
        # as you f". A value either fits or wraps; it never gets shortened
        # without saying so.
        from ..ui.conn_window import open_conn
        win, _quay = _at_a_quay("clip-check")
        assert win is not None
        conn_win = open_conn(win)
        app.processEvents()
        app.processEvents()
        clipped = []
        for made in getattr(conn_win, "_side_made", []):
            if not isinstance(made, QLabel) or not made.text():
                continue
            if made.wordWrap():
                continue
            wanted = QFontMetrics(made.font()).horizontalAdvance(made.text())
            if wanted > made.width() + 1:
                clipped.append(f"{made.text()!r} wants {wanted}px in "
                               f"{made.width()}px")
        assert not clipped, f"readings cut off: {clipped}"
        return (f"{len(getattr(conn_win, '_side_made', []))} readings, none "
                f"cut off")

    @check("a crowded plot thins its names rather than piling them up")
    def _():
        # At the default zoom the inner system is a few pixels across, so a
        # star, its worlds, a quay and the ship all wrote their names in the
        # same place. The marks are always drawn; the names give way.
        from PyQt6.QtCore import QPointF
        from ..ui.plot_canvas import NAME_GAP, PlotCanvas
        canvas = PlotCanvas(new_game("plot-declutter"))
        canvas._named = []
        assert canvas._room_for(QPointF(100.0, 100.0)), "the first name was refused"
        assert not canvas._room_for(QPointF(100.0 + NAME_GAP / 2, 100.0)), (
            "a name was drawn on top of one already there")
        assert canvas._room_for(QPointF(100.0 + NAME_GAP + 2, 100.0)), (
            "a name with room of its own was refused")
        # A chosen mark is named whatever else is near it.
        assert canvas._room_for(QPointF(100.0, 100.0), chosen=True), (
            "the mark the player asked about was left unnamed")
        return f"names kept {NAME_GAP:.0f}px apart; a chosen mark always named"

    return True
