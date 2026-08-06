"""Solvency checks — money cannot be conjured, and forecasts read the ledger.

The 2026-08-04 economy review's residue, as played claims: every exploit here
was measured live before it was fixed, and each check performs the move the
exploit used rather than asserting a constant. The theme is one rule worn four
ways: **the number a screen quotes, a breaker pays, or an ending counts must
come from the same function the till actually moves money through.**
"""

from __future__ import annotations

import re
from pathlib import Path

from ..core.rng import RNG
from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..data.colonies import COLONIES
from ..data.parts import material_value
from ..data.robots import ROBOTS
from ..sim import diplomacy as dip
from ..sim import exchequer as ex
from ..sim import market as market_sim
from ..sim import robots as robots_sim
from ..sim import shipyard
from ..sim import threat as threat_sim
from ..sim.encounters import make_enemy
from ..sim.ship import make_ship
from ..world import economy
from .harness import Suite


def _worth(cost: dict) -> float:
    """A bill in credit-equivalents, matter valued as itself."""
    return (cost.get("credits", 0)
            + sum(material_value(k) * n for k, n in cost.items()
                  if k != "credits"))


def run(suite: Suite) -> None:
    check = suite.check

    @check("nothing outside the counter quotes the raw prices")
    def _():
        # `world.economy.buy_price`/`sell_price` are the *inputs* to a quote,
        # not a quote: `market.quote_buy`/`quote_sell` add the grudge bias,
        # the office rate and the sell-under-buy clamp. Every module that
        # imported the raw pair quoted a figure the counter would not honour
        # — the freight desk, the bunkering button, the bridge's market verb
        # and `is_stranded` all did. Two exceptions are deliberate and
        # documented in place: `contracts` prices generation neutrally, and
        # `industry` forecasts on a throwaway market twin with no game to ask.
        allowed = {"contracts.py", "industry.py", "market.py"}
        root = Path(__file__).resolve().parent.parent
        offenders = []
        for pkg in ("sim", "ui", "bridge"):
            for py in sorted((root / pkg).glob("*.py")):
                if py.name in allowed:
                    continue
                text = py.read_text()
                for m in re.finditer(
                        r"from\s+\.\.world\.economy\s+import\s+([^\n(]+|\([^)]*\))",
                        text):
                    names = m.group(1)
                    if re.search(r"\b(buy_price|sell_price)\b", names):
                        offenders.append(f"{pkg}/{py.name}")
        assert not offenders, (
            f"raw prices imported outside the counter: {offenders} — quote "
            "through sim/market, or document the exception here")
        return ("sim/, ui/ and bridge/ take prices from the counter; "
                f"{len(allowed)} documented exceptions")

    @check("a hull is always worth less broken up than the cheapest build")
    def _():
        # The exploit: `scrap_value` recomputed the bill *without* the
        # fabricator discount the build was given, and paid a flat 60 a tonne
        # for the matter — +146,470 credits per build-and-scrap cycle.
        # `start_build` pays `cost_of(..., fabricating)` verbatim, so the
        # discounted bill below is exactly what the cheapest builder paid.
        rng = RNG("scrap-sweep")
        hulls = [(CHASSIS_BY_ID[cid], make_ship(cid, [], "bare"))
                 for cid in sorted(CHASSIS_BY_ID)]
        for fid in ("freeholds", "concordat", "sanhedrin"):
            for d in (0.8, 1.6, 3.0):
                enemy = make_enemy(rng, fid, d)
                hulls.append((CHASSIS_BY_ID[enemy["ship"].chassis],
                              enemy["ship"]))
        margins = []
        for chassis, ship in hulls:
            cheap = _worth(shipyard.cost_of(chassis, ship.fitted,
                                            fabricator=True))
            full = _worth(shipyard.cost_of(chassis, ship.fitted,
                                           fabricator=False))
            got = shipyard.scrap_value(ship)
            assert got < cheap <= full, (
                f"{chassis.id}: scrapped for {got:,.0f} against a cheapest "
                f"build of {cheap:,.0f}")
            margins.append(got / cheap)
        return (f"{len(hulls)} hulls: scrap pays "
                f"{min(margins):.0%}–{max(margins):.0%} of the cheapest bill, "
                "never more")

    @check("a tonne of contraband does not conjure a market")
    def _():
        # One dumped tonne used to lift the supply off zero; the next tick
        # adopted that as a baseline at the scarcity cap, and a port
        # `make_market` refused the good then stocked it at 2.75× base for
        # ever. The tonnes still land on the quay; the market does not appear.
        game = new_game("conjure")
        rng = RNG("conjure-tick")
        found = None
        for system in game.galaxy.systems:
            if system.market is None:
                continue
            s = system.market.stock.get("wildseed")
            if s is not None and s.base <= 0 and s.supply <= 0:
                found = system
                break
        assert found is not None, "no port refuses wildseed in this sector"
        market = found.market
        economy.apply_sale(market, "wildseed", 1.0)
        for _day in range(400):
            economy.tick_market(market, 1.0, rng, level=found.port.level)
        s = market.stock["wildseed"]
        assert economy.buy_price(market, "wildseed") is None, (
            "a year after one dumped tonne, the port sells contraband it was "
            "built without")
        assert s.base <= 0 and s.supply <= 0, (s.base, s.supply)
        assert s.units >= 1.0, "the dumped tonnes vanished from the quay"
        return (f"{found.name} took the tonne, and 400 days later still "
                "does not trade the good")

    @check("machines cannot spend money the captain does not have")
    def _():
        # The one unguarded `credits -=` in the game. Unpaid is starved now,
        # and a starved machine spends itself instead of the treasury.
        klass = next(k for k in ROBOTS if k.upkeep.get("credits"))
        game = new_game("robot-debt")
        game.robots = [robots_sim.Robot(id=1, class_id=klass.id, name="Tick")]
        rng = RNG("robot-debt")
        game.credits = 1_000.0
        robots_sim.tick(game, 30, rng)
        fed = game.robots[0].condition
        assert game.credits < 1_000.0, "a funded machine was not charged"

        game.credits = 0.0
        game.robots[0].condition = 1.0
        robots_sim.tick(game, 30, rng)
        starved = game.robots[0].condition
        assert game.credits == 0.0, (
            f"the treasury went to {game.credits:,.2f} with nothing in it")
        assert starved < fed, (
            "an unpaid machine wore no faster than a paid one")
        return (f"paid wears to {fed:.3f}, unpaid to {starved:.3f}, "
                "and the purse never goes below nought")

    @check("a thriving capital is worth promoting, and a rich power does it")
    def _():
        # By arithmetic a *bare* berth never promotes (level 2 clears exactly
        # nothing more than level 1), so no power ever promoted anything in
        # 2,000 played days. The forecast now reads the same multipliers the
        # ledger pays — capital, industries — through `would_yield`.
        from ..sim import industry
        game = new_game("promotion")
        capital = next(s for s in game.galaxy.systems
                       if s.port is not None and s.port.capital)
        power = capital.port.faction
        while capital.port is not None and capital.port.level > 1:
            ex.demote(game, capital)
        assert capital.port is not None and capital.port.level == 1
        held = industry.state(game).held
        for tech in ("t-one", "t-two", "t-three"):
            held.setdefault(tech, []).append(power)

        told_promote = ex.payback(game, power, ex.STEP_COST[2],
                                  "promote:2", capital)
        assert told_promote < float("inf"), (
            "a capital with three industries still reads as never paying")

        purse = ex.purse(game, power)
        purse.credits = 600_000.0
        seen = []
        for _ in range(60):
            told = ex._invest(game, power, purse)
            if told is None:
                break
            seen.append(told)
        assert any("is now a" in t for t in seen), (
            f"sixty investments and no promotion among them: {seen[:6]}")
        return (f"promote:2 at the capital pays back in {told_promote:,.0f} "
                f"days; the purse bought {len(seen)} works including a "
                "promotion")

    @check("every colony class has ground the generator can actually grow")
    def _():
        # SOL-FORGE required a body of kind "star", and `_kind_for_orbit`
        # produces no such kind — 0 candidate bodies in 1,223 over eight
        # sectors, a whole colony class unbuildable by construction.
        producible = set()
        for seed in ("ground-a", "ground-b", "ground-c"):
            game = new_game(seed)
            for system in game.galaxy.systems:
                producible |= {b.kind for b in system.bodies}
        for c in COLONIES:
            assert set(c.sites) & producible, (
                f"{c.name} sites on {c.sites}, and no generated sector grows "
                f"any of them (seen: {sorted(producible)})")
        return (f"{len(COLONIES)} classes, all with ground among "
                f"{sorted(producible)}")

    @check("the Cartel ending counts living prices, not a filing cabinet")
    def _():
        # `priced` counted register keys — quotes twenty years stale and
        # ports that had since closed both counted toward cornering a market.
        game = new_game("cartel-ledger")
        for system in game.galaxy.systems:
            if system.market is not None:
                market_sim.note_prices(game, system)
        game.credits = threat_sim.CARTEL_PURSE
        fresh = threat_sim.victory_progress(game)["cartel"]
        assert fresh[2], f"a fully noted, fully funded sector did not corner: {fresh}"

        for quote in game.register.values():
            quote.day = game.day - 10_000
        stale = threat_sim.victory_progress(game)["cartel"]
        assert not stale[2], "twenty-year-old quotes still corner the market"
        assert stale[0] == 0, f"stale quotes still counted: {stale[0]}"

        # And a port that closes takes its quote off the count with it.
        # (One that *can* close — a capital never does, and nothing closes
        # with the captain's hull alongside.)
        noted = [s for s in game.galaxy.systems
                 if s.market is not None and not s.port.capital
                 and s.id != game.location_id][:3]
        for system in noted:
            market_sim.note_prices(game, system)
        alive = threat_sim.victory_progress(game)["cartel"][0]
        closing = noted[0]
        while closing.port is not None:
            ex.demote(game, closing)
        assert closing.market is None, "demotion to nothing left the market"
        after = threat_sim.victory_progress(game)["cartel"][0]
        assert after == alive - 1, (alive, after)
        return (f"fresh notes corner ({fresh[0]}/{fresh[1]}); stale ones "
                "count nothing; a closed port drops off the ledger")
