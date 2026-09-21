"""A world in eight characters: the profile every other answer hangs off.

Taken from *Traveller*, whose Universal World Profile has been the best idea
in science-fiction gaming since 1977 for one reason — it is **one short string
that a dozen unrelated systems can all read**. What a port will sell you, what
the law will stop you carrying, what a colony can build, who is likely to be
shooting: in Traveller all of it falls out of the same eight digits, and a
referee who knows the profile knows the world.

    A867954-B
    │││││││ └── tech level
    ││││││└──── law level
    │││││└───── government
    ││││└────── population
    │││└─────── hydrographics
    ││└──────── atmosphere
    │└───────── size
    └────────── starport

SEEDFALL already had most of these facts and kept them in eight different
places: `world/planets.Body` knows the radius, the gravity and the biome,
`world/galaxy.Port` knows the starport and who holds it, `sim/piracy` knows
the lawlessness, and the factions know the rest. **Nothing is stored twice
and nothing new is saved** — `sim/profile.py` derives the digits from what
the sector already is, so a profile cannot drift from the world it describes
and an old chronicle grows one without a migration.

Everything here is a table. The deriving is `sim/profile.py`; reading a
profile into sentences is `says` at the bottom of this file.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Traveller's own alphabet: 0-9 then A-Z, so a single character carries a
#: value past nine. Kept because the whole point of a profile is that it fits
#: on one line and can be read aloud.
DIGITS = "0123456789ABCDEFGHJKLMNPQRSTUVW"


def digit(value: int) -> str:
    """One characteristic as its character. Clamped rather than raising: a
    profile is a *description*, and a world at the end of a scale is still a
    world."""
    return DIGITS[max(0, min(len(DIGITS) - 1, int(value)))]


def value(char: str) -> int:
    """Back the other way, for anything that reads a written profile."""
    return DIGITS.index(char.upper()) if char.upper() in DIGITS else 0


#: The starport classes, by what they will actually do for a hull. This is the
#: one digit a captain reads first, because it answers "can I get out of here
#: again": an A yard builds ships, a D has a dirt strip and unrefined fuel,
#: and an X is a place you do not land at twice.
STARPORTS = {
    5: ("A", "Excellent", "shipyard, refined fuel, every repair"),
    4: ("B", "Good", "hulls built, refined fuel, most repairs"),
    3: ("C", "Routine", "refined fuel and a yard that can patch a hull"),
    2: ("D", "Poor", "unrefined fuel, a berth, and little else"),
    1: ("E", "Frontier", "a cleared patch of ground; no fuel, no yard"),
    0: ("X", "None", "no port at all — nobody is expecting you"),
}

#: Size, as the diameter it means and what that does to a person standing on
#: it. The gravity figures are Traveller's and match what `world/planets`
#: already computes from a radius, which is why this reads as one scale.
SIZES = {
    0: ("under 1,000 km", 0.00, "an asteroid or a shard"),
    1: ("1,600 km", 0.05, "you could jump off it"),
    2: ("3,200 km", 0.15, "low enough to feel wrong"),
    3: ("4,800 km", 0.25, "low"),
    4: ("6,400 km", 0.35, "low"),
    5: ("8,000 km", 0.45, "noticeably light"),
    6: ("9,600 km", 0.70, "comfortable"),
    7: ("11,200 km", 0.90, "near enough to a standard"),
    8: ("12,800 km", 1.00, "standard"),
    9: ("14,400 km", 1.25, "heavy"),
    10: ("16,000 km", 1.40, "punishing over a long stay"),
}

#: Atmosphere, and whether a person can breathe it unaided. The middle of the
#: scale is where people live; both ends are where the interesting cargo is.
ATMOSPHERES = {
    0: ("None", "vacuum — a suit, always"),
    1: ("Trace", "a suit, always"),
    2: ("Very thin, tainted", "a mask and a filter"),
    3: ("Very thin", "a mask"),
    4: ("Thin, tainted", "a filter"),
    5: ("Thin", "breathable, and you will feel it"),
    6: ("Standard", "breathable"),
    7: ("Standard, tainted", "a filter"),
    8: ("Dense", "breathable"),
    9: ("Dense, tainted", "a filter"),
    10: ("Exotic", "air supply"),
    11: ("Corrosive", "a hostile suit, and not for long"),
    12: ("Insidious", "a hostile suit; it finds the seams anyway"),
    13: ("Dense, high", "breathable in the lowlands only"),
    14: ("Ellipsoidal", "breathable at the poles"),
    15: ("Thin, low", "breathable in the trenches"),
}

#: Hydrographics: how much of the surface is liquid, in tenths.
HYDROGRAPHICS = {
    0: "desert — no free liquid at all",
    1: "dry — a few per cent",
    2: "arid",
    3: "dry continents",
    4: "wet continents",
    5: "half and half",
    6: "more sea than land",
    7: "scattered continents",
    8: "islands and archipelagos",
    9: "a few islands",
    10: "water world — no land worth the name",
}

#: Population, as the order of magnitude it is. The jump from 4 to 6 is the
#: difference between an outpost and somewhere with its own politics.
POPULATIONS = {
    0: "nobody", 1: "a few dozen", 2: "hundreds", 3: "thousands",
    4: "tens of thousands", 5: "hundreds of thousands", 6: "millions",
    7: "tens of millions", 8: "hundreds of millions", 9: "a billion",
    10: "tens of billions", 11: "hundreds of billions", 12: "trillions",
}

#: Government, in the words this sector would use. Traveller's list, trimmed
#: to the kinds the Verge actually grows and named in the game's own voice.
GOVERNMENTS = {
    0: ("None", "nobody speaks for it"),
    1: ("Company", "a charter holds the deed and the police"),
    2: ("Participating democracy", "everyone votes on everything, slowly"),
    3: ("Self-perpetuating oligarchy", "the same names, always"),
    4: ("Representative democracy", "elected, and it mostly works"),
    5: ("Feudal technocracy", "authority follows the licence"),
    6: ("Captive government", "run from somewhere else"),
    7: ("Balkanised", "several governments, none of them agreed"),
    8: ("Civil service bureaucracy", "the forms are the government"),
    9: ("Impersonal bureaucracy", "the forms have forgotten why"),
    10: ("Charismatic dictator", "one person, and they are listened to"),
    11: ("Non-charismatic leader", "one person, and they are not"),
    12: ("Charismatic oligarchy", "a few, and they are loved"),
    13: ("Religious dictatorship", "the doctrine is the law"),
}

#: Law level, as what it actually stops you carrying. The whole reason a
#: captain reads this digit: it is a list of what is in the hold and a list of
#: what the port will find.
LAW_LEVELS = {
    0: ("None", "carry what you like; nobody asks"),
    1: ("Low", "no poison gas, no explosives, no undetectable weapons"),
    2: ("Low", "no portable energy weapons"),
    3: ("Moderate", "weapons licensed; military hardware refused"),
    4: ("Moderate", "no light assault weapons"),
    5: ("Moderate", "no personal concealable weapons"),
    6: ("High", "most firearms refused"),
    7: ("High", "shotguns refused"),
    8: ("High", "no blade over a hand's length"),
    9: ("Extreme", "any weapon out of its case is an offence"),
    10: ("Extreme", "weapons are contraband; so is much else"),
    11: ("Extreme", "movement is licensed"),
    12: ("Extreme", "leaving is licensed"),
}

#: Tech level, by what it can make and what it is worth buying there.
TECH_LEVELS = {
    0: "pre-industrial", 1: "steam", 2: "combustion", 3: "electric",
    4: "atomic", 5: "electronic", 6: "orbital", 7: "interplanetary",
    8: "early fusion", 9: "in-system industry", 10: "jump-capable",
    11: "grown hulls", 12: "the Verge's best", 13: "better than the Charter",
    14: "Weave-adjacent", 15: "nobody will say where it came from",
}


@dataclass(frozen=True)
class Profile:
    """One world in eight characteristics. Derived, never stored."""

    starport: int
    size: int
    atmosphere: int
    hydrographics: int
    population: int
    government: int
    law: int
    tech: int
    #: Bases and the travel advisory, which are not part of the string but are
    #: read in the same breath: a naval base means fuel and a red zone means
    #: the Charter will shoot you for going.
    bases: tuple = ()
    zone: str = "green"
    gas_giant: bool = False

    def __str__(self) -> str:
        return code(self)


def code(p: Profile) -> str:
    """The profile as the eight-character string a captain reads aloud."""
    return (f"{STARPORTS.get(p.starport, STARPORTS[0])[0]}"
            f"{digit(p.size)}{digit(p.atmosphere)}{digit(p.hydrographics)}"
            f"{digit(p.population)}{digit(p.government)}{digit(p.law)}"
            f"-{digit(p.tech)}")


#: The trade classifications, and the profile that earns each. Traveller's
#: own conditions, because they are what make the codes mean anything: a
#: world is *agricultural* when its air, its water and its population say so,
#: not because somebody labelled it.
#:
#: `(code, name, test)` — the test is asked of a `Profile`.
TRADE_CODES = (
    ("Ag", "Agricultural",
     lambda p: 4 <= p.atmosphere <= 9 and 4 <= p.hydrographics <= 8
     and 5 <= p.population <= 7),
    ("As", "Asteroid belt",
     lambda p: p.size == 0 and p.atmosphere == 0 and p.hydrographics == 0),
    ("Ba", "Barren",
     lambda p: p.population == 0 and p.government == 0 and p.law == 0),
    ("De", "Desert",
     lambda p: p.atmosphere >= 2 and p.hydrographics == 0),
    ("Fl", "Fluid oceans",
     lambda p: p.atmosphere >= 10 and p.hydrographics >= 1),
    ("Ga", "Garden",
     lambda p: p.atmosphere >= 5 and 4 <= p.hydrographics <= 9
     and 4 <= p.population <= 8),
    ("Hi", "High population", lambda p: p.population >= 9),
    ("Ic", "Ice-capped",
     lambda p: p.atmosphere <= 1 and p.hydrographics >= 1),
    ("In", "Industrial",
     lambda p: p.atmosphere in (0, 1, 2, 4, 7, 9) and p.population >= 9),
    ("Lo", "Low population", lambda p: 1 <= p.population <= 3),
    ("Lt", "Low technology", lambda p: p.population > 0 and p.tech <= 5),
    ("Ht", "High technology", lambda p: p.tech >= 12),
    ("Na", "Non-agricultural",
     lambda p: p.atmosphere <= 3 and p.hydrographics <= 3
     and p.population >= 6),
    ("Ni", "Non-industrial", lambda p: 4 <= p.population <= 6),
    ("Po", "Poor",
     lambda p: 2 <= p.atmosphere <= 5 and p.hydrographics <= 3),
    ("Ri", "Rich",
     lambda p: p.atmosphere in (6, 8) and 6 <= p.population <= 8),
    ("Va", "Vacuum", lambda p: p.atmosphere == 0),
    ("Wa", "Water world", lambda p: p.hydrographics == 10),
)

TRADE_NAMES = {code_: name for code_, name, _test in TRADE_CODES}


def codes(p: Profile) -> tuple:
    """Every trade classification this world earns, in the usual order."""
    return tuple(code_ for code_, _name, test in TRADE_CODES if test(p))


#: What each classification means for what a world makes and what it wants.
#: **Said rather than priced.** Wiring these into `world/economy` moves every
#: number in an economy the rest of the game is tuned against — measured, it
#: broke the freight desk's load clamp and put the careful captain's five-year
#: ending out of reach. What a world *is* is true whatever it charges, and it
#: is what a captain reads a profile for; the prices are their own piece of
#: work, with its own measurement (see `IMPROVEMENTS.md`).
TRADES = {
    "Ag": "grows more food than it eats",
    "As": "mines its own ore and imports everything else",
    "Ba": "nobody here to trade with",
    "De": "buys every drop of water it drinks",
    "Fl": "chemistry, and nothing you would drink",
    "Ga": "comfortable, and it exports the surplus",
    "Hi": "more mouths than the ground can feed",
    "Ic": "volatiles under the crust, if you can get at them",
    "In": "yards and furnaces; it makes what others buy",
    "Lo": "too few people to make anything at scale",
    "Lt": "buys its machinery in, at a price",
    "Ht": "makes what nobody else in the Verge can",
    "Na": "no farms — the food comes by ship",
    "Ni": "no industry — the tools come by ship",
    "Po": "thin air, no water, and it shows",
    "Ri": "comfortable and moneyed; it buys the good things",
    "Va": "airless — everything is imported, including the air",
    "Wa": "water without end, and land worth fighting over",
}


def trades(p: Profile) -> list:
    """What this world makes and wants, in a sentence per classification."""
    return [f"{TRADE_NAMES[c]} — {TRADES[c]}." for c in codes(p) if c in TRADES]


def says(p: Profile) -> list:
    """The profile as sentences, in the order a captain reads them."""
    port = STARPORTS.get(p.starport, STARPORTS[0])
    size = SIZES.get(p.size, SIZES[0])
    air = ATMOSPHERES.get(p.atmosphere, ATMOSPHERES[0])
    law = LAW_LEVELS.get(p.law, LAW_LEVELS[0])
    gov = GOVERNMENTS.get(p.government, GOVERNMENTS[0])
    return [
        f"Starport {port[0]} — {port[1]}: {port[2]}.",
        f"{size[0]} across at {size[1]:.2f} g — {size[2]}.",
        f"{air[0]} atmosphere: {air[1]}.",
        f"Hydrographics {p.hydrographics} — "
        f"{HYDROGRAPHICS.get(p.hydrographics, '—')}.",
        f"Population {POPULATIONS.get(p.population, '—')}.",
        f"{gov[0]} — {gov[1]}.",
        f"Law level {p.law} ({law[0]}): {law[1]}.",
        f"Tech level {p.tech} — {TECH_LEVELS.get(p.tech, '—')}.",
    ]
