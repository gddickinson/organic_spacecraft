"""Buying and selling over a counter.

These were methods on `PortView`. The transaction — what it costs, what the
port thinks of you afterwards, what the quartermaster notices — was written
into the screen, so nothing but a mouse could perform it and no headless run
could measure it. Same defect the engagement aftermath had, spread thinner.

The screen calls these and draws what comes back.
"""

from __future__ import annotations

from ..data.commodities import BY_ID, bulk_of
from . import assembly
from . import customs as customs_sim
from . import inquiry
from . import market as market_sim
from . import officials as officials_sim
from . import quayside as quayside_sim
from . import wharfage as wharfage_sim
from . import diplomacy as dip_sim
from . import loyalty as loyalty_sim
from . import renown as renown_sim
from .ship import add_cargo, cargo_free
from ..world.economy import apply_sale, apply_trade

#: A sale worth this much is a sale the quartermaster notices.
NOTICED = 2500

#: Standing given up for buying contraband over a counter that sells it.
BUY_TAINT = 3.0

#: And for selling it to somebody who does not deal in it.
SELL_TAINT = 8.0


#: What "a quiet price" is worth: goods move at the office rate, which is
#: about twelve per cent inside the posted one, in whichever direction helps.


#: How long a counter remembers selling you something.
#:
#: **Standing was for sale.** Every sale granted `min(2, n * 0.05)` with no
#: cooldown and no question of where the goods came from, so buying at a
#: counter and selling straight back to it bought standing with the spread:
#: measured, 40 to 100 with the Charter in **zero game days** for about 8,000
#: credits — which, with the survey loop, opened Concord and Apostasy by day
#: 201. A port is glad of what you *bring*; its own stock handed back is not
#: trade. So a sale counts for standing only on tonnes this counter did not
#: sell you inside this window — long enough to cover a loiter, short enough
#: that a round trip away and back is ordinary business.
BOUGHT_MEMORY = 60


def _bought(game, system, cid: str, units: float) -> None:
    """Remember that this counter sold you these."""
    ledger = system.market.yours
    had, _day = ledger.get(cid, (0.0, game.day))
    ledger[cid] = [(had if game.day - _day <= BOUGHT_MEMORY else 0.0) + units,
                   game.day]


def imported(game, system, cid: str, units: float) -> float:
    """How many of these tonnes this counter did *not* sell you lately.

    Spends the memory as it goes: tonnes sold back are forgotten, so the
    next honest cargo is counted in full.
    """
    ledger = getattr(system.market, "yours", None) if system.market else None
    if not ledger or cid not in ledger:
        return units
    had, day = ledger[cid]
    if game.day - day > BOUGHT_MEMORY:
        ledger.pop(cid, None)
        return units
    back = min(units, had)
    if had - back > 1e-6:
        ledger[cid] = [had - back, day]
    else:
        ledger.pop(cid, None)
    return units - back


def can_buy(game, cid: str) -> tuple:
    """May a single tonne of this be bought here at all? `(ok, why)`.

    **The gate the Buy button is lit by, and the one the till refuses on.**
    They were two: the market grid lit Buy on "somebody here is selling it"
    and `buy` refused on credits, hold room and stock, so a session pressing
    a lit control was answered "no room in the hold" and "not enough
    credits". `buy` already clamps the tonnage asked for down to what will
    fit and what is affordable — asking for ten and getting three is a fair
    answer to a question about quantity — so the only thing that needs
    saying up front is whether *one* tonne is possible.
    """
    from . import enforce as enforce_sim
    dealing, refusal = enforce_sim.may_trade(game, game.system)
    if not dealing:
        return False, refusal
    system = game.system
    if not system.port:
        return False, "No port here."
    price = market_sim.quote_buy(game, system, cid)
    if price is None:
        return False, "They do not stock it."
    moving, refusal = quayside_sim.may_move(game, 1.0, system)
    if not moving:
        return False, refusal
    if int(cargo_free(game.ship, game.ship_stats) / bulk_of(cid)) < 1:
        return False, "No room in the hold."
    if game.credits < wharfage_sim.unit_cost(game, system, price):
        return False, "Not enough credits for a tonne of it."
    if system.market.stock[cid].units < 1:
        return False, "The port has none left."
    return True, ""


