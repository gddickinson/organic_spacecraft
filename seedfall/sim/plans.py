"""The ship as a thing you can look at: hull, fittings, hold, berths, damage.

Everything on the ship screen was already true and none of it was visible. You
could read that a Polyp Laboratory was fitted and that the ablative layer was at
41%, and still have no picture of the machine you were flying — where the
laboratory sat, which end took the hit, how full the hold was.

This builds that picture out of the actual ship: its chassis decides the
silhouette, every fitted part is placed at its slot's mount, the hold fills from
the floor with what is really in it, and each of the six layers is tinted by how
much of it is left. Refit something and the model changes, because the model is
the fitted list.

Geometry only — `core/solid.py` knows nothing about ships, this knows nothing
about drawing. What comes back is a list of `Solid`s and a legend.
"""

from __future__ import annotations

import math

from ..core.solid import (Solid, box, centre_of, ellipsoid, orient, petal,
                          ring_of, tube)
from ..data.chassis import CHASSIS_BY_ID
from ..data.commodities import BY_ID as COMMODITIES_BY_ID
from ..data.hullforms import (LIVING, ROCK, SLOT_SHAPE, STRUCT, SYSTEM, WARM,
                              form_for)
from ..data.parts import PARTS_BY_ID
from .ship import cargo_used, stats as ship_stats

#: Layers run outermost first in `data/hull_types.py`; so does the drawing.
LAYER_TINT = (STRUCT, STRUCT, LIVING, LIVING, SYSTEM, SYSTEM)


def _hull(form, chassis) -> Solid:
    rings, segments = form.facets
    faces = ellipsoid(form.beam, form.beam, form.length, form.skin,
                      tag="hull", rings=rings, segments=segments,
                      taper=form.taper)
    return Solid("hull", chassis.name, faces,
                 f"{chassis.mass_t:,.0f} t · {chassis.crew} berths")


def _radius_at(form, z: float) -> float:
    """The hull's equatorial radius at height z, tapered as the drawings are."""
    inside = max(1e-4, 1.0 - (z / form.length) ** 2)
    return form.beam * (1 - form.taper * z / form.length) * math.sqrt(inside)


def _furniture(form) -> list:
    """The fixed anatomy of the family — ridge, cap, bloom, spine, lattice."""
    out = []
    for kind, count in form.furniture:
        if kind == "ridge":
            faces = ring_of(form.beam * 1.02, form.beam * 0.045, STRUCT,
                            tag="ridge", segments=24)
            for index in range(count):
                angle = 2 * math.pi * index / count
                at = (_radius_at(form, 0) * math.cos(angle),
                      _radius_at(form, 0) * math.sin(angle), 0.0)
                faces += orient(tube((0, 0, -0.02), (0, 0, 0.03),
                                     form.beam * 0.16, SYSTEM, tag="ridge"),
                                (math.cos(angle), math.sin(angle), 0.0), at)
            out.append(Solid("ridge", f"docking ridge · {count} sphincters",
                             faces, "Where anything else comes aboard."))
        elif kind == "cap":
            faces = ellipsoid(form.beam * 0.36, form.beam * 0.36,
                              form.beam * 0.28, SYSTEM, tag="cap",
                              at=(0, 0, form.length * 0.96))
            faces += tube((0, 0, form.length * 1.04),
                          (0, 0, form.length * 1.30), 0.012, SYSTEM, tag="cap")
            out.append(Solid("cap", "phototropic cap", faces,
                             "Eye-lens, clarified windows, sensor mast."))
        elif kind == "bloom":
            faces = []
            for index in range(count):
                angle = 2 * math.pi * index / count
                direction = (math.sin(1.02) * math.cos(angle),
                             math.sin(1.02) * math.sin(angle), -math.cos(1.02))
                faces += petal(direction, form.length * 0.62, form.beam * 0.5,
                               WARM, at=(0, 0, -form.length * 1.0), tag="bloom")
            out.append(Solid("bloom", f"radiator bloom · {count} petals", faces,
                             "Sheds heat. Folds when you are running quiet."))
        elif kind == "root":
            hub = (0, 0, -form.length * 1.34)
            faces = tube((0, 0, -form.length * 1.06), hub, form.beam * 0.12,
                         SYSTEM, tag="root")
            faces += ellipsoid(form.beam * 0.42, form.beam * 0.42,
                               form.beam * 0.36, ROCK, at=(0, 0, -form.length * 1.58),
                               tag="root", rings=7, segments=12)
            out.append(Solid("root", "mining root", faces,
                             "Reaches down and holds while the rig works."))
        elif kind == "spine":
            out.append(Solid("spine", "keel spine",
                             tube((0, 0, -form.length * 1.16),
                                  (0, 0, form.length * 1.10),
                                  form.beam * 0.22, STRUCT, tag="spine",
                                  segments=6),
                             "Welded, not grown. It will not mend itself."))
        elif kind == "slab":
            out.append(Solid("slab", "bow slab",
                             box(form.beam * 1.9, form.beam * 1.9,
                                 form.beam * 0.55, STRUCT,
                                 at=(0, 0, form.length * 0.80), tag="slab"),
                             "Armour where the shooting comes from."))
        elif kind in ("fins", "shards", "cradle", "lattice"):
            faces = []
            for index in range(count):
                angle = 2 * math.pi * index / count + 0.4
                direction = (math.cos(angle), math.sin(angle),
                             -0.35 if kind == "fins" else 0.2)
                faces += petal(direction, form.length * 0.45, form.beam * 0.4,
                               STRUCT if kind != "shards" else SYSTEM,
                               at=(0, 0, -form.length * 0.2), tag=kind)
            out.append(Solid(kind, kind, faces, ""))
        elif kind == "core":
            out.append(Solid("core", "instrument core",
                             ellipsoid(form.beam * 0.5, form.beam * 0.5,
                                       form.length * 0.4, SYSTEM, tag="core"),
                             "No berths. Nobody aboard to need them."))
    return out


