"""Drawing a deck by saying what each square is for.

A blueprint (`sim/afoot_hullplan`, `afoot_structplan`, `afoot_groundplan`)
paints **regions** onto a sheet: this square is corridor, that one is the
galley, these are open ground, and everything unpainted is outside the hull.
Everything else follows from the regions, the same way for every shape a
structure can have — a tapering hull, a ring, a dome, a stack of floors,
sheds on bare regolith:

- **walls** go where two regions meet, on the side of the room (a corridor
  keeps its full width), and wherever anything meets the outside — the hull
  skin, the dome's shell, the map's edge;
- **doors** are cut where a room's wall has its own floor on one side and a
  corridor on the other, one per room, nearest where the room asked for it;
- a room with no corridor beside it is **linked** through a wall it shares
  with a room that can be reached, until every room can be.

So a blueprint never draws a wall or places a door, and cannot get either
wrong: it only decides the shape of the thing and what is where in it. A
room is whatever cells its region ends up with, which is how a cabin in the
curve of a grown hull comes out the shape of the curve.
"""

from __future__ import annotations

from dataclasses import dataclass

from .afoot_state import (FLOOR, GROUND, HALL, VOID, WALL, WINDOW, Room,
                          Thing)

OUTSIDE = -1
ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))
#: Marks that are a way onto a deck: where reaching a room is measured from.
WAYS_ON = ("airlock", "gangway", "lift", "pod")

#: Room kinds whose walls against the outside are glazed where they can be.
GLAZED = ("bridge", "lounge", "observation", "suites", "salon", "sensors",
          "park", "pools", "command")


@dataclass
class Region:
    rid: int
    #: hall | room | ground | solid (structure: every square of it a wall)
    kind: str
    want: object = None
    #: Who gets the wall where two regions meet: the higher rank.
    rank: int = 0
    #: Where the room would like its door, if it can have it there.
    door_at: tuple = ()


