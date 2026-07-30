"""What a particular hull can actually push with, and how hard.

`data/mounts.py` says where the engines are. This asks what that means for
*this* ship: how much mass there is to move, how much thrust is fitted to move
it, and therefore how briskly it accelerates and how quickly it can turn.

The point of all of it is that the loadout stops being a stat line. A Fusion
Torch on a SPORE is a rocket and on a LEVIATHAN is a nudge, because the same
900 kN is dividing into very different masses — and until now both read as
"speed +0.58" and behaved identically at close quarters.

Three numbers come out, and the conn uses all three:

* `main_accel` — m/s² along the nose, from the fitted drives.
* `rcs_accel` — m/s² in any direction, from the attitude clusters.
* `slew_rate` — how fast the hull can rotate, which is what makes pointing
  the main drive somewhere a decision rather than a formality.

Nothing here is stored. Like `ship_stats`, it is derived from the loadout
every time it is asked for, so refitting is felt immediately.
"""

from __future__ import annotations

import math

from ..data.chassis import CHASSIS_BY_ID
from ..data.mounts import (DRIVE_STATIONS, DRIVE_THRUST, MAIN_AXIS, Mount,
                           RCS_BASE_THRUST, RCS_CLUSTERS, RCS_SIZE_SHARE)

#: Tonnes of ship per point of a chassis's `hull` rating.
#:
#: `hull` is the structural number the whole damage model is written against
#: — a SPORE is 240 and a NAVIS 1400 — and it is the only size the data
#: carries. Rather than invent a second one that could drift out of step, mass
#: is read from it. The constant is what turns a hull rating into tonnes.
TONNES_PER_HULL = 0.9

#: How long a hull is, in metres per point of `hull` rating. Only used for
#: the moment arm, which is what decides how fast a thing rotates.
METRES_PER_HULL = 0.11

#: Cargo counts, and so does everything bolted on. A full hold really does
#: make a ship handle worse, which is a thing a captain can feel and plan
#: around.
def mass_tonnes(ship) -> float:
    """Everything that has to be accelerated, in tonnes."""
    from ..data.armaments import ARMAMENTS
    from ..data.modules import MODULES

    parts = {p.id: p for p in list(MODULES) + list(ARMAMENTS)}
    chassis = CHASSIS_BY_ID[ship.chassis]
    total = chassis.hull * TONNES_PER_HULL
    for pid in ship.fitted:
        part = parts.get(pid)
        if part is not None:
            total += part.mass
    total += sum(max(0.0, amount) for amount in ship.cargo.values())
    return max(1.0, total)


def half_length_m(ship) -> float:
    """Half the hull's length in metres — the arm an attitude cluster works on."""
    chassis = CHASSIS_BY_ID[ship.chassis]
    return max(2.0, chassis.hull * METRES_PER_HULL * 0.5)


def drives(ship) -> list[Mount]:
    """Every drive fitted, where it sits and what it gives.

    A hull with two slots and one engine leaves the other station empty, so
    the thrust is off the centreline — which is a real consequence of losing
    an engine and is visible on the conn's engine board.
    """
    from ..data.modules import MODULES

    by_id = {p.id: p for p in MODULES}
    chassis = CHASSIS_BY_ID[ship.chassis]
    slots = chassis.slots.get("drive", 1)
    stations = DRIVE_STATIONS.get(slots, DRIVE_STATIONS[1])
    out = []
    index = 0
    for pid in ship.fitted:
        part = by_id.get(pid)
        if part is None or part.slot != "drive":
            continue
        at = stations[index] if index < len(stations) else stations[-1]
        out.append(Mount(at=at, axis=MAIN_AXIS,
                         thrust=DRIVE_THRUST.get(pid, 100.0),
                         label=part.name))
        index += 1
    return out


def main_thrust(ship) -> float:
    """Total kN along the nose from everything fitted."""
    return sum(m.thrust for m in drives(ship))


def offset(ship) -> float:
    """How far off the centreline the thrust acts, in half-lengths.

    Zero on a balanced hull. A two-slot hull running one engine pushes from
    0.34 out, which the flight computer has to trim against — and which the
    conn says out loud rather than quietly stealing reaction mass for.
    """
    fitted = drives(ship)
    if not fitted:
        return 0.0
    total = sum(m.thrust for m in fitted)
    if total <= 0:
        return 0.0
    return abs(sum(m.at[0] * m.thrust for m in fitted) / total)


def yaw_torque(ship) -> float:
    """Net torque about the hull's vertical axis under main drive, in N·m.

    `r × F`, summed over the engines actually fitted. This is the one place
    `Mount.axis` is read for what it is rather than assumed: the cross product
    needs the direction each engine pushes, and a mount's contribution to yaw
    is its athwartships offset times its thrust.

    Zero on a balanced hull, because the pair cancel. A two-slot hull running
    one engine pushes from 0.34 half-lengths out and the hull turns under its
    own drive — which `data/mounts.py` has claimed since it was written
    ("losing one leaves the thrust off-axis") and which nothing computed.
    """
    arm = half_length_m(ship)
    total = 0.0
    for mount in drives(ship):
        force = mount.thrust * 1000.0                 # N
        rx, ry, _rz = mount.at
        ax, ay, _az = mount.axis
        # The z component of r × F, in a frame where the offsets are in
        # half-lengths: (rx·Fy − ry·Fx).
        total += ((rx * arm) * (force * ay)
                  - (ry * arm) * (force * ax))
    return total