def _seat(form, mount, size: float) -> tuple:
    """Slide a mount out onto the skin, so a fitting sits proud of the hull.

    The mounts are written as a radius and a height, which is the natural way
    to describe them and buries them: a pod at radius 0.34 inside a beam of
    0.42 is inside the ship. The hull is tapered, so where the skin *is*
    depends on the height, and only the model knows that.
    """
    x, y, z = mount.at
    flat = math.hypot(x, y)
    if flat < 1e-6:
        return mount.at                     # axial: nose and tail are already out
    skin = _radius_at(form, z) + size * 0.55
    return (x / flat * skin, y / flat * skin, z)


def _part_solid(part, mount, form) -> Solid:
    """One fitted part, drawn as the kind of thing it is."""
    shape, tint = SLOT_SHAPE.get(part.slot, ("pod", SYSTEM))
    size = form.beam * 0.34 * mount.size
    at, facing = _seat(form, mount, size), mount.facing
    if shape == "nozzle":
        faces = orient(tube((0, 0, 0), (0, 0, size * 2.0), size * 0.9, tint,
                            radius1=size * 1.35, tag=part.id), facing, at)
    elif shape == "mast":
        faces = orient(tube((0, 0, 0), (0, 0, size * 2.4), size * 0.18, tint,
                            tag=part.id), facing, at)
        faces += ellipsoid(size * 0.42, size * 0.42, size * 0.42, STRUCT,
                           at=(at[0] + size * 2.4 * facing[0],
                               at[1] + size * 2.4 * facing[1],
                               at[2] + size * 2.4 * facing[2]),
                           tag=part.id, rings=6, segments=10)
    elif shape == "barrel":
        faces = orient(tube((0, 0, 0), (0, 0, size * 1.9), size * 0.30, tint,
                            radius1=size * 0.22, tag=part.id), facing, at)
    elif shape == "plate":
        faces = orient(box(size * 2.4, size * 2.4, size * 0.45, tint,
                           tag=part.id), facing, at)
    else:                                    # pod
        faces = ellipsoid(size, size, size * 1.25, tint, at=at, tag=part.id,
                          rings=7, segments=12)
    return Solid(part.id, part.name, faces,
                 f"{part.slot} · {part.mass:g} t")


def _hold(ship, st, form) -> list:
    """The hold, filled from the floor with what is actually aboard."""
    out = []
    capacity = max(1.0, st.cargo)
    floor, ceiling = -form.length * 0.55, form.length * 0.30
    width = form.beam * 0.62
    out.append(Solid("hold", "cargo hold",
                     box(width * 2, width * 2, ceiling - floor, "void",
                         at=(0, 0, (floor + ceiling) / 2), tag="hold"),
                     f"{cargo_used(ship):.0f} of {capacity:.0f} t"))
    level = floor
    for cid, tonnes in sorted(ship.cargo.items(), key=lambda kv: -kv[1]):
        if tonnes <= 0:
            continue
        height = (ceiling - floor) * min(1.0, tonnes / capacity)
        if height < 0.004:
            continue
        commodity = COMMODITIES_BY_ID.get(cid)
        out.append(Solid(f"cargo:{cid}", commodity.name if commodity else cid,
                         box(width * 1.86, width * 1.86, height * 0.92, ROCK,
                             at=(0, 0, level + height / 2), tag=f"cargo:{cid}"),
                         f"{tonnes:.1f} t"))
        level += height
        if level >= ceiling:
            break
    return out


