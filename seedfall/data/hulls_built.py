"""Hulls that were not grown.

FABRICATED are Concordat of Yards work, named after tools and trades in the
deliberate way of people who think a ship is a machine. HYBRID are Freehold
grafts. SYNTHETIC are Dry Choir vessels, named for the mathematics they run on
and crewed by nobody. XENO are the two hulls nobody in the Verge designed.
"""

from __future__ import annotations

from .hull_types import Chassis, slots

# ── FABRICATED · Concordat of Yards ────────────────────────────────────────
FABRICATED: list[Chassis] = [
    Chassis("tender", "TENDER", "fabricated", "Tug", "Yard tender / repair tug",
            300, 700, slots(1, 1, 1, 1, 1, 0, 3), 60, 8, 3.8, 1.15, 0.20,
            {"credits": 15000, "alloy": 18, "silicon": 4}, 10, "monocoque",
            "Manipulator arms, plate stock and a very patient welding crew. It "
            "cannot fight and will not impress anyone, and every yard in the "
            "Verge keeps three of them."),
    Chassis("halyard", "HALYARD", "fabricated", "Courier", "Fast courier / scout",
            380, 900, slots(2, 1, 2, 2, 1, 1, 1), 40, 6, 6.4, 1.55, 0.32,
            {"credits": 26000, "alloy": 30, "silicon": 8}, 12, "monocoque",
            "The Yards' argument in miniature: nothing on it is alive, nothing "
            "on it needs feeding, and it was in service the same fortnight it "
            "was ordered."),
    Chassis("awl", "AWL", "fabricated", "Runner", "Quiet runner / smuggler",
            420, 1100, slots(2, 1, 2, 2, 2, 1, 2), 90, 9, 5.8, 1.48, 0.38,
            {"credits": 33000, "alloy": 26, "silicon": 14}, 16, "ecm",
            "Cold-faced, baffled and radar-shy, with a hold sized precisely to "
            "the things nobody declares. The Concordat denies building it and "
            "the serial numbers disagree."),
    Chassis("pike", "PIKE", "fabricated", "Corvette", "Patrol corvette",
            720, 2600, slots(1, 2, 1, 1, 2, 3, 1), 45, 14, 4.6, 1.30, 0.24,
            {"credits": 38000, "alloy": 55, "silicon": 12}, 20, "monocoque",
            "Three weapon hardpoints on a hull that costs less than the guns. "
            "The Concordat sells these to anyone and is periodically surprised "
            "by who buys them."),
    Chassis("kiln", "KILN", "fabricated", "Industrial", "Mobile refinery",
            980, 16000, slots(1, 2, 1, 1, 2, 1, 6), 520, 26, 3.6, 0.74, 0.07,
            {"credits": 49000, "alloy": 105, "silicon": 16}, 34, "monocoque",
            "A smelter with engines. It chews ore at the rock face and sells "
            "you back the tenth of it that was worth having, warm."),
    Chassis("caravel", "CARAVEL", "fabricated", "Liner", "Passenger liner",
            860, 9000, slots(2, 1, 1, 2, 2, 1, 5), 260, 90, 5.4, 1.12, 0.13,
            {"credits": 52000, "alloy": 78, "silicon": 20}, 28, "monocoque",
            "Ninety berths, actual windows, and passengers who are awake for the "
            "whole crossing and have opinions about the catering. The un-elegant "
            "answer to a stasis liner."),
    Chassis("drayhorse", "DRAYHORSE", "fabricated", "Freighter", "Container hauler",
            1050, 22000, slots(2, 1, 1, 1, 2, 1, 5), 1100, 18, 4.4, 0.88, 0.06,
            {"credits": 54000, "alloy": 140, "silicon": 14}, 30, "monocoque",
            "A spine, eight container locks and an engine. Out-carries a grown "
            "freighter and will do it again tomorrow, provided you pay someone "
            "to weld it."),
    Chassis("spindle", "SPINDLE", "fabricated", "Survey", "Deep-survey platform",
            940, 8000, slots(2, 2, 4, 3, 1, 1, 3), 180, 34, 6.8, 1.06, 0.16,
            {"credits": 61000, "alloy": 70, "silicon": 40}, 34, "aicore",
            "Four sensor mounts and almost nothing else, unfolded on a boom long "
            "enough that the ship stops mattering. It charts; it does not argue."),
    Chassis("meridian", "MERIDIAN", "fabricated", "Cruiser", "Survey cruiser",
            1300, 14000, slots(2, 2, 3, 3, 2, 2, 3), 200, 45, 7.0, 1.10, 0.15,
            {"credits": 72000, "alloy": 130, "silicon": 34}, 40, "aicore",
            "Instrumented to the rivets and jumps seven light-years without "
            "discussion. If you intend to chart rather than settle, this is the "
            "hull."),
    Chassis("longshot", "LONGSHOT", "fabricated", "Destroyer",
            "Stand-off missile destroyer",
            1500, 19000, slots(2, 2, 2, 2, 2, 4, 2), 150, 60, 5.2, 1.05, 0.14,
            {"credits": 96000, "alloy": 190, "silicon": 40}, 55, "missiles",
            "Built around its magazines. It intends to finish the argument at "
            "range four and has very little to say if you get to range zero."),
    Chassis("portcullis", "PORTCULLIS", "fabricated", "Monitor",
            "System-defence monitor",
            2900, 62000, slots(1, 3, 2, 2, 5, 4, 2), 120, 90, 2.4, 0.55, 0.04,
            {"credits": 118000, "alloy": 330, "silicon": 44}, 70, "railgun",
            "Armour and batteries bolted to an engine that can barely move them. "
            "It is not a ship so much as a fort that arrived under its own power "
            "and never intends to leave."),
    Chassis("hammerfall", "HAMMERFALL", "fabricated", "Siege",
            "Siege artillery platform",
            2400, 74000, slots(2, 3, 2, 2, 3, 5, 2), 200, 110, 4.2, 0.66, 0.05,
            {"credits": 164000, "alloy": 400, "silicon": 70}, 92, "fusionlance",
            "Five mounts, all of them long, and a magazine that costs more than "
            "the hull. It exists to open things that were built not to open."),
    Chassis("bastion", "BASTION", "fabricated", "Battleship", "Line battleship",
            3400, 90000, slots(2, 3, 2, 2, 4, 5, 2), 180, 140, 4.0, 0.72, 0.05,
            {"credits": 210000, "alloy": 520, "silicon": 90}, 110, "fusionlance",
            "The heaviest thing the Yards will sell a private captain. Five "
            "hardpoints, armour measured in decimetres, and not one gram of it "
            "will ever grow back."),
]

