"""One registry over every fittable part, so the shipyard and the markets do not
each have to know that weapons live in a different module from radiators."""

from __future__ import annotations

from .armaments import ARMAMENTS
from .chassis import Chassis, accepts_family
from .modules import MODULES
from .xenoparts import XENOPARTS
from .part_types import Part

PARTS: list[Part] = [*MODULES, *ARMAMENTS, *XENOPARTS]
PARTS_BY_ID: dict[str, Part] = {p.id: p for p in PARTS}

# Rough credit value of a tonne of each material, for resale valuation.
_MATERIAL_VALUE = {
    "ore": 42, "volatiles": 38, "phosphate": 340, "biomass": 66, "silicon": 880,
    "alloy": 155, "spidroin": 470, "magnetite": 520, "trehalose": 610,
    "xenolith": 3600,
}


def part(pid: str) -> Part | None:
    return PARTS_BY_ID.get(pid)


def parts_available(slot: str, chassis: Chassis, unlocked) -> list[Part]:
    """Every part that fits this slot on this hull and is unlocked by research."""
    return [p for p in PARTS
            if p.slot == slot
            and accepts_family(chassis, p.family)
            and (p.tech is None or p.tech in unlocked)]


def part_value(p: Part) -> int:
    """Credit-equivalent of a part, for resale and insurance valuation."""
    v = float(p.cost.get("credits", 0))
    for key, n in p.cost.items():
        if key != "credits":
            v += _MATERIAL_VALUE.get(key, 100) * n
    return round(v)
