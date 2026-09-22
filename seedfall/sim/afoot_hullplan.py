"""A hull's decks, laid out inside its own silhouette.

Each deck is a plan-view slice through the body of revolution
`data/hullforms.py` describes and `data/hulls3d.proportions` builds for this
class — the same length, beam and taper law the 3D model is made from, so a
grown hull's deck is an ellipse fatter aft than forward, a Yards hull's a
coarse box flaring into its slab bow, a xeno hull's bent off its own axis.
Inside it:

- a **keel** corridor runs bow to stern down the middle;
- the space whose place is furthest forward (a grown hull's eye, a bridge
  behind a slab) takes the **bow** from side to side; the drives take the
  **stern** the same way;
- everything else is packed along **both sides** of the keel, each room as
  near as it will go to where its program put it — a fitted part at its
  slot's own mount — and each shaped by the curve of the hull it sits in;
- on the deck you come aboard by, the **way in** is where the family's
  drawings put it: a grown hull's equatorial docking ridge, a cross passage
  with an airlock on each side; a Yards hull's side lock aft of amidships;
  a Dry Choir frame's service hatch at the stern;
- what is left between the rooms and the skin is **void space** — the
  crawlways a stowaway hides in — or solid structure;
- two **lift shafts** join the decks, on the keel fore and aft.

A Dry Choir frame is not a hull with rooms in it. It is a lattice: nodes
where its fittings are, joined by crawlways along the struts, with nothing
between them but the vacuum it was built for.
"""

from __future__ import annotations

import math

from ..data.hullforms import form_for
from ..data.hulls3d import BEND, proportions
from . import afoot_blocks as blocks
from . import afoot_latticeplan
from .afoot_gen import Painted, Want

#: How big a deck is drawn, in squares: never smaller than a pod needs, and
#: never so long it will not fit a screen.
LEAST_L, MOST_L = 13, 72
#: Of a deck's area inside the skin, how much becomes room floor.
USABLE = 0.55
MOST_DECKS = 5
#: Squares of hull length a deck needs above it before another is drawn: a
#: small hull is drawn bigger rather than sliced into five cupboards.
LENGTH_PER_DECK = 14
#: The most a room grows past its program area to fill a quiet deck.
ROOMIEST = 2.5
#: Left-over volume this big between the rooms and the skin is fitted out
#: as a spare hold; smaller, it is a crawlway of void space.
SPARE_HOLD = 40

#: Kinds that live forward, aft, or in the stern block.
FORWARD = ("bridge", "sensors", "command", "core", "cabin", "officers",
           "magazine", "weapons", "brig", "lounge", "dining", "library")
STERN = ("drive", "tanks", "works")
DECK_NAMES = {1: ("Main deck",), 2: ("Upper deck", "Lower deck"),
              3: ("Command deck", "Habitation deck", "Engineering deck"),
              4: ("Command deck", "Habitation deck", "Engineering deck",
                  "Hold deck"),
              5: ("Command deck", "Habitation deck", "Service deck",
                  "Engineering deck", "Hold deck")}


class Hull:
    """A hull's outline in squares: length, half-width at every column,
    the centreline, and which way is which."""

    def __init__(self, chassis):
        self.family = getattr(chassis, "family", "grown")
        self.form = form_for(self.family)
        build = proportions(chassis)
        mass = max(1.0, float(getattr(chassis, "mass_t", 1) or 1))
        self.L = int(max(LEAST_L, min(MOST_L, round(
            6 + 1.9 * mass ** (1 / 3) * build.length))))
        beam = self.form.beam * build.beam * {"synthetic": 1.6}.get(
            self.family, 1.0)
        self.W = int(max(7, min(34, round(self.L * beam))))
        self.bend = BEND.get(self.family, 0.0)
        self.pad = 2 + int(self.W * self.bend * 0.6)
        self.width = self.L + 4
        self.height = self.W + 2 * self.pad + 2
        self.mid = self.height / 2 - 0.5

    def grow(self) -> None:
        """A longer hull of the same build: when the program will not fit."""
        self.L = int(self.L * 1.15) + 1
        self.W = int(max(7, min(40, round(self.W * 1.1))))
        self.width = self.L + 4
        self.height = self.W + 2 * self.pad + 2
        self.mid = self.height / 2 - 0.5

    def z(self, x: int) -> float:
        """Where along the axis a column is: stern −1 at the left."""
        return -1.0 + 2.0 * (x - 2 + 0.5) / self.L

    def x_of(self, z: float) -> int:
        return int(round(2 + (z + 1.0) / 2.0 * self.L - 0.5))

    def half(self, x: int) -> float:
        z = self.z(x)
        if abs(z) >= 1.0:
            return 0.0
        taper = 1.0 - self.form.taper * z
        if self.family == "fabricated":
            body = (1.0 - abs(z) ** 6) ** (1 / 6)
        elif self.family == "hybrid":
            body = (1.0 - abs(z) ** 2.6) ** (1 / 2.6)
        else:
            body = math.sqrt(1.0 - z * z)
        return max(0.0, self.W / 2.0 * taper * body)

    def centre(self, x: int) -> float:
        if not self.bend:
            return self.mid
        z = self.z(x)
        return self.mid + self.W * self.bend * 0.45 * (z * z - 0.35)

    def inside(self, x: int, y: int) -> bool:
        h = self.half(x)
        return h >= 0.8 and abs(y - self.centre(x)) <= h

    def cells(self) -> list:
        return [(x, y) for x in range(self.width) for y in range(self.height)
                if self.inside(x, y)]

    def area(self) -> float:
        return sum(2 * self.half(x) for x in range(self.width))