# ── HYBRID · Freehold grafts ───────────────────────────────────────────────
HYBRID: list[Chassis] = [
    Chassis("graft", "GRAFT", "hybrid", "Skiff", "Salvage skiff",
            560, 1400, slots(1, 1, 2, 1, 2, 2, 2), 80, 8, 4.8, 1.25, 0.28,
            {"credits": 21000, "alloy": 22, "biomass": 18, "ore": 20}, 45, "oect",
            "Freehold work: a cut-down Yards frame with tissue grown through it. "
            "It heals slowly, flies well, and no two are quite the same ship."),
    Chassis("midden", "MIDDEN", "hybrid", "Breaker", "Ship-breaker / salvager",
            1150, 15000, slots(1, 2, 2, 1, 3, 2, 6), 620, 22, 4.0, 0.80, 0.11,
            {"credits": 44000, "alloy": 60, "biomass": 45, "ore": 90}, 90, "oect",
            "Cutting heads, a gut that digests what the heads bring in, and a "
            "hold full of other people's hulls. The Freeholds' quiet argument "
            "that nothing is ever really finished."),
    Chassis("palimpsest", "PALIMPSEST", "hybrid", "Cutter",
            "Independent trader-fighter",
            1180, 11000, slots(2, 2, 2, 2, 3, 3, 4), 380, 30, 5.6, 1.08, 0.18,
            {"credits": 66000, "alloy": 90, "biomass": 55, "ore": 110,
             "silicon": 18}, 120, "mea",
            "Written over so many times the original hull is a rumour. Carries "
            "cargo, carries guns, and repairs the parts of itself that happen "
            "to be alive."),
    Chassis("threshold", "THRESHOLD", "hybrid", "Dreadnought", "Hybrid capital ship",
            4200, 140000, slots(3, 3, 3, 3, 5, 5, 4), 500, 180, 6.2, 0.86, 0.09,
            {"credits": 260000, "alloy": 420, "biomass": 260, "ore": 600,
             "phosphate": 130, "silicon": 110}, 330, "neuromorphic",
            "The synthesis nobody's charter quite permits: a fabricated keel, a "
            "grown carapace over it, and a neuromorphic core wired into living "
            "tissue. It fights like a Yards capital and mends like a hull."),
]

