"""Where you may deal from, and what the distance costs.

A play-test asked it as a question: **where can you trade from?** The Port
priced and bought for any hull anywhere in the system — survey data sold at
the Fleet Hub from seven AU out — while the shipyard wanted you alongside
and the berth lesson said the Port opens once you are. Three counters, three
rules, and one of them was no rule at all.

`sim/quayside.py` is the one rule. The claims:

- **Alongside, the cranes are theirs and cost nothing** — the bill is the
  goods and the quay's own due, exactly as before.
- **Out in the system the goods are lightered, and the gap is the price**:
  small change from orbit off the quay, double from an AU, eightfold from
  the seven the play-test sold from.
- **Your own boat carries the first tonnes free**, up to what she lifts in a
  visit and only within her own range — which is a use for the cradle a
  hangar deck sells you.
- **A bench of survey sets is carried in by hand**: that one is a rule and
  not a price, and it is refused until somebody is at the counter.
- **The board says what the till charges** — the port's own line, the
  contract card's sourcing cost, and the counter, all one number.
- **And there is a door out of it**: the harbourmaster brings you in, from
  the Port screen or from the first officer's counsel.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.commodities import bulk_of
from ..sim import (contracts as contract_sim, counsel_doors, crossing,
                   flight, market as market_sim, places, quayside,
                   trade as trade_sim)
from .harness import Suite
from .quay import stand_at


def _at_home(seed: str = "quayside", credits: float = 400_000):
    game = new_game(seed)
    game.credits = credits
    stand_at(game, game.system)
    return game


def _cast_off(game, au: float = 0.0):
    """In the system, alongside nothing — and optionally a long way out.

    `flight.stand_off` is the door a jump's arrival uses, and it takes the
    place to hold, so "seven AU out" is a real position rather than a flag.
    """
    if not au:
        flight.hold_at(game, flight.current_body(game))
        game.berth = game.ashore = ""
        return game
    at = flight.ship_position(game)
    flight.stand_off(game, (at[0] + au, at[1], at[2]))
    return game


def _tradeable(game, system) -> str:
    return next(c for c in system.market.stock
                if market_sim.quote_buy(game, system, c)
                and market_sim.quote_sell(game, system, c))


def run(suite: Suite) -> None:
    check = suite.check

    @check("alongside the quay the cranes are theirs, and cost nothing")
    def _():
        game = _at_home("alongside")
        system = game.system
        assert quayside.alongside(game), "a chronicle opens made fast"
        cid = _tradeable(game, system)
        before = game.credits
        got = trade_sim.buy(game, cid, 20)
        assert got["ok"], got
        assert got["lighter"] == 0, got
        assert abs((before - game.credits)
                   - (got["paid"] + got["due"])) < 0.01
        assert quayside.fee(game, 500.0) == 0, "charged for the quay's crane"
        assert "cranes are theirs" in quayside.line(game)
        return (f"{got['units']} t over the counter for {got['paid']:,} and "
                f"{got['due']:,} of due — not a credit of lighterage")

    @check("out in the system it is lightered, and the gap is the price")
    def _():
        game = _at_home("lightered")
        system = game.system
        cid = _tradeable(game, system)
        game.ship.cargo[cid] = 300
        rows = []
        # In orbit off the quay, and then an AU out, and then seven.
        _cast_off(game)
        near = quayside.fee(game, 100.0)
        rows.append(("in orbit", quayside.reach_au(game), near))
        for au in (1.0, 7.0):
            _cast_off(game, au)
            rows.append((f"{au:g} AU", quayside.reach_au(game),
                         quayside.fee(game, 100.0)))
        assert near > 0, "a hull off the quay was lightered for nothing"
        assert rows[1][2] > rows[0][2] * 1.5, rows
        assert rows[2][2] > rows[1][2] * 2.5, rows
        # And it is charged at the till, and disclosed.
        _cast_off(game)
        before = game.credits
        sold = trade_sim.sell(game, cid, 60)
        assert sold["ok"] and sold["lighter"] > 0, sold
        assert abs((game.credits - before)
                   - (sold["took"] - sold["due"] - sold["lighter"])) < 0.01
        assert sold["net"] == sold["took"] - sold["due"] - sold["lighter"]
        return "; ".join(f"{where} ({au:,.2f} AU): {cost:,} on 100 t"
                         for where, au, cost in rows)

    @check("your own boat carries the first tonnes free, within her own range")
    def _():
        from ..sim import craft as craft_sim
        game = _at_home("boat-free")
        _cast_off(game)
        craft = craft_sim.aboard(game)[0]
        free = quayside.own_lift(game)
        assert free > 0, "a craft on the cradle carried nothing"
        assert quayside.fee(game, free * 0.5) == 0, free
        assert quayside.fee(game, free + 50) > 0
        # A tender is what a captain buys for this: nine tonnes a visit.
        craft.class_id = "dory"
        roomy = quayside.own_lift(game)
        assert roomy > free * 3, (free, roomy)
        # Lost, and the hull lighters everything.
        game.craft = []
        assert quayside.own_lift(game) == 0.0
        assert quayside.fee(game, 1.0) >= quayside.LIGHTER_LEAST
        # And she does not work across a system.
        game.craft = [craft]
        _cast_off(game, 7.0)
        assert quayside.own_lift(game) == 0.0, "a ship's boat crossed 7 AU"
        return (f"a WASP lifts {free:g} t a visit free and a DORY {roomy:g}; "
                "neither of them from seven AU out")

    @check("a bench of survey sets is carried in by hand")
    def _():
        game = _at_home("survey")
        game.ship.cargo["survey"] = 40
        sold = trade_sim.sell_survey_data(game)
        assert sold["ok"], sold
        # Off the quay, with nobody ashore, there is nobody to hand them to.
        game.ship.cargo["survey"] = 40
        _cast_off(game)
        refused = trade_sim.sell_survey_data(game)
        assert not refused["ok"] and "counter" in refused["why"], refused
        # The crew across by boat is somebody at the counter.
        game.ashore = f"port-{game.system.id}"
        allowed = trade_sim.sell_survey_data(game)
        assert allowed["ok"], allowed
        return (f"{sold['sets'] if 'sets' in sold else 40} sets over the "
                "counter alongside; refused from orbit with nobody ashore, "
                "and taken once the crew is across")

    @check("the board says what the till charges, and the harbourmaster is the way out")
    def _():
        game = _at_home("board")
        system = game.system
        _cast_off(game)
        said = quayside.line(game)
        assert "lighters" in said and "Alongside" in said, said
        quote = quayside.quote(game)
        assert not quote["alongside"] and quote["rate"] > 0
        assert not quote["at_counter"]
        # A cargo contract's card prices the sourcing the captain will pay,
        # lighterage included — the card used to under-quote by the whole
        # of it.
        cid = next(c for c in system.market.stock
                   if market_sim.quote_buy(game, system, c)
                   and not game.ship.cargo.get(c))
        posted = market_sim.quote_buy(game, system, cid)
        contract = contract_sim.Contract(
            id=1, kind="deliver", issuer=system.port.faction,
            issued_at=system.id, title="t", posting="p", commodity=cid,
            amount=20)
        card = contract_sim.quote(game, contract)
        lighter = quayside.fee(game, 20 * bulk_of(cid))
        assert lighter > 0, "a card quoted from orbit with nothing to lift"
        assert card["cost"] >= posted * 20 + lighter, (card, posted, lighter)
        spent_before = game.credits
        bought = trade_sim.buy(game, cid, 20)
        if bought.get("ok") and bought["units"] == 20:
            spent = spent_before - game.credits
            assert abs(spent - card["cost"]) < max(2.0, card["cost"] * 0.02), (
                f"the card quoted {card['cost']:,} and it cost {spent:,.0f}")
        # Counsel offers the way out of it, and the way out works.
        moves = {m["id"]: m for m in counsel_doors.come_alongside(game)}
        assert "dock" in moves, moves
        place = places.by_id(game, f"port-{system.id}")
        assert crossing.cross(game, place, "dock")["ok"]
        assert quayside.alongside(game)
        assert quayside.fee(game, 500.0) == 0
        return ("the board names the rate, the card prices the sourcing, and "
                "the harbourmaster's hour puts it all back to nothing")
