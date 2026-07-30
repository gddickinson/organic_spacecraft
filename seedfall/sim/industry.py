"""Licensing a process: technology that changes somebody else's market.

The tree had sixty-two nodes and one economic effect — `trade`, a haggling bonus
on the price *you* are quoted. Nothing the captain could ever learn changed what
a market held, what a port could make, or what anything cost anybody else.

A process is a technology that makes a thing (`data/industry.py`). Licence one to
a power and it becomes an industry at every berth that power holds: the good gets
made there, the local baseline supply rises, and the price comes down. The power
pays out of its treasury (`sim/exchequer.py`), so a licence is bounded by whether
they can actually find the money — and a berth that power founds *later* comes up
with the industry already running.

**It cuts both ways, and that is the point.** A port that starts making alloy is
a port that stops paying well for alloy. Licensing your separation gut to the
power whose quays you sell alloy at is a way to put yourself out of business, and
`forecast` says so — in credits, per berth — before you sign.

**One door, and a dry run rather than a formula.** `industrialise` is the only
thing that writes `Stock.works`, and it recomputes it from the whole set of
processes a power holds rather than multiplying what is already there, so calling
it twice cannot double an industry. `forecast` prices a *copy* of the stock
through the same `buy_price` the counter uses, because a forecast that does its
own arithmetic is how a quote comes to disagree with a till.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field

from ..core.save import register
from ..data.commodities import BY_ID
from ..data.factions import FACTIONS_BY_ID
from ..data.industry import (ILLICIT_COST, LICENSEE_GAIN, MIN_STANDING,
                             OPENED_SUPPLY, PROCESSES, PROCESSES_BY_TECH,
                             PURSE_SHARE, RIVAL_COST, SECOND_HAND,
                             STANDING_BONUS, WORTH_PER_POINT)
from ..data.tech import TECH_BY_ID
from ..world.economy import Market, buy_price, sell_price
from . import diplomacy as dip
from . import exchequer


@register
@dataclass
class Industries:
    """Who has been taught what. `held[tech]` is the powers that hold it."""
    held: dict = field(default_factory=dict)
    #: Every licence granted, oldest first: (day, tech, power, price). The
    #: aftermath reads it, and so does the panel — "what you have sold, and to
    #: whom" is the question a captain asks before selling one more.
    sold: list = field(default_factory=list)


def state(game) -> Industries:
    got = getattr(game, "industries", None)
    if got is None:
        got = game.industries = Industries()
    return got


def holders(game, tech: str) -> list[str]:
    return list(state(game).held.get(tech, ()))


def has(game, tech: str, power: str) -> bool:
    return power in state(game).held.get(tech, ())


def known(game) -> list:
    """The processes the captain could licence to somebody, dearest first.

    A provisional result counts. It works — it does not work as well as the
    paper says — and a power buying a licence is buying the paper.
    """
    got = set(game.research.unlocked) | set(
        getattr(game.research, "provisional", ()) or ())
    out = [p for p in PROCESSES if p.tech in got]
    out.sort(key=lambda p: -TECH_BY_ID[p.tech].cost)
    return out


def process_of(tech: str):
    return PROCESSES_BY_TECH.get(tech)


# ── what it is worth ───────────────────────────────────────────────────────

def worth(game, process, power: str) -> int:
    """What this licence is worth to this power, before asking if they can pay.

    Their berths are the whole of the reason to want it: a process is an
    industry, and an industry needs somewhere to stand.
    """
    tech = TECH_BY_ID[process.tech]
    value = tech.cost * WORTH_PER_POINT
    value *= 0.40 + 0.15 * len(exchequer.holdings(game, power))
    if [p for p in holders(game, process.tech) if p != power]:
        value *= SECOND_HAND
    standing = max(-100.0, min(100.0, float(game.rep.get(power, 0))))
    value *= 1.0 + STANDING_BONUS * standing / 100.0
    return int(round(max(0.0, value)))


def afford(game, power: str) -> float:
    """What a power will commit to one process out of everything it has."""
    return exchequer.purse(game, power).credits * PURSE_SHARE


def can_licence(game, process, power: str) -> tuple[bool, str]:
    """The gate. Reads the same `worth` and the same purse as `licence` does."""
    if process not in known(game):
        return False, "You do not have that process."
    if has(game, process.tech, power):
        return False, f"{FACTIONS_BY_ID[power].short} already runs it."
    if not exchequer.holdings(game, power):
        return False, (f"{FACTIONS_BY_ID[power].short} holds no berth to put "
                       "it on.")
    if float(game.rep.get(power, 0)) < MIN_STANDING:
        return False, (f"{FACTIONS_BY_ID[power].short} will not take a licence "
                       "from you at all.")
    price = worth(game, process, power)
    if price <= 0:
        return False, "Nobody would pay anything for that."
    if afford(game, power) < price:
        return False, (f"{FACTIONS_BY_ID[power].short} cannot raise "
                       f"{price:,} — the treasury will not stand it.")
    return True, ""


def offers(game, process) -> list[dict]:
    """Every power's answer on one process, best price first."""
    out = []
    for power in dip.POWERS:
        ok, why = can_licence(game, process, power)
        out.append({
            "power": power,
            "name": FACTIONS_BY_ID[power].short,
            "tint": FACTIONS_BY_ID[power].tint,
            "price": worth(game, process, power),
            "purse": exchequer.purse(game, power).credits,
            "berths": len(exchequer.holdings(game, power)),
            "ok": ok,
            "why": why,
            "holds": has(game, process.tech, power),
        })
    out.sort(key=lambda row: (not row["ok"], -row["price"]))
    return out


