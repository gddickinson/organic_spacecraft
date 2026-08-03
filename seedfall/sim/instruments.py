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
from .targets import is_open
from . import pilot


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
    if is_open(conn.target):
        # **A free flight is not a slow approach to the place you left.**
        # These three rows used to be the berthing set, and every one of them
        # was answering a question nobody had asked. `conn.range_km` is the
        # distance from the *origin* of the conn's frame, which for an
        # approach is the target and for a free flight is where she let go —
        # so it was labelled "Range" and judged against the 40 km at which a
        # berthing is going badly. Measured on a flight out to a hull: the
        # panel read "Range 8,590.0 km" in amber while the contact the pilot
        # was flying at was 2,968 km off, and "Relative 583.2 m/s" in amber
        # because 583 m/s is a great deal for coming alongside a quay. It is
        # nothing at all for crossing a system, which is what this is.
        #
        # There is no "Closing" row, because out here there is nothing being
        # closed on. Range and bearing to whatever the pilot has laid a course
        # on belong to the screen that holds the mark — `ui/pilot_view` prints
        # them — and putting a second copy here is how two ranges start
        # disagreeing.
        rows = [
            ("Flown", f"{r * 1000:,.0f} m" if r < 2 else f"{r:,.1f} km", "ok"),
            ("Speed", f"{conn.speed:,.1f} m/s", "ok"),
        ]
    elif orbiting:
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
    # What the console is set to. On the panel rather than only under the
    # buttons, because the buttons say "10%" and "5 min" and a bare percentage
    # of a number the pilot cannot see is not information: the throttle is worth
    # reading in m/s, which is the unit every other row is judged in.
    #
    # Always shown, unlike the trim row below. A setting is not an alarm, and a
    # pilot wondering why the drive is barely moving the ship needs to be able
    # to see that it is at a tenth.
    rows.append(("Throttle", f"{conn.throttle * 100:,.0f}% — "
                             f"{pilot.dv_of(conn, True):,.2f} m/s", "ok"))
    rows.append(("Coast", f"{conn.coast_min} min", "ok"))
    # **What has the conn**, on the panel and not only in a button's tint.
    # The armed mode lives on the flight now (`Conn.auto`), so the panel can
    # finally say it — before, the mode was a widget attribute and the sim
    # could not report what it could not see.
    rows.append(("Computer", computer_note(conn), "ok"))
    # **What is in the way**, above everything else a pilot might read. Only
    # when there is something to say: a row that is always "clear" is a row
    # the eye stops going to, which is the fault this panel was rebuilt for.
    from . import collision
    threat = collision.scan(None, conn)
    if threat is not None:
        rows.append(("Collision", f"{threat.name} · "
                                  f"{threat.seconds:,.0f} s · "
                                  f"{threat.closing:,.1f} m/s",
                     collision.tint(threat)))
    if not getattr(conn, "safeties", True):
        rows.append(("Safeties", "OFF — nothing will brake for you", "bad"))

    # And it reads "ok", not "warn". `test_conn.py` caught the first draft
    # marking it amber on fourteen approaches that *succeeded* — which is the
    # very fault this panel was rebuilt to stop. The trim is a fact about the
    # hull, not a fault in the flying: the pilot needs the number, and nothing
    # about a 62% drive makes a good orbit a bad one.
    if conn.hold < 1.0:
        rows.append(("Drive trim", f"{conn.hold * 100:,.0f}% usable", "ok"))
    rows.append(("Elapsed", f"{conn.elapsed / 60:,.0f} min", "ok"))
    return rows


def computer_note(conn: Conn) -> str:
    """One phrase for what the flight computer has been asked to do."""
    mode = getattr(conn, "auto", "")
    if not mode:
        return "off — she flies as you fly her"
    if mode == "null":
        return "holding — killing what drift there is"
    if mode == "close":
        return "closing to berth"
    if mode == "orbit":
        return "making orbit"
    if mode == "run":
        mark = getattr(conn, "mark", "")
        return f"running for {mark}" if mark else "running for nothing"
    if mode == "brake":
        return "braking to zero, then handing back"
    if mode == "depart":
        return ("climbing away to a higher orbit"
                if getattr(conn.target, "mu", 0) > 0 else
                "standing away to clear space")
    return mode
