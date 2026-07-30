"""Berths: the places on a structure a ship can actually tie up to.

Coming alongside was a distance from a *point*. `outcome.alongside` asked for
`range_km <= ALONGSIDE_KM + radius_km` and a slow enough closing rate, and
`radius_km` is a bounding sphere — so a hull that crept up on the far side of
a Fleet Hub, nowhere near a mast, and stopped, was moored. The structure the
window spends the whole approach drawing had nothing to do with it.

`data/berths3d.BERTH_POINTS` says where the berths are, in the same model
space the meshes are authored in and off the same numbers the builders use:
a quay's single arm ends in a warn-lit box, and that box is the berth; a hub's
four lit masts are four berths. So a berth is a thing you can see, and flying
to one is flying to what you are looking at.

This is the sim side of that — the conversion into the approach's own frame,
which of them is nearest, and whether the ship is at one.

**Why the reach is a share and not a distance.** A berth sits somewhere
between the middle of a structure and its skin — a hub's mast is 1.11 model
units out, a holding's gantry 0.45 — and the model is drawn at the target's
`radius_km`, which is anything from a few hundred metres to a few kilometres.
A fixed tolerance in km would be generous on a quay and meaningless on a gate.
A share of the structure's own size is the same rule at every scale.
"""

from __future__ import annotations

import math

from ..data.berths3d import berth_points

#: How near a berth counts as at it, as a share of the structure's radius.
#: Measured against what it has to tell apart: on a hub, the nearest mast from
#: a hull that has come alongside it is well inside this, and the far side of
#: the same hub is 1.9 radii from the nearest mast. Anything from about 0.5
#: down to 0.2 separates those two; 0.35 sits in the middle of that band.
BERTH_REACH = 0.35


#: What share of a berthing's whole speed budget the berth's own motion may
#: take. **Derived from the gate it has to fit inside**, not chosen: a hull is
#: alongside at `conn.ALONGSIDE_RATE` or under, so if the fitting is already
#: moving at that rate there is nothing left for the pilot and no docking is
#: possible. A quarter leaves the manoeuvre a manoeuvre.
RIM_SHARE = 0.25


def rim_speed() -> float:
    """How fast a berth travels as its structure turns, in m/s.

    **The period is set from this, not the other way round.** A station that
    comes round once a minute is 2001's, and on a 400 m hub that is eleven
    metres a second at the rim — eight times what a berthing allows, so nobody
    could ever dock. Fixing a *period* per class of berth is no better: it
    makes a big station undockable and a small one nearly static.

    So every structure turns at whatever period gives its berths the same
    pace, `T = 2πr / rim_speed()`, and that pace is a quarter of the speed a
    berthing is allowed. Measured at a whole one metre a second — two thirds
    of the budget — a hand-flown approach lost the fitting on one chronicle in
    three: the hub came round in forty-seven minutes and the docking took
    forty-eight. At 0.375 a Fleet Hub turns once in a little over two hours,
    which is 2.7 degrees a minute — plainly moving in the window over a
    three-quarter-hour approach, and leadable.
    """
    from .conn import ALONGSIDE_RATE
    return ALONGSIDE_RATE * RIM_SHARE


def turn_seconds(target) -> float:
    """How long this structure takes to come round once, in seconds.

    Zero for anything with no berths, and for a Weave gate: a relic that has
    hung there since before the Verge was settled is not spinning up now, and
    a ring with no inside does not need to.
    """
    if getattr(target, "berth", "") == "gate":
        return 0.0
    berths = berth_points(getattr(target, "berth", "") or "")
    scale = float(getattr(target, "radius_km", 0.0) or 0.0)
    if not berths or scale <= 0.0:
        return 0.0
    out_km = max(math.dist(at, (0.0, 0.0, 0.0)) for _n, at in berths) * scale
    return math.tau * out_km * 1000.0 / rim_speed()


def spin_at(target, elapsed: float) -> float:
    """Which way round the structure is, in radians, after `elapsed` seconds.

    The one door for it, because three things have to agree: where
    `sim/moorings.points` puts the berths, where `ui/viewport` draws the mesh,
    and where the flight computer aims. A station drawn in one attitude and
    berthed in another would be worse than one that does not turn at all.
    """
    period = turn_seconds(target)
    if period <= 0.0:
        return 0.0
    return (float(elapsed) / period) * math.tau


def points(target, spin: float = 0.0) -> list:
    """Every berth on this target, as (name, offset in km from its centre).

    Scaled by `radius_km` because that is the scale `ui/viewport` draws the
    mesh at — so the berth this returns is under the fitting on the screen —
    and turned by `spin`, about the structure's own pole, because the mesh is
    drawn turned by the same angle.
    """
    if getattr(target, "kind", "") != "anchorage":
        return []
    scale = float(getattr(target, "radius_km", 0.0) or 0.0)
    if scale <= 0.0:
        return []
    sort = getattr(target, "berth", "") or ""
    cs, sn = math.cos(spin), math.sin(spin)
    out = []
    for name, offset in berth_points(sort):
        x, y, z = (c * scale for c in offset)
        out.append((name, (x * cs - y * sn, x * sn + y * cs, z)))
    return out


