"""Tactical geometry — where the ships actually are.

Combat used to be an abstract five-band track. It still reports bands, because
weapons are specified in them and the rest of the game reads them, but the band
is now *derived* from a real separation on a real plane. Ships carry a heading
and a speed, weapons have firing arcs, and turning to bring a mount to bear is a
decision that costs you the turn you spent turning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.save import register

#: The arena is a square this many units on a side; ships start apart on it.
ARENA = 1400.0

#: A band is 240 units of separation. Band 0 is contact, band 4 is extreme.
BAND_UNITS = 240.0
MAX_BAND = 4


@register
@dataclass
class Body2D:
    """A combatant's physical state. Angles in degrees, 0 = up the screen."""
    x: float = 0.0
    y: float = 0.0
    heading: float = 0.0
    speed: float = 0.0

    def copy(self) -> "Body2D":
        return Body2D(self.x, self.y, self.heading, self.speed)


# ── firing arcs ────────────────────────────────────────────────────────────

ARCS = {
    "fore": (0, 60, "Fore"),
    "broad": (60, 120, "Broadside"),
    "aft": (120, 180, "Aft"),
    "turret": (0, 180, "Turret"),
}

#: Which arc a mount fires through. Big fixed guns look forward; point defence
#: and anything self-guiding is on a mount that can traverse.
_ARC_BY_PART = {
    "pdc": "turret", "pd_grid": "turret", "missile_rack": "turret",
    "breach_torpedo": "turret", "spore_swarm": "turret", "drone_bay": "turret",
    "photic_flash": "turret", "mag_lance": "broad", "slug_battery": "broad",
    "lixiviant": "fore", "tendril_grapple": "fore", "railgun": "fore",
    "mass_driver": "fore", "particle_beam": "fore", "fusion_lance": "fore",
    "coherent_beam": "fore", "phase_lance": "fore", "standing_projector": "fore",
    "xeno_resonator": "broad",
}


def arc_of(part) -> str:
    """The arc a weapon fires through, derived if it is not listed."""
    if part.id in _ARC_BY_PART:
        return _ARC_BY_PART[part.id]
    if part.wpn and "seeking" in part.wpn.traits:
        return "turret"
    if part.wpn and part.wpn.dmg >= 30:
        return "fore"
    return "broad"


def arc_name(arc: str) -> str:
    return ARCS.get(arc, ARCS["turret"])[2]


# ── geometry ───────────────────────────────────────────────────────────────

def separation(a: Body2D, b: Body2D) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def band_for(distance: float) -> int:
    """Which weapon band a real separation corresponds to."""
    return max(0, min(MAX_BAND, int(distance // BAND_UNITS)))


def bearing_to(frm: Body2D, to: Body2D) -> float:
    """Absolute bearing from one body to another, in degrees, 0 = up."""
    dx, dy = to.x - frm.x, to.y - frm.y
    return (math.degrees(math.atan2(dx, -dy))) % 360


def relative_bearing(frm: Body2D, to: Body2D) -> float:
    """Bearing off the bow, 0..180 — how far the target is from dead ahead."""
    delta = (bearing_to(frm, to) - frm.heading) % 360
    return delta if delta <= 180 else 360 - delta


def bears(arc: str, rel: float) -> bool:
    lo, hi = ARCS.get(arc, ARCS["turret"])[:2]
    return lo <= rel <= hi


def arc_gap(arc: str, rel: float) -> float:
    """Degrees you would have to turn to bring this arc onto the target."""
    lo, hi = ARCS.get(arc, ARCS["turret"])[:2]
    if lo <= rel <= hi:
        return 0.0
    return lo - rel if rel < lo else rel - hi


# ── movement ───────────────────────────────────────────────────────────────

def steer(body: Body2D, turn: float, limit: float) -> float:
    """Turn the ship, clamped by how nimble it is. Returns degrees actually turned."""
    applied = max(-limit, min(limit, turn))
    body.heading = (body.heading + applied) % 360
    return applied


def throttle(body: Body2D, target_speed: float, accel: float) -> None:
    """Ease the speed toward the ordered one."""
    delta = target_speed - body.speed
    body.speed += max(-accel, min(accel, delta))
    body.speed = max(0.0, body.speed)


def advance(body: Body2D) -> None:
    """One turn of travel along the current heading."""
    rad = math.radians(body.heading)
    body.x += math.sin(rad) * body.speed
    body.y -= math.cos(rad) * body.speed
    # Keep the engagement on the plot rather than letting it drift to infinity.
    body.x = max(-ARENA, min(ARENA, body.x))
    body.y = max(-ARENA, min(ARENA, body.y))


def initial_layout(rng, band: int = 3) -> tuple[Body2D, Body2D]:
    """Put two ships on the plot at a plausible opening range and aspect."""
    gap = (band + 0.5) * BAND_UNITS
    angle = rng.float(0, 360)
    rad = math.radians(angle)
    player = Body2D(0.0, 0.0, angle, 0.0)
    enemy = Body2D(math.sin(rad) * gap, -math.cos(rad) * gap,
                   (angle + 180 + rng.float(-50, 50)) % 360, 0.0)
    return player, enemy


def manoeuvrability(stats) -> tuple[float, float, float]:
    """(max turn per turn, acceleration, top speed) from a ship's stats."""
    agility = 0.6 + stats.evade * 2.2
    turn_limit = 24 + 46 * agility
    accel = 14 + 26 * stats.speed
    top = 40 + 120 * stats.speed
    return turn_limit, accel, top
