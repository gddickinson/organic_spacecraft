"""A freight line's trip, port to port, on the sector's clock.

Each line is a small state machine driven by `advance`, which the house's
daily tick calls: *ferry* (in ballast to the home port), *load* (alongside,
buying), *out* (laden), *sell* (alongside at the far end), *home* (in ballast
back). A phase ends on the day its `due` comes round, and a day can carry a
line through several — sold on arrival and away the same afternoon.

**The till is the counter's own.** Nothing here prices a tonne: the buy is
`market.quote_buy`, the sale `market.quote_sell`, the due `wharfage.collect`,
the market moves through `apply_trade`/`apply_sale`, and the counter's memory
of what it sold (`trade._bought`/`trade.imported`) decides what the sale is
worth in standing — the same rule that closed the buy-and-resell exploit. The
house's money moves only through `lineledger.post`.

A trip's fortune is decided at departure from its own dice
(`RNG(seed:line:id:trip)`), never from the chronicle's stream, so a house
running beside the captain cannot change what the captain's own day rolls, and
a reload cannot reroll a voyage already under way.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data.commodities import BY_ID, bulk_of
from ..data.freightlines import (INSURANCE_LOADING, LINE_REGARD_CAP,
                                 REGARD_PERIOD, REPAIR_BELOW, UNSEAWORTHY,
                                 WAIT_MAX, WEAR_PER_HOP)
from ..world.economy import apply_sale, apply_trade
from . import customs as customs_sim
from . import diplomacy as dip_sim
from . import enforce as enforce_sim
from . import exchequer as exchequer_sim
from . import lineledger as ledger
from . import lineroute
from . import market as market_sim
from . import masters as masters_sim
from . import officials as officials_sim
from . import services as services_sim
from . import shipyard as shipyard_sim
from . import trade as trade_sim
from . import wharfage as wharfage_sim
from .ship import (add_cargo, apply_damage, cargo_free, hull_max, hull_pct,
                   is_destroyed)


# ── the till ────────────────────────────────────────────────────────────────

def _due(game, house, line_id: int, system, value: float) -> None:
    """The quay's cut, taken through `wharfage.collect` — the one place a due
    lands in a holder's purse — and charged to the house, not the purse.

    `collect` takes from the captain's purse, and a creditor holding this
    counter distrains there too; both are read as the purse's movement and
    moved back onto the house's books, so the holder is paid exactly what a
    captain would pay and the captain's own money is untouched.
    """
    before = game.credits
    due = wharfage_sim.collect(game, system, value)
    taken = before - game.credits
    game.credits = before
    ledger.post(game, house, line_id, "wharfage", -due)
    ledger.post(game, house, line_id, "distraint", -(taken - due))


def buy(game, house, line, system, cid: str, tonnes: float, price: int,
        kind: str = "purchase") -> float:
    """Take tonnes off a counter for the house. Returns what they cost."""
    slip = masters_sim.slip(lineroute.master_of(game, line))
    cost = tonnes * price * (1.0 + slip)
    ledger.post(game, house, line.id, kind, -cost)
    _due(game, house, line.id, system, tonnes * price)
    # "This once" means this once, for a house as for a captain.
    officials_sim.spend_once(game, system, "quiet_price")
    apply_trade(system.market, cid, tonnes)
    if kind == "purchase":
        trade_sim._bought(game, system, cid, tonnes)
    return cost


def sell(game, house, line, system, cid: str, tonnes: float,
         price: int) -> float:
    """Put tonnes over a counter for the house. Returns what was taken."""
    slip = masters_sim.slip(lineroute.master_of(game, line))
    took = tonnes * price * (1.0 - slip)
    ledger.post(game, house, line.id, "sale", took)
    _due(game, house, line.id, system, tonnes * price)
    officials_sim.spend_once(game, system, "quiet_price")
    brought = trade_sim.imported(game, system, cid, tonnes)
    apply_sale(system.market, cid, tonnes)
    _regard(game, house, system, cid, brought)
    return took


def _regard(game, house, system, cid: str, brought: float) -> float:
    """Standing for what a line brought, through the counter's own rule and
    then under the house's cap for the period. Returns what was granted."""
    power = system.port.faction if system.port else None
    if not power or brought <= 0:
        return 0.0
    start, gained = house.regard.get(power, [game.day, 0.0])
    if game.day - start >= REGARD_PERIOD:
        start, gained = game.day, 0.0
    want = (min(2.0, brought * 0.05)
            * dip_sim.agenda_bonus(game, power, cid))
    grant = max(0.0, min(want, LINE_REGARD_CAP - gained))
    house.regard[power] = [start, gained + grant]
    if grant > 0:
        game.adjust_rep(power, grant)
    return grant


