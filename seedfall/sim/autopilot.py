"""The flight computer: what it would do with the conn, one tick at a time.

Split out of `sim/conn.py`, which holds the physics. The seam is real rather
than a line count: `conn` says what the ship *does* when you fire a thruster,
and this says which thruster a competent pilot would fire. Nothing here
changes state — `autopilot` returns an axis and whether to use the main drive,
and the caller decides whether to take the advice.

Three modes, each a thing a pilot asks for out loud:

* **null** — kill the relative velocity and hold where you are.
* **close** — bring the range down and berth. Across before along: velocity
  across the line of sight is the part that makes you *miss*, and no amount of
  managing the closing rate removes it.
* **orbit** — get across the line of sight at circular speed for the height.

The braking law is the interesting one. See `safe_rate`.
"""

from __future__ import annotations

import math

from .conn import (AXES, ALONGSIDE_KM, ALONGSIDE_RATE, MAIN_DV, RCS_DV, TICK,
                   Conn, apply, can_burn)
from .orbits import ORBIT_FLOOR_KM, orbit_band, orbital_speed
from .conn import _rotate


def autopilot(conn: Conn, mode: str) -> tuple[str | None, bool]:
    """What the flight computer would do this tick: an axis and whether to
    use the main drive. Returning `None` means it would coast.

    Three modes, and each is a thing a pilot asks for out loud:

    * **null** — kill the relative velocity. Burn against the way you have on.
    * **close** — bring the range down, then stop. It hands over to nulling
      once the closing rate is enough for the distance left.
    * **orbit** — get across the line of sight at circular speed.
    """
    if conn.over:
        return None, False
    if mode == "null":
        return _against(conn, conn.vel)
    if mode == "close":
        want = safe_rate(conn)
        # Across before along. Velocity across the line of sight is the part
        # that makes you *miss*, and no amount of managing the closing rate
        # removes it — the first draft only did the latter and hung at 1.7 km
        # circling a hull it never reached, or sailed into a quay sideways at
        # 12 m/s with its closing rate perfectly on profile.
        across = lateral(conn)
        drift = math.dist(across, (0.0, 0.0, 0.0))
        if drift > drift_allowed(conn):
            return _toward(conn, [-a for a in across], drift > MAIN_DV * 0.8)
        error = want - conn.closing
        if error > RCS_DV * 0.5:
            return _toward(conn, [-p for p in conn.pos],
                           error > MAIN_DV * 0.8)
        if error < -RCS_DV * 0.5:
            return _toward(conn, list(conn.pos), -error > MAIN_DV * 0.8)
        # On the profile: let it run and re-check next tick.
        return None, False
    if mode == "orbit":
        want = orbital_speed(conn)
        if want <= 0:
            return _against(conn, conn.vel)
        if conn.range_km < conn.target.radius_km + ORBIT_FLOOR_KM * 1.4:
            return _toward(conn, list(conn.pos), True)     # climb
        # Two errors to null, and the order matters: get the speed right
        # first, then turn what is left across the line of sight.
        band = orbit_band(conn)
        gap = want - conn.speed
        if abs(gap) > band * 0.5:
            return _toward(conn, _across(conn) if gap > 0
                           else [-v for v in conn.vel], abs(gap) > MAIN_DV * 0.8)
        if abs(conn.closing) > band * 0.5:
            # Trade the radial component for tangential: burn across, in the
            # sense that opposes the fall.
            sign = 1.0 if conn.closing > 0 else -1.0
            return _toward(conn, [p * sign for p in conn.pos],
                           abs(conn.closing) > MAIN_DV * 0.8)
        return None, False
    return None, False


def safe_rate(conn: Conn, dv: float = RCS_DV) -> float:
    """The fastest closing rate that can still be stopped in the room left.

    Shedding `dv` a tick, a ship at `v` travels about `TICK · v² / 2dv`
    before it stops, so the rate the remaining distance can absorb is
    `sqrt(2 · dv · d / TICK)`. Two thirds of it, because the thrust comes in
    lumps and the last lump must not be the one that arrives late.

    The first draft capped the rate at a flat 20 m/s instead, which is a fine
    number at ten kilometres and a collision at two hundred metres — the
    autopilot drove into a quay at 70 m/s and called it a berth.
    """
    stop_at = conn.target.radius_km + ALONGSIDE_KM * 0.5
    room = max(0.0, (conn.range_km - stop_at) * 1000.0)
    return max(0.0, math.sqrt(2.0 * dv * room / TICK) * 0.66)


def drift_allowed(conn: Conn) -> float:
    """How much motion across the line of sight to put up with, m/s.

    Tied to what the *arrival* can absorb, not to how far away you are. The
    first draft allowed a share of the closing profile — 2.4 m/s at twelve
    kilometres — which is harmless there and a collision at three hundred
    metres, and the computer never tightened it on the way in. It stalled at
    the threshold and carried the drift all the way to the hull.

    Now it is a half of what counts as berthed, tightening as the room to fix
    it runs out, and floored at one pulse: chasing a drift smaller than the
    thrusters can remove only spends mass.
    """
    return max(RCS_DV, min(ALONGSIDE_RATE * 0.5, safe_rate(conn) * 0.3))


def lateral(conn: Conn) -> list:
    """The part of the velocity across the line of sight, m/s.

    Closing rate is the part along it. Together they are the whole velocity,
    and a pilot has to null both: the first gets you there, the second
    decides whether you arrive or go past.
    """
    r = conn.range_km
    if r < 1e-9:
        return list(conn.vel)
    unit = [p / r for p in conn.pos]
    along = sum(v * u for v, u in zip(conn.vel, unit))
    return [v - along * u for v, u in zip(conn.vel, unit)]


def _across(conn: Conn) -> list:
    """A direction at right angles to the line of sight, in the orbit plane."""
    px, py, pz = conn.pos
    # Prefer the way it is already going, so the computer does not reverse
    # the orbit it is halfway into establishing.
    side = (-py, px, 0.0)
    if sum(a * b for a, b in zip(side, conn.vel)) < 0:
        side = (py, -px, 0.0)
    return list(side)


def _toward(conn: Conn, vec, main: bool) -> tuple[str | None, bool]:
    """The axis whose thrust best points along `vec`."""
    length = math.dist(vec, (0.0, 0.0, 0.0))
    if length < 1e-9:
        return None, False
    want = [v / length for v in vec]
    best, score = None, 0.0
    for axis_id, _label, body_vec in AXES:
        world = _rotate(body_vec, conn.heading)
        dot = sum(a * b for a, b in zip(world, want))
        if dot > score:
            best, score = axis_id, dot
    if best is None:
        return None, False
    ok, _why = can_burn(conn, main)
    if not ok and main:
        main = False
    return best, main


def _against(conn: Conn, vec) -> tuple[str | None, bool]:
    """Burn to cancel a velocity, using the drive only when it is worth it."""
    speed = math.dist(vec, (0.0, 0.0, 0.0))
    if speed < RCS_DV * 0.5:
        return None, False
    return _toward(conn, [-v for v in vec], speed > MAIN_DV * 0.75)


def fly(conn: Conn, mode: str, ticks: int = 240) -> Conn:
    """Hand the conn to the computer until it resolves or the ticks run out.

    This is what the *Engage* button does, and what a check drives to find out
    whether the mode actually works.
    """
    for _ in range(ticks):
        if conn.over:
            break
        axis, main = autopilot(conn, mode)
        apply(conn, axis, main=main)
    return conn
