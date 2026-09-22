"""Places on the ground: a settlement's streets and sheds, a drum's floor.

A power's settlement is a few streets of prefabricated sheds on a world it
was founded to work, with a landing pad at one end. What it looks like
depends on whether the world can be breathed:

- **under a sky you can breathe**, the streets are open ground and the pad
  is a scorched square of it, the gangway in the middle;
- **on an airless rock**, the streets are pressurised tubes between the
  sheds, the pad is inside a landing hangar, and the whole town is one
  sealed footprint on ground that is vacuum (`Deck.outside_air`): walk out
  on it without a sealed suit and you choke.

A spinning drum's floor is a town too — the same streets and rows, on open
ground under the drum's own air — so `town` draws both.
"""

from __future__ import annotations

from . import afoot_blocks as blocks
from .afoot_gen import Painted, Want

#: Depth of a building, and of a street, in squares.
ROW, STREET = 5, 2
#: Columns between cross-streets.
BLOCK = 13
#: Of a town's building land, how much becomes rooms rather than yards.
BUILT = 0.8


def town(sheet, x0: int, y0: int, width: int, wants: list,
         street: str = "ground", entry_cols: int = 0) -> tuple:
    """Streets and back-to-back rows of buildings, from (x0, y0), as many
    bands deep as the program needs. Returns (the bottom row drawn, what
    would not fit). `entry_cols` are kept clear at the west end for a pad
    or a plaza."""
    way = sheet.region(street)
    band = STREET + 2 * ROW
    x1 = x0 + width - 1
    xs = x0 + entry_cols
    queue = sorted(wants, key=lambda w: -w.zone)
    y = y0
    streets = []
    while queue and y + band + STREET < sheet.h - 1:
        streets.append(y)
        sheet.paint(blocks.rect(x0, y, x1, y + STREET - 1), way)
        gaps = {x for x in range(xs, x1 + 1)
                if (x - xs) % BLOCK in (BLOCK - 2, BLOCK - 1)}
        for x in gaps:
            sheet.paint(blocks.rect(x, y + STREET, x, y + band - 1), way)
        top = y + STREET
        queue = blocks.strip(sheet, xs, x1, top, top + ROW - 1, queue,
                             door_y=y, gaps=gaps)
        queue = blocks.strip(sheet, xs, x1, top + ROW, top + 2 * ROW - 1,
                             queue, door_y=y + band, gaps=gaps)
        y += band
    sheet.paint(blocks.rect(x0, y, x1, y + STREET - 1), way)
    streets.append(y)
    # The west end joins every street, so no band is an island.
    sheet.paint(blocks.rect(x0, y0, x0 + 1, y + STREET - 1), way)
    return y + STREET - 1, queue


def size_for(wants: list, width: int) -> int:
    """How deep a town of this width must be drawn to hold its program."""
    area = sum(w.area for w in wants) / BUILT
    per_band = 2 * ROW * width * 0.8
    bands = max(1, -(-int(area) // int(per_band)))
    return bands * (STREET + 2 * ROW) + STREET + 4


def settlement(rng, wants: list, style: str, breathable: bool,
               name: str = "The settlement") -> list:
    """A settlement on the ground: pad, streets and sheds."""
    pad = 9
    area = sum(w.area for w in wants)
    width = int(max(30, min(70, pad + 4 + area * 1.3 / (2 * ROW))))
    for _grow in range(6):
        height = size_for(wants, width - pad)
        sheet = blocks.Sheet(width + 4, max(height, pad + 6))
        ground = sheet.region("ground")
        sheet.paint(blocks.rect(0, 0, sheet.w - 1, sheet.h - 1), ground)
        street = "ground" if breathable else "hall"
        bottom, left = town(sheet, 2, 2, width, wants, street,
                            entry_cols=pad)
        if not left:
            break
        width = min(96, width + 12)
    if not breathable:
        # The tubes and sheds are one sealed footprint on the regolith;
        # what is left of it between them is structure, not vacuum.
        solid = sheet.region("solid")
        sheet.paint([c for c in blocks.rect(1, 1, width + 2, bottom + 1)
                     if sheet.grid[c[1]][c[0]] == ground], solid)
    py = 2 + STREET + ROW
    if breathable:
        # A scorched square of ground, the hull set down in the middle.
        sheet.mark("gangway", 2 + pad // 2, py, "pad")
    else:
        hangar = sheet.region("room", Want("hangar", "Landing hangar",
                                           area=40), door_at=(2, py))
        sheet.paint(blocks.rect(4, 2 + STREET, 2 + pad - 2, py + ROW - 1),
                    hangar)
        sheet.mark("gangway", 2 + pad // 2, py, "hangar")
    return [Painted(sheet, name, style, air=True, outside_air=breathable)]


def floor(sheet, x0: int, y0: int, width: int, wants: list) -> tuple:
    """A drum's floor: a town on the drum's own ground, with the green
    running down the middle of it."""
    sheet.paint(blocks.rect(x0, y0, x0 + width - 1, sheet.h - 3),
                sheet.region("ground"))
    green = [w for w in wants if w.kind == "park"]
    rest = [w for w in wants if w.kind != "park"]
    half = (len(rest) + 1) // 2
    bottom, left = town(sheet, x0, y0, width, rest[:half], "ground",
                        entry_cols=6)
    gy = bottom + 1
    depth = 6
    park = sheet.region("ground")
    sheet.paint(blocks.rect(x0, gy, x0 + width - 1, gy + depth - 1), park)
    for w in green:
        sheet.mark("plant", x0 + width // 2, gy + depth // 2, w.name)
    for n in range(0, width, 5):
        sheet.mark("plant", x0 + 3 + n, gy + 1 + (n // 5) % 4, "trees")
    bottom, more = town(sheet, x0, gy + depth, width, rest[half:] + left,
                        "ground", entry_cols=6)
    return bottom, more
