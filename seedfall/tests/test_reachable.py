"""Nothing computed that nothing consumes.

Three times running a feature shipped a number the game never read. A levy
venture incremented a counter nothing consulted. `death_reason` was recorded on
every death and never shown. The Bloom's growth multiplier was derived from its
responses and used by nobody, so it would have "answered" a provoked captain by
printing a line and changing nothing at all.

Two of those were caught by the `Game`-fields check in `test_orders.py`, which
walks persistent state. This is the other half: a function that returns a value
and is called from nowhere is a feature that does not exist, however carefully
it is written.

Finding it also turned up two genuine holes rather than dead code — treaties
that bought no trade advantage despite the function promising one, and instars
that could never be killed because nothing called `kill_instar`.
"""

from __future__ import annotations

import ast
import pathlib

from .harness import Suite

ROOT = pathlib.Path(__file__).resolve().parents[1]

#: Entry points the package offers rather than consumes. A `main`, a save-codec
#: hook or a suite runner is called from outside the tree or by the framework.
EXPORTED = {"main", "run", "encode", "decode", "read", "write", "exists",
            "clear_save", "report", "check", "build_app"}

#: Deliberately kept, with the reason. Anything added here needs one.
ALLOWED: dict[str, str] = {}


def _hands_back_a_value(node: ast.FunctionDef) -> bool:
    """Whether this function returns anything worth consuming.

    `return None` is a control-flow return, not a result — counting it was the
    first thing the self-check caught, which is the entire argument for having
    written the self-check.
    """
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Return) or sub.value is None:
            continue
        if isinstance(sub.value, ast.Constant) and sub.value.value is None:
            continue
        return True
    return False


def _public_functions() -> dict[str, str]:
    """Every public module-level function, whether or not it returns anything.

    Restricting this to value-returning functions missed `kill_instar`, which
    mutates and returns nothing — and which nothing called, so a roaming Bloom
    mass could never be destroyed. A function nobody calls is a feature that
    does not exist regardless of its return type.
    """
    found: dict[str, str] = {}
    for path in sorted(ROOT.rglob("*.py")):
        if path.parent.name == "tests":
            continue
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if node.name.startswith("_") or node.name in EXPORTED:
                continue
            found[f"{path.stem}.{node.name}"] = node.name
    return found


def _called_anywhere() -> set[str]:
    """Every name called or exported anywhere, tests included.

    Tests count as consumers: a function driven only by the suite is at least
    being exercised deliberately, which is a different mistake from one nobody
    calls at all.
    """
    names: set[str] = set()
    for path in ROOT.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = (func.attr if isinstance(func, ast.Attribute)
                        else getattr(func, "id", None))
                if name:
                    names.add(name)
            # `__all__` entries and getattr("name") count as use.
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.add(node.value)
    return names


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing in the package is written and never called")
    def _():
        # What this does and does not catch, stated plainly: it finds a public
        # function nobody calls *at all*. It will not catch one that is called
        # only from a readout or only by this suite — the Bloom's growth
        # multiplier was consumed by `summary()` from the day it was written
        # while contributing nothing to the simulation, and this check would
        # have passed on it. Being reachable is a floor, not a guarantee.
        defined = _public_functions()
        called = _called_anywhere()
        orphans = sorted(name for name, bare in defined.items()
                         if bare not in called and name not in ALLOWED)
        assert not orphans, (
            f"{len(orphans)} public function(s) nothing ever calls. Either "
            "wire it into the game or delete it:\n      "
            + "\n      ".join(orphans))
        return f"{len(defined)} public functions, every one reachable"

    @check("the check can still see an orphan when there is one")
    def _():
        # A check that cannot fail is worse than no check. Run the same
        # analysis over a synthetic module rather than over the real tree —
        # any literal name used here would otherwise be found *in this file*
        # by the very scan it is testing.
        source = (
            "def gives_nothing():\n    return None\n\n"
            "def gives_something():\n    return 42\n\n"
            "def _private():\n    return 1\n"
        )
        tree = ast.parse(source)
        returning = {n.name for n in tree.body
                     if isinstance(n, ast.FunctionDef)
                     and not n.name.startswith("_")
                     and _hands_back_a_value(n)}
        assert returning == {"gives_something"}, (
            f"the analysis picked out {returning} rather than the one function "
            "that returns a value")
        return "picks out a value-returning public function and ignores the rest"

    @check("treaties are worth something at a quay")
    def _():
        # Found by the check above: `treaty_bonus` promised that signing made
        # everyone easier to trade with, and was called by nothing, so a treaty
        # bought standing and a label and no trade advantage whatever.
        from ..core.state import new_game
        from ..sim import diplomacy as dip

        game = new_game("treaty-worth")
        game.credits = 500000
        for power in dip.POWERS:
            game.rep[power] = 80
        before = game.ship_stats.trade
        for power in dip.POWERS:
            dip.perform(game, "treaty", power)
        game.recompute()
        assert len(dip.ensure(game).treaties) == len(dip.POWERS), "no treaties signed"
        assert game.ship_stats.trade > before, (
            f"four signed treaties left the trade bonus at {game.ship_stats.trade}")
        return f"trade bonus {before:.2f} → {game.ship_stats.trade:.2f} on four treaties"

    @check("a roaming instar can be fought and killed")
    def _():
        # Also found by the check: `kill_instar` was called from nowhere, so
        # instars seeded systems and ate colonies with no counterplay at all —
        # and the provocation table paid seventy for a kill nobody could make.
        from ..core.rng import RNG
        from ..core.state import new_game
        from ..sim import bloom as bloom_sim
        from ..sim import responses as response_sim

        game = new_game("instar-kill")
        state = bloom_sim.ensure(game)
        state.stage = 3
        for system in game.galaxy.systems[:5]:
            system.bloom = 0.7
        instar = bloom_sim._spawn_instar(game, RNG("k"))
        assert instar is not None, "nothing to detach a mass from"
        state.instars.append(instar)
        instar.system_id = game.location_id

        assert bloom_sim.instar_at(game, game.location_id) is not None, (
            "a mass in your own system is invisible")
        encounter = bloom_sim.engage_instar(game, instar)
        assert encounter["enemy"], "no hull to fight"
        assert encounter["no_parley"], "the mass can be talked to"

        before = response_sim.level(game)
        bloom_sim.kill_instar(game, instar)
        assert instar not in state.instars, "killing it left it on the board"
        assert response_sim.level(game) > before, (
            "killing a mass provoked nothing, though the table pays for it")
        return f"engaged, killed, and worth {response_sim.level(game) - before:.0f} provocation"
