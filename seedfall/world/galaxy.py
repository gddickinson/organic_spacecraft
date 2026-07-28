"""Sector generation.

The Verge is forty-odd stars in a seventy-light-year field, seeded so the same
seed always grows the same sky.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.save import register
from ..core.rng import RNG
from ..data.factions import FACTIONS
from ..data.lore import STAR_PREFIX, STAR_SUFFIX
from ..data.xenotech import CULTURES, XENOTECH, by_culture
from .economy import Market, make_market
from .planets import Body, make_body

#: (id, name, heat, tint, weight)
STAR_CLASSES = [
    ("M", "M-type red dwarf", 0.32, "#e07a5f", 34),
    ("K", "K-type orange", 0.52, "#e6ac6d", 22),
    ("G", "G-type yellow", 0.70, "#f2e3a0", 16),
    ("F", "F-type white", 0.86, "#e8f0f5", 9),
    ("A", "A-type blue-white", 1.00, "#b8d8ff", 5),
    ("D", "white dwarf", 0.18, "#cfe6ff", 5),
    ("N", "neutron star", 0.10, "#9fd8ff", 2),
    ("B", "binary pair", 0.78, "#ffd9a0", 7),
]

SECTOR_W = 74.0
SECTOR_H = 52.0

# No star may sit further than this from its nearest neighbour. A starting hull
# jumps a little under eight light-years, so a sparse corner of the sector would
# otherwise strand a captain with nowhere legal to go.
MAX_LANE = 6.2
MIN_SEP = 3.2

#: (id, name, level, services)
PORT_KINDS = [
    ("outpost", "Outpost", 1, ("market", "repair")),
    ("station", "Station", 2, ("market", "repair", "shipyard", "recruit")),
    ("hub", "Fleet Hub", 3,
     ("market", "repair", "shipyard", "recruit", "research", "gestation")),
]


@register
@dataclass
class Port:
    id: str
    name: str
    level: int
    services: tuple[str, ...]
    faction: str
    capital: bool = False
    independent: bool = False
    player_built: bool = False


@register
@dataclass
class System:
    id: int
    name: str
    x: float
    y: float
    star: str
    star_name: str
    tint: str
    heat: float
    bodies: list[Body]
    faction: str | None = None
    port: Port | None = None
    market: Market | None = None
    bloom: float = 0.0
    visited: bool = False
    scanned: bool = False
    note: str | None = None


@register
@dataclass
class Galaxy:
    seed: str
    systems: list[System]
    w: float = SECTOR_W
    h: float = SECTOR_H


def distance(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def _system_name(rng, used: set) -> str:
    for _ in range(60):
        pre, suf = rng.pick(STAR_PREFIX), rng.pick(STAR_SUFFIX)
        name = f"{pre}'s {suf}" if rng.chance(0.35) else f"{pre} {suf}"
        if name not in used:
            used.add(name)
            return name
    fallback = f"Verge {len(used) + 1}"
    used.add(fallback)
    return fallback


def _scatter(rng, count: int) -> list[dict]:
    """Stars on a jittered grid, then relaxed until the sector is navigable."""
    cols = max(2, math.ceil(math.sqrt(count * SECTOR_W / SECTOR_H)))
    rows = max(2, math.ceil(count / cols))
    cw = (SECTOR_W - 8) / cols
    ch = (SECTOR_H - 8) / rows

    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    pts = [{"x": 4 + c * cw + cw * rng.float(0.18, 0.82),
            "y": 4 + r * ch + ch * rng.float(0.18, 0.82)}
           for c, r in cells[:count]]

    for _ in range(8):
        moved = False
        for p in pts:
            near, nd = None, math.inf
            for q in pts:
                if q is p:
                    continue
                d = math.hypot(q["x"] - p["x"], q["y"] - p["y"])
                if d < nd:
                    near, nd = q, d
            if near is None:
                continue
            if nd > MAX_LANE:
                t = (nd - MAX_LANE * 0.85) / nd
                p["x"] += (near["x"] - p["x"]) * t
                p["y"] += (near["y"] - p["y"]) * t
                moved = True
            elif nd < MIN_SEP and nd > 0.001:
                t = (MIN_SEP - nd) / nd
                p["x"] = max(3, min(SECTOR_W - 3, p["x"] - (near["x"] - p["x"]) * t * 0.5))
                p["y"] = max(3, min(SECTOR_H - 3, p["y"] - (near["y"] - p["y"]) * t * 0.5))
                moved = True
        if not moved:
            break
    return pts


def widest_lane(systems) -> float:
    """How far the loneliest star sits from its nearest neighbour."""
    worst = 0.0
    for s in systems:
        d = min((distance(s, t) for t in systems if t is not s), default=0.0)
        worst = max(worst, d)
    return worst


def generate_sector(seed_str: str, count: int = 42) -> Galaxy:
    rng = RNG(f"{seed_str}:sector")
    pts = _scatter(rng, count)
    used: set = set()
    owners = [f.id for f in FACTIONS if not f.hidden and not f.hostile]

    systems: list[System] = []
    for i, p in enumerate(pts):
        sc = rng.weighted([(s[4], s) for s in STAR_CLASSES])
        name = _system_name(rng, used)
        n_bodies = rng.weighted([(1, 1), (3, 2), (5, 3), (5, 4), (3, 5), (2, 6), (1, 7)])
        bodies = [make_body(rng, name, j, n_bodies, sc[2]) for j in range(n_bodies)]
        systems.append(System(i, name, p["x"], p["y"], sc[0], sc[1], sc[3], sc[2], bodies))

    _assign_ports(rng, systems, owners)
    _seed_relics(rng, systems)
    _seed_bloom(rng, systems)
    return Galaxy(seed_str, systems)


def _assign_ports(rng, systems, owners) -> None:
    """Factions cluster: each takes a seed star and the nearest handful to it."""
    claimed: set[int] = set()
    seeds = rng.sample(systems, len(owners))
    for fid, seed_sys in zip(owners, seeds):
        near = sorted((s for s in systems if s.id not in claimed),
                      key=lambda s: distance(s, seed_sys))[:rng.int(4, 7)]
        for j, s in enumerate(near):
            claimed.add(s.id)
            s.faction = fid
            if j == 0:
                k = PORT_KINDS[2]
                s.port = Port(k[0], k[1], k[2], k[3], fid, capital=True)
            elif j <= 2 or rng.chance(0.5):
                k = PORT_KINDS[1] if rng.chance(0.45) else PORT_KINDS[0]
                s.port = Port(k[0], k[1], k[2], k[3], fid)

    # A scatter of independent outposts out in the unclaimed dark.
    for s in systems:
        if s.port is None and rng.chance(0.16):
            k = PORT_KINDS[0]
            s.port = Port(k[0], k[1], k[2], k[3], "freeholds", independent=True)
            s.faction = s.faction or "freeholds"
        if s.port:
            s.market = make_market(rng, s)


def _seed_relics(rng, systems) -> None:
    """Scatter alien sites.

    Every technology gets at least one site so no chronicle is unwinnable, and
    the commoner ones get two. Sites land on body kinds that suit the culture —
    the Abyssals are under ice, the Ossuary is buried in rock.
    """
    for tech in XENOTECH:
        culture = next((c for c in CULTURES if c.id == tech.culture), None)
        if culture is None:
            continue
        candidates = [(s, b) for s in systems for b in s.bodies
                      if b.kind in culture.sites and b.relic is None]
        if not candidates:
            candidates = [(s, b) for s in systems for b in s.bodies if b.relic is None]
        if not candidates:
            return
        # The deepest technologies are rarer; the entry-level ones turn up twice.
        wanted = 1 if tech.requires else 2
        for _sys, body in rng.sample(candidates, min(wanted, len(candidates))):
            body.relic = tech.id


def _seed_bloom(rng, systems) -> None:
    """The Bloom starts at Kessel's Reach — the far corner — and spreads."""
    origin = max(systems, key=lambda s: s.x + s.y)
    origin.bloom = 1.0
    origin.name = "Kessel's Reach"
    origin.port = None
    origin.market = None
    origin.faction = "bloom"
    origin.note = ("Origin of the unlicensed lineage. Everything here has been "
                   "eaten.")
    for s in systems:
        if s is not origin and distance(s, origin) <= 14 and rng.chance(0.45):
            s.bloom = rng.float(0.15, 0.5)


def in_range(systems, origin, jump: float) -> list[System]:
    """Systems reachable in one jump."""
    return [s for s in systems if s is not origin and distance(s, origin) <= jump]


def transit_days(ly: float, speed: float) -> int:
    """Days of transit for a jump of ``ly`` at a given drive speed."""
    return max(1, round((2.2 + ly * 1.35) / max(0.25, speed)))


def nearest_port(systems, origin):
    ports = [s for s in systems if s.port]
    return min(ports, key=lambda s: distance(s, origin)) if ports else None
