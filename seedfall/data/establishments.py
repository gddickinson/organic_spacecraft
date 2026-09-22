"""Establishments: the places people build to sell what people want.

A quay, a drum and a settlement are what a world *is*. These are what grows
round the trade: somewhere to have a hull laid down, somewhere to sleep that
is better than a berth, somebody who will cut you open properly, somewhere
to lose money, somewhere to lose a week. Each is a real place in its system
(`sim/establishments.py` seeds them, `sim/places.py` lists them) with:

- its own **signature doors** (`data/venues_establishments.py`), open there
  and nowhere else — the Grand's suites are at the Grand;
- the **ordinary doors** it carries, by kind: a hotel has eating houses and
  entertainments and no chop shop, a smugglers' den the reverse;
- a **shape** to be walked as (`sim/afoot_plans`): a hotel is a ring, a
  pleasure palace a drum, a free market a quay's can, a base sheds on the
  ground — and the **rooms** that shape has to hold;
- what it **builds**, for a yard: the need it answers in
  `sim/shipyard.can_build_here` — and what it **reactivates**: a breakers'
  yard puts a derelict of a kind nobody in the Verge designed back together
  (never lays down one to a plan nobody has read).

A station stands in orbit of a body; a base stands on one, and keeps a pad
in orbit over it — its landing field's berth, where the shuttle meets you
(`sim/anchorage`). Neither conjures money: every door charges for what it
sells.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Establishment:
    """A kind of establishment."""

    id: str
    name: str
    #: The place kind it is: "station" in orbit, "base" on the ground.
    kind: str
    #: Name patterns: `{body}` is the body it is at, `{word}` a word of its
    #: own from `WORDS`.
    names: tuple
    what: str
    heads: int
    amenity: int
    #: The law it keeps: an absolute level, or None for the system's own.
    law: int | None
    #: How it is laid out afoot: ring, drum, tower, keel, quay or ground.
    shape: str
    #: Whose yard built it — the walls and doors it has.
    family: str
    #: Ordinary venue kinds it carries besides its own signature doors.
    kinds: tuple
    #: Rooms its shape has to hold: (kind, name, count, area).
    rooms: tuple
    #: Bodies it can be at (`world` body kinds), and how often one is.
    at: tuple
    weight: float
    #: A yard's `BUILD_NEED` it answers, if it lays down hulls.
    builds: str = ""
    #: Hull classes it can put back together from a derelict — a breakers'
    #: yard's REVENANT — though it lays nothing else down.
    reactivates: tuple = ()
    #: True if it only sets up where a dead hull is adrift (`BREAKERS_ODDS`),
    #: drawn on a stream of its own so no other house in the sector moves.
    by_wrecks: bool = False
    #: True if it only turns up where there is a starport to trade with.
    needs_port: bool = False
    #: The least tech level it runs at, whatever the world under it: a
    #: surgical station brings its own theatres.
    tech: int = 0


#: Bodies a station can stand off, and bodies a base can stand on.
ORBIT = ("gas", "rocky", "moon", "ice", "asteroid", "ocean", "comet")
SOLID = ("rocky", "moon", "ice", "asteroid")

ESTABLISHMENTS: tuple = (
    # ── stations: somebody's business in orbit ──────────────────────────
    Establishment(
        "shipyard", "Shipyard", "station",
        ("{body} Yards", "{word} Slips", "The {word} Yard"),
        "Slipways and a drydock, and hulls laid down to order.",
        900, 3, None, "keel", "fabricated",
        ("chandler", "eatery", "office", "tech", "lodging"),
        (("slipway", "Slipway", 2, 30), ("drydock", "Drydock", 1, 30),
         ("fabhall", "Fabrication hall", 1, 20),
         ("workshop", "Yard shop", 1, 12), ("dormitory", "Yard hands", 1, 20)),
        ORBIT, 1.0, builds="shipyard", needs_port=True, tech=11),
    Establishment(
        "hull_nursery", "Hull nursery", "station",
        ("{word} Nursery", "The {body} Womb"),
        "A gestation womb and the people who midwife hulls out of it.",
        400, 2, None, "keel", "grown",
        ("eatery", "clinic", "temple"),
        (("works", "Gestation womb", 1, 30), ("lab", "Seed bank", 1, 14),
         ("farm", "Feed tanks", 1, 18), ("dormitory", "Midwives", 1, 14)),
        ORBIT, 0.5, builds="gestation"),
    Establishment(
        "breakers_yard", "Breakers' yard", "station",
        ("The {word} Breakers", "{body} Salvage", "The {word} Boneyard"),
        "Dead hulls cut up for what is in them — and, for a price, one of the "
        "strange ones put back together.",
        500, 2, 4, "keel", "fabricated",
        ("chandler", "tech", "eatery", "vice"),
        (("slipway", "Breaking slip", 2, 30), ("hold", "Salvage hold", 1, 24),
         ("lab", "Reading room", 1, 12), ("workshop", "Cutting shop", 1, 14),
         ("dormitory", "Breakers", 1, 16)),
        ORBIT, 0.5, reactivates=("revenant",), tech=12, by_wrecks=True),
    Establishment(
        "grand_hotel", "Grand hotel", "station",
        ("The {word} Grand", "The {body} Grand", "Hotel {word}"),
        "Suites with a view of the world, and staff who remember names.",
        1400, 4, 6, "ring", "hybrid",
        ("eatery", "entertainment", "arts", "market", "bank", "sport"),
        (("suites", "Suites", 3, 22), ("lounge", "Lounge", 1, 18),
         ("dining", "Dining room", 1, 16), ("pools", "The pool", 1, 18),
         ("observation", "Observation gallery", 1, 14)),
        ORBIT, 0.8, needs_port=True, tech=11),
    Establishment(
        "spacers_rest", "Spacers' rest", "station",
        ("The {word} Rest", "{body} Bunkhouse", "The Capsule"),
        "Bunks by the hour, a canteen that never shuts, and the crew board.",
        300, 2, None, "quay", "fabricated",
        ("eatery", "chandler", "office", "entertainment"),
        (("dormitory", "Capsule deck", 2, 24), ("galley", "Canteen", 1, 12),
         ("heads", "Wash house", 1, 8)),
        ORBIT, 1.0),
    Establishment(
        "pleasure_palace", "Pleasure palace", "station",
        ("The House of {word}", "The {word} Palace", "{word}'s"),
        "A drum given over to pleasure: salons, gardens, and nobody asking.",
        1800, 4, 2, "drum", "hybrid",
        ("eatery", "entertainment", "arts", "lodging", "vice"),
        (("salon", "Salon", 2, 18), ("pools", "The baths", 1, 20),
         ("sauna", "Steam rooms", 1, 10), ("gaming", "Card room", 1, 14),
         ("suites", "Private rooms", 2, 18)),
        ORBIT, 0.6),
    Establishment(
        "surgical_station", "Surgical station", "station",
        ("{word} Infirmary", "The {body} Surgery", "St {word}'s"),
        "Theatres, wards and surgeons who operate on what a clinic sends up.",
        700, 3, 5, "ring", "fabricated",
        ("clinic", "eatery", "lodging", "temple"),
        (("surgery", "Operating theatre", 2, 12), ("wards", "Ward", 2, 18),
         ("clinic", "Casualty", 1, 12), ("lab", "Pathology", 1, 10),
         ("cold", "Cold store", 1, 10)),
        ORBIT, 0.7, needs_port=True, tech=13),
    Establishment(
        "spa_station", "Spa station", "station",
        ("{word} Springs", "The {body} Baths", "{word} Spa"),
        "Heated water, salt, steam and quiet — a week of it mends people.",
        600, 3, 4, "ring", "grown",
        ("eatery", "sport", "clinic", "lodging", "arts"),
        (("pools", "Thermal pool", 2, 20), ("sauna", "Steam house", 1, 12),
         ("salon", "Treatment rooms", 1, 14), ("farm", "The gardens", 1, 20),
         ("suites", "Guest rooms", 2, 16)),
        ORBIT, 0.6),
    Establishment(
        "gaming_wheel", "Gaming wheel", "station",
        ("The {word} Wheel", "{word}'s Wheel", "The {body} Wheel"),
        "A spinning wheel of tables, and a cage that pays out in the morning.",
        1100, 3, 3, "ring", "fabricated",
        ("eatery", "entertainment", "bank", "lodging", "vice"),
        (("gaming", "Gaming floor", 3, 20), ("lounge", "Bar", 1, 14),
         ("vault", "The cage", 1, 10), ("suites", "High rollers' rooms", 1,
                                         16)),
        ORBIT, 0.7),
    Establishment(
        "free_market", "Free market", "station",
        ("The {word} Exchange", "{body} Free Market", "The {word} Souk"),
        "Stalls on every deck, and nobody behind any of them asks for papers.",
        1600, 3, 2, "quay", "hybrid",
        ("market", "chandler", "tech", "eatery", "office", "vice"),
        (("market", "Stall deck", 2, 22), ("hold", "Bonded store", 1, 18)),
        ORBIT, 0.8),
    # ── bases: somebody's ground ─────────────────────────────────────────
    Establishment(
        "mining_base", "Mining base", "base",
        ("{body} Diggings", "Camp {word}", "The {word} Pit"),
        "A shaft, a mill, a company store and a bar, in that order.",
        350, 2, None, "ground", "fabricated",
        ("chandler", "eatery", "clinic", "vice"),
        (("works", "Shaft head", 1, 20), ("works", "Ore mill", 1, 18),
         ("store", "Powder store", 1, 8), ("bunkhouse", "Bunkhouse", 1, 16)),
        SOLID, 1.0),
    Establishment(
        "research_base", "Research base", "base",
        ("{body} Station", "{word} Base", "The {word} Observatory"),
        "Laboratories, a long library, and people who will pay for samples.",
        120, 2, 5, "ground", "fabricated",
        ("tech", "eatery", "clinic"),
        (("lab", "Laboratory", 2, 14), ("library", "Library", 1, 12),
         ("sensors", "Instrument hall", 1, 12), ("cold", "Sample store", 1,
                                                  8)),
        SOLID, 0.7, tech=12),
    Establishment(
        "garrison", "Garrison", "base",
        ("Fort {word}", "{body} Garrison", "Camp {word}"),
        "Barracks, a parade ground, a magazine and a recruiting office.",
        800, 2, 8, "ground", "fabricated",
        ("eatery", "office", "law", "sport"),
        (("barracks", "Barracks", 2, 18), ("magazine", "Magazine", 1, 10),
         ("brig", "Guardroom", 1, 8), ("command", "Headquarters", 1, 12)),
        SOLID, 0.6),
    Establishment(
        "smugglers_den", "Smugglers' den", "base",
        ("{word}'s Hole", "The {word} Den", "{body} Landing"),
        "Hidden holds, a quiet surgeon, and a back room where things change "
        "hands.",
        150, 2, 0, "ground", "hybrid",
        ("vice", "eatery", "lodging", "chandler"),
        (("hold", "Hidden hold", 2, 14), ("cold", "The cooler", 1, 8)),
        SOLID, 0.6, tech=11),
    Establishment(
        "farm_base", "Farm base", "base",
        ("{body} Farms", "{word} Acres", "The {word} Domes"),
        "Growing domes, a processing shed, and a kitchen that feeds the "
        "system.",
        260, 2, None, "ground", "grown",
        ("market", "eatery", "temple"),
        (("farm", "Growing dome", 3, 22), ("works", "Processing shed", 1, 16)),
        SOLID, 0.7),
    Establishment(
        "retreat", "Retreat", "base",
        ("The {word} Retreat", "{word} House", "The Cloister of {word}"),
        "A house of an order, where the quiet is the point.",
        80, 1, 6, "ground", "grown",
        ("temple", "eatery", "arts"),
        (("chapel", "Chapel", 1, 12), ("library", "Scriptorium", 1, 12),
         ("farm", "Kitchen garden", 1, 16), ("quarters", "Cells", 1, 14)),
        SOLID, 0.5),
)
ESTABLISHMENT_BY_ID = {e.id: e for e in ESTABLISHMENTS}

#: What a station looks like in the sky and at the berth: the structure of
#: the class it is built like (`data/works3d`), so a wheel is a ring and a
#: palace a drum there as well as afoot.
MESH = {"shipyard": "fab_yard", "hull_nursery": "gravid_nursery",
        "breakers_yard": "orbital_dock",
        "grand_hotel": "free_port", "spacers_rest": "quay",
        "pleasure_palace": "arca_drum", "surgical_station": "coral_reef",
        "spa_station": "pomona_grove", "gaming_wheel": "orbital_dock",
        "free_market": "hub"}

#: Words an establishment is named with.
WORDS = ("Amber", "Halcyon", "Meridian", "Lantern", "Saffron", "Vesper",
         "Orrery", "Cinder", "Marigold", "Tamarind", "Kestrel", "Sable",
         "Juniper", "Coral", "Harrow", "Lumen", "Obsidian", "Serein",
         "Velvet", "Winter", "Quill", "Thistle", "Cobalt", "Ember")

#: What each is worth, in credits, for a stake in it: a tenth of it is for
#: sale (`STAKE_SHARE`) to a captain alongside, and pays out of the house's
#: own takings (`STAKE_MONTHLY` of the stake's price every `STAKE_DAYS`).
#: A garrison and a retreat are not for sale.
WORTH = {"shipyard": 900_000, "hull_nursery": 300_000,
         "breakers_yard": 350_000,
         "grand_hotel": 600_000, "spacers_rest": 150_000,
         "pleasure_palace": 700_000, "surgical_station": 500_000,
         "spa_station": 400_000, "gaming_wheel": 800_000,
         "free_market": 500_000, "mining_base": 250_000,
         "research_base": 120_000, "smugglers_den": 200_000,
         "farm_base": 200_000}
STAKE_SHARE = 0.1
STAKE_MONTHLY = 0.01
STAKE_DAYS = 30
#: What a stake fetches sold back to the house, as a share of its price.
SELL_BACK = 0.8
#: Every how many days a stakeholder's statement is sent.
STATEMENT_DAYS = 90

#: The odds a system with a dead hull adrift in it has breakers working
#: there — the wreck is why they came.
BREAKERS_ODDS = 0.6

#: How many a system has: the odds of one, of a second, and of a third,
#: by whether it has a starport and whether that port is a capital.
ODDS = {"none": (0.30, 0.08, 0.0), "port": (0.65, 0.30, 0.08),
        "capital": (0.95, 0.70, 0.40)}
