"""Xenobiology tables.

Planet surveys assemble organisms out of these parts, so every world's biota is
generated but describable — the same way the cell atlas builds forty-two types
out of eight functional classes.
"""

from __future__ import annotations

BIOMES = {
    "barren": ("Barren", 0.02, "dim"),
    "regolith": ("Regolith", 0.10, "osteo"),
    "cryo": ("Cryogenic", 0.22, "lumen"),
    "subsurface": ("Subsurface Ocean", 0.80, "lumen"),
    "microbial": ("Microbial Mat", 0.65, "chloro"),
    "verdant": ("Verdant", 0.95, "chloro"),
    "sulfuric": ("Sulfuric", 0.35, "warn"),
    "aerial": ("Aerial Biosphere", 0.55, "xeno"),
}


def biome_name(bid: str) -> str:
    return BIOMES.get(bid, ("Unknown", 0, "dim"))[0]


def biome_life(bid: str) -> float:
    return BIOMES.get(bid, ("Unknown", 0, "dim"))[1]


FORMS = [
    "filamentous mat", "sessile calcifier", "drifting bell", "burrowing tube",
    "crystalline frond", "colonial raft", "armoured grazer", "sail-borne float",
    "chemotrophic reef", "motile spore-cloud", "branching thallus",
    "jointed swimmer", "plated crawler", "luminous shoal", "anchored siphon",
    "vesicular bloom",
]

#: (id, name, note, value multiplier)
METABOLISMS = [
    ("photo", "photoautotroph", "runs on the local star", 1.0),
    ("chemo", "chemolithotroph", "oxidises reduced minerals", 1.3),
    ("thermo", "thermophile", "lives off vent heat", 1.4),
    ("halo", "halophile", "thrives in brine", 1.2),
    ("radio", "radiotroph", "harvests ionising flux, melanin-fashion", 1.8),
    ("crypto", "cryptobiont", "vitrifies between rains", 1.6),
    ("methano", "methanogen", "exhales methane", 1.1),
    ("piezo", "piezophile", "folded to hold at abyssal pressure", 2.0),
]

#: (id, name, note, commodity it hints at)
TRAITS = [
    ("silica", "silaffin lattice", "grows its own glass optics", "magnetite"),
    ("magneto", "magnetotactic", "aligned Fe₃O₄ chains inside it", "magnetite"),
    ("dsup", "damage-suppressed", "chromatin armoured against radicals", "xenopharma"),
    ("antifreeze", "ice-binding", "glycoproteins halting crystal growth", "trehalose"),
    ("silk", "fibre-spinning", "draws a tough β-sheet cable", "spidroin"),
    ("calcify", "calcifying", "precipitates carbonate on command", "ore"),
    ("lumin", "bioluminescent", "signals in a band nobody expected", "xenopharma"),
    ("toxin", "defended", "secretes something clever and unpleasant", "xenopharma"),
    ("symbiont", "obligately symbiotic", "two organisms sharing one metabolism", "biomass"),
    ("social", "quorum-signalling", "coordinates chemically across a colony", "survey"),
]

BEHAVIOURS = [
    "ignores the survey party entirely",
    "follows the lander at a fixed distance",
    "retracts hard on any vibration",
    "aggregates toward the drill heat",
    "flees light and returns in the dark",
    "has begun growing over the beacon",
    "responds to pressure waves in kind",
    "appears to be counting something",
]

#: Rare, high-signal finds that drive the xenology branch and the Genesis path.
ANOMALIES = [
    ("xenolith", "Worked Xenolith", "xeno", 60,
     "Matter shaped by something that had a purpose and no ancestor in common "
     "with you."),
    ("monolith", "Buried Array", "xeno", 110,
     "A kilometre of buried lattice, still faintly warm, still faintly listening."),
    ("wreck", "Derelict Hull", "steel", 40,
     "A Yards frame, opened from the inside. The log ends mid-sentence and the "
     "inner surfaces are furred with something that is still growing."),
    ("seedbank", "Abandoned Seed Cache", "chloro", 45,
     "Dormant husks in trehalose glass, counters intact, licences long expired."),
    ("vent", "Hydrothermal Vent Field", "lumen", 70,
     "Black smokers in an ocean that has never seen light, crowded with things "
     "that never needed it."),
    ("bloomscar", "Bloom Scar", "warn", 55,
     "A body eaten to a shell and abandoned. The tissue left behind is still "
     "metabolising, slowly, with nothing left to metabolise."),
]


def specimen_value(rng, metabolism_id: str, traits: list) -> int:
    """What a catalogued specimen is worth as data and pharma feedstock."""
    base = 40 + rng.int(0, 60)
    mult = next((m[3] for m in METABOLISMS if m[0] == metabolism_id), 1.0)
    return round(base * mult * (1 + 0.35 * len(traits)))