def best_buyer(game, process) -> dict | None:
    got = [row for row in offers(game, process) if row["ok"]]
    return got[0] if got else None


# ── what it does to a market ───────────────────────────────────────────────

def _mine(power: str, cid: str, game) -> list:
    """The processes this power holds that make this good."""
    return [p for p in PROCESSES
            if p.good == cid and has(game, p.tech, power)]


def industrialise(game, system) -> list[str]:
    """Bring up everything that is made in this system.

    The only writer of `Stock.works`, and it *recomputes* rather than
    multiplies: called twice it does the same thing once. `exchequer.found`
    calls it too, so a berth built after the licence was sold comes up with the
    industry already running instead of being the one port that never got it.

    **Two sources now, one number.** A licensed process is what the *holder of
    the berth* was taught to make; a settlement is people on the ground making
    what the ground gives (`sim/settlement.py`). `Stock.works` began as the
    first and means both — "how much of this is made here" should have one
    answer however it came to be made, and two functions writing one field is
    how they come to disagree.
    """
    market = system.market
    if market is None:
        return []
    from . import settlement as settlement_sim
    ground = settlement_sim.supply_at(game, system)
    port = system.port
    told = []
    for cid, stock in market.stock.items():
        works = ground.get(cid, 1.0)
        for process in (_mine(port.faction, cid, game) if port else ()):
            works *= process.supply
            if process.opens and stock.base <= 0:
                # A trade that was not there at all. Nothing multiplies zero
                # into a market, so this one writes the baseline — and it
                # cannot be taken back, because you cannot un-teach a process.
                stock.base = OPENED_SUPPLY
                stock.supply = max(stock.supply, 0.05)
            told.append(process.name)
        stock.works = works
    told.extend(f"{s.good} worked on the ground"
                for s in settlement_sim.in_system(game, system.id))
    return sorted(set(told))


def _priced(system, cid: str, supply: float, rep: float, trade: float):
    """Buy and sell price at a hypothetical supply, through the real pricing.

    A dry run on a copy of the stock rather than a second formula: `preview`
    flies a throwaway twin for the same reason, and `mining.prospect` walks a
    throwaway body down.
    """
    stock = copy.deepcopy(system.market.stock[cid])
    stock.supply = supply
    twin = Market(stock={cid: stock})
    return (buy_price(twin, cid, rep, trade),
            sell_price(twin, cid, rep, trade))


