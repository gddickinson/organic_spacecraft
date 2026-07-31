"""What a machine looks like, built out of what it is for.

Twenty classes and no pictures: the Machines tab was the last catalogue page in
the game that was a wall of text, which is exactly where `works3d` came in and
the same fix applies. Nothing here is hand-drawn — a class's shape is read off
its own entry in `data/robots.py`, so the portrait and the specification are
the same document and a new class gets a body without anybody drawing one.

The vocabulary is morphological rather than decorative, and it is the one real
robotics uses: **what it stands on, what it works with, and what it senses
with.** A frame that lifts has an arm. One that walks a holding has legs. One
that is thrown at a body and left has thrusters and no legs at all. One that is
worn has a harness and no body of its own. A mind racked in a hold has neither
— which is the point of it.

Autonomy shows in the sensing. A teleoperated frame carries a relay mast and
nothing else; a goal-directed one carries a sensor head, because deciding for
itself is what it is *for*, and the thing that decides needs something to
decide with. That is the same reading `sim/robots.grip` runs on, drawn.

Authored nose along +z like everything else in this package, about a unit tall.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models3d import (CHLORO, GOLD, LUMEN, PLATE, PLATE_DARK, ROCK,
                       ROCK_DARK, WARN, _box, _build, _cap, _tube)
from .robots import ROBOTS
from .works3d import ACCENT, DEFAULT_ACCENT

# ── the geometry, once ─────────────────────────────────────────────────────

#: The trunk every machine that has one is built around.
TRUNK_R = 0.20
TRUNK_Z = 0.34
#: How far a limb reaches, and how thick it is.
LIMB = 0.46
LIMB_R = 0.05
#: Where a sensor head or a relay mast sits.
HEAD_Z = 0.52
#: A drone's thruster ring.
DRIVE_R = 0.30
DRIVE_Z = -0.42


#: What a machine's own tonnage does to its build, as a share either way.
#: A Loader Exoframe is 1.2 t and an Ossuary Frame is 14; drawn at one size
#: they were the same picture with different paint. Both figures are printed on
#: the card, so the portrait cannot disagree with the specification.
BULK_SPREAD = 0.55

#: The tonnage a body is authored at — the median of the twenty, measured.
TYPICAL_T = 2.5


def bulk_of(klass) -> float:
    """How heavy this class reads, from what it actually masses."""
    mass = max(0.1, float(getattr(klass, "mass_t", TYPICAL_T) or TYPICAL_T))
    off = (mass / TYPICAL_T) ** (1.0 / 3.0) - 1.0
    return 1.0 + max(-BULK_SPREAD, min(BULK_SPREAD, off))


def _trunk(accent: str, bulk: float = 1.0, family: str = "fabricated") -> list:
    """A body, in the shape its yard builds them.

    Three differences, all read off the card, because four pairs of classes
    came out of the first draft as the same silhouette in different paint —
    and a difference that is only paint is the defect `berths3d` opens with.

    - **A welded frame is a can.** Straight, capped, and obviously assembled.
    - **A grown one is segmented**, and tapers, because it was gestated.
    - **A recording's is slender**, because there is very little in it.
    """
    r = TRUNK_R * bulk
    if family == "grown":
        rows = [(r * 0.72, -TRUNK_Z), (r * 1.06, -TRUNK_Z * 0.4),
                (r * 0.94, TRUNK_Z * 0.35), (r * 0.58, TRUNK_Z)]
        out = [_tube(a[0], a[1], b[0], b[1], 10, 0, PLATE, PLATE_DARK)
               for a, b in zip(rows, rows[1:])]
        out.append(_cap(r * 0.58, TRUNK_Z, 10, 0, PLATE, True))
        out.append(_cap(r * 0.72, -TRUNK_Z, 10, 0, PLATE_DARK, False))
    elif family == "synthetic":
        out = [_tube(r * 0.66, -TRUNK_Z, r * 0.60, TRUNK_Z, 8, 0,
                     PLATE, PLATE_DARK),
               _cap(r * 0.60, TRUNK_Z, 8, 0, PLATE, True),
               _cap(r * 0.66, -TRUNK_Z, 8, 0, PLATE_DARK, False)]
    else:
        out = [_tube(r, -TRUNK_Z, r * 0.86, TRUNK_Z, 9, 0, PLATE, PLATE_DARK),
               _cap(r * 0.86, TRUNK_Z, 9, 0, PLATE, True),
               _cap(r, -TRUNK_Z, 9, 0, PLATE_DARK, False)]
    out.append(_box(r * 1.06, 0.03, 0.04, accent, PLATE_DARK,
                    dz=TRUNK_Z * 0.4))
    return out


def _arm(accent: str, bulk: float = 1.0) -> list:
    """A manipulator: the thing a frame that lifts is mostly made of.

    Scaled by the class's own tonnage, because the trunk alone was not enough:
    with the body the only thing bulk touched, a 2 t Hullwright and a 4 t
    Myrmidon shared **95%** of their outline. Limbs are most of what a machine
    of this shape *is* on the screen, so that is where a heavy frame has to
    read heavy.
    """
    out = []
    reach = LIMB * bulk
    thick = LIMB_R * bulk
    for side in (-1.0, 1.0):
        out.append(_box(reach * 0.5, thick, thick, PLATE, PLATE_DARK,
                        dx=side * (TRUNK_R * bulk + reach * 0.5),
                        dz=TRUNK_Z * 0.5))
        out.append(_box(thick, thick, reach * 0.42, PLATE, PLATE_DARK,
                        dx=side * (TRUNK_R * bulk + reach * 0.92),
                        dz=TRUNK_Z * 0.5 - reach * 0.42))
        out.append(_box(0.07 * bulk, 0.05 * bulk, 0.05 * bulk, accent,
                        PLATE_DARK,
                        dx=side * (TRUNK_R * bulk + reach * 0.92),
                        dz=TRUNK_Z * 0.5 - reach * 0.86))
    return out


def _legs(accent: str, bulk: float = 1.0) -> list:
    """Four of them, splayed. What walks a holding rather than flying to it.

    A heavy frame stands wide and long. Same reasoning as the arms: the stance
    is the outline, so it is where tonnage has to show.
    """
    out = []
    stance = 0.24 * bulk
    drop = 0.26 * bulk
    for i in range(4):
        angle = math.tau * i / 4 + 0.78
        dx, dy = stance * math.cos(angle), stance * math.sin(angle)
        out.append(_box(LIMB_R * bulk, LIMB_R * bulk, drop, PLATE, PLATE_DARK,
                        dx=dx, dy=dy, dz=-TRUNK_Z - drop * 0.78))
        out.append(_box(0.07 * bulk, 0.07 * bulk, 0.035, accent, ROCK_DARK,
                        dx=dx * 1.3, dy=dy * 1.3,
                        dz=-TRUNK_Z - drop * 1.7))
    return out


def _thrusters(accent: str) -> list:
    """A cold-gas ring. Nothing that flies to its work has feet."""
    out = [_tube(DRIVE_R, DRIVE_Z - 0.05, DRIVE_R, DRIVE_Z + 0.05, 12, 0,
                 PLATE, PLATE_DARK)]
    for i in range(4):
        angle = math.tau * i / 4
        out.append(_box(0.05, 0.05, 0.07, accent, WARN,
                        dx=DRIVE_R * math.cos(angle),
                        dy=DRIVE_R * math.sin(angle), dz=DRIVE_Z - 0.09))
    return out


def _head(accent: str) -> list:
    """A sensor head: what a machine that decides for itself decides with."""
    return [_tube(0.13, HEAD_Z - 0.09, 0.11, HEAD_Z + 0.07, 8, 0,
                  PLATE, PLATE_DARK),
            _cap(0.11, HEAD_Z + 0.07, 8, 0, PLATE, True),
            _box(0.12, 0.035, 0.035, accent, LUMEN, dz=HEAD_Z)]


def _mast(accent: str) -> list:
    """A relay mast. A frame somebody else is flying needs to hear them."""
    # Short. At 0.26 it overtopped every other feature on the card and each
    # teleoperated class read as a spike with a machine under it.
    return [_box(0.020, 0.020, 0.13, PLATE, PLATE_DARK, dz=HEAD_Z + 0.02),
            _box(0.05, 0.05, 0.03, accent, WARN, dz=HEAD_Z + 0.17)]


def _dish(accent: str) -> list:
    """A survey dish, for a machine whose work is reading things."""
    rows = [(0.07, HEAD_Z), (0.18, HEAD_Z + 0.08), (0.30, HEAD_Z + 0.20)]
    out = [_tube(a[0], a[1], b[0], b[1], 12, 0, PLATE, PLATE_DARK)
           for a, b in zip(rows, rows[1:])]
    out.append(_box(0.025, 0.025, 0.11, accent, PLATE_DARK, dz=HEAD_Z + 0.14))
    return out


def _rig(accent: str) -> list:
    """Cutting heads, for something that eats rock."""
    out = []
    for i in range(3):
        angle = math.tau * i / 3 + 0.4
        dx, dy = 0.22 * math.cos(angle), 0.22 * math.sin(angle)
        out.append(_tube(0.10, -TRUNK_Z - 0.46, 0.06, -TRUNK_Z + 0.02, 7, 0,
                         ROCK, ROCK_DARK))
        verts, faces = out[-1]
        out[-1] = ([(x + dx, y + dy, z) for x, y, z in verts], faces)
        out.append(_box(0.07, 0.07, 0.05, accent, ROCK_DARK,
                        dx=dx, dy=dy, dz=-TRUNK_Z - 0.50))
    return out


def _hold(accent: str) -> list:
    """A cargo cradle slung under it."""
    return [_box(0.30, 0.18, 0.09, PLATE_DARK, PLATE_DARK, dz=-TRUNK_Z - 0.14),
            _box(0.32, 0.03, 0.03, accent, PLATE_DARK, dz=-TRUNK_Z - 0.24)]


def _guns(accent: str) -> list:
    """A mount. The one class here whose work is being shot at."""
    # Held clear of the graft band. At `TRUNK_Z * 0.2` the mount sat exactly
    # where a hybrid's spokes already are, so a Wet-wired Gunner rendered
    # **100%** the same as a Graft-Pilot — the difference drawn and invisible,
    # for the third time in this package.
    out = [_box(0.44, 0.07, 0.07, accent, WARN, dz=TRUNK_Z * 0.66),
           _box(0.12, 0.12, 0.10, PLATE, PLATE_DARK, dz=TRUNK_Z * 0.66)]
    for side in (-1.0, 1.0):
        out.append(_box(0.06, 0.09, 0.09, PLATE_DARK, WARN,
                        dx=side * 0.46, dz=TRUNK_Z * 0.66))
    return out


def _harness(accent: str) -> list:
    """Worn, not sent: a frame with a person-shaped hole in it."""
    out = []
    for side in (-1.0, 1.0):
        out.append(_box(0.035, 0.035, 0.42, PLATE, PLATE_DARK,
                        dx=side * 0.17, dz=0.0))
        out.append(_box(0.035, 0.035, 0.24, PLATE, PLATE_DARK,
                        dx=side * 0.12, dz=-0.52))
        out.append(_box(0.09, 0.05, 0.04, accent, PLATE_DARK,
                        dx=side * 0.24, dz=0.30))
    out.append(_box(0.17, 0.03, 0.03, PLATE_DARK, PLATE_DARK, dz=0.22))
    return out


def _rack(accent: str) -> list:
    """A mind with no body. Cards in a frame, and that is the whole machine."""
    out = [_box(0.26, 0.15, 0.30, PLATE, PLATE_DARK)]
    for i in range(4):
        out.append(_box(0.24, 0.015, 0.02, accent, LUMEN,
                        dy=0.16, dz=0.20 - i * 0.13))
    return out


def _swarm(accent: str) -> list:
    """Many small pieces that will not be counted twice."""
    out = []
    for i in range(7):
        turn = 2.399 * i                  # the golden angle: never a pattern
        rise = 0.44 - 0.88 * ((i * 0.37) % 1.0)
        size = 0.07 + 0.06 * ((i * 0.53) % 1.0)
        out.append(_box(size, size * 0.5, size * 1.5, accent, ROCK_DARK,
                        dx=0.30 * math.cos(turn), dy=0.30 * math.sin(turn),
                        dz=rise))
    return out


def _hands(accent: str, bulk: float = 1.0) -> list:
    """A second pair of manipulators, low down.

    What a **level** buys, and level was the one figure on the card the first
    draft never drew: a Precentor is rated four and a Coral Tender two, they
    share every other part, and they rendered 89% alike. A senior machine has
    more to work with, which is what being senior means.
    """
    out = []
    reach = LIMB * 0.62 * bulk
    for side in (-1.0, 1.0):
        out.append(_box(reach * 0.5, LIMB_R * 0.8 * bulk, LIMB_R * 0.8 * bulk,
                        PLATE, PLATE_DARK,
                        dx=side * (TRUNK_R * bulk + reach * 0.5),
                        dz=-TRUNK_Z * 0.5))
        out.append(_box(0.06 * bulk, 0.045 * bulk, 0.045 * bulk, accent,
                        PLATE_DARK,
                        dx=side * (TRUNK_R * bulk + reach * 1.0),
                        dz=-TRUNK_Z * 0.5))
    return out


def _pack(accent: str) -> list:
    """A ventral pack: consumables for something going down a hole."""
    # Slung below rather than tucked behind: at the back of the trunk it was
    # inside the outline, and a Chorus Graft read identical to a Graft-Pilot.
    return [_box(0.19, 0.12, 0.11, PLATE_DARK, PLATE_DARK,
                 dz=-TRUNK_Z - 0.10, dy=-0.10),
            _box(0.06, 0.05, 0.05, accent, PLATE_DARK,
                 dz=-TRUNK_Z - 0.22, dy=-0.14)]


def _graft(accent: str) -> list:
    """Tissue on a chassis, and the loom that reads it."""
    out = [_tube(TRUNK_R * 1.15, -0.10, TRUNK_R * 1.15, 0.16, 12, 0,
                 CHLORO, ROCK_DARK)]
    for i in range(6):
        angle = math.tau * i / 6
        out.append(_box(0.13, 0.02, 0.02, accent, PLATE_DARK,
                        dx=TRUNK_R * 1.5 * math.cos(angle),
                        dy=TRUNK_R * 1.5 * math.sin(angle), dz=0.03))
    return out


PARTS = {
    "trunk": _trunk, "arm": _arm, "legs": _legs, "thrusters": _thrusters,
    "head": _head, "mast": _mast, "dish": _dish, "rig": _rig, "hold": _hold,
    "guns": _guns, "harness": _harness, "rack": _rack, "swarm": _swarm,
    "graft": _graft, "pack": _pack, "hands": _hands,
}

#: Which classes are a body at all. A mind racked in a hold and a swarm of
#: pieces are neither, and giving them a trunk would make them the same
#: silhouette as everything else — which is the whole defect being fixed.
BODILESS = ("anchorite", "shardling")

#: Worn rather than sent. The one class whose shape is a hole.
WORN = ("loader",)

#: The level at which a machine is given a second pair of manipulators. Four,
#: which on the twenty separates the six senior classes from the rest.
SENIOR = 4


def shape_of(klass) -> tuple:
    """Every part this class carries, read off what it is and what it does.

    In build order. Each line is a fact the card already prints — the family
    it came out of, the rung it is rated at, the duties it holds and the watch
    it can stand.
    """
    out = []
    if klass.id in WORN:
        out.append("harness")
    elif klass.id in BODILESS:
        out.append("rack" if "swarm" not in klass.name.lower() else "swarm")
        if klass.id == "shardling":
            out = ["swarm"]
    else:
        out.append("trunk")

    duties = set(klass.duties)
    if klass.family == "hybrid":
        out.append("graft")               # a person is in there somewhere
    if "cargo" in duties:
        out.append("hold")
    if "mine" in duties:
        out.append("rig")
    if {"repair", "works"} & duties and klass.id not in BODILESS:
        out.append("arm")
    if "survey" in duties:
        out.append("dish")
    if "ground" in duties:
        out.append("pack")            # it is going somewhere and coming back
    if klass.stat == "tactical":
        out.append("guns")
    # What it stands on. A machine that flies to its work has no feet, and a
    # drone is exactly the one that holds no watch and goes to the body.
    if klass.id not in BODILESS and klass.id not in WORN:
        if not klass.stat and {"survey", "repair"} & duties:
            out.append("thrusters")
        else:
            out.append("legs")
    # What being senior buys: a second pair of manipulators.
    if klass.level >= SENIOR and klass.id not in BODILESS and klass.id not in WORN:
        out.append("hands")
    # And what it senses with, which is the autonomy rung drawn.
    out.append("head" if klass.autonomy >= 3 else "mast")
    return tuple(out)


@dataclass(frozen=True)
class Body:
    """One class's machine: its mesh and the parts it was built from."""

    id: str
    mesh: tuple
    parts: tuple


def build(klass) -> Body:
    accent = ACCENT.get(klass.family, DEFAULT_ACCENT)
    parts = shape_of(klass)
    bulk = bulk_of(klass)
    pieces: list = []
    for part in parts:
        maker = PARTS.get(part)
        if maker is None:
            continue
        if part == "trunk":
            pieces.extend(maker(accent, bulk, klass.family))
        elif part in ("arm", "legs", "hands"):
            pieces.extend(maker(accent, bulk))
        else:
            pieces.extend(maker(accent))
    return Body(id=klass.id, mesh=_build([(v, f) for v, f in pieces]),
                parts=parts)


#: Every class, built once at import.
BODIES: dict = {k.id: build(k) for k in ROBOTS}


def mesh_for(look: str):
    got = BODIES.get(look)
    return got.mesh if got is not None else None


def parts_of(look: str) -> tuple:
    got = BODIES.get(look)
    return got.parts if got is not None else ()
