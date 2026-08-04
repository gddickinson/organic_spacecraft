"""What is out there besides the thing you are approaching.

The conn's cameras drew the target and a starfield, and nothing else in the
system at all. Take the conn with nothing in reach and the windows were empty
— which a player reported, and which is wrong in a way that is easy to
measure: standing off a body at 0.40 AU, **the system's own star subtends
1.34°**. That is two and a half times the width of the Sun from Earth. It is
the brightest thing a hull will ever fly past and it was not being drawn.

So an approach carries a sky. Everything in the system, placed in the
approach's own frame — which is centred on the target — in kilometres, with
the size it really has. `ui/viewport.py` decides what is big enough to be
worth a mesh and what is a point of light.

Built once, when the approach opens. Bodies move, but they move on a scale of
months and an approach is over in hours; recomputing the sky every repaint
would cost more than it could possibly buy.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: Kilometres in an astronomical unit.
AU_KM = 1.495_978_707e8

#: A fallback star radius, in km, for a class nobody has described yet.
#: Real sizes come from `data/starclasses.py`, which knows that a white dwarf
#: is the size of a rocky world and a neutron star the size of a city — a
#: range of a hundred thousand to one that the sky used to flatten into one
#: yellow ball.
STAR_RADIUS_KM = 695_700.0

#: Below this apparent width, in degrees, a thing is a point of light rather
#: than a shape. A pixel is about 0.08° on a 60° field at 760 px, so this is
#: roughly "more than a couple of pixels across".
SHAPE_ABOVE_DEG = 0.25

#: How far off a co-located thing is put, as a share of its own radius.
#:
#: An anchorage's position in AU *is* its body's — that is the simplification
#: the whole flight model rests on, and it is why no screen needs a special
#: case for flying to a quay. It falls over exactly here: asked what the sky
#: looks like from a berth, it says the planet is at zero range and therefore
#: 180° wide, which is a picture of being inside it. A quay is in orbit, so
#: the body goes where an orbit is.
CO_LOCATED_LIFT = 1.18


@dataclass(frozen=True)
class Sight:
    """One thing in the sky, in the approach's frame."""

    name: str
    kind: str                  # star | body | anchorage | hull
    #: Where it is relative to the target, in km.
    at: tuple
    radius_km: float
    #: What colour it reads as. A hint for the window, not a rule.
    tint: str = ""
    #: For a body, what sort of place it is, so the window can pick a mesh
    #: with the right caps and bands on it.
    look: str = ""
    #: True for a world that carries a ring system.
    ringed: bool = False
    #: For a star, the colour of the corona *around* the disc, as against
    #: `tint`, which is the disc itself. Both have been in
    #: `data/starclasses.py` since the classes were written; the window drew
    #: the corona in the core colour and `halo` was read by nobody, so a
    #: blue-white A-type and a red dwarf had coronae of the same hue as their
    #: own discs and the pair of colours did one colour's work.
    halo: str = ""

    @property
    def range_km(self) -> float:
        return math.dist(self.at, (0.0, 0.0, 0.0))

    @property
    def apparent_deg(self) -> float:
        """How wide it looks from the target, in degrees."""
        span = self.range_km
        if span <= self.radius_km:
            return 180.0
        return math.degrees(math.asin(self.radius_km / span)) * 2.0

    @property
    def is_shape(self) -> bool:
        return self.apparent_deg >= SHAPE_ABOVE_DEG


