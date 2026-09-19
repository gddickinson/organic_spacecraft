"""Where an officer's story wants the ship to go — chosen from the galaxy.

A place is chosen **when its beat arms**, not when the arc is drawn: the
nearest Bloom-held system on day one is often clean by the day the beacon's
beat comes round, and a story that sends a captain to a system the Bloom
left a year ago is a story about nothing. The choice is deterministic —
the galaxy as it stands and the officer's own key — so a save reloaded the
day before arms the same place.

Verge places prefer what the ship can reach at its present drive
(`reach.component`): a beat is a thing to do, and "wants to go somewhere no
jump of yours reaches" is a lapse the captain was never offered. Where no
such place is in reach, the beat names the nearest and waits on it without
lapsing (`beyond`), as it does for a place in an unopened region — returned
as its marker (`"region:hollow"`) — and `waiting_for` says what would open
the way.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..world.galaxy import distance, verge

#: Races are run at least this many of the ship's jumps away, and at most
#: `RACE_FAR`: one jump is a hop, not a race, and four is a crossing no
#: forty-five days covers (`data/arcs.RACE_DAYS`).
RACE_NEAR = 1.2
RACE_FAR = 2.6


#: `_reachable` by (seed, systems, here, drive), like `world/regions.anchors`'
#: memo. The walk is pure in those four — the charted lanes are laid at a
#: chronicle's start from its seed — and a beat waiting on a place asks every
#: day. Measured over two idle years: 0.15 ms added to a 0.9 ms day without
#: it, within the noise (±0.1) with it.
_REACH: dict = {}


def _reachable(game) -> set:
    """What the present drive can get to, or everything if nothing says."""
    from . import reach
    try:
        key = (game.galaxy.seed, len(game.galaxy.systems), game.location_id,
               round(float(game.ship_stats.jump), 6))
        if key not in _REACH:
            if len(_REACH) > 256:
                _REACH.clear()
            _REACH[key] = frozenset(reach.component(game))
        return _REACH[key]
    except (LookupError, AttributeError):
        return {s.id for s in game.galaxy.systems}


def _nearest(game, pool, rng=None, among: int = 1):
    """The nearest of `pool` that is not here — or, given `rng`, a seeded
    pick among the `among` nearest. None for an empty pool."""
    here = game.system
    near = sorted((s for s in pool if s.id != here.id),
                  key=lambda s: (distance(s, here), s.id))
    if not near:
        near = [s for s in pool if s.id == here.id]
    if not near:
        return None
    if rng is None or among <= 1:
        return near[0]
    return rng.pick(near[:among])


def _ports(game, power: str, capital: bool | None = None) -> list:
    out = []
    for s in verge(game.galaxy):
        port = s.port
        if port is None or getattr(port, "faction", None) != power:
            continue
        if capital is not None and bool(getattr(port, "capital", False)) \
                != capital:
            continue
        out.append(s)
    return out


def _within(game, pool) -> list:
    """The reachable part of a pool, or the pool itself if none of it is."""
    reach = _reachable(game)
    near = [s for s in pool if s.id in reach]
    return near or list(pool)


def _bloom(game):
    """The nearest Bloom-held system the drive reaches — or, when every mass
    is past the wall (early on it is only the heart, in the far corner), the
    reachable star nearest to one: the edge of Bloom country, which is as
    far in as a beacon's search or a week's study needs to go."""
    from . import threat
    held = list(threat.bloom_systems(game))
    if not held:
        from ..world.regions import heart
        held = [heart(verge(game.galaxy))]
    reach = _reachable(game)
    near = [s for s in held if s.id in reach]
    if near:
        return _nearest(game, near)
    edge = [s for s in verge(game.galaxy) if s.id in reach]
    return min(edge, key=lambda s: (min(distance(s, b) for b in held), s.id),
               default=_nearest(game, held))


def _port_of(game, power: str, capital: bool | None, rng):
    """The power's capital (or one of its other quays) that the drive can
    reach; failing that, any of its quays it can; failing that, the nearest
    of them — which the beat then waits on, and says so."""
    among = 3 if capital is False else 1
    tiers = [_ports(game, power, capital), _ports(game, power, None)]
    reach = _reachable(game)
    for pool in tiers:
        near = [s for s in pool if s.id in reach]
        if near:
            return _nearest(game, near, rng, among)
    pool = next((p for p in tiers if p), None) or \
        [s for s in verge(game.galaxy) if s.port]
    return _nearest(game, pool, rng, among)


def _moon(game, rng):
    pool = [s for s in verge(game.galaxy) if s.bloom < 0.3
            and any(b.kind == "moon" for b in s.bodies)]
    return _nearest(game, _within(game, pool), rng, 3)


def _wreck(game, rng):
    pool = [s for s in verge(game.galaxy) if s.port is None]
    return _nearest(game, _within(game, pool), rng, 4)


def _race(game, rng):
    """A finish a timed run can make: two or three jumps out, reachable."""
    jump = max(1.0, float(getattr(game.ship_stats, "jump", 1.0)))
    here = game.system
    reach = _reachable(game)
    pool = [s for s in verge(game.galaxy) if s.id in reach and s.id != here.id
            and RACE_NEAR * jump <= distance(s, here) <= RACE_FAR * jump]
    if pool:
        return rng.pick(sorted(pool, key=lambda s: s.id))
    far = [s for s in verge(game.galaxy) if s.id in reach and s.id != here.id]
    return max(far, key=lambda s: (distance(s, here), -s.id), default=None)


def resolve(game, rule: str, officer_id: int, beat: int):
    """The system id a beat's place rule names now, a region marker if the
    place is past an unopened rim, or None if the galaxy has no such place.
    """
    rng = RNG(f"{game.seed}:arc:{officer_id}:{beat}:place")
    if rule.startswith("region:"):
        from ..world import regions as world_regions
        held = world_regions.region(game.galaxy, rule.split(":", 1)[1])
        return rule if held is None else int(held.entry_id)
    if rule.startswith("anchor:"):
        from . import relight
        return relight.anchor_of(game, rule.split(":", 1)[1])
    found = {
        "bloom": lambda: _bloom(game),
        "freehold_capital": lambda: _port_of(game, "freeholds", True, rng),
        "freehold_port": lambda: _port_of(game, "freeholds", False, rng),
        "choir_port": lambda: _port_of(game, "sanhedrin", None, rng),
        "charter_capital": lambda: _port_of(game, "charter", True, rng),
        "yards_port": lambda: _port_of(game, "concordat", None, rng),
        "moon": lambda: _moon(game, rng),
        "wreck": lambda: _wreck(game, rng),
        "race": lambda: _race(game, rng),
    }[rule]()
    return None if found is None else int(found.id)


def beyond(game, place) -> bool:
    """Is a named system out of the present drive's reach? A system across
    the rim is reached through its deep gate — free and instant once lit —
    not by jumping, so it is never "beyond"; its clock runs like any other."""
    if not isinstance(place, int):
        return False
    target = game.galaxy.systems[place]
    if getattr(target, "region", "verge") != getattr(game.system, "region",
                                                    "verge"):
        return False
    return place not in _reachable(game)


def waiting_for(game, marker) -> str:
    """What would open the way: the relight for a place past a dark rim, a
    longer jump for one out of the drive's reach."""
    if isinstance(marker, int):
        return (f"{name(game, marker)} is out of reach at this drive: a longer "
                "jump, or a charted lane, would open the way.")
    from ..data.regions import ANCHOR_NAMES
    from . import relight
    region = marker.split(":", 1)[1]
    gate = ANCHOR_NAMES.get(region, "the deep anchor")
    anchor = relight.anchor_of(game, region)
    where = (f" at {game.galaxy.systems[anchor].name}"
             if anchor is not None else "")
    return (f"{gate[:1].upper()}{gate[1:]}{where} is dark. A deep survey "
            "there, the Deep Weave, and the relight bill would open it.")


def name(game, place) -> str:
    """A place as the prose says it."""
    if isinstance(place, int) and 0 <= place < len(game.galaxy.systems):
        return game.galaxy.systems[place].name
    if isinstance(place, str) and place.startswith("region:"):
        return "the " + place.split(":", 1)[1].title()
    return "somewhere"
