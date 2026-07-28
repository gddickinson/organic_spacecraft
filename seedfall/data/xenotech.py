"""Alien technology.

Four cultures left things behind in the Verge, and none of them left an
instruction manual. Their technologies are not researched — they are *found*,
dug out of a world, bought as somebody else's field notes, or taken off a hull
that had them first. Each is understood gradually, on a scale of study points,
and only becomes yours when the understanding is complete.

An incorporated technology is appended to ``research.unlocked`` so the shipyard
and the codex treat it like anything else you know. It is never offered by the
research tree, because you cannot reason your way to it from first principles.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Culture:
    id: str
    name: str
    tint: str
    sites: tuple[str, ...]      # body kinds their remains turn up on
    blurb: str


CULTURES: list[Culture] = [
    Culture(
        "abyssal", "The Abyssals", "lumen", ("ice", "ocean", "moon"),
        "Still living, twenty kilometres down, in water at a hundred and fifty "
        "megapascals. They do not build in metal and they do not appear to have "
        "a word for vacuum. Everything of theirs that we have recovered was "
        "grown, and most of it is still faintly warm."),
    Culture(
        "ossuary", "The Ossuary", "osteo", ("rocky", "moon", "asteroid"),
        "A lineage that ended a very long time ago and spent its last several "
        "centuries preparing to be found. Their vaults are buried deep, "
        "meticulously labelled in a notation nobody has cracked, and in better "
        "condition than anything we have built."),
    Culture(
        "weft", "The Weft", "xeno", ("rocky", "asteroid", "comet", "gas"),
        "Whoever they were, they worked matter at nanometre pitch and left "
        "behind fabric that scatters light in ways the optics people describe "
        "as rude. No bodies, no vaults, no writing — only the cloth."),
    Culture(
        "tessellate", "The Tessellate", "steel", ("asteroid", "rocky", "ice", "gas"),
        "Crystalline, geometric, and evidently fond of standing waves. Their "
        "remains ring when struck and go on ringing for longer than the energy "
        "you put in should allow. This has been measured repeatedly and remains "
        "unexplained."),
]

CULTURES_BY_ID: dict[str, Culture] = {c.id: c for c in CULTURES}


@dataclass(frozen=True)
class XenoTech:
    id: str
    name: str
    culture: str
    study: int                          # points of understanding needed
    blurb: str
    grants: str = ""                    # human-readable summary of the payoff
    bonus: dict = field(default_factory=dict)
    requires: tuple[str, ...] = ()      # other xenotech that must come first


def _x(tid, name, culture, study, blurb, grants="", requires=(), **bonus):
    return XenoTech(tid, name, culture, study, blurb, grants, bonus, tuple(requires))


XENOTECH: list[XenoTech] = [
    # ── ABYSSAL ─────────────────────────────────────────────────────────────
    _x("vent_symbiosis", "Vent Symbiosis", "abyssal", 120,
       "A partnership between something that eats sulfide and something that "
       "eats the first thing's waste, run at four degrees and held stable for, "
       "on the isotope evidence, rather longer than our species has existed.",
       "Fits the Abyssal Vent Bloom power organ."),
    _x("pressure_song", "Pressure Song", "abyssal", 180,
       "They speak in pressure waves, and the grammar is not linear. Two years "
       "of recordings have yielded eleven confirmed phonemes and one very "
       "uncomfortable suspicion about what the eleventh means.",
       "Fits the Pressure Chorus array; improves standing with everyone.",
       diplomacy=0.10, scan=0.06),
    _x("living_pressure", "Living Pressure", "abyssal", 260,
       "Tissue folded to hold at abyssal pressure with no gas voids anywhere in "
       "it — the trick our own divers approximate with piezolytes, done properly "
       "and apparently without effort.",
       "Fits the Abyssal Weave hull lining.",
       requires=("vent_symbiosis",), hull=0.08, regen=0.10),

    # ── OSSUARY ─────────────────────────────────────────────────────────────
    _x("deeptime_glass", "Deep-Time Glass", "ossuary", 140,
       "A storage medium that has held its contents legibly through an interval "
       "we can only bound from below. Whatever they were preserving, they "
       "expected the reader to be late.",
       "Fits the Ossuary Archive; steadier research.",
       research=0.14),
    _x("ossified_frame", "Ossified Frame", "ossuary", 200,
       "Structural members laid down in the manner of bone and then, at the "
       "end, deliberately mineralised solid. Nothing in the vaults was built to "
       "move again.",
       "Fits Ossified Bracing; every hull you lay down is tougher.",
       hull=0.10),
    _x("wake_protocol", "Wake Protocol", "ossuary", 300,
       "The vaults are not tombs. Every one of them contains a mechanism whose "
       "evident purpose is to bring something back, and every one of them is "
       "still, patiently, armed.",
       "Fits the Wake Cradle; the crew survives what should kill them.",
       requires=("deeptime_glass",), growth=0.08),

    # ── WEFT ────────────────────────────────────────────────────────────────
    _x("diffraction_weave", "Diffraction Weave", "weft", 150,
       "Cloth woven at a pitch below the wavelength it is scattering. Light "
       "arrives, and then does not leave in any direction you predicted.",
       "Fits the Diffraction Shroud; harder to hit.",
       ),
    _x("null_seam", "Null Seam", "weft", 210,
       "Where two panels of the weave meet there is a seam that returns nothing "
       "at all to any instrument we own. The seam is four molecules across.",
       "Fits the Null Seam Cowl; you are much harder to find.",
       requires=("diffraction_weave",), scan=0.10),
    _x("phase_loom", "Phase Loom", "weft", 320,
       "The loom is still running. It has been weaving the same eleven metres "
       "of fabric for as long as the site has been monitored, and the fabric "
       "does not accumulate.",
       "Fits the Phase Loom Lance — it goes through armour as though asked.",
       requires=("null_seam",)),

    # ── TESSELLATE ──────────────────────────────────────────────────────────
    _x("resonant_spar", "Resonant Spar", "tessellate", 130,
       "A structural member that rings on impact and sheds the energy into the "
       "ringing instead of into itself. It is not stronger than steel. It "
       "simply declines to break.",
       "Fits Resonant Bracing; armour that answers back.",
       hull=0.06),
    _x("lattice_echo", "Lattice Echo", "tessellate", 190,
       "Strike one face of a Tessellate lattice and the far side answers "
       "before, by our clocks, it should have heard. The discrepancy is small, "
       "consistent, and has ended two careers.",
       "Fits the Lattice Echo array; sees a very long way.",
       scan=0.12, research=0.08),
    _x("standing_wave", "Standing Wave", "tessellate", 340,
       "A wave held in solid matter that does not decay. Feed it, and the "
       "matter on the far side of the node stops holding together in a manner "
       "the Charter has asked us to stop demonstrating.",
       "Fits the Standing Wave Projector.",
       requires=("resonant_spar", "lattice_echo")),
]

XENOTECH_BY_ID: dict[str, XenoTech] = {x.id: x for x in XENOTECH}


def by_culture(culture_id: str) -> list[XenoTech]:
    return [x for x in XENOTECH if x.culture == culture_id]


def site_kinds(culture_id: str) -> tuple[str, ...]:
    c = CULTURES_BY_ID.get(culture_id)
    return c.sites if c else ()


#: What a dig at a fresh site is worth, before survey quality and lab bonuses.
DIG_YIELD = (28, 46)

#: Study points a single relic yields when taken apart in a laboratory.
XENOLITH_STUDY = 22
