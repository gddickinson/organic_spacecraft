"""Fitted systems — drives, power, senses, brains and working organs.

Grown modules are organs from the cell atlas; fabricated modules are machines.
A grown hull will not take a fission pile and a Yards hull cannot host an
intima, but a hybrid frame will carry either, which is the whole point of one.
"""

from __future__ import annotations

from .part_types import Part

MODULES: list[Part] = [
    # ── DRIVE ───────────────────────────────────────────────────────────────
    # No negative `drink`: reaction mass is already paid for as volatiles per
    # jump, and counting it here would show as a negative harvest rate.
    Part("reaction_organ", "Reaction-Mass Organ", "drive", "grown", "reactionorgan",
         40, {"credits": 3200, "biomass": 10, "ore": 8},
         {"jump": 1.2, "speed": 0.10, "draw": 2},
         "Electrolyses stored water and throws the hydrogen. Modest thrust, and "
         "it refuels anywhere there is ice — which, in this arm of the sky, is "
         "everywhere."),
    Part("ion_cluster", "Ion Thruster Cluster", "drive", "fabricated", "monocoque",
         55, {"credits": 5400, "alloy": 12, "silicon": 2},
         {"jump": 1.6, "speed": 0.16, "draw": 4},
         "Gridded xenon ions at high specific impulse. Patient, efficient and "
         "entirely uninterested in how urgently you need to be elsewhere."),
    Part("plasma_drive", "Plasma Drive", "drive", "fabricated", "plasmadrive",
         90, {"credits": 12000, "alloy": 26, "silicon": 6},
         {"jump": 2.4, "speed": 0.34, "draw": 8, "heatCap": 10},
         "Magnetoplasmadynamic, and loud about it. The standard interplanetary "
         "engine anywhere the Yards have a sales office."),
    Part("fusion_torch", "Fusion Torch", "drive", "fabricated", "fusiontorch",
         160, {"credits": 34000, "alloy": 60, "silicon": 20},
         {"jump": 4.0, "speed": 0.58, "draw": 16, "heatCap": 20},
         "Deuterium-helium-3 running open-cycle. It will halve your transit "
         "times and triple everything else about you that a sensor can see."),
    Part("sail_film", "Secreted Sail Film", "drive", "grown", "sailfilm",
         25, {"credits": 9000, "biomass": 16, "ore": 10},
         {"jump": 2.0, "speed": 0.24, "evade": 0.04},
         "A square kilometre of non-living reflective film, secreted and "
         "unfurled the way SOL-FORGE does it. Draws no power at all. Useless "
         "past three AU."),
    Part("foldrunner", "Foldrunner Coil", "drive", "any", "foldrunner",
         210, {"credits": 78000, "alloy": 70, "silicon": 44, "magnetite": 20},
         {"jump": 6.5, "speed": 0.42, "draw": 22, "heatCap": 24},
         "The metric trick the Dry Choir sold to three factions at three prices. "
         "Doubles your reach across the dark. Nobody who fits one asks how it "
         "works twice."),

    # ── POWER ───────────────────────────────────────────────────────────────
    Part("intima_bloom", "Intima Bloom", "power", "grown", "intima",
         30, {"credits": 2400, "biomass": 12},
         {"power": 6, "o2": 60, "regen": 0.05, "graze": 0.3},
         "Extra photosynthetic canopy: Synechocystis and Chlamydomonas at thirty "
         "grams of oxygen per square metre per day. It will not move the ship, "
         "but the crew keeps breathing while you argue about what will."),
    Part("chemo_gut", "Chemotrophic Gut", "power", "grown", "mineralgut",
         70, {"credits": 6800, "biomass": 18, "ore": 22},
         {"power": 14, "mine": 0.5, "heatCap": 8},
         "Oxidises reduced iron and sulfur with the intima's own oxygen. This is "
         "the engine that actually builds a hull — photosynthesis only ever "
         "made the air."),
    Part("fission_pile", "Fission Pile", "power", "fabricated", "fissionpile",
         120, {"credits": 15000, "alloy": 34, "silicon": 8},
         {"power": 26, "heatCap": 16},
         "A shielded fast reactor. Reliable for decades and radiologically "
         "unwelcome in about half the ports you will want to visit."),
    Part("fusion_plant", "Fusion Plant", "power", "fabricated", "fusiontorch",
         180, {"credits": 42000, "alloy": 66, "silicon": 26},
         {"power": 52, "heatCap": 26},
         "Fifty megawatts in a hull-mounted bottle. Everything the Yards build "
         "above corvette weight assumes one of these is present."),
    Part("radiator_bloom", "Radiator Bloom", "power", "grown", "radiatorbloom",
         45, {"credits": 5200, "biomass": 14, "ore": 12},
         {"vent": 14, "heatCap": 22, "power": 2},
         "Two thousand square metres of high-surface-area tissue that opens and "
         "closes. Heat is the one thing a living ship truly excretes; this is how."),
    Part("droplet_rad", "Droplet Radiator", "power", "fabricated", "plasmadrive",
         60, {"credits": 9800, "alloy": 22, "silicon": 4},
         {"vent": 20, "heatCap": 14},
         "Sprays hot liquid metal across a gap and catches it cold. Sheds more "
         "heat than anything grown, and leaves a trail a child could follow."),

    # ── SENSOR ──────────────────────────────────────────────────────────────
    Part("opsin_eyes", "Opsin Eye Cluster", "sensor", "grown", None,
         12, {"credits": 1600, "biomass": 5},
         {"sensor": 1.2, "scan": 0.10, "accuracy": 0.04},
         "Photoreceptor retinas behind grown crystallin lenses. Star-tracking, "
         "docking, and a slow blink when something bright happens."),
    Part("vesper_organ", "VESPER Organ", "sensor", "grown", "magnetite",
         26, {"credits": 7400, "biomass": 8, "magnetite": 6},
         {"sensor": 2.6, "scan": 0.18, "accuracy": 0.05},
         "Aligned magnetosome chains reading planetary and stellar fields. It "
         "works with the lights off, through rock, and when your optics are "
         "dazzled."),
    Part("chemo_array", "Chemoreceptor Array", "sensor", "grown", "chemotropism",
         18, {"credits": 4600, "biomass": 9, "ore": 6},
         {"sensor": 0.8, "scan": 0.30, "mine": 0.4},
         "Tastes ore grade at a distance and steers the mining root toward the "
         "richer seam. The difference between digging and prospecting."),
    Part("phased_array", "Phased Array", "sensor", "fabricated", "monocoque",
         34, {"credits": 6200, "alloy": 12, "silicon": 6},
         {"sensor": 2.2, "scan": 0.14, "accuracy": 0.08},
         "Steered radar and a wideband passive ear. Sees further than an eye and "
         "tells everyone within a light-hour exactly where you are."),
    Part("interferometer", "Interferometric Suite", "sensor", "any", "aicore",
         48, {"credits": 19000, "alloy": 18, "silicon": 18, "magnetite": 8},
         {"sensor": 4.0, "scan": 0.34, "research": 0.4},
         "Baselines synthesised across a picket of relays for microarcsecond "
         "resolution. You can read a hull number from another star with this."),

    # ── COMPUTE ─────────────────────────────────────────────────────────────
    Part("bioelectric_net", "Bioelectric Net", "compute", "grown", "bioelectric",
         10, {"credits": 1900, "biomass": 6},
         {"regen": 0.10, "evade": 0.02, "o2": 20},
         "Body-wide autonomic signalling on the mycelial net. Slow — tens of "
         "metres a second — but it holds homeostasis when everything faster is "
         "dead."),
    Part("silicon_core", "Silicon Core", "compute", "any", None,
         20, {"credits": 5800, "silicon": 4},
         {"accuracy": 0.10, "jump": 0.5, "research": 0.2, "draw": 3},
         "An inorganic payload planted with the seed, like a stone in a fruit. "
         "You cannot grow a processor, so every living ship carries one and "
         "resents it."),
    Part("dishbrain", "DishBrain Cortex", "compute", "grown", "dishbrain",
         24, {"credits": 16000, "biomass": 14, "silicon": 3},
         {"accuracy": 0.12, "evade": 0.08, "research": 0.6, "draw": 1},
         "Cultured neurons on a microelectrode array, trained the way the first "
         "ones were: by playing games with them until they stopped losing."),
    Part("reservoir", "Reservoir Lattice", "compute", "grown", "reservoir",
         18, {"credits": 12000, "biomass": 11},
         {"scan": 0.22, "research": 0.8, "regen": 0.06},
         "Reads the vascular net itself as a dynamical system and takes the "
         "answer off the surface. Computation you grew rather than programmed."),
    Part("ai_core", "Fabricated AI Core", "compute", "fabricated", "aicore",
         40, {"credits": 28000, "alloy": 14, "silicon": 22},
         {"accuracy": 0.20, "jump": 1.0, "research": 1.0, "draw": 8},
         "Yards-standard inference stack. Faster and more precise than anything "
         "wet, and it has never once had an opinion about being switched off."),
    Part("neuromorph", "Neuromorphic Bridge", "compute", "any", "neuromorphic",
         36, {"credits": 44000, "silicon": 26, "biomass": 12, "magnetite": 6},
         {"accuracy": 0.18, "evade": 0.10, "research": 1.2, "regen": 0.10, "draw": 5},
         "OECTs and electrogenetics binding a wet cortex to a dry one so tightly "
         "that neither is in charge. The cyborg thesis, fitted as a component."),

    # ── UTILITY ─────────────────────────────────────────────────────────────
    # Ice processing is the root's third ingest route in the metabolism
    # document — and without it a captain can strand with ore but no fuel.
    Part("mining_root", "Mining Root", "utility", "grown", "bioleach",
         60, {"credits": 4800, "biomass": 14, "ore": 16},
         {"mine": 3.2, "phos": 0.10, "drink": 0.8, "draw": 3},
         "Acidophile cells secreting sulfuric acid at the rock face, pH about "
         "one. It dissolves the asteroid and drinks the result, and it will "
         "melt and crack ice for water when there is no rock worth having."),
    Part("separation_gut", "Separation Gut", "utility", "grown", "separation",
         70, {"credits": 11000, "biomass": 18, "ore": 24},
         {"mine": 1.4, "phos": 0.36, "draw": 4},
         "Biosorption and selective precipitation behind the mining face. This "
         "is the organ that finds phosphorus in rock that is 0.1% phosphorus."),
    Part("ore_crusher", "Ore Processing Rig", "utility", "fabricated", "monocoque",
         90, {"credits": 8600, "alloy": 26, "silicon": 4},
         {"mine": 4.0, "phos": 0.14, "draw": 9, "heatCap": 6},
         "Crushers, mills and a flotation circuit. Cruder than a gut and twice "
         "as fast, and it does not sulk when the ore grade drops."),
    Part("harvest_tendril", "Harvest Tendrils", "utility", "grown", "waterrefinery",
         50, {"credits": 5600, "biomass": 16, "volatiles": 10},
         {"drink": 3.6, "draw": 2},
         "Kilometre-long grabbers with sublimation and filter organs behind "
         "them. A one-kilometre comet holds two hundred and sixty million "
         "tonnes. Take your time."),
    Part("cargo_villi", "Modular Holds", "utility", "any", None,
         30, {"credits": 2600, "ore": 10}, {"cargo": 120},
         "Pressurised, cryogenic or open, budding off the keel and resealing "
         "when they drop. Whatever the shape of the money, it fits in one."),
    Part("crew_girdle", "Habitat Girdle", "utility", "any", None,
         55, {"credits": 4400, "biomass": 10, "ore": 12},
         {"berths": 24, "morale": 0.5, "o2": 30},
         "Spun decks at four-tenths of a gravity, nested inside the fixed hull. "
         "Crews who sleep with weight on them stay sane measurably longer."),
    Part("polyp_lab", "Polyp Laboratory", "utility", "grown", "synnotch",
         42, {"credits": 13000, "biomass": 16, "silicon": 4},
         {"research": 1.4, "scan": 0.20, "draw": 3},
         "A sealed CORAL pod: absolute biocontainment, medical-grade sterility, "
         "and a door that only opens from outside."),
    Part("seed_bay", "Seed Bay", "utility", "grown", "licence",
         65, {"credits": 15000, "biomass": 22, "phosphate": 8},
         {"draw": 3, "colony": 1},
         "Gestation cradles for class seeds, with a placental vascular tree and "
         "a lock that will not open without a signed licence. Lets you found "
         "colonies."),
    Part("torpor_gland", "Torpor Gland", "utility", "grown", "trehalose",
         22, {"credits": 7200, "biomass": 8, "trehalose": 4},
         {"o2": 220, "morale": -0.1},
         "Puts the crew down into trehalose glass and wakes them when the air is "
         "breathable again. Stretches days of oxygen into months of patience."),
    Part("melt_head", "Melt Head", "utility", "grown", "piezolyte",
         80, {"credits": 18000, "biomass": 20, "ore": 26},
         {"draw": 8, "dive": 1, "heatCap": 12},
         "Bores kilometres of ice while the tail refreezes the channel behind. "
         "The only way anyone has reached a subsurface ocean and come back up."),
    Part("chorus_node", "CHORUS Node", "utility", "any", "chorus",
         28, {"credits": 21000, "silicon": 8, "biomass": 10},
         {"research": 0.8, "morale": 0.4, "drift": 1},
         "An exabyte in five grams of DNA, reconciling against every other node "
         "in the mesh. It holds the canonical genome, so your lineage stops "
         "drifting."),
    Part("drydock_arm", "Drydock Arms", "utility", "fabricated", "monocoque",
         75, {"credits": 12000, "alloy": 30, "silicon": 6},
         {"repair": 1, "draw": 5},
         "Manipulators, plate stock and a very patient welding crew. Fabricated "
         "hulls do not heal, so somebody has to be holding the torch."),
    Part("swarm_logic", "Swarm Logic Core", "compute", "synthetic", "dronework",
         26, {"credits": 22000, "silicon": 18, "alloy": 8},
         {"accuracy": 0.16, "research": 0.5, "draw": 6, "sensor": 0.6},
         "Eleven hundred small minds voting on where to be. It is not clever, "
         "individually, and collectively it does not need to be."),
    Part("cold_ledger", "Cold Ledger", "compute", "synthetic", "synthmind",
         30, {"credits": 38000, "silicon": 30},
         {"accuracy": 0.22, "jump": 1.2, "research": 1.4, "draw": 7},
         "The Dry Choir's own inference stack, sold sealed. It answers "
         "navigation problems before the question finishes and declines to "
         "discuss anything else."),
    Part("cryo_hold", "Cryogenic Berths", "utility", "fabricated", "monocoque",
         48, {"credits": 9800, "alloy": 26, "silicon": 6},
         {"berths": 60, "cargo": 40, "o2": 40},
         "Sixty bunks and a chiller, in the volume a grown liner would give to "
         "resin glands. Passengers arrive tired rather than young."),
    Part("smelter_bay", "Smelter Bay", "utility", "fabricated", "monocoque",
         110, {"credits": 16000, "alloy": 44, "silicon": 10},
         {"mine": 1.2, "refine": 1, "draw": 12, "heatCap": 10},
         "An arc furnace and a caster in the hold. Turns ore into alloy on the "
         "way home, which is the difference between hauling rock and hauling "
         "money."),
    Part("survey_boom", "Survey Boom", "sensor", "fabricated", "aicore",
         44, {"credits": 15000, "alloy": 20, "silicon": 14},
         {"sensor": 3.0, "scan": 0.26, "research": 0.5, "draw": 5},
         "A kilometre of unfolded truss holding the instruments far enough from "
         "the reactor to hear anything at all."),
    Part("xeno_lattice", "Xenolith Lattice", "defence", "xeno", "xenoalloy",
         50, {"credits": 30000, "xenolith": 1, "silicon": 12},
         {"armour": 9, "regen": 0.20, "hullMul": 0.10},
         "Grown to a pattern read off a relic. It knits overnight, it rings when "
         "struck, and the ringing is somehow load-bearing."),
]
