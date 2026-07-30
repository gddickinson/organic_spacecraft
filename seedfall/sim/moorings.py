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


def points(target) -> list:
    """Every berth on this target, as (name, offset in km from its centre).

    Scaled by `radius_km` because that is the scale `ui/viewport` draws the
    mesh at — so the berth this returns is under the fitting on the screen.
    """
    if getattr(target, "kind", "") != "anchorage":
        return []
    scale = float(getattr(target, "radius_km", 0.0) or 0.0)
    if scale <= 0.0:
        return []
    sort = getattr(target, "berth", "") or ""
    return [(name, tuple(c * scale for c in offset))
            for name, offset in berth_points(sort)]


#: How far out the approach corridor's hold point sits, as a multiple of
#: whichever is larger: the structure's radius, or the berth's own distance
#: from its centre. A quarter clear of the hull, so the run in is along the
#: berth's own line and never through the spine.
CORRIDOR = 1.25


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
    berths = points(conn.target)
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
    berths = points(conn.target)
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
    at = found["at"]
    out = math.dist(at, (0.0, 0.0, 0.0))
    if out < 1e-9:
        return at
    hold = corridor_km(conn.target)
    point = tuple(c * hold / out for c in at)
    if math.dist(conn.pos, point) > reach_km(conn.target):
        return point
    return at


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
