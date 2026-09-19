"""What a freight line will clear, said before it sails.

**The forecast runs the market's own code, not a model of it.** A line is
priced on throwaway twins of the two stock rows it trades — copied, never the
real ones — which are aged with `economy.tick_market` itself, holding the
market's dice at their mean (`_MeanDice`: no random walk, no change of trend),
bought from with `apply_trade` and sold into with `apply_sale`, and priced
through `market.quote_buy`/`quote_sell` with the twin swapped in for the
length of one call. So the drift back to a port's own equilibrium, the price a
line's own tonnes push against it, and every modifier the counter applies are
the counter's, and cannot drift away from it.

What the dice would have done is the one thing left out, and it is left out on
purpose: over many trips it averages to nothing. `test_freightlines` flies
fifty seeded trips and holds the forecast to the mean it measures.

The risk is `lineroute.risk`, the same numbers the trip is rolled on, and a
delay is priced as the spread of days it could cost.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager

from ..data.freightlines import (DELAY_DAYS, HAND_A_DAY, INSURANCE_LOADING,
                                 ROBBED_DAMAGE, TRIP_KINDS, WAIT_MAX,
                                 WEAR_PER_HOP)
from ..world.economy import Market, apply_sale, apply_trade, tick_market
from . import lineroute
from . import market as market_sim
from . import masters as masters_sim
from . import services as services_sim
from . import wharfage as wharfage_sim
from . import linetrips
from .linetrips import hull_worth, lot
from .ship import hull_max


class _MeanDice:
    """The market's dice, held at their mean: `tick_market`'s walk is
    `lo + next() * span` about nought and a trend turns when `next()` falls
    under a small chance, so a half is no walk and no turn."""

    @staticmethod
    def next() -> float:
        return 0.5


MEAN = _MeanDice()

#: The ledger kinds `trip()["cash"]` forecasts. Repairs are priced separately
#: (`trip()["repair"]`): the forecast charges wear on every trip, and the yard
#: bills it only when she comes home worn.
TRIP_CASH = TRIP_KINDS - {"repair"}


def _twin(system, cids) -> Market:
    stock = system.market.stock
    return Market(stock={c: copy.copy(stock[c]) for c in cids if c in stock})


@contextmanager
def _as_if(system, twin):
    """Price against a twin for the length of one call."""
    real = system.market
    system.market = twin
    try:
        yield
    finally:
        system.market = real


def _price(game, system, twin, cid: str, side: str):
    with _as_if(system, twin):
        quote = market_sim.quote_buy if side == "buy" else market_sim.quote_sell
        return quote(game, system, cid)


def _age(game, system, twin, day: int, flows=None) -> None:
    """One day on a twin: the shocks still live on that day, the tick, and
    what the house's other lines take from and bring to this quay."""
    for cid, stock in twin.stock.items():
        live = [s for s in market_sim.at(game, system.id)
                if s.commodity == cid and s.until > day]
        factor = 1.0
        for shock in live:
            factor *= shock.definition.supply
        stock.shock = factor
    tick_market(twin, 1, MEAN, system.port.level if system.port else 1)
    flows = flows or {}
    for cid, tonnes in (flows.get(system.id, [])
                        + flows.get((system.id, day), [])):
        if cid in twin.stock:
            (apply_sale if tonnes > 0 else apply_trade)(twin, cid, abs(tonnes))


def _flows(game, line) -> dict:
    """What the house's *other* running lines do to this line's two quays, a
    day at a time: each buys its lot at its home port and sells it at the far
    one once a cycle, spread evenly over the cycle — and a cargo already in
    passage lands whole, on the day she is due (keyed `(system id, day)`).

    Without it the second line on a route was forecast as if it were the
    first. Measured: a second TENDER put on a trehalose route was promised
    24,047 in ninety days, and the pair lost 159,000 in fifteen months.
    """
    house = getattr(game, "house", None)
    ends = {line.origin, line.dest}
    out: dict = {}
    for other in (house.lines if house is not None else ()):
        if not other.active or other is line or (line.id and other.id == line.id):
            continue
        if other.good != line.good or not ({other.origin, other.dest} & ends):
            continue
        plan = lineroute.route_for(game, other)
        if plan is None:
            continue
        home = game.galaxy.systems[other.origin]
        lot_t = min(other.tonnes, plan["stats"].cargo,
                    home.market.stock[other.good].units if home.market else 0)
        cycle = max(1, plan["out"]["days"] + plan["back"]["days"],
                    other.cadence or 0)
        out.setdefault(other.origin, []).append((other.good, -lot_t / cycle))
        out.setdefault(other.dest, []).append((other.good, lot_t / cycle))
        aboard = plan and lineroute.hull_of(game, other)
        if other.phase == "out" and aboard is not None:
            laden = aboard.cargo.get(other.good, 0.0)
            out.setdefault((other.dest, other.due), []).append(
                (other.good, laden))
    return out


def _prices_ahead(game, dest, twin, cid, start: int, days: int,
                  flows=None) -> list:
    """What the far counter will pay on each of the next `days` days."""
    ahead = copy.deepcopy(twin)
    out = []
    for k in range(1, days + 1):
        _age(game, dest, ahead, start + k, flows)
        out.append(_price(game, dest, ahead, cid, "sell"))
    return out