def yaw_rate(ship) -> float:
    """Angular acceleration about the vertical, in rad/s², under full drive.

    The same moment of inertia `slew_rate` uses, so a big hull resists an
    unbalanced engine for exactly the reasons it resists being turned on
    purpose.
    """
    arm = half_length_m(ship)
    inertia = mass_tonnes(ship) * 1000.0 * (arm ** 2) / 3.0
    if inertia <= 0:
        return 0.0
    return yaw_torque(ship) / inertia


#: The least of its main drive a hull can ever use, however badly the thrust
#: is placed. A drive that cannot be opened at all is a stranding, and a
#: stranding that follows silently from a refit is a worse fault than a
#: sluggish ship.
HOLD_FLOOR = 0.15

#: What holding an off-axis burn straight costs, as a share added to the
#: main-drive mass bill at full imbalance. The clusters fire throughout to
#: answer the torque, and that mass is real.
TRIM_COST_SHARE = 0.55


def holdable_throttle(ship) -> float:
    """How far the main drive can be opened and still be held straight.

    An off-centreline drive puts a torque on the hull, and the attitude
    clusters have a finite authority to answer it. Both scale linearly — the
    torque with the throttle, the clusters not at all — so there is a throttle
    above which the nose cannot be held, and it is simply the ratio.

    This is the model rather than letting the hull tumble, and the reason is
    the tick. A conn tick is a minute, and an unopposed 0.0012 rad/s² over
    sixty seconds is 126 degrees: a hull that spins like a top, not one that
    needs trimming. A flight computer would never let that happen — it holds
    attitude and limits the throttle to what it can hold, which is what
    `thrusters.offset` meant by "the flight computer has to trim against" it.

    Measured on a NAVIS running one of two engines: 0.62, so a captain gets
    about three fifths of the engine they have left.
    """
    yaw = abs(yaw_rate(ship))
    if yaw <= 1e-12:
        return 1.0
    return max(HOLD_FLOOR, min(1.0, slew_rate(ship) / yaw))


def rcs_thrust(ship) -> float:
    """What one attitude cluster gives, in kN, on this hull."""
    chassis = CHASSIS_BY_ID[ship.chassis]
    scale = (chassis.hull / 600.0) ** RCS_SIZE_SHARE
    return RCS_BASE_THRUST * scale


def main_accel(ship) -> float:
    """m/s² along the nose. Zero with no drive fitted, which is a real state."""
    return main_thrust(ship) / mass_tonnes(ship)


def rcs_accel(ship) -> float:
    """m/s² sideways, from one cluster firing."""
    return rcs_thrust(ship) / mass_tonnes(ship)


def slew_rate(ship) -> float:
    """Angular acceleration in radians per second squared.

    Torque is thrust times arm; a hull's moment of inertia goes as its mass
    times the square of its size. So a big ship turns slowly for two reasons
    at once, which is why a LEVIATHAN handles like a LEVIATHAN even with the
    largest thrusters bolted to it.

    Two clusters work a rotation — one shoving each way — so the torque is
    doubled and the inertia is the hull's own.
    """
    arm = half_length_m(ship)
    torque = 2.0 * rcs_thrust(ship) * 1000.0 * arm        # N·m
    inertia = mass_tonnes(ship) * 1000.0 * (arm ** 2) / 3.0
    if inertia <= 0:
        return 0.0
    return torque / inertia


def board(ship) -> list[tuple[str, str, str]]:
    """The engine board: what is fitted, where, and what it gives."""
    rows = []
    fitted = drives(ship)
    chassis = CHASSIS_BY_ID[ship.chassis]
    slots = chassis.slots.get("drive", 1)
    for index, mount in enumerate(fitted):
        where = "centreline" if abs(mount.at[0]) < 0.01 else (
            f"{'starboard' if mount.at[0] > 0 else 'port'} of the centreline")
        rows.append((mount.label, f"{mount.thrust:,.0f} kN", where))
    for _empty in range(max(0, slots - len(fitted))):
        rows.append(("Empty station", "—", "no engine fitted"))
    rows.append(("Attitude clusters", f"{rcs_thrust(ship):,.1f} kN each",
                 f"{len(RCS_CLUSTERS)} at the extremities"))
    return rows


def summary(ship) -> dict:
    """Everything the conn and the helm need, in one read."""
    return {
        "mass": mass_tonnes(ship),
        "main_kn": main_thrust(ship),
        "main_accel": main_accel(ship),
        "rcs_accel": rcs_accel(ship),
        "slew_rate": slew_rate(ship),
        "offset": offset(ship),
        "yaw_rate": yaw_rate(ship),
        "hold": holdable_throttle(ship),
        "drives": len(drives(ship)),
        "slots": CHASSIS_BY_ID[ship.chassis].slots.get("drive", 1),
        "length_m": half_length_m(ship) * 2.0,
    }


def slew_seconds(ship, radians: float) -> float:
    """How long to turn through an angle, in seconds.

    Bang-bang: spin up for half the arc and brake for the other half, which
    is what a flight computer actually does and what leaves the hull pointing
    where it was aimed rather than tumbling past it.
    """
    angle = abs(radians)
    if angle < 1e-9:
        return 0.0
    rate = slew_rate(ship)
    if rate <= 0:
        return math.inf
    return 2.0 * math.sqrt(angle / rate)
