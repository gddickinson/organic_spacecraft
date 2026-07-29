"""Whether a port stays the kind of port it is.

`world/economy.py` opens by saying each port drifts "toward **its own**
equilibrium — so the profitable run between two systems stays profitable for a
while and then quietly stops being". `make_market` builds that character
carefully: a system rich in ore gives its port up to 1.75x the supply, a
faction's exports 1.55x, the things it is chronically short of 0.62x.

`tick_market` then dragged every commodity at every port toward
`1 + volatility * trend * 12` — a number with nothing to do with the port —
and the geography was gone inside a year.

Measured across eighteen ports, best arbitrage in the whole sector, per tonne:

    year 0   ore 4   alloy 34   biomass 10   phosphate 52   silicon 533
    year 1   ore 0   alloy 21   biomass 17   phosphate -20  silicon -7
    year 2   ore -3  alloy -9   biomass 2    phosphate -8   silicon -10

The spread in ore supply across ports fell from 0.431 to 0.117 in the first
year and sat near 0.09 for ever after. **After year one there was no trade in
the game**: buying at the cheapest port and selling at the dearest lost money
on every commodity in the sector.

`Stock.base` is what `make_market` decided, and `tick_market` reverts to that.
Trends still move a port around its own level, shocks still hit it, and buying
and selling still push it — but a mining world stays cheap in ore.

The claims:

- **A port keeps its character.** The general one: the spread between ports
  survives, rather than collapsing to a sector mean.
- **There is still a living in carrying things about**, years in.
- **A port is not frozen either** — its own prices still move.
- **A save written before ports had a baseline adopts one** rather than
  flattening.
"""

from __future__ import annotations

import statistics

from ..core.state import new_game
from ..world.economy import buy_price, sell_price
from .harness import Suite

GOODS = ("ore", "alloy", "biomass", "phosphate", "silicon")


def _fed(game, years: int, step: int = 7) -> None:
    """Run the clock without starving the crew into an ending."""
    for _ in range(int(years * 365 / step)):
        game.ship.cargo["biomass"] = 500
        game.advance_days(step)


def _ports(game, limit: int = 18) -> list:
    return [s for s in game.galaxy.systems if s.port and s.market][:limit]


def _best_margin(ports, cid: str):
    buys = [p for p in (buy_price(s.market, cid, 0) for s in ports) if p]
    sells = [p for p in (sell_price(s.market, cid, 0) for s in ports) if p]
    if not buys or not sells:
        return None
    return max(sells) - min(buys)


def run(suite: Suite) -> None:
    check = suite.check

    @check("a port keeps the character its geography gave it")
    def _():
        # The general question, and the one the old arithmetic failed: does
        # the difference *between* ports survive the passage of time, or does
        # everywhere become the same place?
        rows = []
        for seed in range(4):
            game = new_game(f"geo{seed}")
            ports = _ports(game)
            assert len(ports) >= 8, len(ports)
            opening = statistics.pstdev(
                s.market.stock["ore"].supply for s in ports)
            _fed(game, 8)
            later = statistics.pstdev(
                s.market.stock["ore"].supply for s in ports)
            rows.append((opening, later))
            assert later > opening * 0.6, (
                f"seed {seed}: the spread in ore supply across ports fell "
                f"from {opening:.3f} to {later:.3f} — eight years of drift "
                "and every port has become the same port")
        return ("ore supply spread across ports, opening → eight years: "
                + " · ".join(f"{a:.2f}→{b:.2f}" for a, b in rows))

    @check("there is still a living in carrying things about")
    def _():
        # The consequence a captain actually feels. Measured before the fix:
        # from year one the best arbitrage in the sector was zero or negative
        # on every commodity, for ever.
        game = new_game("living")
        ports = _ports(game)
        _fed(game, 6)
        margins = {cid: _best_margin(ports, cid) for cid in GOODS}
        alive = [cid for cid, m in margins.items() if m and m > 0]
        assert len(alive) >= 3, (
            f"six years in, only {alive} can be carried at a profit anywhere "
            f"in the sector: {margins}")
        best = max(m for m in margins.values() if m)
        assert best >= 20, (
            f"the best trade in the whole sector is {best} credits a tonne, "
            "which will not pay for the reaction mass to reach it")
        return (f"{len(alive)} of {len(GOODS)} goods worth carrying six years "
                f"in, best {best:,} cr/t")

    @check("a port is not frozen, only anchored")
    def _():
        # The other half: reverting to its own level must not stop it moving.
        # A market that never changes has no reason to be visited twice.
        game = new_game("moves")
        port = _ports(game)[0]
        seen = []
        for _ in range(8):
            seen.append(tuple(buy_price(port.market, c, 0) for c in GOODS))
            _fed(game, 1)
        changed = sum(1 for i in range(1, len(seen)) if seen[i] != seen[i - 1])
        assert changed >= len(seen) // 2, (
            f"prices at {port.name} moved in only {changed} of "
            f"{len(seen) - 1} years")
        # And it stays recognisably itself rather than wandering off.
        for cid in GOODS:
            stock = port.market.stock[cid]
            assert stock.base > 0, f"{cid} has no baseline at all"
            assert abs(stock.supply - stock.base) < stock.base * 3 + 1.5, (
                f"{cid} at {port.name} has drifted to {stock.supply:.2f} "
                f"against a baseline of {stock.base:.2f}")
        return f"prices at {port.name} moved in {changed} of 7 years"

    @check("the baseline is what the port was built as")
    def _():
        # `make_market` is the only thing that decides it, and it must record
        # what it decided rather than a rounded or default value.
        game = new_game("built")
        checked = 0
        for system in _ports(game, limit=6):
            for cid, stock in system.market.stock.items():
                if stock.supply <= 0:
                    continue
                assert abs(stock.base - stock.supply) < 1e-9, (
                    f"{system.name}/{cid}: opened at supply "
                    f"{stock.supply:.3f} with a baseline of {stock.base:.3f}")
                checked += 1
        assert checked > 40, checked
        # And the geography is genuinely varied, or the check above proves
        # nothing about anything.
        spread = statistics.pstdev(
            s.market.stock["ore"].supply for s in _ports(game))
        assert spread > 0.15, f"ore supply barely varies between ports: {spread}"
        return f"{checked} stocks, every baseline the supply it was built with"

    @check("a save written before ports had a baseline adopts one")
    def _():
        # `base` defaults to 0 and is adopted on the first tick, so an old
        # save keeps whatever character it had at the moment it was loaded
        # instead of being flattened to the sector mean.
        import json

        from ..core import save

        game = new_game("migrate")
        blob = json.loads(json.dumps(save.encode(game)))

        def strip(node):
            if isinstance(node, dict):
                node.pop("base", None)
                for value in node.values():
                    strip(value)
            elif isinstance(node, list):
                for value in node:
                    strip(value)

        strip(blob)
        old = save.decode(blob)
        old.recompute()
        port = _ports(old)[0]
        cid = next(c for c, s in port.market.stock.items() if s.supply > 0.3)
        was = port.market.stock[cid].supply
        assert port.market.stock[cid].base == 0.0, "the strip did nothing"
        old.advance_days(1)
        adopted = port.market.stock[cid].base
        assert abs(adopted - was) < 1e-9, (
            f"an old save's {cid} was at {was:.3f} and took a baseline of "
            f"{adopted:.3f} — its character was thrown away on load")
        return f"an old save adopted {adopted:.2f} rather than flattening to 1"
