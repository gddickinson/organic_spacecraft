"""One tick of time, and what the hull runs into during it.

Split out of `sim/conn.py` when that went past five hundred lines, along a seam
that was already there. `conn` is the pilot's side — the console, the axes, the
throttle, what a burn costs and whether there is mass to pay. This is the
other side: given a hull with a velocity, how far does a minute of it carry
her, and does she touch anything on the way.

**Only `conn.apply` calls in here**, and it calls exactly one thing, `step`.
Everything else is the arithmetic of that.

The constants stay in `sim/conn`, where eleven other modules already read them
— `ALONGSIDE_RATE` alone is read by `autopilot`, `moorings`, `clearance`,
`instruments` and the flight window. Moving them here to keep the file tidy
would have made `sim/conn` re-export them, and a re-export is a second door.
So this module imports them from there, and `apply` imports this lazily, the
way it already imports `sim/attitude`.
"""

from __future__ import annotations

import math

from . import outcome as outcome_sim
from .conn import (ADRIFT_MULTIPLE, ALONGSIDE_KM, ALONGSIDE_RATE, Conn,
                   IMPACT_BASE, SAFE_CLOSING)


def _substeps(conn: Conn, dt: float) -> int:
    """How finely to cut a tick so the orbit is not integrated into nonsense.

    A ship in a low orbit crosses a good fraction of it in a minute, and one
    Euler step across that arc adds energy every time — the ship climbs out
    of an orbit it is actually in. Cutting the tick until it moves under a
    hundredth of its radius keeps it honest, and costs nothing anywhere else
    because a hull alongside a quay needs exactly one.
    """
    if conn.target.mu <= 0:
        return 1
    r = conn.range_km
    if r <= 1e-6:
        return 1
    travel = (conn.speed / 1000.0) * dt            # km this tick
    return int(min(120, max(1, math.ceil(travel / (r * 0.01)))))


def _sweep_min(a, b) -> float:
    """The nearest the straight path from `a` to `b` comes to the origin.

    Without this, contact is only ever tested at the *endpoints* of a tick,
    and a ship fast enough to cross the target inside one minute goes clean
    through it. Measured: an approach at 45 m/s covers 2.7 km a tick, passed
    through a station 400 m across, and was reported **adrift** — no impact,
    no damage, the hull untouched. Since impact damage is quadratic, the
    fastest and most dangerous approaches were precisely the ones escaping.
    """
    ax, ay, az = a
    dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
    span = dx * dx + dy * dy + dz * dz
    if span < 1e-18:
        return math.dist(a, (0.0, 0.0, 0.0))
    # Where along the segment the closest point falls, clamped to it.
    t = -(ax * dx + ay * dy + az * dz) / span
    t = max(0.0, min(1.0, t))
    return math.dist((ax + dx * t, ay + dy * t, az + dz * t),
                     (0.0, 0.0, 0.0))


def step(conn: Conn, dt: float) -> None:
    """Integrate one tick: gravity, then motion, then see what we hit.

    Velocity first, then position, from the *new* velocity — semi-implicit,
    which is what keeps a closed orbit closed instead of slowly unwinding.
    """
    subs = _substeps(conn, dt)
    h = dt / subs
    # **The ladder runs on the tick, not the substep.** `_substeps` exists to
    # keep the *integrator* honest and cuts a minute into up to 120 slices
    # near a body — and the structure's patience and its point defence used
    # to run once per slice, so a warded approach to a world was bitten a
    # hundred and twenty times the damage of the same minute at a quay, and
    # the hail→warn→ward ladder climbed through its grace in half a tick.
    # Patience is about minutes, and it is spent out here where a minute is a
    # minute.
    from . import control
    said = control.step(conn, conn.closing > 0.0)
    if said:
        conn.log.append(said)
    bite = control.ward_bite(conn)
    if bite > 0.0:
        conn.warded_for += 1
        conn.damage = round(conn.damage + bite, 1)
    for _ in range(subs):
        was = list(conn.pos)
        r = conn.range_km
        if conn.target.mu > 0 and r > 1e-6:
            # Newton, in km and seconds, converted to the m/s velocity is in.
            pull = conn.target.mu / (r * r)            # km/s²
            for i in range(3):
                conn.vel[i] -= (conn.pos[i] / r) * pull * h * 1000.0
        for i in range(3):
            conn.pos[i] += conn.vel[i] * h / 1000.0    # m/s · s → km
        conn.elapsed += h
        # The boom, if this is a berth with one: it runs out while the hull
        # holds station off it, and back in the moment it does not.
        from . import moorings
        moorings.boom_step(conn, h)
        from . import tug as tug_sim
        # And a structure with somebody aboard simply leaves. See
        # `control.sheer_step`: the range opens because the berth is going,
        # not because the ship is being pushed.
        control.sheer_step(conn, h)
        # And the other side of it: a structure that wants you sends boats.
        tug_sim.tug_step(conn, h)
        # And a hull that was refused and stayed anyway, cutting. The ward
        # above does not pause for it — that is the whole of what makes a
        # well-defended dock unforcible. See `sim/forcing.py`.
        from . import forcing as forcing_sim
        forcing_sim.force_step(conn, h)
        # Contact anywhere along the path, not merely at the end of it — and
        # against what is *solid*, which is not the bounding radius. See
        # `sim/bays.hull_km`: a structure's furniture is what you berth
        # against, and seven holdings had their berths inside the sphere this
        # line used to test. A hull inside the way in touches nothing.
        from . import bays
        if (_sweep_min(was, conn.pos) <= bays.hull_km(conn.target)
                and not bays.in_corridor(conn, moorings.spin_of(conn))):
            _touch(conn)
            if conn.over:
                return
        _resolve(conn)
        if conn.over:
            return


def _touch(conn: Conn) -> None:
    """Put the ship on the target's skin, so contact is resolved there.

    The tick has already carried it past; this walks it back to where it
    actually met the hull, which is the position every reading and every log
    line should be quoting.
    """
    from . import bays
    r = conn.range_km
    skin = max(bays.hull_km(conn.target), 1e-6)
    if r > 1e-9:
        conn.pos = [p * (skin / r) for p in conn.pos]
    else:
        conn.pos = [0.0, -skin, 0.0]
    _resolve(conn)


def _resolve(conn: Conn) -> None:
    """Has this ended? See `sim/outcome.py`, which asks the questions.

    The thresholds stay here and are passed in, so there is one copy of each.
    """
    outcome_sim.resolve(conn, safe_closing=SAFE_CLOSING,
                        impact_base=IMPACT_BASE,
                        alongside_km=ALONGSIDE_KM,
                        alongside_rate=ALONGSIDE_RATE,
                        adrift_multiple=ADRIFT_MULTIPLE)
