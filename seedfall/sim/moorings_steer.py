"""Steering onto a berth: where to aim, how fast it moves, which way to push.

Split out of `sim/moorings.py` at 499 lines. What stays there is the berth
itself — where the fittings are, how a structure turns, which berth is
nearest, and the boom that takes a hull at a standoff. What is here is flying
to one: the aim the flight computer holds and the panel's arrows point at,
the lead on a fitting that is going round, and the rates measured against
the berth rather than the structure's centre. `moorings` re-exports every
name, so `moorings.aim` and `moorings.rates` answer where they always did.
"""

from __future__ import annotations

import math


def _m():
    """`sim/moorings`, imported late: it re-exports this module's names, so a
    module-level import in this direction is a cycle whichever loads first."""
    from . import moorings
    return moorings


def aim(conn) -> tuple:
    """Where an approach is actually flying, in the target's frame.

    **One door, because the computer and the pilot must be given the same
    answer.** `sim/autopilot.py` flies to this and `steer` points at it, so
    the arrows on the manual panel are the course the flight computer would
    hold — a panel that guided somewhere else would be worse than no panel.

    Two phases, and the handover is on *reaching the hold point*, not on
    crossing a radius. Aiming straight at a fitting means flying through
    whatever is between here and it: measured with the computer, two of eight
    off-axis approaches ran the tanks dry shuffling round a hub; measured by
    hand, a pilot pressing toward the mast put the hull into the skin 477 m
    short of it at nine metres a second. So the corridor is a *place* — out
    on the berth's own line and clear of the hull — and the run in only
    begins from there.
    """
    found = _m().nearest(conn)
    if found is None:
        return (0.0, 0.0, 0.0)
    at = lead(conn, found)
    out = math.dist(at, (0.0, 0.0, 0.0))
    if out < 1e-9:
        return at
    hold = _m().corridor_km(conn.target)
    from . import bays
    if bays.is_bay(getattr(conn.target, "berth", "") or ""):
        # A bay is flown through its mouth, not at its berth — the corridor
        # law lives with the corridor, `bays.approach_aim`; None means she
        # is inside the way in and the berth itself is the aim.
        way_in = bays.approach_aim(conn, hold, _m().spin_of(conn))
        return at if way_in is None else way_in
    point = tuple(c * hold / out for c in at)
    if math.dist(conn.pos, point) > _m().reach_km(conn.target):
        return around(conn, point, hold)
    return at


#: The least a waypoint round a structure turns the aim, in radians — so a
#: hull already at the hold point's distance on the wrong side still walks
#: round rather than holding where it is.
ROUND_STEP = math.radians(25.0)


def around(conn, point, hold: float) -> tuple:
    """The hold point — or, when the straight run to it would cross the
    structure, a waypoint round the side.

    **The corridor leg was a straight line to a point on the far side.** A
    Fleet Hub's masts sit on its pole, so that line seldom crossed anything;
    a free port puts one arm out sideways, and an approach from the other
    side flew straight through the station to reach it — measured, the
    computer met a Grand's skin at 2.5 m/s, 597 m from the arm, with the
    berth cleared and assigned. So the aim goes round: at the hold point's
    distance, turned from the hull's own bearing toward the hold point by as
    far as the line from the hull can reach without coming within
    `bays.CLEARANCE` of the solid core (`bays.hull_km`), and never less
    than `ROUND_STEP`. Asked afresh every
    tick, it walks round ahead of the hull until the way in is clear.
    """
    from . import bays
    pos = tuple(conn.pos)
    core = bays.hull_km(conn.target) * bays.CLEARANCE
    if bays.chord_km(pos, point) > core:
        return point
    dist = math.dist(pos, (0.0, 0.0, 0.0))
    if dist < 1e-9:
        return point
    u = tuple(c / dist for c in pos)
    w = tuple(c / hold for c in point)
    gap = math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(u, w)))))
    turn = min(gap, max(ROUND_STEP, math.acos(min(1.0, hold / dist))))
    return tuple(c * hold for c in _slerp(u, w, turn, gap))


def _slerp(u, w, turn: float, gap: float) -> tuple:
    """`u` turned `turn` radians toward `w` (`gap` apart), as a unit vector.
    Dead opposite, any way round will do: it goes over the top."""
    side = tuple(b - a * math.cos(gap) for a, b in zip(u, w))
    size = math.dist(side, (0.0, 0.0, 0.0))
    if size < 1e-9:
        pole = (0.0, 0.0, 1.0) if abs(u[2]) < 0.9 else (1.0, 0.0, 0.0)
        dot = sum(a * b for a, b in zip(u, pole))
        side = tuple(p - a * dot for a, p in zip(u, pole))
        size = math.dist(side, (0.0, 0.0, 0.0))
    v = tuple(c / size for c in side)
    return tuple(a * math.cos(turn) + b * math.sin(turn) for a, b in zip(u, v))


