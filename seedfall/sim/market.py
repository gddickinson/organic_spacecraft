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


def note_prices(game, system, rep: float = 0.0, trade: float = 0.0) -> None:
    """Write down what this port is paying. Called on arrival at a market."""
    if not system.market:
        return
    quote = Quote(system_id=system.id, day=game.day)
    for cid in system.market.stock:
        b = buy_price(system.market, cid, rep, trade)
        s = sell_price(system.market, cid, rep, trade)
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
    """
    out = []
    for key, quote in book(game).items():
        prices = quote.sell if selling else quote.buy
        if cid not in prices:
            continue
        system = game.galaxy.systems[quote.system_id]
        age = game.day - quote.day
        out.append({"system": system, "price": prices[cid], "age": age,
                    "confidence": confidence(age),
                    "shocked": bool([s for s in at(game, system.id)
                                     if s.commodity == cid])})
    out.sort(key=lambda row: row["price"], reverse=selling)
    return out[:limit]


def summary(game) -> dict:
    noted = book(game)
    fresh = [q for q in noted.values() if confidence(game.day - q.day) > 0.5]
    return {"ports": len(noted), "fresh": len(fresh),
            "shocks": len(all_shocks(game))}