# ── SYNTHETIC · the Dry Choir ──────────────────────────────────────────────
SYNTHETIC: list[Chassis] = [
    Chassis("cantor", "CANTOR", "synthetic", "Probe", "Autonomous picket",
            340, 400, slots(1, 1, 3, 3, 1, 1, 1), 20, 2, 7.2, 1.60, 0.36,
            {"credits": 31000, "silicon": 26, "alloy": 14}, 18, "synthmind",
            "Two hundred kilos of instrument and a mind that does not get bored "
            "watching an empty orbit for a decade. It carries two acceleration "
            "couches nobody has ever sat in."),
    Chassis("lattice", "LATTICE", "synthetic", "Carrier", "Drone carrier",
            1450, 12000, slots(2, 3, 2, 3, 3, 4, 4), 260, 6, 5.4, 0.94, 0.12,
            {"credits": 96000, "silicon": 74, "alloy": 120}, 62, "dronework",
            "A rack, a reactor and eleven hundred small things that undock in "
            "formation. It never closes to contact range because it has never "
            "needed to be anywhere in particular."),
    Chassis("ordinal", "ORDINAL", "synthetic", "Cruiser", "Line cruiser",
            1700, 21000, slots(2, 3, 3, 4, 3, 3, 2), 140, 4, 6.6, 1.16, 0.20,
            {"credits": 124000, "silicon": 96, "alloy": 150}, 74, "synthmind",
            "Fast, precise, and entirely uninhabited but for a coolant loop and "
            "an argument that has been running since before the Bloom. The Dry "
            "Choir will sell you one and will not explain the price."),
    Chassis("theorem", "THEOREM", "synthetic", "Capital", "Analysis capital",
            3900, 96000, slots(3, 4, 4, 5, 4, 4, 3), 320, 8, 7.4, 0.90, 0.10,
            {"credits": 290000, "silicon": 240, "alloy": 380, "magnetite": 40},
            180, "neuromorphic",
            "Five compute mounts and four sensor mounts on a hull that thinks "
            "faster than its own weapons can be aimed. Whatever it is actually "
            "for, gunnery is a side effect."),
]

# ── XENO · not ours ────────────────────────────────────────────────────────
XENO: list[Chassis] = [
    Chassis("revenant", "REVENANT", "xeno", "Derelict", "Reactivated derelict",
            1600, 17000, slots(2, 2, 3, 2, 3, 2, 3), 240, 18, 6.0, 1.02, 0.22,
            {"credits": 88000, "xenolith": 2, "silicon": 40, "alloy": 90},
            140, "xenoalloy",
            "Found cold, opened carefully, and persuaded to start again. The "
            "spar layers knit overnight and nobody aboard can say what the "
            "lining is exhaling, only that it is breathable.",
            "incognitum"),
    Chassis("antiphon", "ANTIPHON", "xeno", "Capital", "Xeno-derived capital",
            4600, 160000, slots(3, 3, 4, 3, 5, 4, 4), 480, 40, 8.2, 0.94, 0.14,
            {"credits": 340000, "xenolith": 8, "silicon": 150, "magnetite": 60,
             "phosphate": 120}, 300, "firstcontact",
            "Grown to a plan the Abyssals supplied and nobody has fully read. It "
            "out-jumps a LEVIATHAN, mends like a hull, and rings — audibly, "
            "through the deck — when something large moves nearby.",
            "responsum"),
]

BUILT: list[Chassis] = [*FABRICATED, *HYBRID, *SYNTHETIC, *XENO]