class Sheet:
    """One deck being drawn."""

    def __init__(self, w: int, h: int):
        self.w, self.h = w, h
        self.grid = [[OUTSIDE] * w for _ in range(h)]
        self.regions: list = []
        self.marks: list = []            # (kind, x, y, note) things to place
        #: What the last build could not keep: rooms squeezed to nothing or
        #: with no way in, as the `Want`s they were painted from.
        self.dropped: list = []
        #: What the blueprint found no room for at all, before any build.
        self.left_out: list = []
        #: The region a deck was first filled with, that rooms and corridors
        #: are carved out of: a dome's open ground. -1 for none.
        self.base = -1
        #: The squares the last reach worked out could be walked to.
        self.reached: set = set()
        #: A sheet whose left and right edges are one: a spun ring's level
        #: or a drum's floor, unrolled. Walls do not form across the seam.
        self.wrap = False

    # ── painting ──────────────────────────────────────────────────────────

    def region(self, kind: str, want=None, door_at: tuple = ()) -> int:
        rid = len(self.regions)
        rank = 0 if kind in ("hall", "ground", "solid") else 1 + sum(
            1 for r in self.regions if r.kind == "room")
        self.regions.append(Region(rid, kind, want, rank, door_at))
        return rid

    def inside(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def paint(self, cells, rid: int, over: bool = True) -> int:
        """Give cells to a region. `over=False` only takes unclaimed ones."""
        n = 0
        for x, y in cells:
            if not self.inside(x, y):
                continue
            if not over and self.grid[y][x] != OUTSIDE:
                continue
            self.grid[y][x] = rid
            n += 1
        return n

    def enclose(self, rid: int) -> None:
        """Wrap everything painted so far in `rid` (a solid region, usually):
        the skin of a crawlway strung through vacuum, a tunnel through rock."""
        ring = {(x + dx, y + dy) for y in range(self.h) for x in range(self.w)
                if self.grid[y][x] != OUTSIDE
                for dx in (-1, 0, 1) for dy in (-1, 0, 1)}
        self.paint([c for c in ring if self.inside(*c)], rid, over=False)

    def owned(self, rid: int) -> list:
        return [(x, y) for y in range(self.h) for x in range(self.w)
                if self.grid[y][x] == rid]

    def claimed(self, x: int, y: int) -> bool:
        return self.inside(x, y) and self.grid[y][x] != OUTSIDE

    def mark(self, kind: str, x: int, y: int, note: str = "") -> None:
        """A thing the blueprint wants on a square: a lift, the way out."""
        self.marks.append((kind, x, y, note))

    # ── building ──────────────────────────────────────────────────────────

    def _rid(self, x: int, y: int) -> int:
        if self.wrap and 0 <= y < self.h:
            x %= self.w
        return self.grid[y][x] if self.inside(x, y) else OUTSIDE

    def _walls(self) -> set:
        walls = set()
        for y in range(self.h):
            for x in range(self.w):
                rid = self.grid[y][x]
                if rid == OUTSIDE:
                    continue
                me = self.regions[rid]
                if me.kind == "solid":
                    walls.add((x, y))
                    continue
                for dx, dy in ORTHO:
                    other = self._rid(x + dx, y + dy)
                    if other == rid:
                        continue
                    if other == OUTSIDE:
                        walls.add((x, y))
                        break
                    them = self.regions[other]
                    if them.kind == "solid":
                        continue           # already a wall on their side
                    if me.kind == "room" and (
                            them.kind != "room" or me.rank > them.rank):
                        walls.add((x, y))
                        break
        return walls

    def lost(self) -> list:
        """The program spaces a build of this sheet would lose, so that a
        blueprint can make room for them before it hands the sheet over.
        Void space is not a program space."""
        self.build(0, lambda: 0)
        return self.left_out + [w for w in self.dropped
                                if w is not None and w.area]

    def build(self, deck: int, ids, style: str = "") -> tuple:
        """Terrain rows, rooms (each with the `Want` it came from), and the
        doors and marks as things."""
        walls = self._walls()
        self.dropped = []
        rows = [[VOID] * self.w for _ in range(self.h)]
        for y in range(self.h):
            for x in range(self.w):
                rid = self.grid[y][x]
                if rid == OUTSIDE:
                    continue
                if (x, y) in walls:
                    rows[y][x] = WALL
                    continue
                kind = self.regions[rid].kind
                rows[y][x] = (HALL if kind == "hall" else GROUND
                              if kind == "ground" else FLOOR)
        things, doors = [], []
        rooms = {}
        for region in self.regions:
            if region.kind != "room":
                continue
            cells = [(x, y) for x, y in self.owned(region.rid)
                     if (x, y) not in walls]
            if len(cells) < 2:
                self.dropped.append(region.want)   # squeezed to nothing
                continue
            rooms[region.rid] = cells
        reach = self._reachable(rows, rooms)
        for rid in sorted(rooms, key=lambda r: self.regions[r].rank):
            spot = self._door(rows, walls, rid, rooms, reach, public=True)
            if spot is not None:
                doors.append((spot, rid))
                rows[spot[1]][spot[0]] = FLOOR
                reach = self._reachable(rows, rooms)
        for _pass in range(len(rooms) + 1):
            stuck = [r for r in rooms if r not in reach]
            if not stuck:
                break
            moved = False
            for rid in stuck:
                spot = self._door(rows, walls, rid, rooms, reach, public=True,
                                  first=False) or self._door(
                    rows, walls, rid, rooms, reach, public=False)
                if spot is not None:
                    doors.append((spot, rid))
                    rows[spot[1]][spot[0]] = FLOOR
                    reach = self._reachable(rows, rooms)
                    moved = True
            if not moved:
                break
        for rid in [r for r in rooms if r not in reach]:
            self.dropped.append(self.regions[rid].want)
            for x, y in rooms.pop(rid):
                rows[y][x] = WALL           # a room nobody can reach is solid
        self._glaze(rows, rooms)
        out_rooms = []
        for rid, cells in rooms.items():
            out_rooms.append((_room(ids, self.regions[rid], cells, deck),
                              self.regions[rid].want))
        by_region = {rid: room.id for (room, _w), rid in
                     zip(out_rooms, rooms.keys())}
        for (x, y), rid in doors:
            things.append(Thing(id=ids(), kind="door", deck=deck, x=x, y=y,
                                state="shut", room=by_region.get(rid, -1)))
        taken = {(t.x, t.y) for t in things}
        for kind, x, y, note in self.marks:
            spot = _open_near(rows, x, y, taken)
            if spot is not None:
                taken.add(spot)
                things.append(Thing(id=ids(), kind=kind, deck=deck, x=spot[0],
                                    y=spot[1], note=note,
                                    name=_mark_name(kind, note)))
        return ["".join(r) for r in rows], out_rooms, things

    def _reachable(self, rows, rooms) -> set:
        """Rooms a person could walk into from the ways onto this deck —
        its locks, its gangway, its lifts — or, on a deck with none of
        those, from its corridors and ground. A corridor that leads nowhere
        does not make a room behind it reachable."""
        open_ = {(x, y) for y in range(self.h) for x in range(self.w)
                 if rows[y][x] in (FLOOR, HALL, GROUND)}
        starts = [s for s in (_open_near(rows, x, y, set())
                              for kind, x, y, _n in self.marks
                              if kind in WAYS_ON) if s is not None]
        if not starts:
            starts = [(x, y) for x, y in open_ if self.regions[
                self.grid[y][x]].kind in ("hall", "ground")]
        seen = set(starts)
        stack = list(starts)
        while stack:
            x, y = stack.pop()
            for dx, dy in ORTHO:
                nxt = (x + dx, y + dy)
                if nxt in open_ and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        self.reached = seen
        return {rid for rid, cells in rooms.items()
                if any(c in seen for c in cells)}

    def _door(self, rows, walls, rid, rooms, reach, public: bool,
              first: bool = True):
        """The best wall square to cut a door through for this room.

        `public`: onto a corridor or open ground — on the `first` pass the
        one nearest where the room asked for its door, after that only one
        that is itself reached. Otherwise onto a room that can already be
        reached.
        """
        mine = set(rooms[rid])
        region = self.regions[rid]
        best, best_score = None, None
        cands = set()
        for x, y in mine:
            for dx, dy in ORTHO:
                w = (x + dx, y + dy)
                if w in walls and self.inside(*w):
                    far = (w[0] + dx, w[1] + dy)
                    if not self.inside(*far) or rows[far[1]][far[0]] not in (
                            FLOOR, HALL, GROUND):
                        continue
                    other = self.grid[far[1]][far[0]]
                    kind = self.regions[other].kind
                    if public and kind not in ("hall", "ground"):
                        continue
                    if public and not first and far not in self.reached:
                        continue           # a corridor that leads nowhere
                    if not public and (kind != "room" or other not in reach
                                       or other == rid):
                        continue
                    if rows[w[1]][w[0]] != WALL:
                        continue
                    cands.add(w)
        want = region.door_at
        cx = sum(x for x, _y in mine) / len(mine)
        cy = sum(y for _x, y in mine) / len(mine)
        for w in sorted(cands):
            target = want or (cx, cy)
            score = (w[0] - target[0]) ** 2 + (w[1] - target[1]) ** 2
            if best_score is None or score < best_score:
                best, best_score = w, score
        return best

    def _glaze(self, rows, rooms) -> None:
        """Windows in the outer wall of a room that should look out."""
        for rid, cells in rooms.items():
            want = self.regions[rid].want
            if getattr(want, "kind", "") not in GLAZED:
                continue
            for x, y in cells:
                for dx, dy in ORTHO:
                    wx, wy = x + dx, y + dy
                    ox, oy = x + 2 * dx, y + 2 * dy
                    if self.inside(wx, wy) and rows[wy][wx] == WALL and (
                            not self.inside(ox, oy) or rows[oy][ox] == VOID) \
                            and (wx + wy) % 3:
                        rows[wy][wx] = WINDOW


def _room(ids, region, cells, deck: int) -> Room:
    want = region.want
    xs = [x for x, _y in cells]
    ys = [y for _x, y in cells]
    x0, y0 = min(xs), min(ys)
    w, h = max(xs) - x0 + 1, max(ys) - y0 + 1
    have = set(cells)
    mask = ["".join("1" if (x0 + i, y0 + j) in have else "0"
                    for i in range(w)) for j in range(h)]
    from ..data.afoot_rooms import ROOM_BY_ID
    kind = ROOM_BY_ID.get(getattr(want, "kind", ""), None)
    return Room(id=ids(), name=getattr(want, "name", "") or (
        kind.name if kind else "Room"), kind=getattr(want, "kind", "utility"),
        deck=deck, x=x0, y=y0, w=w, h=h, venue=getattr(want, "venue", ""),
        part=getattr(want, "part", ""), mask=mask)


def _open_near(rows, x: int, y: int, taken: set):
    """The open square a mark goes on: its own, or the nearest within two
    if a wall took it — a lock at the tip of a curving passage."""
    for r in range(3):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if max(abs(dx), abs(dy)) != r:
                    continue
                cx, cy = x + dx, y + dy
                if 0 <= cy < len(rows) and 0 <= cx < len(rows[0]) and \
                        rows[cy][cx] in (FLOOR, HALL, GROUND) and \
                        (cx, cy) not in taken:
                    return cx, cy
    return None


def _mark_name(kind: str, note: str) -> str:
    return {"lift": f"lift {note}".strip(), "airlock": "the way out",
            "gangway": "the way out", "pod": "a lifeboat"}.get(kind, "")


# ── shapes, as cell sets ───────────────────────────────────────────────────

def rect(x0: int, y0: int, x1: int, y1: int) -> list:
    """Every cell from (x0, y0) to (x1, y1), inclusive."""
    return [(x, y) for y in range(min(y0, y1), max(y0, y1) + 1)
            for x in range(min(x0, x1), max(x0, x1) + 1)]


def disc(cx: float, cy: float, r: float) -> list:
    rr = r * r
    return [(x, y) for y in range(int(cy - r) - 1, int(cy + r) + 2)
            for x in range(int(cx - r) - 1, int(cx + r) + 2)
            if (x - cx) ** 2 + (y - cy) ** 2 <= rr]


def line(x0: int, y0: int, x1: int, y1: int, width: int = 1) -> list:
    """A corridor from one point to another, `width` squares wide."""
    out = set()
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for i in range(steps + 1):
        x = round(x0 + (x1 - x0) * i / steps)
        y = round(y0 + (y1 - y0) * i / steps)
        for dx in range(width):
            for dy in range(width):
                out.add((x + dx - width // 2, y + dy - width // 2))
    return sorted(out)


def strip(sheet, x0: int, x1: int, y0: int, y1: int, wants: list,
          door_y: int, gaps=(), fill: bool = True, least: int = 3) -> list:
    """Rooms side by side from x0 to x1, each the full depth y0..y1, their
    doors toward `door_y` — a row of shops on a street, of offices along a
    spine. `gaps` are columns kept clear for cross-streets. Sized to fill
    the row in proportion to what each asked for; returns what would not
    fit."""
    depth = abs(y1 - y0) + 1
    cols = [x for x in range(min(x0, x1), max(x0, x1) + 1) if x not in gaps]
    runs, run = [], []
    for x in cols:
        if run and x != run[-1] + 1:
            runs.append(run)
            run = []
        run.append(x)
    if run:
        runs.append(run)
    queue = sorted(wants, key=lambda w: -w.zone)
    left = []
    for run in runs:
        got = []
        while queue and sum(_cols(w, depth, least) for w in got + [
                queue[0]]) <= len(run):
            got.append(queue.pop(0))
        if not got:
            continue
        need = [_cols(w, depth, least) for w in got]
        spare = len(run) - sum(need) if fill else 0
        i = 0
        for n, (w, cols_) in enumerate(zip(got, need)):
            extra = spare * cols_ // sum(need)
            if n == len(got) - 1 and fill:
                extra = len(run) - i - cols_
            xs = run[i:i + cols_ + extra]
            i += cols_ + extra
            rid = sheet.region("room", w, door_at=(
                (xs[0] + xs[-1]) / 2, door_y))
            sheet.paint(rect(xs[0], y0, xs[-1], y1), rid)
    left += queue
    return left


def _cols(want, depth: int, least: int = 3) -> int:
    """Columns a room in a row needs: three at least, because a room two
    wide between two neighbours is all wall — `least` more where people
    will stand about in it."""
    return max(least, -(-want.area // depth))
