"""The research tree.

Ten branches, five tiers. The whole tree is the Engineering & Biology Compendium
reorganised as things you can be the first to know: the structural materials,
the closed metabolism, the morphogenesis moonshot, the survival tricks borrowed
off tardigrades and Deinococcus, the two-brained control stack, the biomining
chain, propulsion, the Yards' entirely non-living alternative, the containment
regime that keeps all of it licensed, and whatever it is that lives under the ice.
"""

from __future__ import annotations

from dataclasses import dataclass, field

BRANCHES = {
    "structure": ("Structure", "osteo", "Chitin, bone, silk — what holds"),
    "metabolism": ("Metabolism", "chloro", "Air, water, sugar — what feeds"),
    "morphogenesis": ("Morphogenesis", "chloro", "How a seed knows what to become"),
    "survival": ("Survival", "lumen", "Radiation, cold, pressure, time"),
    "cognition": ("Cognition", "lumen", "The wet brain and the dry one"),
    "industry": ("Industry", "osteo", "Eating rock at a hundred tonnes a day"),
    "propulsion": ("Propulsion", "osteo", "Moving the seed, and later the ship"),
    "fabrication": ("Fabrication", "steel", "The Yards' answer: build it instead"),
    "governance": ("Governance", "lumen", "Licences, canon, charter, consensus"),
    "xenology": ("Xenology", "xeno", "Life that is not ours, and what it left"),
}


@dataclass(frozen=True)
class Tech:
    id: str
    name: str
    branch: str
    tier: int
    reqs: tuple[str, ...]
    cost: int
    blurb: str
    bonus: dict[str, float] = field(default_factory=dict)


def _t(tid, name, branch, tier, reqs, cost, blurb, **bonus):
    return Tech(tid, name, branch, tier, tuple(reqs), cost, blurb, bonus)


