"""The way out of a dead end, and whether the game can see it.

`distress_call` is the game's answer to running out of fuel and money at once:
somebody tows you, it costs standing and two thousand credits, and you are
moving again. It is gated on `is_stranded`, and `is_stranded` was answering a
different question from the ones that actually grant a way out.

Found by playing the project's own `captain_bot` for five years, six seeds.
Two runs stopped short — one at day 1406 of 1825, moored at **Amber
Anchorage**, a one-body system, with **0 credits and 2.3 tonnes of reaction
mass**. The single body held 0.271 volatiles and was worked out; `extract`
refused it — *"there are other bodies"* — and there were none. The captain
asked for a tow and was told **"You are not stranded — you can still move."**

Two guesses, in a function whose whole job is to know:

* The ice test read `resources["volatiles"] > 0.05`, which is how *rich* a
  body is. Whether a rig will go on it is `mining.worked_out`, which reads how
  much has been *taken*. Different quantities, so a rich body worked to
  exhaustion counted as fuel for ever.
* The port test fell back to `or 40` when `buy_price` returned None — and None
  is exactly what it returns when the market holds none to sell. A fresh
  sector has no dry port in 417, which is why nothing caught it; a played one
  does. `run-a` found Nine's Crossing with no reaction mass on the board.

And `nearest_port` would answer a distress call with the port you were already
moored at, which reads as a bug even though the fuel it brings is real.

The claims:

- **`is_stranded` is False only when something actually gets you out.** The
  general one, swept over played and constructed states, and the shape both
  bugs had.
- **A worked-out body is not a fuel supply**, and neither is a market with
  none for sale.
- **A tow always leaves you able to move**, which is the point of it.
- **A tow takes you somewhere else.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import actions, mining
from ..world.economy import buy_price
from ..world.galaxy import in_range
from .harness import Suite


def _escapes(game) -> dict:
    """Every way out of here that genuinely works, checked against its owner."""
    reach = in_range(game.galaxy.systems, game.system, game.ship_stats.jump)
    fuel = game.ship.cargo.get("volatiles", 0)
    out = {"jump": any(fuel >= actions.jump_quote(game, s)["fuel"]
                       for s in reach)}

    buy = False
    if game.system.port and game.system.market and reach:
        price = buy_price(game.system.market, "volatiles",
                          game.rep.get(game.system.port.faction, 0))
        cheapest = min(actions.jump_quote(game, s)["fuel"] for s in reach)
        buy = price is not None and game.credits >= price * (cheapest - fuel)
    out["buy"] = buy

    # Asked of `extract` itself rather than of a threshold: the whole bug was
    # a second opinion about whether a body could be worked.
    out["mine"] = game.ship_stats.drink > 0 and any(
        b.resources.get("volatiles", 0) > 0.05 and not mining.worked_out(b)
        for b in game.system.bodies)
    out["nowhere"] = not reach
    return out


def _broke(seed: str, fuel: float = 1.0, credits: float = 0.0):
    """A captain out of money and nearly out of reaction mass."""
    game = new_game(seed)
    game.credits = credits
    game.ship.cargo["volatiles"] = fuel
    return game


def _exhaust(game) -> None:
    """Work every body in this system out."""
    for body in game.system.bodies:
        body.depleted = 1.0


def _dry_port(game) -> None:
    """Take every tonne of reaction mass off the board here."""
    if game.system.market:
        stock = game.system.market.stock.get("volatiles")
        if stock is not None:
            stock.supply = 0.0
            stock.units = 0


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing is called unstranded unless something actually gets it out")
    def _():
        # The general question, and the shape both bugs had: `is_stranded`
        # answering off its own literals rather than asking whoever grants
        # each way out.
        # The combined spoiler matters: with only one of them applied there is
        # always a second way out, so disabling the *jump* escape entirely
        # went unnoticed by the first draft of this check. A full tank in a
        # system with no ice and no fuel on the shelf is the state where
        # jumping is the only answer, and it has to be in the sweep.
        def _both(game):
            _exhaust(game)
            _dry_port(game)

        wrong, checked = [], 0
        for seed in range(14):
            for fuel, credits in ((0.0, 0.0), (2.0, 0.0), (2.0, 400.0),
                                  (60.0, 20_000.0)):
                for spoil in (None, _exhaust, _dry_port, _both):
                    game = _broke(f"agree{seed}", fuel, credits)
                    if spoil:
                        spoil(game)
                    checked += 1
                    stranded = actions.is_stranded(game)
                    ways = _escapes(game)
                    can_move = ways["jump"] or ways["buy"] or ways["mine"]
                    if stranded and can_move:
                        wrong.append(f"seed{seed} f{fuel} c{credits}: called "
                                     f"stranded with {ways}")
                    if not stranded and not can_move and not ways["nowhere"]:
                        wrong.append(f"seed{seed} f{fuel} c{credits}: told it "
                                     f"can still move, and {ways}")
        assert not wrong, (
            f"{len(wrong)} state(s) where the stranding test and the ways out "
            f"disagree: {wrong[:4]}")
        assert checked > 100, checked
        return f"{checked} states, the verdict matching the ways out in all"

    @check("a worked-out body is not a fuel supply")
    def _():
        # The exact case, constructed: a hull with a harvest tendril, no
        # money, almost no reaction mass, and every body in the system worked
        # out. Before, the abundance of the ice was enough to answer "you can
        # still move" — for ever.
        found = 0
        for seed in range(20):
            game = _broke(f"worked{seed}", fuel=1.0, credits=0.0)
            if game.ship_stats.drink <= 0:
                continue
            rich = [b for b in game.system.bodies
                    if b.resources.get("volatiles", 0) > 0.05]
            if not rich:
                continue
            _exhaust(game)
            # It has to be rich and finished at once, or this proves nothing.
            assert any(b.resources.get("volatiles", 0) > 0.05
                       and mining.worked_out(b) for b in game.system.bodies)
            reach = in_range(game.galaxy.systems, game.system,
                             game.ship_stats.jump)
            if not reach:
                continue
            if any(1.0 >= actions.jump_quote(game, s)["fuel"] for s in reach):
                continue                       # could still limp out; not stuck
            _dry_port(game)
            assert actions.is_stranded(game), (
                f"{game.system.name}: every body worked out, no money, one "
                "tonne aboard, and the game says the captain can still move")
            found += 1
        assert found >= 5, f"only {found} systems could be put in this state"
        return f"{found} exhausted systems, every one recognised as a dead end"

    @check("a market with none to sell is not a way out")
    def _():
        # `buy_price` returns None when the shelf is empty and the old code
        # read that as a price of 40. No port in a fresh sector is dry, which
        # is why this went unseen; a played one gets there.
        found = 0
        for seed in range(20):
            game = _broke(f"dry{seed}", fuel=1.0, credits=50_000.0)
            if not (game.system.port and game.system.market):
                continue
            _exhaust(game)
            reach = in_range(game.galaxy.systems, game.system,
                             game.ship_stats.jump)
            if not reach or any(1.0 >= actions.jump_quote(game, s)["fuel"]
                                for s in reach):
                continue
            assert not actions.is_stranded(game), (
                "a captain with fifty thousand credits at a stocked port is "
                "not stranded")
            _dry_port(game)
            assert buy_price(game.system.market, "volatiles",
                             game.rep.get(game.system.port.faction, 0)) is None
            assert actions.is_stranded(game), (
                f"{game.system.name} has no reaction mass on the board and "
                "the game still counts the port as a way out")
            found += 1
        assert found >= 4, f"only {found} ports could be emptied"
        return (f"{found} ports emptied, each one stopping being an answer "
                "when it ran out")

    @check("a tow always leaves you able to move")
    def _():
        # The point of the whole mechanism. If a rescue can land you somewhere
        # you cannot leave either, it is not a rescue.
        towed = 0
        for seed in range(24):
            game = _broke(f"tow{seed}", fuel=0.5, credits=0.0)
            _exhaust(game)
            _dry_port(game)
            if not actions.is_stranded(game):
                continue
            res = actions.distress_call(game)
            if res.get("dead"):
                continue
            assert res.get("ok"), f"stranded and refused a tow: {res}"
            assert not actions.is_stranded(game), (
                f"towed to {game.system.name} and stranded again on arrival")
            assert game.ship.cargo.get("volatiles", 0) > 0.5, (
                "the tow brought no reaction mass")
            towed += 1
        assert towed >= 10, towed
        return f"{towed} tows, every one leaving the captain able to fly"

    @check("a tow takes you somewhere else")
    def _():
        moved = 0
        for seed in range(24):
            game = _broke(f"move{seed}", fuel=0.5, credits=0.0)
            _exhaust(game)
            _dry_port(game)
            if not actions.is_stranded(game):
                continue
            was = game.system.id
            res = actions.distress_call(game)
            if not res.get("ok") or res.get("dead"):
                continue
            assert game.system.id != was, (
                f"answered a distress call by towing the captain to "
                f"{game.system.name}, where they already were")
            moved += 1
        assert moved >= 10, moved
        return f"{moved} tows, none of them to the berth already occupied"

    @check("the naive captain never stalls with time left on the clock")
    def _():
        # `captain_bot` exists to catch deadlocks — its docstring says so —
        # and nothing was checking that it reached the end of its run. Two of
        # six five-year runs stopped short, one of them at day 1406, and the
        # solvency check beside it passed on the mean of all six.
        from .captain_bot import _bot

        short = []
        for seed in ("run-a", "run-b", "run-c", "run-d", "run-e", "run-f"):
            game = _bot(seed, years=5)
            if game.dead or game.victory:
                continue
            if game.day < 365 * 5 - 120:
                short.append(f"{seed} stopped on day {game.day} with "
                             f"{game.credits:,.0f} credits at "
                             f"{game.system.name}")
        assert not short, (
            f"{len(short)} run(s) ran out of moves before running out of "
            f"time: {short}")
        return "six five-year runs, every one playable to the end"