def _berths(ship, chassis, officers, form) -> list:
    """One cell per berth, lit if somebody is in it."""
    if chassis.crew <= 0:
        return []
    out = []
    count = min(chassis.crew, 10)
    for index in range(count):
        angle = 2 * math.pi * index / count
        radius = form.beam * 0.44
        at = (radius * math.cos(angle), radius * math.sin(angle),
              form.length * 0.52)
        who = officers[index] if index < len(officers) else None
        out.append(Solid(
            f"berth:{index}", who.name if who else "empty berth",
            box(form.beam * 0.20, form.beam * 0.20, form.beam * 0.26,
                LIVING if who else "void", at=at, tag=f"berth:{index}"),
            f"{who.role_name} · level {who.level}" if who else "unfilled"))
    return out


#: How big a patch of hull shares one number, in hull radii. Hashing each
#: face on its own made damage a checkerboard — every quad flipping
#: independently reads as a broken texture, not as a wound. Neighbouring
#: faces land in the same cell and rot together.
PATCH = 0.19


def speckle(point, cell: float | None = None) -> float:
    """A stable number in [0, 1) for a point, for scattering without an RNG.

    Coherent, not per-point: everything inside one `cell` cube gets the same
    number, so what it scatters comes out in patches.

    Deliberately not `game.rng()`: the model is drawn many times a second and
    drawing must never advance the chronicle's random state.
    """
    cell = PATCH if cell is None else cell
    n = 0
    for value in point:
        n = (n * 1000003 + math.floor(value / cell)) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 2246822519) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFFFFFF) / 0x100000000


def scar(solid, health: float) -> int:
    """Mark dead patches on a hull. Returns how many faces are hurt.

    A ship at 30% looked exactly like a ship at 100% — every reading of the
    damage was a percentage in a side panel, and the picture of the ship, the
    one thing always on the screen, said nothing at all.

    Patches rather than a uniform dimming, and in the same places each time:
    a face is dying when its own stable number falls above the hull's health,
    so wounds appear where they appeared before and spread as she is hurt.
    """
    hurt = 0
    for face in solid.faces:
        value = speckle(centre_of(face.points))
        face.hurt = max(0.0, min(1.0, (value - health) * 2.2))
        if face.hurt > 0:
            hurt += 1
    return hurt


def build(game, ship=None, fitted=None, cutaway: bool = False) -> dict:
    """The whole model. `fitted` overrides the ship's own, for the designer.

    Passing `fitted` is what lets the shipyard show a refit *before* it is
    bought: the model is a function of the parts list, so handing it a
    prospective list draws the prospective ship.
    """
    ship = ship or game.ship
    chassis = CHASSIS_BY_ID[ship.chassis]
    form = form_for(chassis.family)
    parts = list(fitted if fitted is not None else ship.fitted)
    st = ship_stats(ship, getattr(game, "bonuses", None))

    solids = []
    if not cutaway:
        skin = _hull(form, chassis)
        health = layer_health(ship)
        scar(skin, health[0][1] if health else 1.0)
        solids.append(skin)
    solids.extend(_furniture(form))

    used: dict[str, int] = {}
    for pid in parts:
        part = PARTS_BY_ID.get(pid)
        if part is None:
            continue
        mounts = form.mounts.get(part.slot) or form.mounts.get("utility") or []
        if not mounts:
            continue
        index = used.get(part.slot, 0)
        used[part.slot] = index + 1
        solids.append(_part_solid(part, mounts[index % len(mounts)], form))

    solids.extend(_hold(ship, st, form))
    solids.extend(_berths(ship, chassis, list(getattr(game, "officers", [])),
                          form))
    return {"solids": solids, "form": form, "chassis": chassis,
            "cutaway": cutaway,
            "faces": sum(len(s.faces) for s in solids)}


def layer_health(ship) -> list:
    """(name, fraction, tint) per layer, outermost first — for the cutaway."""
    out = []
    for index, layer in enumerate(ship.layers):
        fraction = layer.hp / layer.max if layer.max else 1.0
        out.append((layer.name, max(0.0, min(1.0, fraction)),
                    LAYER_TINT[index % len(LAYER_TINT)]))
    return out
