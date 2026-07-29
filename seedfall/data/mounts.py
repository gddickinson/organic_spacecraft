"""Where the engines sit on a hull, and which way they push.

Drive slots were a *count*. A hull had two of them, you filled them, and the
`speed` numbers added up — so the six thruster buttons on the conn were pure
abstraction, the main drive could shove the ship sideways, and a fusion torch
on a courier behaved exactly like one on a freighter.

This gives thrust somewhere to come from.

**The frame.** Hull-relative and right-handed, in units of half the hull's
length, so a mount at `y = -0.9` is nine tenths of the way aft:

    +y  the nose            -y  the tail
    +x  starboard           -x  port
    +z  dorsal (the back)   -z  ventral (the belly)

**Main drives mount aft and push forward.** All of them, without exception —
that is what a main drive *is*. A ship that wants to go a different way turns
first, which is `sim/attitude.py`, and that turn costs time and reaction mass.
A hull with two drive slots carries them either side of the centreline, so
losing one leaves the thrust off-axis.

**Attitude thrusters are not fitted.** Every hull is built with them, at the
six extremities, because a ship that could not rotate could not be flown at
all — there is no loadout in which that is an interesting choice. Their
authority comes from the chassis rather than the module list, and how quickly
they turn a given hull is `thrusters.slew_rate`.

**Thrust is in kilonewtons.** A new scale, and deliberately not derived from
the `speed` stat: `speed` is a transfer-time multiplier that the whole economy
is tuned against, and quietly making it mean newtons as well would re-balance
every burn in the game. The ordering matches — a Fusion Torch out-thrusts a
Reaction-Mass Organ by the same margin it out-runs it — but the two numbers
answer different questions and are allowed to be read separately.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mount:
    """One engine, where it is and which way it pushes."""

    #: Position on the hull, in half-lengths from the centre of mass.
    at: tuple
    #: Unit vector the thrust pushes the ship along, in the hull's frame.
    axis: tuple
    #: How hard, in kN.
    thrust: float
    #: What it is, for the panel.
    label: str


#: Thrust for each drive, in kN. Ordered like the `speed` stat they carry,
#: which keeps a captain's intuition intact: the drive that gets you there
#: sooner also pushes harder at close quarters.
DRIVE_THRUST = {
    "reaction_organ": 120.0,
    "ion_cluster": 90.0,        # patient rather than strong — see the blurb
    "sail_film": 40.0,          # a sail is not a thruster at all
    "plasma_drive": 380.0,
    "fusion_torch": 900.0,
    "foldrunner": 300.0,        # its work is done between systems
}

#: Where a hull's drive slots sit, by how many it has. One goes on the
#: centreline; more are spread across the transom so a lost engine leaves the
#: thrust off-axis and the ship crabbing.
DRIVE_STATIONS = {
    1: [(0.0, -0.92, 0.0)],
    2: [(-0.34, -0.92, 0.0), (0.34, -0.92, 0.0)],
    3: [(-0.40, -0.92, 0.0), (0.0, -0.92, 0.0), (0.40, -0.92, 0.0)],
    4: [(-0.40, -0.92, -0.24), (0.40, -0.92, -0.24),
        (-0.40, -0.92, 0.24), (0.40, -0.92, 0.24)],
}

#: Every drive pushes the ship along its nose. This is the whole reason
#: attitude matters.
MAIN_AXIS = (0.0, 1.0, 0.0)

#: The attitude thrusters every hull is built with: where they sit and which
#: way each pair shoves. Six clusters at the extremities, so each has the
#: longest arm the hull can give it.
RCS_CLUSTERS = [
    ((0.0, 0.94, 0.0), (0.0, -1.0, 0.0), "Forward cluster"),
    ((0.0, -0.94, 0.0), (0.0, 1.0, 0.0), "Aft cluster"),
    ((0.92, 0.0, 0.0), (-1.0, 0.0, 0.0), "Starboard cluster"),
    ((-0.92, 0.0, 0.0), (1.0, 0.0, 0.0), "Port cluster"),
    ((0.0, 0.0, 0.92), (0.0, 0.0, -1.0), "Dorsal cluster"),
    ((0.0, 0.0, -0.92), (0.0, 0.0, 1.0), "Ventral cluster"),
]

#: Thrust of one attitude cluster, in kN, before the hull's size is taken
#: into account. A big hull carries bigger thrusters, but not in proportion
#: to its mass — which is why a freighter handles like a freighter.
RCS_BASE_THRUST = 8.0

#: How much of a hull's size shows up in its attitude thrusters. At 1.0 every
#: hull would turn identically and the stat would be decoration; at 0 a
#: LEVIATHAN could not rotate at all. Measured against play in
#: `tests/test_thrusters.py`.
RCS_SIZE_SHARE = 0.55


#: The six directions a hull carries cameras in, as unit vectors in the
#: ship's own frame: along its nose, its tail, its beams, its back and belly.
VIEWS = [
    ("fore", "Fore", (0.0, 1.0, 0.0)),
    ("aft", "Aft", (0.0, -1.0, 0.0)),
    ("port", "Port", (-1.0, 0.0, 0.0)),
    ("starboard", "Starboard", (1.0, 0.0, 0.0)),
    ("dorsal", "Dorsal", (0.0, 0.0, 1.0)),
    ("ventral", "Ventral", (0.0, 0.0, -1.0)),
]

#: The axes a pilot translates along, in the ship's frame.
AXES = [
    ("forward", "Ahead", (0.0, 1.0, 0.0)),
    ("back", "Astern", (0.0, -1.0, 0.0)),
    ("left", "Port", (-1.0, 0.0, 0.0)),
    ("right", "Starboard", (1.0, 0.0, 0.0)),
    ("up", "Up", (0.0, 0.0, 1.0)),
    ("down", "Down", (0.0, 0.0, -1.0)),
]
AXES_BY_ID = {a[0]: a for a in AXES}
