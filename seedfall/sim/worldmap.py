"""A world as a map you can look at: terrain, at a longitude and a latitude.

The game has had two scales of ground and nothing between them. A body is a
line on a survey — kind, biome, gravity, a resource table — and a *landing
zone* is a 7×7 grid of terrain a party walks one tile at a time
(`sim/expedition.py`). There was no answer to "what is this world like",
only "what is this corner of it like", and no way to choose where to set
down.

This is the scale between: **one map per body, derived and never stored**,
seeded off the sector the way every other derived thing here is
(`RNG(f"{seed}:world:{system}:{body}")`, the idiom `sim/profile` and
`sim/afoot_plans` already use). Ask for it twice and it is the same map;
nothing is saved, and a save from before this module reads exactly the same.

How a cell gets its terrain, in the order the answers arrive:

- **Height** is a seeded value-noise field (`_fbm`), warped so a world has a
  few broad masses rather than static.
- **Water** is the profile's own hydrographics digit (`sim/profile`), read
  as the share of the surface that is under something — so a world the
  Traveller profile calls 70% water has 70% of its cells below sea level,
  and the same world reads the same on the survey screen and here.
- **Wet** is a second field, damped at the belt of a hot world and raised
  near water, which is what puts standing growth by a coast and dunes in
  the middle of a continent.
- **Cold** is latitude against the body's own `temp_k`, which is what makes
  ice shelves at the poles of a world that is temperate at its equator.

The terrain vocabulary is the nine `data/expedition.TERRAIN` kinds and not a
second one, deliberately: a cell of this map *is* where a landing zone
happens, so the ground a party walks should be the ground the map showed
them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.rng import RNG
from ..data.expedition import TERRAIN

#: The map, in cells. Wide enough to read as a world and small enough to
#: derive on demand: 24 × 14 is 336 cells, about a millisecond.
WIDE, HIGH = 24, 14

#: How many octaves of noise a field is, and how fast they fall away.
OCTAVES, GAIN = 4, 0.55

#: Below this share of the height range a cell is under water, if the world
#: has any. Set from the profile's hydrographics rather than fixed.
#: `data/uwp.HYDROGRAPHICS` is in tenths, so 7 means seven tenths.
TENTHS = 10.0

#: What counts as high ground and as a wall, as shares of the range above
#: sea level. A scarp is the edge of the highest ground there is.
UPLAND, WALL = 0.62, 0.86

#: How cold the poles are against the equator, as a share of the body's own
#: surface temperature. A world at 280 K at its belt is at 196 K at its cap.
POLE_CHILL = 0.70

#: Below this, in kelvin, standing water is ice and the map says so.
FREEZING = 260.0


@dataclass(frozen=True)
class Cell:
    """One cell of a world's surface."""

    x: int
    y: int
    terrain: str
    #: 0 at the deepest, 1 at the highest.
    height: float
    #: 0 bone dry, 1 saturated.
    wet: float
    #: True where the cell is below the world's sea level.
    water: bool

    @property
    def lat(self) -> float:
        """Degrees, +90 at the north cap."""
        return 90.0 - (self.y + 0.5) * (180.0 / HIGH)

    @property
    def lon(self) -> float:
        """Degrees east of the prime meridian this map calls zero."""
        return (self.x + 0.5) * (360.0 / WIDE) - 180.0


@dataclass(frozen=True)
class World:
    """A body's whole surface, in cells."""

    body_id: str
    name: str
    cells: tuple
    #: The share of the surface under water, as it came out.
    water: float
    #: What the profile said it should be, in tenths.
    hydro: int
    mean_k: int

    def at(self, x: int, y: int) -> Cell:
        """The cell at `x`, `y`. East–west wraps; north–south does not."""
        return self.cells[max(0, min(HIGH - 1, y)) * WIDE + (x % WIDE)]

    def rows(self) -> list:
        return [self.cells[y * WIDE:(y + 1) * WIDE] for y in range(HIGH)]

    def count(self, terrain: str) -> int:
        return sum(1 for c in self.cells if c.terrain == terrain)


# ── the fields ─────────────────────────────────────────────────────────────

def _lattice(rng_seed: str, size: int) -> list:
    """A grid of random values the noise is interpolated between."""
    rng = RNG(rng_seed)
    return [rng.float(0.0, 1.0) for _n in range(size * size)]


def _sample(grid: list, size: int, u: float, v: float) -> float:
    """Smooth value noise at (u, v) in [0, 1), wrapping in u."""
    fx, fy = u * size, v * size
    x0, y0 = int(math.floor(fx)) % size, max(0, min(size - 1,
                                                    int(math.floor(fy))))
    x1, y1 = (x0 + 1) % size, min(size - 1, y0 + 1)
    tx, ty = fx - math.floor(fx), fy - math.floor(fy)
    # Smoothstep, so the field has no creases along the lattice.
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    a = grid[y0 * size + x0] * (1 - tx) + grid[y0 * size + x1] * tx
    b = grid[y1 * size + x0] * (1 - tx) + grid[y1 * size + x1] * tx
    return a * (1 - ty) + b * ty


def _fbm(seed: str, u: float, v: float) -> float:
    """Fractal noise in [0, 1]: a few octaves of `_sample`, halving."""
    total = weight = 0.0
    size, amp = 3, 1.0
    for octave in range(OCTAVES):
        grid = _grid(f"{seed}:{octave}", size)
        total += _sample(grid, size, u, v) * amp
        weight += amp
        size, amp = size * 2, amp * GAIN
    return total / max(1e-9, weight)


