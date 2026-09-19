"""The Kith: a living people of the Cradle, and the words they sing in light.

The Verge's aliens were the dead (four cultures known by their relics) and
the unreachable (the Abyssals, under the ice). The Kith are the first other
anybody can *talk to*: a communal, spacefaring people whose hulls are colonies
of many bodies, who speak in modulated light, and who trade by reciprocity
rather than by price. The rules live in `sim/kith.py`; their gatherings are
laid into the Cradle by `sim/kith_world.py`.

Pure data: the 24 signs and their glyphs, the phrases the bench works on,
what each gathering thinks of each good (a prior the gatherings are drawn
from), the reactions and what they are worth, the three grafts, and the
thresholds every Kith act is gated on.
"""

from __future__ import annotations

from dataclasses import dataclass

from .adaptations import pct, plus
from .hull_types import Chassis, slots
from .part_types import Part

FACTION = "kith"
CRADLE = "cradle"

# ── the lexicon ────────────────────────────────────────────────────────────

#: The four domains, in the order the panel draws them.
DOMAINS: dict[str, str] = {
    "kin": "Kin", "place": "Place", "exchange": "Exchange", "intent": "Intent",
}


@dataclass(frozen=True)
class Sign:
    id: str
    domain: str
    #: What the sign is drawn as. A Kith sign has no sound, so it has no
    #: name in their language: the screen draws the picture.
    glyph: str
    gloss: str


SIGNS: list[Sign] = [
    Sign("self", "kin", "◉", "we, this colony"),
    Sign("other", "kin", "◎", "you, a body not of us"),
    Sign("many", "kin", "⊛", "a colony: many bodies, one will"),
    Sign("young", "kin", "◦", "a bud not yet joined"),
    Sign("old", "kin", "◍", "a body that has sung for a long time"),
    Sign("loss", "kin", "◐", "a body gone quiet"),
    Sign("here", "place", "▣", "this star"),
    Sign("there", "place", "▢", "another star"),
    Sign("far", "place", "▭", "past where the light is felt"),
    Sign("light", "place", "◇", "a star's song; food"),
    Sign("dark", "place", "▪", "cold, and the stone"),
    Sign("gate", "place", "◫", "the old ring, and what it lets through"),
    Sign("give", "exchange", "↦", "to hand over"),
    Sign("take", "exchange", "↤", "to receive"),
    Sign("enough", "exchange", "⇥", "the exchange is even"),
    Sign("more", "exchange", "⇈", "the exchange is not yet even"),
    Sign("gift", "exchange", "⇡", "a thing given that asks to be answered"),
    Sign("debt", "exchange", "⇄", "an answer not yet given"),
    Sign("peace", "intent", "▽", "we mean no hurt"),
    Sign("danger", "intent", "▲", "hurt is near"),
    Sign("question", "intent", "◬", "we ask"),
    Sign("yes", "intent", "⊕", "it is so"),
    Sign("no", "intent", "⊖", "it is not so"),
    Sign("wait", "intent", "⋯", "not yet"),
]
SIGNS_BY_ID = {s.id: s for s in SIGNS}


@dataclass(frozen=True)
class Phrase:
    id: str
    gloss: str
    signs: tuple


#: What the bench works on: a recording of one phrase. Every sign appears in
#: at least one phrase, so decoding alone can reach every word.
PHRASES: list[Phrase] = [
    Phrase("greeting", "We are here, and at peace with you.",
           ("self", "other", "peace", "here")),
    Phrase("kinship", "We are many: the young and the old are one body.",
           ("many", "young", "old", "self")),
    Phrase("mourning", "Many old ones went quiet in the dark.",
           ("loss", "old", "dark", "many")),
    Phrase("stars", "The light here, the light there, the far light.",
           ("light", "far", "there", "here")),
    Phrase("gate", "The ring is far and it is dangerous — do you ask it?",
           ("gate", "far", "danger", "question")),
    Phrase("offer", "Do you give a gift?",
           ("give", "gift", "other", "question")),
    Phrase("enough", "Taken. Yes, it is even. Wait.",
           ("enough", "take", "yes", "wait")),
    Phrase("more", "Yes — give more of that gift.",
           ("more", "gift", "give", "yes")),
    Phrase("debt", "The answer is owed. Do not take. Wait.",
           ("debt", "take", "no", "wait")),
    Phrase("stone", "The dark stone is danger. We do not take it.",
           ("danger", "dark", "no", "take")),
    Phrase("welcome", "Yes: peace here, as to our young.",
           ("peace", "yes", "here", "young")),
    Phrase("passage", "Do you ask the way through the ring, in peace?",
           ("gate", "there", "question", "peace")),
]
PHRASES_BY_ID = {p.id: p for p in PHRASES}

