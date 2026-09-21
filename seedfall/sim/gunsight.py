"""Where to point a gun, and where the target will be when the round arrives.

Pure geometry: kilometres in, degrees out, no state and nothing that knows
what a `Game` is. Everything that aims — the gunner's own sight, the mounting
the computer swings, the foe shooting back at you — asks here, so a lead that
is right for one of them is right for all three.

**The frame is the hull's**, the same one `data/mounts.py` puts the engines
in: `+y` is the nose, `+x` is starboard, `+z` is the back. A turret's bearing
is degrees round from the nose toward starboard and its elevation is degrees
up from the hull's plane, which is what a gunner would say out loud and what
the ring on the sight is graduated in.

**Lead is the whole craft of it.** A slug leaves the tube at four kilometres a
second, so a corvette ten kilometres off is two and a half seconds away — and
a corvette crossing at 300 m/s is three quarters of a kilometre from where the
sight says it is. `lead_point` solves the intercept the same way the gun does:
guess the flight time from the present range, ask where the target will be by
then, and go round again. Three passes is inside a metre for anything the
game can fly, and a beam takes none at all because it arrives when it is
fired.
"""

from __future__ import annotations

import math

#: How many times `lead_point` goes round. Measured against a closed-form
#: solve on the worst case the drills can produce — a torpedo at 0.6 km/s
#: chasing a corvette crossing at 0.4 — where the third pass moves the aim
#: point by 0.7 m and the fourth by under a centimetre.
LEAD_PASSES = 3

#: A bearing this near the one the gun is already on counts as on it. A
#: mounting that chased the last thousandth of a degree would hum for ever
#: and never read as *still*.
ON_BORE = 0.25


def polar(vec) -> tuple:
    """A vector in the hull's frame to `(bearing, elevation, range)`.

    Bearing is -180..180 off the nose, positive to starboard; elevation is
    -90..90 from the hull's plane, positive up. Both are what a gunner says.
    """
    x, y, z = vec
    span = math.sqrt(x * x + y * y + z * z)
    if span < 1e-9:
        return 0.0, 0.0, 0.0
    bearing = math.degrees(math.atan2(x, y))
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, z / span))))
    return bearing, elevation, span


def vector(bearing: float, elevation: float) -> tuple:
    """`(bearing, elevation)` back to a unit vector in the hull's frame."""
    b, e = math.radians(bearing), math.radians(elevation)
    flat = math.cos(e)
    return (math.sin(b) * flat, math.cos(b) * flat, math.sin(e))


def delta(from_deg: float, to_deg: float) -> float:
    """The short way round from one bearing to another, -180..180."""
    return (to_deg - from_deg + 180.0) % 360.0 - 180.0


def off_bore(bearing: float, elevation: float,
             want_bearing: float, want_elevation: float) -> float:
    """How far the gun is from where it wants to be, in degrees.

    The true angle between the two directions, not the sum of the two axes:
    a mounting 40° off in bearing at 80° of elevation is nearly on the
    target, and an aim error added up axis by axis says it is 40° out.
    """
    a = vector(bearing, elevation)
    b = vector(want_bearing, want_elevation)
    dot = max(-1.0, min(1.0, sum(p * q for p, q in zip(a, b))))
    return math.degrees(math.acos(dot))


def in_arc(kind, bearing: float, elevation: float) -> bool:
    """Will the mounting train this far, or is the hull in the way?"""
    return (abs(delta(0.0, bearing)) <= kind.arc + 1e-9
            and -kind.down - 1e-9 <= elevation <= kind.up + 1e-9)


def clamp(kind, bearing: float, elevation: float) -> tuple:
    """The nearest place inside the arc the mounting can actually sit."""
    off = delta(0.0, bearing)
    held = max(-kind.arc, min(kind.arc, off))
    return held, max(-kind.down, min(kind.up, elevation))


