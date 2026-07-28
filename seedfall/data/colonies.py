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
    # ── stations nobody grew ────────────────────────────────────────────
    ColonyClass(
        "fab_yard", "Fabricator Yard", "fabricated", "monocoque",
        ("asteroid", "moon", "rocky"), 60,
        {"credits": 46000, "alloy": 90, "silicon": 20},
        {"alloy": 1.6, "credits": 60}, {"ore": 1.0, "credits": 20}, 400,
        "Gantries, a rolling mill and a smelter, delivered in crates. It will "
        "not grow, heal, or surprise you, and it can put a corvette in the water "
        "in three weeks. The Concordat licenses these to anyone who can pay.",
        "", {"build_here": True, "fabricate": True}),
    ColonyClass(
        "orbital_dock", "Orbital Drydock", "fabricated", "whipple",
        ("asteroid", "moon", "rocky", "gas"), 80,
        {"credits": 58000, "alloy": 130, "silicon": 28},
        {"credits": 140}, {"alloy": 0.4}, 600,
        "Four slipways, a plate mill and a gantry crane you can see from the "
        "next orbit. It lays down welded hulls and charges everyone else in the "
        "system for the privilege of being repaired.",
        "", {"build_here": True, "drydock": True}),
    ColonyClass(
        "refinery", "Refinery Platform", "fabricated", "monocoque",
        ("asteroid", "moon", "rocky"), 70,
        {"credits": 32000, "alloy": 60, "silicon": 12},
        {"alloy": 2.2, "credits": 40}, {"ore": 3.0}, 300,
        "Roasters, a flotation circuit and a caster. It eats three tonnes of "
        "your ore for every two of alloy it hands back, which is a poor trade "
        "until you notice what alloy sells for.",
        "", {"fabricate": True}),
    ColonyClass(
        "monitor_station", "Monitor Station", "fabricated", "railgun",
        ("asteroid", "moon", "rocky", "comet", "ice", "gas"), 110,
        {"credits": 64000, "alloy": 210, "silicon": 30},
        {}, {"alloy": 0.3, "credits": 30}, 120,
        "Batteries, a fire-control mast and standing orders to burn anything "
        "that germinates without a licence. It cannot chase, but nothing "
        "unlicensed takes root in a system it is watching.",
        "", {"ward": 0.6, "watch": True}),
    ColonyClass(
        "skimmer", "Helium Skimmer", "fabricated", "plasmadrive",
        ("gas",), 90,
        {"credits": 27000, "alloy": 52, "silicon": 10},
        {"volatiles": 3.6, "credits": 30}, {"credits": 15}, 120,
        "A scoop on a very long tether, trailing through the upper cloud deck "
        "and coming back up heavy. Cheaper than a comet and it never runs out.",
        "", {}),
    ColonyClass(
        "free_port", "Free Port", "hybrid", "oect",
        ("asteroid", "moon", "rocky", "comet", "ice", "gas"), 140,
        {"credits": 74000, "alloy": 90, "biomass": 60, "ore": 120},
        {"credits": 260}, {"biomass": 0.2}, 5000,
        "A Yards frame with habitat grown through it, a market floor, and a "
        "harbourmaster who asks nothing. Opens a port in a system that had "
        "none — which is worth rather more than the docking fees.",
        "", {"port": True, "diplomacy": 0.03}),
    ColonyClass(
        "relay_choir", "Relay Choir", "synthetic", "synthmind",
        ("asteroid", "moon", "comet", "ice", "rocky", "gas"), 100,
        {"credits": 52000, "silicon": 60, "magnetite": 20},
        {"research": 3.0, "survey": 0.10}, {"credits": 25}, 0,
        "A cold rack of Dry Choir substrate that thinks about the system it sits "
        "in and tells you what it concluded. Nobody has established whether it "
        "is also telling anyone else.",
        "", {"sensor": 4.0, "watch": True}),
    ColonyClass(
        "xeno_array", "Reactivated Array", "xeno", "xenoalloy",
        ("rocky", "moon", "ice", "asteroid"), 260,
        {"credits": 96000, "xenolith": 3, "silicon": 50, "biomass": 40},
        {"research": 4.2, "xenolith": 0.01}, {"credits": 40}, 40,
        "A kilometre of buried lattice, dug out and persuaded to run again. It "
        "is still faintly warm, still faintly listening, and it will lay down "
        "hulls to a plan nobody in the Verge wrote.",
        "responsum", {"xenoyard": True, "sensor": 3.0}),
]

COLONIES_BY_ID: dict[str, ColonyClass] = {c.id: c for c in COLONIES}


def colonies_for(body_kind: str, unlocked) -> list[ColonyClass]:
    return [c for c in COLONIES
            if body_kind in c.sites and (c.tech is None or c.tech in unlocked)]
