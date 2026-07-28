"""Parts you can only fit once you understand the technology behind them.

Each of these is gated on a :mod:`xenotech` entry rather than a research-tree
node, so none of them can be reasoned out — they have to be dug up, bought or
taken. Most are family ``any``: the whole point of incorporating alien work is
bolting it to the hull you already fly.
"""

from __future__ import annotations

from .part_types import Ability, Part, Weapon

XENOPARTS: list[Part] = [
    # ── ABYSSAL ─────────────────────────────────────────────────────────────
    Part("vent_bloom", "Abyssal Vent Bloom", "power", "any", "vent_symbiosis",
         55, {"credits": 24000, "xenolith": 1, "biomass": 20},
         {"power": 22, "o2": 40, "vent": 6},
         "A sulfide-eating partnership in a warm pocket amidships, running the "
         "chemistry it has run for longer than our species has existed. It asks "
         "for nothing and it does not stop."),
    Part("pressure_chorus", "Pressure Chorus", "sensor", "any", "pressure_song",
         30, {"credits": 29000, "xenolith": 1, "magnetite": 8},
         {"sensor": 3.4, "scan": 0.24, "accuracy": 0.06},
         "Listens in pressure waves rather than photons, which turns out to work "
         "through rock, ice and hull plate. It also occasionally answers, and "
         "nobody aboard authorised that."),
    Part("abyssal_weave", "Abyssal Weave", "defence", "any", "living_pressure",
         60, {"credits": 41000, "xenolith": 2, "biomass": 30},
         {"armour": 8, "regen": 0.26, "hullMul": 0.10, "crewGuard": 0.20},
         "Tissue folded to hold at abyssal pressure with no gas voids anywhere "
         "in it. Grafted over your own hull it closes wounds faster than any "
         "blastema the Charter ever engineered."),

    # ── OSSUARY ─────────────────────────────────────────────────────────────
    Part("ossuary_archive", "Ossuary Archive", "compute", "any", "deeptime_glass",
         34, {"credits": 33000, "xenolith": 1, "silicon": 10},
         {"research": 1.6, "scan": 0.10, "morale": 0.2},
         "A slab of deep-time glass and a reader we built by guessing. It holds "
         "everything you put in it, legibly, for longer than you will need — "
         "which was rather the point when they made it."),
    Part("ossified_bracing", "Ossified Bracing", "defence", "any", "ossified_frame",
         95, {"credits": 36000, "xenolith": 2, "ore": 60},
         {"armour": 11, "hullMul": 0.18, "evade": -0.05},
         "Structural members laid down like bone and then deliberately "
         "mineralised solid. Nothing braced this way was ever meant to move "
         "again, and it shows in the handling."),
    Part("wake_cradle", "Wake Cradle", "utility", "any", "wake_protocol",
         50, {"credits": 47000, "xenolith": 2, "trehalose": 12},
         {"o2": 180, "crewGuard": 0.35, "morale": 0.3, "berths": 20},
         "The mechanism every Ossuary vault contains, whose evident purpose is "
         "to bring something back. Fitted to a crew compartment it is "
         "extraordinarily good at not letting people die."),

    # ── WEFT ────────────────────────────────────────────────────────────────
    Part("diffraction_shroud", "Diffraction Shroud", "defence", "any",
         "diffraction_weave",
         38, {"credits": 31000, "xenolith": 1, "spidroin": 10},
         {"evade": 0.18, "armour": 2},
         "Cloth woven below the wavelength it scatters. Gunnery officers report "
         "that the hull is visibly there and that their solutions keep arriving "
         "somewhere it is not."),
    Part("null_cowl", "Null Seam Cowl", "sensor", "any", "null_seam",
         28, {"credits": 38000, "xenolith": 2, "silicon": 12},
         {"sensor": 2.0, "scan": 0.16, "evade": 0.10},
         "Panels of weave joined along a seam four molecules across that returns "
         "nothing at all to any instrument we own. What it does to yours is a "
         "separate and happier question."),
    Part("phase_lance", "Phase Loom Lance", "weapon", "any", "phase_loom",
         80, {"credits": 58000, "xenolith": 3, "silicon": 24}, {"draw": 16},
         "A working length of the loom, pointed. Armour on the far side does not "
         "resist so much as decline to have been continuous.",
         wpn=Weapon(38, (1, 4), 8, 0.14, None, ("pierce",))),

    # ── TESSELLATE ──────────────────────────────────────────────────────────
    Part("resonant_bracing", "Resonant Bracing", "defence", "any", "resonant_spar",
         70, {"credits": 27000, "xenolith": 1, "ore": 40},
         {"armour": 7, "hullMul": 0.12, "vent": 4},
         "Members that ring on impact and shed the energy into the ringing "
         "instead of into themselves. Not stronger than steel; simply less "
         "willing to break."),
    Part("lattice_array", "Lattice Echo Array", "sensor", "any", "lattice_echo",
         42, {"credits": 44000, "xenolith": 2, "magnetite": 14},
         {"sensor": 5.2, "scan": 0.30, "research": 0.6, "draw": 6},
         "Strike one face and the far side answers before, by our clocks, it "
         "should have heard. Used as a telescope this is worth two careers and "
         "has cost exactly that."),
    Part("standing_projector", "Standing Wave Projector", "weapon", "any",
         "standing_wave",
         110, {"credits": 76000, "xenolith": 4, "magnetite": 20, "silicon": 30},
         {"draw": 24, "heatCap": 10},
         "Feed the wave and the matter beyond the node stops holding together. "
         "The Charter has asked, in writing, that we stop demonstrating this.",
         wpn=Weapon(52, (2, 4), 18, 0.08, None, ("pierce", "emp"))),
]
