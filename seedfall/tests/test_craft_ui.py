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
        craft = craft_sim.aboard(game)[0]
        named = {b.objectName(): b for b in view.findChildren(QPushButton)}
        launch = [b for name, b in named.items()
                  if name.startswith("craft_launch_") and b.isEnabled()]
        assert launch, sorted(named)
        launch[0].click()
        _pump()
        assert craft.state == "out" and game.sortie is not None
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


    win.close()
    return True
