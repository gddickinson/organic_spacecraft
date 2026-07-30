"""The conn's panel: what the pilot reads while flying.

Split out of `sim/conn.py`, which does the flying. Each row is judged against
what the approach is actually trying to do — the first draft judged them all
against berthing, so a ship correctly established in a 360 km orbit at 5,728
m/s had its range and its speed both marked in red: the two numbers it had
just got right. A panel that cries wolf at a good orbit teaches the pilot to
ignore it.
"""

from __future__ import annotations

from .conn import (ALONGSIDE_RATE, MAIN_COST, SAFE_CLOSING, Conn)
from .orbits import ORBIT_FLOOR_KM, in_orbit, orbit_band, orbital_speed


def readout(conn: Conn) -> list[tuple[str, str, str]]:
    """The instrument panel: label, value, and how it reads (ok/warn/bad).

    Each row is judged against what the *approach* is trying to do. The first
    draft judged them all against berthing, so a ship correctly established in
    a 360 km orbit at 5,728 m/s had its range and its speed both marked in
    red — the two numbers it had just got right. A panel that cries wolf at a
    good orbit teaches the pilot to ignore it.
    """
    orbiting = conn.target.mu > 0
    r = conn.range_km
    if orbiting:
        want = orbital_speed(conn)
        band = orbit_band(conn)
        altitude = r - conn.target.radius_km
        # A sound orbit is the answer to both of these rows, so ask *the
        # orbit* rather than the instant. The pair of instantaneous tests
        # below them are true of a good orbit only at its apses: once
        # `in_orbit` learned to judge the ellipse, a ship correctly
        # established at 9,123 m/s had the speed it had just got right marked
        # in amber, on five of twelve approaches. The same fault, and the same
        # fix, as `orbits.orbit_note`.
        sound = in_orbit(conn)
        rows = [
            ("Altitude", f"{altitude:,.0f} km",
             "ok" if altitude >= ORBIT_FLOOR_KM else "bad"),
            ("Closing", f"{conn.closing:+,.1f} m/s",
             "ok" if sound or abs(conn.closing) <= band else "warn"),
            ("Relative", f"{conn.speed:,.1f} m/s",
             "ok" if sound or abs(conn.speed - want) <= band else "warn"),
            ("Circular here", f"{want:,.0f} m/s", "ok"),
        ]
    else:
        rows = [
            ("Range", f"{r * 1000:,.0f} m" if r < 2 else f"{r:,.1f} km",
             "ok" if r < 40 else "warn"),
            ("Closing", f"{conn.closing:+,.1f} m/s",
             "bad" if conn.closing > SAFE_CLOSING else "ok"),
            ("Relative", f"{conn.speed:,.1f} m/s",
             "ok" if conn.speed <= ALONGSIDE_RATE else "warn"),
        ]
    rows.append(("Thruster mass", f"{conn.rcs:,.1f}",
                 "bad" if conn.rcs < MAIN_COST else "ok"))
    # Only when there is something to say. A hull whose drive is on the
    # centreline reads 100% forever, and a row that is always fine is a row the
    # pilot learns to skip — the same fault as crying wolf at a good orbit.
    # But a pilot whose throttle silently refuses to open past six tenths needs
    # to be told it is the missing engine and not a fault in the drive.
    # And it reads "ok", not "warn". `test_conn.py` caught the first draft
    # marking it amber on fourteen approaches that *succeeded* — which is the
    # very fault this panel was rebuilt to stop. The trim is a fact about the
    # hull, not a fault in the flying: the pilot needs the number, and nothing
    # about a 62% drive makes a good orbit a bad one.
    if conn.hold < 1.0:
        rows.append(("Drive trim", f"{conn.hold * 100:,.0f}% usable", "ok"))
    rows.append(("Elapsed", f"{conn.elapsed / 60:,.0f} min", "ok"))
    return rows
