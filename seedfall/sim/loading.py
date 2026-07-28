"""What a hull weighs, and what that costs it.

Fitted mass used to be free. Every slot took the heaviest, best part that would
go in it, because nothing anywhere read the tonnage — a hull carrying two
hundred tonnes of extra armour flew exactly as well as an empty one, and
usually jumped further.

Mass is now the price of everything you bolt on. A drive raises what the hull
can shift; parts, cargo and crew raise what it has to. The ratio between them
is the number that makes a shipyard a design problem rather than a shopping
list.
"""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID
from ..data.parts import PARTS_BY_ID

#: What one fitting slot is designed to carry, in tonnes. Chassis structural
#: mass is useless as a basis — it runs from a sixty-tonne SPORE to a
#: twelve-billion-tonne LEVIATHAN — but slots and hold rating are on the same
#: scale as the parts and cargo that fill them.
SLOT_TONNES = 52.0

#: How far performance can fall, and how far it can rise.
FLOOR, CEILING = 0.55, 1.18

#: A tonne of crew, in life support, water and volume.
CREW_TONNES = 1.4


def part_mass(ship) -> float:
    return sum(PARTS_BY_ID[p].mass for p in ship.fitted if p in PARTS_BY_ID)


def cargo_mass(ship) -> float:
    return sum(ship.cargo.values())


def capacity(ship) -> float:
    """Tonnes this chassis is built to shift beyond its own structure."""
    ch = CHASSIS_BY_ID[ship.chassis]
    slots = sum(ch.slots.values())
    return max(1.0, slots * SLOT_TONNES + ch.cargo + ch.crew * CREW_TONNES)


def laden(ship) -> float:
    """Everything the drive has to move that is not the hull itself."""
    return part_mass(ship) + cargo_mass(ship) + ship.crew * CREW_TONNES


def loading(ship) -> float:
    """Fraction of the designed load actually aboard. 1.0 is on the marks."""
    return laden(ship) / capacity(ship)


def factor(ship, thrust: float = 0.0) -> float:
    """Multiplier on speed, jump and evasion for how the hull is loaded.

    Thrust from fitted drives raises what counts as nominal, so a heavy hull
    with the engines to match is not penalised for being heavy — it is
    penalised for being heavy *and* underpowered.
    """
    ratio = laden(ship) / (capacity(ship) * (1.0 + thrust * 0.22))
    if ratio <= 1.0:
        # Under the marks: a modest bonus, tapering, so stripping a hull bare
        # is worth something but never worth more than carrying a useful fit.
        return min(CEILING, 1.0 + (1.0 - ratio) * 0.22)
    return max(FLOOR, 1.0 - (ratio - 1.0) * 0.55)


def note(ship, thrust: float = 0.0) -> tuple[str, str]:
    """How the loading reads on a design sheet."""
    ratio = loading(ship)
    scale = factor(ship, thrust)
    if ratio <= 0.55:
        return "light", "chloro"
    if ratio <= 0.9:
        return "on the marks", "chloro"
    if ratio <= 1.15:
        return "heavy", "osteo"
    if scale <= 0.7:
        return "grossly overloaded", "bad"
    return "overloaded", "warn"


def summary(ship, thrust: float = 0.0) -> dict:
    return {"parts": part_mass(ship), "cargo": cargo_mass(ship),
            "crew": ship.crew * CREW_TONNES, "laden": laden(ship),
            "capacity": capacity(ship), "loading": loading(ship),
            "factor": factor(ship, thrust)}
