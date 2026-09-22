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
import zlib

from . import elements
# The height ladder, split out at 485 lines; re-exported so the conn, the
# autopilot, the flight quote and the checks keep asking this module.
from .orbit_heights import (CLIMB_MARGIN, DEFAULT_HEIGHT,  # noqa: F401
                            HEIGHT_TOLERANCE, LOOK_EXPONENT, ORBIT_HEIGHTS,
                            QUOTABLE, climb_dv, departure_factor, height_km,
                            heights, heights_for, holdable, look_factor,
                            nearest_height, quotable)

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

#: How far from a circle an orbit may be and still count as one.
#:
#: This replaces a pair of instantaneous speed tests that could only ever be
#: satisfied at an apse. 0.05 is a visibly round orbit — apoapsis and
#: periapsis within a tenth of each other — and is tighter than the old
#: speed band allowed at a small body (0.2) and looser than at a large one
#: (0.003), where the old test demanded 15 m/s out of five kilometres a
#: second and no captain could hold it after a transfer.
ORBIT_ECCENTRICITY = 0.05


def orbital_speed(conn, r_km: float | None = None) -> float:
    """The circular speed at a radius, m/s. Zero where there is no gravity."""
    r = conn.range_km if r_km is None else r_km
    if conn.target.mu <= 0 or r <= 1e-6:
        return 0.0
    return math.sqrt(conn.target.mu / r) * 1000.0


def semi_major_km(conn) -> float:
    """The size of the orbit the ship is actually on, in km.

    From the vis-viva equation rearranged: `a = 1 / (2/r − v²/mu)`. This is
    *the* height of an orbit — where the ship happens to be this second is a
    point on it, and on anything but a perfect circle those two differ.

    Which matters because the question "am I in the orbit I asked for?" was
    being answered with the instantaneous range: a ship in a sound orbit
    whose mean height was right read 4% low or high depending on which part
    of it you caught, and the arrival never registered.

    Returns `inf` for anything not bound, which is the honest answer.
    """
    r = conn.range_km
    mu = conn.target.mu
    if mu <= 0 or r <= 1e-9:
        return r
    denom = 2.0 / r - (conn.speed / 1000.0) ** 2 / mu
    return 1.0 / denom if denom > 1e-12 else float("inf")


def eccentricity(conn) -> float:
    """How far from circular the orbit is. 0 is a circle, 1 a parabola."""
    mu = conn.target.mu
    a = semi_major_km(conn)
    if mu <= 0 or a <= 0 or a == float("inf"):
        return 1.0
    px, py, pz = conn.pos
    vx, vy, vz = (v / 1000.0 for v in conn.vel)         # km/s
    hx = py * vz - pz * vy
    hy = pz * vx - px * vz
    hz = px * vy - py * vx
    h2 = hx * hx + hy * hy + hz * hz
    return math.sqrt(max(0.0, 1.0 - h2 / (mu * a)))


def in_orbit(conn) -> bool:
    """Is this an orbit, or merely a fall that has not finished yet?

    Three questions about the *orbit*: is it bound, does the low point clear
    the ground, and is it round enough to be worth calling an orbit.

    It used to ask two questions about the *instant* instead — speed within a
    band of circular, and motion across the line of sight rather than along
    it. Both are true of a good orbit only at its apses, which was fine while
    a ship arrived already near-circular and only had to trim. The moment
    captains could ask to change height it stopped being fine: a ship that
    had flown a clean transfer and settled within 1.5% of the height it asked
    for was told, forty thousand ticks running, that it was not in orbit —
    because the test was being asked at points on the ellipse rather than
    about the ellipse.
    """
    mu = conn.target.mu
    if mu <= 0:
        return False
    a = semi_major_km(conn)
    if a == float("inf") or a <= 0:
        return False                        # not bound: this is a departure
    ecc = eccentricity(conn)
    if a * (1.0 - ecc) < conn.target.radius_km + ORBIT_FLOOR_KM:
        return False                        # the low point is underground
    return ecc <= ORBIT_ECCENTRICITY


def orbit_band(conn) -> float:
    """How near circular counts as circular here, in m/s.

    Whichever is tighter: what a pilot can hold, or a fifth of the orbit. A
    world demands the main drive and a rock demands the thrusters, and both
    are a real manoeuvre rather than a formality.
    """
    return min(ORBIT_BAND, orbital_speed(conn) * ORBIT_BAND_SHARE)