def swing(kind, bearing: float, elevation: float,
          want_bearing: float, want_elevation: float,
          seconds: float) -> tuple:
    """Move the mounting toward an aim for this long. Returns where it got to.

    Each axis at its own rate, because a mounting is two motors and they do
    not wait for each other — which is why a gun that has to come a long way
    round in bearing is already at the right elevation when it gets there.
    """
    across = delta(bearing, want_bearing)
    room = kind.traverse * seconds
    bearing += max(-room, min(room, across))
    up = want_elevation - elevation
    room = kind.elevate * seconds
    elevation += max(-room, min(room, up))
    return clamp(kind, (bearing + 180.0) % 360.0 - 180.0, elevation)


def flight_time(kind, range_km: float) -> float:
    """How long the round is in the air. Zero for a beam."""
    if kind.muzzle_kms <= 0.0:
        return 0.0
    return range_km / kind.muzzle_kms


def lead_point(kind, at, vel, shooter_vel=(0.0, 0.0, 0.0)) -> tuple:
    """Where to put the sight so the round and the target arrive together.

    `at` is where the target is now, in the hull's frame, and `vel` is how it
    is moving in km/s. `shooter_vel` is how *you* are moving: a round leaves
    the tube carrying the ship's own velocity, so a gunner on a hull that is
    itself crossing does not have to correct for their own motion and would
    be badly wrong if the sight made them.

    A beam needs no lead and is handed back the target's own position, which
    is the honest answer rather than a special case at the call site.
    """
    if kind.muzzle_kms <= 0.0:
        return tuple(at)
    drift = tuple(v - s for v, s in zip(vel, shooter_vel))
    guess = math.dist(at, (0.0, 0.0, 0.0)) / kind.muzzle_kms
    for _pass in range(LEAD_PASSES):
        ahead = tuple(p + d * guess for p, d in zip(at, drift))
        guess = math.dist(ahead, (0.0, 0.0, 0.0)) / kind.muzzle_kms
    return tuple(p + d * guess for p, d in zip(at, drift))


def solution(kind, at, vel, shooter_vel=(0.0, 0.0, 0.0)) -> dict:
    """Everything the sight needs about one target, in one read.

    `aim` is where to point, `now` is where the target actually is, `lead` is
    how far apart those two are in degrees — the number that tells a gunner
    whether this is a shot or a prayer — and `reach` is the flight time.
    """
    here = polar(at)
    mark = lead_point(kind, at, vel, shooter_vel)
    aim = polar(mark)
    return {
        "range_km": here[2],
        "now": (here[0], here[1]),
        "aim": (aim[0], aim[1]),
        "at": tuple(at),
        "mark": mark,
        "lead": off_bore(here[0], here[1], aim[0], aim[1]),
        "seconds": flight_time(kind, aim[2]),
        "in_arc": in_arc(kind, aim[0], aim[1]),
    }


def hit_chance(kind, off: float, range_km: float, reach_km: float) -> float:
    """How likely this pull is to land, 0..1, from the aim and the range.

    Two ways to miss and they are different mistakes. **Off the aim** is the
    gunner's: the cone the gun throws into is `kind.spread`, so inside that
    it is a hit however far away the target is, and outside it falls away
    over the same width again. **Past the reach** is the weapon's: beyond the
    range the armament is specified for, the round is still going but it is
    no longer going where it was pointed.

    A seeking round corrects for the first of those and not the second, which
    is exactly what makes it worth carrying.
    """
    from ..data.turrets import SEEKING
    slack = max(kind.spread, 0.4)
    if kind.look == SEEKING:
        slack = max(slack, 8.0)
    aimed = 1.0 if off <= slack else max(0.0, 1.0 - (off - slack) / slack)
    if reach_km <= 0.0:
        return aimed
    over = range_km / reach_km
    far = 1.0 if over <= 1.0 else max(0.0, 1.0 - (over - 1.0) * 1.6)
    return max(0.0, min(1.0, aimed * far))
