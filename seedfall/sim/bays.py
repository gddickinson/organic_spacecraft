"""Structures you fly *into*, and what a hull can actually hit.

Two things, and they are the same thing seen from either end of the problem
`data/works3d.py` exposed. Plant one of each holding and measure where its
berths sit against the sphere the approach treats as solid:

    lichen_dome       0.60 km skin, berth at 0.56  ← inside
    gravid_nursery    0.55 km skin, berth at 0.37  ← inside
    arca_drum         2.50 km skin, berth at 2.16  ← inside
    ... seven of nineteen

Flown, not computed: a conn opened on an ARCA Habitat and driven straight in
reports **"ARCA Deepcut at 12 m/s — 3,995 m from mast 3. The frames took it."**
The biggest structure in the sector could not be docked with. Nor could a
GRAVID Nursery, an Orbital Drydock, a Fabricator Yard, a Free Port, a LICHEN
Dome or a CORAL Reef.

**A bounding radius is not a hull.** `radius_km` is how big a structure *is* —
what the window draws it at, what a captain reads on the card. What a ship can
strike is the solid middle: the keel and the core. Everything past that is
furniture — rings, masts, gantries, arms — and furniture is the thing you berth
against, so a berth outside the core and inside the bounding sphere is normal
rather than impossible. `hull_km` is the one door for that distinction.

**And some structures are meant to be flown into.** A drum a million people
live inside and a gestation shell that hands out finished hulls both have their
berths in the middle *on purpose*, and getting to one is not a matter of
tolerance — it is a corridor through an aperture, and missing the aperture is
hitting the rim. That is `mouth_of` and `in_corridor`, and it is the last piece
of #108: the structure grants the berth, sends the approach data, and for these
two the approach goes inside.
"""

from __future__ import annotations

import math

from ..data import works3d
from ..data.berths3d import berth_points
from ..data.models3d import attitude_of, place

#: How much of a structure's bounding radius is solid **when you must use the
#: way in** — a drum or a gestation shell, whose berths are deliberately deep
#: inside and are not supposed to be reachable by flying at the skin.
CORE_SHARE = 0.55

#: How far inside its nearest berth a structure's hull ends.
#:
#: A berth is a fitting on the *outside* of a structure, so the solid part
#: stops just short of it — and that is the whole rule, derived per structure
#: from the mesh's own numbers rather than from one share applied to all.
#:
#: The first draft did apply one share, 0.55, to everything. It made the seven
#: unreachable holdings reachable and it also halved the solid radius of a
#: quay, a hub and a Weave gate, whose berths sit at 0.91 to 1.11 and never
#: needed it — and three checks caught it at once: a hull driven into a station
#: at 45 m/s came away `adrift`, because the thing it was aimed at had quietly
#: shrunk out from under it. Ramming a hub is a real act with real consequences
#: for both hulls, and a constant chosen for one problem broke it.
SKIN_MARGIN = 0.95

#: Which parts of a `works3d` body mean "you go inside this one".
#:
#: Read off the shape rather than listed here, so a structure drawn with a
#: drum or a gestation shell is one you can fly into and nobody has to
#: remember to add it to a second table.
BAY_PARTS = ("drum", "womb")

#: How wide the way in is, as a share of the structure's radius, and how far
#: down the axis the aperture plane sits.
#:
#: Both are the mesh's own numbers: a gestation shell's mouth is `WOMB_MOUTH`
#: at `WOMB_Z`, and a drum is open across `DRUM_R` at `DRUM_Z`. Taken from
#: `works3d` so the hole a pilot flies through is the hole that is drawn.
#:
#: **The bore has to be narrower than the solid part**, or there is no rim to
#: miss and the corridor means nothing. Measured on the first draft: a drum at
#: 0.78 of its radius gave a 3.2 km way in through a 2.7 km solid middle, so
#: every off-axis approach simply flew past the structure. `test_bay` holds
#: the two apart.
def mouth_of(look: str):
    """Where the way in is, in model space: (bore, plane along +z).

    None for a structure with no bay. The aperture faces the model's +z, which
    is the axis everything in this package is authored along, and the same axis
    `models3d.place` turns when the structure comes round.
    """
    parts = works3d.WORKS[look].traits if look in works3d.WORKS else ()
    if "drum" in parts:
        return works3d.DRUM_R * 0.50, works3d.DRUM_Z
    if "womb" in parts:
        return works3d.WOMB_MOUTH * 1.35, works3d.WOMB_Z
    return None


