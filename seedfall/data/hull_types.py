"""Hull shapes: the layer stacks, the chassis record, and which parts graft to
which frame.

Five families, five philosophies:

GROWN
    Gestated from a seed. Slow to make, cheap in credits, hungry for phosphate,
    and it heals. Six living layers, per the design dossier.
FABRICATED
    Bolted together in a Yard. Instant, expensive, tougher per tonne, and it
    never repairs itself without a drydock.
HYBRID
    A fabricated spine with tissue grown over it. Both bills, both gifts.
SYNTHETIC
    Dry Choir work: no crew, no air, no biology. A photonic skin over a
    spaceframe wrapped around a substrate vault. Precise, fast-thinking, and
    quite unable to mend a scratch.
XENO
    Grown from something that shares no ancestor with us. Nobody can say how it
    heals, only that it does.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Layer:
    id: str
    name: str
    w: float        # share of total hull points
    regen: float    # fraction of max regrown per day
    note: str
    critical: bool = False   # the pressure vessel: breach it and the crew dies
    life: bool = False       # the atmosphere plant


# Outermost first. Weights sum to 1 within each family.
LAYER_SETS: dict[str, list[Layer]] = {
    "grown": [
        Layer("epidermis", "Sacrificial Epidermis", 0.12, 0.09,
              "Dead scute cells. Ablative bumper, regrown continuously."),
        Layer("rind", "Melanised Rind", 0.13, 0.05,
              "Eumelanin. Absorbs radiation and heat, quenches radicals."),
        Layer("mycelium", "Mycelial Matrix", 0.22, 0.045,
              "Chitin–glucan hyphal net. The wood; carries tension."),
        Layer("osteoid", "Osteoid Trusses", 0.24, 0.02,
              "Collagen–hydroxyapatite along the stress lines."),
        Layer("pneumostat", "Pneumostat Membrane", 0.20, 0.03,
              "The actual pressure vessel. Breach it and the air leaves.",
              critical=True),
        Layer("intima", "Photosynthetic Intima", 0.09, 0.06,
              "The crew's atmosphere plant. Lose it and you are on bottled air.",
              life=True),
    ],
    "fabricated": [
        Layer("whipple", "Whipple Bumper", 0.16, 0.0,
              "Stand-off plate. Flashes debris to plasma before it reaches you."),
        Layer("plate", "Alloy Armour", 0.34, 0.0,
              "Rolled Ti-Al. Dumb, dense and utterly reliable."),
        Layer("frame", "Load Frame", 0.26, 0.0,
              "Monocoque ribs. When these go, the geometry goes."),
        Layer("presshull", "Pressure Hull", 0.24, 0.0,
              "Welded gas envelope. The last thing between crew and vacuum.",
              critical=True),
    ],
    "hybrid": [
        Layer("whipple", "Whipple Bumper", 0.12, 0.0,
              "Fabricated stand-off plate over living tissue."),
        Layer("rind", "Melanised Rind", 0.13, 0.05,
              "Grown radiation mat, grafted to the plate."),
        Layer("plate", "Alloy Armour", 0.22, 0.0,
              "Rolled plate on the primary load paths."),
        Layer("mycelium", "Mycelial Matrix", 0.19, 0.045,
              "Hyphal packing between the ribs. Heals; also stinks."),
        Layer("pneumostat", "Pneumostat Membrane", 0.22, 0.03,
              "Grown lamellae sealing a fabricated frame.", critical=True),
        Layer("intima", "Photosynthetic Intima", 0.12, 0.06,
              "Partial canopy. Supplements bottled air rather than replacing it.",
              life=True),
    ],
    "synthetic": [
        Layer("aerogel", "Ablative Aerogel", 0.14, 0.0,
              "Spun silica foam. Cheap, light, and meant to be lost."),
        Layer("photonic", "Photonic Mesh", 0.20, 0.0,
              "The skin is the sensor. Damage here blinds before it hurts."),
        Layer("spaceframe", "Composite Spaceframe", 0.30, 0.0,
              "Filament-wound truss. No pressure to hold, so it holds only itself."),
        Layer("corevault", "Core Vault", 0.36, 0.0,
              "The substrate, and the coolant that keeps it thinking. Open this "
              "and whatever was running in there stops.", critical=True),
    ],
    "xeno": [
        Layer("diffraction", "Diffraction Skin", 0.15, 0.06,
              "It scatters most of what you shine at it and none of it the same "
              "way twice."),
        Layer("resonant", "Resonant Lattice", 0.25, 0.04,
              "A standing wave in solid matter. It rings when struck, and the "
              "ringing is load-bearing."),
        Layer("spar", "Nacreous Spar", 0.24, 0.03,
              "Laid down in sheets like shell, along stress lines nobody chose."),
        Layer("bladder", "Pressure Bladder", 0.22, 0.05,
              "Holds an atmosphere it was never designed to hold. It seems willing.",
              critical=True),
        Layer("symbiont", "Symbiont Lining", 0.14, 0.06,
              "Something lives in the walls and exhales what the crew needs. "
              "The arrangement is not fully understood.", life=True),
    ],
}


@dataclass(frozen=True)
class Chassis:
    id: str
    name: str
    family: str
    tier: str
    role: str
    hull: int
    mass_t: float
    slots: dict[str, int]
    cargo: int
    crew: int
    jump: float
    speed: float
    evade: float
    cost: dict[str, float]
    grow: int                      # days in the cradle or the slip
    tech: str | None
    blurb: str
    binomial: str = ""


def slots(drive=0, power=0, sensor=0, compute=0, defence=0, weapon=0, utility=0):
    """Terse slot spec, used by the hull tables."""
    return {"drive": drive, "power": power, "sensor": sensor, "compute": compute,
            "defence": defence, "weapon": weapon, "utility": utility}


FAMILY_LABEL = {
    "grown": "Grown", "fabricated": "Fabricated", "hybrid": "Hybrid",
    "synthetic": "Synthetic", "xeno": "Xeno",
}

FAMILY_TINT = {
    "grown": "chloro", "fabricated": "steel", "hybrid": "osteo",
    "synthetic": "xeno", "xeno": "lumen",
}

FAMILY_NOTE = {
    "grown": "Gestated from a seed. Heals itself; eats phosphate; takes months.",
    "fabricated": "Welded in a Yard. Fast and dear, and it never grows back.",
    "hybrid": "A Yards frame with tissue grown through it. Both bills, both gifts.",
    "synthetic": "Crewless Dry Choir work. Superb instruments, no self-repair.",
    "xeno": "Not ours. It mends, and nobody has explained how.",
}

#: Which module families each hull family will physically accept.
ACCEPTS: dict[str, frozenset[str]] = {
    "grown": frozenset({"grown", "any"}),
    "fabricated": frozenset({"fabricated", "any"}),
    "hybrid": frozenset({"grown", "fabricated", "hybrid", "any"}),
    "synthetic": frozenset({"fabricated", "synthetic", "any"}),
    "xeno": frozenset({"xeno", "fabricated", "any"}),
}

#: Families that cannot close their own wounds.
NO_REGEN = frozenset({"fabricated", "synthetic"})

#: Baseline hotel power, before any fitted plant.
BASE_POWER = {"grown": 6, "fabricated": 4, "hybrid": 5, "synthetic": 9, "xeno": 7}

#: What a yard needs to lay one of these down.
#:   gestation → a nursery (fleet hub, GRAVID, or your own yard)
#:   shipyard  → a slipway (station, fleet hub, or a fabricator yard)
#:   xenoyard  → a reactivated alien array, or a nursery willing to try
BUILD_NEED = {
    "grown": "gestation", "hybrid": "gestation", "xeno": "xenoyard",
    "fabricated": "shipyard", "synthetic": "shipyard",
}


def accepts_family(chassis: Chassis, module_family: str) -> bool:
    """Will this hull physically accept a part of that family?"""
    return module_family in ACCEPTS.get(chassis.family, frozenset({"any"}))
