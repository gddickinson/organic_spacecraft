"""Founding checks — the seed dialog has to say what will grow.

It showed each class's name, blurb, cost and gestation time, and never what it
produced. Measured on one rocky body: fourteen classes on offer, yielding
anything from 2.6 tonnes of ore a day (RADIX Mine, 12,000 credits) to 260
credits a day (Free Port, 74,000) to 4.2 research a day (Reactivated Array,
96,000) — and two of them, the GRAVID Nursery at 60,000 and the Monitor Station
at 64,000, yielding nothing at all and buying effects instead, which the dialog
did not say either.

Founding is a months-long, tens-of-thousands commitment. The screen gave a
price and a wait and no other side to the ledger.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.colonies import COLONIES, colonies_for
from ..data.tech import TECH
from ..sim import colony as colony_sim
from ..sim import works as works_sim
from .harness import Suite


def _ready(seed: str = "found"):
    game = new_game(seed)
    game.credits = 9_000_000
    game.ship.fitted.append("seed_bay")
    game.research.unlocked.extend(t.id for t in TECH)
    game.recompute()
    # Stock everything any class might ask for, rather than a guessed list —
    # the first version missed spidroin and the check died on a class it had
    # nothing to do with.
    from ..data.commodities import COMMODITIES
    for good in COMMODITIES:
        game.stores[good.id] = 900_000
    game.system.bloom = 0.0
    return game


def _site(game):
    return next(b for b in game.system.bodies
                if b.kind in ("rocky", "moon", "asteroid", "ice"))


def run(suite: Suite) -> None:
    check = suite.check

    @check("the forecast is what the colony actually does")
    def _():
        # The honesty check. Plant it, mature it, and compare.
        checked = 0
        for klass in COLONIES:
            game = _ready(f"fc-{klass.id}")
            body = _site(game)
            if klass.id not in {c.id for c in
                                colonies_for(body.kind, game.research.unlocked)}:
                continue
            said = colony_sim.forecast(game, game.system, body, klass.id)
            colony, why = colony_sim.found(game, game.system, body, klass.id)
            assert colony, why
            assert colony.need == said["days"], (
                f"{klass.id}: forecast {said['days']} days, gestates "
                f"{colony.need}")
            game.advance_days(colony.need + 5)
            assert colony.online, f"{klass.id} never matured"
            assert works_sim.yields_of(colony) == said["yields"], (
                f"{klass.id}: forecast {said['yields']}, yields "
                f"{works_sim.yields_of(colony)}")
            assert works_sim.upkeep_of(colony) == said["upkeep"]
            assert works_sim.effects_of(colony) == said["effects"]
            checked += 1
        assert checked >= 8, f"only {checked} classes could be planted"
        return f"{checked} classes planted, every forecast matched"

    @check("asking what would grow does not plant it")
    def _():
        game = _ready("pure")
        body = _site(game)
        before = (game.credits, dict(game.stores), len(game.colonies),
                  body.colony)
        for klass in COLONIES:
            for _ in range(2):
                colony_sim.forecast(game, game.system, body, klass.id)
        after = (game.credits, dict(game.stores), len(game.colonies),
                 body.colony)
        assert after == before, "forecasting planted something"
        return f"{len(COLONIES) * 2} forecasts, nothing planted"

    @check("every class is worth something, one way or the other")
    def _():
        # A class that neither produces nor grants anything is a money sink
        # with a blurb.
        game = _ready("worth")
        body = _site(game)
        empty = []
        for klass in COLONIES:
            said = colony_sim.forecast(game, game.system, body, klass.id)
            if not said.get("yields") and not said.get("effects"):
                empty.append(klass.id)
        assert not empty, f"classes that do nothing at all: {empty}"
        yielding = sum(1 for k in COLONIES
                       if colony_sim.forecast(game, game.system, body,
                                              k.id).get("yields"))
        return (f"{len(COLONIES)} classes, {yielding} that produce and "
                f"{len(COLONIES) - yielding} that only grant")

    @check("a payback is quoted when there is one and withheld when there is not")
    def _():
        game = _ready("payback")
        body = _site(game)
        paying = silent = 0
        for klass in colonies_for(body.kind, game.research.unlocked):
            said = colony_sim.forecast(game, game.system, body, klass.id)
            if said["a_day"] > 0:
                assert said["payback"] and said["payback"] > 0, (
                    f"{klass.id} earns {said['a_day']:.0f} a day and quotes "
                    "no payback")
                paying += 1
            else:
                assert said["payback"] is None, (
                    f"{klass.id} earns nothing and quotes a payback anyway")
                silent += 1
        assert paying and silent, (
            f"{paying} paying and {silent} not — one case is untested")
        return f"{paying} classes quote a payback, {silent} rightly do not"

    @check("the classes are not interchangeable on the same ground")
    def _():
        # The decision the dialog exists to support.
        game = _ready("spread")
        body = _site(game)
        offered = colonies_for(body.kind, game.research.unlocked)
        assert len(offered) >= 6, f"only {len(offered)} classes on offer"
        rates = {k.id: colony_sim.forecast(game, game.system, body,
                                           k.id)["a_day"] for k in offered}
        earners = [v for v in rates.values() if v > 0]
        assert max(earners) > min(earners) * 3, (
            f"every class earns about the same: {rates}")
        kinds = {tuple(sorted(colony_sim.forecast(game, game.system, body,
                                                  k.id)["yields"]))
                 for k in offered}
        assert len(kinds) >= 4, f"they all produce the same things: {kinds}"
        return (f"{len(offered)} classes, {len(kinds)} different outputs, "
                f"{min(earners):.0f}–{max(earners):.0f} a day")
