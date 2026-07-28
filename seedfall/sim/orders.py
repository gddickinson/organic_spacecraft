"""Deciding which standing orders apply right now.

One predicate per entry in `data/orders.py`, matched by id. Everything here
reads state and returns a bool — nothing changes the world, so this can be
called as often as a screen is drawn.
"""

from __future__ import annotations

from ..data.orders import ORDERS, ORDERS_BY_ID, SHOWN
from . import chains, colony as colony_sim, consorts, intel
from . import inquiry, loading, loyalty, market as market_sim
from . import rumours as rumour_sim
from . import ventures as venture_sim
from . import works as works_sim
from .ship import is_breached


def _at_port(game) -> bool:
    return bool(game.system.port)


# Each returns True when the order is worth putting in front of the captain.
PREDICATES = {
    "fuel": lambda g: g.ship.cargo.get("volatiles", 0) < 8,
    "air": lambda g: g.ship.o2 < 0.5,
    "breach": lambda g: is_breached(g.ship),
    "payroll": lambda g: (g.officers
                          and g.credits < sum(o.wage for o in g.officers) / 3),
    "restless": lambda g: bool(loyalty.restless(g)),

    "overloaded": lambda g: loading.loading(g.ship) > 1.05,
    "escort": lambda g: any(s is not g.ship and not getattr(s, "escort", False)
                            for s in g.fleet),

    "commission": lambda g: (_at_port(g)
                             and any(ok for _c, ok, _w
                                     in chains.offered(g, g.system))),
    "contracts": lambda g: _at_port(g) and not contracts_in_hand(g),
    "rumour": lambda g: _at_port(g) and not rumour_sim.held(g),

    "research": lambda g: g.research.current is None,
    "evidence": lambda g: bool(getattr(g.research, "starved", None)),
    "survey": lambda g: any(not b.surveyed for b in g.system.bodies),
    "land": lambda g: (g.expedition is None
                       and any(b.surveyed and b.kind not in ("gas", "star")
                               for b in g.system.bodies)),
    "colony": lambda g: (g.ship_stats.can_colonise
                         and not any(c.system_id == g.system.id
                                     for c in g.colonies)),
    "works": lambda g: any(c.online and not getattr(c, "job", None)
                           and works_sim.available(g, c)
                           for c in g.colonies),
    "survey_sale": lambda g: _at_port(g) and bool(intel.sellable(g)),

    "venture": lambda g: any(v.stance == "none" for v in venture_sim.live(g)),
    "bloom": lambda g: g.bloom_total > 0.12,
    "trade": lambda g: _at_port(g) and not g.ship.cargo,
}


def contracts_in_hand(game) -> list:
    from . import contracts as contract_sim
    return contract_sim.active(game)


def applies(game, order_id: str) -> bool:
    predicate = PREDICATES.get(order_id)
    if predicate is None:
        return False
    try:
        return bool(predicate(game))
    except Exception:
        # An order that cannot be evaluated is not worth crashing a screen for.
        return False


def standing(game, limit: int = SHOWN) -> list:
    """The orders that apply, most pressing first."""
    live = [o for o in ORDERS if applies(game, o.id)]
    live.sort(key=lambda o: -o.weight)
    return live[:limit]


def all_applicable(game) -> list:
    return [o for o in ORDERS if applies(game, o.id)]


def summary(game) -> dict:
    live = all_applicable(game)
    return {"count": len(live),
            "urgent": len([o for o in live if o.weight >= 90]),
            "ids": [o.id for o in live]}
