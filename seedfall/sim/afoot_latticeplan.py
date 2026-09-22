"""A Dry Choir frame, laid out: the synthetic family's deck plans.

A synthetic hull is not a hull with rooms in it. It is a lattice — the
`data/hullforms.py` frame of struts and cores with nothing between them but
the vacuum it was built for. Its plan is the same: a spine crawlway bow to
stern, a **node** for each fitting as near its slot's own mount as it will
go without fouling another, a crawlway from each node to the spine, and the
struts. Nothing aboard breathes, so none of it has air.

`sim/afoot_hullplan.decks` hands a synthetic hull here with its share of
the program, frame by frame.
"""

from __future__ import annotations

import math

from . import afoot_blocks as blocks
from .afoot_gen import Painted


def _node(sheet, hull, cols, mid: int, zone: float, r: float):
    """Where a node of radius `r` goes: as near its own mount as it can be
    without touching another node or the spine, above or below it."""
    home = hull.x_of(zone)
    off = int(max(3, r + 2))
    for dx in sorted(range(-hull.L, hull.L + 1), key=abs):
        x = home + dx
        if not cols[0] + 2 <= x <= cols[-1] - 2:
            continue
        for cy in (mid - off, mid + off, mid - off - 3, mid + off + 3):
            cells = blocks.disc(x, cy, r + 1)
            # The node's own crawlway to the spine must be clear too, or it
            # runs into the node before it and the node is cut off.
            stalk = [(x + dx, y) for dx in (-1, 0, 1)
                     for y in range(min(mid, cy) + 1, max(mid, cy))]
            if all(sheet.inside(*c) and not sheet.claimed(*c)
                   for c in cells + stalk):
                return x, cy
    return None


def frame(hull, wants: list, index: int, count: int, style: str = "synthetic",
          air: bool = False, names=("Frame", "Inner frame"),
          round_: bool = True):
    """A Dry Choir frame: nodes where the fittings are, crawlways between.

    The same plan with air in it is a station of modules on a keel — a
    picket, a mine's orbital plant — which `sim/afoot_worksplan` draws with
    its own style, names and (for anything welded) square modules."""
    sheet = blocks.Sheet(hull.width, hull.height)
    hall = sheet.region("hall")
    mid = round(hull.mid)
    cols = [x for x in range(hull.width) if hull.half(x) >= 0.8]
    sheet.paint(blocks.line(cols[0], mid, cols[-1], mid), hall)
    for w in sorted(wants, key=lambda w: -w.zone):
        r = max(1.6, math.sqrt(w.area / math.pi) + 0.8)
        spot = _node(sheet, hull, cols, mid, w.zone, r)
        if spot is None:
            sheet.left_out.append(w)       # no room on this frame
            continue
        x, cy = spot
        rid = sheet.region("room", w)
        k = int(r)
        shape = blocks.disc(x, cy, r) if round_ else blocks.rect(
            x - k, cy - k, x + k, cy + k)
        sheet.paint(shape, rid, over=False)
        sheet.paint(blocks.line(x, mid, x, cy), hall, over=False)
    for x in cols[::6] if not air else ():    # the struts, bare frame only
        h = int(hull.half(x))
        sheet.paint(blocks.line(x, mid - h, x + 3, mid), hall, over=False)
    sheet.enclose(sheet.region("solid"))
    if index == 0:
        sheet.mark("airlock", cols[0] + 1, mid, "hatch")
    if count > 1:
        x = cols[len(cols) // 2]
        if index < count - 1:
            sheet.mark("lift", x, mid, "down:core")
        if index > 0:
            sheet.mark("lift", x + 1, mid, "up:core")
    return Painted(sheet, names[min(index, len(names) - 1)], style, air=air)
