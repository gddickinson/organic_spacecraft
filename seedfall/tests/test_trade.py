"""Trade checks — a market with news, and notes that go stale.

Prices used to drift and nothing ever happened. These hold shocks to actually
moving a market and lifting cleanly afterwards, and hold the register to being
a record of what you personally saw rather than an oracle.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.commodities import BY_ID
from ..data.shocks import MAX_PER_SYSTEM, SHOCKS, STALE_DAYS
from ..sim import market as market_sim
from ..sim.market import Shock
from ..world.economy import buy_price
from .harness import Suite


def _ported(seed: str):
    game = new_game(seed)
    game.credits = 200000
    system = next(s for s in game.galaxy.systems if s.market)
    return game, system


def run(suite: Suite) -> None:
    check = suite.check

    @check("every shock can name itself without blowing up")
    def _():
        # A stray brace in one of these would crash the port screen the first
        # time that shock landed, months into somebody's game.
        for kind in SHOCKS:
            assert kind.goods or kind.supply != 1.0, f"{kind.id} does nothing"
            shock = Shock(id=1, kind=kind.id, system_id=0,
                          commodity=(kind.goods[0] if kind.goods else "ore"),
                          until=100)
            text = shock.text("Somewhere")
            assert "Somewhere" in text, f"{kind.id} drops the place name"
            assert "{" not in text, f"{kind.id} left a field unfilled: {text}"
            assert kind.days[0] > 0 and kind.days[1] >= kind.days[0]
        return f"{len(SHOCKS)} kinds, all legible"

    @check("a shock moves the price, and lifts cleanly when it ends")
    def _():
        game, system = _ported("shock-price")
        cid = next(c for c in system.market.stock if BY_ID.get(c))
        before = buy_price(system.market, cid)

        game.shocks = [Shock(id=1, kind="convoy", system_id=system.id,
                             commodity=cid, until=game.day + 100)]
        market_sim.apply_to_markets(game)
        during = buy_price(system.market, cid)
        assert during > before * 1.15, (
            f"a convoy failure moved the price {before} → {during}")

        # Expiring it must put the price back where it was.
        game.shocks[0].until = game.day - 1
        market_sim.tick(game, 1, RNG("expire"))
        market_sim.apply_to_markets(game)
        after = buy_price(system.market, cid)
        assert not market_sim.at(game, system.id), "the shock did not expire"
        assert abs(after - before) <= max(1, before * 0.02), (
            f"the price did not come back: {before} → {during} → {after}")
        return f"{cid}: {before} → {during} under the shock → {after} after"

    @check("shocks arrive, expire, and never pile up")
    def _():
        game = new_game("shock-flow")
        rng = game.rng("flow")
        seen, peak = set(), 0
        for _ in range(40):
            game.advance_days(90)
            live = market_sim.all_shocks(game)
            peak = max(peak, len(live))
            for shock in live:
                seen.add(shock.kind)
                assert shock.until > game.day, "an expired shock is still live"
            for system in game.galaxy.systems:
                assert len(market_sim.at(game, system.id)) <= MAX_PER_SYSTEM, (
                    f"{system.name} carries more than {MAX_PER_SYSTEM} shocks")
        assert len(seen) >= 4, f"only {len(seen)} kinds ever fired in ten years"
        assert peak > 0, "nothing ever happened anywhere in ten years"
        return f"{len(seen)} kinds seen over 10 years, at most {peak} live at once"

    @check("the register records what you saw, and only what you saw")
    def _():
        game, system = _ported("register")
        assert market_sim.summary(game)["ports"] == 0, "the book starts written"

        market_sim.note_prices(game, system)
        assert market_sim.summary(game)["ports"] == 1
        assert market_sim.age_of(game, system.id) == 0

        other = next(s for s in game.galaxy.systems
                     if s.market and s.id != system.id)
        assert market_sim.age_of(game, other.id) is None, (
            "the register knows a port you have never stood in")

        cid = next(c for c in system.market.stock)
        rows = market_sim.best_markets(game, cid)
        assert [r["system"].id for r in rows] == [system.id], (
            "best_markets returned somewhere unvisited")
        return "one port noted, the rest unknown"

    @check("a noted price goes stale")
    def _():
        game, system = _ported("stale")
        market_sim.note_prices(game, system)
        assert market_sim.confidence(0) == 1.0
        fresh = market_sim.confidence(market_sim.age_of(game, system.id))
        assert fresh > 0.99, "a note taken today is not fresh"

        game.day += STALE_DAYS // 2
        middling = market_sim.confidence(market_sim.age_of(game, system.id))
        assert 0.3 < middling < 0.7, f"half-life confidence is {middling:.2f}"

        game.day += STALE_DAYS
        assert market_sim.confidence(market_sim.age_of(game, system.id)) == 0.0, (
            "a note years old is still trusted")
        return f"1.00 fresh → {middling:.2f} at half-life → 0.00 stale"

    @check("the register ranks the best buyer first")
    def _():
        game, system = _ported("rank")
        cid = next(c for c in system.market.stock)
        for index, target in enumerate(
                [s for s in game.galaxy.systems if s.market][:4]):
            market_sim.note_prices(game, target)
            # Rewrite the noted price so the ordering is unambiguous.
            market_sim.book(game)[str(target.id)].sell[cid] = 100 + index * 50
        rows = market_sim.best_markets(game, cid, selling=True)
        prices = [r["price"] for r in rows]
        assert prices == sorted(prices, reverse=True), f"not ranked: {prices}"
        assert prices[0] >= 250, f"best buyer is {prices[0]}"
        return f"best first: {prices}"

    @check("news only reaches you from places you know")
    def _():
        game = new_game("news")
        unknown = next(s for s in game.galaxy.systems
                       if not s.visited and s.id != game.location_id)
        assert not market_sim.known_of(game, unknown.id), (
            "news arrives from a system never visited")
        unknown.visited = True
        assert market_sim.known_of(game, unknown.id), (
            "no news from a system you have been to")
        return "silence from unvisited space"

    @check("shocks and the register survive a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game, system = _ported("persist-trade")
        market_sim.note_prices(game, system)
        cid = next(c for c in system.market.stock)
        game.shocks = [Shock(id=7, kind="blight", system_id=system.id,
                             commodity=cid, until=game.day + 150)]
        market_sim.apply_to_markets(game)
        priced = buy_price(system.market, cid)

        back = decode(json.loads(json.dumps(encode(game))))
        assert len(market_sim.all_shocks(back)) == 1, "the shock was lost"
        assert market_sim.age_of(back, system.id) == 0, "the register emptied"
        reloaded = back.galaxy.systems[system.id]
        assert buy_price(reloaded.market, cid) == priced, (
            "the shock stopped biting after a reload")
        return "one shock and one noted port came back, still priced"