TECH: list[Tech] = [
    # ── STRUCTURE ───────────────────────────────────────────────────────────
    _t("mycelium", "Mycelial Matrix", "structure", 0, [], 0,
       "Chitin–glucan hyphae grown by tip-extension, a hundred to four hundred "
       "kilos per cubic metre. Superb in tension, hopeless in compression. "
       "Everything begins here."),
    _t("osteoid", "Osteoid Trusses", "structure", 1, ["mycelium"], 150,
       "Collagen triple-helix nucleating hydroxyapatite in its gap zones, "
       "deposited along the stress lines by Wolff's law. The hull starts "
       "growing its own skeleton.", hull=0.06),
    _t("tendon1", "Tendon Cage Mk I", "structure", 2, ["osteoid"], 300,
       "Spun spidroin at a hundred megapascals working stress. Two and a half "
       "times lighter than steel for the same hoop load, and it can be grown in "
       "place.", hull=0.08),
    _t("tendon2", "Tendon Cage Mk II", "structure", 3, ["tendon1", "turing"], 560,
       "Crimped hierarchical fibril bundles in a mineral-reinforced sheath: "
       "twice the usable fibre stress, half the structure for the same strength.",
       hull=0.12),
    _t("silkbone", "Silk-Bone Composite", "structure", 4, ["tendon2", "separation"], 940,
       "Silk spun directly onto mineralised bone anchors. The joint stops being "
       "the weak point, which is the last thing standing between a hull and a "
       "habitat drum.", hull=0.15, growth=0.10),

    # ── METABOLISM ──────────────────────────────────────────────────────────
    _t("intima", "Photosynthetic Intima", "metabolism", 0, [], 0,
       "Cyanobacteria and green algae carpeting the inner surface at thirty "
       "grams of oxygen per square metre per day. This makes the air. It does "
       "not make the ship."),
    _t("radiatorbloom", "Radiator Bloom", "metabolism", 1, ["intima"], 140,
       "Regulated high-surface-area tissue that opens and closes. Waste heat is "
       "the only thing a closed organism truly excretes, and it must go "
       "somewhere."),
    _t("waterrefinery", "Water Refinery", "metabolism", 1, ["intima"], 160,
       "Melt, filter, electrolyse. Ice becomes oxygen, hydrogen and drinking "
       "water, and suddenly every comet in the sector is a fuel depot."),
    _t("mineralgut", "Mineral Gut", "metabolism", 2, ["waterrefinery", "bioleach"], 320,
       "An alimentary canal at descending pH: leach, separate, refine, absorb. "
       "The organ that admits a grown ship is a chemoheterotroph that happens "
       "to breathe.", growth=0.08),
    _t("sabatier", "Sabatier Loop", "metabolism", 3, ["mineralgut"], 500,
       "Carbon dioxide and hydrogen to methane and water, closing the carbon "
       "loop against leakage. The difference between a long voyage and a "
       "one-way one.", growth=0.06),
    _t("organics", "Organics Digestion", "metabolism", 3, ["mineralgut"], 540,
       "Hydrolysing chondritic kerogen into sugars and amino acids — one and a "
       "half megawatts of chemical energy out of rock that looks like soot. "
       "The real food.", growth=0.12),

    # ── MORPHOGENESIS ───────────────────────────────────────────────────────
    _t("morphogen", "Morphogen Gradients", "morphogenesis", 0, [], 0,
       "A diffusing signal and a set of thresholds — the French-flag model. It "
       "patterns a millimetre. Everything after this is the fight to pattern a "
       "kilometre."),
    _t("synnotch", "synNotch Patterning", "morphogenesis", 1, ["morphogen"], 180,
       "Modular contact receptors building layered structure cell by touching "
       "cell. Lets a growth front lay down a wall in the right order without "
       "being told."),
    _t("turing", "Turing Lamellae", "morphogenesis", 2, ["synnotch"], 340,
       "Short-range activator, long-range inhibitor, and texture that organises "
       "itself: Whipple lamellae, placental villi, bone trabeculae. Specify the "
       "rule, not the strut.", hull=0.05, growth=0.06),
    _t("blastema", "Blastema Regeneration", "morphogenesis", 2, ["synnotch"], 360,
       "Stem cells de-differentiating at a wound and re-running the growth "
       "program locally, sealing first and rebuilding the six layers in order.",
       regen=0.15),
    _t("segclock", "Segmentation Clock", "morphogenesis", 3, ["turing"], 580,
       "A repressilator oscillator against a moving growth front. Segment length "
       "is period times speed — the only known way to lay out ten million "
       "somites.", growth=0.14),
    _t("multifront", "Parallel Growth Fronts", "morphogenesis", 4,
       ["segclock", "silkbone"], 980,
       "Twenty growth fronts held in register across kilometres. One front would "
       "take five hundred and seventy years to grow a habitat drum; twenty take "
       "thirty.", growth=0.30),
    _t("selfheal2", "Self-Heal Mk II", "morphogenesis", 3, ["blastema"], 520,
       "Contractile rings clamp a puncture in seconds, ahead of the clot, over "
       "caches of pre-stocked repair cells. Roughly three times the regrowth "
       "rate.", regen=0.25),

    # ── SURVIVAL ────────────────────────────────────────────────────────────
    _t("melanin", "Melanised Rind", "survival", 1, ["mycelium"], 130,
       "Eumelanin polymerised from tyrosine: broadband absorber, radical "
       "scavenger, and — measured on the station, not argued in a paper — "
       "mildly radiotrophic."),
    _t("dsup", "Dsup Chromatin", "survival", 2, ["melanin"], 300,
       "The tardigrade damage-suppressor bound along the DNA, physically "
       "shielding it from hydroxyl radicals. About forty percent less damage, "
       "in human cells, today."),
    _t("deinococcus", "Deinococcus Repair", "survival", 3, ["dsup"], 540,
       "Manganese antioxidant complexes protecting the repair machinery while "
       "RecA reassembles a shattered genome from overlapping copies. Five "
       "thousand grays.", hull=0.05),
    _t("trehalose", "Trehalose Cryptobiosis", "survival", 3, ["dsup"], 500,
       "Vitrification: sugar glass replaces the water and holds the proteins in "
       "place. Metabolism stops without dying. This is how anything crosses "
       "deep time."),
    _t("piezolyte", "Piezolyte Physiology", "survival", 4, ["trehalose", "separation"], 880,
       "Trimethylamine N-oxide against pressure denaturation, and not one gas "
       "void in the whole body. Rated to a hundred and fifty megapascals — the "
       "bottom of an ocean."),

    # ── COGNITION ───────────────────────────────────────────────────────────
    _t("bioelectric", "Bioelectric Signalling", "cognition", 0, [], 0,
       "Action-potential analogues along nerve tracts and the mycelial net. "
       "Tens of metres a second: fast enough for a reflex, far too slow to fly "
       "a ship."),
    _t("oect", "OECT Interface", "cognition", 1, ["bioelectric"], 190,
       "PEDOT:PSS transistors translating ionic currents into electronic ones. "
       "The native translator between a grown nervous system and a fabricated "
       "one."),
    _t("mea", "Microelectrode Arrays", "cognition", 2, ["oect"], 350,
       "Read and write neural activity at once, with electrogenetic switches "
       "turning a chip instruction into gene expression. The interface becomes "
       "two-way."),
    _t("dishbrain", "Grown Neural Cortex", "cognition", 3, ["mea"], 560,
       "Cultured neurons on an array, trained by consequence until they stop "
       "losing. Twenty watts, superb at pattern, hopeless at arithmetic."),
    _t("reservoir", "Reservoir Computing", "cognition", 3, ["mea"], 520,
       "Stop programming the net and start reading it: the vasculature is "
       "already a dynamical system with the answer on its surface.", research=0.15),
    _t("neuromorphic", "Neuromorphic Bridge", "cognition", 4, ["dishbrain", "aicore"], 960,
       "Wet cortex and dry core bound so tightly through OECTs, MEAs and "
       "optogenetics that the question of which one is flying the ship stops "
       "having an answer.", research=0.20, scan=0.15),

    # ── INDUSTRY ────────────────────────────────────────────────────────────
    _t("bioleach", "Bioleach Root", "industry", 1, ["mycelium"], 140,
       "Acidithiobacillus oxidising iron and sulfur, making its own acid and "
       "drinking the rock it dissolves. Industrially proven on Earth and flown "
       "on the station."),
    _t("chemotropism", "Chemotropic Steering", "industry", 2, ["bioleach"], 300,
       "Chemoreceptors in the root reading ore grade and steering the growing "
       "tip toward the richer seam. Prospecting rather than merely digging."),
    _t("separation", "Separation Gut", "industry", 3, ["chemotropism"], 540,
       "Biosorption and selective precipitation concentrating the scarce "
       "elements. Chondrite is one part in a thousand phosphorus, and bone will "
       "accept no substitute.", trade=0.08),
    _t("magnetite", "Magnetosome Biomineralisation", "industry", 2,
       ["bioleach", "osteoid"], 320,
       "Membrane-templated Fe₃O₄ aligned by MamK into chains. Grown compasses, "
       "grown antennas, and the only sense that still works when the optics are "
       "blind.", scan=0.10),
    _t("solforge", "Solar Foundry", "industry", 4, ["silkbone", "fusiontorch"], 900,
       "A five-kilometre secreted film at a fifth of an AU gathering a terawatt, "
       "with the living part hiding in its shadow behind brutal radiators. "
       "Biology, admitting a limit.", trade=0.15),

    # ── PROPULSION ──────────────────────────────────────────────────────────
    _t("reactionorgan", "Reaction-Mass Organ", "propulsion", 1, ["waterrefinery"], 170,
       "Electrolyse the cargo and throw the hydrogen. Little thrust, and it "
       "refuels at any ice body in the sky, which turns out to matter more."),
    _t("sailfilm", "Secreted Sail Film", "propulsion", 2, ["turing", "organics"], 360,
       "Square kilometres of non-living reflective film, secreted and unfurled. "
       "Draws no power whatsoever and stops working past about three AU."),
    _t("foldrunner", "Foldrunner Coil", "propulsion", 4,
       ["neuromorphic", "fusiontorch", "magnetite"], 1000,
       "The metric trick, sold by the Dry Choir to three factions at three "
       "prices. It roughly doubles how far anyone can reach across the dark.",
       jump=0.10),

    # ── FABRICATION ─────────────────────────────────────────────────────────
    _t("monocoque", "Alloy Monocoque", "fabrication", 0, [], 0,
       "Rolled titanium-aluminium over ribs. Heavier per unit of strength than "
       "grown bone and finished in a fortnight, which is the entire Concordat "
       "argument."),
    _t("whipple", "Whipple Shielding", "fabrication", 1, ["monocoque"], 150,
       "Stand-off plate that flashes a grain to plasma and spreads its load over "
       "a hundred times the area. Ten times less wall mass, for the cost of a "
       "gap."),
    _t("fissionpile", "Fission Pile", "fabrication", 1, ["monocoque"], 180,
       "A shielded fast reactor. Decades of power, and a berthing conversation "
       "at roughly half the ports in the sector."),
    _t("plasmadrive", "Plasma Drive", "fabrication", 2, ["fissionpile"], 320,
       "Magnetoplasmadynamic thrust and a droplet radiator to survive it. The "
       "standard interplanetary engine anywhere the Yards keep an office."),
    _t("pdc", "Point-Defence Cannon", "fabrication", 2, ["monocoque"], 280,
       "Radar-cued autocannon filling a cone with tungsten. It exists to kill "
       "missiles and spore pods, and it is very good at both."),
    _t("railgun", "Railgun", "fabrication", 3, ["pdc"], 480,
       "Eight megajoules down a pair of rails. The weapon that ended the "
       "pretence that Concordat patrol boats were survey vessels."),
    _t("missiles", "Guided Munitions", "fabrication", 3, ["railgun"], 540,
       "Terminal guidance, and a torpedo aimed past the armour at the pressure "
       "hull. Indifferent to evasion; entirely vulnerable to point defence."),
    _t("fusiontorch", "Fusion Torch", "fabrication", 3, ["plasmadrive"], 620,
       "Deuterium and helium-3, open cycle. Halves every transit in the sector "
       "and makes you the brightest thing on anyone's sensors.", jump=0.08),
    _t("fusionlance", "Fusion Lance", "fabrication", 4, ["railgun", "fusiontorch"], 920,
       "A shaped fusion pulse down a magnetic nozzle. One hit ends most "
       "arguments and two overheat you badly enough to lose the next one."),
    _t("ecm", "Electronic Warfare", "fabrication", 3, ["aicore"], 500,
       "False returns, synthetic baselines and a rude noise across the guidance "
       "bands. The cheapest survivability the Yards sell."),
    _t("aicore", "Fabricated AI Core", "fabrication", 2, ["monocoque"], 340,
       "Yards-standard inference silicon. Faster and more precise than anything "
       "wet, and it has never once had an opinion about being switched off.",
       research=0.10),
    _t("nanolam", "Nanolaminate Armour", "fabrication", 4, ["whipple", "silkbone"], 900,
       "Alternating metal and ceramic at nanometre pitch, cracks arrested at "
       "every interface. The best plate anyone rolls, and it still will not grow "
       "back.", hull=0.18),

    # ── GOVERNANCE ──────────────────────────────────────────────────────────
    _t("licence", "Reproduction Licence", "governance", 0, [], 0,
       "No seed germinates unbidden. Every husk carries a cryptographic lock and "
       "will not open without a signed authorisation. The whole containment "
       "regime is this one file."),
    _t("chorus", "CHORUS Consensus", "governance", 2, ["licence", "oect"], 330,
       "An exabyte in five grams of DNA, reconciled across every node like "
       "immune memory. It holds the canonical genome, so lineages stop drifting "
       "apart.", research=0.12),
    _t("firewall", "Genetic Firewall", "governance", 3, ["chorus", "deinococcus"], 560,
       "A recoded genome and obligate dependence on a nutrient found nowhere in "
       "nature. An escapee does not colonise the wild biosphere; it starves in "
       "it.", diplomacy=0.10),
    _t("charter", "The Charter", "governance", 3, ["chorus"], 520,
       "A bounded constitution for a fleet with no sovereign. Decisions ride on "
       "consensus across worlds — the hardest problem in the whole design, and "
       "the least solved.", diplomacy=0.20, trade=0.10),
    _t("consensus", "Fleet Consensus", "governance", 4, ["charter", "firewall"], 960,
       "Every hull, node and dome voting the same canon at light-hour latency "
       "without fragmenting into rival fleets. Nobody has managed it yet. You "
       "would be first.", diplomacy=0.30, growth=0.10),

    # ── XENOLOGY ────────────────────────────────────────────────────────────
    _t("xenobiology", "Comparative Xenobiology", "xenology", 1, ["intima"], 200,
       "A grammar for biochemistries that are not ours. Mostly it teaches you "
       "how much of what you assumed was life was only ever a description of "
       "yourself.", scan=0.12),
    _t("xenopharma", "Xenopharmacology", "xenology", 2, ["xenobiology", "trehalose"], 380,
       "Compounds refined from surveyed organisms. Some of them cure things. "
       "Some are sold long before anyone establishes which.", trade=0.15),
    _t("abyssal", "Abyssal Ecology", "xenology", 3, ["xenobiology", "piezolyte"], 640,
       "What lives at a hundred and fifty megapascals under twenty kilometres of "
       "ice, and the still-unanswered question of whether we had any business "
       "going to look.", research=0.18),
    _t("firstcontact", "First Contact Protocol", "xenology", 4,
       ["abyssal", "consensus"], 1100,
       "A method for speaking to something that shares no ancestor with you, and "
       "a standing rule about what you may do afterwards. Both halves are "
       "load-bearing.", diplomacy=0.25, research=0.25),
]

TECH_BY_ID: dict[str, Tech] = {t.id: t for t in TECH}

#: Techs every commander begins with — a Charter education, and nothing else.
STARTING_TECH = ["mycelium", "intima", "bioelectric", "morphogen", "licence"]

BONUS_KEYS = ("hull", "regen", "jump", "scan", "research", "trade", "diplomacy", "growth")


def can_research(tech_id: str, unlocked) -> bool:
    t = TECH_BY_ID.get(tech_id)
    if t is None or tech_id in unlocked:
        return False
    return all(r in unlocked for r in t.reqs)


def researchable(unlocked) -> list[Tech]:
    return [t for t in TECH if can_research(t.id, unlocked)]


def bonuses(unlocked) -> dict[str, float]:
    """Sum every passive bonus granted by what has been unlocked."""
    out = {k: 0.0 for k in BONUS_KEYS}
    for tid in unlocked:
        t = TECH_BY_ID.get(tid)
        if t:
            for k, v in t.bonus.items():
                out[k] = out.get(k, 0.0) + v
    return out
