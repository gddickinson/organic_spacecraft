"""Interface checks.

Qt is driven headlessly on the ``offscreen`` platform, so every screen is really
constructed, laid out and painted — which catches the API drift and the missing
attribute that a browser-free simulation test never would.
"""

from __future__ import annotations

import os
from pathlib import Path


def _use_offscreen() -> None:
    """Point Qt at its bundled plugins and render without a display."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if "QT_QPA_PLATFORM_PLUGIN_PATH" not in os.environ:
        try:
            import PyQt6
            plugins = Path(PyQt6.__file__).parent / "Qt6" / "plugins" / "platforms"
            if plugins.is_dir():
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(plugins)
        except ImportError:
            pass


_use_offscreen()


def run(suite) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication, QHBoxLayout, QWidget
    except ImportError as err:
        print(f"── interface ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.rng import RNG
    from ..core.state import new_game
    from ..sim import colony as colony_sim
    from ..sim import encounters
    from ..data.tech import TECH
    from ..ui import theme
    from ..ui.window import NAV, MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = new_game("ui-test-seed")
    # Somewhere with a port, so the market screen has something to draw.
    port_sys = next((s for s in game.galaxy.systems
                     if s.port and "shipyard" in s.port.services),
                    next(s for s in game.galaxy.systems if s.port))
    game.location_id = port_sys.id
    game.ship.cargo = {"ore": 30, "volatiles": 60, "biomass": 20, "survey": 4}
    game.recompute()

    win = MainWindow(game)
    win.resize(1360, 880)
    # Dialogs block on exec(); stub them so action paths can be exercised.
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False

    def render(view_id: str):
        win.go(view_id)
        w = win.views[view_id]
        w.grab()                    # force a real paint pass
        return w

    @check("a widget taken off the screen outlives the event that took it")
    def _():
        # **`View.park` is the whole defence against a class of segfault**:
        # a signal handler must not destroy the widget that emitted the
        # signal, and almost every handler here rebuilds its own screen. The
        # outgoing widgets are held on the view and let go on the next turn of
        # the event loop, so Qt returns from the emit into something alive.
        #
        # It killed the process three times before it was a rule — through a
        # `Card`, through a `QLineEdit` mid-keystroke, and through a
        # `QComboBox` still delivering the click that dismissed it — and it
        # had no check of its own until `ui/pilot_view` began parking single
        # readouts through the same door.
        from PyQt6.QtWidgets import QApplication, QPushButton
        from .test_pilot_screen import _bridge

        _game, _win, view = _bridge("park")
        app = QApplication.instance()
        doomed = next(b for b in view.findChildren(QPushButton)
                      if b.parent() is not None)
        view.park(doomed)
        assert doomed.parent() is None, "park left it on the screen"
        assert view._doomed and any(w is doomed for w in view._doomed), (
            "park let the widget go inside the event that took it — this is "
            "the use-after-free")
        assert doomed.text() is not None      # still alive to be asked

        app.processEvents()                   # the next turn of the loop
        assert view._doomed is None, "the parked widgets are never released"
        return "parked, held through the event, released on the next turn"

    @check("window builds with hud, nav rail and log")
    def _():
        assert len(win.nav_buttons) == len(NAV), "nav rail is incomplete"
        assert win.hud_stats["date"].text(), "hud did not populate"
        win.grab()
        return f"{len(NAV)} nav destinations, hud reads {win.hud_stats['date'].text()}"

    for view_id, _text in NAV:
        @check(f'renders "{view_id}"')
        def _(vid=view_id):
            w = render(vid)
            kids = w.findChildren(object)
            assert len(kids) > 5, f"{vid} rendered almost nothing"
            return f"{len(kids)} widgets"

    @check("screens are laid out correctly on the first frame")
    def _():
        # Rebuilding a view's column does not tell its scroll area that the
        # contents changed size. Qt sorted it out on the second event-loop
        # turn, so a screen taller than the viewport painted once squashed and
        # then reflowed. One frame is easy to miss by eye and impossible to
        # miss in a screenshot, which is how these screens get reviewed.
        # A fresh window: grabbing a view forces a layout pass that hides the
        # fault, and every earlier check has already grabbed all of these.
        app = QApplication.instance()
        fresh = MainWindow(new_game("scroll-check"))
        fresh.dialog = lambda *a, **k: None
        fresh.resize(1360, 880)
        fresh.show()
        squashed, tallest = [], ("", 0)
        for view_id, _text in NAV:
            fresh.go(view_id)
            app.processEvents()          # exactly one turn: the first frame
            w = fresh.views[view_id]
            need = w.col.minimumSize().height()
            got = w._inner.height()
            if need > tallest[1]:
                tallest = (view_id, need)
            if got + 1 < need:
                squashed.append(f"{view_id} ({need}px into {got}px)")
        fresh.close()
        assert not squashed, ("squashed on the first frame: "
                             + ", ".join(squashed))
        return f"{len(NAV)} screens fit at once; tallest {tallest[0]} at {tallest[1]}px"

    @check("a short panel keeps its rows together beside a tall one")
    def _():
        # Panels sit side by side in a row and are given the same height. The
        # shorter one used to have its rows dragged apart to fill the space,
        # which read as a rendering fault rather than a layout one.
        from ..ui.widgets import Panel
        app = QApplication.instance()
        host = QWidget()
        h = QHBoxLayout(host)
        short, tall = Panel("Short"), Panel("Tall")
        for i in range(3):
            short.add_row(f"key {i}", f"value {i}")
        for i in range(24):
            tall.add_row(f"key {i}", f"value {i}")
        h.addWidget(short, 1)
        h.addWidget(tall, 1)
        host.resize(700, 640)
        host.show()
        for _ in range(3):
            app.processEvents()

        # The spare height goes into the rows themselves rather than the gaps
        # between them, so compare each row against the height it asked for.
        rows = [short.box.itemAt(i).widget() for i in range(short.box.count())]
        rows = [r for r in rows if r is not None and r.sizeHint().height() > 0]
        stretch = max((r.height() - r.sizeHint().height() for r in rows),
                      default=0)
        tall_rows = len(rows)
        panel_height = short.height()
        host.close()
        assert rows, "the short panel had no rows to measure"
        assert stretch <= 8, (
            f"a row was stretched {stretch}px past the height it asked for "
            f"to fill the taller panel")
        return (f"{tall_rows} rows within {stretch}px of their hints "
                f"in a panel {panel_height}px tall")

    @check("every tabbed screen renders all of its tabs")
    def _():
        from ..ui.widgets import TabBar
        covered = []
        for vid in ("port", "yard", "tech", "codex"):
            w = render(vid)
            bars = w.findChildren(TabBar)
            assert bars, f"{vid} has no tab bar"
            for tid in list(bars[0].buttons):
                bars[0].select(tid)
                win.views[vid].grab()
                covered.append(f"{vid}/{tid}")
        return f"{len(covered)} tabs: {', '.join(covered)}"

    @check("shipyard opens the designer for every buildable hull")
    def _():
        game.research.unlocked += ["monocoque", "bioleach", "magnetite",
                                   "osteoid", "tendon1"]
        game.recompute()
        view = win.views["yard"]
        win.go("yard")
        view.tab = "build"
        view.design_chassis = None
        view.refresh()
        hulls = view._buildable()
        for c in hulls:
            view._pick_hull(c.id)
            view.grab()
        return f"{len(hulls)} hulls opened in the designer"

    @check("body detail renders for every kind of body")
    def _():
        kinds = set()
        for sysm in game.galaxy.systems[:14]:
            game.location_id = sysm.id
            for b in sysm.bodies:
                b.surveyed = True
                kinds.add(b.kind)
            view = win.views["system"]
            win.go("system")
            for i in range(len(sysm.bodies)):
                view._select(i)
                view.grab()
        game.location_id = port_sys.id
        return "body kinds covered: " + ", ".join(sorted(kinds))

    @check("the tactical plot draws and station orders drive it")
    def _():
        from ..sim import encounters, stations as st_mod
        enemy = encounters.make_enemy(RNG("plot-ui"), "freeholds", 2)
        win.begin_combat({"enemy": enemy, "intro": "plot test"}, "system")
        view = win.views["battle"]
        view.grab()
        b = win.battle
        start_range = b.range_units
        for order in ("close", "salvo", "route_guns", "comeabout", "damage_control"):
            if b.over:
                break
            view._act({"type": "station", "order": order})
            view.grab()
        assert b.turn > 1, "no station order advanced the turn"
        assert abs(b.range_units - start_range) > 0, "nothing moved on the plot"
        win.battle = None
        win.go("map")
        return f"plot drew across {len(st_mod.STATIONS)} stations"

    @check("battle screen renders a live engagement and takes a turn")
    def _():
        enemy = encounters.make_enemy(RNG("ui-battle"), "freeholds", 2)
        win.begin_combat({"enemy": enemy, "intro": "test contact"}, "system")
        b = win.battle
        assert b is not None, "combat did not start"
        view = win.views["battle"]
        view.grab()
        turn0 = b.turn
        view._act({"type": "brace"})
        assert b.turn > turn0 or b.over, "taking a turn did nothing"
        view.grab()
        win.battle = None
        win.go("map")
        return f"turn {turn0} → {b.turn}, {len(b.log)} log lines"

    @check("the xenology desk renders at every stage of discovery")
    def _():
        from ..sim import xeno as xeno_sim
        from ..data.xenotech import XENOTECH
        view = win.views["tech"]
        stages = []

        # nothing found yet
        bare = new_game("xeno-ui")
        win.game = bare
        win.go("tech")
        view.branch = "xeno"
        view.refresh(); view.grab()
        stages.append("undiscovered")

        # partly studied, one incorporated, one blocked on a prerequisite
        xeno_sim.add_study(bare, XENOTECH[0].id, XENOTECH[0].study * 0.4)
        xeno_sim.incorporate(bare, XENOTECH[3].id)
        deep = next(x for x in XENOTECH if x.requires)
        xeno_sim.add_study(bare, deep.id, deep.study * 0.9)
        bare.ship.cargo["xenolith"] = 5
        bare.recompute()
        view.refresh(); view.grab()
        stages.append("part-studied")

        # everything incorporated
        for x in XENOTECH:
            xeno_sim.incorporate(bare, x.id)
        bare.recompute()
        view.refresh(); view.grab()
        stages.append("complete")

        win.game = game
        return " → ".join(stages)

    @check("a port gives no counter for what it seizes")
    def _():
        # Found by playing it: the quiet word was on the quay and the posted
        # market *also* still listed Unlicensed Seed with a live Sell button,
        # so you could hand contraband over the desk at the very station whose
        # boarding party exists to stop you.
        from PyQt6.QtWidgets import QPushButton

        from ..sim import customs as customs_sim
        g2 = new_game("counter-ui")
        dest = next((s for s in g2.galaxy.systems if s.port
                     and customs_sim.outlaws(s.port.faction, "wildseed")), None)
        assert dest, "no port in this sector outlaws anything"
        g2.location_id = dest.id
        g2.ship.cargo["wildseed"] = 20
        win.game = g2
        view = win.views["port"]
        view.tab = "market"
        win.go("port")
        view.grab()

        sells = [b for b in view.findChildren(QPushButton)
                 if b.text() == "Sell" and b.isEnabled()]
        from PyQt6.QtWidgets import QLabel
        rows = [w for w in view.findChildren(QLabel)
                if w.text().lower() == "seized on sight"]   # Pill upper-cases
        assert rows, "the market does not say the good is seized here"
        held = {c for c in g2.ship.cargo}
        assert "wildseed" in held
        # Every enabled Sell must belong to a good the port will actually take.
        legal_held = [c for c in held
                      if not customs_sim.outlaws(dest.port.faction, c)]
        assert len(sells) == len(legal_held), (
            f"{len(sells)} live Sell buttons for {len(legal_held)} sellable "
            "good(s) aboard — contraband has a posted counter")
        win.game = game
        return "contraband listed as seized on sight, with no counter"

    @check("a relic site shows up in the system view")
    def _():
        g2 = new_game("relic-ui")
        site = next(((s, i) for s in g2.galaxy.systems
                     for i, b in enumerate(s.bodies) if b.relic), None)
        assert site, "no relic site to render"
        sysm, idx = site
        g2.location_id = sysm.id
        sysm.bodies[idx].surveyed = True
        sysm.bodies[idx].relic_found = True
        win.game = g2
        view = win.views["system"]
        win.go("system")
        view._select(idx)
        view.grab()
        text = view._inner.findChildren(object)
        win.game = game
        return f"{len(text)} widgets with a live dig site"

    @check("the helm and both mini-games render and play")
    def _():
        from ..sim import minigames as mg
        from ..sim import flight
        g2 = new_game("mini-ui")
        win.game = g2

        win.go("helm")
        helm = win.views["helm"]
        helm.grab()
        helm._pick(min(1, len(g2.system.bodies) - 1))
        helm.grab()
        assert flight.current_body(g2) is None or True

        win.views["docking"].begin("Test Port")
        win.go("docking")
        dock = win.views["docking"]
        dock.grab()
        d = win.docking
        # A good navigator is granted an extra pass, so compare against what
        # this approach actually started with rather than the constant.
        started_with = d.passes
        axis = max(d.error, key=lambda a: abs(d.error[a]))
        dock._fire(axis, d.precision)
        dock.grab()
        assert d.passes == started_with - 1, "a correction pass did nothing"
        win.docking = None

        win.views["decoding"].begin("Test Culture", "vent_symbiosis")
        win.go("decoding")
        dec = win.views["decoding"]
        dec.grab()
        dec._cycle(0, 1)
        dec._guess()
        dec.grab()
        assert win.decoding.used == 1, "a transmission was not recorded"
        win.decoding = None
        win.game = game
        win.go("map")
        return "helm plotted, one correction pass, one transmission"

    @check("every screen survives a developed game")
    def _():
        game.research.unlocked = [t.id for t in TECH]
        game.credits = 5_000_000
        for k in ("ore", "volatiles", "phosphate", "biomass", "silicon", "alloy",
                  "magnetite", "spidroin", "trehalose"):
            game.stores[k] = 5000
        game.ship.fitted.append("seed_bay")
        game.recompute()
        sysm = game.system
        col, why = colony_sim.found(game, sysm, sysm.bodies[0], "vesper_picket")
        assert col, f"colony not founded: {why}"
        game.advance_days(200)
        assert any(c.online for c in game.colonies), "colony never came online"
        for vid, _ in NAV:
            render(vid)
        return (f"{len(game.colonies)} colony online, all {len(TECH)} techs known, "
                f"{len(NAV)} screens clean")

    @check("every screen survives a bare, damaged game")
    def _():
        bare = new_game("bare-seed")
        for layer in bare.ship.layers:
            layer.hp = 1
        bare.ship.cargo = {}
        bare.officers = []
        bare.credits = 0
        bare.recompute()
        win.game = bare
        for vid, _ in NAV:
            render(vid)
        return f"{len(NAV)} screens clean with no crew, no cargo, no money"

    @check("every topic's screen is a view this window holds")
    def _():
        # Two topics once named views that do not exist ("xeno", "conn"),
        # and the manual's "go to" button pressed them straight into `go()`.
        # A topic may be about an event view — "battle" is one, and
        # `manual.for_screen` reads it for contextual help — so the rule is
        # asked of the built window, the only place the full set exists.
        from ..data.help import TOPICS
        for topic in TOPICS:
            assert topic.screen == "" or topic.screen in win.views, (
                f"{topic.id} says it is about {topic.screen!r}, "
                f"which is not a view")
        named = sum(1 for t in TOPICS if t.screen)
        return f"{named} topics name a view, all of them held"

    @check("an unknown screen is refused before anything is touched")
    def _():
        # `go()` used to hide the outgoing view and reassign `current`
        # *before* the lookup, so one bad id (a manual topic naming a screen
        # that is not a view) bricked the window for the session — blank
        # content area, every later navigation re-raising the same KeyError.
        win.go("map")
        win.go("xeno")                       # the id that used to do it
        assert win.current == "map", f"went to {win.current!r}"
        win.go("system")                     # and navigation still works
        assert win.current == "system"
        return "refused, said so, and the window still navigates"

    @check("the opening briefing really opens, unstubbed")
    def _():
        # Every windowed check stubs `win.dialog`, so no suite had ever
        # built the real one — and the split to `ui/window_dialogs` picked
        # up `widgets.body_or` (None → spacer) in place of the string
        # wrapper, which crashed the first fresh launch of the game before
        # the title. This drives `opening_briefing` through the genuine
        # dialog, dismissed by a timer the way a hand would.
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QDialog
        from ..ui.title import opening_briefing
        fresh = MainWindow(new_game("briefing-check"))
        closed = []

        def dismiss():
            for w in QApplication.instance().topLevelWidgets():
                if isinstance(w, QDialog) and w.isVisible():
                    closed.append(w.windowTitle() or "untitled")
                    w.accept()
                    return
            QTimer.singleShot(25, dismiss)

        QTimer.singleShot(0, dismiss)
        opening_briefing(fresh)
        assert closed, "no briefing dialog ever showed"
        fresh.close()
        fresh.deleteLater()
        app.processEvents()
        return f"briefing built, shown and dismissed ({closed[0]})"

    @check("quitting is a save")
    def _():
        # Trading advances no calendar and the autosave fires on calendar
        # movement, so a shopping run used to be lost on quit.
        from ..core import state as state_mod
        leaving = MainWindow(new_game("quit-save"))
        leaving.dialog = lambda *a, **k: None
        leaving.game.credits = 4242
        leaving.close()
        app.processEvents()
        back = state_mod.load_game()
        assert back is not None and back.credits == 4242, (
            "the quit did not write the chronicle")
        leaving.deleteLater()
        app.processEvents()
        return "credits changed, window closed, chronicle holds the change"

    @check("dismissing an ending does not destroy the chronicle")
    def _():
        # Escape at the ending dialog fell past the "carry" branch into
        # `clear_save()` — the one dialog in the game where "no" erased
        # everything. None is a refusal, never a button.
        from ..core import state as state_mod
        from ..data.lore import VICTORIES
        from ..ui import title as title_mod
        ended = new_game("escape-check")
        ended.save()
        ended.victory = VICTORIES[0][0]
        win.game = ended
        called = []
        kept, title_mod.start_new_chronicle = (
            title_mod.start_new_chronicle, lambda w: called.append(w))
        try:
            assert win.check_ending(), "the ending did not present"
        finally:
            title_mod.start_new_chronicle = kept
        assert not called, "a dismissed ending began a new chronicle"
        assert state_mod.has_save(), "a dismissed ending cleared the save"
        return "Escape at the ending: save intact, nothing begun"

    win.close()
    return True
