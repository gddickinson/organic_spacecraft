"""What the conn is flying relative to, and how far off an approach opens.

Lifted out of `sim/conn.py`. A target is the one place the close-quarters
model meets the rest of the game: it is where a body's `radius_km` and
`gravity` become a `mu`, and where a quay stops being a service list and
becomes a structure with a size you can hit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .orbits import ORBIT_FLOOR_KM

#: Standard gravity, for turning a body's surface gravity into a mu.
G0 = 9.80665


#: The kind a free flight's target carries: open space, at the place the ship
#: took the conn. It lives here rather than in `sim/freeflight` because `Conn`
#: is built here and asks the question before that module is importable —
#: `freeflight` imports the conn, so the conn cannot import it back.
OPEN = "open"


def is_open(target) -> bool:
    """Is this 'target' the open space of a free flight rather than a thing?"""
    return getattr(target, "kind", "") == OPEN


@dataclass
class Target:
    """What the conn is flying relative to."""

    id: str
    name: str
    kind: str                    # body | anchorage | hull | point
    #: How big it is, in km. A hull is a hundred metres; a world is thousands.
    radius_km: float = 0.05
    #: Standard gravitational parameter, km³/s². Zero for anything but a body.
    mu: float = 0.0
    detail: str = ""
    #: Which body this is, or the body it orbits. A berth is a place, and
    #: `orbit_body` is how the game records one.
    body_index: int | None = None
    #: For an anchorage, what sort of berth: quay, hub, holding or gate.
    berth: str = ""
    #: For a hull, what it is out here doing. Same reason as `berth`: the
    #: window should not have to parse a detail string to know whether it is
    #: closing on a courier or on something with no transponder.
    errand: str = ""
    #: For a body, what sort of world — so the window picks a mesh with the
    #: right caps and bands rather than a grey ball with a label on it.
    look: str = ""
    #: For a body, whether it carries a ring system. The *sky* drew rings on
    #: a ringed giant from the moment giants had them; the thing you were
    #: actually approaching did not — so a giant's rings vanished at exactly
    #: the point you got near enough for them to be worth looking at.
    ringed: bool = False


def target_from_body(body, name: str | None = None,
                    index: int | None = None) -> Target:
    """A world or a moon, with the gravity it actually has.

    `mu = g · R²` in the units the rest of this module uses. A body's
    `gravity` is in gees and its `radius_km` in km, so this is the body's own
    numbers carried through and not a difficulty setting.
    """
    from .sky import has_rings
    r_km = max(1.0, float(getattr(body, "radius_km", 1000)))
    g = max(0.0, float(getattr(body, "gravity", 0.0))) * G0     # m/s²
    return Target(id=body.id, name=name or body.name, kind="body",
                  radius_km=r_km, mu=g * r_km * r_km / 1000.0,
                  detail=getattr(body, "kind_name", "") or body.kind,
                  look=getattr(body, "kind", "rocky"), body_index=index,
                  ringed=has_rings(body))


def target_from_contact(game, contact) -> Target:
    """Build a conn target from anything `track` can put a cursor on.

    A `Target` handed in is already the answer. `sim/freeflight` builds one
    for open space — there is no contact behind it, because the whole point
    is that the ship is not approaching anything — and it must arrive at the
    conn unchanged rather than being flattened into a "point".
    """
    if isinstance(contact, Target):
        return contact
    system = game.system
    if contact.kind in ("body", "anchorage") and contact.body_index is not None:
        body = system.bodies[contact.body_index]
        if contact.kind == "body":
            return target_from_body(body, contact.name, contact.body_index)
        # A quay orbits its body but is a structure in its own right: you come
        # alongside the station, not the planet underneath it.
        berth = getattr(contact, "berth", "")
        # An anchor is a far bigger thing than a quay, and it should read
        # that way in the window on the way in.
        # How big it is comes from `berths3d.radius_km` — the same door the
        # sky draws it at, so what you pick out at range and what you come
        # alongside are one object. An anchor is a far bigger thing than a
        # quay and always was; an ARCA Habitat is bigger again.
        from ..data.berths3d import radius_km
        return Target(id=contact.id, name=contact.name, kind="anchorage",
                      radius_km=radius_km(berth),
                      detail=contact.detail, berth=berth,
                      body_index=contact.body_index)
    if contact.kind == "hull":
        return Target(id=contact.id, name=contact.name, kind="hull",
                      radius_km=0.08, detail=contact.detail,
                      errand=getattr(contact, "errand", ""))
    return Target(id=contact.id, name=contact.name, kind="point",
                  radius_km=0.0, detail=contact.detail)


def approach_range(target: Target) -> float:
    """How far off an approach opens, in km from the target's centre.

    A quay is met at twelve kilometres. A world cannot be: twelve kilometres
    from the centre of one is several thousand kilometres underground, which
    is where the first draft of this put the ship — and `mu / r²` at that
    range threw it out of the system at eleven thousand kilometres a second.
    """
    if target.kind == "body":
        return target.radius_km + max(ORBIT_FLOOR_KM * 4, target.radius_km * 0.1)
    return 12.0


def starlight(game, contact) -> tuple:
    """Which way the star's light travels, in the target's own frame.

    The star sits at the system's centre and the target somewhere out from
    it, so light falls along the target's own position vector. That one line
    is what gives a world a terminator on the correct side, and a station a
    lit face and a dark one.
    """
    from . import track as track_sim
    try:
        x, y = track_sim.at(game, contact, game.day)
    except Exception:
        return (0.0, 1.0, 0.0)
    span = math.hypot(x, y)
    if span < 1e-9:
        return (0.0, 1.0, 0.0)
    # A little out of the orbital plane as well, so a sphere is never lit
    # dead-on and the terminator always has somewhere to fall.
    return (x / span, y / span, -0.25)
