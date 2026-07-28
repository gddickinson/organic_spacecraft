"""Anything you are in the middle of survives being put down.

A crossing, an approach and a decoding exchange all used to live on the window
rather than on the game. Saving mid-approach and coming back lost it silently:
the guard that had been holding you in the docking screen simply stopped, and
the passes you had spent were gone.

The transit cycle exposed it by fixing only itself; this closes the rest. The
general check is the one that matters — the window's own guard names every
activity it will hold you inside, and every one of those has to be a field on
the `Game`.
"""

from __future__ import annotations

import ast
import pathlib

from ..core.state import Game
from .harness import Suite

#: Deliberately not persisted, with the reason. `battle_state` records that a
#: Battle is transient because no time passes while you are being shot at.
TRANSIENT = {"battle": "combat is resolved in one sitting; no clock runs"}


def _guarded_activities() -> set[str]:
    """Every `self.X` the window's `go()` will divert you into.

    An activity is recognised by its `.over` flag: the guard reads
    `self.X is not None and not self.X.over`. Matching every `self.X` in the
    method instead sweeps up `self.views`, `self.current` and the rest of the
    window's own furniture, which is how the first version of this check
    failed on five things that were never state at all.
    """
    source = (pathlib.Path(__file__).resolve().parents[1]
              / "ui" / "window.py").read_text()
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "go"):
            continue
        for sub in ast.walk(node):
            # self.X.over  →  X is an activity with a finished state
            if (isinstance(sub, ast.Attribute) and sub.attr == "over"
                    and isinstance(sub.value, ast.Attribute)
                    and isinstance(sub.value.value, ast.Name)
                    and sub.value.value.id == "self"):
                found.add(sub.value.attr)
    return found


def run(suite: Suite) -> bool:
    try:
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
    except ImportError as err:      # pragma: no cover - no Qt, no window
        print(f"── resume ───\n  skipped: {err}\n")
        return False

    import os
    import tempfile

    from ..core import save as save_mod
    from ..core.state import load_game, new_game
    from ..sim import minigames, transit as transit_sim
    from ..ui import theme
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    check = suite.check

    def window(game):
        win = MainWindow(game)
        win.resize(1400, 900)
        win.dialog = lambda *a, **k: None
        win.confirm = lambda *a, **k: True
        win.toast = lambda *a, **k: None
        win.show()
        return win

    def round_trip(game):
        os.environ["HOME"] = tempfile.mkdtemp()
        save_mod.write({"game": game})
        return load_game()

    @check("every activity the window holds you in lives on the game")
    def _():
        # The general form. A new mini-game or mode that guards navigation but
        # keeps its state on the window would be lost over a save exactly as
        # docking and decoding were, for cycles, unnoticed.
        fields = set(Game.__dataclass_fields__)
        guarded = _guarded_activities()
        assert guarded, "the window's go() no longer guards anything"
        stray = sorted(name for name in guarded
                       if name not in fields and name not in TRANSIENT)
        assert not stray, (
            "activities guarded on the window but not stored on the game — a "
            f"save taken during one loses it: {stray}")
        return (f"{len(guarded)} guarded activities, "
                f"{len(guarded & fields)} persisted, "
                f"{len(guarded & set(TRANSIENT))} transient by design")

    @check("an approach half flown comes back half flown")
    def _():
        game = new_game("resume-dock")
        win = window(game)
        win.docking = minigames.start_docking(
            game.rng("dock"), "Fleet Hub", game.ship_stats, game.officers)
        from ..sim.minigames import AXES
        minigames.correct(win.docking, AXES[0][0], +1, game.rng("c"))
        before = (win.docking.passes, dict(win.docking.error),
                  win.docking.port_name)
        win.close()

        back = window(round_trip(game))
        assert back.docking is not None, "the approach was lost"
        after = (back.docking.passes, dict(back.docking.error),
                 back.docking.port_name)
        assert after == before, f"{after} != {before}"
        back.close()
        return f"{before[0]} passes and the error on all three axes kept"

    @check("a decoding exchange cannot be re-rolled by saving")
    def _():
        # The sharper half: if the secret were regenerated on load, a player
        # could save, guess, reload and guess again against a fresh code.
        game = new_game("resume-decode")
        win = window(game)
        win.decoding = minigames.start_decoding(
            game.rng("dec"), "a xenolith", game.ship_stats, game.officers)
        win.decoding_tech = "phase_loom"
        minigames.guess(win.decoding, [1, 2, 3, 4])
        before = (list(win.decoding.secret), len(win.decoding.guesses),
                  win.decoding.tries, win.decoding_tech)
        win.close()

        back = window(round_trip(game))
        assert back.decoding is not None, "the exchange was lost"
        after = (list(back.decoding.secret), len(back.decoding.guesses),
                 back.decoding.tries, back.decoding_tech)
        assert after == before, f"{after} != {before}"
        assert back.decoding.secret == before[0], (
            "the code was re-rolled on load — save, guess, reload, repeat")
        back.close()
        return f"the code and {before[1]} guess(es) survived, tech kept"

    @check("a crossing under way comes back under way")
    def _():
        from ..core.rng import RNG

        game = new_game("resume-transit")
        game.ship.cargo = {"volatiles": 120}
        target = max(range(len(game.system.bodies)),
                     key=lambda i: game.system.bodies[i].orbit)
        started = transit_sim.begin(game, target, "standard")
        assert started["ok"], started.get("why")
        game.transit = started["transit"]
        transit_sim.stand(game, game.transit, RNG("resume"))
        before = (game.transit.stood, game.transit.days_spent,
                  round(game.transit.fuel_spent, 3), game.transit.event)

        back = round_trip(game)
        assert back.transit is not None, "the crossing was lost"
        after = (back.transit.stood, back.transit.days_spent,
                 round(back.transit.fuel_spent, 3), back.transit.event)
        assert after == before, f"{after} != {before}"
        return f"watch {after[0]} of {back.transit.watches}, {after[1]} days out"

    @check("reloading mid-approach puts you back in the seat")
    def _():
        # Persisting it is only half the fix: the guard has to still divert.
        game = new_game("resume-guard")
        win = window(game)
        win.docking = minigames.start_docking(
            game.rng("dock"), "Fleet Hub", game.ship_stats, game.officers)
        win.close()

        back = window(round_trip(game))
        back.go("map")
        assert back.current == "docking", (
            f"asked for the map mid-approach and landed on {back.current!r}")
        back.docking.over = True
        back.go("map")
        assert back.current == "map", (
            "the approach is finished and still will not let go")
        back.close()
        return "held until the approach is done, released afterwards"

    return True