def trip(game, line, plan, account: float, twins=None, day=None,
         flows=None) -> dict:
    """One trip's expected cash, from the twins' state (or the real one)."""
    systems = game.galaxy.systems
    origin, dest = systems[line.origin], systems[line.dest]
    day = game.day if day is None else day
    o_twin, d_twin = twins or (_twin(origin, {line.good, "volatiles"}),
                               _twin(dest, {line.good}))
    hull = lineroute.hull_of(game, line)
    master = plan["master"]
    slip = masters_sim.slip(master)
    price = _price(game, origin, o_twin, line.good, "buy")
    fuel_t = plan["out"]["fuel"] + plan["back"]["fuel"]
    fuel_price = _price(game, origin, o_twin, "volatiles", "buy") or 0
    if price is None:
        return {"ok": False, "why": "the home port sells none"}
    if line.max_buy and price > line.max_buy:
        return {"ok": False, "why": f"price {price:,} is over the rule's "
                                    f"{line.max_buy:,}", "price": price}
    tonnes = lot(line, hull, plan["stats"], o_twin.stock[line.good].units,
                 account, price, fuel_t, fuel_price, slip,
                 wharfage_sim.rate(game, origin))
    if tonnes < 1:
        return {"ok": False, "why": "nothing to load", "price": price}
    out_days, back_days = plan["out"]["days"], plan["back"]["days"]
    lo, hi = DELAY_DAYS
    series = _prices_ahead(game, dest, d_twin, line.good, day,
                           out_days + hi + WAIT_MAX, flows)
    if linetrips.judged(game, origin, dest, tonnes, price,
                        series[out_days - 1], slip,
                        fuel_t * fuel_price) <= 0:
        return {"ok": False, "why": "the spread is closed", "price": price}
    fuel = fuel_t * fuel_price * (1 + slip)
    outlay = tonnes * price * (1 + slip)
    dues_in = (wharfage_sim.due_on(game, origin, tonnes * price)
               + wharfage_sim.due_on(game, origin, fuel_t * fuel_price))
    odds = plan["risk"]
    ok = 1.0 - odds["lost"] - odds["robbed"] - odds["seized"]
    spread = [(1.0 - odds["delay"], 0)] + [
        (odds["delay"] / (hi - lo + 1), d) for d in range(lo, hi + 1)]
    takings = sell_price = cycle = 0.0
    for weight, delay in spread:
        at = out_days + delay
        sold = at
        while (line.min_sell and sold < at + WAIT_MAX
               and (series[sold - 1] or 0) < line.min_sell):
            sold += 1
        got = series[sold - 1] or 0
        sell_price += weight * got
        net = (tonnes * got * (1 - slip)
               - wharfage_sim.due_on(game, dest, tonnes * got))
        takings += weight * net
        cycle += weight * (sold + back_days)
    paid = outlay + wharfage_sim.due_on(game, origin, tonnes * price)
    lose_cargo = odds["lost"] + odds["robbed"] + odds["seized"]
    worth = _hull_worth(hull)
    claims = premium = 0.0
    house = getattr(game, "house", None)
    if house is not None and house.insured:
        claims = lose_cargo * paid + odds["lost"] * worth
        premium = INSURANCE_LOADING * claims
    rate_r = (services_sim.REPAIR_RATE_FABRICATED
              if plan["stats"].family == "fabricated"
              else services_sim.REPAIR_RATE_GROWN)
    hp = hull_max(hull) if hull is not None else 0.0
    repair = rate_r * hp * (WEAR_PER_HOP * 2 * plan["out"]["hops"]
                            + odds["robbed"] * sum(ROBBED_DAMAGE) / 2)
    cash = ok * takings - outlay - fuel - dues_in - premium + claims
    # What a trip that gets through clears — the figure to hold a completed
    # trip to, since whether it gets through is `risk`'s to say.
    clear = takings - outlay - fuel - dues_in - premium
    return {"ok": True, "why": "", "tonnes": tonnes, "price": price,
            "fuel_t": fuel_t, "fuel_price": fuel_price, "outlay": outlay,
            "fuel": fuel, "dues_in": dues_in, "sell_price": sell_price,
            "takings": ok * takings, "premium": premium, "claims": claims,
            "repair": repair, "cash": cash, "clear": clear, "cycle": cycle,
            "sold": ok * tonnes, "days_out": out_days, "days_back": back_days}


def arrival(game, line, plan) -> int | None:
    """What the far counter is expected to pay the day she gets there, the
    house's other lines on the route included — the price a master judges a
    cargo by before loading it (`linetrips.judged`)."""
    dest = game.galaxy.systems[line.dest]
    if dest.market is None:
        return None
    days = plan["out"]["days"]
    return _prices_ahead(game, dest, _twin(dest, {line.good}), line.good,
                         game.day, days, _flows(game, line))[days - 1]


