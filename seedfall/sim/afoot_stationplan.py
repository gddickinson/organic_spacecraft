"""Stations, laid out as they are built.

The shapes are `data/berths3d.py`'s and `data/works3d.py`'s own:

- **a quay** is "a single can with a mast and one arm": a stack of round
  decks on one lift core — the quay deck with the arm out to the berths,
  the concourse decks above it, the plant below, and the mast on top where
  traffic control looks out;
- **a Fleet Hub** is "two habitation rings on a long spine, and four arms":
  the spine deck with a berth on the end of each arm, customs and the
  harbour office along it, and a lift from the spine up each ring's spoke
  to its hub — the concourse on one ring, where people live on the other;
- **a ringed station** (a drydock, a free port, a reef, a bastion) is a hub
  deck with its docking arm and its works, and the ring round it;
- **a drum** (an ARCA habitat) is its axis — where you dock, where the plant
  is — and the inside of the drum, a town on the drum's own ground with the
  green down the middle (`sim/afoot_groundplan.floor`).

Every blueprint takes its program (`sim/afoot_placeprog.py`) and returns
`Painted` decks; nothing in the program is left out — a deck that cannot
hold its share hands the rest to the next, and the last grows.
"""

from __future__ import annotations

from . import afoot_blocks as blocks
from . import afoot_groundplan as ground
from . import afoot_loops as loops
from .afoot_gen import Painted

#: The largest a round deck is drawn, and the smallest.
LEAST_R, MOST_R = 9, 24
#: How far an arm runs out from the skin to its berths.
ARM = 12
#: How much of a habitation ring's radius is built: rooms, corridor, rooms.
RIM = 13
#: The radius a Fleet Hub's rings are drawn at. A ring does not grow to
#: hold more; it has more levels. 22 keeps a level narrow enough to be
#: drawn at a size the screen letters its rooms at.
HUB_RING_R = 22
#: Floor a can's deck is drawn to hold before the can is given another.
PER_DECK = 280
#: What keeps a structure running goes on its plant deck.
PLANT = ("lifesupport", "power", "reclaim", "store", "workshop", "dormitory",
         "quarters", "galley")


def _can(wants: list, radius: float, core: float = 2.5, arm: list = (),
         spokes: int = 4, square: bool = False, floor: str = "hall",
         rim=None):
    """One round deck — square-cornered for a tower floor, open ground for
    a dome — with an arm to the east if `arm` has berths for it. Returns
    (sheet, geo, what would not fit)."""
    extra = (ARM + 4) if arm else 0
    size = int(2 * radius) + 5
    sheet = blocks.Sheet(size + extra, size)
    c = size // 2
    if floor == "ground":
        sheet.base = sheet.region("ground")
        sheet.paint(loops.band(c, c, 0, radius + 0.01, square), sheet.base)
    geo, left = loops.loop(sheet, c, c, radius, wants, core=core,
                           spokes=spokes, arms=(0.0,) if arm else (),
                           square=square, floor=floor, rim=rim,
                           shell=floor != "ground" and rim is None)
    if arm:
        left += _arm(sheet, geo, list(arm))
    sheet.enclose(sheet.region("solid"))
    return sheet, geo, left


def _arm(sheet, geo, berths: list) -> list:
    """A docking arm east from the skin, the berths along its far end and
    the gangway at the very end of it."""
    x0 = int(geo.cx + geo.radius)
    x1 = x0 + ARM
    cy = int(geo.cy)
    sheet.paint(blocks.rect(x0, cy - 1, x1, cy), sheet.region("hall"))
    half = (len(berths) + 1) // 2
    left = blocks.strip(sheet, x0 + 3, x1, cy - 5, cy - 2, berths[:half],
                        door_y=cy - 1, fill=True)
    left = blocks.strip(sheet, x0 + 3, x1, cy + 1, cy + 4,
                        berths[half:] + left, door_y=cy, fill=True)
    sheet.mark("gangway", x1, cy, "arm")
    return left


def _lift(sheet, geo, shaft: str, up: bool, down: bool) -> None:
    cx, cy = int(geo.cx), int(geo.cy)
    if down:
        sheet.mark("lift", cx, cy - 1, f"down:{shaft}")
    if up:
        sheet.mark("lift", cx, cy + 1, f"up:{shaft}")