#: How far out the approach corridor's hold point sits, as a multiple of
#: whichever is larger: the structure's radius, or the berth's own distance
#: from its centre. A quarter clear of the hull, so the run in is along the
#: berth's own line and never through the spine.
CORRIDOR = 1.25


def spin_of(conn) -> float:
    """How far round the thing being approached has turned, this tick."""
    return spin_at(conn.target, getattr(conn, "elapsed", 0.0))


def corridor_km(target) -> float:
    """The radius at which an approach commits to a berth and turns in.

    One door, because two things need the same number: `sim/autopilot.py`
    hands over from the corridor leg to the final leg here, and `assign`
    stops changing its mind here.
    """
    berths = points(target)
    if not berths:
        return 0.0
    out = max(math.dist(at, (0.0, 0.0, 0.0)) for _name, at in berths)
    return max(out, float(getattr(target, "radius_km", 0.0) or 0.0)) * CORRIDOR


def assign(conn) -> str:
    """Which berth this approach is for. Chosen freely far out, held on final.

    **Two mistakes, both measured, and the rule is what is left between
    them.** Re-picking the nearest fitting on every tick makes the computer
    chase a moving aim: a hull arriving with 15 m/s across the line of sight
    shuffled between two masts of a hub and ran its tanks dry 140 m short of
    both. Committing at the start is worse — the berth is chosen twelve
    kilometres out, before the drift has played out, and the ship then spends
    its mass flying round the structure to reach a mast that stopped being
    the near one long ago.

    A pilot is cleared for a berth on final approach, and that is the rule:
    outside the corridor take whichever is nearest and keep looking, inside it
    commit and stop changing your mind.
    """
    berths = points(conn.target, spin_of(conn))
    if not berths:
        return ""
    known = {name for name, _at in berths}
    if conn.berth in known and conn.range_km <= corridor_km(conn.target):
        return conn.berth
    name, _at = min(berths, key=lambda row: math.dist(conn.pos, row[1]))
    conn.berth = name
    return name


def nearest(conn) -> dict | None:
    """The berth this approach is for, and how far off it is.

    None when the target has no berths at all — a world is orbited, not moored
    to, and nothing here should pretend otherwise.
    """
    berths = points(conn.target, spin_of(conn))
    if not berths:
        return None
    want = assign(conn)
    at = next((offset for name, offset in berths if name == want), None)
    if at is None:
        want, at = berths[0]
    gap = math.dist(conn.pos, at)
    reach = reach_km(conn.target)
    return {"name": want, "at": at, "km": gap, "reach_km": reach,
            "at_it": gap <= reach}


def reach_km(target) -> float:
    """How near counts as at a berth, in km, for this structure."""
    return float(getattr(target, "radius_km", 0.0) or 0.0) * BERTH_REACH


def at_berth(conn) -> bool:
    """Is the ship at a berth — not merely near the structure?

    True for a target with no berths, because that is not a berthing at all
    and this must not be the thing that refuses it: the caller's other rules
    decide. A quay with no berth points would be a data fault, and one that
    silently refused every mooring would be a hard one to find.
    """
    found = nearest(conn)
    return True if found is None else bool(found["at_it"])


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
    found = nearest(conn)
    if found is None:
        return (0.0, 0.0, 0.0)
    at = lead(conn, found)
    out = math.dist(at, (0.0, 0.0, 0.0))
    if out < 1e-9:
        return at
    hold = corridor_km(conn.target)
    point = tuple(c * hold / out for c in at)
    if math.dist(conn.pos, point) > reach_km(conn.target):
        return point
    return at


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
    found = found or nearest(conn)
    if found is None:
        return (0.0, 0.0, 0.0)
    period = turn_seconds(conn.target)
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
    want = name or (nearest(conn) or {}).get("name", "")
    turned = points(conn.target,
                    spin_at(conn.target,
                            getattr(conn, "elapsed", 0.0) + float(ahead)))
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
    found = found or nearest(conn)
    period = turn_seconds(conn.target)
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
    found = nearest(conn)
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

    if nearest(conn) is None:
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


def line(conn) -> str:
    """One line for the console: which berth, and how far off it is."""
    found = nearest(conn)
    if found is None:
        return ""
    gap = found["km"]
    span = f"{gap * 1000:,.0f} m" if gap < 2.0 else f"{gap:,.1f} km"
    if found["at_it"]:
        return f"At {found['name']} — {span}."
    return f"{found['name']} is the nearest berth, {span} off."
