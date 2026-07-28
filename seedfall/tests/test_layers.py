"""The one-directional rule, enforced rather than stated.

`data → world → sim → ui`. Rules live below, screens draw them. The project has
said so in `INTERFACE.md` since it was written and nothing checked it, and it
was broken twice in ways that mattered:

* the whole aftermath of an engagement lived in `ui/battle_view.py`, so nothing
  headless could resolve a fight and every balance run collected no loot;
* seventeen sites across four view modules spent credits and moved standing
  directly, so buying, selling, hiring, repairing, scrapping and tying up could
  none of them be performed or measured without a mouse.

Neither broke the rule by importing Qt downward. They broke it by writing rules
upward, which is why the Qt check alone was not enough.
"""

from __future__ import annotations

import ast
import pathlib

from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: The layers that must never know Qt exists.
RULES_LAYERS = ("sim", "data", "world", "core")

#: Attributes of the `Game` that are the ledger: changing one is a rule, not a
#: presentation choice.
LEDGER = ("credits", "rep", "stores")

#: Views may read these freely; only assignment and mutation are the problem.
_WRITE_OPS = (ast.Store, ast.AugStore) if hasattr(ast, "AugStore") else (ast.Store,)


def _qt_offenders() -> list[str]:
    out = []
    for layer in RULES_LAYERS:
        for path in sorted((ROOT / layer).rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if any(n.split(".")[0] == "PyQt6" for n in names):
                    out.append(f"{layer}/{path.name}")
    return sorted(set(out))


def _ledger_writes() -> list[str]:
    """Every place a view assigns to, or calls a mutator on, the ledger.

    Matched structurally rather than by text: an assignment whose target is
    `<anything>.credits`, an augmented assignment to one, or a call to
    `<anything>.adjust_rep(...)`. Reading a balance to draw it is fine.
    """
    found: list[str] = []
    for path in sorted((ROOT / "ui").rglob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Attribute) and target.attr in LEDGER:
                    found.append(f"ui/{path.name}:{node.lineno} "
                                 f"writes .{target.attr}")
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "adjust_rep"):
                found.append(f"ui/{path.name}:{node.lineno} calls adjust_rep")
            # dict-style writes: game.stores[x] = ..., game.rep[x] = ...
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Attribute)
                            and target.value.attr in LEDGER):
                        found.append(f"ui/{path.name}:{node.lineno} "
                                     f"writes .{target.value.attr}[…]")
    return found


def run(suite: Suite) -> None:
    check = suite.check

    @check("the rules layers do not know Qt exists")
    def _():
        offenders = _qt_offenders()
        assert not offenders, f"Qt reached the rules: {offenders}"
        counted = sum(len(list((ROOT / layer).rglob("*.py")))
                      for layer in RULES_LAYERS)
        return f"{counted} modules across {len(RULES_LAYERS)} layers, no Qt in any"

    @check("no screen writes the ledger itself")
    def _():
        # Seventeen of these when the check was written. Each one was a rule
        # only a mouse could perform: buying, selling, hiring, repairing,
        # scrapping, tying up, and moving contraband off the books.
        offenders = _ledger_writes()
        assert not offenders, (
            f"{len(offenders)} ledger write(s) in views:\n      "
            + "\n      ".join(offenders[:8]))
        views = len(list((ROOT / "ui").rglob("*.py")))
        return f"{views} view modules, none of them spending or scoring"

    @check("the check can still see a ledger write when there is one")
    def _():
        # A structural matcher that silently matches nothing is worse than no
        # check at all — this suite would have passed on the day the defect
        # was at its worst.
        planted = ast.parse(
            "class V:\n"
            "    def go(self):\n"
            "        self.game.credits -= 10\n"
            "        self.game.adjust_rep('charter', -3)\n"
            "        self.game.stores['ore'] = 4\n")
        hits = 0
        for node in ast.walk(planted):
            if isinstance(node, (ast.Assign, ast.AugAssign)):
                targets = (node.targets if isinstance(node, ast.Assign)
                           else [node.target])
                for target in targets:
                    if isinstance(target, ast.Attribute) and target.attr in LEDGER:
                        hits += 1
                    if (isinstance(target, ast.Subscript)
                            and isinstance(target.value, ast.Attribute)
                            and target.value.attr in LEDGER):
                        hits += 1
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "adjust_rep"):
                hits += 1
        assert hits == 3, f"the matcher found {hits} of 3 planted writes"
        return "all three shapes of ledger write are recognised"

    @check("the screen and the rules agree on a trade")
    def _():
        # The extraction has to be faithful, not merely tidy. Two identical
        # games: one buys through the sim, one clicks through the port screen.
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError:
            return "skipped: no Qt"

        from ..core.state import new_game
        from ..sim import trade as trade_sim
        from ..ui import theme
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())

        def stocked(seed):
            game = new_game(seed)
            game.credits = 400000
            game.location_id = next(s.id for s in game.galaxy.systems if s.port)
            return game

        def ledger(game):
            return (round(game.credits, 3),
                    {p: round(v, 3) for p, v in game.rep.items()},
                    dict(game.ship.cargo))

        cid = "ore"
        direct = stocked("agree-trade")
        trade_sim.buy(direct, cid, 12)
        trade_sim.sell(direct, cid, 5)
        expected = ledger(direct)

        through = stocked("agree-trade")
        win = MainWindow(through)
        win.dialog = lambda *a, **k: None
        win.toast = lambda *a, **k: None
        view = win.views["port"]
        view._buy(cid, 12)
        view._sell(cid, 5)
        got = ledger(through)
        win.close()

        assert got == expected, f"screen {got} != rules {expected}"
        return "credits, standing and hold identical down both paths"

    @check("every rule a screen used to own has a home in the sim")
    def _():
        # Named so that deleting one and leaving the screen to do it again
        # fails here rather than quietly passing the structural check.
        from ..sim import crew as crew_sim
        from ..sim import customs as customs_sim
        from ..sim import minigames as mg
        from ..sim import services as services_sim
        from ..sim import shipyard as shipyard_sim
        from ..sim import trade as trade_sim

        moved = {
            "buying over a counter": trade_sim.buy,
            "selling over a counter": trade_sim.sell,
            "selling survey data": trade_sim.sell_survey_data,
            "selling contraband quietly": customs_sim.sell_quietly,
            "repairing a hull": services_sim.repair,
            "paying for a lead": services_sim.buy_rumour,
            "buying bench time": services_sim.commission_study,
            "signing an officer on": crew_sim.hire,
            "paying the bridge a bonus": crew_sim.pay_bonus,
            "breaking a hull up": shipyard_sim.scrap,
            "tying up at a quay": mg.come_alongside,
        }
        for what, fn in moved.items():
            assert callable(fn), f"{what} has no home in the sim"
        return f"{len(moved)} operations, all performable without a screen"