def _radius(wants: list, core: float = 2.5, least: float = LEAST_R,
            rim=None, square: bool = False) -> float:
    return loops.fit_radius(sum(w.area for w in wants), core, least,
                            MOST_R + (10 if rim else 0), square, rim)


def _stack(queue: list, radius: float, style: str, namer, arm: list = (),
           above: bool = False, square: bool = False) -> list:
    """A can: round decks of one radius on one lift core, the arm on the
    first, filled in program order — each deck as full as it will go, what
    it cannot hold carried up to the next. `namer(n, wants, last)` names a
    deck by what is on it. `above`: the core goes on up to a deck the caller
    adds — a quay's mast."""
    cap = loops.capacity(radius, 2.5, square)
    out, carry, rest = [], [], list(queue)
    while (rest or carry) and len(out) < 12:
        share = list(carry)
        while rest and sum(w.area for w in share) + rest[0].area <= cap:
            share.append(rest.pop(0))
        if not share and rest:
            share.append(rest.pop(0))
        sheet, geo, carry = _can(share, radius,
                                 arm=arm if not out else (), square=square)
        last = not rest and not carry
        _lift(sheet, geo, "core", up=bool(out), down=above or not last)
        placed = [w for w in share if w not in carry]
        out.append(Painted(sheet, namer(len(out), placed, last), style))
    return out


def _deck_name(first: str, plant: str = "Plant deck"):
    def name(n: int, wants: list, last: bool) -> str:
        if n == 0:
            return first
        if last and any(w.kind in PLANT for w in wants):
            return plant
        return f"Deck {n + 1}"
    return name


# ── the blueprints ─────────────────────────────────────────────────────────

