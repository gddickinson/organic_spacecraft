"""Growing the Far Reaches: where the deep anchors stand, and what is behind them.

`data/regions.py` says what each region is like. This lays one out, once, on
the day its deep anchor is relit — never before. Three rules, and each is a
trap somebody would otherwise fall into:

- **The Verge is never re-rolled.** A region draws only from
  `RNG(f"{seed}:region:{id}")`, a stream of its own, and appends; nothing of
  the Verge's sequence is touched, so every existing seed and every pinned
  fixture keeps the sky it had. `test_reaches` hashes every Verge system
  before and after opening all three.
- **Appended with id == index.** The code says `galaxy.systems[sid]` in
  seventy-two places. A region's systems go on the end of the list in one
  block, numbered where they land.
- **Each region is its own frame.** `x`/`y` are local to `Region.w`/`h`, and
  `galaxy.distance` is infinite across the rim, so a hop, a raid or a Bloom
  throw cannot cross it. `span` is the one door for "how far, by way of the
  gates" — what a price per light year or a courier's days needs.

**For the Kith (innovation 2).** The Cradle is generated with every system
unclaimed (`faction=None`) and no port. To put gatherings in an
already-generated Cradle, derive them from the Cradle's own systems and a
seed of their own — `RNG(f"{seed}:kith:{system.id}")` — and set `port` and
`market` on the systems chosen; never re-run `generate`, and never draw from
the region's stream, so a save opened before the Kith existed and one opened
after grow the same Cradle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.rng import RNG, hash_seed
from ..core.save import register
from ..data import regions as data
from ..data import remnants as remnant_data
from .economy import Market, Stock, add_line, make_market
from .galaxy import PORT_KINDS, Port, System, _system_name, distance, verge
from .planets import Anomaly, make_body


@register
@dataclass
class Region:
    """One opened region: its frame, and the two ends of its deep gate."""

    id: str
    name: str
    w: float
    h: float
    #: The Verge system whose deep anchor was relit.
    anchor_id: int
    #: The region's own system on the far side of it.
    entry_id: int
    opened_day: int = 0
    #: The region's own lit rings, as [a, b] system-id pairs. Only the Hollow
    #: has any: older than the Weave, toll-free, and lit.
    rings: list = field(default_factory=list)


# ── where the deep anchors stand ───────────────────────────────────────────

#: `anchors` by galaxy seed and Verge size. Pure in both, like `weave.sites`.
_ANCHORS: dict = {}


def heart(systems):
    """Kessel's Reach by the generator's own rule: the far corner, max x + y.

    Asked of the Verge only. A region's frame starts at its own origin, so a
    Cradle star at (35, 27) would otherwise out-rank the Verge's far corner
    the day the Cradle opened, and the Bloom's heart would move.
    """
    return max(systems, key=lambda s: s.x + s.y)


def anchors(galaxy) -> dict:
    """Region id -> the Verge system its deep anchor stands in.

    Deterministic from the Verge's own geometry: the Shoals behind the
    westmost star, the Hollow the northmost (the chart's top edge), the
    Cradle the eastmost that is not Kessel's Reach. One system never holds
    two, and none stands on the Bloom's heart.
    """
    home = verge(galaxy)
    key = (galaxy.seed, len(home))
    hit = _ANCHORS.get(key)
    if hit is not None:
        return hit
    taken = {heart(home).id}
    order = {"west": lambda s: s.x, "north": lambda s: s.y,
             "east": lambda s: -s.x}
    out = {}
    for spec in data.REGIONS:
        pool = [s for s in home if s.id not in taken]
        if not pool:
            break
        pick = min(pool, key=lambda s, f=order[spec.rim]: (f(s), s.id))
        out[spec.id] = pick.id
        taken.add(pick.id)
    _ANCHORS[key] = out
    return out


def region(galaxy, region_id: str):
    """The opened `Region` record, or None if it has not been relit."""
    return next((r for r in getattr(galaxy, "regions", ()) or ()
                 if r.id == region_id), None)


def systems_of(galaxy, region_id: str) -> list:
    """Every system in one region, in id order."""
    return [s for s in galaxy.systems
            if getattr(s, "region", data.VERGE) == region_id]


# ── how far, by way of the gates ───────────────────────────────────────────

def _to_verge(galaxy, system) -> tuple:
    """(the Verge system this one is reached through, light years to it)."""
    rid = getattr(system, "region", data.VERGE)
    if rid == data.VERGE:
        return system, 0.0
    opened = region(galaxy, rid)
    if opened is None:
        return None, math.inf
    entry = galaxy.systems[opened.entry_id]
    return galaxy.systems[opened.anchor_id], distance(system, entry)


def span(galaxy, a, b) -> float:
    """Light years from one system to another *through the deep gates*.

    Within a region it is `distance`. Across the rim it is the way a hull
    would actually go: to its region's entry, through (a gate crossing is no
    distance at all), and on from the anchor. What a price per light year, a
    courier's days or a machine's light-lag wants — never what a drive can
    hop, which is `distance` and is infinite.
    """
    if galaxy is None:
        return distance(a, b)
    if getattr(a, "region", data.VERGE) == getattr(b, "region", data.VERGE):
        return distance(a, b)
    here, out = _to_verge(galaxy, a)
    there, back = _to_verge(galaxy, b)
    if here is None or there is None:
        return math.inf
    return out + distance(here, there) + back


# ── laying one out ─────────────────────────────────────────────────────────

def _scatter(rng, spec) -> list[dict]:
    """`galaxy._scatter`'s jittered grid and relaxation, in the region's frame."""
    w, h = spec.w, spec.h
    cols = max(2, math.ceil(math.sqrt(spec.count * w / h)))
    rows = max(2, math.ceil(spec.count / cols))
    cw, ch = (w - 6) / cols, (h - 6) / rows
    cells = [(c, r) for r in range(rows) for c in range(cols)]
    rng.shuffle(cells)
    pts = [{"x": 3 + c * cw + cw * rng.float(0.2, 0.8),
            "y": 3 + r * ch + ch * rng.float(0.2, 0.8)}
           for c, r in cells[:spec.count]]
    for _ in range(10):
        moved = False
        for p in pts:
            near = min((q for q in pts if q is not p),
                       key=lambda q: math.hypot(q["x"] - p["x"], q["y"] - p["y"]))
            nd = math.hypot(near["x"] - p["x"], near["y"] - p["y"])
            if nd > spec.max_lane:
                t = (nd - spec.max_lane * 0.85) / nd
                p["x"] += (near["x"] - p["x"]) * t
                p["y"] += (near["y"] - p["y"]) * t
                moved = True
            elif 0.001 < nd < spec.min_sep:
                t = (spec.min_sep - nd) / nd * 0.5
                p["x"] = max(2, min(w - 2, p["x"] - (near["x"] - p["x"]) * t))
                p["y"] = max(2, min(h - 2, p["y"] - (near["y"] - p["y"]) * t))
                moved = True
        if not moved:
            break
    return _connect(pts, spec)


def _connect(pts: list[dict], spec) -> list[dict]:
    """Pull stray clusters in until every star can be hopped to at `link`.

    No draws: the nearest outside star moves along the line to the nearest
    inside one until it is just within reach, and the walk repeats. The
    stream is `_scatter`'s alone, so a region grows the same sky whether
    this had anything to do or not.
    """
    reach = spec.link * 0.95
    joined = {0}
    while len(joined) < len(pts):
        grew = True
        while grew:
            grew = False
            for i, p in enumerate(pts):
                if i not in joined and any(
                        math.hypot(p["x"] - pts[j]["x"], p["y"] - pts[j]["y"])
                        <= spec.link for j in joined):
                    joined.add(i)
                    grew = True
        if len(joined) == len(pts):
            break
        gap, far, near = min(
            (math.hypot(pts[i]["x"] - pts[j]["x"], pts[i]["y"] - pts[j]["y"]), i, j)
            for i in range(len(pts)) if i not in joined for j in joined)
        t = (gap - reach) / gap
        pts[far]["x"] += (pts[near]["x"] - pts[far]["x"]) * t
        pts[far]["y"] += (pts[near]["y"] - pts[far]["y"]) * t
    return pts


def _bodies(rng, spec, name: str, star) -> list:
    """A system's bodies, as the Verge grows them, then made over for here."""
    n = rng.weighted([(1, 1), (3, 2), (5, 3), (5, 4), (3, 5), (2, 6), (1, 7)])
    bodies = [make_body(rng, name, j, n, star[2], star[0]) for j in range(n)]
    leavings = remnant_data.of(star[0])
    if leavings is not None:
        keep = max(1, min(len(bodies), leavings.keeps))
        bodies = bodies[len(bodies) - keep:]
    for body in bodies:
        _make_over(spec.id, name, body)
    return bodies


