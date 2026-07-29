"""What counts as an orbit, and how near to one you are.

Lifted out of `sim/conn.py`, which flies the ship. This is the one question
that is not about flying: given where you are and how fast, is this an orbit,
a fall, or a departure?

The answer is a body's own arithmetic. `mu` comes from its `radius_km` and
`gravity`, so circular speed at a middling world really is about five
kilometres a second and at a rock really is four metres — and the tolerance
has to work at both ends, which is what `orbit_band` is for.
"""

from __future__ import annotations

import math

#: How near a body you may hold station before the drag of its exosphere and
#: the traffic-control of anyone living there make it somebody's business.
ORBIT_FLOOR_KM = 80.0

#: How near circular speed counts as circular, in m/s — at a world big
#: enough for it to be the binding limit.
#:
#: Not a percentage, which was the first draft and was wrong: circular speed
#: at a middling world is about 5 km/s, so a tenth of it is 500 m/s — forty
#: main-drive burns, which no captain is going to sit through, and a ship
#: arriving 50 m/s out would have read as already in orbit. The transfer does
#: the kilometres a second; the conn trims what it leaves you with.
#:
#: But it cannot be flat either. Circular speed round a rock is four metres a
#: second, so a flat band of fifteen is wider than the orbit — every approach
#: began already in one, and the start condition came out retrograde. See
#: `orbit_band`, which takes whichever of the two is tighter.
ORBIT_BAND = 15.0

#: The share of circular speed that counts as circular at a small body, where
#: `ORBIT_BAND` would be the whole orbit.
ORBIT_BAND_SHARE = 0.2


def orbital_speed(conn, r_km: float | None = None) -> float:
    """The circular speed at a radius, m/s. Zero where there is no gravity."""
    r = conn.range_km if r_km is None else r_km
    if conn.target.mu <= 0 or r <= 1e-6:
        return 0.0
    return math.sqrt(conn.target.mu / r) * 1000.0


def in_orbit(conn) -> bool:
    """Is this an orbit, or merely a fall that has not finished yet?

    Circular enough that it will not come down and will not leave: the speed
    within a tenth of circular, and the motion across the line of sight rather
    than along it.
    """
    if conn.target.mu <= 0:
        return False
    r = conn.range_km
    if r < conn.target.radius_km + ORBIT_FLOOR_KM:
        return False
    want = orbital_speed(conn)
    band = orbit_band(conn)
    if want <= 0 or abs(conn.speed - want) > band:
        return False
    return abs(conn.closing) <= band


def orbit_band(conn) -> float:
    """How near circular counts as circular here, in m/s.

    Whichever is tighter: what a pilot can hold, or a fifth of the orbit. A
    world demands the main drive and a rock demands the thrusters, and both
    are a real manoeuvre rather than a formality.
    """
    return min(ORBIT_BAND, orbital_speed(conn) * ORBIT_BAND_SHARE)


def orbit_note(conn) -> str:
    """What the flight computer says about the orbit you are not yet in."""
    if conn.target.mu <= 0:
        return ""
    want = orbital_speed(conn)
    r = conn.range_km
    floor = conn.target.radius_km + ORBIT_FLOOR_KM
    if r < floor:
        return (f"Too low: {r - conn.target.radius_km:.0f} km up, and nothing "
                f"holds below {ORBIT_FLOOR_KM:.0f}.")
    band = orbit_band(conn)
    if conn.speed < want - band:
        return (f"{want - conn.speed:,.0f} m/s short of circular "
                f"({want:,.0f} m/s at this height). You are falling.")
    if conn.speed > want + band:
        return (f"{conn.speed - want:,.0f} m/s over circular. This is a "
                "departure, not an orbit.")
    if abs(conn.closing) > orbit_band(conn):
        return (f"Speed is right; {conn.closing:+,.0f} m/s of it is along the "
                "line of sight. Turn it across.")
    return f"Circular at {r - conn.target.radius_km:.0f} km."


# Deliberately no import of `Conn`: `sim/conn.py` imports this module, so
# naming its type here would close the loop. Everything below reads an
# approach through the same handful of attributes and nothing else.
