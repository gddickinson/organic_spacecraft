"""Weapons and defences.

A note the Charter would want made: nothing in the GESTALT design programme is
a weapon. TESTUDO carries a thousand grams per square centimetre of carapace and
no gun at all — doctrine is avoidance, never interception. Every grown weapon
below is therefore a working organ pointed the wrong way: the mineral gut
throwing its own slag, the mining root spraying its lixiviant, the beacon
flashing at lethal intensity. Captains improvise. The Charter disapproves.
"""

from __future__ import annotations

from .part_types import Ability, Part, Weapon

ARMAMENTS: list[Part] = [
    # ── GROWN WEAPONS ───────────────────────────────────────────────────────
    Part("slug_battery", "Mineral Slug Battery", "weapon", "grown", "mineralgut",
         45, {"credits": 6400, "biomass": 12, "ore": 20}, {"draw": 3},
         "The gut compacts its own tailings into slag slugs and throws them at "
         "four kilometres a second. Ammunition is the one thing a mining ship "
         "never runs out of.",
         wpn=Weapon(22, (2, 4), 4, 0.0, ("ore", 1))),
    Part("lixiviant", "Lixiviant Sprayer", "weapon", "grown", "bioleach",
         30, {"credits": 5200, "biomass": 10, "ore": 8}, {"draw": 2},
         "Sulfuric acid at pH one, sprayed from the mining root. It does very "
         "little to a pressure hull and appalling things to whatever is on the "
         "outside of it.",
         wpn=Weapon(15, (0, 1), 2, 0.10, None, ("ablate",))),
    Part("mag_lance", "Magnetite Lance", "weapon", "grown", "magnetite",
         55, {"credits": 11000, "biomass": 10, "magnetite": 12}, {"draw": 7},
         "A coil of biogenic magnetite discharging the ship's own bioelectric "
         "potential. It barely dents armour and it puts other people's "
         "computers to sleep.",
         wpn=Weapon(13, (1, 3), 6, 0.05, None, ("emp",))),
    Part("photic_flash", "Photic Flash Organ", "weapon", "grown", None,
         18, {"credits": 3400, "biomass": 8}, {"draw": 2},
         "The bioluminescent beacon, run far past its rated output. It hurts no "
         "one and it makes the next thing anyone shoots at you miss.",
         wpn=Weapon(3, (0, 2), 1, 0.20, None, ("blind", "nonlethal"))),
    Part("spore_swarm", "Spore Swarm Pod", "weapon", "grown", "blastema",
         40, {"credits": 14000, "biomass": 20, "phosphate": 4}, {"draw": 4},
         "Germinating spores that root in someone else's hull and start "
         "disassembling it for feedstock. Every treaty in the sector bans "
         "these. Three factions field them.",
         wpn=Weapon(9, (1, 3), 2, 0.05, ("biomass", 1), ("board", "seeking"))),
    Part("tendril_grapple", "Tendril Grapple", "weapon", "grown", "tendon1",
         50, {"credits": 7800, "biomass": 14, "spidroin": 6}, {"draw": 4},
         "Spidroin cable at a gigapascal and a half, meant for catching comets. "
         "It catches other things. What you do once you are holding them is "
         "your business.",
         wpn=Weapon(5, (0, 0), 1, 0.15, None, ("grapple", "plunder"))),

    # ── FABRICATED WEAPONS ──────────────────────────────────────────────────
    Part("pdc", "Point-Defence Cannon", "weapon", "fabricated", "pdc",
         32, {"credits": 6800, "alloy": 16, "silicon": 3}, {"draw": 4},
         "A radar-cued autocannon that fills a cone with tungsten. It kills "
         "missiles, spore pods and, given long enough, corvettes.",
         wpn=Weapon(8, (0, 2), 2, 0.18, ("alloy", 1), ("flak",))),
    Part("railgun", "Railgun", "weapon", "fabricated", "railgun",
         70, {"credits": 16000, "alloy": 34, "silicon": 8}, {"draw": 9},
         "Eight megajoules down a pair of rails. Simple, brutal, and the reason "
         "the Yards stopped pretending their patrol boats were survey vessels.",
         wpn=Weapon(31, (2, 4), 7, 0.05, ("alloy", 1))),
    Part("particle_beam", "Particle Beam", "weapon", "fabricated", "fusionlance",
         85, {"credits": 24000, "alloy": 30, "silicon": 16}, {"draw": 14},
         "Relativistic protons that treat an ablative bumper as a suggestion. "
         "It draws power like a small city and radiates like one too.",
         wpn=Weapon(25, (1, 3), 12, 0.10, None, ("pierce",))),
    Part("fusion_lance", "Fusion Lance", "weapon", "fabricated", "fusionlance",
         130, {"credits": 46000, "alloy": 60, "silicon": 28}, {"draw": 22},
         "A shaped fusion pulse thrown down a magnetic nozzle. One hit ends most "
         "arguments; two overheat you badly enough that you lose the next one.",
         wpn=Weapon(48, (2, 3), 20, 0.0)),
    Part("missile_rack", "Missile Rack", "weapon", "fabricated", "missiles",
         60, {"credits": 19000, "alloy": 26, "silicon": 10}, {"draw": 3},
         "Terminal-guided and indifferent to how well you dodge. Anyone with a "
         "point-defence cannon is indifferent right back.",
         wpn=Weapon(36, (2, 4), 3, 0.0, ("alloy", 2), ("seeking",))),
    Part("breach_torpedo", "Breach Torpedo", "weapon", "fabricated", "missiles",
         95, {"credits": 38000, "alloy": 44, "silicon": 18}, {"draw": 5},
         "A shaped charge on a long stick, aimed at the pressure hull rather "
         "than the armour. Slow, expensive, and it ends ships.",
         wpn=Weapon(68, (3, 4), 5, -0.10, ("alloy", 4), ("seeking", "pierce"))),

    # ── EXOTIC ──────────────────────────────────────────────────────────────
    Part("xeno_resonator", "Xenolith Resonator", "weapon", "any", "firstcontact",
         55, {"credits": 62000, "silicon": 20, "magnetite": 14, "xenolith": 1},
         {"draw": 12},
         "Nobody can say what it does, only what happens afterwards: matter on "
         "the far side stops holding together. The Dry Choir would like it back.",
         wpn=Weapon(30, (1, 4), 6, 0.15, None, ("pierce", "emp"))),

    # ── GROWN DEFENCES ──────────────────────────────────────────────────────
    Part("regrowth_surge", "Regrowth Surge Gland", "defence", "grown", "blastema",
         35, {"credits": 9000, "biomass": 16, "phosphate": 4},
         {"regen": 0.22, "draw": 3},
         "Caches of repair stem cells and nutrient bladders held just under the "
         "skin. Deposition surges to thirty times baseline: a half-metre gouge "
         "closes in a fortnight instead of a season.",
         ability=Ability("regrow", "Regrowth Surge", 3)),
    Part("sphincter_seal", "Sphincter Bulkheads", "defence", "grown", None,
         40, {"credits": 4200, "biomass": 12, "ore": 8}, {"armour": 2},
         "Muscular leaves that iris shut and clamp airtight, the same mechanism "
         "as a docking port. Sacrifices the breached compartment to save the "
         "rest — lizard-tail logic, and it works.",
         ability=Ability("seal", "Compartment Seal", 4)),
    Part("carapace", "Interposing Carapace", "defence", "grown", "tendon2",
         110, {"credits": 17000, "biomass": 24, "ore": 40, "phosphate": 10},
         {"armour": 7, "hullMul": 0.14, "evade": -0.03},
         "The TESTUDO answer to being shot at: put more tortoise between the "
         "hazard and the thing that matters. Doctrine calls this all of defence.",
         ability=Ability("interpose", "Interpose", 3)),
    Part("ablative_shed", "Ablative Shed Reflex", "defence", "grown", None,
         25, {"credits": 3600, "biomass": 10}, {"regen": 0.10},
         "Drops the entire sacrificial layer at once, taking the incoming hit "
         "with it. The epidermis was always meant to die; this only hurries it.",
         ability=Ability("shed", "Shed Epidermis", 3)),
    Part("melanin_ward", "Melanised Ward", "defence", "grown", "melanin",
         45, {"credits": 6200, "biomass": 14},
         {"armour": 4, "vent": 5, "heatCap": 10},
         "Eumelanin thickened past shielding spec. Broadband absorber, radical "
         "scavenger, and — tested on the station, not in theory — mildly "
         "radiotrophic."),
    Part("nociception", "Nociception Mesh", "defence", "grown", "selfheal2",
         30, {"credits": 12000, "biomass": 14, "magnetite": 4},
         {"regen": 0.16, "evade": 0.06, "accuracy": 0.04, "draw": 2},
         "A sensor net that localises damage in milliseconds and pre-thickens "
         "tissue wherever it keeps getting hit. The ship learns where it is "
         "vulnerable."),
    Part("dsup_chromatin", "Dsup Chromatin", "defence", "grown", "dsup",
         15, {"credits": 10000, "biomass": 8, "trehalose": 4},
         {"armour": 2, "crewGuard": 0.45},
         "Tardigrade damage-suppressor bound along the DNA, cutting radiation "
         "damage by about forty percent. It protects the crew, not the hull."),

    # ── FABRICATED DEFENCES ─────────────────────────────────────────────────
    Part("whipple_screen", "Whipple Screen", "defence", "fabricated", "whipple",
         60, {"credits": 5800, "alloy": 22}, {"armour": 6, "hullMul": 0.08},
         "Stand-off plate ahead of the hull. A grain hitting it flashes to "
         "plasma and spreads its load over a hundred times the area — ten times "
         "less wall, for the cost of a gap."),
    Part("ablative_plate", "Ablative Plating", "defence", "fabricated", "monocoque",
         80, {"credits": 7400, "alloy": 30},
         {"armour": 8, "evade": -0.04, "hullMul": 0.12},
         "Sacrificial layers of boron carbide and foam. Heavy, cheap, and it "
         "must be replaced in dock because it certainly will not replace itself."),
    Part("ecm_suite", "ECM Suite", "defence", "fabricated", "ecm",
         40, {"credits": 14000, "alloy": 12, "silicon": 12},
         {"evade": 0.12, "draw": 6},
         "Deceptive returns, false baselines, and a very rude noise across the "
         "guidance bands. Missiles hate it. So do gunnery officers.",
         ability=Ability("jam", "Jam Fire Control", 3)),
    Part("pd_grid", "Point-Defence Grid", "defence", "fabricated", "pdc",
         55, {"credits": 11000, "alloy": 20, "silicon": 8},
         {"armour": 3, "flak": 1, "draw": 5},
         "Networked turrets on a shared fire-control picture. Nothing seeking "
         "gets through cleanly, which is the entire reason torpedoes cost so "
         "much."),
    Part("heat_sink_bank", "Heat Sink Bank", "defence", "any", "plasmadrive",
         50, {"credits": 8200, "alloy": 18, "silicon": 4},
         {"heatCap": 40, "vent": 8},
         "Lithium blocks that soak what the radiators cannot. Heat is the only "
         "thing you truly must get rid of; this buys a few more minutes of "
         "ignoring that.",
         ability=Ability("vent", "Emergency Vent", 4)),
    Part("mass_driver", "Mass Driver", "weapon", "fabricated", "railgun",
         120, {"credits": 27000, "alloy": 58, "silicon": 12}, {"draw": 12},
         "A coilgun long enough to need its own keel, throwing unrefined slag "
         "at the horizon. The ammunition is whatever you were standing on.",
         wpn=Weapon(41, (3, 4), 9, -0.05, ("ore", 2))),
    Part("drone_bay", "Drone Bay", "weapon", "fabricated", "dronework",
         70, {"credits": 23000, "alloy": 30, "silicon": 20}, {"draw": 6},
         "Racks of small autonomous things that undock, form up, and do not "
         "come back. Banned in two jurisdictions and standard in the other four.",
         wpn=Weapon(27, (1, 3), 3, 0.08, ("alloy", 1), ("seeking",))),
    Part("coherent_beam", "Coherent Beam", "weapon", "synthetic", "synthmind",
         90, {"credits": 44000, "silicon": 34, "alloy": 24}, {"draw": 20},
         "A phased optical array firing on a solution computed after the shot "
         "was already in flight. It does not miss so much as decline to.",
         wpn=Weapon(33, (2, 4), 15, 0.20, None, ("pierce",))),
    Part("phase_screen", "Phase Screen", "defence", "synthetic", "synthmind",
         46, {"credits": 26000, "silicon": 22, "magnetite": 8},
         {"evade": 0.16, "armour": 3, "draw": 9},
         "The hull is somewhere in a cloud of plausible hulls. Gunnery officers "
         "describe shooting at it as demoralising.",
         ability=Ability("jam", "Fold the Screen", 3)),
]
