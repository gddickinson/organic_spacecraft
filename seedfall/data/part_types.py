"""Shared shapes for fittable parts — organs, machines, weapons and defences.

``fx`` keys, all optional and all additive unless noted::

    power   generated      draw    consumed        jump    +light-years
    speed   +fraction      evade   +fraction       sensor  +scan range (ly)
    scan    +survey quality        cargo +tonnes   berths  +crew
    regen   +fraction of layer regrowth            hullMul +fraction of hull
    vent    heat shed per combat turn              heatCap +heat capacity
    mine    ore/day        drink  volatiles/day    graze biomass/day
    phos    phosphate/day  research +points/day    accuracy +fraction
    armour  flat damage soak       o2 +days of air morale +crew morale/day
    colony  enables founding grown colonies        dive enables ocean descent
    repair  fabricated self-repair  flak intercepts seeking shots
    drift   holds the lineage canon (CHORUS)
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Weapon:
    dmg: float
    bands: tuple[int, int]          # effective range band, 0 = contact
    heat: float
    acc: float = 0.0
    ammo: tuple[str, int] | None = None      # (commodity id, units per shot)
    traits: tuple[str, ...] = ()

    def bears_at(self, band: int) -> float:
        """Accuracy penalty at this range band; > 0.6 means it cannot fire."""
        lo, hi = self.bands
        if lo <= band <= hi:
            return 0.0
        return min(abs(band - lo), abs(band - hi)) * 0.22


@dataclass(frozen=True)
class Ability:
    id: str
    name: str
    cd: int          # cooldown in turns


@dataclass(frozen=True)
class Part:
    id: str
    name: str
    slot: str        # drive power sensor compute defence weapon utility
    family: str      # grown | fabricated | any
    tech: str | None
    mass: float
    cost: dict[str, float]
    fx: dict[str, float]
    blurb: str
    wpn: Weapon | None = None
    ability: Ability | None = None
    #: Kit for a trade rather than a fight. NPC loadouts skip these: a Yards
    #: patrol boat rolling a smuggler's false manifest is nonsense, and letting
    #: new civilian parts into the enemy pool silently re-tunes every
    #: encounter in the game — which is exactly what adding two of them did.
    civilian: bool = False


SLOT_LABEL = {
    "drive": "Drive", "power": "Power", "sensor": "Sensor", "compute": "Compute",
    "defence": "Defence", "weapon": "Weapon", "utility": "Utility",
}

SLOT_ORDER = ["drive", "power", "sensor", "compute", "defence", "weapon", "utility"]

# Range-band names, 0 (grappling distance) to 4 (extreme).
BANDS = ["Contact", "Close", "Medium", "Long", "Extreme"]

# What the combat resolver does with each weapon trait.
TRAIT_NOTES = {
    "ablate": "double damage to the outermost intact layer",
    "pierce": "ignores the outermost layer entirely",
    "emp": "drains power and may knock a module offline",
    "blind": "lowers the target's accuracy for a turn",
    "board": "may disable a random fitted module",
    "grapple": "target cannot disengage next turn",
    "plunder": "steals cargo on a hit",
    "flak": "also intercepts incoming seeking shots",
    "seeking": "ignores evasion, but point defence can stop it",
    "nonlethal": "never kills crew",
}
