"""Where a landing party is set down, and what it gets home with.

Split out of `sim/expedition.py` at 499 lines, along its two ends: laying out
a landing zone before anybody walks it, and the accounting done after they
stop — what can be carried, what stranding costs, and the forecast of both.
The walk itself (moving, working a feature, weather, the ending) stays in
`expedition`, which re-exports every name here, so `exp_sim.generate` and
`exp_sim.haul_kept` still answer where they always did.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core import ids
from ..data.expedition import BASE_SUPPLY, PARTY_CAPACITY
from . import weather as weather_sim

if TYPE_CHECKING:
    from .expedition import Expedition


# ── generation ─────────────────────────────────────────────────────────────

_TERRAIN_BY_BIOME = {
    "barren": ("plain", "ridge", "scarp", "dunes"),
    "regolith": ("plain", "ridge", "dunes", "basin"),
    "cryo": ("shelf", "crevasse", "plain", "ridge"),
    "subsurface": ("shelf", "crevasse", "vent", "basin"),
    "microbial": ("basin", "plain", "vent", "forest"),
    "verdant": ("forest", "basin", "ridge", "plain"),
    "sulfuric": ("vent", "scarp", "plain", "crevasse"),
    "aerial": ("basin", "dunes", "plain", "ridge"),
}

_FEATURE_BY_BIOME = {
    "barren": ("seam", "wreck", "cache", "ruin"),
    "regolith": ("seam", "ruin", "cache", "wreck"),
    "cryo": ("shaft", "wreck", "cache", "monolith"),
    "subsurface": ("vent_field", "shaft", "monolith", "nest"),
    "microbial": ("nest", "vent_field", "garden", "seam"),
    "verdant": ("garden", "nest", "ruin", "monolith"),
    "sulfuric": ("vent_field", "seam", "wreck", "bloomscar"),
    "aerial": ("nest", "monolith", "wreck", "garden"),
}


def _around(game, body, at) -> tuple:
    """The ground at a surface cell and the eight around it, as the mix a
    landing zone is laid out from. The middle counts three times, so a zone
    reads as the cell that was picked rather than as its neighbourhood.
    """
    from . import worldmap
    world = worldmap.of(game, body)
    x, y = int(at[0]), int(at[1])
    here = world.at(x, y)
    out = [here.terrain] * 3
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                out.append(world.at(x + dx, y + dy).terrain)
    # Standing water is not ground a party walks; the shore is.
    return tuple(t for t in out if t) or (here.terrain,)


def generate(rng, system, body, officers: list[int],
             supply: int = BASE_SUPPLY, at=None, game=None) -> Expedition:
    """Lay out a landing zone. Denser features further from the lander.

    With `at` — a cell of the body's own surface (`sim/worldmap`) — the
    ground is **that** cell's and its neighbours', so a party that picked a
    dune sea off the map walks a dune sea. Without it the mix is the
    biome's, which is what every landing before there was a map got.
    """
    # Imported here, not at the top: `expedition` re-exports this module's
    # names, so a module-level import either way round is a cycle.
    from .expedition import H, LANDER, W, Expedition, Tile, _reveal, say
    kinds = _TERRAIN_BY_BIOME.get(body.biome, ("plain", "ridge", "scarp"))
    if at is not None and game is not None:
        kinds = _around(game, body, at) or kinds
    feats = list(_FEATURE_BY_BIOME.get(body.biome, ("seam", "wreck", "ruin")))
    if body.relic and body.relic_found:
        feats = ["ruin", "monolith"] + feats
    if body.anomaly and body.anomaly.found:
        feats = ["wreck", "cache"] + feats

    tiles: list[Tile] = []
    for y in range(H):
        for x in range(W):
            t = Tile(x, y, rng.pick(kinds))
            # Nothing interesting on the pad itself.
            if (x, y) != LANDER:
                dist = abs(x - LANDER[0]) + abs(y - LANDER[1])
                if rng.chance(min(0.55, 0.10 + dist * 0.07)):
                    t.feature = rng.pick(feats)
            tiles.append(t)

    exp = Expedition(id=ids.next_id("expedition"), system_id=system.id, body_id=body.id,
                     body_name=body.name, tiles=tiles,
                     officers=list(officers), supply=supply,
                     biome=body.biome or "")
    weather_sim.roll(exp, rng, exp.biome)
    exp.tile(*LANDER).seen = True
    exp.tile(*LANDER).visited = True
    _reveal(exp)
    say(exp, f"The lander is down on {body.name}. "
             f"{exp.supply} days of supply aboard.", "good")
    return exp


#: What a stranded party gets home with, as a share of what they could carry.
STRANDED_SHARE = 0.4


def haul_kept(exp: Expedition) -> dict[str, float]:
    """What actually comes home: what they can carry, less what stranding costs.

    The order matters and used to be the other way round. Stranding returned
    40% of the pile **without applying the carrying limit at all**, so a party
    that stayed out until the supplies ran out brought home 40% of everything
    they had ever picked up, while a party that walked back to the lander was
    capped at what four people can lift. Measured: 500 t collected came home
    as 200 t stranded against 60 t returned, and a driver that never turned
    back kept 933 t against 41 t for one that always did.

    So the penalty was a reward, by a factor of twenty-three, and the way to
    play the ground was to strand the party on purpose — which is also the
    opposite of what the ending says happens, since everything not on their
    backs is supposed to stay where it fell.
    """
    kept = dict(exp.haul)
    if exp.carried > PARTY_CAPACITY:
        scale = PARTY_CAPACITY / exp.carried
        kept = {k: v * scale for k, v in kept.items()}
    if exp.outcome == "stranded":
        kept = {k: v * STRANDED_SHARE for k, v in kept.items()}
    return kept


def landing_forecast(exp: Expedition) -> dict:
    """What comes up, what stays, and what stranding would cost — now.

    The screen showed "Carrying 140 / 60" in amber and left the captain to
    infer that eighty tonnes would simply cease to exist, and said nothing at
    all about the further share stranding takes. Both numbers come from
    `haul_kept`, so the forecast and the outcome cannot drift apart.
    """
    was = exp.outcome
    try:
        exp.outcome = "returned"
        kept = sum(haul_kept(exp).values())
        exp.outcome = "stranded"
        stranded = sum(haul_kept(exp).values())
    finally:
        exp.outcome = was
    return {"carried": exp.carried, "kept": kept, "stranded": stranded,
            "left": max(0.0, exp.carried - kept)}


def study_kept(exp: Expedition) -> float:
    total = sum(exp.study.values())
    return total * (0.5 if exp.outcome == "stranded" else 1.0)
