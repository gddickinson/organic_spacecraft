"""Which way the ship is pointing, and what it costs to point it somewhere else.

`Conn.heading` existed for a whole cycle and was never written to. The ship
had an orientation in the sense that a variable held a number; nothing turned
it, nothing read it, and the main drive cheerfully shoved the hull sideways.

A main drive pushes along the nose. That is the entire physical content of
this module, and everything else follows from it:

* To burn in a direction you must first **point** that way.
* Pointing takes **time**, set by the hull's `slew_rate` — 46 seconds to flip
  a SPORE, eight minutes to flip a LEVIATHAN.
* Pointing costs **reaction mass**, because attitude clusters are thrusters
  like any other.
* So a hard burn is not one act but three: turn, burn, and — if you mean to
  arrive rather than fly past — turn again and burn back.

The attitude thrusters can still translate the hull directly, in any
direction, without turning at all. That is what they are for, it is why close
work is done on them, and it is the trade the conn is built around: the
thrusters are nimble and weak, the main drive is strong and has to be aimed.
"""

from __future__ import annotations

import math

#: Off by less than this and the flight computer calls it pointed. A hull
#: cannot hold an attitude to the arc-second, and demanding it would make
#: every burn a slew.
POINTED_RAD = math.radians(2.0)

#: Reaction mass a full rotation costs, per tonne of ship, in tonnes.
#:
#: Small — turning is cheap next to going anywhere — but not free, so a
#: captain who flips the hull a dozen times settling an approach pays for it.
#: Measured against play: a NAVIS flip costs about 0.09 t against the 0.54 t
#: a whole berthing runs to.
TURN_COST_PER_TONNE = 3.4e-5


def unit(vec) -> tuple:
    """A vector scaled to length one. The zero vector points along the nose."""
    length = math.sqrt(sum(c * c for c in vec))
    if length < 1e-12:
        return (0.0, 1.0, 0.0)
    return (vec[0] / length, vec[1] / length, vec[2] / length)


def angle_between(a, b) -> float:
    """The angle between two directions, in radians, 0 to pi."""
    ua, ub = unit(a), unit(b)
    dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(ua, ub))))
    return math.acos(dot)


def pointed_at(nose, toward) -> bool:
    """Is the hull aimed closely enough to burn?"""
    return angle_between(nose, toward) <= POINTED_RAD


def turn_cost(ship, radians: float) -> float:
    """Reaction mass to swing through an angle, in tonnes."""
    from . import thrusters
    if radians <= 0:
        return 0.0
    share = abs(radians) / math.tau
    return thrusters.mass_tonnes(ship) * TURN_COST_PER_TONNE * share


def plan_turn(ship, nose, toward) -> dict:
    """What it would take to point the hull a given way.

    Quoted before it is done, in the terms the panel shows, so a captain can
    see that swinging a loaded freighter round costs eight minutes before
    they commit to it.
    """
    from . import thrusters
    angle = angle_between(nose, toward)
    return {
        "radians": angle,
        "degrees": math.degrees(angle),
        "seconds": thrusters.slew_seconds(ship, angle),
        "fuel": turn_cost(ship, angle),
        "already": angle <= POINTED_RAD,
    }


def turned(nose, toward, radians: float) -> tuple:
    """Rotate `nose` toward `toward` by at most `radians`.

    A great-circle turn: the shortest path on the sphere between where the
    hull points and where it is being asked to point. Overshooting is not
    possible — the arc is clamped — because a flight computer that sailed
    past its aim point would need a second correction and then a third.
    """
    start, goal = unit(nose), unit(toward)
    angle = angle_between(start, goal)
    if angle <= 1e-9 or radians <= 0:
        return start
    if radians >= angle:
        return goal
    # Slerp. The component of the goal perpendicular to the start, normalised,
    # is the direction the nose sweeps through.
    dot = sum(a * b for a, b in zip(start, goal))
    perp = tuple(g - dot * s for s, g in zip(start, goal))
    if math.dist(perp, (0.0, 0.0, 0.0)) < 1e-9:
        # Dead astern. There is no shortest great circle to a point exactly
        # opposite — every one is the same length — so the perpendicular
        # component is zero and the arithmetic above has nothing to sweep
        # through. Left alone it returns the nose unchanged, which means a
        # hull asked to reverse **can never turn at all**: `conn.apply`
        # spends every tick slewing, the slew moves nothing, and no thrust is
        # ever delivered. Nothing asked for a reversal until the orbit
        # computer did, and then a ship sat at e=0.123 for fifty thousand
        # ticks with the main drive lit and the hull pointing the wrong way.
        #
        # Any perpendicular will do. Pick one that is definitely not parallel
        # to the nose and start the turn; the next tick has a real gradient
        # to follow.
        axis = (1.0, 0.0, 0.0) if abs(start[0]) < 0.9 else (0.0, 1.0, 0.0)
        drop = sum(a * b for a, b in zip(start, axis))
        perp = tuple(a - drop * s for s, a in zip(start, axis))
    perp = unit(perp)
    c, s = math.cos(radians), math.sin(radians)
    return unit(tuple(start[i] * c + perp[i] * s for i in range(3)))


def slew(conn, toward, seconds: float) -> dict:
    """Turn the hull for a while. Returns how far it got.

    The conn carries the hull's `slew_rate`, so this needs nothing but the
    approach itself — and the mass it spends comes out of the same tank the
    thrusters draw on, because it is the same thrusters.
    """
    rate = getattr(conn, "slew_rate", 0.0)
    if rate <= 0 or seconds <= 0:
        return {"turned": 0.0, "pointed": pointed_at(conn.nose, toward)}
    was = angle_between(conn.nose, toward)
    # Bang-bang again: the arc a hull can cover in a time, turning and
    # stopping, is `rate * (t/2)^2`.
    reach = rate * (seconds / 2.0) ** 2
    swept = min(was, reach)
    conn.nose = list(turned(conn.nose, toward, swept))
    cost = getattr(conn, "turn_rate_cost", 0.0) * (swept / math.tau)
    if cost:
        conn.rcs = max(0.0, conn.rcs - cost)
    return {"turned": swept, "degrees": math.degrees(swept),
            "pointed": pointed_at(conn.nose, toward), "fuel": cost}


def heading_note(conn, toward=None) -> str:
    """One line saying where the nose is, for the conn's panel."""
    if toward is None:
        toward = [-p for p in conn.pos]
    off = math.degrees(angle_between(conn.nose, toward))
    if off <= math.degrees(POINTED_RAD):
        return "Nose on the target."
    if off > 150:
        return f"Nose {off:.0f}° off — pointing away from the target."
    return f"Nose {off:.0f}° off the target."