def decks(rng, chassis, wants: list, style: str, air: bool = True) -> list:
    """Every deck of this hull, painted. Returns `Painted` sheets."""
    hull = Hull(chassis)
    if hull.family == "synthetic":
        count = 1 + (len(wants) > 10)
        while True:
            split = _split(wants, count)
            frames = [afoot_latticeplan.frame(hull, share, n, len(split))
                      for n, share in enumerate(split)]
            if count >= 3 or not any(f.sheet.lost() for f in frames):
                return frames
            count += 1
    need = sum(w.area for w in wants) / USABLE
    count = max(1, min(_most_decks(hull), math.ceil(need / max(1.0,
                                                               hull.area()))))
    # **Nothing is left out.** What one deck cannot hold goes on to the
    # next; what the last cannot hold is offered back to any deck with room;
    # and only then does the design grow another deck — or, past the most
    # decks a hull of its length is drawn with, grow the hull itself.
    while True:
        sheets, left = _lay(rng, hull, _split(wants, count))
        if not left:
            break
        if count < _most_decks(hull):
            count += 1
        elif hull.L < MOST_L + 24:
            hull.grow()
        else:
            break
    names = DECK_NAMES[len(sheets)]
    return [Painted(sheet, names[n], style, air=air, g=_weight(sheet))
            for n, sheet in enumerate(sheets)]


def _weight(sheet) -> float:
    """A hull is weightless, but for the deck a Habitat Girdle's spun
    berths are on."""
    from ..data.afoot_programs import GIRDLE_G
    girdled = any(getattr(r.want, "part", "") == "crew_girdle"
                  for r in sheet.regions if r.want is not None)
    return GIRDLE_G if girdled else 0.0


def _lay(rng, hull, shares: list) -> tuple:
    """Paint every deck of one split. Returns the sheets and the spaces no
    deck could take."""
    sheets, held, carry = [], [], []
    for n, share in enumerate(shares):
        sheet, rest = _deck(rng, hull, share + carry, n, len(shares))
        rest += sheet.lost()
        sheets.append(sheet)
        held.append([w for w in share + carry if w not in rest])
        carry = rest
    for n in sorted(range(len(shares)), key=lambda n: sum(
            w.area for w in held[n])):
        if not carry:
            break
        sheet, rest = _deck(rng, hull, held[n] + carry, n, len(shares))
        rest += sheet.lost()
        if len(rest) < len(carry):
            sheets[n] = sheet
            held[n] = [w for w in held[n] + carry if w not in rest]
            carry = rest
    return sheets, carry


def _most_decks(hull) -> int:
    return max(1, min(MOST_DECKS, round(hull.L / LENGTH_PER_DECK)))


def _split(wants: list, count: int) -> list:
    """Share the program between decks: command up, engineering down, the
    way in on the first. Nothing is left out; a deck can be busier."""
    if count <= 1:
        return [list(wants)]

    def band(w) -> int:
        if w.kind in ("bridge", "command", "sensors", "core", "cabin",
                      "officers", "magazine", "brig", "weapons"):
            return 0
        if w.kind in ("drive", "power", "tanks", "hold", "works", "hangar",
                      "workshop", "reclaim", "store", "utility", "farm",
                      "vault", "lab"):
            return 2
        return 1
    decks_: list = [[] for _ in range(count)]
    load = [0.0] * count
    total = sum(w.area for w in wants) or 1
    for w in sorted(wants, key=lambda w: (band(w), -w.zone)):
        pref = min(count - 1, round(band(w) * (count - 1) / 2))
        if w.kind == "airlock":
            pref = 0
        order = sorted(range(count), key=lambda d: (abs(d - pref),
                                                    load[d]))
        target = next((d for d in order if load[d] + w.area
                       <= total / count * 1.35), order[0])
        decks_[target].append(w)
        load[target] += w.area
    return [d for d in decks_ if d] or [list(wants)]