def buy(game, cid: str, units: int) -> dict:
    """Take `units` off the local market, as many as can be paid for and stowed."""
    # A counter that has struck you from the record does not price for you.
    # `sim/enforce.may_trade` is the one door — anathema is the only
    # instrument that closes a market, because an interdict stops you getting
    # alongside and does not stop them taking your money if you manage it.
    from . import enforce as enforce_sim
    dealing, refusal = enforce_sim.may_trade(game, game.system)
    if not dealing:
        return {"ok": False, "why": refusal}
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    # `quote_buy` is the price, office rate included — the screen and the
    # counter read the same helper so they cannot disagree.
    price = market_sim.quote_buy(game, system, cid)
    if price is None:
        return {"ok": False, "why": "They do not stock it."}

    # **And the goods have to cross the gap** (`sim/quayside`): alongside
    # the quay that is the port's crane, and from anywhere else in the
    # system it is your boat or their lighters, by the tonne.
    moving, refusal = quayside_sim.may_move(game, 1.0, system)
    if not moving:
        return {"ok": False, "why": refusal}
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
    lighter = quayside_sim.collect(game, n * bulk_of(cid), system)
    # "This once" means this once: the office rate is spent by using it.
    officials_sim.spend_once(game, system, "quiet_price")
    add_cargo(game.ship, cid, n)
    apply_trade(system.market, cid, n)
    _bought(game, system, cid, n)
    officials_sim.dealt_with(game, system, min(2.0, n * price / 9000))
    if not BY_ID[cid].legal:
        game.adjust_rep(system.port.faction, -BUY_TAINT)
    game.add_log(f"Bought {n} {BY_ID[cid].short} at {price:,} — "
                 f"{n * price:,}." + (f" Wharfage {due:,}." if due else "")
                 + (f" Lighterage {lighter:,}." if lighter else ""))
    return {"ok": True, "units": n, "price": price, "paid": n * price,
            "due": due, "lighter": lighter,
            "spent": n * price + due + lighter}


def sell(game, cid: str, units: int) -> dict:
    """Sell over the posted counter. Refused for anything this power seizes."""
    # A counter that has struck you from the record does not price for you.
    # `sim/enforce.may_trade` is the one door — anathema is the only
    # instrument that closes a market, because an interdict stops you getting
    # alongside and does not stop them taking your money if you manage it.
    from . import enforce as enforce_sim
    dealing, refusal = enforce_sim.may_trade(game, game.system)
    if not dealing:
        return {"ok": False, "why": refusal}
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    # `seizes`, not `outlaws`: the power's list *and* this world's own law
    # (`sim/lawlevel.py`). A quay that will take a good off you at the lock
    # does not also post a price for it at the desk.
    if customs_sim.seizes(game, cid):
        return {"ok": False,
                "why": "Not over this counter. Not on this station."}
    barred = assembly.embargoed(game, system.port.faction, cid)
    if barred:
        return {"ok": False, "why": barred}

    moving, refusal = quayside_sim.may_move(game, 1.0, system)
    if not moving:
        return {"ok": False, "why": refusal}
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
    # And what it cost to get it across (`sim/quayside`) — nothing alongside.
    out["lighter"] = quayside_sim.collect(game, n * bulk_of(cid), system)
    out["net"] = n * price - out["due"] - out["lighter"]
    officials_sim.spend_once(game, system, "quiet_price")
    # Only what you brought counts as trade — for the crew's pride as much as
    # for the port's regard. See `BOUGHT_MEMORY`.
    brought = imported(game, system, cid, n)
    out["brought"] = brought
    if brought * price >= NOTICED:
        loyalty_sim.record(game, "trade_profit",
                           scale=min(2.0, brought * price / 6000))
    add_cargo(game.ship, cid, -n)
    apply_sale(system.market, cid, n)
    from . import nemeses as nemeses_sim      # the cartel keeps a ledger
    nemeses_sim.undercut(game, system, brought * price)
    # Trading here is dealing with whoever runs the quay. This and `buy` are
    # the only routes by which a harbourmaster comes to know you at all.
    officials_sim.dealt_with(game, system, min(2.0, n * price / 9000))
    game.adjust_rep(system.port.faction,
                    min(2, brought * 0.05)
                    * dip_sim.agenda_bonus(game, system.port.faction, cid))
    game.add_log(f"Sold {round(n)} {BY_ID[cid].short} at {price:,} — "
                 f"{round(n * price):,}."
                 + (f" Wharfage {out['due']:,}, {out['net']:,} clear."
                    if out["due"] else "")
                 + (f" Lighterage {out['lighter']:,}."
                    if out["lighter"] else ""))
    renown_sim.note(game, "sales", int(brought > 0))   # only what you brought
    return out


