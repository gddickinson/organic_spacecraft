"""What each family of hull looks like, and where things mount on it.

Five families, five silhouettes. A grown hull is a prolate organism with an
equatorial docking ridge and a radiator bloom aft; a Yards hull is a welded
spine with a slab bow; a hybrid is a grown body in a fabricated cradle; a Dry
Choir frame is a crewless lattice around an instrument core; a xeno hull is not
symmetrical and does not explain itself.

Only shape lives here. Which parts a hull will take is `ACCEPTS` in
`hull_types.py`, and what any of it does is `sim/ship.py`. The vocabulary
follows `models3d/build.py` so that the in-game model and the exported one read
as the same ship.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Tint keys, resolved by whatever is drawing. Named for what they mean.
LIVING = "living"        # grown tissue
SYSTEM = "system"        # engineered machinery
STRUCT = "struct"        # structure, docking, armour plate
WARM = "warm"            # radiators, drives under load
ROCK = "rock"            # rock, ore, inert mass
VOID = "void"            # cutaway interior


@dataclass(frozen=True)
class Mount:
    """Where a slot's parts sit on this hull, and which way they face."""
    at: tuple
    facing: tuple
    size: float = 1.0


@dataclass(frozen=True)
class HullForm:
    id: str
    #: Half-length along +z (fore) and equatorial radius.
    length: float
    beam: float
    #: Fore narrows by this fraction — the A < C < B beam law of the drawings.
    taper: float
    skin: str
    #: (rings, segments) for the body. A grown hull is smooth because it was
    #: gestated; a Yards hull is coarse because it was welded out of plate,
    #: and drawing both at the same resolution made every family the same
    #: ship in a different colour.
    facets: tuple = (14, 22)
    mounts: dict = field(default_factory=dict)
    #: Extra fixed furniture, as (kind, parameters). Read by `sim/plans.py`.
    furniture: tuple = ()


def _around(count: int, radius: float, z: float, size: float,
            outward: bool = True) -> list:
    """`count` mounts spaced around the hull at height z."""
    import math
    out = []
    for index in range(count):
        angle = 2 * math.pi * index / count + 0.3
        at = (radius * math.cos(angle), radius * math.sin(angle), z)
        facing = (math.cos(angle), math.sin(angle), 0.0) if outward else \
                 (0.0, 0.0, 1.0)
        out.append(Mount(at, facing, size))
    return out


GROWN = HullForm(
    id="grown", length=1.0, beam=0.42, taper=0.14, skin=LIVING,
    facets=(16, 24),
    mounts={
        "drive":   [Mount((0, 0, -1.02), (0, 0, -1), 1.0)],
        "power":   _around(2, 0.30, -0.45, 0.8),
        "sensor":  [Mount((0, 0, 1.00), (0, 0, 1), 0.9)],
        "compute": [Mount((0, 0, 0.42), (0, 0, 1), 0.7)],
        "defence": _around(3, 0.40, 0.05, 0.8),
        "weapon":  _around(4, 0.38, 0.30, 0.7),
        "utility": _around(3, 0.34, -0.18, 0.8),
    },
    furniture=(("ridge", 6), ("cap", 1), ("bloom", 8), ("root", 1)))

FABRICATED = HullForm(
    id="fabricated", length=1.0, beam=0.30, taper=-0.10, skin=STRUCT,
    facets=(6, 8),
    mounts={
        "drive":   [Mount((0, 0, -1.05), (0, 0, -1), 1.1)],
        "power":   _around(2, 0.26, -0.30, 0.8),
        "sensor":  [Mount((0, 0, 1.02), (0, 0, 1), 0.8)],
        "compute": [Mount((0, 0, 0.20), (0, 0, 1), 0.7)],
        "defence": _around(4, 0.32, -0.05, 0.8),
        "weapon":  _around(4, 0.30, 0.45, 0.8),
        "utility": _around(3, 0.28, -0.60, 0.8),
    },
    furniture=(("spine", 1), ("slab", 1), ("fins", 4)))

HYBRID = HullForm(
    id="hybrid", length=1.0, beam=0.38, taper=0.06, skin=LIVING,
    facets=(10, 12),
    mounts={
        "drive":   [Mount((0, 0, -1.03), (0, 0, -1), 1.0)],
        "power":   _around(2, 0.30, -0.40, 0.8),
        "sensor":  [Mount((0, 0, 1.00), (0, 0, 1), 0.85)],
        "compute": [Mount((0, 0, 0.34), (0, 0, 1), 0.7)],
        "defence": _around(3, 0.38, 0.00, 0.8),
        "weapon":  _around(4, 0.36, 0.34, 0.75),
        "utility": _around(3, 0.32, -0.20, 0.8),
    },
    furniture=(("ridge", 4), ("cradle", 3), ("bloom", 5)))

SYNTHETIC = HullForm(
    id="synthetic", length=1.0, beam=0.26, taper=0.0, skin=SYSTEM,
    facets=(8, 6),
    mounts={
        "drive":   [Mount((0, 0, -1.00), (0, 0, -1), 0.9)],
        "power":   _around(3, 0.24, -0.25, 0.7),
        "sensor":  [Mount((0, 0, 1.06), (0, 0, 1), 1.1)],
        "compute": _around(2, 0.22, 0.30, 0.9),
        "defence": _around(3, 0.28, -0.05, 0.7),
        "weapon":  _around(3, 0.26, 0.50, 0.7),
        "utility": _around(2, 0.24, -0.55, 0.7),
    },
    furniture=(("lattice", 6), ("core", 1)))

XENO = HullForm(
    id="xeno", length=1.0, beam=0.44, taper=0.22, skin=SYSTEM,
    facets=(11, 9),
    mounts={
        "drive":   [Mount((0.10, 0, -0.98), (0.1, 0, -1), 1.0)],
        "power":   _around(2, 0.32, -0.35, 0.9),
        "sensor":  [Mount((-0.08, 0, 0.96), (-0.1, 0, 1), 1.0)],
        "compute": [Mount((0, 0.10, 0.30), (0, 1, 0.3), 0.8)],
        "defence": _around(3, 0.42, 0.10, 0.9),
        "weapon":  _around(3, 0.40, 0.40, 0.8),
        "utility": _around(3, 0.36, -0.22, 0.8),
    },
    furniture=(("shards", 7), ("bloom", 4)))

FORMS = {"grown": GROWN, "fabricated": FABRICATED, "hybrid": HYBRID,
         "synthetic": SYNTHETIC, "xeno": XENO}


def form_for(family: str) -> HullForm:
    return FORMS.get(family, GROWN)


#: How each slot's parts are drawn, so a sensor never looks like a gun.
SLOT_SHAPE = {
    "drive":   ("nozzle", WARM),
    "power":   ("pod", SYSTEM),
    "sensor":  ("mast", SYSTEM),
    "compute": ("pod", SYSTEM),
    "defence": ("plate", STRUCT),
    "weapon":  ("barrel", STRUCT),
    "utility": ("pod", LIVING),
}
