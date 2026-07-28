"""The twelve grown hull classes — the GESTALT fleet itself.

Every one of these is a vessel class from the Fleet Class Reference, with its
own role, crew, mass and gestation time. They are cheap in credits and dear in
phosphate, they take months to ripen, and they close their own wounds.
"""

from __future__ import annotations

from .hull_types import Chassis, slots

GROWN: list[Chassis] = [
    # ── GROWN ───────────────────────────────────────────────────────────────
    Chassis("spore", "SPORE", "grown", "Pod", "Lifeboat / short-hop courier",
            240, 60, slots(1, 1, 1, 1, 1, 0, 1), 12, 2, 3.5, 1.35, 0.30,
            {"credits": 4000, "biomass": 8, "ore": 6}, 21, None,
            "Four metres of ovoid husk with a torpor gland. It cannot fight and "
            "barely carries anything, but it germinates in three weeks from a "
            "seed you can hold in one hand.", "Semen vivum"),
    Chassis("vesper", "VESPER", "grown", "Sentinel", "Scout / relay picket",
            420, 500, slots(1, 1, 3, 2, 1, 1, 1), 30, 4, 5.2, 1.30, 0.26,
            {"credits": 14000, "biomass": 20, "ore": 30, "magnetite": 8}, 60, "magnetite",
            "A tensioned magnetite dish that grew eyes. Sees further than "
            "anything its size and reports what it sees to everyone at once, "
            "which is not always what you wanted.", "Vigil viva"),
    Chassis("radix", "RADIX", "grown", "Uncrewed", "Asteroid miner / seed foundry",
            900, 3200, slots(1, 2, 1, 1, 2, 1, 4), 180, 6, 3.2, 0.80, 0.10,
            {"credits": 26000, "biomass": 40, "ore": 90, "phosphate": 12}, 150, "bioleach",
            "Where RADIX takes hold, a shipyard grows. It eats rock at a hundred "
            "tonnes a day, refines the useful tenth, and gestates the seeds of "
            "every other class from what is left.", "Radix viva"),
    Chassis("medusa", "MEDUSA", "grown", "Harvester", "Comet & volatile harvester",
            760, 2400, slots(1, 1, 2, 1, 2, 1, 4), 320, 8, 4.4, 0.95, 0.18,
            {"credits": 24000, "biomass": 46, "ore": 60, "volatiles": 40}, 130, "waterrefinery",
            "A translucent bell trailing kilometre-long tendrils, glowing "
            "because its ancestor gave science the green fluorescent protein. "
            "It drinks comets and is never short of fuel.", "Aequorea viva"),
    Chassis("navis", "NAVIS", "grown", "Ship", "Crewed long-range explorer",
            1400, 24000, slots(2, 2, 2, 2, 3, 2, 3), 220, 50, 6.0, 1.05, 0.16,
            {"credits": 52000, "biomass": 90, "ore": 180, "phosphate": 40, "silicon": 6},
            240, "osteoid",
            "The reference vessel: 120 metres of hollow organism whose whole "
            "inner surface breathes for its crew, thickening its own shielding "
            "as it flies. Everything else is measured against it.", "Navis viva"),
    Chassis("atlas", "ATLAS", "grown", "Freighter", "Bulk hauler",
            1250, 18000, slots(2, 1, 1, 1, 2, 1, 5), 900, 24, 4.8, 0.85, 0.08,
            {"credits": 46000, "biomass": 70, "ore": 210, "phosphate": 26}, 200, "tendon1",
            "Six hundred metres of grown keel strung with modular holds like a "
            "fish heavy with roe. It electrolyses its own cargo for reaction "
            "mass, which is either elegant or alarming depending on the cargo.",
            "Onus vivum"),
    Chassis("testudo", "TESTUDO", "grown", "Guardian", "Armoured escort",
            2600, 150000, slots(1, 2, 2, 1, 5, 1, 2), 120, 12, 3.6, 0.62, 0.05,
            {"credits": 64000, "biomass": 120, "ore": 340, "phosphate": 70}, 260, "tendon2",
            "A thousand grams per square centimetre of regrowing carapace — "
            "fifty times what a solar storm asks for. Charter doctrine gives it "
            "no weapons at all. It survives hits; it does not return them.",
            "Testudo viva"),
    Chassis("coral", "CORAL", "grown", "Research", "Mobile laboratory",
            1100, 9000, slots(1, 2, 3, 3, 2, 1, 3), 160, 40, 5.0, 0.90, 0.14,
            {"credits": 48000, "biomass": 60, "ore": 130, "phosphate": 30, "silicon": 10},
            210, "synnotch",
            "Grown as a calcite reef, budded with sealed polyp pods for anything "
            "you would rather not share air with. The fleet does its thinking "
            "and its quarantining in the same building.", "Recif vivum"),
    Chassis("nereus", "NEREUS", "grown", "Diver", "Ice-moon ocean explorer",
            980, 3000, slots(1, 2, 3, 2, 2, 1, 3), 90, 6, 4.2, 1.00, 0.20,
            {"credits": 44000, "biomass": 50, "ore": 90, "phosphate": 18, "trehalose": 8},
            170, "piezolyte",
            "Pressure-equalised to 150 MPa with no gas voids anywhere in its "
            "body. It bores through crust with a hot head while its tail "
            "refreezes the channel, and it is the only hull that can reach what "
            "lives under the ice.", "Abyssus viva"),
    Chassis("amber", "AMBER", "grown", "Liner", "Stasis passenger liner",
            1150, 130000, slots(2, 2, 1, 2, 3, 1, 4), 400, 20, 6.6, 0.98, 0.10,
            {"credits": 58000, "biomass": 80, "ore": 150, "trehalose": 30, "phosphate": 22},
            190, "trehalose",
            "Fifty thousand people set in resin at three tonnes a head, against "
            "a habitat's two thousand four hundred. It carries no biosphere "
            "because its passengers are not, for the moment, using one.",
            "Sucinum vivum"),
    Chassis("tardigrade", "TARDIGRADE", "grown", "Vault", "Deep-time archive hull",
            3200, 40000, slots(1, 1, 1, 2, 4, 0, 3), 100, 4, 3.0, 0.55, 0.04,
            {"credits": 70000, "biomass": 90, "ore": 300, "phosphate": 60, "trehalose": 20},
            240, "deinococcus",
            "Mostly shielding wrapped around a very small archive, carrying Dsup "
            "protein and Deinococcus-grade repair. It is rated for a million "
            "years of dormancy, so an afternoon of gunfire is beneath its notice.",
            "Ursus vivus"),
    Chassis("leviathan", "LEVIATHAN", "grown", "Ark", "Interstellar generation ark",
            9000, 12e9, slots(4, 4, 3, 4, 5, 3, 8), 4000, 400, 9.0, 0.50, 0.02,
            {"credits": 900000, "biomass": 2200, "ore": 6000, "phosphate": 900,
             "spidroin": 500, "silicon": 260}, 1400, "multifront",
            "Twelve six-by-twelve-kilometre drums budded from a single trunk, "
            "siphonophore-fashion, sharing one spine and one course. Ten million "
            "people and a full gene library, pointed at somewhere else.",
            "Cetus vivus"),
]