def _deck(rng, hull: Hull, wants: list, index: int, count: int):
    sheet = blocks.Sheet(hull.width, hull.height)
    body = hull.cells()
    solid = sheet.region("solid")
    sheet.paint(body, solid)
    keel_w = 1 if hull.W < 12 else 2
    cols = sorted({x for x, _y in body})
    stern_x, bow_x = cols[0], cols[-1]

    def keel_at(x: int) -> list:
        c = round(hull.centre(x))
        return [(x, c + dy) for dy in range(-(keel_w // 2),
                                            keel_w - keel_w // 2)]
    hall = sheet.region("hall")
    keel = [c for x in range(stern_x + 1, bow_x) for c in keel_at(x)
            if hull.inside(*c)]
    sheet.paint(keel, hall)
    wants = list(wants)
    # The bow takes what lives furthest forward — a grown hull's eye at the
    # very tip, its bridge behind it — and the stern its drives and tanks,
    # each room the full width of the hull where it is.
    bow = _ends(wants, lambda w: w.kind in FORWARD and w.zone >= 0.6,
                forward=True)
    stern = _ends(wants, lambda w: w.kind in STERN and w.zone <= -0.7,
                  forward=False)
    x_lo = _block(sheet, hull, body, stern, from_x=stern_x, forward=True)
    x_hi = _block(sheet, hull, body, bow, from_x=bow_x, forward=False)
    passage = _way_in(sheet, hull, hall, index, x_lo, x_hi, keel_w)
    left = _sides(sheet, hull, wants, x_lo, x_hi, passage, keel_w)
    _voids(sheet, hull, solid)
    _lifts(sheet, hull, index, count, x_lo, x_hi, keel_at)
    _furniture(sheet, hull)
    return sheet, left


def _ends(wants: list, test, forward: bool) -> list:
    """Take the rooms that belong at one end out of the program, the
    outermost first. At most three: the rest of the end goes to the sides."""
    got = sorted((w for w in wants if test(w)),
                 key=lambda w: -w.zone if forward else w.zone)[:3]
    for w in got:
        wants.remove(w)
    return got


def _block(sheet, hull, body, wants, from_x: int, forward: bool) -> int:
    """Rooms that take the full width at one end; returns the next free
    column. Only floor inside the walls counts toward a room's area: the
    skin takes a square off every column, and each room after the first
    gives its outer column to the bulkhead it shares with the one before."""
    x = from_x
    step = 1 if forward else -1
    inner = set(body)
    for n, w in enumerate(wants):
        cells, got, first = [], 0, True
        while got < w.area and 0 <= x < hull.width:
            col = [c for c in body if c[0] == x]
            cells += col
            if not (first and n):
                got += sum(1 for cx, cy in col if all(
                    (cx + dx, cy + dy) in inner for dx, dy in blocks.ORTHO))
            first = False
            x += step
        rid = sheet.region("room", w)
        sheet.paint(cells, rid)
    return x


def _way_in(sheet, hull, hall, index, x_lo, x_hi, keel_w) -> tuple:
    """The cross passage and the locks, on the deck you come aboard by."""
    if index != 0:
        return ()
    z = {"grown": 0.0, "hybrid": 0.0, "fabricated": -0.3, "xeno": -0.2
         }.get(hull.family, 0.0)
    x = max(x_lo + 2, min(x_hi - 2, hull.x_of(z)))
    cols = tuple(range(x, x + max(1, keel_w)))
    cells = [(cx, y) for cx in cols for y in range(hull.height)
             if hull.inside(cx, y)]
    sheet.paint(cells, hall)
    ys = [y for _cx, y in cells]
    sheet.mark("airlock", x, min(ys) + 1, "port")
    if hull.family in ("grown", "hybrid", "fabricated"):
        sheet.mark("airlock", x, max(ys) - 1, "starboard")
    return cols


def _depth(hull, x: int, keel_w: int) -> int:
    """Squares of room from the keel to the skin at this column."""
    return max(0, int(hull.half(x) - keel_w / 2.0))


def _sides(sheet, hull, wants, x_lo, x_hi, passage, keel_w) -> list:
    """Pack the rest along both sides, bow to stern in program order, with
    no gaps between rooms — and then **grow every room alike** until the
    deck is full, so a lightly loaded deck has roomier rooms rather than a
    cavern of void aft. Returns whatever would not fit on this deck."""
    args = (hull, wants, x_lo, x_hi, passage, keel_w)
    best, left = _pack(*args, scale=1.0)
    if not left:
        lo, hi = 1.0, ROOMIEST
        for _step in range(6):
            mid = (lo + hi) / 2
            trial, rest = _pack(*args, scale=mid)
            if rest:
                hi = mid
            else:
                lo, best = mid, trial
    for w, side, a, b in best:
        rid = sheet.region("room", w, door_at=(
            (a + b) / 2, hull.centre((a + b) // 2)))
        sheet.paint(_side_cells(hull, a, b, side, keel_w), rid)
    return left


def _pack(hull, wants, x_lo, x_hi, passage, keel_w, scale: float):
    """Where each room would go with every area times `scale`: a list of
    (want, top side?, from column, to column), and what would not fit."""
    cursor = {True: x_hi - 1, False: x_hi - 1}
    out, left = [], []
    for w in sorted(wants, key=lambda w: (-w.zone, -w.area)):
        # The side with more hull ahead of its cursor takes the next room.
        top = cursor[True] >= cursor[False]
        for side in (top, not top):
            span = _span(hull, w.area * scale, cursor[side], x_lo, passage,
                         keel_w)
            if span is not None:
                cursor[side] = span[0] - 1
                out.append((w, side, *span))
                break
        else:
            left.append(w)
    return out, left


def _span(hull, area, start: int, x_lo: int, passage, keel_w):
    """Columns from `start` sternward holding `area` of floor, stepping over
    the cross passage; None if the hull runs out first."""
    x = start
    while x in passage:
        x -= 1
    end, got = x, 0
    while got < area and x > x_lo:
        if x in passage:
            return _span(hull, area, min(passage) - 1, x_lo, passage, keel_w)
        # The skin and the keel each take a square off the column; the
        # room's bow column is its bulkhead with the room ahead.
        if x != end:
            got += max(0, _depth(hull, x, keel_w) - 2)
        x -= 1
    if got < area:
        return None
    return (min(x + 1, end - 2), end)


def _side_cells(hull, a: int, b: int, top: bool, keel_w: int) -> list:
    out = []
    for x in range(a, b + 1):
        c = hull.centre(x)
        for y in range(hull.height):
            if not hull.inside(x, y):
                continue
            off = y - round(c)
            if top and off < -(keel_w // 2):
                out.append((x, y))
            if not top and off >= keel_w - keel_w // 2:
                out.append((x, y))
    return out


def _voids(sheet, hull, solid) -> None:
    """Between the rooms and the skin: crawlways where there is room for
    one, structure where there is not."""
    left = sheet.owned(solid)
    seen: set = set()
    for cell in left:
        if cell in seen:
            continue
        group, stack = [], [cell]
        seen.add(cell)
        while stack:
            x, y = stack.pop()
            group.append((x, y))
            for dx, dy in blocks.ORTHO:
                n = (x + dx, y + dy)
                if n not in seen and sheet.claimed(*n) and \
                        sheet.grid[n[1]][n[0]] == solid:
                    seen.add(n)
                    stack.append(n)
        if len(group) >= SPARE_HOLD:
            rid = sheet.region("room", Want("hold", "Spare hold", area=0))
            sheet.paint(group, rid)
        elif len(group) >= 12:
            rid = sheet.region("room", Want("utility", "Void space", area=0))
            sheet.paint(group, rid)


def _lifts(sheet, hull, index, count, x_lo, x_hi, keel_at) -> None:
    if count <= 1:
        return
    for shaft, z in (("aft", -0.35), ("fore", 0.35)):
        x = max(x_lo + 1, min(x_hi - 3, hull.x_of(z)))
        cx, cy = keel_at(x)[0]
        if index < count - 1:
            sheet.mark("lift", cx, cy, f"down:{shaft}")
        if index > 0:
            sheet.mark("lift", cx + 1, cy, f"up:{shaft}")


def _furniture(sheet, hull) -> None:
    """What the family's drawings hang outside the skin: a grown hull's
    radiator bloom astern, a hybrid's cradle, a Yards hull's fins."""
    solid = sheet.region("solid")
    stern = min(x for x, _y in hull.cells())
    c = round(hull.centre(stern))
    kinds = dict(hull.form.furniture)
    if "bloom" in kinds:
        for dy in (-1, 1):
            sheet.paint([(stern - 1 - i, c + dy * (1 + i)) for i in range(2)],
                        solid, over=False)
    if "cradle" in kinds or "fins" in kinds:
        for x in (hull.x_of(-0.5), hull.x_of(0.4)):
            h = hull.half(x)
            for dy in (-1, 1):
                y = round(hull.centre(x) + dy * (h + 1))
                sheet.paint([(x, y)], solid, over=False)