# ── the phases ──────────────────────────────────────────────────────────────

def advance(game, house, line) -> None:
    """Carry a line through every phase whose day has come."""
    for _ in range(8):
        before = (line.phase, line.due)
        if not line.active:
            return
        if line.phase in ("ferry", "home") and game.day >= line.due:
            _home(game, house, line)
        elif line.phase == "load":
            line.waiting = depart(game, house, line)
        elif line.phase == "out" and game.day >= line.due:
            _arrive(game, house, line)
        elif line.phase == "sell":
            _sell(game, house, line)
        if (line.phase, line.due) == before:
            return


def depart(game, house, line) -> str:
    """Load and sail, or say why not. Empty string means she sailed."""
    from . import freightlines as lines_sim
    if line.stopping:
        lines_sim.stand_down(game, house, line)
        return ""
    from .lineforecast import closed_end
    closed = closed_end(game, line)
    if closed:
        game.add_log(f"{closed}; the line from "
                     f"{game.galaxy.systems[line.origin].name} stands down.",
                     "warn")
        lines_sim.stand_down(game, house, line)
        return ""
    if game.day < line.next_start:
        return f"next sailing on day {line.next_start}"
    hull = lineroute.hull_of(game, line)
    if hull is None:
        return "no hauler"
    if hull_pct(hull) < UNSEAWORTHY and not repair(game, house, line, hull):
        return "not seaworthy until she is repaired"
    if house.owed_charter > 0 or house.owed_hands > 0:
        return "the house is in arrears; the hands will not sail unpaid"
    plan = lineroute.route_for(game, line, hull)
    if plan is None:
        return "her drive cannot make the passage"
    origin = game.galaxy.systems[line.origin]
    dealing, why = enforce_sim.may_trade(game, origin)
    if not dealing:
        return why
    load = loading(game, house, line, hull, plan)
    if not load["ok"]:
        return load["why"]
    rng = RNG(f"{game.seed}:line:{line.id}:{line.trips}")
    luck = lineroute.roll(rng, plan["risk"])
    line.trip_net = 0.0
    line.started = game.day
    buy(game, house, line, origin, "volatiles", load["fuel_t"],
        load["fuel_price"], kind="fuel")
    line.paid = buy(game, house, line, origin, line.good, load["tonnes"],
                    load["price"])
    add_cargo(hull, line.good, load["tonnes"])
    line.insured = house.insured
    if line.insured:
        premium = insurance(game, line, hull, plan["risk"], line.paid)
        ledger.post(game, house, line.id, "premium", -premium)
        exchequer_sim.purse(game, house.power).credits += premium
    line.stake = -line.trip_net
    market_sim.note_prices(game, origin)
    line.fate, line.delay, line.damage = (luck["fate"], luck["delay"],
                                          luck["damage"])
    line.phase = "out"
    line.due = game.day + plan["out"]["days"] + line.delay
    hull.docked_at = None
    return ""


def loading(game, house, line, hull, plan) -> dict:
    """What she would load now, and what it costs — or why she cannot."""
    origin = game.galaxy.systems[line.origin]
    price = market_sim.quote_buy(game, origin, line.good)
    if price is None:
        return {"ok": False, "why": "the home port sells none"}
    if line.max_buy and price > line.max_buy:
        return {"ok": False, "why": f"price {price:,} is over the rule's "
                                    f"{line.max_buy:,}"}
    fuel_t = plan["out"]["fuel"] + plan["back"]["fuel"]
    fuel_price = market_sim.quote_buy(game, origin, "volatiles")
    if not fuel_price or origin.market.stock["volatiles"].units < fuel_t:
        return {"ok": False, "why": "the quay has no reaction mass to spare"}
    stock = origin.market.stock[line.good].units
    tonnes = lot(line, hull, plan["stats"], stock, spendable(house), price,
                 fuel_t, fuel_price, masters_sim.slip(plan["master"]),
                 wharfage_sim.rate(game, origin))
    if tonnes < 1:
        return {"ok": False, "why": "nothing she can afford or stow is on "
                                    "the quay"}
    from .lineforecast import arrival
    dest = game.galaxy.systems[line.dest]
    sell = arrival(game, line, plan)
    margin = judged(game, origin, dest, tonnes, price, sell,
                    masters_sim.slip(plan["master"]), fuel_t * fuel_price)
    if margin <= 0:
        return {"ok": False, "why": (f"the spread is closed — {dest.name} "
                                     f"should pay {sell or 0:,} when she "
                                     f"arrives, against {price:,} here")}
    return {"ok": True, "tonnes": tonnes, "price": price, "fuel_t": fuel_t,
            "fuel_price": fuel_price}


