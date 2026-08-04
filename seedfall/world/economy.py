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
    #: What this port is structurally: an ore world's yards sit above one,
    #: a power's imports below it. `make_market` computes it and it does not
    #: move. Without it `tick_market` dragged every commodity at every port
    #: toward the same 1.0, so the geography this module builds — local
    #: resources, what a faction sells, what it is short of — was gone inside
    #: a year. Measured: the best trade in the sector fell from 533 credits a
    #: tonne of silicon in year zero to nought or negative, on everything,
    #: for ever after.
    base: float = 0.0
    #: Set by sim.market from live shocks; multiplies supply when pricing. It
    #: is kept apart from supply so the daily drift cannot quietly erase a
    #: blight, and so the shock can end cleanly.
    shock: float = 1.0
    #: Industry: what the holder of this berth has been taught to make here.
    #: Multiplies the *baseline* rather than the price, so an industry is a
    #: permanent change in what the place produces and the drift settles onto
    #: it, where a shock is a temporary change in what it costs and lifts
    #: cleanly. Written only by `sim.industry.industrialise`; `base` stays what
    #: `make_market` decided so the two can always be told apart.
    works: float = 1.0


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
        supply = max(0.0, supply)
        stock[c.id] = Stock(supply,
                            round(supply * level * rng.int(30, 140)),
                            rng.float(-0.02, 0.02), base=supply)
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
    """Unit price this market pays you. Always below buy — that is the spread.

    The last clause is enforced rather than hoped. The buy side applies the
    trade skill as a discount and this side applied it as a premium, so the
    two crossed at trade 0.222 — measured, 18,000 credits became 2,645,369 in
    two hundred same-counter round trips on day zero. The offer is clamped
    under what *this* captain would pay to buy the tonne back, so the spread
    survives every modifier either term grows in future.
    """
    b = buy_price(market, cid, rep, 0)
    if b is None:
        c = BY_ID.get(cid)
        return max(1, round(c.base * 0.55 * (1 + trade_bonus))) if c else None
    offered = round(b * (0.80 + trade_bonus * 0.4))
    asked = buy_price(market, cid, rep, trade_bonus)
    return max(1, min(offered, asked - 1))


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


def tick_market(market: Market, days: float, rng, level: int = 1) -> None:
    """Daily drift back toward equilibrium, plus a small random walk.

    **`level` is how big the port is, and it has to be passed in.** A berth's
    size is scaled into its opening stock by `make_market` — and then this
    function pulled every commodity at every port toward the same `supply × 60`
    regardless of it, so within about a month a Fleet Hub held exactly as much
    cargo as an outpost. The level was doing nothing but decorate the opening
    inventory.

    It matters more now than it did: the powers pay for their own ports and
    promote them up the ladder (`sim/exchequer.py`), so a berth's size is a
    thing that changes over a chronicle rather than a fact of generation. A hub
    is a deep market and an outpost is a thin one, permanently.
    """
    for cid, s in market.stock.items():
        c = BY_ID.get(cid)
        if s.base <= 0 and s.supply <= 0:
            # Not traded here at all, and the drift must leave it that way.
            # Two separate lines below used to lift it off zero on the very
            # first tick: the baseline shim wrote 1.0 when it found no
            # baseline, and the supply floor of 0.02 pushed the supply itself
            # up so that the shim then adopted *that*. Between them, a good
            # `make_market` deliberately left out of a port was on sale there
            # one day into the chronicle. Measured: unlicensed seed is stocked
            # at 9 ports in 21, and **all 21 sold it after a single day**,
            # which is most of the point of contraband gone. Found while
            # checking that licensing the seed process opens a trade
            # somewhere — there was nowhere left for it to open.
            continue
        if s.base <= 0:
            # A save written before ports had a character of their own. Adopt
            # whatever it is now rather than flattening it to the sector mean.
            #
            # **`and s.supply > 0` is not a nicety.** The old version wrote a
            # baseline of 1.0 whenever it found none, and a stock with no
            # baseline *and* no supply is not an old save — it is a good this
            # port does not trade. Unlicensed seed is stocked at six ports in
            # twenty-one by `make_market`, and this line quietly gave it a
            # sector-average baseline at all the others on the first tick: one
            # day into every chronicle, **all twenty-one ports would sell you
            # contraband**. Found while checking that licensing the seed process
            # opens a trade somewhere, because it turned out there was nowhere
            # left for it to open.
            s.base = s.supply
        # Toward what this port is, not toward the sector mean. The
        # docstring at the top of this module has always said "its own
        # equilibrium"; for a long time the arithmetic said 1.0.
        eq = (s.base * getattr(s, "works", 1.0)
              * (1 + (c.volatility if c else 0.3) * s.trend * 12))
        s.supply += (eq - s.supply) * min(0.6, 0.018 * days)
        s.supply = max(0.02, s.supply + rng.float(-0.012, 0.012) * days)
        deep = s.supply * 60 * max(1, level)
        s.units = max(0, round(s.units + (deep - s.units) * 0.03 * days))
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