def orbit_note(conn) -> str:
    """What the flight computer says about the orbit you are or are not in.

    Asks exactly the questions `in_orbit` asks, in the same order, because it
    is the sentence a captain reads about that decision. It did not, and the
    two promptly disagreed the moment `in_orbit` started asking about the
    ellipse rather than the instant: the conn reported an orbit made and the
    panel beside it said, of the same tick, "this is a departure, not an
    orbit". A readout that contradicts the thing it is reporting on is worse
    than no readout.
    """
    if conn.target.mu <= 0:
        return ""
    r = conn.range_km
    hull = conn.target.radius_km
    floor = hull + ORBIT_FLOOR_KM
    if r < floor:
        return (f"Too low: {r - hull:.0f} km up, and nothing "
                f"holds below {ORBIT_FLOOR_KM:.0f}.")
    a = semi_major_km(conn)
    if a == float("inf") or a <= 0:
        return (f"{conn.speed - orbital_speed(conn):,.0f} m/s over circular "
                "and not coming back. This is a departure, not an orbit.")
    ecc = eccentricity(conn)
    low = a * (1.0 - ecc)
    if low < floor:
        return (f"This orbit comes down to {low - hull:,.0f} km. Raise the "
                "low point or you will meet the ground on the far side.")
    if ecc > ORBIT_ECCENTRICITY:
        return (f"Elliptical: {low - hull:,.0f} km at the low point and "
                f"{a * (1 + ecc) - hull:,.0f} at the high. Round it off.")
    # Name the rung as well as the altitude. "Circular at 4,719 km" is a
    # number; "a standard orbit" is the thing the captain chose, and the
    # departure cost and the survey resolution both follow from which one it
    # is rather than from the figure.
    rung = nearest_height(hull, a)
    label = next((lab for hid, lab, _l, _s in ORBIT_HEIGHTS if hid == rung),
                 rung)
    return f"Circular at {a - hull:,.0f} km — a {label.lower()} orbit."


# Deliberately no import of `Conn`: `sim/conn.py` imports this module, so
# naming its type here would close the loop. Everything below reads an
# approach through the same handful of attributes and nothing else.


#: Kilometres in an AU, and how long a held orbit takes to come round — the
#: same devices `anchorage.KM_PER_AU` and `BERTH_DAYS` use on a quay.
KM_PER_AU = 149_597_870.7
#: How far off a structure's centre a hull made fast to it lies, in km:
#: alongside, not inside its skin (the largest berth is 0.4 km round).
MOORED_KM = 0.6
ORBIT_DAYS = 0.5


def ship_orbit_offset(game, body) -> tuple[float, float, float]:
    """Where the hull sits relative to the body it is alongside, in AU.

    **A ship in orbit is not at the planet's core.** `flight.ship_position`
    used to
    return the body's exact position, so every range to the thing you were
    standing at came out zero — the third defect of that shape, after
    `anchorage.berth_orbit` for a quay and `traffic.STATION_KM` for a hull.

    The radius is the one the flight holds (`Game.orbit_alt_km`) or the
    standard rung, so this and the conn's altitude are the same number.
    Derived from the body's identity and the calendar, never stored.
    """
    berth = getattr(game, "berth", "")
    if berth:
        # **Made fast is at the berth**, not on an orbit of one's own: the
        # structure's place (`anchorage.berth_orbit`), and the hull lying
        # `MOORED_KM` off its centre, on the side away from the world.
        from .anchorage import berth_orbit
        at = berth_orbit(berth, body, game.day)
        span = math.sqrt(sum(c * c for c in at)) or 1.0
        grow = 1.0 + MOORED_KM / KM_PER_AU / span
        return tuple(c * grow for c in at)
    radius_km = max(0.0, float(getattr(body, "radius_km", 0.0) or 0.0))
    held = float(getattr(game, "orbit_alt_km", 0.0) or 0.0)
    if held <= 0:
        held = height_km(radius_km, DEFAULT_HEIGHT)
    if held <= 0:
        return 0.0, 0.0, 0.0
    seed = zlib.crc32(str(getattr(body, "id", "")).encode())
    orbit = elements.Elements(
        a=held / KM_PER_AU, e=0.0,
        incl=((seed >> 19) % 1000) / 1000.0 * math.pi,
        node=((seed >> 5) % 3600) / 3600.0 * math.tau,
        peri=0.0, m0=(seed % 3600) / 3600.0 * math.tau)
    return elements.at(orbit, game.day, ORBIT_DAYS)