def quay(rng, own: list, halls: list, style: str) -> list:
    """A quay: the can, its arm, its mast."""
    berths = [w for w in own if w.kind == "docks"]
    mast = [w for w in own if w.kind == "traffic"]
    plant = [w for w in own if w.kind in PLANT]
    front = [w for w in own if w not in berths + mast + plant]
    queue = front + halls + plant
    total = sum(w.area for w in queue)
    per = max(2, min(5, -(-total // PER_DECK)))
    radius = loops.fit_radius(total // per + 20, 2.5, LEAST_R, MOST_R)
    out = _stack(queue, radius, style, _deck_name("The quay"), arm=berths,
                 above=True)
    # The mast: traffic control, on top of it all, glazed all round.
    sheet, geo, left = _can(mast, 6, core=1.5, spokes=2)
    _lift(sheet, geo, "core", up=True, down=False)
    sheet.left_out += left
    out.append(Painted(sheet, "The mast", style))
    return out


def hub(rng, own: list, halls: list, style: str) -> list:
    """A Fleet Hub: the spine with its four arms, and its two rings — each
    as many levels deep as its doors and homes need."""
    spine = _spine(own, style)
    venues = [w for w in halls if w.kind != "homes"]
    homes = [w for w in halls if w.kind == "homes"]
    ring_a = venues[: (len(venues) * 2 + 2) // 3]
    ring_b = venues[len(ring_a):] + homes
    out = [spine]
    for name, shaft, share in (("The first ring", "ring_a", ring_a),
                               ("The second ring", "ring_b", ring_b)):
        out += levels(share, HUB_RING_R, name, shaft, style)
    return out


def levels(wants: list, radius: float, name: str, shaft: str, style: str,
           core: float = 3.5, rim=None) -> list:
    """A ring (or, with `rim=False`, a can) as many levels deep as its
    program needs, all one radius, joined at the hub by one lift shaft that
    the deck before it reaches with `down:<shaft>1`. Named "…, level n" when
    there is more than one."""
    rim = RIM if rim is None else (rim or None)
    cap = loops.capacity(radius, core, rim=rim)
    rest = sorted(wants, key=lambda w: -w.zone)
    sheets = []
    while (rest or not sheets) and len(sheets) < 12:
        share = []
        while rest and sum(w.area for w in share) + rest[0].area <= cap:
            share.append(rest.pop(0))
        if not share and rest:
            share.append(rest.pop(0))
        sheet, geo, left = _can(share, radius, core=core, spokes=4, rim=rim)
        rest = left + rest
        n = len(sheets) + 1
        _lift(sheet, geo, f"{shaft}{n}", up=True, down=False)
        if rest:
            _lift(sheet, geo, f"{shaft}{n + 1}", up=False, down=True)
        sheets.append(sheet)
    sheets[-1].left_out += rest
    many = len(sheets) > 1
    return [Painted(sheet, f"{name}, level {n + 1}" if many else name, style)
            for n, sheet in enumerate(sheets)]


def _spine(own: list, style: str):
    """The spine deck: a long corridor, an arm up and down at each end with
    a berth on it, and the port's own rooms along both sides."""
    berths = [w for w in own if w.kind == "docks"]
    rest = [w for w in own if w.kind != "docks"]
    depth, arm = 5, 6
    width = max(56, min(90, 16 + sum(w.area for w in rest) // (2 * depth)))
    height = 2 * (depth + arm + 6) + 4
    sheet = blocks.Sheet(width + 4, height)
    mid = height // 2
    hall = sheet.region("hall")
    sheet.paint(blocks.rect(2, mid - 1, width + 1, mid), hall)
    xs = (width // 4, width // 4 + 2, 3 * width // 4, 3 * width // 4 + 2)
    gaps = set()
    for n, x in enumerate(xs):
        up = n % 2 == 0
        y_end = 2 if up else height - 3
        sheet.paint(blocks.rect(x, min(mid, y_end), x + 1, max(mid, y_end)),
                    hall)
        gaps |= {x - 1, x, x + 1, x + 2}
    lifts = (width // 2 - 6, width // 2 + 6)
    for x, shaft in zip(lifts, ("ring_a1", "ring_b1")):
        sheet.mark("lift", x, mid - 1, f"down:{shaft}")
    left = blocks.strip(sheet, 3, width, mid - 1 - depth, mid - 2,
                        rest[::2], door_y=mid - 1, gaps=gaps)
    left = blocks.strip(sheet, 3, width, mid + 1, mid + depth,
                        rest[1::2] + left, door_y=mid, gaps=gaps)
    for n, (x, w) in enumerate(zip(xs, berths)):
        up = n % 2 == 0
        y0, y1 = (2, 6) if up else (height - 7, height - 3)
        rid = sheet.region("room", w, door_at=(x, y1 + 1 if up else y0 - 1))
        sheet.paint(blocks.rect(x - 3, y0, x + 4, y1), rid)
        sheet.mark("gangway", x, y0 + 1 if up else y1 - 1, f"arm {n + 1}")
    sheet.left_out += left + berths[len(xs):]
    sheet.enclose(sheet.region("solid"))
    return Painted(sheet, "The spine", style)


def ringed(rng, wants: list, style: str) -> list:
    """A hub deck with its works and its arm; the ring round it, as many
    levels deep as the people who live on it need."""
    berths = [w for w in wants if w.kind in ("airlock", "docks")]
    live = [w for w in wants if w.kind in ("homes", "park", "farm", "clinic",
                                           "wards", "surgery", "quarters",
                                           "dormitory", "galley")
            or w.venue]
    works = [w for w in wants if w not in berths + live]
    sheet, geo, left = _can(works, _radius(works), arm=berths)
    _lift(sheet, geo, "spoke1", up=False, down=True)
    radius = _radius(live + left, core=3.5, least=RIM + 7, rim=RIM)
    return [Painted(sheet, "The hub", style)] + levels(
        live + left, min(radius, HUB_RING_R), "The ring", "spoke", style)


def drum(rng, wants: list, style: str) -> list:
    """The axis, and the town inside the drum."""
    berths = [w for w in wants if w.kind in ("airlock", "docks")]
    axis = [w for w in wants if w.kind in ("command", "sensors", "power",
                                           "lifesupport", "reclaim")]
    town = [w for w in wants if w not in berths + axis]
    sheet, geo, left = _can(axis, _radius(axis), arm=berths)
    _lift(sheet, geo, "spoke", up=False, down=True)
    width = max(48, min(84, 24 + len(town) * 2))
    height = 2 * ground.size_for(town, width) + 10
    inside = blocks.Sheet(width + 4, height)
    _bottom, more = ground.floor(inside, 2, 2, width, town + left)
    inside.mark("lift", 3, 3, "up:spoke")
    inside.left_out += more
    return [Painted(sheet, "The axis", style),
            Painted(inside, "Inside the drum", style)]