#: Lattices are pure functions of their seed, so they are built once and
#: kept. A sector has a few dozen worlds and each wants four small grids.
_GRIDS: dict = {}


def _grid(seed: str, size: int) -> list:
    got = _GRIDS.get((seed, size))
    if got is None:
        got = _lattice(seed, size)
        _GRIDS[(seed, size)] = got
    return got


# ── the map ────────────────────────────────────────────────────────────────

#: Built maps, by the seed they were derived from. Nothing here is state: a
#: world is a pure function of the sector and the body, and this only saves
#: deriving the same one for every repaint.
_MADE: dict = {}


def of(game, body) -> World:
    """This body's surface. The one door; cheap to call twice."""
    key = (getattr(game, "seed", "verge"), getattr(game.system, "id", 0),
           getattr(body, "id", "?"))
    got = _MADE.get(key)
    if got is None:
        got = _build(game, body, ":".join(str(k) for k in key))
        _MADE[key] = got
    return got


def _build(game, body, seed: str) -> World:
    from . import profile as profile_sim
    got = profile_sim.profile(game, game.system, body)
    hydro = int(getattr(got, "hydrographics", 0) or 0)
    mean_k = int(getattr(body, "temp_k", 250) or 250)

    heights = []
    for y in range(HIGH):
        for x in range(WIDE):
            u, v = (x + 0.5) / WIDE, (y + 0.5) / HIGH
            # Two fields, the second warping the first, so the masses are
            # lobed rather than round.
            warp = _fbm(f"{seed}:warp", u, v) - 0.5
            heights.append(_fbm(f"{seed}:height", u + warp * 0.12,
                                v + warp * 0.08))
    low, high = min(heights), max(heights)
    span = max(1e-9, high - low)
    heights = [(h - low) / span for h in heights]

    # Sea level: the share the profile says is under water.
    share = max(0.0, min(1.0, hydro / TENTHS))
    ranked = sorted(heights)
    sea = ranked[min(len(ranked) - 1, int(share * len(ranked)))] if share \
        else -1.0

    cells = []
    for y in range(HIGH):
        for x in range(WIDE):
            index = y * WIDE + x
            height = heights[index]
            u, v = (x + 0.5) / WIDE, (y + 0.5) / HIGH
            lat = abs(90.0 - (y + 0.5) * (180.0 / HIGH)) / 90.0
            wet = _fbm(f"{seed}:wet", u, v)
            # Wetter near water, drier deep inside a landmass, and a hot
            # belt is drier than its own latitude suggests.
            wet = min(1.0, wet * (0.6 + 0.8 * share)
                      + max(0.0, 0.35 - abs(height - sea)) * (1.0 if share
                                                              else 0.0))
            here_k = mean_k * (1.0 - (1.0 - POLE_CHILL) * lat * lat)
            cells.append(Cell(x=x, y=y,
                              terrain=_terrain(body, height, sea, wet,
                                               here_k, share),
                              height=round(height, 3), wet=round(wet, 3),
                              water=height < sea))
    made = tuple(cells)
    return World(body_id=body.id, name=body.name, cells=made,
                 water=round(sum(1 for c in made if c.water) / len(made), 3),
                 hydro=hydro, mean_k=mean_k)


def _terrain(body, height: float, sea: float, wet: float, here_k: float,
             share: float = 0.0) -> str:
    """Which of the nine this cell is.

    A Whittaker table in the shape this game already has a vocabulary for:
    height decides the broad kind, warmth and wet decide between the ones
    that share a height, and a world's own biome gets the last word where
    it is emphatic (a sulfuric world vents; an ice world is ice).
    """
    biome = getattr(body, "biome", "") or ""
    under = height < sea
    # **Cold is only ice where there is something to freeze.** A barren
    # asteroid at 114 K is not an ice shelf, it is regolith that happens to
    # be cold, and reading every cold world as ice made four fifths of the
    # sector's bodies look like the same moon.
    frozen = here_k < FREEZING and (share > 0.0
                                    or biome in ("cryo", "subsurface"))
    above = (height - max(sea, 0.0)) / max(1e-9, 1.0 - max(sea, 0.0))
    if under:
        # Standing water, or what a world this cold has instead.
        return "shelf" if frozen else "basin"
    if biome == "sulfuric" and wet > 0.55:
        return "vent"
    if frozen:
        return "crevasse" if above > UPLAND else "shelf"
    if above > WALL:
        return "scarp"
    if above > UPLAND:
        return "ridge"
    if biome in ("verdant", "microbial") and wet > 0.58:
        return "forest"
    if wet < 0.32:
        return "dunes"
    if wet > 0.70:
        return "basin"
    return "plain"


def says(game, body) -> str:
    """One line for a screen: what this world's surface is mostly like."""
    world = of(game, body)
    counts = sorted(((world.count(t), t) for t in TERRAIN), reverse=True)
    biggest = [f"{TERRAIN[t].name.lower()}" for n, t in counts[:2] if n]
    wet = (f"{world.water:.0%} of it under water — {world.hydro} tenths by "
           "the profile" if world.water else "no standing water")
    return (f"{world.name}: {', '.join(biggest)}, {wet}, "
            f"{world.mean_k} K at the belt.")
