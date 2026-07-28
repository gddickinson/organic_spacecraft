"""The hull registry.

The shapes and the compatibility rules live in :mod:`hull_types`; the hulls
themselves are tabulated in :mod:`hulls_grown` (the GESTALT fleet) and
:mod:`hulls_built` (everything nobody grew). This module assembles them and is
the single import site for the rest of the game.
"""

from __future__ import annotations

from .hull_types import (ACCEPTS, BASE_POWER, BUILD_NEED, FAMILY_LABEL,
                         FAMILY_NOTE, FAMILY_TINT, LAYER_SETS, NO_REGEN,
                         Chassis, Layer, accepts_family, slots)
from .hulls_built import BUILT, FABRICATED, HYBRID, SYNTHETIC, XENO
from .hulls_grown import GROWN

CHASSIS: list[Chassis] = [*GROWN, *BUILT]
CHASSIS_BY_ID: dict[str, Chassis] = {c.id: c for c in CHASSIS}

#: Display order for the codex and the hull picker.
FAMILY_ORDER = ["grown", "fabricated", "hybrid", "synthetic", "xeno"]


def by_family(family: str) -> list[Chassis]:
    return [c for c in CHASSIS if c.family == family]


__all__ = [
    "CHASSIS", "CHASSIS_BY_ID", "FAMILY_ORDER", "by_family",
    "Chassis", "Layer", "LAYER_SETS", "slots", "accepts_family",
    "FAMILY_LABEL", "FAMILY_TINT", "FAMILY_NOTE", "ACCEPTS", "NO_REGEN",
    "BASE_POWER", "BUILD_NEED",
    "GROWN", "BUILT", "FABRICATED", "HYBRID", "SYNTHETIC", "XENO",
]
