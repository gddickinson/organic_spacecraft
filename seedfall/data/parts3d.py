"""What a fitting looks like, from its slot, its yard and its mass.

The last page in the catalogue that was words only. Eighty-four parts across
seven slots — a drive, a power plant, a sensor, a compute core, armour, a
weapon, a utility — and the shipyard listed every one of them as a name, a
tonnage and a sentence.

The claim a picture has to make here is narrower than for a hull or an
organism, and worth stating so the shapes are not asked to do more than they
can. A fitting is a component: at a glance a captain needs

- **what kind of thing it is** — the slot, which is the silhouette,
- **whose yard it came out of** — the family, which is the colour,
- **and roughly how much of the hull it will eat** — the mass, which is bulk.

Not "which of the eighteen defensive fittings is this". Eighteen plates cannot
be eighteen pictures and pretending otherwise would be the same lie as five
silhouettes across thirty-five hull classes, in the other direction: a
distinction drawn where none exists. What the picture *does* separate is a
railgun from a radiator, and a Yards weld from a grown organ.

Three marks carry the rest, and each is a field the card already prints:
something with a `wpn` has a barrel, something with an `ability` has an
emitter, and something `civilian` has no hardpoint at all.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models3d import (CHLORO, GOLD, LUMEN, PLATE, PLATE_DARK, ROCK,
                       ROCK_DARK, WARN, _box, _build, _cap, _tube)
from .part_types import SLOT_ORDER
from .parts import PARTS

#: Whose yard, in colour. `any` is a fitting nobody's tradition owns — a
#: standard part that bolts to anything — and reads as plain plate.
YARD = {
    "grown": (CHLORO, "#2f7d4a"),
    "fabricated": (GOLD, "#7d6430"),
    "synthetic": (LUMEN, "#2b7d79"),
    "xeno": (WARN, "#7d3a30"),
    "any": (PLATE, PLATE_DARK),
}
DEFAULT_YARD = (PLATE, PLATE_DARK)

#: What a fitting's own tonnage does to its build, as a share either way.
#: The lightest part in the game is 4 t and the heaviest 60; drawn at one size
#: they would all be the same box in different paint.
BULK_SPREAD = 0.5

#: The tonnage a fitting is authored at — the median of the eighty-four.
TYPICAL_T = 20.0


def bulk_of(part) -> float:
    """How big this fitting reads, from what it actually masses."""
    mass = max(0.5, float(getattr(part, "mass", TYPICAL_T) or TYPICAL_T))
    off = (mass / TYPICAL_T) ** (1.0 / 3.0) - 1.0
    return 1.0 + max(-BULK_SPREAD, min(BULK_SPREAD, off))


# ── one silhouette per slot ────────────────────────────────────────────────

def _drive(light, dark, bulk) -> list:
    """A bell. Everything that pushes ends in one."""
    return [_tube(0.16 * bulk, 0.42 * bulk, 0.20 * bulk, 0.10 * bulk, 12, 0,
                  light, dark),
            _tube(0.20 * bulk, 0.10 * bulk, 0.52 * bulk, -0.46 * bulk, 12, 0,
                  light, dark),
            _cap(0.16 * bulk, 0.42 * bulk, 12, 0, light, True)]


def _power(light, dark, bulk) -> list:
    """A cell with radiating fins: the one part whose problem is heat."""
    out = [_tube(0.26 * bulk, -0.34 * bulk, 0.26 * bulk, 0.34 * bulk, 10, 0,
                 light, dark),
           _cap(0.26 * bulk, 0.34 * bulk, 10, 0, light, True),
           _cap(0.26 * bulk, -0.34 * bulk, 10, 0, dark, False)]
    for i in range(6):
        turn = math.tau * i / 6
        out.append(_box(0.30 * bulk, 0.02, 0.24 * bulk, dark, dark,
                        dx=0.42 * bulk * math.cos(turn),
                        dy=0.42 * bulk * math.sin(turn)))
    return out


def _sensor(light, dark, bulk) -> list:
    """A dish on a gimbal, pointed at whatever you asked about."""
    rows = [(0.08 * bulk, 0.0), (0.30 * bulk, 0.16 * bulk),
            (0.52 * bulk, 0.40 * bulk)]
    out = [_tube(a[0], a[1], b[0], b[1], 14, 0, light, dark)
           for a, b in zip(rows, rows[1:])]
    out.append(_box(0.03, 0.03, 0.22 * bulk, dark, dark, dz=0.24 * bulk))
    out.append(_box(0.14 * bulk, 0.14 * bulk, 0.10 * bulk, dark, dark,
                    dz=-0.22 * bulk))
    return out


def _compute(light, dark, bulk) -> list:
    """A rack of cards. Nothing about thinking looks like anything."""
    out = [_box(0.30 * bulk, 0.20 * bulk, 0.34 * bulk, dark, dark)]
    for i in range(5):
        out.append(_box(0.28 * bulk, 0.012, 0.026, light, light,
                        dy=0.21 * bulk, dz=(i - 2) * 0.12 * bulk))
    return out


def _defence(light, dark, bulk) -> list:
    """Plate. Layered, angled, and mostly in the way of something."""
    out = []
    for i in range(3):
        out.append(_box(0.44 * bulk - i * 0.06, 0.34 * bulk - i * 0.05, 0.05,
                        light if i % 2 else dark, dark,
                        dz=(i - 1) * 0.14 * bulk))
    return out


def _weapon(light, dark, bulk) -> list:
    """A mount and a barrel down it."""
    return [_box(0.20 * bulk, 0.20 * bulk, 0.20 * bulk, dark, dark,
                 dz=-0.26 * bulk),
            _tube(0.09 * bulk, -0.10 * bulk, 0.07 * bulk, 0.52 * bulk, 9, 0,
                  light, dark),
            _tube(0.13 * bulk, -0.14 * bulk, 0.13 * bulk, 0.02 * bulk, 9, 0,
                  dark, dark)]


def _utility(light, dark, bulk) -> list:
    """A can with fittings on it. Everything that is not one of the above."""
    out = [_tube(0.24 * bulk, -0.30 * bulk, 0.24 * bulk, 0.30 * bulk, 8, 0,
                 light, dark),
           _cap(0.24 * bulk, 0.30 * bulk, 8, 0, light, True),
           _cap(0.24 * bulk, -0.30 * bulk, 8, 0, dark, False)]
    for i in range(4):
        turn = math.tau * i / 4 + 0.5
        out.append(_box(0.10 * bulk, 0.05, 0.05, dark, dark,
                        dx=0.32 * bulk * math.cos(turn),
                        dy=0.32 * bulk * math.sin(turn), dz=0.14 * bulk))
    return out


SHAPES = {"drive": _drive, "power": _power, "sensor": _sensor,
          "compute": _compute, "defence": _defence, "weapon": _weapon,
          "utility": _utility}
DEFAULT_SLOT = "utility"


# ── what it does, on top of what it is ─────────────────────────────────────

def _barrel(light, dark, bulk) -> list:
    """It fires. A longer tube than the mount alone would need."""
    return [_tube(0.05 * bulk, 0.48 * bulk, 0.045 * bulk, 0.86 * bulk, 8, 0,
                  WARN, dark),
            _box(0.09 * bulk, 0.09 * bulk, 0.04, WARN, dark, dz=0.88 * bulk)]


def _emitter(light, dark, bulk) -> list:
    """It does something on command: an emitter ring, lit."""
    return [_tube(0.34 * bulk, 0.30 * bulk, 0.34 * bulk, 0.36 * bulk, 14, 0,
                  LUMEN, dark)]


def _softened(light, dark, bulk) -> list:
    """No hardpoint. A civilian fitting is a housing, not a mount."""
    return [_tube(0.30 * bulk, -0.36 * bulk, 0.34 * bulk, -0.30 * bulk, 12, 0,
                  dark, dark)]


@dataclass(frozen=True)
class Fitting:
    """One part's picture, and what it was built from."""

    id: str
    mesh: tuple
    slot: str
    marks: tuple


