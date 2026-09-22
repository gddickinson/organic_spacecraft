"""Rooms round a loop: the plan a can, a ring, a tower floor and a dome share.

Most things people build to live in are round a middle. A quay's can is a
drum stood on end with a lift up its core; a hub's habitation ring is the
same thing a hundred times the size, with the core a hub the spokes run in
from; a tower floor is a can with square corners; a dome is a can whose
floor is the ground. `loop` draws one deck of any of them:

- a **core** at the middle — the lift shaft, or the hub the spokes meet at;
- a **ring corridor** round it, two squares wide;
- **spokes** from the core out to the ring, and **arms** from the ring out
  through the skin to whatever is moored there;
- rooms in the two **bands** either side of the ring corridor, packed by
  angle round the loop in the order the program gives them, each with its
  door on the ring, and never across a spoke.

The rooms are sized to fill their band, in proportion to what each asked
for: a quiet deck has roomier rooms rather than an empty quarter.
"""

from __future__ import annotations

import math

from . import afoot_blocks as blocks

#: The width of a ring corridor and a spoke.
CORRIDOR = 2
#: A band narrower than this has no rooms in it: it is structure.
THINNEST_BAND = 3
#: The most a room grows past what it asked for, to fill a quiet band.
ROOMIEST = 3.0
#: A can no deeper than this from core to skin is a pie: wedge rooms off a
#: central lobby, no ring corridor.
PIE = 9
#: How deep a band of rooms is inside the outermost one.
BAND = 5


def dist(x: float, y: float, cx: float, cy: float, square: bool) -> float:
    if square:
        return max(abs(x - cx), abs(y - cy))
    return math.hypot(x - cx, y - cy)


def band(cx, cy, r0: float, r1: float, square: bool = False) -> list:
    """The cells from r0 (inclusive) to r1 (exclusive) of the middle."""
    n = int(r1) + 2
    return [(x, y) for y in range(int(cy) - n, int(cy) + n + 1)
            for x in range(int(cx) - n, int(cx) + n + 1)
            if r0 <= dist(x, y, cx, cy, square) < r1]


def angle_of(x, y, cx, cy, start: float = 0.0) -> float:
    return (math.atan2(y - cy, x - cx) - start) % math.tau


class Loop:
    """One round deck's geometry, as `loop` drew it."""

    def __init__(self, cx, cy, radius, core, ring, square):
        self.cx, self.cy = cx, cy
        self.radius, self.core, self.ring = radius, core, ring
        self.square = square

    def at(self, a: float, r: float) -> tuple:
        """The square at angle `a` and distance `r` from the middle."""
        return (round(self.cx + r * math.cos(a)),
                round(self.cy + r * math.sin(a)))

    def edge(self, a: float) -> tuple:
        """The first square outside the skin at angle `a`."""
        r = self.radius
        while dist(*self.at(a, r), self.cx, self.cy, self.square) \
                < self.radius:
            r += 0.5
        return self.at(a, r)


def layout(radius: float, core: float, rim=None) -> tuple:
    """(ring corridors, bands of rooms): each corridor as the radius it
    starts at, each band as (from, to, the radius of its door, outermost?).

    - a **pie** — a small can: no ring corridor, wedge rooms from the core
      lobby out to the skin, every door on the lobby;
    - a **can** — from the skin inward, a band of rooms, a ring corridor,
      a band back to back with the next, another corridor, and so on to the
      core, so no room is deeper than a room should be;
    - a **rim** — a habitation ring: only the outer `rim` squares are built,
      rooms either side of one corridor, and the spokes cross open space
      from the hub to reach it.
    """
    if rim is None and radius - core <= PIE:
        return [], [(core + 1, radius, core, True)]
    floor_r = core + 1 if rim is None else max(core + 1, radius - rim)
    corridors, out = [], []
    r, depth = radius, min(6.5, max(5.0, (radius - core - CORRIDOR) * 0.55))
    while r - depth - CORRIDOR >= floor_r:
        ring = r - depth - CORRIDOR
        door = ring + CORRIDOR / 2
        corridors.append(ring)
        out.append((r - depth, r, door, not out))
        inner = max(floor_r, ring - BAND)
        if ring - inner >= THINNEST_BAND:
            out.append((inner, ring, door, False))
        r, depth = inner, BAND
        if rim is not None:
            break
    if rim is None and corridors and r - floor_r >= THINNEST_BAND:
        out.append((floor_r, r, core, False))   # doors on the core lobby
    return corridors, out


def bands(cx, cy, radius, core, square=False, rim=None) -> list:
    """Every band's cells, with its door radius and whether it is the
    outermost, for a loop of this size."""
    _rings, rows = layout(radius, core, rim)
    return [(band(cx, cy, r0, r1, square), door, outer)
            for r0, r1, door, outer in rows]


def capacity(radius: float, core: float, square: bool = False,
             rim=None) -> int:
    """Squares of room floor a loop of this size has, roughly: its bands,
    less the walls."""
    return int(0.6 * sum(len(cells) for cells, _d, _o in
                         bands(0, 0, radius, core, square, rim)))


def fit_radius(area: int, core: float, least: float, most: float,
               square: bool = False, rim=None) -> float:
    """The smallest radius whose bands hold `area`, within limits."""
    r = least
    while r < most and capacity(r, core, square, rim) < area:
        r += 1
    return r


