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
from . import market as market_sim
from . import officials as officials_sim
from . import wharfage as wharfage_sim
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


#: What "a quiet price" is worth: goods move at the office rate, which is
#: about twelve per cent inside the posted one, in whichever direction helps.


def buy(game, cid: str, units: int) -> dict:
    """Take `units` off the local market, as many as can be paid for and stowed."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    # `quote_buy` is the price, office rate included — the screen and the
    # counter read the same helper so they cannot disagree.
    price = market_sim.quote_buy(game, system, cid)
    if price is None:
        return {"ok": False, "why": "They do not stock it."}

    room = int(cargo_free(game.ship, game.ship_stats) / bulk_of(cid))
    # Sized against what a tonne actually costs here — the posted price plus the
    # quay's cut. Filling the hold to the last credit of the posted price and
    # then being unable to pay the due is the same defect as an approach that
    # orders burns it has no mass for.
    afford = int(game.credits // wharfage_sim.unit_cost(game, system, price))
    stocked = system.market.stock[cid].units
    n = min(units, room, afford, stocked)
    if n <= 0:
        why = ("Not enough credits." if afford < 1 else
               "No room in the hold." if room < 1 else
               "The port has none left.")
        return {"ok": False, "why": why}

    game.credits -= n * price
    due = wharfage_sim.collect(game, system, n * price)
    # "This once" means this once: the office rate is spent by using it.
    officials_sim.spend_once(game, system, "quiet_price")
    add_cargo(game.ship, cid, n)
    apply_trade(system.market, cid, n)
    officials_sim.dealt_with(game, system, min(2.0, n * price / 9000))
    if not BY_ID[cid].legal:
        game.adjust_rep(system.port.faction, -BUY_TAINT)
    game.add_log(f"Bought {n} {BY_ID[cid].short} at {price:,} — "
                 f"{n * price:,}." + (f" Wharfage {due:,}." if due else ""))
    return {"ok": True, "units": n, "price": price, "paid": n * price,
            "due": due, "spent": n * price + due}


def sell(game, cid: str, units: int) -> dict:
    """Sell over the posted counter. Refused for anything this power seizes."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    if customs_sim.outlaws(system.port.faction, cid):
        return {"ok": False,
                "why": "Not over this counter. Not on this station."}

    price = market_sim.quote_sell(game, system, cid)
    n = min(units, game.ship.cargo.get(cid, 0))
    if n <= 0 or price is None:
        return {"ok": False, "why": "Nothing aboard to sell."}

    out = {"ok": True, "units": n, "price": price, "took": n * price,
           "logged": False, "due": 0, "net": n * price}
    fac = dip_sim.FACTIONS_BY_ID.get(system.port.faction)
    if not BY_ID[cid].legal and (not fac or cid not in fac.sells):
        game.adjust_rep(system.port.faction, -SELL_TAINT)
        out["logged"] = True

    game.credits += n * price
    out["due"] = wharfage_sim.collect(game, system, n * price)
    out["net"] = n * price - out["due"]
    officials_sim.spend_once(game, system, "quiet_price")
    if n * price >= NOTICED:
        loyalty_sim.record(game, "trade_profit",
                           scale=min(2.0, n * price / 6000))
    add_cargo(game.ship, cid, -n)
    apply_sale(system.market, cid, n)
    # Trading here is dealing with whoever runs the quay. This and `buy` are
    # the only routes by which a harbourmaster comes to know you at all.
    officials_sim.dealt_with(game, system, min(2.0, n * price / 9000))
    game.adjust_rep(system.port.faction,
                    min(2, n * 0.05)
                    * dip_sim.agenda_bonus(game, system.port.faction, cid))
    game.add_log(f"Sold {round(n)} {BY_ID[cid].short} at {price:,} — "
                 f"{round(n * price):,}."
                 + (f" Wharfage {out['due']:,}, {out['net']:,} clear."
                    if out["due"] else ""))
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


def jettison(game, cid: str, tonnes: float | None = None) -> dict:
    """Put cargo over the side.

    The only way to dump anything used to be the contraband panel, which shows
    up solely when you are carrying contraband at a port that outlaws it. So a
    full hold and no reaction mass was a hard stranding: you cannot mine ice
    for fuel with nowhere to put it, and you cannot jump without the fuel. The
    project already holds that an empty tank must not be a deadlock; a full
    hold is the same rule from the other side.
    """
    held = game.ship.cargo.get(cid, 0.0)
    if held <= 0:
        return {"ok": False, "why": "None of that aboard."}
    going = held if tonnes is None else min(held, tonnes)
    add_cargo(game.ship, cid, -going)
    good = BY_ID.get(cid)
    game.add_log(f"Vented {going:.0f} t of {good.short if good else cid} "
                 "to space.", "warn")
    return {"ok": True, "tonnes": going, "left": held - going}