def build(part) -> Fitting:
    """One fitting, from its slot, its yard, its tonnage and what it does."""
    slot = getattr(part, "slot", "") or DEFAULT_SLOT
    light, dark = YARD.get(getattr(part, "family", "any"), DEFAULT_YARD)
    bulk = bulk_of(part)
    maker = SHAPES.get(slot, SHAPES[DEFAULT_SLOT])
    pieces = list(maker(light, dark, bulk))
    marks = []
    if getattr(part, "wpn", None) is not None:
        pieces.extend(_barrel(light, dark, bulk))
        marks.append("barrel")
    if getattr(part, "ability", None) is not None:
        pieces.extend(_emitter(light, dark, bulk))
        marks.append("emitter")
    if getattr(part, "civilian", False):
        pieces.extend(_softened(light, dark, bulk))
        marks.append("housing")
    return Fitting(id=part.id, mesh=_build([(v, f) for v, f in pieces]),
                   slot=slot, marks=tuple(marks))


#: Every part, built once at import.
FITTINGS: dict = {p.id: build(p) for p in PARTS}

#: One of each slot, at a standard build, for comparing the silhouettes
#: without a family's paint or a tonnage getting in the way.
BY_SLOT: dict = {slot: _build([(v, f) for v, f in
                               SHAPES[slot](PLATE, PLATE_DARK, 1.0)])
                 for slot in SLOT_ORDER if slot in SHAPES}

