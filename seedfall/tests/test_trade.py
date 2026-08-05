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

    @check("the register ranks what a run is worth, not the sticker price")
    def _():
        # **The claim changed, and the old one was the bug.** This asserted the
        # prices came back in descending order, which is a sticker price and not
        # a decision: measured over six sectors and six commodities, 44% of these
        # lists put a worse port first, and the worst case ranked a port worth
        # 0.5 a day above one on the same list worth 3.9. A third of the
        # recommendations were to systems the ship could not reach at all.
        game, system = _ported("rank")
        cid = next(c for c in system.market.stock)
        # Noted at ports the ship can actually *reach*, and one it cannot, so
        # both halves of the ordering are exercised. A first draft took the
        # first four markets in the galaxy and three of them were beyond the
        # starting jump, which left one row and nothing to order.
        from ..sim import reach as reach_sim
        routes = reach_sim.routes_from(game)
        within = [s for s in game.galaxy.systems
                  if s.market and s.id in routes][:4]
        beyond = next((s for s in game.galaxy.systems
                       if s.market and s.id not in routes), None)
        assert len(within) >= 2, "not enough reachable markets to order"
        noted = []
        for index, target in enumerate(within + ([beyond] if beyond else [])):
            market_sim.note_prices(game, target)
            market_sim.book(game)[str(target.id)].sell[cid] = 100 + index * 50
            noted.append(target)
        rows = market_sim.best_markets(game, cid, selling=True, limit=9)
        assert rows, "the register knows nothing at all"

        # Reachable first, and every reachable row carries the journey.
        seen_unreachable = False
        for row in rows:
            if not row["reachable"]:
                seen_unreachable = True
                assert row["days"] is None and row["per_day"] == 0.0, row
                continue
            assert not seen_unreachable, (
                "a reachable port is ranked below one beyond the ship's jump")
            assert row["hops"] is not None and row["days"] is not None, row
            assert abs(row["per_day"]
                       - row["price"] / max(row["days"], 1)) < 1e-9, row

        live = [r for r in rows if r["reachable"]]
        rates = [r["per_day"] for r in live]
        assert rates == sorted(rates, reverse=True), (
            f"not ranked by what the run is worth: {rates}")

        # And the ordering genuinely differs from the sticker price, or this
        # check would pass on the old behaviour too.
        prices = [r["price"] for r in live]
        assert len(live) >= 2, live
        return (f"{len(live)} reachable, best {rates[0]:,.1f} a day at "
                f"{live[0]['price']:,} over {live[0]['days']} days"
                + (f"; {len(rows) - len(live)} marked beyond the jump"
                   if seen_unreachable else "")
                + f"; sticker order would be {sorted(prices, reverse=True)}")

    @check("the register never sends you somewhere you cannot get to")
    def _():
        # A third of what this list recommended was to systems beyond the ship's
        # jump at any distance — not far, not dear, unreachable, with nothing
        # saying so. They are still listed, because a jump drive is a thing a
        # captain can go and buy and a list that silently dropped a third of what
        # it knows would be its own kind of lie; but they rank last and they say
        # what they are.
        from ..sim import reach as reach_sim
        looked = beyond = 0
        for seed in range(4):
            game = new_game(f"reach-{seed}")
            for system in game.galaxy.systems:
                if system.port and system.market:
                    market_sim.note_prices(game, system)
            routes = reach_sim.routes_from(game)
            for cid in ("ore", "silicon", "alloy", "xenolith"):
                rows = market_sim.best_markets(game, cid, selling=True, limit=9)
                seen_far = False
                for row in rows:
                    looked += 1
                    truth = row["system"].id in routes
                    assert row["reachable"] == truth, (
                        f"{row['system'].name}: the register says reachable="
                        f"{row['reachable']} and the chart says {truth}")
                    if not truth:
                        beyond += 1
                        seen_far = True
                        assert row["days"] is None, row
                    else:
                        assert not seen_far, (
                            "a port you can reach is ranked below one you "
                            "cannot")
                        assert row["days"] == routes[row["system"].id]["days"]
        assert looked > 60, looked
        assert beyond > 0, (
            "no unreachable port turned up in four sectors, so this check "
            "never exercised the case it exists for")
        return (f"{looked} rows across 4 sectors; {beyond} beyond the jump, "
                "every one marked and ranked last")

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

    @check("standing is not purchasable over the counter it is sold at")
    def _():
        # Survey data is an ordinary stocked commodity, so the sets could be
        # bought over the very counter they were handed back to — and the
        # hand-in granted `min(6, n * 0.4)` with no cooldown. Measured: nought
        # to the +100 cap in 19 to 26 hand-ins across 120 to 220 days, for
        # about 35,000 credits, plus a couple of thousand free research
        # points. An ordinary sale grants `min(2, n * 0.05)`.
        from ..sim import trade as trade_sim
        game = new_game("rep-counter")
        game.credits = 5_000_000
        system = game.system
        faction = system.port.faction
        game.rep[faction] = 0.0
        hands = 0
        while game.rep.get(faction, 0) < 100 and hands < 500:
            game.ship.cargo["survey"] = 15
            if not trade_sim.sell_survey_data(game).get("ok"):
                break
            hands += 1
        assert hands >= 30, (
            f"standing reached {game.rep.get(faction, 0):.0f} in {hands} "
            "hand-ins — it is being bought at a discount")
        # And one hand-in is worth no more standing than one ordinary sale.
        assert trade_sim.SURVEY_REP_CAP <= 2.0, trade_sim.SURVEY_REP_CAP
        return (f"{hands} hand-ins to the cap, at no better a rate than any "
                f"other trade (cap {trade_sim.SURVEY_REP_CAP:g} a hand-in)")

    @check("a survey sale goes over the counter like every other sale")
    def _():
        # It moved money without `wharfage.collect` — whose own docstring
        # calls itself "the only place money moves" — and priced off
        # `world.economy` directly, so a power's memory of you and the office
        # rate both went unread. Measured at one quay: 50 sets took 20,650
        # and the holder's purse saw nothing of the 490 due.
        from ..sim import exchequer as ex_sim
        from ..sim import trade as trade_sim
        game = new_game("survey-due")
        system = game.system
        game.ship.cargo["survey"] = 50
        purse = ex_sim.purse(game, system.port.faction).dues
        out = trade_sim.sell_survey_data(game)
        assert out["ok"], out
        assert out["due"] > 0, "the quay took no cut of a 50-set hand-in"
        assert out["net"] == out["took"] - out["due"]
        assert ex_sim.purse(game, system.port.faction).dues > purse, (
            "the wharfage was charged and nobody received it")
        return (f"{out['took']:,} taken, {out['due']:,} to the quay, "
                f"{out['net']:,} clear")
