"""Hull chassis — the frame you fit everything else into.

Three families, three philosophies:

GROWN
    Gestated from a seed. Slow to make, cheap in credits, hungry for phosphate,
    and it heals. Six living layers, per the design dossier.
FABRICATED
    Bolted together in a Yard. Instant, expensive, tougher per tonne, and it
    never repairs itself without a drydock.
HYBRID
    A fabricated spine with tissue grown over it. Both bills, both gifts.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Layer:
    id: str
    name: str
    w: float        # share of total hull points
    regen: float    # fraction of max regrown per day
    note: str
    critical: bool = False   # the pressure vessel: breach it and the crew dies
    life: bool = False       # the atmosphere plant


# Outermost first.
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


def _s(drive=0, power=0, sensor=0, compute=0, defence=0, weapon=0, utility=0):
    return {"drive": drive, "power": power, "sensor": sensor, "compute": compute,
            "defence": defence, "weapon": weapon, "utility": utility}


CHASSIS: list[Chassis] = [
    # ── GROWN ───────────────────────────────────────────────────────────────
    Chassis("spore", "SPORE", "grown", "Pod", "Lifeboat / short-hop courier",
            240, 60, _s(1, 1, 1, 1, 1, 0, 1), 12, 2, 3.5, 1.35, 0.30,
            {"credits": 4000, "biomass": 8, "ore": 6}, 21, None,
            "Four metres of ovoid husk with a torpor gland. It cannot fight and "
            "barely carries anything, but it germinates in three weeks from a "
            "seed you can hold in one hand.", "Semen vivum"),
    Chassis("vesper", "VESPER", "grown", "Sentinel", "Scout / relay picket",
            420, 500, _s(1, 1, 3, 2, 1, 1, 1), 30, 4, 5.2, 1.30, 0.26,
            {"credits": 14000, "biomass": 20, "ore": 30, "magnetite": 8}, 60, "magnetite",
            "A tensioned magnetite dish that grew eyes. Sees further than "
            "anything its size and reports what it sees to everyone at once, "
            "which is not always what you wanted.", "Vigil viva"),
    Chassis("radix", "RADIX", "grown", "Uncrewed", "Asteroid miner / seed foundry",
            900, 3200, _s(1, 2, 1, 1, 2, 1, 4), 180, 6, 3.2, 0.80, 0.10,
            {"credits": 26000, "biomass": 40, "ore": 90, "phosphate": 12}, 150, "bioleach",
            "Where RADIX takes hold, a shipyard grows. It eats rock at a hundred "
            "tonnes a day, refines the useful tenth, and gestates the seeds of "
            "every other class from what is left.", "Radix viva"),
    Chassis("medusa", "MEDUSA", "grown", "Harvester", "Comet & volatile harvester",
            760, 2400, _s(1, 1, 2, 1, 2, 1, 4), 320, 8, 4.4, 0.95, 0.18,
            {"credits": 24000, "biomass": 46, "ore": 60, "volatiles": 40}, 130, "waterrefinery",
            "A translucent bell trailing kilometre-long tendrils, glowing "
            "because its ancestor gave science the green fluorescent protein. "
            "It drinks comets and is never short of fuel.", "Aequorea viva"),
    Chassis("navis", "NAVIS", "grown", "Ship", "Crewed long-range explorer",
            1400, 24000, _s(2, 2, 2, 2, 3, 2, 3), 220, 50, 6.0, 1.05, 0.16,
            {"credits": 52000, "biomass": 90, "ore": 180, "phosphate": 40, "silicon": 6},
            240, "osteoid",
            "The reference vessel: 120 metres of hollow organism whose whole "
            "inner surface breathes for its crew, thickening its own shielding "
            "as it flies. Everything else is measured against it.", "Navis viva"),
    Chassis("atlas", "ATLAS", "grown", "Freighter", "Bulk hauler",
            1250, 18000, _s(2, 1, 1, 1, 2, 1, 5), 900, 24, 4.8, 0.85, 0.08,
            {"credits": 46000, "biomass": 70, "ore": 210, "phosphate": 26}, 200, "tendon1",
            "Six hundred metres of grown keel strung with modular holds like a "
            "fish heavy with roe. It electrolyses its own cargo for reaction "
            "mass, which is either elegant or alarming depending on the cargo.",
            "Onus vivum"),
    Chassis("testudo", "TESTUDO", "grown", "Guardian", "Armoured escort",
            2600, 150000, _s(1, 2, 2, 1, 5, 1, 2), 120, 12, 3.6, 0.62, 0.05,
            {"credits": 64000, "biomass": 120, "ore": 340, "phosphate": 70}, 260, "tendon2",
            "A thousand grams per square centimetre of regrowing carapace — "
            "fifty times what a solar storm asks for. Charter doctrine gives it "
            "no weapons at all. It survives hits; it does not return them.",
            "Testudo viva"),
    Chassis("coral", "CORAL", "grown", "Research", "Mobile laboratory",
            1100, 9000, _s(1, 2, 3, 3, 2, 1, 3), 160, 40, 5.0, 0.90, 0.14,
            {"credits": 48000, "biomass": 60, "ore": 130, "phosphate": 30, "silicon": 10},
            210, "synnotch",
            "Grown as a calcite reef, budded with sealed polyp pods for anything "
            "you would rather not share air with. The fleet does its thinking "
            "and its quarantining in the same building.", "Recif vivum"),
    Chassis("nereus", "NEREUS", "grown", "Diver", "Ice-moon ocean explorer",
            980, 3000, _s(1, 2, 3, 2, 2, 1, 3), 90, 6, 4.2, 1.00, 0.20,
            {"credits": 44000, "biomass": 50, "ore": 90, "phosphate": 18, "trehalose": 8},
            170, "piezolyte",
            "Pressure-equalised to 150 MPa with no gas voids anywhere in its "
            "body. It bores through crust with a hot head while its tail "
            "refreezes the channel, and it is the only hull that can reach what "
            "lives under the ice.", "Abyssus viva"),
    Chassis("amber", "AMBER", "grown", "Liner", "Stasis passenger liner",
            1150, 130000, _s(2, 2, 1, 2, 3, 1, 4), 400, 20, 6.6, 0.98, 0.10,
            {"credits": 58000, "biomass": 80, "ore": 150, "trehalose": 30, "phosphate": 22},
            190, "trehalose",
            "Fifty thousand people set in resin at three tonnes a head, against "
            "a habitat's two thousand four hundred. It carries no biosphere "
            "because its passengers are not, for the moment, using one.",
            "Sucinum vivum"),
    Chassis("tardigrade", "TARDIGRADE", "grown", "Vault", "Deep-time archive hull",
            3200, 40000, _s(1, 1, 1, 2, 4, 0, 3), 100, 4, 3.0, 0.55, 0.04,
            {"credits": 70000, "biomass": 90, "ore": 300, "phosphate": 60, "trehalose": 20},
            240, "deinococcus",
            "Mostly shielding wrapped around a very small archive, carrying Dsup "
            "protein and Deinococcus-grade repair. It is rated for a million "
            "years of dormancy, so an afternoon of gunfire is beneath its notice.",
            "Ursus vivus"),
    Chassis("leviathan", "LEVIATHAN", "grown", "Ark", "Interstellar generation ark",
            9000, 12e9, _s(4, 4, 3, 4, 5, 3, 8), 4000, 400, 9.0, 0.50, 0.02,
            {"credits": 900000, "biomass": 2200, "ore": 6000, "phosphate": 900,
             "spidroin": 500, "silicon": 260}, 1400, "multifront",
            "Twelve six-by-twelve-kilometre drums budded from a single trunk, "
            "siphonophore-fashion, sharing one spine and one course. Ten million "
            "people and a full gene library, pointed at somewhere else.",
            "Cetus vivus"),

    # ── FABRICATED ──────────────────────────────────────────────────────────
    Chassis("halyard", "HALYARD", "fabricated", "Courier", "Fast courier / scout",
            380, 900, _s(2, 1, 2, 2, 1, 1, 1), 40, 6, 6.4, 1.55, 0.32,
            {"credits": 26000, "alloy": 30, "silicon": 8}, 12, "monocoque",
            "The Yards' argument in miniature: nothing on it is alive, nothing "
            "on it needs feeding, and it was in service the same fortnight it "
            "was ordered."),
    Chassis("pike", "PIKE", "fabricated", "Corvette", "Patrol corvette",
            720, 2600, _s(1, 2, 1, 1, 2, 3, 1), 45, 14, 4.6, 1.30, 0.24,
            {"credits": 38000, "alloy": 55, "silicon": 12}, 20, "monocoque",
            "Three weapon hardpoints on a hull that costs less than the guns. "
            "The Concordat sells these to anyone and is periodically surprised "
            "by who buys them."),
    Chassis("drayhorse", "DRAYHORSE", "fabricated", "Freighter", "Container hauler",
            1050, 22000, _s(2, 1, 1, 1, 2, 1, 5), 1100, 18, 4.4, 0.88, 0.06,
            {"credits": 54000, "alloy": 140, "silicon": 14}, 30, "monocoque",
            "A spine, eight container locks and an engine. Out-carries a grown "
            "freighter and will do it again tomorrow, provided you pay someone "
            "to weld it."),
    Chassis("meridian", "MERIDIAN", "fabricated", "Cruiser", "Survey cruiser",
            1300, 14000, _s(2, 2, 3, 3, 2, 2, 3), 200, 45, 7.0, 1.10, 0.15,
            {"credits": 72000, "alloy": 130, "silicon": 34}, 40, "aicore",
            "Instrumented to the rivets and jumps seven light-years without "
            "discussion. If you intend to chart rather than settle, this is the "
            "hull."),
    Chassis("longshot", "LONGSHOT", "fabricated", "Destroyer",
            "Stand-off missile destroyer",
            1500, 19000, _s(2, 2, 2, 2, 2, 4, 2), 150, 60, 5.2, 1.05, 0.14,
            {"credits": 96000, "alloy": 190, "silicon": 40}, 55, "missiles",
            "Built around its magazines. It intends to finish the argument at "
            "range four and has very little to say if you get to range zero."),
    Chassis("bastion", "BASTION", "fabricated", "Battleship", "Line battleship",
            3400, 90000, _s(2, 3, 2, 2, 4, 5, 2), 180, 140, 4.0, 0.72, 0.05,
            {"credits": 210000, "alloy": 520, "silicon": 90}, 110, "fusionlance",
            "The heaviest thing the Yards will sell a private captain. Five "
            "hardpoints, armour measured in decimetres, and not one gram of it "
            "will ever grow back."),

    # ── HYBRID ──────────────────────────────────────────────────────────────
    Chassis("graft", "GRAFT", "hybrid", "Skiff", "Salvage skiff",
            560, 1400, _s(1, 1, 2, 1, 2, 2, 2), 80, 8, 4.8, 1.25, 0.28,
            {"credits": 21000, "alloy": 22, "biomass": 18, "ore": 20}, 45, "oect",
            "Freehold work: a cut-down Yards frame with tissue grown through it. "
            "It heals slowly, flies well, and no two are quite the same ship."),
    Chassis("palimpsest", "PALIMPSEST", "hybrid", "Cutter",
            "Independent trader-fighter",
            1180, 11000, _s(2, 2, 2, 2, 3, 3, 4), 380, 30, 5.6, 1.08, 0.18,
            {"credits": 66000, "alloy": 90, "biomass": 55, "ore": 110, "silicon": 18},
            120, "mea",
            "Written over so many times the original hull is a rumour. Carries "
            "cargo, carries guns, and repairs the parts of itself that happen "
            "to be alive."),
    Chassis("threshold", "THRESHOLD", "hybrid", "Dreadnought", "Hybrid capital ship",
            4200, 140000, _s(3, 3, 3, 3, 5, 5, 4), 500, 180, 6.2, 0.86, 0.09,
            {"credits": 260000, "alloy": 420, "biomass": 260, "ore": 600,
             "phosphate": 130, "silicon": 110}, 330, "neuromorphic",
            "The synthesis nobody's charter quite permits: a fabricated keel, a "
            "grown carapace over it, and a neuromorphic core wired into living "
            "tissue. It fights like a Yards capital and mends like a hull."),
]

CHASSIS_BY_ID: dict[str, Chassis] = {c.id: c for c in CHASSIS}

FAMILY_LABEL = {"grown": "Grown", "fabricated": "Fabricated", "hybrid": "Hybrid"}
FAMILY_TINT = {"grown": "chloro", "fabricated": "steel", "hybrid": "osteo"}


def accepts_family(chassis: Chassis, module_family: str) -> bool:
    """Will this hull physically accept a part of that family?"""
    if module_family == "any":
        return True
    if chassis.family == "hybrid":
        return True
    return chassis.family == module_family