#: The bench's tech tag for a Kith recording: `"kith:" + phrase id`. The
#: decoding bench (`sim/minigames`) carries it in `game.decoding_tech`.
BENCH_TAG = "kith:"


# ── learning ───────────────────────────────────────────────────────────────

#: Comprehension a day of listening adds, as a share of what is left below
#: `LISTEN_CAP`, before the officer and the array. Measured on a NAVIS just
#: through the relight (science 3-4, sensor 3.8-4.0), three seeds: thirty
#: days attending takes Kin and Place to 0.31-0.36 and Exchange to 0.17-0.20
#: — a start, not a language. Listening alone reaches the trade gate in
#: 118-129 days; with every recording worked on the bench, 51-59.
LISTEN_RATE = 0.012
#: What each domain gets of a day's listening. They sing of kin and of stars;
#: the words for bargaining are rarer in a song nobody is bargaining in.
LISTEN_WEIGHT = {"kin": 1.0, "place": 1.0, "intent": 0.6, "exchange": 0.45}
#: Eavesdropping stops here: nobody learns to talk by overhearing. Past it
#: takes the bench and the exchanges — and the accord asks 0.7.
LISTEN_CAP = 0.55
#: A day at a gathering you are not attending still teaches this share.
PASSIVE_SHARE = 0.25
#: Each level of the best science officer aboard adds this to the rate.
SCIENCE_WORTH = 0.25
#: An opening array's sensor reach. More sees more of the song, to a cap.
SENSOR_REF = 3.0
SENSOR_FLOOR, SENSOR_CAP = 0.5, 1.6
#: Days attending a gathering that make one recording worth decoding.
DAYS_PER_RECORDING = 4
#: What a solved recording teaches each sign in the phrase: the bench's
#: points over this, as a share of what is left below 1. A typical solve
#: (spare three attempts, 76 points) is 0.25 of the gap.
DECODE_SCALE = 300.0
#: What an exchange teaches each sign spoken in it, as a share of the gap.
EXCHANGE_TEACH = 0.08
#: What watching their star teaches the Place signs, per survey in the
#: Cradle that saw something (the Kith sing about their stars).
OBSERVE_TEACH = 0.04
OBSERVE_SIGNS = ("light", "dark", "far", "here", "there")


# ── what the lexicon opens ─────────────────────────────────────────────────

#: Offering a gift, or asking about one, needs the Exchange signs.
TRADE_NEEDS = 0.4
#: Asking for a berth or for passage needs Place *and* Intent.
PASSAGE_NEEDS = 0.5
#: A treaty needs every domain, and standing.
ACCORD_NEEDS = 0.7
#: "Trusted" in `data/factions.STANDINGS`.
ACCORD_STANDING = 40
#: A berth or a graft is asked of a people that at least tolerate you.
TOLERATED = 15

#: The odds of misreading an act: this times the square of what is not yet
#: understood, capped. At the trade gate (0.4) it is 29%; at the accord's
#: 0.7, 7%; fluent, nothing. A light-throat graft sings back: the odds fall
#: to `THROAT_MISREAD` of themselves, and it hears half as much again.
MISREAD_SCALE = 0.8
MISREAD_MAX = 0.6
THROAT_MISREAD = 0.6
THROAT_LISTEN = 1.5
#: Curious about grown ships, wary of welded ones: the odds, by the family of
#: the hull you arrive in. A family not named is read as it is.
WARINESS = {"grown": 0.85, "fabricated": 1.3, "synthetic": 1.3}
#: What a misreading costs, and the share of misread gifts, berths, passages
#: and treaties that the colony answers with its bells out.
MISREAD_STANDING = -4.0
FIGHT_SHARE = 0.3


# ── the gift economy ───────────────────────────────────────────────────────

#: How a gathering takes a gift, and what the gift is worth to it as a share
#: of the good's base price. Offence is worth nothing and costs standing.
REACTIONS = ("prized", "welcome", "plain", "offended")
WORTH = {"prized": 1.3, "welcome": 1.0, "plain": 0.5, "offended": 0.0}
REACTION_TINT = {"prized": "chloro", "welcome": "lumen", "plain": "dim",
                 "offended": "warn"}
#: The signs a reaction is spoken in — what the exchange teaches.
SPOKEN = {
    "prized": ("gift", "more", "yes", "peace"),
    "welcome": ("gift", "give", "yes"),
    "plain": ("give", "take", "enough"),
    "offended": ("no", "danger", "take"),
    "debt": ("debt", "give", "enough"),
    "ask": ("question", "more", "enough"),
}

