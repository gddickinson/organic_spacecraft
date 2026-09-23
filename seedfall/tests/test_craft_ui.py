"""The cradle and the cockpit, on the screen.

The Ship screen's Cradle tab launches a craft with a named pilot, and the
cockpit window (`ui/craft_window.py`) flies her: the stick, the drive, the
computer's modes, a firing run, and the way back to the cradle. Optional,
like every Qt suite — `tests/runner._run_here` reads the `True`.
"""

from __future__ import annotations


def run(suite) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication, QPushButton  # noqa: F401
    except ImportError as err:
        print(f"── the cockpit ───\n  skipped: PyQt6 not available ({err})\n")
        return False
    from ..core.state import new_game
    from ..ui.window import MainWindow
    from .test_ui import _use_offscreen
    _use_offscreen()
    app = QApplication.instance() or QApplication([])
    game = new_game("craft-ui")
    win = MainWindow(game)
    win.resize(1360, 880)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    check = suite.check

    def _pump(times: int = 4):
        for _ in range(times):
            app.processEvents()

    @check("the cradle launches a craft, and the cockpit flies her")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..sim import craft as craft_sim
        from ..ui.craft_window import open_cockpit
        game = win.game
        win.go("ship")
        view = win.views["ship"]
        view.tab = "cradle"
        view.refresh()
        _pump()
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        launch = [b for name, b in named.items()
                  if name.startswith("craft_launch_") and b.isEnabled()]
        assert launch, sorted(named)
        launch[0].click()
        _pump()
        # Two craft on the cradle now, so follow whichever the tab sent.
        craft = craft_sim.flying(game)
        assert craft is not None and game.sortie is not None
        cockpit = getattr(win, "craft_window", None) or open_cockpit(win)
        _pump()
        buttons = {b.objectName() for b in cockpit.findChildren(QPushButton)}
        for want in ("craft_burn_forward", "craft_drive", "craft_auto_run",
                     "craft_clock", "craft_strike", "craft_recover"):
            assert want in buttons, sorted(buttons)
        cockpit.aim = cockpit.contacts()[0].id
        cockpit._toggle_drive()                  # main drive armed
        for _ in range(8):
            cockpit._burn("forward")
        _pump()
        assert craft_sim.out_km(game) > 1.0, (
            f"the cockpit flew {craft_sim.out_km(game):.2f} km")
        cockpit.findChild(QPushButton, "craft_recover")
        got = craft_sim.recover(game)
        cockpit.close()
        _pump()
        return (f"launched {craft.name} from the cradle, flew "
                f"{craft_sim.out_km(game):,.0f} km from the cockpit"
                + ("" if got["ok"] else f" (home: {got['why'][:30]})"))

    @check("the battle screen launches her into the fight, and calls her in")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..core.rng import RNG
        from ..sim import combat as combat_sim
        from ..sim import craft as craft_sim
        from ..sim import encounters as enc_sim
        game = win.game
        # Everything back on the cradle: the check above left one of them
        # three thousand km out, which is a long way to come for a fight
        # that has not started yet.
        for got in craft_sim.aboard(game):
            got.state, got.pilot = "cradled", ""
        game.sortie = None
        craft = next(c for c in craft_sim.aboard(game)
                     if craft_sim.kind_of(c).guns)
        rng = RNG("battle-ui")
        enemy = enc_sim.make_enemy(rng, "charter", difficulty=1.3)
        win.battle = combat_sim.start(game.ship, game.ship_stats, enemy,
                                      bonuses=game.bonuses,
                                      officers=game.officers, game=game,
                                      rng=rng)
        # The window keeps it on the chronicle, which is what `sim` reads.
        assert game.battle is win.battle
        win.go("battle")
        _pump()
        view = win.views["battle"]
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        away = named.get("battle_craft_launch")
        assert away is not None and away.isEnabled(), sorted(named)
        away.click()
        _pump()
        assert craft.state == "out", "the button did not launch her"
        assert craft.struck >= 1, "away and never ran in"
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        home = named.get("battle_craft_home")
        assert home is not None, sorted(named)
        if not win.battle.over:
            home.click()
            _pump()
            assert craft.state == "cradled", "called in and stayed out"
        win.battle = None
        win.go("system")
        _pump()
        return (f"launched off the battle screen, {craft.struck} run"
                f"{'' if craft.struck == 1 else 's'} made, and the cradle "
                "took her back")

    @check("the yard's cradles tab fits a cradle, lays one down, mends and sells")
    def _():
        from PyQt6.QtWidgets import QPushButton
        from ..sim import craft as craft_sim
        from ..sim import hangar as hangar_sim
        game = win.game
        game.credits = 300_000
        for key in ("biomass", "silicon", "alloy"):
            game.stores[key] = 400.0
        win.go("yard")
        view = win.views["yard"]
        view.tab = "cradles"
        view.refresh()
        _pump()
        # The hull she sails with has both cradles full, so put her back to
        # one craft in one cradle — the state this check is about.
        for got in craft_sim.aboard(game):
            got.state, got.pilot = "cradled", ""
        game.sortie = None
        game.craft = [next(c for c in craft_sim.aboard(game)
                           if craft_sim.kind_of(c).guns)]
        game.ship.cradles = 1
        view.refresh()
        _pump()
        had = hangar_sim.cradles(game.ship)
        fit = view.findChild(QPushButton, "yard_cradle_fit")
        assert fit is not None and fit.isEnabled(), "no way to fit a cradle"
        fit.click()
        _pump()
        assert hangar_sim.cradles(game.ship) == had + 1
        view = win.views["yard"]
        buy = view.findChild(QPushButton, "yard_craft_buy_mote")
        assert buy is not None and buy.isEnabled(), buy
        aboard = len(craft_sim.aboard(game))
        buy.click()
        _pump()
        assert len(craft_sim.aboard(game)) == aboard + 1, "the slip laid down nothing"
        # Mend the one that is hurt, and sell the one that is not wanted.
        bought = craft_sim.aboard(game)[-1]
        bought.hp = 30
        view = win.views["yard"]
        view.refresh()
        _pump()
        mends = [b for b in view.findChildren(QPushButton)
                 if b.objectName() == "yard_craft_mend" and b.isEnabled()]
        assert mends, "nothing offered to mend a damaged craft"
        mends[-1].click()
        _pump()
        assert bought.hp == craft_sim.kind_of(bought).hull, "the yard mended nothing"
        money = game.credits
        sells = [b for b in win.views["yard"].findChildren(QPushButton)
                 if b.objectName() == "yard_craft_sell" and b.isEnabled()]
        assert sells, "nothing offered to sell"
        sells[-1].click()
        _pump()
        assert game.credits > money and len(craft_sim.aboard(game)) == aboard
        return (f"a cradle cut, a MOTE laid down, mended and sold for "
                f"₡{game.credits - money:,.0f}")

    win.close()
    return True