def lead(conn, found=None) -> tuple:
    """Where the berth **will be** when the ship gets there, in km.

    A structure turns, so a fitting is not where it was by the time a hull has
    crossed the last few hundred metres — a hub's berth walks at a metre a
    second and a slow approach takes minutes. Aiming at where it is now is how
    a pilot arrives beside a berth that has gone round: measured, an arrival
    at half a metre a second that used to moor became a collision, and a
    hand-flown approach from the corridor did the same.

    So lead it, the way anyone throws to a moving target: how long the run in
    will take at the speed being made good, and where the berth has turned to
    by then. One pass rather than a solve, because the berth moves slowly
    against the closing rate and a second pass moves the answer by less than
    the reach it is aiming inside.
    """
    found = found or _m().nearest(conn)
    if found is None:
        return (0.0, 0.0, 0.0)
    period = _m().turn_seconds(conn.target)
    gap = found["km"]
    if period <= 0.0 or gap <= 0.0:
        return found["at"]
    # The speed actually being made good at the berth, floored so a ship that
    # has stopped does not ask for an infinite lead.
    pace = max(abs(getattr(conn, "closing", 0.0)), 0.05)
    ahead = min(gap / pace, period * 0.25)
    return where_at(conn, ahead, found["name"])


def where_at(conn, ahead: float, name: str = "") -> tuple:
    """Where a berth will be `ahead` seconds from now, in km.

    **The one door for a moving fitting**, because everything that has to hit
    one needs the same answer: the flight computer leading its aim, the manual
    panel's arrows, and a ballistic arrival that has to be pointed at where
    the berth *will be* rather than where it is.
    """
    want = name or (_m().nearest(conn) or {}).get("name", "")
    berths = _m()
    turned = berths.points(conn.target,
                           berths.spin_at(conn.target,
                                          getattr(conn, "elapsed", 0.0)
                                          + float(ahead)))
    for berth, at in turned:
        if berth == want:
            return at
    return turned[0][1] if turned else (0.0, 0.0, 0.0)


def berth_velocity(conn, found=None) -> tuple:
    """How fast the berth itself is travelling, in m/s, and which way.

    A fitting on a turning structure is moving: `ω × r`, straight out of the
    rotation. Nothing needed this while stations were static, and everything
    needs it now.
    """
    found = found or _m().nearest(conn)
    period = _m().turn_seconds(conn.target)
    if found is None or period <= 0.0:
        return (0.0, 0.0, 0.0)
    omega = math.tau / period                      # radians a second
    x, y, _z = found["at"]                         # km from the pole
    # v = ω × r with ω along the structure's own pole, in m/s.
    return (-omega * y * 1000.0, omega * x * 1000.0, 0.0)


def rates(conn) -> dict:
    """Closing and cross rates **relative to the berth**, in m/s.

    **The instruments a rotating station makes necessary.** `conn.closing` and
    `autopilot.lateral` are measured against the target's *centre*, which is
    the right frame for a structure that sits still and the wrong one for a
    fitting that is going round: a hull perfectly matched to a moving berth
    still reads a metre a second of lateral drift, and a pilot — or a check's
    pilot — told to null it will fight the rotation for ever instead of
    joining it.

    Measured: a hand-flown approach to a turning quay spent its whole budget
    nulling and arrived 482 m from the fitting. The instruction is not *kill
    the drift*, it is *match the berth*.
    """
    found = _m().nearest(conn)
    if found is None:
        return {"closing": getattr(conn, "closing", 0.0), "cross": 0.0,
                "gap_km": 0.0, "berth_speed": 0.0}
    theirs = berth_velocity(conn, found)
    rel = [v - b for v, b in zip(conn.vel, theirs)]
    toward = [a - p for a, p in zip(found["at"], conn.pos)]
    gap = math.dist(toward, (0.0, 0.0, 0.0))
    if gap < 1e-9:
        return {"closing": 0.0, "cross": math.dist(rel, (0.0, 0.0, 0.0)),
                "gap_km": 0.0,
                "berth_speed": math.dist(theirs, (0.0, 0.0, 0.0))}
    line = [c / gap for c in toward]
    closing = sum(r * c for r, c in zip(rel, line))
    across = [r - closing * c for r, c in zip(rel, line)]
    return {"closing": closing,
            "cross": math.dist(across, (0.0, 0.0, 0.0)),
            "gap_km": gap,
            "berth_speed": math.dist(theirs, (0.0, 0.0, 0.0))}


def steer(conn) -> dict:
    """Which of the ship's own thrusters push it toward the berth.

    **Because a manual docking panel that does not say which way the berth
    lies is not flyable.** Measured, flying one by hand: a pilot pressing
    *ahead* — the nose, which points at the middle of the structure — put the
    hull into the skin 477 m from the mast at nine metres a second. The berth
    is somewhere off the bow, and the pad is in the ship's frame, so the two
    have to be brought together somewhere. Here, once, off `conn.thrust_axis`
    — the same function the burn itself uses, so a button this calls helpful
    is a button that helps.

    Returns each axis id against how much of a push along it goes toward the
    berth: +1 straight at it, −1 straight away, 0 across.
    """
    from . import conn as conn_sim

    if _m().nearest(conn) is None:
        return {}
    want = [a - p for a, p in zip(aim(conn), conn.pos)]
    span = math.dist(want, (0.0, 0.0, 0.0))
    if span < 1e-9:
        return {}
    want = [c / span for c in want]
    out = {}
    for axis_id, _label, _vec in conn_sim.AXES:
        push = conn_sim.thrust_axis(conn, axis_id, False)
        out[axis_id] = sum(w * p for w, p in zip(want, push))
    return out
