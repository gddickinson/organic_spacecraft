"""Where a leg actually runs: the arc, the star's heat on it, and the risk.

Split out of `sim/flight.py`, which was a recorded five-hundred-line debt, along
a seam that was already there: `flight` owns *when and what* — orbits,
intercepts, quotes, the act of travelling — and this owns *where the line
goes and what standing on it costs*. Nothing here reads the game's tables or
the calendar; `hot_risk` is the one function that takes a `game`, and it reads
two numbers off the hull.

`flight` imports these for its own quoting and pricing, so the names remain
reachable where their readers have always found them — the same arrangement as
`sim/conn` and `sim/conn_step`.
"""

from __future__ import annotations

import math

#: The star, which every distance here is measured against. Named because it
#: is now a point in three dimensions rather than an implied pair of zeroes.
_ORIGIN = (0.0, 0.0, 0.0)

#: Inside this radius a leg is running through the star's heat, in AU.
HOT_RADIUS = 1.2

#: How much a hull already running hot adds to the risk of a burn.
HOT_RISK = 0.28

#: Below this share of the cap, the heat you are carrying adds so little risk
#: that saying so would be noise on every screen in the game.
WORTH_SAYING = 0.25

#: How much risk a long leg adds per AU, and the most it can add. A longer arc
#: is more time for something to go wrong.
PER_AU = 0.012
LONG_LEG_CAP = 0.10

#: Below this the distance surcharge is not worth a line on the screen.
LONG_ENOUGH = 0.03


def _closest_approach(start, target) -> float:
    """How near the star the straight leg passes, in AU."""
    return math.dist(_closest_point(start, target), _ORIGIN)


def route(start, target) -> tuple[list, float]:
    """The legs actually flown, and their total length in AU.

    You cannot fly through a star. When the direct line would pass inside the
    hot radius — which it does for any target on the far side of the system —
    the helm bends the course around it, and the detour is what an opposite
    conjunction costs you. Reaching a body that genuinely lives down there is
    still allowed: the clearance never closes tighter than the destination.
    """
    start, target = tuple(start), tuple(target)
    clear = min(HOT_RADIUS, math.dist(start, _ORIGIN), math.dist(target,
                                                                _ORIGIN))
    near = _closest_approach(start, target)
    direct = math.dist(start, target)
    # The tolerance is not decoration. The innermost orbit slot sits at
    # exactly `R_INNER`, so for a body there the clearance *is* the target's
    # own distance and the closest point of the leg is the target itself —
    # `near` and `clear` are the same number computed two ways, and they
    # differ by about 1e-16. Without the slack that sends the course down the
    # bend path, where the waypoint is the closest point pushed out to a
    # radius it is already at: a three-leg route whose detour is exactly zero,
    # which is a course reported as bent around the star while going straight
    # through where it always went.
    if near >= clear - 1e-9 or clear <= 1e-6:
        return [start, target], direct

    # Push the tightest point of the leg out to the clearance radius. If it
    # runs dead through the star there is no side to favour, so take a
    # perpendicular and go around the short way.
    #
    # **The star is a sphere now, not a circle.** All of this reads the same
    # in three dimensions — the closest point on a segment to the origin does
    # not care how many axes there are — which is why the bend survived the
    # orbits gaining a tilt. Only the degenerate case needed thought: in a
    # plane there is one perpendicular to a line, and in space there is a
    # whole circle of them, so one is chosen off an axis the leg is not
    # already parallel to.
    mid = _closest_point(start, target)
    length = math.dist(mid, _ORIGIN)
    if length < 1e-6:
        mid = _perpendicular(start, target)
        length = math.dist(mid, _ORIGIN) or 1.0
    way = tuple(c / length * clear for c in mid)
    legs = [start, way, target]
    total = math.dist(start, way) + math.dist(way, target)
    return legs, total


def _closest_point(start, target) -> tuple:
    """The point on the leg that passes nearest the star."""
    span_v = tuple(b - a for a, b in zip(start, target))
    span = sum(c * c for c in span_v)
    if span <= 1e-9:
        return tuple(start)
    t = max(0.0, min(1.0,
                     -sum(a * c for a, c in zip(start, span_v)) / span))
    return tuple(a + c * t for a, c in zip(start, span_v))


def _perpendicular(start, target) -> tuple:
    """Some direction square to a leg that runs dead through the star.

    In a plane there is one answer up to sign. In space there is a circle of
    them and any will do, so this crosses the leg with whichever axis it is
    least parallel to — which cannot itself be degenerate.
    """
    span_v = tuple(b - a for a, b in zip(start, target))
    axis = min(range(3), key=lambda i: abs(span_v[i]))
    other = tuple(1.0 if i == axis else 0.0 for i in range(3))
    return (span_v[1] * other[2] - span_v[2] * other[1],
            span_v[2] * other[0] - span_v[0] * other[2],
            span_v[0] * other[1] - span_v[1] * other[0])


def burn_heat(burn, stats) -> float:
    """Heat a profile leaves in the hull, as a share of what it can hold."""
    return burn.heat * stats.heat_cap


def hot_risk(game) -> float:
    """A hull with heat still in it is a worse thing to burn hard in.

    This is what makes the profiles a decision. Without it a hard burn saved
    nineteen days for three hundred credits of reaction mass and 1.2% of a
    hull that heals itself, and nobody would ever have coasted.
    """
    cap = getattr(game.ship_stats, "heat_cap", 0) or 1
    return HOT_RISK * min(1.0, max(0.0, game.ship.heat / cap))


def _heat_risk(start, target) -> float:
    """Working close to the star is hot however carefully you route."""
    deep = min(math.dist(start, _ORIGIN), math.dist(target, _ORIGIN))
    if deep >= HOT_RADIUS:
        return 0.0
    return min(0.18, (HOT_RADIUS - deep) * 0.16)
