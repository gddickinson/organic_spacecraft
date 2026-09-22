"""A spun ring's levels, unrolled: the floor you walk on is the ring's rim.

Nothing in the Verge makes a floor pull, so a habitation ring spins: its
weight is the rim pushing up under your feet, and "down" is outward. A plan
of it seen along the axis would put rooms up the wall. So each level is
drawn **unrolled** — the way a map of a cylinder is drawn:

- left to right is **round the ring**, and the two ends are one (the sheet
  and the deck `wrap`): walk off one end and you come on at the other, and
  you cannot see further than the curve of the floor lets you;
- top to bottom is **across the ring**, from one side wall to the other;
- the **ring corridor** runs its whole length down the middle, rooms either
  side of it, all at one height and one weight;
- four **spoke lobbies** cross it, each with a lift: the first up the spoke
  to the hub (weightless), the others between the levels;
- levels stack outward from the hub, the same circumference each, and the
  outermost is the heaviest (`RING_G`).
"""

from __future__ import annotations

from . import afoot_blocks as blocks
from .afoot_gen import Painted

#: The weight on the outermost level of a habitation ring, in gravities,
#: and what each level further in loses.
RING_G = 0.8
RING_STEP = 0.03
#: Room rows either side of the corridor, and the corridor itself.
ROW, CORRIDOR = 5, 2
#: The fewest columns a room on a ring takes, walls and all: three squares
#: of floor across, room for a counter and somebody to stand at it.
WIDEST = 4
#: Columns of rooms a level holds along each side before another level is
#: opened, and the least and most a ring is drawn round.
LEVEL_COLS = 58
LEAST_ROUND, MOST_ROUND = 44, 110
#: Spoke lobbies round the ring, and their width.
SPOKES, LOBBY = 4, 3
#: The most levels a ring is drawn with.
MOST_LEVELS = 8


def levels(wants: list, name: str, shaft: str, style: str) -> list:
    """The ring's levels, from the hub outward. The deck before the first
    reaches it with `down:<shaft>1`. What one level cannot hold goes on to
    the next, and a level more is opened rather than a room left out."""
    shares = _shares(sorted(wants, key=lambda w: -w.zone))
    around = max(LEAST_ROUND, min(MOST_ROUND, max(
        _needed(share) for share in shares) + SPOKES * LOBBY + 4))
    sheets, spokes, carry = [], [], []
    while (len(sheets) < len(shares) or carry) and len(sheets) < MOST_LEVELS:
        n = len(sheets)
        share = (shares[n] if n < len(shares) else []) + carry
        sheet, where = _level(share, around)
        carry, sheet.left_out = sheet.left_out, []
        sheets.append(sheet)
        spokes.append(where)
    sheets[-1].left_out += carry
    count = len(sheets)
    out = []
    for n, (sheet, where) in enumerate(zip(sheets, spokes), start=1):
        _lifts(sheet, where, shaft, n, count)
        g = round(RING_G * (1 - RING_STEP * (count - n)), 2)
        title = f"{name}, level {n}" if count > 1 else name
        out.append(Painted(sheet, title, style, g=g))
    return out


def _cols(w) -> int:
    return max(WIDEST, -(-w.area // ROW))


def _needed(share: list) -> int:
    """Columns along one side a share needs, split across both sides."""
    return -(-sum(_cols(w) for w in share) // 2) + 2


def _shares(queue: list) -> list:
    out, cur = [], []
    for w in queue:
        if cur and _needed(cur + [w]) > LEVEL_COLS:
            out.append(cur)
            cur = []
        cur.append(w)
    return out + [cur] if cur or not out else out


def _level(share: list, around: int):
    """One level: rooms, corridor, rooms, the spokes crossing. Returns the
    sheet and where its spokes are; what would not fit is its `left_out`."""
    height = 2 * ROW + CORRIDOR + 2
    sheet = blocks.Sheet(around, height)
    sheet.wrap = True
    sheet.paint(blocks.rect(0, 0, around - 1, height - 1),
                sheet.region("solid"))
    hall = sheet.region("hall")
    mid = 1 + ROW
    sheet.paint(blocks.rect(0, mid, around - 1, mid + CORRIDOR - 1), hall)
    spokes = [int(around * (k + 0.5) / SPOKES) - 1 for k in range(SPOKES)]
    gaps = set()
    for x in spokes:
        sheet.paint(blocks.rect(x, 1, x + LOBBY - 1, height - 2), hall)
        gaps |= set(range(x, x + LOBBY))
    left = blocks.strip(sheet, 0, around - 1, 1, ROW, share[::2],
                        door_y=mid, gaps=gaps, least=WIDEST)
    left = blocks.strip(sheet, 0, around - 1, mid + CORRIDOR,
                        mid + CORRIDOR + ROW - 1, share[1::2] + left,
                        door_y=mid + CORRIDOR - 1, gaps=gaps, least=WIDEST)
    sheet.left_out += left
    return sheet, spokes


def _lifts(sheet, spokes: list, shaft: str, n: int, count: int) -> None:
    """The first spoke runs up to the hub; every spoke joins the levels."""
    height = sheet.h
    for k, x in enumerate(spokes):
        tag = shaft if k == 0 else f"{shaft}s{k}"
        if k == 0 or n > 1:
            sheet.mark("lift", x + 1, 2, f"up:{tag}{n}")
        if n < count:
            sheet.mark("lift", x + 1, height - 3, f"down:{tag}{n + 1}")
