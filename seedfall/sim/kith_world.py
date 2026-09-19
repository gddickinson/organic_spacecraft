"""Where the Kith are: their gatherings in the Cradle, and what each one likes.

The Cradle is grown with no port in it (`world/regions`), and this lays the
Kith's gatherings into it — **never by re-running the generator and never by
drawing from the region's stream**, as the `world/regions` docstring asks.
Everything here comes from seeds of its own, keyed on the galaxy's seed and
the system: which systems hold a gathering (`{seed}:kith:gatherings`), what
each is called and what it thinks of each good (`{seed}:kith:{system id}…`).
So a Cradle opened before the Kith existed and one opened after grow the same
gatherings, whenever `place` happens to run: at the relight
(`sim/relight`), on load for an older save (`core/loading`), or the first
day the clock finds the Cradle open and empty.

A gathering is a `Port(faction="kith")` on an unclaimed system (the Cradle
stays nobody's: `System.faction` is left None) with a market flagged
`gift_economy` — no line on it, no price posted, and `sim/enforce.may_trade`
refuses a buy or a sale there with the reason.

A gathering's **preferences** are not saved: they are a fact about the
gathering, derived afresh from its seed, and what the captain has *learned*
of them is saved instead (`KithState.known_prefs`).
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import kith as data
from ..data.commodities import COMMODITIES
from ..world import regions as world_regions
from ..world.economy import Market, add_line
from ..world.galaxy import Port, verge


def is_gathering(system) -> bool:
    """Is there a Kith gathering at this system?"""
    port = getattr(system, "port", None)
    return port is not None and port.faction == data.FACTION


def gatherings(galaxy) -> list:
    """Every gathering, in id order. Empty until the Cradle is open."""
    if world_regions.region(galaxy, data.CRADLE) is None:
        return []
    return [s for s in world_regions.systems_of(galaxy, data.CRADLE)
            if is_gathering(s)]


def chosen(galaxy) -> list:
    """The Cradle systems that hold a gathering, from their own seed.

    Never the entry: the first sighting is a colony keeping its distance at
    the edge of the region, not a quay waiting at the door.
    """
    opened = world_regions.region(galaxy, data.CRADLE)
    if opened is None:
        return []
    pool = [s for s in world_regions.systems_of(galaxy, data.CRADLE)
            if s.id != opened.entry_id]
    rng = RNG(f"{galaxy.seed}:kith:gatherings")
    count = min(len(pool), rng.int(data.GATHERINGS_MIN, data.GATHERINGS_MAX))
    return sorted(rng.sample(pool, count), key=lambda s: s.id)


def _name(galaxy, system, taken: set) -> str:
    rng = RNG(f"{galaxy.seed}:kith:{system.id}:name")
    for _ in range(40):
        name = f"{rng.pick(data.NAME_FIRST)}-{rng.pick(data.NAME_LAST)}"
        if name not in taken:
            return name
    return f"{name} {system.id}"


def place(galaxy) -> list:
    """Lay the gatherings into an open Cradle. Returns the systems placed.

    Idempotent: a system that already has its gathering is left alone, so a
    second call — on load, on the relight, from the clock — places nothing.
    """
    placed, taken = [], set()
    for system in chosen(galaxy):
        name = _name(galaxy, system, taken)
        taken.add(name)
        if system.port is not None:
            continue
        system.port = Port(data.PORT_KIND, name, 2, (data.PORT_KIND,),
                           data.FACTION, independent=True)
        system.market = Market(gift_economy=True)
        placed.append(system)
    if placed:
        open_buyers(galaxy)
    return placed


def ensure(game) -> list:
    """Place the gatherings if the Cradle is open and they are not there yet.

    The door the relight, the loader and the clock all come through, so an
    old save's Cradle is populated the moment it is read.
    """
    galaxy = game.galaxy
    if world_regions.region(galaxy, data.CRADLE) is None:
        return []
    return place(galaxy)


def open_buyers(galaxy) -> list:
    """Give the Verge's songglass buyers a line for it. Returns who got one.

    The Charter's and the Dry Choir's markets (`data/kith.SONGGLASS_BUYERS`),
    each from a seed of its own, the way the Shoals give condensate its
    buyers. Idempotent.
    """
    out = []
    for system in verge(galaxy):
        port, market = system.port, system.market
        if port is None or market is None or data.SONGGLASS in market.stock:
            continue
        short = data.SONGGLASS_BUYERS.get(port.faction)
        if short is None:
            continue
        rng = RNG(f"{galaxy.seed}:songglass:{system.id}")
        add_line(market, data.SONGGLASS, short, port.level, rng)
        out.append(system.id)
    return out


# ── what a gathering thinks of each good ───────────────────────────────────

_PREFS: dict = {}


def prefs(galaxy, system) -> dict:
    """Good → reaction at this gathering: the hidden truth, from its seed.

    Each good is drawn from a stream of its own, so a commodity added to the
    game later never reshuffles what a gathering thought of the others.
    """
    key = (galaxy.seed, system.id)
    hit = _PREFS.get(key)
    if hit is not None:
        return hit
    out = {}
    for good in COMMODITIES:
        rng = RNG(f"{galaxy.seed}:kith:{system.id}:{good.id}")
        prior = data.PRIORS.get(good.id, data.DEFAULT_PRIOR)
        out[good.id] = rng.weighted(list(prior))
    _PREFS[key] = out
    return out


def prior(cid: str) -> dict:
    """Reaction → probability for a good at a gathering nobody has asked."""
    rows = data.PRIORS.get(cid, data.DEFAULT_PRIOR)
    total = float(sum(w for w, _r in rows))
    out = {r: 0.0 for r in data.REACTIONS}
    for weight, reaction in rows:
        out[reaction] += weight / total
    return out


def graft_of(galaxy, system):
    """The graft this gathering grows (`data/kith.GRAFTS`), or None.

    Dealt round the gatherings in id order from a shuffled deck of the
    three, so every graft is grown somewhere in every Cradle.
    """
    order = list(data.GRAFTS)
    RNG(f"{galaxy.seed}:kith:grafts").shuffle(order)
    ids = [s.id for s in chosen(galaxy)]
    if system.id not in ids:
        return None
    return order[ids.index(system.id) % len(order)]