def _make_over(region_id: str, system_name: str, body) -> None:
    """What the region does to a body the ordinary generator made.

    The Shoals are volatile-rich (the nebula is the feedstock), the Cradle's
    young rock carries the richest ore grades in the sky, and a share of the
    Hollow's worlds are rogues with no sun at all — chosen from the body's own
    identity rather than a draw, so this changes nothing about the stream.
    """
    res = body.resources
    if region_id == "shoals":
        res["volatiles"] = min(1.0, res.get("volatiles", 0.0) * 1.35 + 0.15)
    elif region_id == "cradle":
        res["ore"] = min(1.0, res.get("ore", 0.0) * 1.45 + 0.10)
    elif region_id == "hollow" and body.kind not in ("gas",):
        share = (hash_seed(f"rogue|{system_name}|{body.id}") % 1000) / 1000.0
        if share < data.ROGUE_SHARE:
            body.sunless = True
            body.temp_k = min(body.temp_k, 40 + int(share * 60))
            body.biome = "cryo" if body.kind in ("ice", "comet") else "barren"
            # Nothing photosynthetic survives a world with no light on it.
            body.lifeforms = [lf for lf in body.lifeforms
                              if lf.metabolism != "photo"]
            if share < data.ROGUE_SHARE * data.RUIN_SHARE:
                # Where the Hollow's makers left something: a site a survey
                # can find, on a world where the tank is what you breathe.
                body.anomaly = Anomaly(*data.PRECURSOR_RUIN)


