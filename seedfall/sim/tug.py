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

import math

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

#: The sphere a tow will not cross, as a share of the structure's radius.
#: A shade outside the skin: the boats walk a hull round the hull, and
#: "round" has to mean clear of it rather than along it.
KEEP_OUT = 1.12

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
    # It has the hull. Walk it in at the tug's own rate, on the tug's own
    # mass — `conn.rcs` is untouched, which is the point.
    #
    # **Down the corridor, not straight at the fitting.** This drew the hull
    # along a chord to the berth from wherever the boats caught it, and the
    # boats come out as far as `TUG_REACH` of the opening range. From the
    # twelve kilometres an approach normally opens at, that chord is
    # harmless. From a run handed over fifty kilometres out on whatever
    # bearing the ship happened to arrive on, it goes *through the
    # structure*: measured, a cleared hull under tow at a Fleet Hub was
    # walked onto the skin 634 m from the mast it had been granted and the
    # log read "the frames took it" — a collision, at nought metres a second,
    # performed by the harbour's own boats.
    #
    # `moorings.aim` is the two-phase route the flight computer is held to —
    # out to the hold point on the berth's own line, and only then in. A tug
    # that ignored it was the one thing in the game allowed to fly a course
    # no captain would be permitted.
    from . import moorings as _m
    at = _m.aim(conn)
    step = TUG_RATE * float(seconds) / 1000.0
    conn.pos = list(_walk(conn.pos, at, step, _keep_out(conn.target)))
    conn.vel = [0.0, 0.0, 0.0]
    conn.towed = round(float(getattr(conn, "towed", 0.0)) + step, 6)
    return conn.tug


def _keep_out(target) -> float:
    """The sphere the boats will not take a hull through, in km."""
    return float(getattr(target, "radius_km", 0.0) or 0.0) * KEEP_OUT


def _walk(pos, at, step: float, safe: float) -> tuple:
    """One step of the tow, round the structure rather than through it.

    **A tow is not a straight line.** The hold point sits barely outside the
    skin — at a Fleet Hub it is 555 m out against a 400 m hull — so a hull
    caught on the far side and drawn straight at it crosses the structure on
    the way. Measured before this: cleared, under tow, granted mast 4, and
    walked onto the plating 579 m short of it at nought metres a second, the
    log reading "the frames took it". The boats did that, not the captain.

    So while the straight line would cut inside the keep-out sphere, the tow
    goes *round*: the hull is swung along the sphere toward the bearing it
    wants, at the radius it already has. Once the line is clear it is drawn
    straight in. That is how a harbour walks a hull, and it is the same
    two-phase discipline `moorings.aim` holds the flight computer to.
    """
    gap = math.dist(pos, at)
    if gap <= 1e-9:
        return tuple(pos)
    # **The sphere may never exclude the place she is going.** The hold point
    # sits just outside the skin and the keep-out just outside that, so at
    # some structures the destination is *inside* the guard — measured at a
    # hub whose hold point is 444 m out against a 448 m keep-out, which
    # forbade every route to it and froze the tow: 2,100 beats, the hull not
    # moving a millimetre while the station turned 136° underneath it. The
    # guard is for the crossing, not for the arrival.
    safe = min(safe, math.dist(at, (0.0, 0.0, 0.0)) * 0.999)
    if step >= gap or not _cuts_inside(pos, at, safe):
        share = min(1.0, step / gap)
        return tuple(p + (a - p) * share for p, a in zip(pos, at))
    out = math.dist(pos, (0.0, 0.0, 0.0))
    reach = max(out, safe)
    if out <= 1e-9:
        return tuple(pos)
    here = [p / out for p in pos]
    want = math.dist(at, (0.0, 0.0, 0.0))
    if want <= 1e-9:
        return tuple(pos)
    there = [a / want for a in at]
    # The part of the destination bearing square to where she lies, which is
    # the direction to swing in.
    dot = sum(h * t for h, t in zip(here, there))
    side = [t - h * dot for t, h in zip(there, here)]
    span = math.dist(side, (0.0, 0.0, 0.0))
    if span <= 1e-9:
        # **Dead in line — and if that line runs through the structure, any
        # way round will do.** Falling back to a straight run here was the
        # hole: a hull on the *far side* is exactly anti-parallel to its
        # berth, which is precisely the case this guard exists for, and it
        # was towed clean through the middle — 12 m from the centre of a
        # 400 m hull. There is a whole circle of ways round; take the one
        # square to the axis she is least parallel to, the way `sim/path`
        # picks a way round a star for the same reason.
        if dot > 0.0:                     # same side, nothing in the way
            share = min(1.0, step / gap)
            return tuple(p + (a - p) * share for p, a in zip(pos, at))
        axis = min(range(3), key=lambda i: abs(here[i]))
        other = [1.0 if i == axis else 0.0 for i in range(3)]
        side = [here[1] * other[2] - here[2] * other[1],
                here[2] * other[0] - here[0] * other[2],
                here[0] * other[1] - here[1] * other[0]]
        span = math.dist(side, (0.0, 0.0, 0.0)) or 1.0
    side = [s / span for s in side]
    arc = min(step / reach, math.acos(max(-1.0, min(1.0, dot))))
    swung = [h * math.cos(arc) + s * math.sin(arc)
             for h, s in zip(here, side)]
    return tuple(c * reach for c in swung)


def _cuts_inside(pos, at, safe: float) -> bool:
    """Would the straight run from here to there pass inside the sphere?"""
    if safe <= 0.0:
        return False
    span = [a - p for p, a in zip(pos, at)]
    length = sum(c * c for c in span)
    if length <= 1e-12:
        return math.dist(pos, (0.0, 0.0, 0.0)) < safe
    t = max(0.0, min(1.0, -sum(p * c for p, c in zip(pos, span)) / length))
    near = [p + c * t for p, c in zip(pos, span)]
    return math.dist(near, (0.0, 0.0, 0.0)) < safe


def tug_line(conn) -> str:
    """What a hull under tow is being told."""
    if not under_tow(conn):
        return ""
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    return (f"{station}'s boats have you. Hands off the drive — they will "
            "walk you in.")

