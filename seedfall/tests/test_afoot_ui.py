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

    @check("fire, weight and the latest word are on the screen, and a friend down can be left")
    def _():
        from types import SimpleNamespace as NS
        from PyQt6.QtWidgets import QLabel, QPushButton, QWidget
        from ..sim import afoot, afoot_fight, afoot_map
        from ..sim.afoot_state import Actor, party
        from ..ui.afoot_marks import tokens
        from ..ui.afoot_view import weight_name
        app, game, win, view = _window("afoot-ui-fire")
        walk = _begin(app, game, view, keys=afoot_kit.everybody(game)[:2])
        me, mate = party(walk)[:2]
        marks = tokens(walk)
        assert len(marks[me.id]) == 2 and marks[me.id] != marks[mate.id]
        me.weapon, me.kit = "carbine", me.kit + ["frag_grenade"]
        g = afoot_map.ground(walk, me.deck)
        taken = {(a.x, a.y) for a in walk.actors if a.deck == me.deck}
        spot = next(sq for sq in sorted(afoot.visible(walk, me.deck))
                    if 2 <= afoot_map.distance(me.x, me.y, *sq) <= 4
                    and g.passable(*sq) and sq not in taken
                    and afoot_map.sees(walk, me.deck, me.x, me.y, *sq))
        foe = Actor(id=9900, name="Raider", side="npc", folk="raider",
                    deck=me.deck, x=spot[0], y=spot[1], hp=60, hp_max=60,
                    mood="hostile", weapon="carbine",
                    stats={k: 7 for k in ("str", "dex", "end", "int", "edu",
                                          "soc")})
        walk.actors.append(foe)
        walk.version += 1
        luck = game.rng_seed
        view.refresh()
        _pump(app)
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        for name in (f"afoot_burst_{foe.id}", f"afoot_suppress_{foe.id}",
                     f"afoot_throw_frag_grenade_{foe.id}"):
            assert name in named and named[name].isEnabled(), name
        assert game.rng_seed == luck, "drawing the buttons rolled"
        texts = [l.text().lower() for l in view.findChildren(QLabel)]
        assert weight_name(walk.decks[walk.viewing]) in texts, texts[:12]
        assert (weight_name(NS(g=0.8, wrap=True)),
                weight_name(NS(g=0.0, wrap=False))) == (
            "0.8 g · spun", "weightless")
        named[f"afoot_suppress_{foe.id}"].click()
        _pump(app, 6)
        assert foe.pinned == 1, foe.pinned
        side = view.findChild(QWidget, "afoot_side")
        said = [l.text() for l in side.findChildren(QLabel)]
        assert any("pinned" in t for t in said[:12]), said[:12]
        afoot_fight.hurt(game, walk, mate, mate.hp + 2)
        view.pick(mate.id)
        _pump(app, 6)
        hand = view.findChild(QPushButton, f"afoot_hand_to_{me.id}")
        assert hand is not None, "no way to take anybody else in hand"
        hand.click()
        _pump(app, 6)
        assert walk.selected == me.id, walk.selected
        assert not _clipped(view), _clipped(view)
        return (f"burst, suppress and a throw offered; “{marks[me.id]}” on "
                f"the deck; {weight_name(walk.decks[walk.viewing])} in the "
                "head; the pin in the latest lines; the one down left for "
                "the one standing")

    @check("a ring's level has no ends: the party stays in the middle and an arrow walks on round")
    def _():
        from PyQt6.QtCore import QPoint, Qt
        from PyQt6.QtTest import QTest
        from ..core.state import new_game
        from ..sim import afoot, afoot_sites
        from ..sim.afoot_state import party
        app = qtkit.app()
        game = new_game("afoot-ui-ring")
        object.__setattr__(game.system.port, "capital", True)   # a Fleet Hub
        win = qtkit.main_window(game, SIZE)
        win.show()
        win.go("afoot")
        _pump(app)
        view = win.views["afoot"]
        port = next(s for s in afoot_sites.here(game) if s.kind == "port")
        view.site_key, view.keys = port.key, ["captain"]
        view.go_afoot()
        _pump(app)
        walk = game.afoot
        ring = next(i for i, d in enumerate(walk.decks) if d.wrap)
        wide = walk.decks[ring].w
        me = party(walk)[0]
        me.deck, me.x, me.y, walk.viewing = ring, wide - 1, 6, ring
        afoot.look(walk)
        view.refresh()
        _pump(app)
        canvas = view.canvas
        tile, x0, y0 = canvas.frame()
        middle = QPoint(int(x0 + (wide // 2 + 0.5) * tile),
                        int(y0 + (me.y + 0.5) * tile))
        assert canvas.square_at(middle.x(), middle.y()) == (me.x, me.y), (
            canvas.square_at(middle.x(), middle.y()), (me.x, me.y))
        canvas.setFocus()
        QTest.keyClick(canvas, Qt.Key.Key_Right)
        _pump(app)
        assert me.x == 0, f"stopped at the end of the strip: {me.x}"
        canvas = view.canvas
        tile, x0, y0 = canvas.frame()
        # Still in the middle, and the square a click there names is theirs.
        assert canvas.square_at(int(x0 + (wide // 2 + 0.5) * tile),
                                int(y0 + (me.y + 0.5) * tile)) == (0, me.y)
        QTest.mouseClick(canvas, Qt.MouseButton.LeftButton,
                         Qt.KeyboardModifier.NoModifier,
                         QPoint(int(x0 + (wide // 2 - 2.5) * tile),
                                int(y0 + (me.y + 0.5) * tile)))
        _pump(app)
        assert me.x == wide - 3, f"a click back across the seam: {me.x}"
        return (f"off the end at column {wide - 1} onto column 0 with an "
                f"arrow, and clicked back across to {wide - 3}; the one in "
                "hand stayed in the middle")

    @check("getting across is on the screen: the start page's way is taken, the Concourse crosses")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..sim import crossing, flight, places
        from .test_crossing import _at_hub_with_station, _neighbour
        app = qtkit.app()
        game = _at_hub_with_station()
        station = _neighbour(game)
        win = qtkit.main_window(game, SIZE)
        win.show()
        win.go("afoot")
        _pump(app)
        view = win.views["afoot"]
        view.pick_site(f"place:{station.id}")
        _pump(app)
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        assert named["afoot_across_boat"].isEnabled()
        assert not named["afoot_across_suits"].isEnabled()
        named["afoot_across_shuttle"].click()
        _pump(app)
        assert view.across == "shuttle"
        cash = game.credits
        view.findChild(QPushButton, "afoot_go").click()
        _pump(app, 6)
        assert game.afoot is not None and game.credits < cash
        assert game.ashore == station.id
        game.afoot = None
        # The Concourse at a place the crew is not across to crosses.
        flight.hold_at(game, flight.current_body(game))
        hub = next(p for p in places.here(game) if p.kind == "port")
        win.go("concourse")
        con = win.views["concourse"]
        con.go_place(hub.id)
        _pump(app)
        dock = con.findChild(QPushButton, "concourse_across_dock")
        assert dock is not None and dock.isEnabled(), "no way to come alongside"
        dock.click()
        _pump(app, 6)
        assert game.berth == hub.id and crossing.across(game, hub)
        assert con.findChild(QPushButton, "concourse_across_dock") is None
        assert not _clipped(view)
        return (f"shuttled to {station.name} from the start page; came "
                f"alongside {hub.name} from its Concourse")

    return True