#: What each gathering is drawn from: good → (weight, reaction) pairs. The
#: shape of Kith opinion — condensate is light made solid and prized; the
#: silicon core is "the stone", feared; biomass reads as bodies — and each
#: gathering draws its own view from its own seed. A good not listed is
#: taken plainly.
PRIORS: dict[str, tuple] = {
    "condensate": ((8, "prized"), (2, "welcome")),
    "silicon": ((85, "offended"), (15, "plain")),
    "biomass": ((7, "offended"), (3, "plain")),
    "volatiles": ((6, "welcome"), (4, "plain")),
    "ore": ((3, "welcome"), (6, "plain"), (1, "offended")),
    "phosphate": ((3, "prized"), (5, "welcome"), (2, "plain")),
    "alloy": ((4, "offended"), (6, "plain")),
    "spidroin": ((2, "prized"), (5, "welcome"), (3, "plain")),
    "magnetite": ((4, "prized"), (4, "welcome"), (2, "plain")),
    "trehalose": ((5, "welcome"), (5, "plain")),
    "xenopharma": ((5, "plain"), (5, "offended")),
    "survey": ((3, "welcome"), (7, "plain")),
    "xenolith": ((4, "plain"), (6, "offended")),
    "licence": ((1, "plain"),),
    "wildseed": ((1, "offended"),),
    "songglass": ((1, "offended"),),     # handing a gift back is an insult
}
DEFAULT_PRIOR = ((1, "plain"),)

#: A gathering answers more generously than it was given to: the surplus is
#: its own gift, and it is owed back. Measured over twenty gifts of 10 t with
#: the debt repaid in kind, songglass sold at the best Verge buyer: a prized
#: good fetches 1.02-1.45x the best Verge counter's price for it, a welcome
#: one 0.78-1.36x, a plain one 0.41-0.68x. An outlet, not a mint.
GENEROSITY = 1.25
#: Days a gathering waits for its gift to be answered before the silence is
#: an insult, and what the insult costs.
DEBT_DAYS = 90
INSULT_STANDING = -10.0
#: Standing a gift earns: its worth over this, to a cap, and only once in
#: `GIFT_STANDING_DAYS` at any one gathering — a hold of condensate handed
#: over in twenty pieces is one gift.
GIFT_STANDING_PER = 3000.0
GIFT_STANDING_CAP = 3.0
GIFT_STANDING_DAYS = 10
OFFENCE_STANDING = -3.0
DEBT_PAID_STANDING = 1.0

#: What they give back in: songglass, valued by the Kith at its base price.
SONGGLASS = "songglass"
#: Verge powers short of songglass, and where their supply settles: the
#: Charter makes lenses of it, and the Dry Choir listens to it.
SONGGLASS_BUYERS = {"charter": 0.62, "sanhedrin": 0.66}

#: What a gathering has to have been given before it grows you a graft.
GRAFT_AT = 15000.0


# ── the grafts ─────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Graft:
    #: The part id (`data/parts.PARTS`) and the gate a gathering's gift
    #: unlocks — `research.unlocked`, as incorporated alien work does.
    part: str
    gate: str
    #: The adaptation (`data/adaptations`) it answers, and what the pair is
    #: worth on top. Folded in by `sim/adaptation.fx`, the one door.
    pairs_with: str
    bonus: tuple
    why: str


GRAFTS: list[Graft] = [
    Graft("chorus_lens", "kith_chorus_lens", "acute_opsins",
          (plus("scan", 0.04),),
          "A retina already packed a receptor to the channel reads the lens's "
          "thousand small lights one at a time."),
    Graft("siphon_bell", "kith_siphon_bell", "mineral_gut",
          (pct("cargo", 0.06),),
          "A gut grown to eat rock feeds the bell, and the bell swells."),
    Graft("light_throat", "kith_light_throat", "sun_fed_intima",
          (plus("diplomacy", 0.08),),
          "An intima fed hard light gives the throat more to sing with."),
]
GRAFTS_BY_PART = {g.part: g for g in GRAFTS}
GRAFTS_BY_GATE = {g.gate: g for g in GRAFTS}

#: The gate the Kith hulls are built behind, set by the accord.
ACCORD_GATE = "kith_accord"
#: Every gate a Kith gift sets in `research.unlocked`, for the checks that
#: ask where a part's gate comes from.
GATES = (ACCORD_GATE, *(g.gate for g in GRAFTS))


# ── the gatherings ─────────────────────────────────────────────────────────

