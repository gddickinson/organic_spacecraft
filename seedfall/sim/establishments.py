"""Which establishments are in a system, read off the chronicle's seed.

Nothing here is stored and nothing spends luck: the same system has the same
yard, the same Grand and the same den in every visit and every process,
drawn from `RNG(f"{seed}:establish:{system id}")` the way a derelict is. How
many a system has depends on its trade (`data/establishments.ODDS`): a
Fleet Hub has three or four, a quiet rock with no port one at most, and
the kinds that need a port to trade with only turn up where there is one.

`here(game, system)` is every establishment in a system as `Found` rows;
`sim/places.py` turns each into a `Place`, and `builds_here` answers the
yard's question for `sim/shipyard.can_build_here`.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.rng import RNG
from ..data.establishments import ESTABLISHMENTS, ODDS, WORDS


@dataclass(frozen=True)
class Found:
    """One establishment, at one body of one system."""

    kind: object
    name: str
    body_id: str
    body_name: str


def here(game, system) -> list:
    """Every establishment in this system, in the order the seed drew them."""
    if system is None or not getattr(system, "bodies", None):
        return []
    rng = RNG(f"{getattr(game, 'seed', 'verge')}:establish:{system.id}")
    port = getattr(system, "port", None)
    trade = "capital" if port is not None and getattr(
        port, "capital", False) else "port" if port is not None else "none"
    out, used = [], set()
    for odds in ODDS[trade]:
        if not rng.chance(odds):
            break
        pool = [(e.weight, e) for e in ESTABLISHMENTS
                if e.id not in used and (port is not None or not e.needs_port)
                and any(b.kind in e.at for b in system.bodies)]
        if not pool:
            break
        kind = rng.weighted(pool)
        used.add(kind.id)
        body = rng.pick([b for b in system.bodies if b.kind in kind.at])
        name = rng.pick(kind.names).format(body=body.name,
                                           word=rng.pick(WORDS))
        out.append(Found(kind, name, body.id, body.name))
    return out


def builds_here(game, system, need: str) -> bool:
    """Does a yard in this system lay down hulls that need `need`?"""
    return any(f.kind.builds == need for f in here(game, system))