def forecast(game, process, power: str) -> dict:
    """What licensing this does to the licensee's quays, in credits.

    Includes what it costs *you*: the good gets cheaper there, so a berth you
    have been selling it at pays less for it afterwards. That is the trade, and
    it is quoted rather than discovered.
    """
    cid = process.good
    rep = float(game.rep.get(power, 0))
    trade = game.ship_stats.trade
    rows = []
    for system in exchequer.holdings(game, power):
        stock = system.market.stock.get(cid)
        if stock is None:
            continue
        # **Settled against settled.** Comparing today's live price with where
        # the industry will put it mixes two different things: a market drifts
        # around its own baseline all the time, and for a process whose only
        # effect is to *open* a trade the drift was the whole of the difference
        # — the panel duly reported that licensing unlicensed seed would put
        # the price *up*. So both sides are read at the baseline, and what is
        # left is the industry.
        works = getattr(stock, "works", 1.0)
        now = stock.base * works
        opens = stock.base <= 0 and process.opens
        after = (OPENED_SUPPLY if opens else now) * process.supply
        buy_now, sell_now = ((None, None) if now <= 0
                             else _priced(system, cid, now, rep, trade))
        buy_then, sell_then = _priced(system, cid, after, rep, trade)
        rows.append({
            "system": system,
            "opens": opens,
            "buy_now": buy_now, "buy_then": buy_then,
            "sell_now": sell_now, "sell_then": sell_then,
        })
    good = BY_ID.get(cid)
    return {
        "good": good.name if good else cid,
        "rows": rows,
        "berths": len(rows),
        "opens": any(r["opens"] for r in rows),
        # What a tonne you meant to sell them stops being worth, averaged over
        # the berths it lands on. The number a captain actually needs — and
        # only over the berths that were already buying it, because a berth
        # where the trade is *opened* had no price to fall from.
        "your_loss": _loss([r for r in rows if not r["opens"]]),
        "opened": sum(1 for r in rows if r["opens"]),
    }


def _loss(rows) -> int:
    if not rows:
        return 0
    return round(sum(r["sell_now"] - r["sell_then"] for r in rows) / len(rows))


# ── the act ────────────────────────────────────────────────────────────────

def licence(game, process, power: str) -> dict:
    """Sell it. Their treasury pays, their quays change, everybody notices."""
    ok, why = can_licence(game, process, power)
    if not ok:
        return {"ok": False, "why": why}
    price = worth(game, process, power)
    purse = exchequer.purse(game, power)
    purse.credits -= price
    game.credits += price

    got = state(game)
    got.held.setdefault(process.tech, []).append(power)
    got.sold.append([game.day, process.tech, power, price])

    brought = []
    for system in exchequer.holdings(game, power):
        brought.extend(industrialise(game, system))

    game.adjust_rep(power, LICENSEE_GAIN)
    for other in dip.POWERS:
        if other == power:
            continue
        game.adjust_rep(other, RIVAL_COST)
        # And it is a fact about the two of them, not only about you: one of
        # them can now make something the other cannot.
        dip.shift_relation(game, power, other, -4)
    if process.illicit:
        for other in dip.POWERS:
            game.adjust_rep(other, ILLICIT_COST if other != power else 0.0)

    short = FACTIONS_BY_ID[power].short
    return {"ok": True, "price": price, "power": power,
            "berths": len(exchequer.holdings(game, power)),
            "brought": sorted(set(brought)),
            "text": (f"{short} has the {process.name} licence, and "
                     f"{len(exchequer.holdings(game, power))} berth(s) to run "
                     f"it at. Paid {price:,}.")}


# ── what the screens read ──────────────────────────────────────────────────

def ledger(game) -> list[dict]:
    """One row per process the captain could sell, with its best buyer."""
    out = []
    for process in known(game):
        best = best_buyer(game, process)
        out.append({
            "process": process,
            "tech": TECH_BY_ID[process.tech],
            "held_by": [FACTIONS_BY_ID[p].short
                        for p in holders(game, process.tech)],
            "best": best,
            "forecast": (forecast(game, process, best["power"])
                         if best else None),
        })
    return out


def summary(game) -> dict:
    got = state(game)
    industries = sum(len(v) for v in got.held.values())
    return {
        "processes": len(PROCESSES),
        "sellable": len(known(game)),
        "licensed": industries,
        "earned": sum(row[3] for row in got.sold),
        "powers": sorted({row[2] for row in got.sold}),
    }
