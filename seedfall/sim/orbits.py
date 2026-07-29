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


# ── how high an orbit ──────────────────────────────────────────────────────
#
# There was one orbit, and it was wherever you happened to be when you asked
# for it: `autopilot` circularised at the current range and `game.orbit_body`
# recorded *which* body without a word about how far off. So every orbit in
# the game was the same orbit, and the only number that decided it was where
# the transfer happened to drop you.
#
# A height is worth choosing only if the choice costs something. It does, and
# the arithmetic is not invented: the speed you must throw away to leave is
# sqrt(2·mu/r), so a low orbit is dearer to leave than a high one by the
# square root of the ratio of their radii. That is the whole trade — low sees
# more and costs more to quit, high is cheap to hold and quit and shows you
# less.

#: The ladder, as (id, label, altitude above the orbit floor).
#:
#: Measured from the floor rather than from the surface, and additive rather
#: than multiplicative, because a rock and a gas giant differ by two hundred
#: times in radius and any single scheme keyed on one of them inverts on the
#: other. An asteroid's floor is 80 km up and a giant's is 80 km up; what
#: differs is how much room there is above it, which is what `share` reads.
#: The middle rung is `targets.approach_range` exactly — see `height_km`.
#: The outer two are as far apart as the physics allows: a body's surface is
#: at zero, so a low orbit can only ever be a little under the standard one,
#: while a high orbit can be most of a radius further out. That asymmetry is
#: not a design choice, it is where the ground is.
ORBIT_HEIGHTS = (
    ("low", "Low", 1.5, 0.02),
    ("standard", "Standard", 4.0, 0.10),
    ("high", "High", 20.0, 0.80),
)

#: The height an orbit is held at when nobody says otherwise.
DEFAULT_HEIGHT = "standard"

#: How sharply what you can see falls off with height.
#:
#: Well under 1. The honest optical figure is 1 — resolved ground scale is
#: linear in range — but a low orbit is already about 2.4 times closer than a
#: high one at a world, and a linear benefit would make a low orbit strictly
#: correct every time for a tenth more fuel. At 0.45 a low orbit resolves
#: about a fifth more than standard and a high one about a fifth less, which
#: is worth choosing between rather than obvious.
LOOK_EXPONENT = 0.45


def height_km(radius_km: float, height_id: str) -> float:
    """The radius from the body's centre, in km, for a named height.

    `radius + max(floor · lift, radius · share)`, which is deliberately the
    same shape as `targets.approach_range` — and the standard rung is exactly
    it, so **a transfer drops you at the standard orbit** and low and high
    are each a real piece of flying away from it.

    That matching is the whole of why this is written the way it is. A first
    draft scaled the ladder off the orbit floor alone, which put a comet's
    three heights at 97, 108 and 151 km when the transfer arrives at 335 —
    every rung below where the ship starts, all three within a whisker of
    each other, and the autopilot chasing a descent it could not fly. The two
    formulae have to agree or the ladder is somewhere the captain is not.

    Monotone by construction: both terms only grow along the ladder.
    """
    radius_km = max(0.0, radius_km)
    for hid, _label, lift, share in ORBIT_HEIGHTS:
        if hid == height_id:
            return radius_km + max(ORBIT_FLOOR_KM * lift, radius_km * share)
    return radius_km + max(ORBIT_FLOOR_KM * 4.0, radius_km * 0.10)


def heights(radius_km: float) -> list[tuple[str, str, float]]:
    """Every height for a body: (id, label, radius from centre in km)."""
    return [(hid, label, height_km(radius_km, hid))
            for hid, label, _lift, _share in ORBIT_HEIGHTS]


def holdable(mu: float, r_km: float, pulse: float) -> bool:
    """Could a ship whose thrusters come in `pulse`-sized lumps hold this?

    Not every body can be orbited to order. A four-kilometre comet has a
    circular speed of about two metres a second; a hull's attitude clusters
    move it half a metre at a time. Asking such a ship to hold a particular
    orbit there is asking it to steer with an instrument coarser than the
    thing being steered, and it cannot be done — measured, every comet under
    twenty kilometres failed to reach any height asked of it, at every gain
    and every control law tried.

    The bound is derived rather than fitted. An orbit counts as one below
    `ORBIT_ECCENTRICITY`, which at circular speed `v` is a velocity budget of
    `v · e`; the ship needs at least a couple of pulses of authority inside
    that budget to converge on it rather than clatter across it. So
    `v · e ≥ 2 · pulse`.
    """
    if mu <= 0 or r_km <= 0:
        return False
    v = math.sqrt(mu / r_km) * 1000.0
    return v * ORBIT_ECCENTRICITY >= 2.0 * max(pulse, 1e-9)


def heights_for(target, pulse: float) -> list[tuple[str, str, float]]:
    """The heights *this* ship can actually hold at *this* body.

    What the conn should offer. Where nothing is holdable the answer is an
    empty list, and the honest thing for a screen to say is that this body
    cannot be orbited to order — which is not a failure, it is a four
    kilometre lump of ice.
    """
    return [row for row in heights(getattr(target, "radius_km", 0.0))
            if holdable(getattr(target, "mu", 0.0), row[2], pulse)]


def nearest_height(radius_km: float, r_km: float) -> str:
    """Which rung of the ladder a given radius is closest to."""
    return min(heights(radius_km), key=lambda row: abs(row[2] - r_km))[0]


def departure_factor(radius_km: float, r_km: float) -> float:
    """What leaving costs from here, against leaving from a standard orbit.

    `sqrt(2·mu/r)` is the speed you must find to escape, so the ratio between
    two orbits is the square root of the inverse ratio of their radii — and
    `mu` cancels, which is why this needs only the geometry. A low orbit runs
    about a tenth dearer and a high one about a quarter cheaper.
    """
    standard = height_km(radius_km, DEFAULT_HEIGHT)
    if r_km <= 1e-6 or standard <= 1e-6:
        return 1.0
    return math.sqrt(standard / r_km)


def look_factor(radius_km: float, r_km: float) -> float:
    """How much better this height sees than a standard orbit does.

    The other half of the trade, and the reason to pay the departure cost. A
    survey run from close in resolves more than one run from a long way out,
    which is not a game rule so much as an optical one.
    """
    standard = height_km(radius_km, DEFAULT_HEIGHT)
    if r_km <= 1e-6 or standard <= 1e-6:
        return 1.0
    return (standard / r_km) ** LOOK_EXPONENT


# Deliberately no import of `Conn`: `sim/conn.py` imports this module, so
# naming its type here would close the loop. Everything below reads an
# approach through the same handful of attributes and nothing else.


# Deliberately no import of `Conn`: `sim/conn.py` imports this module, so
# naming its type here would close the loop. Everything below reads an
# approach through the same handful of attributes and nothing else.