def _entry(spec, placed: list):
    """The system nearest the Verge: the region's rim that faces home."""
    facing = {"west": lambda s: -s.x, "north": lambda s: -s.y,
              "east": lambda s: s.x}[spec.rim]
    return min(placed, key=lambda s: (facing(s), s.id))


def _ports(rng, spec, placed: list) -> None:
    """Freehold havens in the Shoals, one derelict relay in the Hollow, and
    nothing at all in the Cradle, which is left unclaimed for the Kith."""
    if spec.id == "shoals":
        havens = rng.sample(placed, rng.int(2, 3))
        for index, system in enumerate(havens):
            kind = PORT_KINDS[1] if index == 0 else PORT_KINDS[0]
            services = tuple(x for x in kind[3] if x != "shipyard")
            system.port = Port(kind[0], data.HAVEN_NAME, kind[2], services,
                               "freeholds", independent=True)
            system.faction = "freeholds"
            system.market = make_market(rng, system)
    elif spec.id == "hollow":
        relay = max(placed, key=lambda s: (len(s.bodies), -s.id))
        relay.port = Port(PORT_KINDS[0][0], data.RELAY_NAME, 1, ("repair",),
                          "freeholds", independent=True)
        # A caretaker's stock and nothing else: reaction mass and rock. The
        # one place in a region of nine-light-year lanes you can buy fuel.
        relay.market = Market({cid: Stock(sup, round(sup * 60), 0.0, base=sup)
                               for cid, sup in (("volatiles", 1.3),
                                                ("ore", 1.1))})


