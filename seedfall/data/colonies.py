"""Colony classes — the empire layer.

You plant a seed on a body and walk away for a year or two. Grown colonies
gestate slowly and cost almost no credits; the Concordat's fabricated yard is
the opposite bargain. Yields are per day and accrue wherever you are.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColonyClass:
    id: str
    name: str
    family: str
    tech: str | None
    sites: tuple[str, ...]       # body kinds it will take root on
    days: int
    cost: dict[str, float]
    yields: dict[str, float]     # per day
    upkeep: dict[str, float]     # per day
    pop: int
    blurb: str
    binomial: str = ""
    effects: dict = field(default_factory=dict)


COLONIES: list[ColonyClass] = [
    ColonyClass(
        "radix_mine", "RADIX Mine", "grown", "bioleach",
        ("asteroid", "moon", "rocky"), 150,
        {"credits": 12000, "biomass": 20, "ore": 20},
        {"ore": 2.6, "phosphate": 0.11}, {"biomass": 0.10}, 0,
        "Roots into the body and does not stop. Bioleaches metal at tonnes per "
        "day and mineralises the rest into feedstock pellets. Where RADIX takes "
        "hold, a shipyard grows.", "Radix viva"),
    ColonyClass(
        "medusa_still", "MEDUSA Still", "grown", "waterrefinery",
        ("comet", "ice", "moon"), 120,
        {"credits": 11000, "biomass": 22, "volatiles": 15},
        {"volatiles": 3.2}, {"biomass": 0.08}, 0,
        "A moored bell sublimating and filtering ice into water, carbon and "
        "nitrogen. A single one-kilometre comet holds two hundred and sixty "
        "million tonnes; you will get bored before it does.", "Aequorea viva"),
    ColonyClass(
        "lichen_dome", "LICHEN Dome", "grown", "melanin",
        ("rocky", "moon"), 130,
        {"credits": 9000, "biomass": 26, "ore": 14},
        {"credits": 90, "biomass": 1.1}, {}, 10000,
        "A pressure blister grown into the regolith under nine metres of its "
        "own spoil. Detoxing the perchlorate in the first metre of floor "
        "liberates fourteen hundred tonnes of oxygen — the poison is the "
        "startup air supply.", "Lichen vivum"),
    ColonyClass(
        "pomona_grove", "POMONA Grove", "grown", "intima",
        ("asteroid", "moon", "rocky", "gas", "comet"), 100,
        {"credits": 8000, "biomass": 18},
        {"biomass": 2.8, "credits": 25}, {"volatiles": 0.15}, 50,
        "Eighteen square kilometres of photosynthetic frond around a spine, "
        "almost all surface and almost no mass. Two point eight square "
        "kilometres of algae covers a hundred thousand people's oxygen.",
        "Hortus vivus"),
    ColonyClass(
        "gravid_nursery", "GRAVID Nursery", "grown", "segclock",
        ("asteroid", "moon", "rocky"), 300,
        {"credits": 60000, "biomass": 90, "ore": 160, "phosphate": 40},
        {}, {"biomass": 0.4, "ore": 0.5}, 200,
        "Twelve to twenty-four placental cradles, each feeding a growing vessel "
        "twenty-six tonnes a day through an umbilical trunk. It cuts a "
        "starship's wild five-year gestation to two, and it grows every class "
        "including itself.", "Mater viva",
        {"gestation": 0.45, "build_here": True}),
    ColonyClass(
        "vesper_picket", "VESPER Picket", "grown", "magnetite",
        ("asteroid", "comet", "moon", "ice", "rocky", "gas"), 45,
        {"credits": 6000, "biomass": 8, "magnetite": 6},
        {"survey": 0.06}, {}, 0,
        "A tensioned magnetite dish with grown eyes and a beacon. Spread across "
        "a system the nodes phase into one microarcsecond interferometer, and "
        "they will tell you the Bloom is coming before it arrives.", "Vigil viva",
        {"sensor": 2.5, "watch": True}),
    ColonyClass(
        "chorus_node", "CHORUS Node", "grown", "chorus",
        ("asteroid", "moon", "rocky", "ice", "comet"), 70,
        {"credits": 18000, "biomass": 12, "silicon": 6},
        {"research": 1.1}, {}, 0,
        "An exabyte in five grams of DNA, reconciling against every other node "
        "through the picket mesh. It holds the canon your germline resyncs "
        "against, and the argument about who curates it.", "Memoria viva",
        {"drift": True, "diplomacy": 0.04}),
    ColonyClass(
        "coral_reef", "CORAL Reef", "grown", "synnotch",
        ("asteroid", "moon", "rocky", "gas"), 160,
        {"credits": 28000, "biomass": 40, "ore": 50, "phosphate": 12},
        {"research": 2.4, "xenopharma": 0.05}, {"biomass": 0.2}, 2000,
        "A calcite ring reef budded with sealed polyp pods. The fleet does its "
        "thinking and its quarantining in the same building, on the theory that "
        "the two activities keep an eye on each other.", "Recif vivum",
        {"medical": True}),
    ColonyClass(
        "tardigrade_vault", "TARDIGRADE Vault", "grown", "deinococcus",
        ("asteroid", "moon", "ice"), 200,
        {"credits": 34000, "biomass": 40, "ore": 120, "phosphate": 26},
        {}, {}, 0,
        "Five hundred grams per square centimetre of shielding wrapped around a "
        "very small archive, glassified into cryptobiosis. If you lose "
        "everything, this is what you come back from.", "Ursus vivus",
        {"vault": True}),
    ColonyClass(
        "solforge", "SOL-FORGE", "grown", "solforge",
        ("star",), 240,
        {"credits": 70000, "biomass": 60, "ore": 200, "spidroin": 40},
        {"credits": 420, "alloy": 0.9}, {}, 0,
        "Five kilometres of secreted reflective film at a fifth of an AU, "
        "gathering a terawatt. At three hundred and fifty degrees nothing living "
        "survives, so the organism hides in its own shadow: a living thing "
        "tending a furnace it cannot enter.", "Fornax viva"),
    ColonyClass(
        "arca_drum", "ARCA Habitat", "grown", "multifront",
        ("asteroid",), 900,
        {"credits": 400000, "biomass": 900, "ore": 2600, "phosphate": 400,
         "spidroin": 300},
        {"credits": 1400, "biomass": 4, "research": 3}, {"volatiles": 1.2}, 1000000,
        "A five-by-ten-kilometre drum at six-tenths of a revolution per minute, "
        "lit from the axis by fifteen gigawatts of piped starlight. A million "
        "people living on the inside, under a sky made of the far side of their "
        "own world.", "Arca viva", {"megastructure": True}),
    ColonyClass(
        "fab_yard", "Fabricator Yard", "fabricated", "monocoque",
        ("asteroid", "moon", "rocky"), 60,
        {"credits": 46000, "alloy": 90, "silicon": 20},
        {"alloy": 1.6, "credits": 60}, {"ore": 1.0, "credits": 20}, 400,
        "Gantries, a rolling mill and a smelter, delivered in crates. It will "
        "not grow, heal, or surprise you, and it can put a corvette in the water "
        "in three weeks. The Concordat licenses these to anyone who can pay.",
        "", {"build_here": True, "fabricate": True}),
]

COLONIES_BY_ID: dict[str, ColonyClass] = {c.id: c for c in COLONIES}


def colonies_for(body_kind: str, unlocked) -> list[ColonyClass]:
    return [c for c in COLONIES
            if body_kind in c.sites and (c.tech is None or c.tech in unlocked)]