def loop(sheet, cx, cy, radius: float, wants: list, *, core: float = 2.5,
         spokes: int = 4, arms=(), square: bool = False, start: float = 0.0,
         floor: str = "hall", shell: bool = True, fill: bool = True,
         rim=None):
    """Draw one round deck. Returns (Loop, what would not fit).

    `arms` are angles at which a corridor runs out through the skin; the
    caller draws what is on the end of each. `floor` is what the corridors
    are: "hall" aboard, "ground" under a dome. `shell` paints the whole
    disc as structure first, so what no room takes is structure; without
    it, it is open space (a ring's middle) or open ground (a dome's).
    """
    rings, _rows = layout(radius, core, rim)
    geo = Loop(cx, cy, radius, core, rings[0] if rings else core, square)
    if shell:
        sheet.paint(band(cx, cy, 0, radius + 0.01, square),
                    sheet.region("solid"))
    way = sheet.region(floor)
    sheet.paint(band(cx, cy, 0, core, square), way)
    cuts = [start + math.tau * k / spokes for k in range(spokes)] \
        if rings else []
    for ring in rings:
        sheet.paint(band(cx, cy, ring, ring + CORRIDOR, square), way)
    for a in cuts:
        sheet.paint(_ray(geo, a, 0, geo.ring + 1), way)
    for a in arms:
        sheet.paint(_ray(geo, a, geo.ring, radius + 1.5), way)
    rows = bands(cx, cy, radius, core, square, rim)
    # Each band takes its share of the program by its size, the outermost
    # — the one with the windows, where the arm comes in — first.
    total_cells = sum(len(cells) for cells, _d, _o in rows) or 1
    total = sum(w.area for w in wants)
    queue = sorted(wants, key=lambda w: -w.zone)
    left, seen, given = [], 0, 0.0
    for cells, door, outer in rows:
        seen += len(cells)
        share = list(left)
        while queue and given + queue[0].area / 2 <= total * seen / \
                total_cells:
            given += queue[0].area
            share.append(queue.pop(0))
        left = pack(sheet, geo, cells, share, list(arms) if outer else cuts,
                    door, start, fill)
    return geo, left + queue


def _ray(geo, a: float, r0: float, r1: float) -> list:
    x0, y0 = geo.at(a, r0)
    x1, y1 = geo.at(a, r1)
    return blocks.line(x0, y0, x1, y1, CORRIDOR)


def pack(sheet, geo, cells: list, wants: list, cuts, door_r: float,
         start: float = 0.0, fill: bool = True) -> list:
    """Rooms round a band in program order, sized to fill it, never across
    a spoke or an arm. Returns what would not fit."""
    free = [c for c in cells if not _taken(sheet, c)]
    if not free or not wants:
        return list(wants)
    # Angles are measured from the first cut, so no run wraps past zero.
    base = min(cuts) if cuts else start
    arcs = _arcs(free, geo, base, sorted((a - base) % math.tau
                                         for a in cuts))
    queue = sorted(wants, key=lambda w: -w.zone)
    # A room is at least three squares across the band, or it is all wall.
    depth = max(1.0, max(dist(*c, geo.cx, geo.cy, geo.square) for c in free)
                - min(dist(*c, geo.cx, geo.cy, geo.square) for c in free))

    def size(w) -> int:
        return int(max(w.area, 3.5 * (depth + 1)))
    plans, left = [], []
    for arc in arcs:
        room, got = len(arc), []
        while queue and sum(size(w) for w in got) + size(queue[0]) <= room:
            got.append(queue.pop(0))
        plans.append((arc, got))
    left = queue
    for arc, got in plans:
        if not got:
            continue
        asked = sum(size(w) for w in got)
        scale = min(ROOMIEST, len(arc) / asked) if fill else 1.0
        # The last room takes up the rounding, unless the band is so quiet
        # every room is already as big as a room gets.
        rest = fill and scale < ROOMIEST
        # Cut at cumulative boundaries, so rounding never starves the last
        # room of an arc down to a sliver of wall.
        cum = 0
        for n, w in enumerate(got):
            start = int(round(cum * scale))
            cum += size(w)
            end = len(arc) if n == len(got) - 1 and rest else \
                int(round(cum * scale))
            part = arc[start:end]
            if not part:
                left.append(w)
                continue
            mid = part[len(part) // 2]
            a = math.atan2(mid[1] - geo.cy, mid[0] - geo.cx)
            rid = sheet.region("room", w, door_at=geo.at(a, door_r))
            sheet.paint(part, rid)
    return left


def _taken(sheet, cell) -> bool:
    """A cell some corridor or room has already claimed. What a deck was
    first filled with — the shell's structure, a dome's open ground — does
    not count: rooms are carved out of it."""
    if not sheet.claimed(*cell):
        return False
    rid = sheet.grid[cell[1]][cell[0]]
    return sheet.regions[rid].kind != "solid" and rid != sheet.base


def _arcs(cells: list, geo, base: float, cuts: list) -> list:
    """Split a band's free cells into the runs between the cuts, each in
    angle order so a room is a slice of it. `cuts` are measured from
    `base`, and the first is zero."""
    def a(c):
        return angle_of(*c, geo.cx, geo.cy, base)
    order = sorted(cells, key=lambda c: (a(c), dist(*c, geo.cx, geo.cy,
                                                     geo.square)))
    if not cuts:
        return [order]
    runs: list = [[] for _ in cuts]
    for c in order:
        ang = a(c)
        runs[max(i for i, cut in enumerate(cuts) if cut <= ang)].append(c)
    return [r for r in runs if r]