def _rings(placed: list, entry) -> list:
    """The Hollow's own lit rings: its longest crossings, entry first."""
    far = max((s for s in placed if s is not entry),
              key=lambda s: (distance(s, entry), -s.id))
    rings, used = [[entry.id, far.id]], {entry.id, far.id}
    pairs = sorted(((distance(a, b), a.id, b.id) for a in placed for b in placed
                    if a.id < b.id), reverse=True)
    for _span, a, b in pairs:
        if len(rings) >= data.HOLLOW_RINGS:
            break
        if a in used or b in used:
            continue
        rings.append([a, b])
        used |= {a, b}
    return rings


def _names(galaxy, region_id: str) -> list[str]:
    """A region's star names — the same whichever order regions are opened in.

    From a stream of their own, so a name that collides and is drawn again
    cannot shift the region's stars and worlds; and each region avoids the
    Verge's names and those of every region listed before it in
    `data/regions.REGIONS`, which are computed rather than looked up. Drawn
    from the region's main stream and avoiding whatever happened to be open,
    the Hollow grown after the Shoals was a different Hollow from the one
    grown first.
    """
    used = {s.name for s in verge(galaxy)}
    for spec in data.REGIONS:
        rng = RNG(f"{galaxy.seed}:region:{spec.id}:names")
        mine = [_system_name(rng, used) for _ in range(spec.count)]
        if spec.id == region_id:
            return mine
    return []


def generate(galaxy, region_id: str, day: int = 0):
    """Lay a region out and append it. Returns the `Region`, or the one
    already there — opening twice grows nothing twice."""
    have = region(galaxy, region_id)
    if have is not None:
        return have
    spec = data.REGIONS_BY_ID[region_id]
    # Asked before anything is appended: `verge` is the whole list until the
    # first region is on record, and the anchors are the Verge's geometry.
    anchor_id = anchors(galaxy)[region_id]
    rng = RNG(f"{galaxy.seed}:region:{region_id}")
    names = _names(galaxy, region_id)
    first = len(galaxy.systems)
    placed = []
    for index, p in enumerate(_scatter(rng, spec)):
        star = rng.weighted([(s[4], s) for s in spec.stars])
        name = names[index]
        system = System(first + index, name, p["x"], p["y"], star[0], star[1],
                        star[3], star[2], _bodies(rng, spec, name, star),
                        region=region_id)
        placed.append(system)
    _ports(rng, spec, placed)
    entry = _entry(spec, placed)
    galaxy.systems.extend(placed)
    made = Region(region_id, spec.name, spec.w, spec.h,
                  anchor_id=anchor_id, entry_id=entry.id,
                  opened_day=int(day),
                  rings=_rings(placed, entry) if region_id == "hollow" else [])
    galaxy.regions.append(made)
    return made


def open_buyers(galaxy) -> list:
    """Give the Verge's condensate buyers a line for it. Returns who got one.

    The Concordat's and the Dry Choir's markets, short of it and staying so
    (`data/regions.CONDENSATE_BUYERS`), each drawn from a seed of its own so
    the Verge's own streams are untouched. Idempotent: a market that already
    trades it is left alone, so a second call is nothing.
    """
    out = []
    for system in verge(galaxy):
        port, market = system.port, system.market
        if port is None or market is None or data.CONDENSATE in market.stock:
            continue
        short = data.CONDENSATE_BUYERS.get(port.faction)
        if short is None:
            continue
        rng = RNG(f"{galaxy.seed}:condensate:{system.id}")
        add_line(market, data.CONDENSATE, short, port.level, rng)
        out.append(system.id)
    return out