#: What a hand-in of survey data is worth in standing, and the most any one
#: of them can be.
#:
#: **Standing used to be purchasable at about 350 credits a point.** Survey
#: data is an ordinary stocked commodity, so the sets could be bought over
#: the very counter they were handed back to, and this granted `min(6, n *
#: 0.4)` with no cooldown — measured, nought to the +100 cap in 19 to 26
#: hand-ins across 120 to 220 days, for about 35,000 credits and a couple of
#: thousand free research points on top. Ordinary selling grants `min(2, n *
#: 0.05)` for comparison. Charting is worth standing; it is not worth *that*
#: much standing, and what is bought back over a counter is worth none.
SURVEY_REP_PER_SET = 0.12
SURVEY_REP_CAP = 2.0


def sell_survey_data(game) -> dict:
    """Hand over accumulated survey sets. Worth standing as well as money."""
    system = game.system
    if not system.port:
        return {"ok": False, "why": "No port here."}
    # A bench of sets is handed over, not transmitted: somebody has to be at
    # the counter (`sim/quayside`). A play-test sold survey data at the Fleet
    # Hub from seven AU out.
    there, why = quayside_sim.at_counter(game, system)
    if not there:
        return {"ok": False, "why": why}
    # And at law 10 movement is licensed and so are charts: a world that
    # seizes survey data has no Survey Office window open to you
    # (`sim/lawlevel.py`).
    if customs_sim.seizes(game, "survey"):
        return {"ok": False,
                "why": "Charts are licensed here. This office will take "
                       "them and not pay for them."}
    n = game.ship.cargo.get("survey", 0)
    if n < 1:
        return {"ok": False, "why": "No survey data aboard."}
    # **Through the same counter as everything else.** This moved money
    # without `wharfage.collect` — whose docstring calls itself "the only
    # place money moves" — and priced off `world.economy` directly, so a
    # power's memory of you and the office rate both went unread. Measured
    # at one quay: 50 sets took 20,650 and the holder's purse saw nothing of
    # the 490 due.
    price = market_sim.quote_sell(game, system, "survey") or 250
    took = round(n * price)
    game.credits += took
    due = wharfage_sim.collect(game, system, took)
    officials_sim.spend_once(game, system, "quiet_price")
    officials_sim.dealt_with(game, system, min(2.0, took / 9000))
    add_cargo(game.ship, "survey", -n)
    # **And it floods the office like any other sale.** This never called
    # `apply_sale`, so the hundredth set handed in fetched what the first did.
    # Charts bought over this very counter are its own charts back: no
    # standing and nothing for the bench.
    brought = n
    if system.market:
        brought = imported(game, system, "survey", n)
        apply_sale(system.market, "survey", n)
    game.adjust_rep(system.port.faction,
                    min(SURVEY_REP_CAP, brought * SURVEY_REP_PER_SET))
    game.research.banked += brought * 6
    renown_sim.note(game, "survey_sales", int(brought > 0))
    inquiry.add(game.research, "survey", brought * assembly.effect(game, "commons", 0.0))
    game.add_log(f"Sold {round(n)} survey sets for {took:,}."
                 + (f" Wharfage {due:,}, {took - due:,} clear." if due else ""),
                 "good")
    return {"ok": True, "units": n, "price": price, "took": took,
            "due": due, "net": took - due}


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