def judged(game, origin, dest, tonnes: int, price: int, sell, slip: float,
           fuel: float) -> float:
    """What a cargo would clear at the price the far end is expected to pay
    on arrival — the master's judgement, and the one thing a master will not
    do is sail a loss. Measured before it: two TENDERs on one trehalose route
    sailed on at any price and lost 159,000 in fifteen months, three
    thousand a trip, with no rule set to stop them; judged on the far
    counter's price *today*, a second line on a silicon route still lost
    14,000 a trip, because the first line's cargo landed ahead of hers. A
    line on a closed spread now waits for it to open, which is what
    saturation looks like to the house: fewer sailings, thinner ones."""
    if not sell:
        return -1.0
    cost = (tonnes * price * (1 + slip) + fuel * (1 + slip)
            + wharfage_sim.due_on(game, origin, tonnes * price + fuel))
    take = (tonnes * sell * (1 - slip)
            - wharfage_sim.due_on(game, dest, tonnes * sell))
    return take - cost


def spendable(house) -> float:
    """What a cargo may be bought with: the account above its reserve.

    The reserve is the payroll's. Buying with every credit in the account
    meant one robbed cargo left nothing for the month's wages — measured, the
    master of a licence line that lost a 194,000-credit cargo went unpaid
    twice and walked on day 60, and the line with them.
    """
    return max(0.0, house.account - house.reserve)


