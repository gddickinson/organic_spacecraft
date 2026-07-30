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


#: A body plan, and only that. **Not a biochemistry** — `"chemotrophic reef"` was
#: in this pool, and since the metabolism is a separate field the generator
#: cheerfully filed a chemotrophic reef as a photoautotroph. Nobody could see it
#: until the catalogue started grouping by metabolism, and then it was a
#: contradiction printed on the screen. Every entry here is a shape or a habit;
#: what the organism runs on is `METABOLISMS`.
FORMS = [
    "filamentous mat", "sessile calcifier", "drifting bell", "burrowing tube",
    "crystalline frond", "colonial raft", "armoured grazer", "sail-borne float",
    "encrusting reef", "motile spore-cloud", "branching thallus",
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


# ── what your own biology explains ─────────────────────────────────────────
#
# **`Lifeform.metabolism` was the identity key behind the two strings the screens
# show, and nothing read the key itself.** So a catalogue could not group by it
# and nothing could ask whether the captain had any business understanding what
# they were looking at.
#
# The pairing is not invented. Each metabolism is matched to the node in
# `data/tech.py` that is the *same biochemistry*, which the tree's own names give
# away: the Sabatier Loop makes methane, trehalose vitrification *is*
# cryptobiosis, piezolyte physiology is what a piezophile has, and Deinococcus is
# the radiation organism. Four are exact and the rest are the obvious reading of
# both names.
#
# It closes a loop that was already half-built: `data/inquiry.py` says the
# metabolism branch of research runs on **60% specimen evidence**, and
# `world/planets.survey_body` grants research for catalogued life. So knowing a
# biochemistry makes the specimens you find worth more, and the specimens fund
# the branch that knows more biochemistries.
METABOLISM_TECH = {
    "photo": "intima",             # Photosynthetic Intima
    "chemo": "mineralgut",         # Mineral Gut — eats rock
    "thermo": "radiatorbloom",     # Radiator Bloom
    "halo": "waterrefinery",       # Water Refinery
    "methano": "sabatier",         # Sabatier Loop — makes methane
    "crypto": "trehalose",         # Trehalose Cryptobiosis
    "piezo": "piezolyte",          # Piezolyte Physiology
    "radio": "deinococcus",        # Deinococcus Repair — radiation
}

#: What a specimen you can actually read is worth against one you cannot, in
#: research. A tissue sample nobody has the biochemistry for is still a sample:
#: it is catalogued, it still counts, and it yields less until somebody can say
#: what it is doing.
UNDERSTOOD_WORTH = 0.60
