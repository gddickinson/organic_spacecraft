"""What a world has on it, at a longitude as well as a latitude.

`data/worlds3d.py` colours a sphere by **latitude**, and says so: caps for
nothing, bands for a giant, a wave across the middle for a mottled surface.
That buys a great deal cheaply, and it has one consequence nobody had looked
at — *a world painted by latitude alone is the same picture from every side*.

Measured, which is how this cycle started. Berthing happens in orbit, so the
world is the backdrop to the entire docking activity, and at 200 km over a
3,000 km world the frame is **a flat wash of one colour with three banding arcs
in it**. Nothing to judge motion against, nothing to recognise a place by, and
the same wash over every world of that kind in the sector.

So: features. Each is a cap of surface centred on a point — a mare, a crater
field, a continent, a storm — with a latitude, a **longitude**, an angular
radius and a colour. `ui/surface.py` projects them; this file decides what each
kind of world wears, and hands out a set that is stable for a given body, so a
world looks like itself every time you come back to it.

The tables are deliberately coarse. This is a game that paints its worlds with
`QPainter` and no textures, and a dozen soft ellipses is the whole budget: it
is the difference between a marble and a place, and going further would be a
texture pipeline, which is the dependency `ui/render3d.py` exists to avoid.
"""

from __future__ import annotations

import math

#: One recipe per kind of world: how many features, how big they run as a share
#: of a hemisphere, and what colour they are against the ground.
#:
#: `spread` is the angular radius in radians, low to high. 0.35 rad is about
#: 20°, which is a fifth of the way from the sub-camera point to the limb — big
#: enough to read at a glance and small enough that a dozen of them are a
#: surface rather than a repaint.
#:
#: `tone` is a straight colour rather than a blend of the ground, because a
#: mare on a moon is not a darker moon: it is basalt, and it reads as basalt.
#: The ground colours in `worlds3d.WORLD_PAINTS` keep the *kinds* apart; these
#: keep the individuals apart.
RECIPES = {
    "rocky":    {"count": 11, "spread": (0.16, 0.40), "tone": "#8a5230",
                 "second": "#c99a67", "alpha": 150},
    "ocean":    {"count": 8,  "spread": (0.18, 0.46), "tone": "#3f7a4a",
                 "second": "#b8a879", "alpha": 190},
    "ice":      {"count": 9,  "spread": (0.12, 0.30), "tone": "#8fbcd4",
                 "second": "#dff2fb", "alpha": 130},
    "moon":     {"count": 12, "spread": (0.14, 0.34), "tone": "#43434c",
                 "second": "#7e7e88", "alpha": 165},
    "asteroid": {"count": 10, "spread": (0.16, 0.38), "tone": "#3a3028",
                 "second": "#8a785c", "alpha": 150},
    "comet":    {"count": 7,  "spread": (0.12, 0.28), "tone": "#63b6bd",
                 "second": "#e8ffff", "alpha": 120},
    # A giant's weather runs *along* its bands, so its features are wide and
    # flat rather than round — see `ui/surface.py`, which stretches a storm in
    # longitude by `BAND_STRETCH`.
    # A giant is drawn banded by `worlds3d.band_paint`, and the bands *are* its
    # weather. Blotch texture on top of them fought the bands and read as a
    # fingerprint — the picture said whirl where the palette said belt. So a
    # giant gets a few great storms, sheared along the band by `BAND_STRETCH`,
    # and no ground lattice at all: see `detail_near`, which returns nothing for
    # a world with no ground.
    "gas":      {"count": 5,  "spread": (0.09, 0.19), "tone": "#9c7238",
                 "second": "#fbf0cd", "alpha": 120},
}

#: What a world nobody wrote a recipe for wears. Kept deliberately plain.
DEFAULT = {"count": 8, "spread": (0.15, 0.34), "tone": "#5f6f68",
           "second": "#9db3aa", "alpha": 140}

#: How much wider than tall a gas giant's storms run. Weather on a banded world
#: is sheared out along the band by the wind that makes the band.
BAND_STRETCH = 2.6