def lot(line, hull, stats, stock: float, account: float, price: int,
        fuel_t: float, fuel_price: int, slip: float, rate: float) -> int:
    """How many tonnes she takes: the rule's tonnage, as far as her hold, the
    quay's stock and the account (after her reaction mass) allow. One sum,
    read by the trip and by its forecast."""
    fuel = fuel_t * fuel_price * (1 + slip + rate)
    unit = price * (1 + slip + rate)
    afford = int(max(0.0, account - fuel) // unit) if unit > 0 else 0
    room = (int(cargo_free(hull, stats) / bulk_of(line.good))
            if hull is not None else int(stats.cargo))
    return int(max(0, min(line.tonnes, room, int(stock), afford)))


def insurance(game, line, hull, odds: dict, cargo: float) -> float:
    """The premium: the expected claim, loaded. Cargo is covered for what
    it cost; the hull for what laying her down again would cost."""
    lose_cargo = odds["lost"] + odds["robbed"] + odds["seized"]
    return INSURANCE_LOADING * (lose_cargo * cargo
                                + odds["lost"] * hull_worth(hull))


def hull_worth(hull) -> float:
    """What laying this hull down again would cost, matter valued as itself —
    the same bill `shipyard.scrap_value` discounts."""
    from ..data.chassis import CHASSIS_BY_ID
    from ..data.parts import material_value
    bill = shipyard_sim.cost_of(CHASSIS_BY_ID[hull.chassis], hull.fitted,
                                fabricator=True)
    return bill.get("credits", 0) + sum(material_value(k) * n
                                        for k, n in bill.items()
                                        if k != "credits")


def _claim(game, house, line, amount: float) -> float:
    """The underwriter pays, out of its own purse and no further."""
    purse = exchequer_sim.purse(game, house.power)
    paid = max(0.0, min(amount, purse.credits))
    purse.credits -= paid
    ledger.post(game, house, line.id, "claim", paid)
    return paid


def _arrive(game, house, line) -> None:
    """Landfall at the far end — or not."""
    from . import freightlines as lines_sim
    hull = lineroute.hull_of(game, line)
    dest = game.galaxy.systems[line.dest]
    origin = game.galaxy.systems[line.origin]
    fate = line.fate
    if hull is None:
        lines_sim.stand_down(game, house, line)
        return
    if fate in ("robbed", "seized", "lost"):
        hull.cargo.pop(line.good, None)
        worth = line.paid + (hull_worth(hull) if fate == "lost" else 0.0)
        paid = _claim(game, house, line, worth) if line.insured else 0.0
        cover = f" The underwriters paid {round(paid):,}." if paid else ""
    if fate == "lost":
        game.fleet = [s for s in game.fleet if s is not hull]
        game.add_log(f"<b>{hull.name} was lost</b> on the {origin.name}–"
                     f"{dest.name} line, with her cargo.{cover}", "bad")
        finish(game, house, line)
        return
    hull.docked_at = dest.id
    if fate == "robbed":
        apply_damage(hull, line.damage * hull_max(hull))
        game.add_log(f"{hull.name} was boarded on the way to {dest.name} and "
                     f"her cargo taken.{cover}", "warn")
    elif fate == "seized":
        game.add_log(f"{hull.name}'s cargo was seized as contraband of war "
                     f"on the way to {dest.name}.{cover}", "warn")
    line.phase = "sell"
    line.since = game.day


def _sell(game, house, line) -> None:
    """Sell to the rule, or wait for it — but not for ever."""
    hull = lineroute.hull_of(game, line)
    dest = game.galaxy.systems[line.dest]
    tonnes = hull.cargo.get(line.good, 0.0) if hull is not None else 0.0
    waited = game.day - line.since
    if tonnes >= 1e-6:
        dealing, _why = enforce_sim.may_trade(game, dest)
        barred = (not dealing or dest.port is None
                  or customs_sim.outlaws(dest.port.faction, line.good))
        price = None if barred else market_sim.quote_sell(game, dest, line.good)
        if price is None:
            if waited < WAIT_MAX:
                line.waiting = "the far counter will not buy"
                return
            hull.cargo.pop(line.good, None)
            game.add_log(f"{hull.name} could not sell at {dest.name} and put "
                         f"her cargo over the side.", "warn")
        elif line.min_sell and price < line.min_sell and waited < WAIT_MAX:
            line.waiting = (f"price {price:,} is under the rule's "
                            f"{line.min_sell:,}")
            return
        else:
            sell(game, house, line, dest, line.good, tonnes, price)
            add_cargo(hull, line.good, -tonnes)
            market_sim.note_prices(game, dest)
    line.waiting = ""
    if line.stopping:
        from . import freightlines as lines_sim
        lines_sim.stand_down(game, house, line)
        return
    plan = lineroute.route_for(game, line, hull)
    line.phase = "home"
    line.due = game.day + (plan["back"]["days"] if plan else 1)
    if hull is not None:
        hull.docked_at = None


def _home(game, house, line) -> None:
    """Back alongside at the home port: the trip is done, and it wore her."""
    hull = lineroute.hull_of(game, line)
    ferried = line.phase == "ferry"
    line.phase = "load"
    if hull is None:
        return
    hull.docked_at = line.origin
    if ferried:
        return
    plan = lineroute.route_for(game, line, hull)
    hops = plan["out"]["hops"] * 2 if plan else 2
    apply_damage(hull, WEAR_PER_HOP * hops * hull_max(hull))
    if hull_pct(hull) < REPAIR_BELOW:
        repair(game, house, line, hull)
    finish(game, house, line)


def finish(game, house, line) -> None:
    """Close a trip's books, and tell the captain if it was one to tell."""
    fate = line.fate or "done"
    if fate == "done" and line.delay:
        fate = "delayed"
    line.trips += 1
    line.last = fate
    line.last_net = line.trip_net
    line.last_day = game.day
    line.next_start = line.started + line.cadence
    master = lineroute.master_of(game, line)
    if master is not None:
        masters_sim.after_trip(master, fate)
    if fate in ("done", "delayed") and line.trip_net > house.record > 0:
        good = BY_ID.get(line.good)
        game.add_log(f"<b>A record trip for the house:</b> "
                     f"{round(line.trip_net):,} clear on "
                     f"{good.short if good else line.good} to "
                     f"{game.galaxy.systems[line.dest].name}.", "good")
    if fate in ("done", "delayed"):
        house.record = max(house.record, line.trip_net)
    from . import freightlines as lines_sim
    if master is not None and masters_sim.walks(master):
        lines_sim.stand_down(game, house, line, lost=fate == "lost")
        masters_sim.leave(game, house, master)
    elif fate == "lost":
        lines_sim.stand_down(game, house, line, lost=True)


def repair(game, house, line, hull) -> bool:
    """Put her right at the drydock's own rate, if the account can pay."""
    damage = hull_max(hull) - sum(l.hp for l in hull.layers)
    if damage < 1 or is_destroyed(hull):
        return damage < 1
    rate = (services_sim.REPAIR_RATE_FABRICATED
            if lineroute.hauler_stats(game, hull).family == "fabricated"
            else services_sim.REPAIR_RATE_GROWN)
    cost = round(damage * rate)
    if house.account < cost:
        return False
    ledger.post(game, house, line.id, "repair", -cost)
    for layer in hull.layers:
        layer.hp = layer.max
    hull.disabled = []
    return True
