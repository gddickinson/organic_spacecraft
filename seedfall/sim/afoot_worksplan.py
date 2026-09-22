"""Holdings and the rest, laid out as they are built.

What `data/works3d.traits_of` says a class of holding looks like decides
which blueprint it gets — the same traits the 3D model is assembled from:

- a **tower** (a STACK arcology): square floors on one lift core, the
  concourse at the bottom where the skybridge comes in, the wards and the
  homes above, the sky garden on the roof;
- a **dome** (a LICHEN dome): one floor of open ground under the shell,
  the galleries and homes round a plaza, the lock through the shell;
- anything else in orbit is **modules on a keel** — a picket, a vault, a
  still, a foundry: the keel runs from the docking lock to the far end,
  and each working space is a module on a short tube off it, as near the
  lock or as far from it as its band says (`sim/afoot_latticeplan.frame`,
  the same plan a Dry Choir frame is, with air in it);
- a **Kith gathering** is their own: the singing hall at the heart, the
  listening hall and the garden round it, the nest behind.

Everything with a ring or a drum is `sim/afoot_stationplan`'s; everything
on the ground is `sim/afoot_groundplan`'s.
"""

from __future__ import annotations

import dataclasses
import math

from . import afoot_latticeplan as lattice
from . import afoot_stationplan as station
from .afoot_gen import Painted

#: A tower floor's program, most public first: what goes on which floor.
LOBBY = ("chandler", "eatery", "market", "tech", "bank", "office", "law",
         "transport", "customs", "airlock", "docks")
MEDICAL = ("wards", "surgery", "clinic")


def tower(rng, wants: list, style: str) -> list:
    """Square floors on one core: lobby, wards, homes, the sky garden."""
    arm = [w for w in wants if w.kind in ("airlock", "docks")]
    roof = [w for w in wants if w.kind == "park"]
    lobby = [w for w in wants if w.kind in LOBBY and w not in arm]
    medical = [w for w in wants if w.kind in MEDICAL]
    upper = [w for w in wants if w not in arm + roof + lobby + medical]
    queue = lobby + medical + upper + roof
    radius = station._radius(lobby or upper, least=10, square=True)
    radius = max(radius, station.loops.fit_radius(
        sum(w.area for w in queue) // 4, 2.5, 10, station.MOST_R, True))

    def name(n: int, wants: list, last: bool) -> str:
        if n == 0:
            return "Skybridge level"
        if any(w.kind == "park" for w in wants):
            return "The sky garden"
        if any(w.kind in MEDICAL for w in wants):
            return f"Level {n + 1} — medical"
        return f"Level {n + 1}"
    return station._stack(queue, radius, style, name, arm=arm, square=True)


def dome(rng, wants: list, style: str) -> list:
    """One floor of ground under the shell, and the lock through it."""
    lock = [w for w in wants if w.kind in ("airlock", "docks")]
    inside = [w for w in wants if w not in lock]
    r = station._radius(inside, core=4.0, least=12)
    while True:
        sheet, geo, left = station._can(inside, r, core=4.0, arm=lock,
                                        spokes=6, floor="ground")
        if not left or r >= station.MOST_R + 8:
            break
        r += 2
    out = [Painted(sheet, "Under the dome", style)]
    if left:
        # What the dome's floor cannot hold is dug out beneath it.
        station._lift(sheet, geo, "galleries1", up=False, down=True)
        out += station.can_levels(left, station.MOST_R,
                                  "The galleries beneath", "galleries", style)
    return out


#: Modules a keel holds comfortably before a second deck is drawn.
MODULES_PER_DECK = 18
#: What a keel station's decks are called, by how many it has.
KEEL_DECKS = {2: ("upper", "lower"), 3: ("upper", "middle", "lower")}


class Keel:
    """The outline a module station is strung along: what
    `afoot_latticeplan.frame` asks of a hull."""

    def __init__(self, wants: list):
        area = sum(w.area for w in wants)
        self.L = int(max(24, min(84, 10 + area / 5)))
        self.W = int(max(18, min(30, 12 + len(wants))))
        self.width = self.L + 4
        self.height = self.W + 4
        self.mid = self.height / 2 - 0.5

    def half(self, x: int) -> float:
        return self.W / 2.0 if 2 <= x < 2 + self.L else 0.0

    def x_of(self, zone: float) -> int:
        return int(round(2 + (zone + 1.0) / 2.0 * self.L - 0.5))

    def grow(self) -> None:
        self.L = min(110, int(self.L * 1.2) + 2)
        self.width = self.L + 4


def modules(rng, wants: list, style: str, air: bool = True,
            name: str = "The station") -> list:
    """Modules on a keel, the lock at the near end. A program band of +1
    (by the way in) is drawn at the keel's near end, where the lock is. A
    keel that cannot hold every module at its longest gets a second deck of
    them, and a third, joined by a lift up the keel."""
    pairs = sorted(((dataclasses.replace(w, zone=-w.zone), w) for w in wants),
                   key=lambda pair: -pair[0].zone)
    flipped = [copy for copy, _w in pairs]
    back = {id(copy): w for copy, w in pairs}
    # Start from as many decks as the program plainly needs.
    first = max(1, min(3, -(-len(flipped) // MODULES_PER_DECK)))
    for count in range(first, 4):
        shares = [flipped[n::count] for n in range(count)]
        names = (name,) if count == 1 else tuple(
            f"{name} — {deck} deck" for deck in KEEL_DECKS[count])
        keel = Keel(shares[0])
        for _grow in range(6):
            frames = [lattice.frame(keel, share, n, count, style=style,
                                    air=air, names=names,
                                    round_=style != "fabricated")
                      for n, share in enumerate(shares)]
            if not any(f.sheet.lost() for f in frames):
                break
            keel.grow()
        if not any(f.sheet.lost() for f in frames):
            break
    # The rooms carry the program's own wants, not the flipped copies.
    for frame in frames:
        for region in frame.sheet.regions:
            if region.want is not None and id(region.want) in back:
                region.want = back[id(region.want)]
        frame.sheet.left_out = [back.get(id(w), w)
                                for w in frame.sheet.left_out]
    return frames


def gathering(rng, wants: list) -> list:
    """The Kith's own hall: the singing hall at the heart."""
    heart = max(wants, key=lambda w: w.area)
    ring = [w for w in wants if w is not heart and w.kind != "docks"]
    lock = [w for w in wants if w.kind == "docks"]
    r = max(10, math.sqrt(heart.area / math.pi) + 7)
    while True:
        sheet, geo, left = station._can(ring, r, core=math.sqrt(
            heart.area / math.pi) + 1, arm=lock, spokes=3, floor="ground")
        if not left or r >= station.MOST_R:
            break
        r += 2
    # The heart is the core itself: the hall the spokes run into.
    core = sheet.region("room", heart, door_at=(geo.cx + geo.core, geo.cy))
    from . import afoot_loops as loops
    sheet.paint(loops.band(geo.cx, geo.cy, 0, geo.core - 1), core)
    sheet.left_out += left
    return [Painted(sheet, "The gathering", "xeno")]
