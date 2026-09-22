"""Furnishing a room of any shape: counters, beds, consoles, crates — and never a blocked door.

`data/afoot_rooms.py` says what stands in each kind of room and roughly
where; this puts it there. A room is whatever cells its structure gave it —
a rectangle off a corridor, a wedge of a ring, a cabin in the curve of a
hull — so every placement is read from the room itself rather than from a
rectangle's sides:

- **back** — the far wall, as far from the door as the room goes;
- **bar** — one step in front of the back wall, leaving the back row free
  for whoever works behind it;
- **walls** — against any wall, away from the door;
- **corners** — where two walls meet;
- **centre** — the middle of the room;
- **scatter** — anywhere with floor all round it.

Two rules hold for every room, whatever the table asks: **a doorway stays a
doorway** — nothing that blocks is put beside a door — and **the floor stays
whole**: after each blocking thing, the room's free floor must still be one
piece reachable from its doors.
"""

from __future__ import annotations

from ..data.afoot_rooms import ROOM_BY_ID
from ..data.afoot_things import THING_BY_ID
from .afoot_state import OPEN, Thing

ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _whole(free: set, starts: list) -> bool:
    """Is every free square reachable from a doorway square?"""
    if not free:
        return True
    seeds = [s for s in starts if s in free]
    if not seeds:
        return False
    seen = {seeds[0]}
    stack = [seeds[0]]
    while stack:
        x, y = stack.pop()
        for dx, dy in ORTHO:
            nxt = (x + dx, y + dy)
            if nxt in free and nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return len(seen) == len(free)


class Shape:
    """A room's floor, read for placement."""

    def __init__(self, deck, room, door_cells: list):
        self.cells = [c for c in room.cells() if deck.at(*c) in OPEN]
        self.have = set(self.cells)
        near = []
        for x, y in door_cells:
            for dx, dy in ORTHO:
                if (x + dx, y + dy) in self.have:
                    near.append((x + dx, y + dy))
        self.entry = near or self.cells[:1]
        self.dist = self._distances()
        self.far = max(self.dist.values(), default=0)

    def _distances(self) -> dict:
        dist = {c: 0 for c in self.entry}
        queue = list(self.entry)
        while queue:
            x, y = queue.pop(0)
            for dx, dy in ORTHO:
                nxt = (x + dx, y + dy)
                if nxt in self.have and nxt not in dist:
                    dist[nxt] = dist[(x, y)] + 1
                    queue.append(nxt)
        return dist

    def walled(self, c) -> int:
        return sum(1 for dx, dy in ORTHO
                   if (c[0] + dx, c[1] + dy) not in self.have)

    def spots(self, where: str, rng) -> list:
        d = self.dist
        if where == "back":
            out = [c for c in self.cells if self.walled(c) and
                   d.get(c, 0) >= self.far - 1]
            return sorted(out, key=lambda c: -d.get(c, 0))
        if where == "bar":
            out = [c for c in self.cells if d.get(c, 0) == max(1, self.far - 1)
                   and not self.walled(c)]
            if len(out) < 2:
                out = [c for c in self.cells
                       if d.get(c, 0) == max(1, self.far - 1)]
            return sorted(out)
        if where == "walls":
            out = [c for c in self.cells if self.walled(c) and d.get(c, 0) >= 2]
        elif where == "corners":
            out = [c for c in self.cells if self.walled(c) >= 2
                   and d.get(c, 0) >= 1]
        elif where == "centre":
            cx = sum(x for x, _y in self.cells) / max(1, len(self.cells))
            cy = sum(y for _x, y in self.cells) / max(1, len(self.cells))
            return sorted(self.cells, key=lambda c: (c[0] - cx) ** 2
                          + (c[1] - cy) ** 2)
        else:
            out = [c for c in self.cells if not self.walled(c)
                   and d.get(c, 0) >= 2]
        out = list(out)
        rng.shuffle(out)
        # A room too thin to have a middle — a hold two squares deep in the
        # curve of a narrow hull — still has its walls to stack against.
        rest = [c for c in self.cells if c not in out and d.get(c, 0) >= 1]
        rng.shuffle(rest)
        return out + rest


def furnish(rng, deck, room, ids, door_cells: list) -> list:
    """Every thing the room's kind asks for that will fit, placed."""
    kind = ROOM_BY_ID[room.kind]
    shape = Shape(deck, room, door_cells)
    free = set(shape.cells)
    near_door = {(x + dx, y + dy) for x, y in door_cells
                 for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    near_door |= set(shape.entry)
    out = []
    for thing_kind, least, most, where in kind.kit:
        tk = THING_BY_ID[thing_kind]
        if thing_kind == "counter" and where == "back" and shape.far >= 3:
            where = "bar"
        want = rng.int(least, most)
        placed = 0
        for spot in shape.spots(where, rng):
            if spot not in free:
                continue
            if placed >= want and where != "bar":
                break
            if where == "bar" and placed >= max(2, want * 4):
                break
            if tk.blocks and spot in near_door:
                continue
            if tk.blocks:
                trial = free - {spot}
                if not _whole(trial, shape.entry):
                    continue
                free = trial
            out.append(Thing(id=ids(), kind=thing_kind, deck=room.deck,
                             x=spot[0], y=spot[1], room=room.id,
                             state="shut" if thing_kind in (
                                 "locker", "crate", "strongbox") else ""))
            placed += 1
    return out


def post(walk, room) -> tuple:
    """Where somebody who works in this room stands: behind the counter if
    there is one, else as far from the door as the room goes."""
    from .afoot_map import ground
    g = ground(walk, room.deck)
    doors = [(t.x, t.y) for t in walk.things if t.deck == room.deck
             and t.kind in ("door", "hatch") and any(
                 room.holds(room.deck, t.x + dx, t.y + dy)
                 for dx, dy in ORTHO)]
    shape = Shape(walk.decks[room.deck], room, doors)
    counters = [(t.x, t.y) for t in walk.things if t.room == room.id
                and t.kind == "counter"]
    # Nobody works standing in the doorway.
    by_door = {(x + dx, y + dy) for x, y in doors
               for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
    spots = [c for c in shape.cells if g.passable(*c) and c not in by_door] \
        or [c for c in shape.cells if g.passable(*c)]
    if counters:
        behind = [c for c in spots if any(
            (c[0] + dx, c[1] + dy) in counters for dx, dy in ORTHO)
            and shape.dist.get(c, 0) > min(shape.dist.get(k, 0)
                                           for k in counters)]
        if behind:
            return max(behind, key=lambda c: shape.dist.get(c, 0))
    if not spots:
        return None
    return max(spots, key=lambda c: (shape.dist.get(c, 0), -c[0], -c[1]))
