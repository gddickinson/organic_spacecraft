"""Named rivals: what kinds there are, how each fights, and what they say.

Tables only. `sim/nemeses.py` decides who rises, where they go and when they
come back; `sim/rivals.py` builds the fight and spends its outcome;
`sim/hunts.py` is the board, the search and the trophy. Nothing here decides
anything — it says what a Yards ace *is*, so the rules can ask.

**Every one of these comes out of something that already happened.** A
corsair is the raider you ran from; a warrant hunter is a posted price that
grew a face; a Yards ace is a Concordat captain who struck to you and was let
go; a Freehold duellist is what the cartel sends after a captain who has been
selling under it; a husk is a Charter hull the Bloom took, still answering to
its old name. None of them is rolled out of the air.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .part_types import Part


@dataclass(frozen=True)
class Archetype:
    id: str
    name: str
    #: The colours they sail under, for the fight and for the law. None is a
    #: hull on nobody's register: killing it is no power's business, which is
    #: why a corsair can carry a bounty without the bounty being a crime.
    sails: str | None
    #: Whose yards the hull comes out of — `encounters.make_enemy`'s pool.
    yard: str
    origin: str
    style: str
    #: `enemy_ai.STYLES` key: how readily they close, fire and run.
    personality: str
    #: Share of their moves made toward where they last heard of you.
    pursuit: float
    #: Odds they come for you when you arrive where they are, lit.
    aggression: float
    parley: bool
    #: Whether a price ends it: the Freeholds' duellists are for hire.
    buy_off: bool
    #: Odds a spared one stays grateful, before the grudge is counted.
    ally: float
    traits: tuple
    #: Whether they post a price of their own on the hull: set per archetype
    #: rather than per rise, because who pays for a corsair is a fact about
    #: corsairs.
    wanted: bool
    #: What their kind adds to the threat they rose at. Measured, not felt:
    #: level for level a Yards ace won 38% against a warfitted NAVIS and a
    #: husk 97%, because the Concordat's yards build battleships and the
    #: Bloom's take whatever it finds. These pull both toward the middle.
    edge: float = 0.0


ARCHETYPES = (
    Archetype(
        "corsair", "Corsair", None, "freeholds",
        "A raider you ran from, or drove off, who took it personally.",
        "Ambush, and gone at the first real hurt.",
        "cautious", 0.35, 0.55, True, False, 0.45,
        ("ambusher", "coward", "ghost", "swarm", "shielded"), True),
    Archetype(
        "hunter", "Warrant hunter", "", "freeholds",
        "A posted price with a face. Somebody's paper on your hull.",
        "Relentless: follows you between systems, and hears where you went.",
        "aggressive", 0.85, 0.75, True, False, 0.25,
        ("relentless", "shielded", "swarm", "ambusher"), False, -0.3),
    Archetype(
        "ace", "Yards ace", "concordat", "concordat",
        "A Concordat captain who struck to you, and was let go.",
        "A duellist: closes to short band and makes every shot count.",
        "aggressive", 0.5, 0.6, True, False, 0.55,
        ("duellist", "shielded", "relentless"), False, -0.6),
    Archetype(
        "duellist", "Freehold duellist", "freeholds", "freeholds",
        "What the cartel sends after a captain who sells under it.",
        "Mercenary: fights for the fee, and a better fee ends it.",
        "balanced", 0.45, 0.6, True, True, 0.5,
        ("duellist", "coward", "ambusher", "swarm"), False),
    Archetype(
        "husk", "Bloom-ridden husk", "bloom", "bloom",
        "A Charter hull the Bloom took. It still answers to its name.",
        "No parley. It learns your guns the way the Bloom does.",
        "feral", 0.3, 0.8, False, False, 0.0,
        ("relentless", "shielded", "swarm", "ghost"), True, 0.6),
)
ARCHETYPES_BY_ID = {a.id: a for a in ARCHETYPES}


@dataclass(frozen=True)
class Trait:
    id: str
    name: str
    blurb: str


TRAITS = (
    Trait("ambusher", "Ambusher", "Fires first: a volley before you have "
          "the range, unless you found them."),
    Trait("duellist", "Duellist", "A trained eye at short band: +8% on "
          "every mount."),
    Trait("coward", "Coward", "Two fifths less nerve. Breaks off as soon as "
          "the hull is really opened."),
    Trait("relentless", "Relentless", "Never retreats twice. Once beaten, "
          "two fifths more nerve, and no running on a broken hull."),
    Trait("shielded", "Shielded", "An extra layer of armour: a quarter "
          "more hull."),
    Trait("swarm", "Swarm", "Brings one or two escorts from level four; "
          "each screens an eighth of a hull and steadies the crew."),
    Trait("ghost", "Ghost", "Runs dark. Sightings go stale twice as fast "
          "and a search sees her at a quarter the range."),
)
TRAITS_BY_ID = {t.id: t for t in TRAITS}


#: How each way an engagement can end reads in a rival's file. **Every
#: result id in `battle_state.ENDINGS`, and no new one** — a new result id
#: breaks every outcome tally in the game, so the rivalry keeps its own words
#: for the ones that already exist. `test_nemeses` holds the two key sets
#: equal.
ENDINGS = {
    "destroyed": ("dead", "you destroyed {them}"),
    "driven-off": ("wounded", "you drove {them} off"),
    "struck": ("spared", "{they} struck to you, and you let {them} live"),
    "parley": ("truce", "you talked {them} down"),
    "escaped": ("ran", "you ran from {them}"),
    "routed": ("beaten", "{they} beat you and let you go"),
    "stalemate": ("even", "neither of you could finish it"),
    "lost": ("beaten", "{they} took your hull apart"),
}

#: Pronouns by subject form, for the lines above.
OBJECT = {"she": "her", "he": "him", "they": "them", "it": "it"}

#: Who won each meeting, for the history line and the grudge.
WINNER = {"destroyed": "you", "driven-off": "you", "struck": "you",
          "parley": "neither", "escaped": "them", "routed": "them",
          "stalemate": "neither", "lost": "them"}


#: Names, with the pronoun the header uses. A husk keeps its hull's old
#: Charter name and is "it"; `sim/nemeses.rise` handles that one.
NAMES = (
    ("Vorn Aldane", "he"), ("Iselle Kast", "she"), ("Maro Quell", "he"),
    ("Tamsin Orr", "she"), ("Dace Whitlow", "he"), ("Oona Brisk", "she"),
    ("Hollis Venn", "they"), ("Pell Sarrow", "she"), ("Rook Hadeline", "he"),
    ("Anneke Soto", "she"), ("Juno Castellan", "they"), ("Brenn Tacey", "he"),
    ("Sable Ferrant", "she"), ("Cato Imrie", "he"), ("Lise Vantongeren", "she"),
    ("Absalom Reyes", "he"),
)


#: What they send, by occasion. `{name}` is theirs, `{you}` your hull's,
#: `{place}` where it happened. Picked stably per rival and day.
TAUNTS = {
    "rise": (
        "{you}. I know the name now. I will know the hull when I see it.",
        "They say you are good. I would like to find out at {place}.",
        "Nobody walks away from me twice, {you}. You have used your once.",
    ),
    "before": (
        "I heard you put in at {place}. I am not far.",
        "Keep your transponder on, {you}. It saves me the looking.",
        "Soon. You will know me by the first shot.",
    ),
    "won": (
        "You ran well. Run further next time.",
        "I took what I wanted from your hold. Next time I take the hull.",
        "Tell your crew who did that to them, {you}.",
    ),
    "wounded": (
        "This is not finished. I am only going to the yard.",
        "You were lucky at {place}. I will bring a better hull.",
        "Mend your holes, {you}. I am mending mine.",
    ),
    "return": (
        "New fittings, {you}. I thought of you while they went on.",
        "I am back in the lanes, and I have been practising.",
    ),
    "spared": (
        "You could have finished it. I will not forget that.",
        "I owe you a hull, {you}. I pay what I owe.",
    ),
    "betray": (
        "I said I owed you. I lied.",
        "Gratitude is a luxury, {you}. I could not afford it.",
    ),
    "truce": (
        "Talk is cheap, {you}. So was this.",
        "Another day, then.",
    ),
}


#: The shroud: the only fitting that deepens running dark. **Kit for a voyage
#: rather than a fight**, so NPC loadouts skip it (`civilian`) — letting a new
#: utility part into the enemy pool re-rolls every encounter in the game, which
#: is what adding the smuggling parts once did. A shroud only works dark: a
#: hull squawking its transponder is not hiding behind anything.
SHROUDS = (
    Part("stilling_mantle", "Stilling Mantle", "utility", "grown", "melanin",
         18, {"credits": 11000, "biomass": 20, "phosphate": 4},
         {"draw": 2},
         "A mantle of chromatophores over a vasculature that holds the skin "
         "at the temperature of the sky behind it. Run dark, she stops "
         "answering at all.", civilian=True),
    Part("plasma_shroud", "Plasma Shroud", "utility", "fabricated", "ecm",
         26, {"credits": 16000, "alloy": 10, "silicon": 6},
         {"draw": 6, "heatCap": -6},
         "Chaff and a thin plasma skin, fed off the reactor. Run dark, it "
         "takes most of what is left of the signature; lit, it is ballast.",
         civilian=True),
)
SHROUD_IDS = tuple(p.id for p in SHROUDS)


#: What a trophy mount gains over the gun it was taken from.
TROPHY_ACCURACY = 0.08


def trophy_part(record: dict, base: Part) -> Part:
    """The unique fitting taken from a rival's best mount.

    `record` is the rival's trophy entry (`id`, `owner`); `base` is the part
    it was cut from. Same slot, family and cost — a trophy is a gun you can
    fit, not a new class of thing — with the owner's name and a better eye.
    """
    owner = str(record.get("owner", "")).split()[0] or "Someone"
    noun = base.name.split()[-1]
    wpn = (replace(base.wpn, acc=base.wpn.acc + TROPHY_ACCURACY)
           if base.wpn is not None else None)
    return replace(base, id=str(record["id"]), name=f"{owner}'s {noun}",
                   wpn=wpn, tech=None, civilian=True,
                   blurb=(f"Taken off {record.get('owner', 'a rival')}'s hull. "
                          f"The {base.name} as they kept it: "
                          f"+{TROPHY_ACCURACY:.0%} accuracy."))
