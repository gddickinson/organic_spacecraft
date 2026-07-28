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
        from PyQt6.QtWidgets import QApplication
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

    win.close()
    return True
