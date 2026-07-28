"""Buying and selling over a counter.

These were methods on `PortView`. The transaction — what it costs, what the
port thinks of you afterwards, what the quartermaster notices — was written
into the screen, so nothing but a mouse could perform it and no headless run
could measure it. Same defect the engagement aftermath had, spread thinner.

The screen calls these and draws what comes back.
"""

from __future__ import annotations

from ..data.commodities import BY_ID, bulk_of
from . import customs as customs_sim
from . import diplomacy as dip_sim
from . import loyalty as loyalty_sim
from .ship import add_cargo, cargo_free
from ..world.economy import apply_sale, apply_trade, buy_price, sell_price

#: A sale worth this much is a sale the quartermaster notices.
NOTICED = 2500

#: Standing given up for buying contraband over a counter that sells it.
BUY_TAINT = 3.0

#: And for selling it to somebody who does not deal in it.
SELL_TAINT = 8.0


def buy(game, cid: str, units: int) -> dict:
    """Take `units` off the local market, as many as can be paid for and stowed."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    rep = game.rep.get(system.port.faction, 0)
    price = buy_price(system.market, cid, rep, game.ship_stats.trade)
    if price is None:
        return {"ok": False, "why": "They do not stock it."}

    room = int(cargo_free(game.ship, game.ship_stats) / bulk_of(cid))
    afford = int(game.credits // price)
    stocked = system.market.stock[cid].units
    n = min(units, room, afford, stocked)
    if n <= 0:
        why = ("Not enough credits." if afford < 1 else
               "No room in the hold." if room < 1 else
               "The port has none left.")
        return {"ok": False, "why": why}

    game.credits -= n * price
    add_cargo(game.ship, cid, n)
    apply_trade(system.market, cid, n)
    if not BY_ID[cid].legal:
        game.adjust_rep(system.port.faction, -BUY_TAINT)
    game.add_log(f"Bought {n} {BY_ID[cid].short} at {price:,} — "
                 f"{n * price:,}.")
    return {"ok": True, "units": n, "price": price, "paid": n * price}


def sell(game, cid: str, units: int) -> dict:
    """Sell over the posted counter. Refused for anything this power seizes."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    if customs_sim.outlaws(system.port.faction, cid):
        return {"ok": False,
                "why": "Not over this counter. Not on this station."}

    rep = game.rep.get(system.port.faction, 0)
    price = sell_price(system.market, cid, rep, game.ship_stats.trade)
    n = min(units, game.ship.cargo.get(cid, 0))
    if n <= 0 or price is None:
        return {"ok": False, "why": "Nothing aboard to sell."}

    out = {"ok": True, "units": n, "price": price, "took": n * price,
           "logged": False}
    fac = dip_sim.FACTIONS_BY_ID.get(system.port.faction)
    if not BY_ID[cid].legal and (not fac or cid not in fac.sells):
        game.adjust_rep(system.port.faction, -SELL_TAINT)
        out["logged"] = True

    game.credits += n * price
    if n * price >= NOTICED:
        loyalty_sim.record(game, "trade_profit",
                           scale=min(2.0, n * price / 6000))
    add_cargo(game.ship, cid, -n)
    apply_sale(system.market, cid, n)
    game.adjust_rep(system.port.faction,
                    min(2, n * 0.05)
                    * dip_sim.agenda_bonus(game, system.port.faction, cid))
    game.add_log(f"Sold {round(n)} {BY_ID[cid].short} at {price:,} — "
                 f"{round(n * price):,}.")
    return out


def sell_survey_data(game) -> dict:
    """Hand over accumulated survey sets. Worth standing as well as money."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    n = game.ship.cargo.get("survey", 0)
    if n < 1:
        return {"ok": False, "why": "No survey data aboard."}
    rep = game.rep.get(system.port.faction, 0)
    price = sell_price(system.market, "survey", rep, game.ship_stats.trade) or 250
    took = round(n * price)
    game.credits += took
    add_cargo(game.ship, "survey", -n)
    game.adjust_rep(system.port.faction, min(6, n * 0.4))
    game.research.banked += n * 6
    game.add_log(f"Sold {round(n)} survey sets for {took:,}.", "good")
    return {"ok": True, "units": n, "price": price, "took": took}