def closed_end(game, line) -> str:
    """A port at either end with no market any more, in words, or "".

    A berth can close — a power that cannot pay for a port lets it go down the
    ladder, and an outpost that goes down a step takes its market with it
    (`exchequer.demote`). Found by a five-year house chronicle, which crashed
    pricing a line into a port that had closed under it.
    """
    for end in (line.origin, line.dest):
        system = game.galaxy.systems[end]
        if system.market is None:
            return f"{system.name} has closed its market"
    return ""


def _hull_worth(hull) -> float:
    return hull_worth(hull) if hull is not None else 0.0


def time_cost(game, line, plan) -> float:
    """What a line costs a day whether or not she is earning: the master's
    wage and her own hands."""
    master = plan["master"]
    hull = lineroute.hull_of(game, line)
    hands = (hull.crew if hull is not None else 0) * HAND_A_DAY
    return (master.wage / 30.0 if master is not None else 0.0) + hands


def forecast(game, line, account: float | None = None,
             horizon: int = 90) -> dict:
    """The next trip, and the next `horizon` days of trips, with the line's
    own tonnes pushing on both ends of its route as they would."""
    plan = lineroute.route_for(game, line)
    if plan is None:
        return {"ok": False, "why": "her drive cannot make the passage"}
    closed = closed_end(game, line)
    if closed:
        return {"ok": False, "why": closed}
    house = getattr(game, "house", None)
    money = (account if account is not None
             else linetrips.spendable(house) if house else 0.0)
    systems = game.galaxy.systems
    origin, dest = systems[line.origin], systems[line.dest]
    flows = _flows(game, line)
    first = trip(game, line, plan, money, flows=flows)
    daily = time_cost(game, line, plan)
    risk = plan["risk"]
    out = {"ok": first["ok"], "why": first.get("why", ""), "first": first,
           "risk": risk, "daily": daily,
           "route": [s.name for s in plan["route"]],
           "p_lost": risk["lost"],
           "p_cargo": risk["lost"] + risk["robbed"] + risk["seized"]}
    if not first["ok"]:
        out.update(per_trip=0.0, per90=-daily * horizon, trips90=0)
        return out
    o_twin = _twin(origin, {line.good, "volatiles"})
    d_twin = _twin(dest, {line.good})
    t, total, trips = 0, 0.0, 0
    while t < horizon and trips < 40:
        leg = trip(game, line, plan, money, (o_twin, d_twin), game.day + t,
                   flows)
        if not leg["ok"]:
            t += 1
            _age(game, origin, o_twin, game.day + t, flows)
            _age(game, dest, d_twin, game.day + t, flows)
            continue
        total += leg["cash"] - leg["repair"]
        trips += 1
        apply_trade(o_twin, line.good, leg["tonnes"])
        apply_trade(o_twin, "volatiles", leg["fuel_t"])
        span = max(1, round(max(leg["cycle"], line.cadence or 0)))
        arrive = leg["days_out"]
        for k in range(1, span + 1):
            _age(game, origin, o_twin, game.day + t + k, flows)
            _age(game, dest, d_twin, game.day + t + k, flows)
            if k == arrive:
                apply_sale(d_twin, line.good, leg["sold"])
        t += span
    per_trip = first["cash"] - first["repair"] - daily * max(
        first["cycle"], line.cadence or 0)
    # A rate, not a count: the last trip begun inside the horizon ends
    # outside it, so what the trips clear is spread over the days they took.
    out.update(per_trip=per_trip,
               per90=(total / max(t, 1) - daily) * horizon,
               trips90=trips, cycle=max(first["cycle"], line.cadence or 0))
    return out


def suggest(game, hauler, master_id: int, limit: int = 3,
            shortlist: int = 12) -> list:
    """The freight desk's best runs within this hauler's reach, priced as
    lines. `freight.runs` ranks what is worth loading at each port the house
    has a factor at, by what the captain's notes and the harbourmasters say;
    the best of those are then forecast as lines and ranked on what a line
    would clear in ninety days, its own saturation included."""
    from . import freight as freight_sim
    from . import freightlines as lines_sim
    from . import reach
    if hauler is None or hauler.docked_at is None:
        return []
    st = lineroute.hauler_stats(game, hauler)
    within = reach.routes_from(game, st.jump, hauler.docked_at)
    known = {int(k) for k in game.register if str(k).isdigit()}
    picks = []
    for here in game.galaxy.systems:
        if here.id not in within or here.id not in known or not here.market:
            continue
        # Every run, not the desk's top six: the six it would show a captain
        # standing there are ranked for the captain's drive, and a hauler's
        # reach is its own.
        for run in freight_sim.runs(game, here, limit=99):
            if run.target_id in within and run.target_id in known:
                picks.append((run.worth, here.id, run))
    picks.sort(key=lambda row: -row[0])
    out = []
    for _worth, origin, run in picks[:shortlist]:
        line = lines_sim.draft(game, hauler.uid, master_id, origin,
                               run.target_id, run.commodity, int(st.cargo))
        told = forecast(game, line)
        if told.get("ok") and told["per90"] > 0:
            out.append({"line": line, "run": run, "forecast": told})
    out.sort(key=lambda row: -row["forecast"]["per90"])
    return out[:limit]
