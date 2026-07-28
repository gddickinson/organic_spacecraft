"""Overture checks — the screen has to say what an overture does.

It listed a name, a blurb and a price, and never what any of it bought.
Measured: tribute is 12,000 credits for +9 standing, intelligence 6 survey
sets for +7, relief 40 tonnes of biomass for +11 — so relief is about six
times better per credit than tribute, and there was no way to see it.

A treaty was worse than merely opaque. It costs 30,000 *and* charges standing
with the signatory's enemies through `allegiance`, and that was stated
nowhere: you signed, and two other powers thought less of you for reasons the
game never mentioned.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.diplomacy import ACTIONS
from ..sim import diplomacy as dip
from .harness import Suite

POWERS = dip.POWERS
NEEDS_PARTNER = ("broker", "denounce")


def _able(seed: str, standing: float = 70.0):
    game = new_game(seed)
    game.credits = 5_000_000
    for key in ("biomass", "volatiles", "survey", "ore"):
        game.stores[key] = 100_000
    for power in POWERS:
        game.rep[power] = standing
    return game


def _snapshot(game):
    return ({p: game.rep.get(p, 0) for p in POWERS},
            {(a, b): dip.relation(game, a, b)
             for i, a in enumerate(POWERS) for b in POWERS[i + 1:]})


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the screen previews is what the overture does")
    def _():
        checked = 0
        for action in ACTIONS:
            game = _able(f"pv-{action.id}")
            other = "concordat" if action.id in NEEDS_PARTNER else None
            said = dip.preview(game, action.id, "charter", other)
            before_rep, before_rel = _snapshot(game)
            result = dip.perform(game, action.id, "charter", other)
            assert result["ok"], f"{action.id}: {result.get('why')}"
            after_rep, after_rel = _snapshot(game)

            moved = {p: round(after_rep[p] - before_rep[p], 2)
                     for p in POWERS if abs(after_rep[p] - before_rep[p]) > 0.01}
            promised = {p: round(v, 2) for p, v in said["standing"]}
            assert moved == promised, (
                f"{action.id}: said {promised}, did {moved}")

            shifted = {(a, b): round(after_rel[(a, b)] - before_rel[(a, b)], 2)
                       for (a, b) in before_rel
                       if abs(after_rel[(a, b)] - before_rel[(a, b)]) > 0.01}
            if said["relations"]:
                a, b, delta = said["relations"]
                key = (a, b) if (a, b) in shifted else (b, a)
                assert shifted.get(key) == round(delta, 2), (
                    f"{action.id}: said the matrix moves {delta}, it moved "
                    f"{shifted}")
            else:
                assert not shifted, (
                    f"{action.id} said nothing about the matrix and moved "
                    f"{shifted}")
            checked += 1
        assert checked == len(ACTIONS)
        return f"all {checked} overtures do exactly what they preview"

    @check("previewing an overture does not perform it")
    def _():
        game = _able("pure")
        before = _snapshot(game)
        cash = game.credits
        for action in ACTIONS:
            other = "concordat" if action.id in NEEDS_PARTNER else None
            for _ in range(3):
                dip.preview(game, action.id, "charter", other)
        assert _snapshot(game) == before, "previewing moved the world"
        assert game.credits == cash, "previewing spent money"
        return f"{len(ACTIONS) * 3} previews, nothing moved"

    @check("a treaty says what it costs you with their enemies")
    def _():
        # The half nobody was told about. At war it is a great deal more than
        # the couple of points it is at the opening.
        game = _able("treaty-cost")
        for index, a in enumerate(POWERS):
            for b in POWERS[index + 1:]:
                dip.shift_relation(game, a, b, -90 - dip.relation(game, a, b))
        said = dip.preview(game, "treaty", "charter")
        losers = [(p, v) for p, v in said["standing"] if v < 0]
        assert len(losers) == len(POWERS) - 1, (
            f"a treaty in a sector at war offends {len(losers)} powers")
        before, _rel = _snapshot(game)
        dip.perform(game, "treaty", "charter")
        after, _rel2 = _snapshot(game)
        for power, delta in losers:
            actual = after[power] - before[power]
            assert abs(actual - delta) < 0.01, (
                f"{power}: said {delta:.1f}, did {actual:.1f}")
        return (f"{len(losers)} powers minded, "
                + ", ".join(f"{p} {v:.1f}" for p, v in losers))

    @check("only brokering repairs the matrix, only denouncing tears it")
    def _():
        movers = {}
        for action in ACTIONS:
            game = _able(f"matrix-{action.id}")
            other = "concordat" if action.id in NEEDS_PARTNER else None
            before = dip.relation(game, "charter", "concordat")
            result = dip.perform(game, action.id, "charter", other)
            if not result.get("ok"):
                continue
            delta = dip.relation(game, "charter", "concordat") - before
            if abs(delta) > 0.01:
                movers[action.id] = round(delta, 1)
        assert movers.get("broker", 0) > 0, "brokering does not repair anything"
        assert movers.get("denounce", 0) < 0, "denouncing costs them nothing"
        assert set(movers) == {"broker", "denounce"}, (
            f"something else moves the matrix: {movers}")
        return " · ".join(f"{k} {v:+g}" for k, v in sorted(movers.items()))

    @check("the overtures are not interchangeable")
    def _():
        # Relief is far better per credit than tribute, and tribute is the only
        # one a distrusted captain can use at all. Both halves matter.
        game = _able("compare")
        from ..world.economy import sell_price
        port = next(s for s in game.galaxy.systems if s.market)

        def spend(action) -> float:
            total = float(action.cost_credits or 0)
            if action.cost_goods:
                cid, amount = action.cost_goods
                total += amount * (sell_price(port.market, cid) or 0)
            return total

        rates = {}
        for action in ACTIONS:
            if action.id in NEEDS_PARTNER or action.gain <= 0:
                continue
            cost = spend(action)
            rates[action.id] = cost / action.gain if cost else 0.0
        assert rates["relief"] < rates["tribute"] * 0.5, (
            f"relief and tribute cost about the same per point: {rates}")

        floors = {a.id: a.min_rep for a in ACTIONS}
        assert floors["tribute"] < floors["relief"], (
            "tribute buys nothing that relief does not, at any standing")
        distrusted = _able("distrusted", standing=-40.0)
        usable = [a.id for a, ok, _why in dip.available(distrusted, "charter")
                  if ok]
        assert "tribute" in usable and "relief" not in usable, (
            f"at -40 standing the usable overtures are {usable}")
        return (" · ".join(f"{k} {v:,.0f}/pt" for k, v in sorted(rates.items()))
                + f" · at -40 only {usable}")
