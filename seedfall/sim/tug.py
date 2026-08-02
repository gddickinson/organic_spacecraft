"""The boats that come out and walk you in.

Split out of `sim/control.py` when that went past five hundred lines, along a
seam the file had already drawn for itself — its own banner said "the tug", and
nothing above the banner called anything below it.

**This is the other side of the ledger, and the reason clearance is worth
asking for** rather than merely a gate to get past. `sim/control` is what a
structure does about a hull it does not want: the ladder, the sheer, the
standing off. This is what it does for one it does want.

The constants came with it, because nothing else reads them — unlike the split
of `sim/conn`, where five constants had eleven readers between them and had to
stay put. They are swept by `tests/tripwire.py` under this module's own name
now, and its fast path is recorded in `tests/test_tripwire.MEASURED`.
"""

from __future__ import annotations

from .control import step, welcome
#: The port level at which a structure keeps tugs. A wayside quay has one arm
#: and a docking light; somewhere a fleet lives has boats.
TUG_FROM = 2

#: How long a tug takes to come out and get a line on you, in seconds.
TUG_SECONDS = 240.0

#: How fast it draws a hull in once it has one, in metres a second. Under the
#: rate any structure allows, because a tug that had to be *caught* would be
#: one more thing to fly at.
TUG_RATE = 0.9

#: How much faster than the berthing rate a hull may still be moving and have
#: the boats get a line on it.
#:
#: This is what the tug is *for*. At three times the rate it caught only a hull
#: that had already braked itself to a standstill, and saved 0.04 t of a 0.98 t
#: approach — a service nobody would wait for. At eight it catches one that
#: arrives at the corridor with way still on, which is the burn a captain would
#: otherwise have to make and the whole reason to ask for boats.
TUG_CATCH = 8.0

#: How far out the boats will come, as a share of where the approach opened.
#:
#: The trade this buys is the point of the whole thing: the tug is **free and
#: slow** against **fast and expensive**. At 0.9 m/s a tug takes a couple of
#: hours to walk a hull in from the opening range, and it costs the ship
#: nothing at all — so a captain in a hurry burns, and one with more time than
#: reaction mass waits.
TUG_REACH = 0.9


def has_tug(game, contact) -> bool:
    """Does this structure keep boats?"""
    if getattr(contact, "kind", "") != "anchorage":
        return False
    system = getattr(game, "system", None)
    port = getattr(system, "port", None) if system is not None else None
    return bool(port is not None and port.level >= TUG_FROM)


def under_tow(conn) -> bool:
    """Has a tug got a line on this hull?"""
    return float(getattr(conn, "tug", 0.0)) >= 1.0


def tug_step(conn, seconds: float) -> float:
    """Bring the tug out, and once it is out, bring the hull in. Returns 0..1.

    The same shape as `moorings.boom_step`, and for the same reason: it is
    something the *structure* does while the ship holds still, so it runs out
    while the hull is steady and lets go when it is not. A captain who keeps
    burning is a captain the boats cannot get a line on.

    **What it buys is reaction mass.** The tug's own drive does the work, so a
    hull that waits is berthed for nothing — which is the whole of why being
    cleared is worth having rather than a formality to be got past.
    """
    said = getattr(conn, "cleared", None)
    if said is None or not getattr(said, "tug", False) or not welcome(conn):
        conn.tug = 0.0
        return 0.0
    from . import moorings
    found = moorings.nearest(conn)
    steady = moorings.rates(conn)
    # The boats come out to meet you, not merely to the corridor. Measured:
    # catching a hull only at the hold point saved 8% of an approach, because
    # nearly all of the mass goes into *reaching* the corridor rather than
    # into the last five hundred metres. Meeting it where the approach opens
    # is what makes waiting a decision instead of a rounding error.
    reach = max(moorings.corridor_km(conn.target),
                float(getattr(conn, "start_km", 0.0)) * TUG_REACH)
    if found is None or found["km"] > reach:
        conn.tug = max(0.0, float(getattr(conn, "tug", 0.0))
                       - float(seconds) / TUG_SECONDS)
        return conn.tug
    if abs(steady.get("closing", 0.0)) > moorings.hold_rate(conn.target) * TUG_CATCH:
        # Still coming in hard: nothing is getting a line on that.
        conn.tug = max(0.0, float(getattr(conn, "tug", 0.0))
                       - float(seconds) / TUG_SECONDS)
        return conn.tug
    conn.tug = min(1.0, float(getattr(conn, "tug", 0.0))
                   + float(seconds) / TUG_SECONDS)
    if conn.tug < 1.0:
        return conn.tug
    # It has the hull. Walk it to the berth at the tug's own rate, on the
    # tug's own mass — `conn.rcs` is untouched, which is the point.
    at = found["at"]
    gap = found["km"]
    step = min(gap, TUG_RATE * float(seconds) / 1000.0)
    if gap > 1e-9:
        share = step / gap
        conn.pos = [p + (a - p) * share for p, a in zip(conn.pos, at)]
    conn.vel = [0.0, 0.0, 0.0]
    conn.towed = round(float(getattr(conn, "towed", 0.0)) + step, 6)
    return conn.tug


def tug_line(conn) -> str:
    """What a hull under tow is being told."""
    if not under_tow(conn):
        return ""
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    return (f"{station}'s boats have you. Hands off the drive — they will "
            "walk you in.")