def is_bay(look: str) -> bool:
    """Whether this sort of structure is one a hull goes inside."""
    got = works3d.WORKS.get(look)
    return bool(got and set(BAY_PARTS) & set(got.traits))


def hull_km(target) -> float:
    """**What a hull can actually strike**, in km from the structure's centre.

    The one door, and there was none: `sim/outcome` tested `r <= radius_km`,
    which is the *bounding* sphere — the size the thing is drawn at, furniture
    and all. Seven structures had berths inside it and could not be docked
    with at any speed.

    A world is different and is left alone: a planet has no furniture, and its
    radius is its ground.
    """
    radius = float(getattr(target, "radius_km", 0.0) or 0.0)
    if getattr(target, "kind", "") == "body":
        return radius
    look = getattr(target, "berth", "") or ""
    if is_bay(look):
        # A bay is solid: that is what makes the aperture matter.
        return radius * CORE_SHARE
    points = berth_points(look)
    if not points:
        return radius
    nearest = min(math.dist(at, (0.0, 0.0, 0.0)) for _name, at in points)
    return radius * min(1.0, nearest * SKIN_MARGIN)


def bore_km(target) -> float:
    """How wide the way in is, in km. Zero for a structure with no bay."""
    got = mouth_of(getattr(target, "berth", "") or "")
    if got is None:
        return 0.0
    bore, _plane = got
    return bore * float(getattr(target, "radius_km", 0.0) or 0.0)


def axis(target, spin: float = 0.0) -> tuple:
    """The way in, as a unit vector in the approach's frame.

    Through `models3d.place`, which is the one door for a model's rotation —
    the same one `sim/moorings.points` turns a berth by and `ui/viewport` draws
    the mesh by. An aperture computed any other way would be a hole in a
    different place from the hole on the screen, which is the fault this
    package has been fixed for twice.
    """
    sort = getattr(target, "berth", "") or ""
    _rate, tilt = attitude_of("anchorage", sort)
    turned = place((0.0, 0.0, 1.0), spin, tilt)
    length = math.dist(turned, (0.0, 0.0, 0.0)) or 1.0
    return tuple(component / length for component in turned)


def in_corridor(conn, spin: float = 0.0) -> bool:
    """Is the hull inside the way in, rather than against the skin?

    The test is the honest one: how far the ship is **off the axis** of the
    aperture, against the bore. On the axis you are in the corridor at any
    depth; a bore's width off it you are at the rim, and the rim is structure.
    """
    target = getattr(conn, "target", None)
    if target is None or not is_bay(getattr(target, "berth", "") or ""):
        return False
    bore = bore_km(target)
    if bore <= 0:
        return False
    way = axis(target, spin)
    at = tuple(conn.pos)
    along = sum(a * b for a, b in zip(at, way))
    if along <= 0:
        return False              # astern of the mouth: that is the far skin
    off = math.sqrt(max(0.0, sum(c * c for c in at) - along * along))
    return off <= bore


def berths_inside(target) -> list:
    """The berths of this structure that sit within its solid part.

    What makes a bay a bay rather than a wide berth: these are the ones no
    approach could reach without the corridor.
    """
    sort = getattr(target, "berth", "") or ""
    radius = float(getattr(target, "radius_km", 0.0) or 0.0)
    solid = hull_km(target)
    return [(name, at) for name, at in berth_points(sort)
            if math.dist(at, (0.0, 0.0, 0.0)) * radius < solid]


def line(target) -> str:
    """What a structure with a bay tells an approaching hull."""
    if not is_bay(getattr(target, "berth", "") or ""):
        return ""
    bore = bore_km(target)
    return (f"{target.name} is open along its axis. The way in is "
            f"{bore * 2000:,.0f} m across; hold the centreline and mind the "
            "rim.")
