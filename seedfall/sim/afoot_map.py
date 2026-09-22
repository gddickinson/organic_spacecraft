"""The ground under the party: where a person can step, see and hide.

Pure geometry over a `Walk`. Nothing here rolls a die or writes state, so the
screen may ask any of it on every repaint — which it does, for the squares a
person can reach this round, the path to the square under the mouse, and the
cover a target is standing behind.

**Squares are Chebyshev.** A diagonal step is one square, the way Star
Frontiers and most tactical boards count, so "within six" is a square of
thirteen by thirteen and a range band reads the same in every direction. A
step may not cut a corner: moving diagonally past a wall or a counter needs
both orthogonal squares open, which is what makes a doorway a doorway.

**Sight is symmetric.** If you can see them, they can see you: a line is
clear if it is clear drawn from either end, so a pillar never hides one of
two people from the other and not the reverse.
"""

from __future__ import annotations

import heapq

from ..data.afoot_things import DOORS, THING_BY_ID
from .afoot_state import BLIND, OPEN, WINDOW

#: How far anybody sees on a lit deck, in squares.
SIGHT = 12

#: Neighbours: the four orthogonals first, so a straight path is preferred
#: over a zig-zag of the same length.
STEPS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

_CACHE: dict = {}


def distance(ax: int, ay: int, bx: int, by: int) -> int:
    """Squares between two points, a diagonal counting one."""
    return max(abs(ax - bx), abs(ay - by))


class Ground:
    """What one deck is made of, with the things on it, read once.

    Built from the terrain and the things; people are asked separately,
    because they move every step and the walls do not.
    """

    def __init__(self, walk, deck: int):
        self.deck = walk.decks[deck]
        self.index = deck
        self.blocked: set = set()
        self.opaque: set = set()
        self.shut: set = set()        # a door that must be opened, 1 MP
        self.locked: set = set()
        self.cover: dict = {}
        self.hazard: dict = {}
        for t in walk.things:
            if t.deck != deck:
                continue
            kind = THING_BY_ID.get(t.kind)
            if kind is None:
                continue
            here = (t.x, t.y)
            if t.kind in DOORS:
                if t.state == "locked":
                    self.locked.add(here)
                    self.blocked.add(here)
                    self.opaque.add(here)
                elif t.state not in ("open", "broken"):
                    self.shut.add(here)
                    self.opaque.add(here)
                continue
            if kind.blocks:
                self.blocked.add(here)
            if kind.opaque:
                self.opaque.add(here)
            if kind.cover:
                self.cover[here] = max(self.cover.get(here, 0), kind.cover)
            if t.kind in ("spores", "breach"):
                self.hazard[here] = t.kind

    def floor(self, x: int, y: int) -> bool:
        return self.deck.at(x, y) in OPEN

    def passable(self, x: int, y: int) -> bool:
        return self.floor(x, y) and (x, y) not in self.blocked

    def see_through(self, x: int, y: int) -> bool:
        cell = self.deck.at(x, y)
        if cell in BLIND:
            return False
        if cell == WINDOW:
            return True
        return (x, y) not in self.opaque


def ground(walk, deck: int) -> Ground:
    """The deck's ground, rebuilt only when a thing has changed."""
    key = (id(walk), deck, walk.version, len(walk.things))
    got = _CACHE.get(key)
    if got is None or got.deck is not walk.decks[deck]:
        if len(_CACHE) > 64:
            _CACHE.clear()
        got = _CACHE[key] = Ground(walk, deck)
    return got


# ── sight ──────────────────────────────────────────────────────────────────

def _line(ax: int, ay: int, bx: int, by: int) -> list:
    """The squares on the way from a to b, both ends included (Bresenham)."""
    out = []
    dx, dy = abs(bx - ax), -abs(by - ay)
    sx, sy = (1 if ax < bx else -1), (1 if ay < by else -1)
    err = dx + dy
    x, y = ax, ay
    while True:
        out.append((x, y))
        if x == bx and y == by:
            return out
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def _clear(g: Ground, ax: int, ay: int, bx: int, by: int) -> bool:
    return all(g.see_through(x, y) for x, y in _line(ax, ay, bx, by)[1:-1])


def sees(walk, deck: int, ax: int, ay: int, bx: int, by: int,
         reach: int = SIGHT) -> bool:
    """Whether a person at a can see b on the same deck."""
    if distance(ax, ay, bx, by) > reach:
        return False
    g = ground(walk, deck)
    return _clear(g, ax, ay, bx, by) or _clear(g, bx, by, ax, ay)


def view(walk, deck: int, x: int, y: int, reach: int = SIGHT) -> set:
    """Every square a person standing here can see."""
    g = ground(walk, deck)
    out = {(x, y)}
    for yy in range(max(0, y - reach), min(g.deck.h, y + reach + 1)):
        for xx in range(max(0, x - reach), min(g.deck.w, x + reach + 1)):
            if (xx - x) ** 2 + (yy - y) ** 2 > reach * reach + reach:
                continue
            if _clear(g, x, y, xx, yy) or _clear(g, xx, yy, x, y):
                out.add((xx, yy))
    return out


