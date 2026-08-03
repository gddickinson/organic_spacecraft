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


def _closest_approach(sx: float, sy: float, tx: float, ty: float) -> float:
    """How near the star the straight leg passes, in AU."""
    dx, dy = tx - sx, ty - sy
    span = dx * dx + dy * dy
    if span <= 1e-9:
        return math.hypot(sx, sy)
    t = max(0.0, min(1.0, -(sx * dx + sy * dy) / span))
    return math.hypot(sx + dx * t, sy + dy * t)


def route(sx: float, sy: float, tx: float, ty: float) -> tuple[list, float]:
    """The legs actually flown, and their total length in AU.

    You cannot fly through a star. When the direct line would pass inside the
    hot radius — which it does for any target on the far side of the system —
    the helm bends the course around it, and the detour is what an opposite
    conjunction costs you. Reaching a body that genuinely lives down there is
    still allowed: the clearance never closes tighter than the destination.
    """
    clear = min(HOT_RADIUS, math.hypot(sx, sy), math.hypot(tx, ty))
    near = _closest_approach(sx, sy, tx, ty)
    direct = math.hypot(tx - sx, ty - sy)
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
        return [(sx, sy), (tx, ty)], direct

    # Push the tightest point of the leg out to the clearance radius. If it
    # runs dead through the star there is no side to favour, so take the
    # perpendicular and go around the short way.
    mx, my = _closest_point(sx, sy, tx, ty)
    length = math.hypot(mx, my)
    if length < 1e-6:
        mx, my = -(ty - sy), (tx - sx)
        length = math.hypot(mx, my) or 1.0
    wx, wy = mx / length * clear, my / length * clear
    legs = [(sx, sy), (wx, wy), (tx, ty)]
    total = math.hypot(wx - sx, wy - sy) + math.hypot(tx - wx, ty - wy)
    return legs, total


def _closest_point(sx: float, sy: float, tx: float, ty: float) -> tuple[float, float]:
    dx, dy = tx - sx, ty - sy
    span = dx * dx + dy * dy
    if span <= 1e-9:
        return sx, sy
    t = max(0.0, min(1.0, -(sx * dx + sy * dy) / span))
    return sx + dx * t, sy + dy * t


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


def _heat_risk(sx: float, sy: float, tx: float, ty: float) -> float:
    """Working close to the star is hot however carefully you route."""
    deep = min(math.hypot(sx, sy), math.hypot(tx, ty))
    if deep >= HOT_RADIUS:
        return 0.0
    return min(0.18, (HOT_RADIUS - deep) * 0.16)