def build(game, contact=None) -> list:
    """Everything worth seeing from an approach on `contact`.

    Positions are in the approach's frame: the target at the origin, the rest
    of the system placed around it. The star comes first because it is both
    the biggest thing in the sky and the only light in it.

    With no contact this is the view from wherever the ship is standing —
    because a captain with nothing in reach can still look out of a window,
    and used to be shown a black rectangle for their trouble.
    """
    from . import flight
    from . import track as track_sim

    system = game.system
    if contact is None:
        tx, ty, tz = flight.ship_position(game)
        skip = None
    else:
        try:
            tx, ty, tz = track_sim.at(game, contact, game.day)
        except Exception:
            return []
        skip = contact.id

    def offset(at_au, radius_km: float = 0.0, index: int = 0) -> tuple:
        """Something's place in the approach's frame, in km.

        **The third number is real now.** This used to end `, 0.0` for
        everything: the sky was a flat disc, so a world on a steeply inclined
        orbit was drawn level with the hull however far above the plane it
        actually stood. With orbits tilted (`sim/elements`) a body can be an
        AU out of the reference plane, and from a berth that is the
        difference between a planet on the horizon and one overhead.
        """
        dx, dy, dz = ((at_au[0] - tx) * AU_KM, (at_au[1] - ty) * AU_KM,
                      ((at_au[2] if len(at_au) > 2 else 0.0) - tz) * AU_KM)
        if math.dist((dx, dy, dz), (0.0, 0.0, 0.0)) > (radius_km
                                                       * CO_LOCATED_LIFT):
            return (dx, dy, dz)
        # Sharing a position with the target: put it where it actually is.
        # A world an anchorage orbits is *below* the berth; a hull holding
        # station beside one is off to a side, spread so they do not stack.
        lift = max(radius_km * CO_LOCATED_LIFT, radius_km + 400.0)
        angle = index * 1.7
        return (math.cos(angle) * lift * 0.3, math.sin(angle) * lift * 0.3,
                -lift)

    from ..data.starclasses import of as star_class
    star = star_class(system)
    out = [Sight(name=system.star_name or star.name, kind="star",
                 at=offset((0.0, 0.0, 0.0), star.radius_km),
                 radius_km=star.radius_km, tint=star.core, look=star.id,
                 halo=star.halo)]

    # Where the docked traffic is, so a hull holding a berth is drawn *on* it
    # rather than floating near the structure. `sim/control` knows who is in
    # which berth; without this the occupancy existed and a pilot flying up to
    # a full station saw four empty masts.
    from . import control
    docked = {}
    for other in track_sim.contacts(game, system):
        if other.kind != "anchorage":
            continue
        for berth, who in control.holders(game, other).items():
            docked[who] = (other, berth)

    for index, other in enumerate(track_sim.contacts(game, system)):
        if other.id == skip or other.kind == "star":
            continue
        try:
            x, y, z = track_sim.at(game, other, game.day)
        except Exception:
            continue
        if other.kind == "body" and other.body_index is not None:
            body = system.bodies[other.body_index]
            radius = float(getattr(body, "radius_km", 1000))
            kind = "body"
            look = getattr(body, "kind", "rocky")
            ringed = has_rings(body)
        elif other.kind == "anchorage":
            # `look` used to be "" here and on the line below, so every berth
            # and every hull in the sky reached the window as an anonymous
            # "not a world" and was drawn with the one shipyard mesh. Both
            # contacts have carried what they are all along.
            # Size from the same door the approach reads, `berths3d.radius_km`.
            # This said 0.6 while `targets` said 0.4 for the same structure,
            # so the thing you picked out at forty kilometres was half again
            # the size of the thing you came alongside.
            from ..data.berths3d import radius_km
            look = other.berth
            radius, kind, ringed = radius_km(look), "anchorage", False
        else:
            radius, kind, look, ringed = 0.08, "hull", other.errand, False
        where = offset((x, y, z), radius, index)
        held = docked.get(other.name) if kind == "hull" else None
        if held is not None and contact is not None:
            # On the berth it is holding. Only when the frame is an approach —
            # with no target the sky is the view from wherever the ship is
            # standing, and the structure's own frame is not the one being
            # drawn in.
            spot = _berth_spot(game, held[0], held[1], tx, ty, tz)
            if spot is not None:
                where = spot
        out.append(Sight(name=other.name, kind=kind,
                         at=where,
                         radius_km=radius, tint=other.tint,
                         look=look, ringed=ringed))
    return out


def _berth_spot(game, structure, berth: str, tx: float, ty: float,
                tz: float = 0.0):
    """Where a berth on this structure is, in the approach's own frame.

    Through `moorings.points`, which is the one door for where a fitting is —
    the same numbers the flight computer aims at and `ui/viewport` draws the
    mesh by, so a hull shown on a mast is on the mast.

    Deliberately **not** through `offset`. That helper lifts anything sharing
    the target's position clear of it so a world and its quay do not stack, and
    a berth is the one thing that must not be moved: measured, a docked hull
    came out 418 km from a mast 444 m off the structure's pole.
    """
    from . import moorings
    from . import targets as targets_sim
    from . import track as track_sim
    try:
        target = targets_sim.target_from_contact(game, structure)
        spin = moorings.spin_at(target, 0.0)
        at = dict(moorings.points(target, spin)).get(berth)
        if at is None:
            return None
        sx, sy, sz = track_sim.at(game, structure, game.day)
    except Exception:
        return None
    dx, dy, dz = ((sx - tx) * AU_KM, (sy - ty) * AU_KM, (sz - tz) * AU_KM)
    return (dx + at[0], dy + at[1], dz + at[2])


def has_rings(body) -> bool:
    """Does this world carry a ring system?

    Derived from the body's **name**, so a ringed world is ringed in every
    chronicle grown from that seed and there is nothing to save. Only giants
    get them — a ring round a 2,000 km ice ball would be a decoration rather
    than a fact.

    The name and not the id: a body's id is "1", "2" or "3" and repeats in
    every system, so a digest of it had almost no entropy at all and produced
    **1% ringed against a target of 45%**. A name carries its system with it.
    """
    from ..core.rng import RNG
    from ..data.worlds3d import RINGED_SHARE
    if getattr(body, "kind", "") != "gas":
        return False
    return RNG(f"rings:{getattr(body, 'name', '') or body.id}").chance(
        RINGED_SHARE)


def shapes(sky) -> list:
    """The ones big enough to draw as objects, biggest first.

    Sorted so the painter puts the far ones down before the near ones, which
    is all the depth sorting a handful of widely-separated bodies needs.
    """
    return sorted((s for s in sky if s.is_shape),
                  key=lambda s: -s.range_km)


def points(sky) -> list:
    """The ones that are only a light."""
    return [s for s in sky if not s.is_shape]


def note(sky) -> str:
    """One line naming what is in the sky, for the panel."""
    seen = shapes(sky)
    if not seen:
        return "Nothing out there but the field."
    biggest = max(seen, key=lambda s: s.apparent_deg)
    return (f"{len(seen)} body/bodies in view; {biggest.name} is "
            f"{biggest.apparent_deg:.1f}° across.")
