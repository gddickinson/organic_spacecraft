"""Markets.

Each port has its own supply and demand, drifting daily toward its own
equilibrium — so the profitable run between two systems stays profitable for a
while and then quietly stops being.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from ..data.commodities import BY_ID, COMMODITIES
from ..data.factions import FACTIONS_BY_ID, price_mod


@register
@dataclass
class Stock:
    supply: float      # > 1 locally abundant (cheap), < 1 locally short (dear)
    units: int
    trend: float
    #: Set by sim.market from live shocks; multiplies supply when pricing. It
    #: is kept apart from supply so the daily drift cannot quietly erase a
    #: blight, and so the shock can end cleanly.
    shock: float = 1.0


@register
@dataclass
class Market:
    stock: dict[str, Stock] = field(default_factory=dict)
    day: int = 0


def make_market(rng, system) -> Market:
    """Build a market for a port, skewed by what the system produces."""
    fac = FACTIONS_BY_ID.get(system.port.faction) if system.port else None
    level = system.port.level if system.port else 1
    stock: dict[str, Stock] = {}

    rich = {"ore": 0.0, "volatiles": 0.0, "phosphate": 0.0, "biomass": 0.0}
    for b in system.bodies:
        for k in rich:
            rich[k] = max(rich[k], b.resources.get(k, 0.0))

    for c in COMMODITIES:
        supply = rng.gauss(1, 0.42, 0.3, 2.1)
        if c.id in rich:
            supply *= 1 + rich[c.id] * 0.75
        if fac:
            if c.id in fac.sells:
                supply *= 1.55
            if c.id in fac.buys:
                supply *= 0.62
        if not c.legal:
            supply = rng.float(0.4, 1.1) if (fac and c.id in fac.sells) else 0.0
        stock[c.id] = Stock(max(0.0, supply),
                            round(supply * level * rng.int(30, 140)),
                            rng.float(-0.02, 0.02))
    return Market(stock)


def buy_price(market: Market, cid: str, rep: float = 0, trade_bonus: float = 0):
    """Unit price to buy from this market, or None if it stocks none."""
    s = market.stock.get(cid)
    c = BY_ID.get(cid)
    if s is None or c is None or s.supply <= 0:
        return None
    scarcity = 1 / max(0.25, s.supply * getattr(s, "shock", 1.0))
    raw = c.base * (0.55 + 0.55 * scarcity)
    return max(1, round(raw * price_mod(rep) * (1 - trade_bonus * 0.5)))


def sell_price(market: Market, cid: str, rep: float = 0, trade_bonus: float = 0):
    """Unit price this market pays you. Always below buy — that is the spread."""
    b = buy_price(market, cid, rep, 0)
    if b is None:
        c = BY_ID.get(cid)
        return max(1, round(c.base * 0.55 * (1 + trade_bonus))) if c else None
    return max(1, round(b * (0.80 + trade_bonus * 0.4)))


def apply_trade(market: Market, cid: str, units: float) -> None:
    """Buying drains local stock and pushes the price up."""
    s = market.stock.get(cid)
    if s is None:
        return
    s.units = max(0, s.units - units)
    s.supply = max(0.05, s.supply - units * 0.0016)


def apply_sale(market: Market, cid: str, units: float) -> None:
    """Selling floods it and pushes the price down."""
    s = market.stock.get(cid)
    if s is None:
        return
    s.units += units
    s.supply += units * 0.0013


def tick_market(market: Market, days: float, rng) -> None:
    """Daily drift back toward equilibrium, plus a small random walk."""
    for cid, s in market.stock.items():
        c = BY_ID.get(cid)
        eq = 1 + (c.volatility if c else 0.3) * s.trend * 12
        s.supply += (eq - s.supply) * min(0.6, 0.018 * days)
        s.supply = max(0.02, s.supply + rng.float(-0.012, 0.012) * days)
        s.units = max(0, round(s.units + (s.supply * 60 - s.units) * 0.03 * days))
        if rng.chance(0.02 * days):
            s.trend = rng.float(-0.03, 0.03)
    market.day += days


def price_note(market: Market, cid: str) -> tuple[str, str]:
    """A one-line read on whether a good is worth carrying out of here."""
    s = market.stock.get(cid)
    if s is None or s.supply <= 0:
        return "unavailable", "dim"
    supply = s.supply * getattr(s, "shock", 1.0)
    if supply > 1.6:
        return "glut", "chloro"
    if supply > 1.15:
        return "plentiful", "chloro"
    if supply < 0.5:
        return "acute shortage", "warn"
    if supply < 0.8:
        return "short", "osteo"
    return "steady", "dim"


def demands(market: Market, limit: int = 3) -> list[str]:
    """What this port is unusually keen to buy."""
    legal = [(cid, s) for cid, s in market.stock.items()
             if BY_ID.get(cid) and BY_ID[cid].legal]
    legal.sort(key=lambda kv: kv[1].supply * getattr(kv[1], "shock", 1.0))
    return [cid for cid, _ in legal[:limit]]
