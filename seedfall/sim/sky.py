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

#: A star's radius, in km. The game does not give its stars a size — they are
#: a spectral class and a tint — so this is the one number invented here, and
#: it is a middling main-sequence star. At 0.40 AU that is 1.34° of sky.
STAR_RADIUS_KM = 700_000.0

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
        tx, ty = flight.ship_position(game)
        skip = None
    else:
        try:
            tx, ty = track_sim.at(game, contact, game.day)
        except Exception:
            return []
        skip = contact.id

    def offset(x_au: float, y_au: float, radius_km: float = 0.0,
               index: int = 0) -> tuple:
        dx, dy = (x_au - tx) * AU_KM, (y_au - ty) * AU_KM
        if math.hypot(dx, dy) > radius_km * CO_LOCATED_LIFT:
            return (dx, dy, 0.0)
        # Sharing a position with the target: put it where it actually is.
        # A world an anchorage orbits is *below* the berth; a hull holding
        # station beside one is off to a side, spread so they do not stack.
        lift = max(radius_km * CO_LOCATED_LIFT, radius_km + 400.0)
        angle = index * 1.7
        return (math.cos(angle) * lift * 0.3, math.sin(angle) * lift * 0.3,
                -lift)

    out = [Sight(name=system.star_name or "the star", kind="star",
                 at=offset(0.0, 0.0, STAR_RADIUS_KM), radius_km=STAR_RADIUS_KM,
                 tint=getattr(system, "tint", "") or "#ffd9a0")]

    for index, other in enumerate(track_sim.contacts(game, system)):
        if other.id == skip or other.kind == "star":
            continue
        try:
            x, y = track_sim.at(game, other, game.day)
        except Exception:
            continue
        if other.kind == "body" and other.body_index is not None:
            radius = float(getattr(system.bodies[other.body_index],
                                   "radius_km", 1000))
            kind = "body"
        elif other.kind == "anchorage":
            radius, kind = 0.6, "anchorage"
        else:
            radius, kind = 0.08, "hull"
        out.append(Sight(name=other.name, kind=kind,
                         at=offset(x, y, radius, index),
                         radius_km=radius, tint=other.tint))
    return out


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
