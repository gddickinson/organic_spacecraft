"""How an approach ends: alongside, in orbit, aground, or drifted away.

Lifted out of `sim/conn.py`, which took the file past five hundred lines. The
seam is a real one rather than a line count: `conn` answers *what the ship
does* when you fire a thruster, and this answers *whether the approach is
over* — a question asked once a tick, about the state the physics has just
produced, and one that has proved much subtler than it looks.

Three of the four outcomes are about a distance. The fourth is not: an orbit
is a shape, and asking about it at an instant is the mistake that took four
control laws and three contradicting screens to find. See `orbits.in_orbit`.
"""

from __future__ import annotations

from .orbits import in_orbit, semi_major_km

#: How near the height you asked for counts as arriving at it. Wider than the
#: autopilot's own tolerance, so the flight computer settles inside the band
#: rather than chasing an edge it can never quite hold.
ORBIT_HEIGHT_SLACK = 0.035


def at_wanted_height(conn) -> bool:
    """Is this the orbit that was actually asked for?

    Without this the approach ended the instant the ship was in *any* orbit,
    which is why a captain could not choose one: asked for a standard orbit
    from an arrival 400 km up, the conn resolved at the first circular pass it
    fell into and reported success 21% low. Asked for a high one, 59% low. An
    orbit you cannot choose the height of is not a choice, and a screen that
    says "orbit" while sitting somewhere else is worse than no screen.
    """
    want = conn.orbit_want_km
    if want <= 0:
        return True                 # no height asked for: anywhere will do
    # The orbit's own size, not where the ship is on it — see
    # `orbits.semi_major_km`. Asked against the instantaneous range, a ship in
    # a perfectly sound orbit at the right mean height read several per cent
    # out depending on which part of it you caught, and never arrived.
    return abs(semi_major_km(conn) - want) <= max(want * ORBIT_HEIGHT_SLACK,
                                                  1.0)


def impact_damage(speed: float, safe_closing: float, base: float) -> float:
    """What hitting something at this speed takes off the hull.

    Quadratic and uncapped. A cap is what let a five-kilometre-a-second
    lithobraking manoeuvre cost less than a bad week in the Bloom.
    """
    if speed <= 0:
        return 0.0
    return round((speed / safe_closing) ** 2 * base, 1)


def alongside(conn, alongside_km: float, alongside_rate: float) -> bool:
    """Near enough and slow enough to call it a berth."""
    if conn.target.kind == "body":
        return False          # a world is orbited, not moored to
    return (conn.range_km <= alongside_km + conn.target.radius_km
            and conn.speed <= alongside_rate)


def resolve(conn, *, safe_closing: float, impact_base: float,
            alongside_km: float, alongside_rate: float,
            adrift_multiple: float) -> None:
    """Has this ended? Writes `conn.outcome`, and the damage if any.

    The thresholds come in from `sim/conn.py` rather than being duplicated
    here. This module decides *which question* to ask; the numbers stay in one
    place, because a constant written twice is the fault this project has been
    bitten by more than any other.
    """
    r = conn.range_km
    hull = conn.target.radius_km

    def hurt(speed: float) -> float:
        return impact_damage(speed, safe_closing, impact_base)

    if conn.target.kind == "body":
        if r <= hull:
            conn.outcome = "aground"
            conn.damage = hurt(conn.speed)
            conn.log.append(
                f"The hull is down on {conn.target.name} at "
                f"{conn.speed:,.0f} m/s. That was not a landing.")
            return
        if in_orbit(conn) and at_wanted_height(conn):
            conn.outcome = "orbit"
            conn.log.append(
                f"Orbit at {r - hull:.0f} km, "
                f"{conn.speed:.0f} m/s. The drive can rest.")
            return
    elif r <= hull:
        speed = conn.speed
        if speed <= safe_closing:
            conn.outcome = "alongside"
            conn.log.append(f"Alongside {conn.target.name}.")
        else:
            conn.outcome = "collision"
            conn.damage = hurt(speed)
            conn.log.append(
                f"{conn.target.name} at {speed:,.0f} m/s — the frames took it.")
        return

    if alongside(conn, alongside_km, alongside_rate):
        conn.outcome = "alongside"
        conn.log.append(
            f"Station held on {conn.target.name}: {r * 1000:.0f} m, "
            f"{conn.speed:.1f} m/s relative. Lines across.")
        return

    # Drifting away is measured against where the approach opened — but a
    # captain who asks for a high orbit is *supposed* to end up a long way
    # out, and at a small body the high rung is nearly four times the arrival
    # range. So the yardstick is whichever is further: where we started, or
    # where we were told to go. Without this, climbing to the orbit the screen
    # had just offered was reported as losing the target astern.
    limit = max(conn.start_km, conn.orbit_want_km) * adrift_multiple
    if r > limit:
        conn.outcome = "adrift"
        conn.log.append(
            f"{conn.target.name} is {r:,.0f} km astern and opening. "
            "The approach is off.")
