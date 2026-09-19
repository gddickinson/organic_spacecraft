"""What a grown hull becomes from what it has been through.

A hull that was *grown* changed after launch only by refit, exactly like a
welded one — while the GESTALT dossier describes tissue that answers load:
bone laid down where strain is chronic (Wolff's law), a melanised rind, scute
turnover paced to the flux the skin reports, a mining root that eats rock.
This is the table of those answers. `sim/adaptation.py` holds the rules.

Every adaptation is a **trade**, not a prize. It has a channel and a
threshold (what the body has to have been through), a gain and a cost — both
written as the `Stats` fields the ship pipeline already reads — and the
families it can occur in. Fabricated and synthetic hulls appear in none:
metal does not remember, and that is a trait of the family, not a gap.

An effect is `pct` (a fraction of the computed stat) or `plus` (added to
it), and `sim/adaptation.apply` is the one place either is done. Magnitudes
are held under a tier-2 fitting on the stat they move — `test_adaptation`
measures that against the parts table rather than trusting this comment.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    stat: str          # a `sim/ship.Stats` field
    amount: float
    pct: bool          # True: a fraction of the computed stat; False: added


def pct(stat: str, amount: float) -> Effect:
    return Effect(stat, amount, True)


def plus(stat: str, amount: float) -> Effect:
    return Effect(stat, amount, False)


#: Channel id → (name, unit, what records it).
CHANNELS: dict[str, tuple[str, str, str]] = {
    "impact": ("Impact", "hp", "damage the layers absorbed under fire"),
    "heat": ("Heat", "heat-days", "running over the cap, and cooking"),
    "crossing": ("Crossing", "ly", "light-years jumped"),
    "dark": ("Dark", "days", "days at a dim star"),
    "glare": ("Glare", "days", "days at a blue-white star"),
    "gut": ("Gut", "t", "tonnes mined or extracted"),
    "eyes": ("Eyes", "looks", "surveys that saw something new"),
    "depth": ("Depth", "dives", "ocean dives"),
    "burn": ("Burn", "burns", "hard-burn crossings"),
}

#: A star this dim or dimmer is dark to the body; this bright or brighter,
#: glare. Read from `System.heat`: white dwarfs (0.18), neutron stars (0.10)
#: and black holes (0.05) are dark; A-types (1.00) are glare.
DARK_BELOW = 0.25
GLARE_FROM = 0.9

ADAPTIVE = ("grown", "hybrid", "xeno")
TISSUE = ("grown", "hybrid")     # the layers GESTALT describes: rind, osteoid

#: How fast each family's body answers load. A family missing here never
#: adapts. Hybrids are half tissue; xeno bodies answer faster and stranger.
RATE = {"grown": 1.0, "hybrid": 0.5, "xeno": 1.5}

#: Adaptations a hull can carry, by the hit points its chassis is rated at —
#: the size of the body there is to grow things in. SPORE (240) 1, NAVIS
#: (1,400) 3, TESTUDO and TARDIGRADE 4, LEVIATHAN (9,000) 5.
BUDGET_STEPS = ((300, 1), (1000, 2), (2000, 3), (5000, 4))
BUDGET_MAX = 5
#: Hybrids keep one fewer, and never fewer than one.
HYBRID_BUDGET_LESS = 1

#: Ship days an emergence waits for an answer before setting in by itself.
AUTO_SET_DAYS = 60
#: Ship days an encouraged emergence takes to set in.
ENCOURAGE_DAYS = 20
#: What encouraging costs a NAVIS-sized body (1,400 hull), in growth
#: material. Scaled by chassis hull; about 2,150 credits of matter at base
#: prices, against the 6,000 to 15,000 a tier-2 fitting costs to buy.
ENCOURAGE_COST = {"phosphate": 4.0, "biomass": 12.0}
#: Where suppressing or pruning leaves the channel, as a multiple of the
#: threshold that fired: a full threshold *below* nothing, so the body has
#: to be taught it twice over before it offers it again. Measured on twelve
#: five-year careers answering every emergence with "suppress": left at 0.4
#: of the threshold the same thing came back 7 to 29 times a career (an
#: explorer's eyes refill in eight surveys); at 0, 4 to 16; at -0.5, 2 to
#: 12; here, 2 to 9.
DRAW_DOWN = -1.0
#: A channel stops filling at this multiple of its highest threshold. The
#: bar has somewhere to stop, and a prune does not release a year's backlog.
STRESS_CAP = 1.25
#: A surgeon at a Fleet Hub, per NAVIS-sized body, and the days it takes.
PRUNE_CREDITS = 3000
PRUNE_DAYS = 8
#: The body a NAVIS is, which the costs above are written for.
REFERENCE_HULL = 1400


@dataclass(frozen=True)
class Adaptation:
    id: str
    name: str
    channel: str
    threshold: float
    #: What it gives and what it takes, as `Effect`s. Not `gain`: that
    #: name is the courtship curve's, and `test_courtship` holds it to one door.
    gives: tuple
    takes: tuple
    text: str
    families: tuple = ADAPTIVE
    #: Radiation dose the crew takes, as a multiple. Read by nothing in the
    #: game yet — the Cradle's dose arrives with another innovation — and
    #: exposed now through `adaptation.dose_multiplier`.
    dose: float = 1.0


ADAPTATIONS: list[Adaptation] = [
    Adaptation(
        "callused_rind", "Callused rind", "impact", 240,
        (plus("armour", 1.0),), (pct("speed", -0.03),),
        "The epidermis is scute cells that thicken their walls and die on "
        "purpose, and their turnover is paced to the flux the baroreceptors "
        "report. Hit often enough, the body reads the flux as chronic: the "
        "dead horn goes on deeper and stays. It soaks a point off every hit, "
        "and she carries it everywhere.", TISSUE),
    Adaptation(
        "scar_lattice", "Scar lattice", "impact", 600,
        (pct("regen", 0.15),), (plus("evade", -0.02),),
        "Repair is the growth programme aimed at a hole: a clot seals it, a "
        "blastema of reactivated stem cells re-forms, and the tissue regrows "
        "layer by layer and remodels the scar. A hull opened often keeps "
        "caches of repair cells primed under the skin, so regrowth does not "
        "wait on the vasculature. Scar is stiffer than what it replaced, and "
        "she answers the helm a beat late."),
    Adaptation(
        "radiator_fronds", "Radiator fronds", "heat", 250,
        (pct("vent", 0.20),), (plus("conceal", -0.10),),
        "The radiator bloom dumps waste heat through high-surface tissue, "
        "opening and closing to hold temperature. Cooked often, it does what "
        "any tissue under chronic load does and grows more of itself: fronds "
        "of vascular sheet along the aft organ. They shed heat well, and they "
        "shed it where anybody with an infrared eye can see — they glow."),
    Adaptation(
        "heat_shock_chaperones", "Heat-shock chaperones", "heat", 900,
        (pct("heat_cap", 0.15),), (pct("regen", -0.05),),
        "Every living layer is protein, and heat unfolds protein. Tissue "
        "that is cooked and survives keeps its chaperones raised — the "
        "proteins that catch others as they unfold and fold them back — and "
        "fails later the next time. It is margin, not immunity: living "
        "tissue tops out near 122 °C, which is why SOL-FORGE hides behind "
        "its radiators. The protein spent on it is not spent on regrowth."),
    Adaptation(
        "long_haul_metabolism", "Long-haul metabolism", "crossing", 130,
        (plus("jump", 0.4),), (plus("morale", -0.10),),
        "The storage parenchyma banks sugar, lipid and starch against an "
        "outage. On long hauls the body learns to live on it between stars, "
        "turning the hotel metabolism down and handing the reaction organ "
        "more of the budget. The reach grows. The cabins run colder and "
        "dimmer, and the crew notices."),
    Adaptation(
        "torpor_reflex", "Torpor reflex", "crossing", 480,
        (pct("o2_days", 0.25),), (pct("speed", -0.02),),
        "SPORE's trick is torpor — dropping the occupant into hibernation "
        "stretches days of air into months. A body that has crossed far "
        "enough grows the reflex into its own tissue: when the air plant "
        "falters, everything that breathes slows down. She lasts longer on "
        "a tank, and she is slow to come back up to speed."),
    Adaptation(
        "melanised_rind", "Melanised rind", "dark", 40,
        (pct("o2_days", 0.30),), (pct("vent", -0.10),),
        "The rind is melanocytes packed with eumelanin, absorbing ionising "
        "radiation and heat and perhaps harvesting a little of that energy "
        "— radiotrophic, as Cladosporium was aboard the ISS. Starved of "
        "starlight the body leans on it: the rind darkens and thickens, the "
        "sugar it makes eases the air plant, and the crew takes a fifth less "
        "dose. A darker skin also holds its heat.", TISSUE, dose=0.8),
    Adaptation(
        "night_adapted_eyes", "Night-adapted eyes", "dark", 120,
        (pct("sensor", 0.12),), (plus("scan", -0.03),),
        "The opsin eyes are retinas behind grown crystallin lenses. Kept "
        "long enough in the dark, the retina does what every night eye "
        "does: it pools its photoreceptors, many to a channel, so a faint "
        "source registers at all. The array reaches further. What it sees, "
        "it sees in less detail."),
    Adaptation(
        "glare_mantle", "Glare mantle", "glare", 60,
        (plus("crew_guard", 0.05),), (pct("sensor", -0.08),),
        "The sunward cap admits starlight through clarified panels that "
        "filter ultraviolet onto the intima. Under a blue-white star it "
        "cannot close far enough, so the body grows a mantle over the cap "
        "and the decks beneath: more filter, more melanin between the light "
        "and the people. The crew takes a quarter less of the sky, and a "
        "breach finds them better covered. So are the eyes.", dose=0.75),
    Adaptation(
        "sun_fed_intima", "Sun-fed intima", "glare", 150,
        (pct("regen", 0.10),), (pct("heat_cap", -0.05),),
        "Only one class of cell brings new energy into the body: the "
        "phototrophs of the intima. Fed hard light long enough, the "
        "light-guide bundles multiply and the canopy thickens, and there is "
        "more sugar for every structural cell living on it — regrowth runs "
        "faster. The windows that let the light in let its heat in too.",
        TISSUE),
    Adaptation(
        "mineral_gut", "Mineral gut hypertrophy", "gut", 250,
        (pct("mine", 0.15), pct("phos", 0.10)), (pct("cargo", -0.03),),
        "The mining root is chemolithotrophs — Acidithiobacillus-type — "
        "oxidising iron and sulfur and leaching metal from rock, run as a "
        "tissue. Work it and it grows, as a gut fed well grows: more root "
        "at the rock face, more concentrator behind it. The body is grown "
        "by eating the rock, and the gut takes its room out of the hold.",
        TISSUE),
    Adaptation(
        "concentrator_root", "Concentrator root", "gut", 900,
        (pct("phos", 0.30),), (pct("mine", -0.05),),
        "Phosphorus sets the digging: the reference starship's bone holds "
        "some 440 t of it, from rock that is a tenth of a percent "
        "phosphorus, so a hull eats eighteen times its own mass in asteroid. "
        "A root that has eaten enough grows the accumulator cells that pull "
        "the scarce element out first — and pass more slowly over the rest.",
        TISSUE),
    Adaptation(
        "acute_opsins", "Acute opsins", "eyes", 14,
        (plus("scan", 0.05),), (pct("sensor", -0.05),),
        "The retinas are photoreceptor cells, and a body that keeps looking "
        "closely grows more of them to the degree of arc — the fovea's "
        "answer, one receptor to a channel. The survey resolves finer. Each "
        "receptor catches less light, and the far edge of the array goes "
        "dim."),
    Adaptation(
        "magnetite_antenna", "Magnetite antenna", "eyes", 40,
        (pct("sensor", 0.10),), (pct("speed", -0.02),),
        "VESPER's cells biomineralise magnetite into aligned chains — the "
        "trick magnetotactic bacteria perform for real — for magnetic "
        "sensing and a grown antenna. A hull that has spent years looking "
        "starts laying the chains down in its own dish. The array hears "
        "further, and the mineral is mass she carries."),
    Adaptation(
        "pressure_bone", "Pressure bone", "depth", 3,
        (plus("armour", 1.0), plus("crew_guard", 0.04)),
        (pct("speed", -0.03),),
        "Deep-sea fauna carry piezolytes — TMAO rises with depth in real "
        "fish — so protein holds its shape under a pressure that should "
        "crush it, and NEREUS is built with no gas voids anywhere. Dived "
        "often, the osteoid lays bone along the load paths the ocean found, "
        "Wolff's law in a crushing sea. The hull is harder, the dive safer, "
        "and the bone is weight.", TISSUE),
    Adaptation(
        "motile_trim", "Motile trim", "burn", 5,
        (pct("speed", 0.05),), (pct("heat_cap", -0.05),),
        "Contractile cells wrap every channel and valve, the body's pump "
        "and its flow regulator. Stand the drive up often enough and the "
        "ring muscles along the drive trunk thicken to take the load: she "
        "trims faster under thrust. Muscle is heat, and more of it leaves "
        "less room under the cap."),
]

ADAPTATIONS_BY_ID = {a.id: a for a in ADAPTATIONS}