#: Features are kept off the poles, where the latitude caps already do the
#: work and where the projection of a cap that contains the pole is not an
#: ellipse. In radians of latitude from the equator.
POLE_KEEPOUT = 1.05


def _seeded(name: str) -> int:
    """A stable integer for a body's name.

    `hash()` is salted per process in Python 3, so a world would have worn a
    different face every time the game was started — which is the one thing a
    place must not do.
    """
    value = 2166136261
    for ch in name or "unnamed":
        value = ((value ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return value


def _stream(seed: int):
    """A small deterministic float source. No `random`, no global state."""
    state = seed or 1

    def nxt() -> float:
        nonlocal state
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        return state / 0x7FFFFFFF
    return nxt


def features_for(kind: str, name: str) -> tuple:
    """The surface of one body: `(lat, lon, radius, colour, alpha)` per feature.

    `lat` runs -π/2 to π/2 and `lon` 0 to 2π, so a feature has a place on the
    globe rather than a place on the picture — which is the whole point, and
    what makes the far side of a world a different view of it.
    """
    recipe = RECIPES.get(kind) or DEFAULT
    nxt = _stream(_seeded(name))
    low, high = recipe["spread"]
    out = []
    for i in range(recipe["count"]):
        lat = (nxt() - 0.5) * POLE_KEEPOUT * 2.0
        lon = nxt() * math.tau
        size = low + (high - low) * nxt()
        # Two tones, so a surface has both its darker and its lighter ground
        # rather than one colour of blotch repeated.
        colour = recipe["tone"] if nxt() < 0.62 else recipe["second"]
        out.append((lat, lon, size, colour, recipe["alpha"]))
    return tuple(out)


def stretch_for(kind: str) -> float:
    """How far a feature is sheared along its band. 1.0 for a solid world."""
    return BAND_STRETCH if kind == "gas" else 1.0


# ── detail, at the scale you are looking from ──────────────────────────────
#
# The features above are the size of a continent, which is the right size to
# see a globe by and no use at all from low orbit. At 200 km over a 3,000 km
# world the frame holds about twenty degrees of arc: a continent is bigger than
# the picture, so the picture is one flat colour again — which is precisely the
# reading this cycle started from, and shipping only the coarse features would
# have left the docking backdrop exactly as blank as it was found.
#
# Detail has to come from a **lattice fixed to the ground**, not from a list.
# A list fine enough to hold low orbit would be tens of thousands of features
# for the handful ever on screen. A lattice is generated per cell from the
# cell's own index, so it costs the cells in view and no more — and, far more
# importantly, the same patch of ground gives the same answer every time it is
# looked at. Anything seeded from where the *camera* is would boil as the hull
# moved, which is worse than a flat wash: a flat wash is at least still.

#: How many cells of detail to span the frame with. Judged by looking: six was
#: the first try and read as soap bubbles — a handful of circles each a sixth of
#: the picture. Twelve is ground. Past about twenty the marks are smaller than
#: the contrast between them can carry and it goes back to being a flat wash,
#: the expensive way.
CELLS_ACROSS = 12.0

#: A cell's feature covers this share of it, at most. Under 1.0 so the ground
#: shows between them rather than the surface becoming a tiling.
CELL_FILL = 0.62

#: The coarsest and finest a detail cell is ever allowed to be, in radians.
#: The floor stops the lattice subdividing for ever as a hull settles onto a
#: berth; the ceiling stops detail competing with the continents at globe range.
CELL_MIN, CELL_MAX = 0.0016, 0.24

#: Worlds with no surface to texture. A gas giant has no ground: what it has is
#: banded cloud, which `worlds3d.band_paint` already draws, and a lattice of
#: blotches over the top of it reads as a fingerprint rather than as weather.
NO_GROUND = frozenset({"gas"})

#: How many cells out from the one underfoot the lattice is ever walked. The
#: cell size is quantised to powers of two, so `reach / step` swings by a factor
#: of two either side of `CELLS_ACROSS` and the cell count by a factor of four —
#: which reached 532 features in a frame before this bound went on. Six rings is
#: a 13x13 patch, which covers the frame at every range the quantisation lands.
MAX_RING = 6

#: How much dimmer detail is than the named features. It is ground texture, not
#: geography, and at the alpha of a mare it reads as a rash.
DETAIL_ALPHA = 0.42


def _hash3(a: int, b: int, c: int) -> int:
    """A stable hash of three integers — the cell's own name."""
    value = 2166136261 ^ (a & 0xFFFF) ^ ((b & 0xFFFF) << 8) ^ ((c & 0xFF) << 20)
    value = (value * 16777619) & 0xFFFFFFFF
    value ^= value >> 15
    return (value * 2246822519) & 0xFFFFFFFF


def cell_angle(span: float) -> float:
    """How big a detail cell should be to put `CELLS_ACROSS` in the frame.

    Quantised to powers of two so the lattice halves rather than sliding: a
    cell size that varied smoothly with range would re-seed every feature on
    every frame, and the ground would crawl.
    """
    want = max(1e-6, span / CELLS_ACROSS)
    level = math.floor(math.log2(want / CELL_MAX))
    return max(CELL_MIN, min(CELL_MAX, CELL_MAX * (2.0 ** level)))


def detail_near(kind: str, name: str, lat0: float, lon0: float,
                span: float) -> tuple:
    """Detail features on the ground within `span` radians of (lat0, lon0).

    Returned in the same shape as `features_for`, so one drawing path serves
    both. Bounded by construction: the lattice is sized to the view, so the
    count is about `CELLS_ACROSS²` however close the hull gets.
    """
    if kind in NO_GROUND:
        return ()
    recipe = RECIPES.get(kind) or DEFAULT
    step = cell_angle(span)
    level = int(round(math.log2(CELL_MAX / step)))
    seed = _seeded(name)
    reach = span * 0.62
    out = []
    # **Snapped to the globe, not to the camera.** The first version walked out
    # from `lat0` in steps — `lat = lat0 + dr * step` — and hashed the cell by
    # `round(lat / step)`. So the *name* of a cell was anchored to the world and
    # its *position* was anchored to the eye: slide the camera a tenth of a cell
    # and every blotch slid with it, then changed identity as it crossed a
    # boundary. That is the ground boiling, which is the one thing this lattice
    # exists to prevent, and it went in under a comment claiming it could not
    # happen. `tests/test_surfaces.py` found it by moving the camera and asking
    # the cells they share to agree.
    home_row = int(round(lat0 / step))
    rows = min(MAX_RING, int(reach / step) + 1)
    for dr in range(-rows, rows + 1):
        row = home_row + dr
        lat = row * step
        if abs(lat) > math.pi / 2 - 1e-3:
            continue
        # Longitude cells are widened by the cosine so a cell stays square on
        # the ground rather than pinching to nothing toward the poles. Taken
        # from the *snapped* latitude, so a row's cells are the same width
        # whichever cell of it the camera is over.
        wide = step / max(0.12, math.cos(lat))
        cols = min(MAX_RING, int(reach / wide) + 1)
        home_col = int(round(lon0 / wide))
        for dc in range(-cols, cols + 1):
            col = home_col + dc
            lon = col * wide
            h = _hash3(row, col, level + seed)
            if (h & 0xFF) < 96:              # not every cell carries one
                continue
            jitter_a = ((h >> 8) & 0xFF) / 255.0 - 0.5
            jitter_b = ((h >> 16) & 0xFF) / 255.0 - 0.5
                    # Sizes spread wide on purpose: a lattice of same-sized marks
            # reads as a pattern, and the eye finds a pattern faster than it
            # finds a texture.
            size = step * CELL_FILL * (0.35 + 0.95 * (((h >> 24) & 0xFF) / 255.0))
            tone = recipe["tone"] if (h & 0x100) else recipe["second"]
            out.append((lat + jitter_a * step * 0.7,
                        lon + jitter_b * wide * 0.7,
                        size, tone,
                        max(24, int(recipe["alpha"] * DETAIL_ALPHA))))
    return tuple(out)
