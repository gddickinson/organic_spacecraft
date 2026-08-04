"""Market shocks, and what you remember about prices elsewhere.

Two halves of the same problem. Shocks make a market worth watching: a port is
short of alloy this season and paying for it, and will not be next year. The
register is how you can possibly know that from somewhere else — you write down
what you saw, and what you wrote down goes stale.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register as save_register
from ..data.commodities import BY_ID, COMMODITIES
from ..data.officials import QUIET_SHARE
from ..data.shocks import (MAX_PER_SYSTEM, ONSET_PER_MONTH, SHOCKS,
                           SHOCKS_BY_ID, STALE_DAYS)
from ..world.economy import buy_price, sell_price

_uid = itertools.count(1)


@save_register
@dataclass
class Shock:
    id: int
    kind: str
    system_id: int
    commodity: str
    until: int

    @property
    def definition(self):
        return SHOCKS_BY_ID[self.kind]

    def text(self, place: str) -> str:
        good = BY_ID.get(self.commodity)
        return self.definition.text.format(
            place=place, commodity=good.name if good else self.commodity)


@save_register
@dataclass
class Quote:
    """What you saw at a port, and when."""
    system_id: int
    day: int
    buy: dict = field(default_factory=dict)
    sell: dict = field(default_factory=dict)


# ── shocks ─────────────────────────────────────────────────────────────────

def all_shocks(game) -> list:
    if getattr(game, "shocks", None) is None:
        game.shocks = []
    return game.shocks


def at(game, system_id: int) -> list:
    return [s for s in all_shocks(game) if s.system_id == system_id]


def factor(game, system_id: int, cid: str) -> float:
    """How much a shock is moving one good at one port."""
    out = 1.0
    for shock in at(game, system_id):
        if shock.commodity == cid:
            out *= shock.definition.supply
    return out


def _pick_commodity(kind, system, rng) -> str | None:
    pool = [c.id for c in COMMODITIES if c.legal
            and (not kind.goods or c.id in kind.goods)]
    if system.market:
        pool = [c for c in pool if c in system.market.stock] or pool
    return rng.pick(pool) if pool else None


def tick(game, days: float, rng) -> list[tuple[str, str]]:
    """Age out finished shocks and start new ones. Returns log events."""
    live = all_shocks(game)
    events: list[tuple[str, str]] = []

    ended = [s for s in live if game.day >= s.until]
    if ended:
        game.shocks = [s for s in live if game.day < s.until]
        live = game.shocks

    ports = [s for s in game.galaxy.systems if s.port and s.market]
    chance = ONSET_PER_MONTH * (days / 30.0)
    for system in ports:
        if len(at(game, system.id)) >= MAX_PER_SYSTEM:
            continue
        if not rng.chance(chance):
            continue
        kind = rng.weighted([(k.weight, k) for k in SHOCKS])
        cid = _pick_commodity(kind, system, rng)
        if cid is None:
            continue
        shock = Shock(id=next(_uid), kind=kind.id, system_id=system.id,
                      commodity=cid, until=game.day + rng.int(*kind.days))
        live.append(shock)
        # You only hear about it if you have some way of knowing.
        if known_of(game, system.id):
            events.append(("warn" if kind.supply < 1 else "",
                           shock.text(system.name)))
    return events


def known_of(game, system_id: int) -> bool:
    """Whether news from this system would reach you at all."""
    system = game.galaxy.systems[system_id]
    if system.visited or system_id == game.location_id:
        return True
    return any(c.system_id == system_id for c in game.colonies)


def apply_to_markets(game) -> None:
    """Push live shocks onto the stock rows the price functions read.

    Recomputed wholesale each tick rather than adjusted, so a shock that has
    expired lifts cleanly and two overlapping ones cannot drift out of step.
    """
    touched = {s.system_id for s in all_shocks(game)}
    for system in game.galaxy.systems:
        if not system.market:
            continue
        for cid, stock in system.market.stock.items():
            want = factor(game, system.id, cid) if system.id in touched else 1.0
            if stock.shock != want:
                stock.shock = want


# ── the register ───────────────────────────────────────────────────────────

def book(game) -> dict:
    if getattr(game, "register", None) is None:
        game.register = {}
    return game.register


def _office_rate(game, system) -> bool:
    """Does this counter owe you the office rate right now?"""
    from . import officials as officials_sim
    return (officials_sim.favour_running(game, system, "quiet_price") > 0
            or officials_sim.pending_once(game, system, "quiet_price"))


def quote_buy(game, system, cid: str):
    """What this quay would actually charge *you*, memory included.

    One helper rather than a bias applied at the till, because a screen that
    quotes one number and charges another is the defect this project keeps
    finding. `note_prices`, `trade.buy` and the port screen all read this.
    """
    if not system.market or not system.port:
        return None
    from . import grudge as grudge_sim
    rep = game.rep.get(system.port.faction, 0)
    raw = buy_price(system.market, cid, rep, game.ship_stats.trade)
    if raw is None:
        return None
    raw *= grudge_sim.price_bias(game, system.port.faction)
    # The office rate, if somebody behind the counter owes you one. Applied
    # here and not at the till: this helper exists precisely so the screen and
    # the counter cannot quote different numbers, and the favour was breaking
    # that from the moment it was added.
    if _office_rate(game, system):
        raw *= QUIET_SHARE
    return max(1, round(raw))


def quote_sell(game, system, cid: str):
    """What this quay would actually pay you, memory included."""
    if not system.market or not system.port:
        return None
    from . import grudge as grudge_sim
    rep = game.rep.get(system.port.faction, 0)
    raw = sell_price(system.market, cid, rep, game.ship_stats.trade)
    if raw is None:
        return None
    # A power that remembers you badly charges more and pays less, so the
    # bias is inverted on the way out.
    bias = grudge_sim.price_bias(game, system.port.faction)
    if bias:
        raw = raw / bias
    if _office_rate(game, system):
        raw = raw / QUIET_SHARE          # the same twelve per cent, your way
    # Warm memory and the office rate act on both sides of the counter, and
    # inverting a favourable modifier squares it across the pair — at bias
    # 0.82 that alone was a 49% instant round-trip profit. The law is stated
    # where both quotes exist: the same counter never pays more than it asks.
    asked = quote_buy(game, system, cid)
    if asked is not None:
        raw = min(raw, asked - 1)
    return max(1, round(raw))


def note_prices(game, system, rep: float = 0.0, trade: float = 0.0) -> None:
    """Write down what this port is paying. Called on arrival at a market."""
    if not system.market:
        return
    quote = Quote(system_id=system.id, day=game.day)
    for cid in system.market.stock:
        b = quote_buy(game, system, cid)
        s = quote_sell(game, system, cid)
        if b is not None:
            quote.buy[cid] = b
        if s is not None:
            quote.sell[cid] = s
    book(game)[str(system.id)] = quote


def age_of(game, system_id: int) -> int | None:
    quote = book(game).get(str(system_id))
    return None if quote is None else game.day - quote.day


def confidence(age: int | None) -> float:
    """How much a noted price is still worth, 0..1."""
    if age is None:
        return 0.0
    return max(0.0, 1.0 - age / STALE_DAYS)


def best_markets(game, cid: str, selling: bool = True, limit: int = 4) -> list[dict]:
    """Where your notes say to take this, best first.

    Everything here is remembered rather than observed: the age is part of the
    answer, because a price you wrote down two years ago is a rumour.

    **"Best" used to mean the biggest number, which is a sticker price and not a
    decision.** The rows carried no distance at all and the panel drew a
    straight-line light-year count beside them, so a port eight hops and
    sixty-five days away outranked one a single hop and eight days off for
    paying three credits more. Measured over six sectors and six commodities:

    - **32% of the recommendations were to systems the ship cannot reach at
      all** — not far, not dear, unreachable, and nothing said so.
    - **44% of the lists put a worse port first.** The worst case had the
      register's first choice for ore worth 0.5 a day against another entry on
      the same list worth 3.9 — **seven times better, ranked below it.**

    `reach.routes_from` has existed since the contract board needed it, for
    exactly this reason: its docstring says the board "named a reward and a
    deadline and never once said where the work *was*". So the rows carry `hops`
    and `days` now, and selling ranks on **revenue a day** — which is what a
    captain choosing between two ports is actually choosing between.

    Buying ranks on the price, cheapest first, with the days breaking ties: what
    you want is the low number, and how far you will go for it is yours to
    weigh rather than mine to fold into one figure.

    The unreachable are kept and marked rather than dropped. A list that
    silently omitted a third of what it knows would be a different kind of lie,
    and a jump drive is a thing a captain can go and buy.
    """
    from . import reach as reach_sim
    routes = reach_sim.routes_from(game)
    out = []
    for key, quote in book(game).items():
        prices = quote.sell if selling else quote.buy
        if cid not in prices:
            continue
        system = game.galaxy.systems[quote.system_id]
        age = game.day - quote.day
        route = routes.get(quote.system_id)
        days = route["days"] if route else None
        price = prices[cid]
        out.append({"system": system, "price": price, "age": age,
                    "confidence": confidence(age),
                    "hops": route["hops"] if route else None,
                    "days": days,
                    "reachable": route is not None,
                    # Revenue a day of standing here and taking it there. Zero
                    # for somewhere unreachable, which sorts it to the bottom
                    # without hiding it.
                    "per_day": (price / max(days, 1)) if route else 0.0,
                    # **A berth can close now.** The powers pay for their own
                    # ports, and one that falls off the bottom of the ladder
                    # takes its market with it (`sim/exchequer.py`). The note
                    # in the register is still a true record of a price that
                    # was paid there — but there is nothing there to pay it
                    # any more, and a list that did not say so would be
                    # sending a captain to an empty orbit.
                    "open": system.market is not None,
                    "shocked": bool([s for s in at(game, system.id)
                                     if s.commodity == cid])})
    if selling:
        out.sort(key=lambda row: (row["open"], row["reachable"],
                                  row["per_day"]), reverse=True)
    else:
        out.sort(key=lambda row: (not row["open"], not row["reachable"],
                                  row["price"],
                                  row["days"] if row["days"] is not None
                                  else 10 ** 6))
    return out[:limit]


def summary(game) -> dict:
    noted = book(game)
    fresh = [q for q in noted.values() if confidence(game.day - q.day) > 0.5]
    return {"ports": len(noted), "fresh": len(fresh),
            "shocks": len(all_shocks(game))}
