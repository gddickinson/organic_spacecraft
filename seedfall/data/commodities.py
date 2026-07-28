"""Tradeable goods.

The economy is the metabolism document turned inside out: a grown ship eats
rock, ice and phosphate and excretes heat and tailings, so those are what the
ports want. Silicon is the interesting one — nobody can grow a processor, so
even the Charter's living fleet has to buy its brains.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Commodity:
    id: str
    name: str
    short: str
    base: int          # baseline credits per unit
    volatility: float
    cat: str
    legal: bool
    blurb: str
    bulk: float = 1.0  # tonnes of hold consumed per unit


COMMODITIES: list[Commodity] = [
    Commodity(
        "ore", "Ore Pellets", "Ore", 42, 0.30, "bulk", True,
        "Mineralised feedstock from a RADIX gut — iron, silicon, magnesium. "
        "The bulk of every hull, grown or riveted."),
    Commodity(
        "volatiles", "Volatiles", "Ice", 38, 0.35, "bulk", True,
        "Cometary water, CO₂ and ammonia. Reaction mass, drinking water and "
        "oxygen, in that order of how loudly people complain when it runs out."),
    Commodity(
        "phosphate", "Phosphate Concentrate", "Phos", 340, 0.45, "strategic", True,
        "Chondrite runs 0.1% phosphorus. Bone needs it and nothing substitutes. "
        "A hull is ~18× its own mass in rock, chased almost entirely for this."),
    Commodity(
        "biomass", "Biomass", "Bio", 66, 0.28, "bulk", True,
        "Cultured protein and structural polysaccharide. Feeds crews, patches "
        "hulls, and starts arguments about which is the better use."),
    Commodity(
        "silicon", "Silicon Cores", "Cores", 880, 0.25, "strategic", True,
        "Fabricated logic. You cannot grow a processor or a radio, so every "
        "living ship carries a stone in the fruit — and buys it from the Yards."),
    Commodity(
        "alloy", "Structural Alloy", "Alloy", 155, 0.22, "industrial", True,
        "Rolled titanium-aluminium plate. Heavier than grown bone per unit of "
        "strength, and it never once needs feeding."),
    Commodity(
        "spidroin", "Spidroin Fibre", "Silk", 470, 0.33, "industrial", True,
        "Spun MaSp1/MaSp2 dope at 1.3 GPa and 300 MJ/m³ of toughness. Kevlar "
        "manages fifty. The tendon cage of every spinning thing ever grown."),
    Commodity(
        "magnetite", "Magnetosome Chain", "Mag", 520, 0.30, "industrial", True,
        "Aligned biogenic Fe₃O₄ grown by magnetotactic culture. Antennas, "
        "compasses, and the only sense organ that works with the lights off."),
    Commodity(
        "trehalose", "Trehalose Glass", "Glass", 610, 0.38, "medical", True,
        "Vitrified sugar with CAHS proteins. Replaces the water in a cell and "
        "holds it, unbreathing, for as long as you need it held."),
    Commodity(
        "xenopharma", "Xenopharma", "Pharma", 1240, 0.55, "medical", True,
        "Compounds refined from surveyed lifeforms. Some cure things. Some are "
        "sold before anyone establishes which."),
    Commodity(
        "survey", "Survey Data", "Data", 460, 0.40, "information", True,
        "Charted orbits, ore grades, spectra. Every faction buys it and every "
        "faction believes the copy they bought is exclusive.", bulk=0.1),
    Commodity(
        "xenolith", "Xenolith", "Relic", 3600, 0.60, "information", True,
        "Worked matter of no human origin. The Dry Choir pays in cores; the "
        "Charter asks, politely, that you stop picking them up.", bulk=0.2),
    Commodity(
        "licence", "Reproduction Licence", "Licence", 2400, 0.50, "strategic", True,
        "A signed cryptographic authorisation. No seed germinates without one. "
        "The whole containment regime rests on this being unforgeable, "
        "which it is not.", bulk=0.05),
    Commodity(
        "wildseed", "Unlicensed Seed", "Wildseed", 5200, 0.70, "contraband", False,
        "A viable seed husk with the Hayflick counter cut out of it. Grows "
        "anything, anywhere, forever. This is precisely how the Bloom started.",
        bulk=0.05),
]

BY_ID: dict[str, Commodity] = {c.id: c for c in COMMODITIES}
TRADE_IDS: list[str] = [c.id for c in COMMODITIES]


def bulk_of(cid: str) -> float:
    c = BY_ID.get(cid)
    return c.bulk if c else 1.0


def name_of(cid: str) -> str:
    c = BY_ID.get(cid)
    return c.name if c else cid


CATEGORIES = {
    "bulk": ("Bulk", "osteo"),
    "strategic": ("Strategic", "lumen"),
    "industrial": ("Industrial", "osteo"),
    "medical": ("Medical", "chloro"),
    "information": ("Information", "lumen"),
    "contraband": ("Contraband", "warn"),
}