#: How many gatherings the Cradle holds. The entry system is never one: the
#: first sighting is a colony keeping its distance.
GATHERINGS_MIN, GATHERINGS_MAX = 4, 6
PORT_KIND = "gathering"
#: A gathering's name is two of its songs, rendered.
NAME_FIRST = ("Many", "Slow", "Bright", "Far", "Quiet", "Deep", "Young",
              "Ringing", "Low", "Open")
NAME_LAST = ("Lights", "Bell", "Chorus", "Wake", "Drift", "Bloom", "Shoal",
             "Veil", "Reach", "Cradle")

#: Days a berth takes: the colony closes round the hull and tends it.
BERTH_DAYS = 5

#: The Kith pilot's lineage (`data/lineages`), station and level.
PILOT_LINEAGE = "kith"
PILOT_ROLE = "nav"
PILOT_LEVEL = 4
PILOT_NAMES = ("Seven-Lights", "Slow-Bell", "Far-Answer", "Low-Chorus",
               "Wake-of-Many")


# ── words ──────────────────────────────────────────────────────────────────

FIRST_SIGHTING = (
    "A Kith colony on the edge of the {system} system: a hundred bodies strung "
    "on one stem, keeping its distance and flashing. Not a signal lamp — a "
    "song, in light, and it is being sung at you.")
BLURB = (
    "A people of the Cradle. Their hulls are colonies of many bodies grown "
    "along one stem, their speech is modulated light, and they trade by "
    "reciprocity: no price is posted, a gift asks to be answered, and a gift "
    "left unanswered is a debt, then an insult. They are curious about grown "
    "ships and wary of welded ones.")


# ── what they grow: grafts for a grown hull, and their own hulls ───────────

#: The grafts as parts, merged into `data/parts.PARTS`. Family "kith": only a
#: grown hull takes one (`data/hull_types.ACCEPTS`) — they are grown for a
#: body that already heals the way theirs do. Gated on a Kith gift, never on
#: research, so no Verge yard and no NPC loadout can reach them.
KITH_PARTS: list[Part] = [
    Part("chorus_lens", "Chorus Lens", "sensor", "kith", "kith_chorus_lens",
         16, {"credits": 2400, "biomass": 18, "songglass": 3},
         {"sensor": 2.0, "scan": 0.12},
         "A cluster of small bodies that each see one colour, grafted into the "
         "sensor fold. It was grown to hear light-song, and it reads a "
         "spectrum the way a choir reads a chord."),
    Part("siphon_bell", "Siphon Bell", "utility", "kith", "kith_siphon_bell",
         40, {"credits": 2800, "biomass": 30, "songglass": 4},
         {"cargo": 45, "regen": 0.10},
         "A swimming bell off a Kith stem, taught to hold rather than to push. "
         "It carries, and it seeps the colony's healing into the hull "
         "around it."),
    Part("light_throat", "Light-Throat", "compute", "kith",
         "kith_light_throat",
         10, {"credits": 2200, "biomass": 12, "songglass": 3},
         {"morale": 0.10},
         "A photophore row along the bow that sings back. The crew cannot "
         "read it; the Kith can, and they misread you less and are heard "
         "better while it sings."),
]

#: The Kith's own hulls, classes within the xeno family: a colony of many
#: bodies on one stem. Built only at a gathering, and only after an accord.
KITH_HULLS: list[Chassis] = [
    Chassis("drifter", "DRIFTER", "xeno", "Drifter", "Kith drifter / scout",
            420, 900, slots(2, 1, 3, 1, 1, 1, 2), 70, 6, 7.0, 1.45, 0.34,
            {"credits": 36000, "songglass": 12, "biomass": 40}, 40,
            ACCORD_GATE,
            "A short stem of swimming bells and one bright eye, loosed to "
            "wander ahead of a colony and sing back what it finds. It heals "
            "the way a Kith heals: by budding, slowly, everywhere.",
            "Physalia vagans"),
    Chassis("choir", "CHOIR-COLONY", "xeno", "Colony", "Kith choir-colony",
            1900, 11000, slots(2, 2, 4, 2, 3, 1, 4), 320, 24, 6.6, 1.05, 0.16,
            {"credits": 120000, "songglass": 40, "biomass": 160,
             "phosphate": 30}, 120, ACCORD_GATE,
            "A siphonophore the size of a station hull: feeding bodies, "
            "swimming bells, a crown of photophores, and room between them for "
            "a crew the colony has decided to carry. It sings while it "
            "flies, and nothing aboard can stop it.",
            "Nanomia chorus"),
]