def cover_for(walk, deck: int, tx: int, ty: int, ax: int, ay: int) -> int:
    """How much cover a target at t has against a shot from a: 0, 1 or 2.

    The square next to the target towards the shooter, and for a shot from
    a diagonal both of the squares either side of it — somebody crouched
    behind a counter corner is behind the counter.
    """
    g = ground(walk, deck)
    sx = (ax > tx) - (ax < tx)
    sy = (ay > ty) - (ay < ty)
    if sx == 0 and sy == 0:
        return 0
    near = {(tx + sx, ty + sy)}
    if sx and sy:
        near |= {(tx + sx, ty), (tx, ty + sy)}
    if distance(tx, ty, ax, ay) <= 1:
        return 0            # hand to hand, nothing is between you
    best = 0
    for sq in near:
        best = max(best, g.cover.get(sq, 0))
        if sq in g.shut and best < 1:
            best = 1        # a door frame is something to stand behind
    return best


# ── movement ───────────────────────────────────────────────────────────────

def _occupied(walk, deck: int, mover) -> dict:
    """Squares with somebody on them, and whether the mover may pass."""
    out = {}
    for a in walk.actors:
        if a.id == mover.id or a.deck != deck or a.status in ("gone",):
            continue
        if any(b.carrying == a.id for b in walk.actors):
            continue
        # Friends may be walked past, never stood on. Anybody down is
        # stepped over the same way — and a party can squeeze past anybody
        # who is not against it, rather than wait at a door for a clerk.
        friend = a.side == mover.side or not a.standing or (
            mover.side == "party" and a.side == "npc"
            and a.mood in ("friendly", "neutral"))
        out[(a.x, a.y)] = friend
    return out


def _moves(g: Ground, x: int, y: int, keys: bool = False):
    """Squares one step on. `keys` walks through locked doors, which is
    what the people who live aboard can do and the party cannot."""
    def ok(px, py):
        return g.passable(px, py) or (keys and (px, py) in g.locked)
    for dx, dy in STEPS:
        nx, ny = x + dx, y + dy
        if not ok(nx, ny):
            continue
        if dx and dy and not (ok(x + dx, y) and ok(x, y + dy)):
            continue            # no cutting a corner
        yield nx, ny


def _keys(mover) -> bool:
    return getattr(mover, "side", "party") == "npc"


def reach(walk, mover, budget: int | None = None) -> dict:
    """Every square the mover can end on this round, and what it costs."""
    budget = mover.mp if budget is None else budget
    g = ground(walk, mover.deck)
    busy = _occupied(walk, mover.deck, mover)
    start = (mover.x, mover.y)
    cost = {start: 0}
    queue = [(0, start)]
    while queue:
        spent, (x, y) = heapq.heappop(queue)
        if spent > cost.get((x, y), 1 << 30):
            continue
        for nx, ny in _moves(g, x, y, _keys(mover)):
            if (nx, ny) in busy and not busy[(nx, ny)]:
                continue
            step = spent + 1 + (1 if (nx, ny) in g.shut else 0)
            if step > budget or step >= cost.get((nx, ny), 1 << 30):
                continue
            cost[(nx, ny)] = step
            heapq.heappush(queue, (step, (nx, ny)))
    return {sq: c for sq, c in cost.items() if sq not in busy}


def path(walk, mover, tx: int, ty: int, near: bool = False) -> list:
    """The cheapest way to (tx, ty), as squares after the first; [] if none.

    `near` accepts ending next to the target instead — how somebody walks up
    to a counter, a door or a person.
    """
    g = ground(walk, mover.deck)
    busy = _occupied(walk, mover.deck, mover)
    start = (mover.x, mover.y)
    goal = (tx, ty)

    def done(sq) -> bool:
        if near:
            return distance(sq[0], sq[1], tx, ty) <= 1 and sq not in busy
        return sq == goal

    if done(start):
        return []
    came: dict = {start: None}
    cost = {start: 0.0}
    queue = [(0.0, start)]
    while queue:
        _f, here = heapq.heappop(queue)
        if done(here):
            out = []
            while here != start:
                out.append(here)
                here = came[here]
            return out[::-1]
        for nxt in _moves(g, *here, _keys(mover)):
            if nxt in busy and not busy[nxt]:
                continue
            step = cost[here] + 1 + (1 if nxt in g.shut else 0) \
                + (2 if nxt in g.hazard else 0)
            if step < cost.get(nxt, 1e9):
                cost[nxt] = step
                came[nxt] = here
                heapq.heappush(queue, (step + distance(*nxt, tx, ty), nxt))
    return []


def price(walk, deck: int, squares: list) -> int:
    """What walking these squares costs in movement: one a step, one more
    for a shut door opened on the way."""
    g = ground(walk, deck)
    return sum(1 + (1 if sq in g.shut else 0) for sq in squares)


def open_squares(walk, deck: int) -> list:
    """Every square on the deck a person could stand on."""
    g = ground(walk, deck)
    return [(x, y) for y in range(g.deck.h) for x in range(g.deck.w)
            if g.passable(x, y)]


def connected(walk, deck: int, start: tuple) -> set:
    """Every square reachable on foot from `start`, doors opened as met and
    locks left alone — what the generator is held to."""
    g = ground(walk, deck)
    seen = {start}
    stack = [start]
    while stack:
        x, y = stack.pop()
        for nxt in _moves(g, x, y):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen
