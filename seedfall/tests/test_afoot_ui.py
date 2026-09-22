"""Afoot, on the screen: pressed the way a player presses it.

- **It paints**, on the start page and on a deck, at the smallest window the
  game allows, with nothing clipped out of its column and no frame lost.
- **A click walks.** A square pressed on the canvas moves the one in hand
  there; an arrow key steps; Space ends the turn.
- **A counter sells.** Walking up to a keeper, talking, doing business and
  pressing a shelf's button spends exactly the shelf's price and puts the
  thing in the captain's keeping.
- **The walk holds the window**, as a landing party does — but a quay's
  own counters stay open to a party standing on the quay.
- **Leaving comes back to the start page**, with what the walk came to.
- **Looking at the deck moves no dice.**
"""

from __future__ import annotations

from .harness import Suite
from . import afoot_kit, qtkit

SIZE = (1040, 680)


def _pump(app, n: int = 4) -> None:
    for _i in range(n):
        app.processEvents()


def _window(seed: str, credits: float = 50_000):
    app = qtkit.app()
    game = afoot_kit.fresh(seed)
    game.credits = credits
    win = qtkit.main_window(game, SIZE)
    win.show()
    win.go("afoot")
    _pump(app)
    return app, game, win, win.views["afoot"]


def _begin(app, game, view, kind: str = "port", keys=None):
    from ..sim import afoot
    site = next(s for s in afoot.sites(game) if s.kind == kind)
    view.site_key = site.key
    view.keys = list(keys or ["captain"])
    view.go_afoot()
    _pump(app)
    return game.afoot


def _clipped(view) -> list:
    """Buttons wider than the column they sit in."""
    from PyQt6.QtWidgets import QPushButton
    out = []
    for b in view.findChildren(QPushButton):
        if not b.isVisible():
            continue
        parent = b.parentWidget()
        while parent is not None and parent.objectName() != "afoot_side" \
                and parent is not view:
            parent = parent.parentWidget()
        if parent is None:
            continue
        right = b.mapTo(parent, b.rect().topRight()).x()
        if right > parent.width() + 2:
            out.append((b.text(), right, parent.width()))
    return out


def run(suite: Suite) -> bool:
    """An optional (Qt) suite: True says it ran (`tests/runner._run_here`)."""
    check = suite.check

    @check("the screen paints, start page and deck, at the smallest window")
    def _():
        from ..ui import painting
        app, game, win, view = _window("afoot-ui-paint")
        before = len(painting.MISSES)
        view.grab()
        assert not _clipped(view), _clipped(view)
        walk = _begin(app, game, view, keys=afoot_kit.everybody(game)[:2])
        assert walk is not None and view.canvas is not None
        _pump(app)
        view.grab()
        assert view.canvas.width() >= 300, view.canvas.width()
        assert len(painting.MISSES) == before, painting.MISSES[before:]
        assert not _clipped(view), _clipped(view)
        return (f"canvas {view.canvas.width()}×{view.canvas.height()} at "
                f"{SIZE[0]}×{SIZE[1]}; nothing clipped, nothing missed")

    @check("a click on the deck walks the one in hand there, and a key steps")
    def _():
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from ..sim import afoot_map
        from ..sim.afoot_state import party
        app, game, win, view = _window("afoot-ui-click")
        walk = _begin(app, game, view)
        me = party(walk)[0]
        goal = max(afoot_map.reach(walk, me, 5).items(),
                   key=lambda kv: kv[1])[0]
        tile, x0, y0 = view.canvas.frame()
        point = QPoint(int(x0 + (goal[0] + 0.5) * tile),
                       int(y0 + (goal[1] + 0.5) * tile))
        QTest.mouseClick(view.canvas, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier, point)
        _pump(app)
        assert (me.x, me.y) == goal, ((me.x, me.y), goal)
        was = (me.x, me.y)
        view.canvas.setFocus()
        for key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up,
                    Qt.Key.Key_Down):
            QTest.keyClick(view.canvas, key)
            _pump(app, 2)
            if (me.x, me.y) != was:
                break
        assert (me.x, me.y) != was, "no arrow key moved anybody"
        rounds = walk.round
        QTest.keyClick(view.canvas, Qt.Key.Key_Space)
        _pump(app)
        assert walk.round == rounds + 1, (rounds, walk.round)
        return f"clicked to {goal}; an arrow stepped; Space ended the round"

    @check("walking up to a keeper and buying across the counter costs the shelf price")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..sim import afoot, afoot_map, places, shore
        from ..sim.afoot_state import party
        app, game, win, view = _window("afoot-ui-shop")
        walk = _begin(app, game, view)
        me = party(walk)[0]
        keeper = next((a for a in walk.actors if a.folk == "keeper" and any(
            r.id == a.room and r.kind == "chandler" for r in walk.rooms)),
            None)
        assert keeper is not None, "no chandler on this quay"
        g = afoot_map.ground(walk, keeper.deck)
        spot = next(s for s in ((keeper.x + dx, keeper.y + dy)
                                for dx in (-2, -1, 0, 1, 2)
                                for dy in (-2, 2, -1, 1))
                    if g.passable(*s) and afoot_map.sees(
                        walk, keeper.deck, *s, keeper.x, keeper.y))
        me.deck, (me.x, me.y) = keeper.deck, spot
        afoot.view_deck(game, keeper.deck)
        view.talk_to(keeper.id)
        _pump(app)
        view.say("business")
        _pump(app)
        buys = [b for b in view.findChildren(QPushButton)
                if b.objectName().startswith("afoot_buy_") and b.isEnabled()]
        assert buys, "the counter had nothing to sell"
        item_id = buys[0].objectName().removeprefix("afoot_buy_")
        place = places.by_id(game, walk.place_id)
        price = next(r["cr"] for r in shore.shelves(game, place)
                     if r["item"].id == item_id)
        was = game.credits
        buys[0].click()
        _pump(app)
        assert item_id in game.kit, (item_id, game.kit)
        assert abs((was - game.credits) - price) < 0.01, (was, game.credits,
                                                          price)
        return f"bought {item_id} for {price} cr, exactly"

    @check("a walk holds the window, but leaves the quay's own counters open")
    def _():
        app, game, win, view = _window("afoot-ui-lock")
        _begin(app, game, view)
        win.go("map")
        _pump(app)
        assert win.current == "afoot", win.current
        win.go("concourse")
        _pump(app)
        assert win.current == "concourse", win.current
        win.go("afoot")
        _pump(app)
        assert win.current == "afoot"
        return "the chart refused; the concourse opened; back to the deck"

    @check("leaving through the screen comes back to the start page, with the walk's end")
    def _():
        from PyQt6.QtWidgets import QLabel
        from ..sim import afoot_acts
        from ..sim.afoot_state import party
        app, game, win, view = _window("afoot-ui-leave")
        walk = _begin(app, game, view, kind="ship")
        me = party(walk)[0]
        leave = next(a for a in afoot_acts.offer(game, walk, me)
                     if a.id == "leave")
        view.do_act(leave)
        _pump(app, 6)
        assert game.afoot is None, "still out"
        assert view.canvas is None
        texts = " ".join(l.text() for l in view.findChildren(QLabel))
        assert "The last walk" in texts, texts[:300]
        return "the start page is back, with the last walk on it"

    @check("painting the deck and hovering over it move no dice")
    def _():
        app, game, win, view = _window("afoot-ui-look")
        _begin(app, game, view, keys=afoot_kit.everybody(game)[:2])
        before = game.rng_seed
        canvas = view.canvas
        for x in range(0, canvas.width(), 37):
            for y in range(0, canvas.height(), 41):
                canvas.hover = canvas.square_at(x, y)
                canvas.grab()
        assert game.rng_seed == before, "looking moved the chronicle's luck"
        return "every square hovered and painted; not one die spent"

    return True
