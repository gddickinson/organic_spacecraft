"""The Assembly — what the four powers table when they sit, and how often.

The powers never met. Their interests collided only in private — a venture, a
blockade, a treaty with the captain — and nothing a captain with standing could
do moved more than one pair at a time. A sector council gives the collision a
room: every season the four sit at a capital in turn, two or three instruments
are tabled, and each power votes its interest in public.

**Every effect is a key in a closed vocabulary (`EFFECTS`), and every key is
read at one line by the system it names.** A resolution that changed nothing
anybody computes would be a speech. `tests/test_assembly` switches each key off
and measures its reader's number move.

How to add a resolution:

1. Add a row to `RESOLUTIONS`: the stances come from each power's creed and
   doctrine (`data/factions`), and `effects` may use only keys in `EFFECTS`.
2. A new effect key also needs its `EFFECTS` row and **one line in the system
   that obeys it**, reading `sim/assembly.effect(game, key, default)`.
3. Add its reader to `tests/assembly_probes.READERS`, which is the efficacy
   probe; `tests/test_assembly` refuses a key without one.

Two are waiting on other work, and slot in exactly that way: a **Bounty
Compact** (`bounty`, read where `sim/contracts` prices a bounty, once the
nemeses land) and a **Deep Gate Moratorium** (`deep_gates`, read where the
Far Reaches decide whether a deep gate may be lit).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Days between sittings, and the seeded jitter either side of it.
SESSION_DAYS = 90
SESSION_JITTER = 10
#: How long before a sitting the clerk publishes its agenda.
NOTICE_DAYS = 30
#: How long a passed resolution binds, in days.
TERM_DAYS = 180
#: Instruments tabled at one sitting, fewest and most.
TABLED = (2, 3)
#: The seat rotates through the capitals in this order.
SEAT_ORDER = ("charter", "concordat", "freeholds", "sanhedrin")


@dataclass(frozen=True)
class Effect:
    """One key of the vocabulary, and how two instruments setting it combine.
    The comment on each row is the one line that obeys it."""
    key: str
    #: "mul" multiplies, "add" sums, "any" is a flag, "set" a union of names,
    #: "floor" keeps the highest. Per-system values ("lawless") multiply per
    #: system.
    combine: str
    #: What `sim/assembly.effect` answers with nothing in force, when the
    #: reader names no default of its own.
    default: object


EFFECTS: dict[str, Effect] = {e.key: e for e in [
    Effect("wharfage", "mul", 1.0),        # sim/wharfage.rate
    Effect("tithe", "add", 0.0),           # sim/exchequer._books
    Effect("containment", "add", 0.0),     # sim/ventures.odds
    Effect("amnesty", "any", 0.0),         # sim/enforce.may_seed, customs.aboard
    Effect("embargo", "set", ()),          # sim/trade.sell
    Effect("ceasefire", "set", ()),        # sim/war.at_war
    Effect("commons", "add", 0.0),         # sim/trade.sell_survey_data
    Effect("salvage_tax", "add", 0.0),     # sim/aftermath._salvage
    Effect("choir_floor", "floor", None),  # sim/assembly.hold
    Effect("lawless", "mul", {}),          # sim/piracy.lawlessness
    Effect("founding", "add", 0.0),        # sim/colony.found
    Effect("repairs", "mul", 1.0),         # sim/services.repair_quote
    Effect("border", "set", ()),           # sim/war.spoils
    Effect("search", "mul", 1.0),          # sim/customs.chance
    Effect("tolls", "mul", 1.0),           # sim/gates.toll
]}


@dataclass(frozen=True)
class Resolution:
    """An instrument the Assembly can table.

    `stance` is each power's interest before anything else is counted, in
    vote points, from its creed and doctrine; `why` is the clause that says
    so, and is what the forecast prints. `shape` says what the instrument
    names: "" nothing, "power" one power (an embargo), "pair" two (a
    ceasefire), "lanes" or "unclaimed" a set of systems.
    """
    id: str
    name: str
    text: str
    plain: str
    effects: dict
    stance: dict
    why: dict
    shape: str = ""
    #: Commodities it puts in somebody's hands; a power whose agenda wants
    #: one leans for it.
    feeds: tuple = ()
    #: What it costs a purse, in points at an empty treasury. Negative pays.
    costs: float = 0.0
    #: "bloom", "war" or "smuggling": the sector state that tables it.
    pressure: str = ""
    weight: float = 1.0
    #: For a "pair" or "power" instrument, what the named parties feel about
    #: being named, in place of their creed.
    party: float = 0.0
    term: int = TERM_DAYS
    tint: str = "lumen"
    #: What passing it does once, on the day: "shift" moves a named pair by
    #: an amount, "lift" raises the named pair's relation to a floor.
    extra: dict = field(default_factory=dict)


RESOLUTIONS: list[Resolution] = [
    Resolution(
        "bloom_levy", "Bloom Levy",
        "Every power tithes a share of its port income to a common containment "
        "fund, and every quay adds a surcharge to its due to pay for it.",
        "the powers tithe 5% of port income to containment; their containment "
        "flotillas gain 15 points of odds; every due rises by a twentieth",
        {"tithe": 0.05, "containment": 0.15, "wharfage": 1.05},
        {"charter": 4.0, "concordat": 1.5, "freeholds": -1.0, "sanhedrin": 1.0},
        {"charter": "the containment regime is theirs",
         "concordat": "a hull that can grow can grow wrong",
         "freeholds": "a tithe is a tax on the margin",
         "sanhedrin": "the Bloom eats substrate too"},
        costs=1.0, pressure="bloom", weight=1.2, tint="warn"),
    Resolution(
        "open_quays", "Open Quays",
        "Every quay in the Verge halves its due for the term.",
        "wharfage halved at every quay",
        {"wharfage": 0.5},
        {"charter": 0.5, "concordat": -3.0, "freeholds": 4.0, "sanhedrin": 3.0},
        {"charter": "trade feeds the programme",
         "concordat": "eleven yards live off their berths",
         "freeholds": "whatever flies, flies for us",
         "sanhedrin": "recordings travel on cheap hulls"},
        costs=0.5, tint="lumen"),
    Resolution(
        "amnesty", "Licence Amnesty",
        "For the term, no seed put in the ground is asked for its licence, and "
        "no hold is searched for seed.",
        "unlicensed seeding is legal; seed is not seized at any dock",
        {"amnesty": 1.0},
        {"charter": -6.0, "concordat": -1.0, "freeholds": 5.0, "sanhedrin": 0.5},
        {"charter": "no seed germinates unbidden",
         "concordat": "nothing aboard that can make more of itself",
         "freeholds": "the licence is a piece of paper",
         "sanhedrin": "substrate is an implementation detail"},
        weight=0.4, tint="osteo"),
    Resolution(
        "embargo", "Embargo on the {power}",
        "No power's quay buys the goods the {power} export until the term is "
        "out.",
        "the {power}'s exports cannot be sold at any other power's counter",
        {"embargo": "power"},
        {"charter": 0.5, "concordat": 0.5, "freeholds": 0.5, "sanhedrin": 0.5},
        {"charter": "an instrument they can sign",
         "concordat": "leverage, which the Yards understand",
         "freeholds": "somebody else's margin",
         "sanhedrin": "a lesson about dependence"},
        shape="power", party=-8.0, weight=0.3, tint="warn"),
    Resolution(
        "ceasefire", "Ceasefire between the {a} and the {b}",
        "Neither the {a} nor the {b} moves hulls against the other for the "
        "term, and the grievance between them is set back to where a truce "
        "can hold.",
        "no war between the {a} and the {b} for the term; their relation is "
        "raised to -40 when it passes",
        {"ceasefire": "pair"},
        {"charter": 3.0, "concordat": 3.0, "freeholds": 3.0, "sanhedrin": 3.0},
        {"charter": "no hull carries a weapon",
         "concordat": "a war nobody wins is bad for the order book",
         "freeholds": "wars close markets",
         "sanhedrin": "the dead record nothing"},
        shape="pair", party=-3.0, costs=-2.5, pressure="war", weight=0.0,
        tint="chloro", extra={"lift": -40.0}),
    Resolution(
        "commons", "Research Commons",
        "Survey data sold at any counter is copied to the seller's own bench.",
        "every survey set you sell also puts 4 survey evidence on your bench",
        {"commons": 4.0},
        {"charter": 3.0, "concordat": -1.0, "freeholds": 0.5, "sanhedrin": 4.0},
        {"charter": "the programme was always a science",
         "concordat": "their tables are sold, not shared",
         "freeholds": "information is margin",
         "sanhedrin": "recordings, of anything"},
        feeds=("survey",), tint="lumen"),
    Resolution(
        "salvage_law", "Salvage Law",
        "What is taken from a destroyed hull is taxed by whoever holds the "
        "space it died in.",
        "the local power takes 30% of what salvage is worth, in credits",
        {"salvage_tax": 0.30},
        {"charter": 3.0, "concordat": 3.0, "freeholds": -1.0, "sanhedrin": -1.0},
        {"charter": "a wreck is a hull somebody armed",
         "concordat": "wrecks are Yards frames",
         "freeholds": "salvage is half their trade",
         "sanhedrin": "a wreck's core is a recording they buy"},
        costs=-1.0, tint="steel"),
    Resolution(
        "recognition", "Charter Recognition of the Choir",
        "The Charter recognises the Dry Choir as a power of the Verge with a "
        "standing of its own, and the two exchange envoys.",
        "your standing with the Dry Choir cannot fall below -10; the Charter "
        "and the Choir move 15 closer when it passes",
        {"choir_floor": -10.0},
        {"charter": -1.0, "concordat": 3.0, "freeholds": 1.0, "sanhedrin": 6.0},
        {"charter": "one biology, many bodies",
         "concordat": "a machine that cannot grow is safe",
         "freeholds": "another buyer",
         "sanhedrin": "we are the stone"},
        weight=0.8, tint="xeno", extra={"shift": ("charter", "sanhedrin", 15.0)}),
    Resolution(
        "convoy", "Convoy Escort Mandate",
        "Every power escorts traffic on the lanes between the four capitals.",
        "lawlessness a quarter lower on the {n} systems of the capital lanes",
        {"lawless": 0.75},
        {"charter": 1.0, "concordat": 4.0, "freeholds": -0.5, "sanhedrin": 1.0},
        {"charter": "escorts are hulls that carry weapons",
         "concordat": "they will sell anyone a battleship",
         "freeholds": "raiders feed their fences, convoys buy from them",
         "sanhedrin": "safe lanes carry more recordings"},
        shape="lanes", costs=0.5, tint="steel"),
    Resolution(
        "privateers", "Privateer Licences",
        "Any hull may take cargo in space no power claims, on a letter from "
        "any power.",
        "lawlessness a quarter higher on the {n} systems nobody claims",
        {"lawless": 1.25},
        {"charter": -3.5, "concordat": -3.0, "freeholds": 5.0, "sanhedrin": -1.0},
        {"charter": "no hull carries a weapon",
         "concordat": "their frames are what gets taken",
         "freeholds": "whatever flies, flies for us",
         "sanhedrin": "disorder spoils the data"},
        shape="unclaimed", costs=-1.0, weight=0.3, tint="warn"),
    Resolution(
        "colony_charter", "Colony Charter",
        "A holding founded in space no power claims is part-funded by the "
        "Assembly.",
        "a fifth of what a holding costs comes back, if nobody claims the "
        "system",
        {"founding": 0.20},
        {"charter": 4.0, "concordat": 0.0, "freeholds": 3.0, "sanhedrin": -1.0},
        {"charter": "one biology, many bodies",
         "concordat": "somebody else's ground",
         "freeholds": "every holding is a customer",
         "sanhedrin": "one biology is not their creed"},
        costs=0.5, tint="chloro"),
    Resolution(
        "harbour_dues", "Harbour Dues Reform",
        "Drydock charges are capped by the Assembly at every quay.",
        "repairs 15% cheaper at every drydock",
        {"repairs": 0.85},
        {"charter": 1.0, "concordat": -1.0, "freeholds": 4.0, "sanhedrin": 3.0},
        {"charter": "a mended hull is not a new germination",
         "concordat": "the yards bill for the torch",
         "freeholds": "cheap berths fill",
         "sanhedrin": "indifferent to plate"},
        costs=0.5, tint="lumen"),
    Resolution(
        "border", "Border Treaty between the {a} and the {b}",
        "Neither the {a} nor the {b} annexes ground the other holds, whatever "
        "else passes between them.",
        "no system changes hands between the {a} and the {b}",
        {"border": "pair"},
        {"charter": 1.0, "concordat": 1.0, "freeholds": 1.0, "sanhedrin": 1.0},
        {"charter": "a register is a promise",
         "concordat": "fixed lines are good for planning",
         "freeholds": "borders are paper",
         "sanhedrin": "stable states record better"},
        shape="pair", party=3.0, weight=0.0, tint="steel"),
    Resolution(
        "contraband", "Contraband Accord",
        "The powers share their manifests: a hold searched anywhere is known "
        "everywhere.",
        "customs search odds half again as high at every dock that looks",
        {"search": 1.5},
        {"charter": 4.0, "concordat": 3.0, "freeholds": -4.0, "sanhedrin": -1.0},
        {"charter": "the licence must be unforgeable",
         "concordat": "nothing that can make more of itself",
         "freeholds": "we can do paper",
         "sanhedrin": "wet law, for wet cargo"},
        pressure="smuggling", weight=0.5, tint="warn"),
    Resolution(
        "free_passage", "Free Passage",
        "The rings of the Weave open to every hull at half the toll.",
        "Weave tolls halved",
        {"tolls": 0.5},
        {"charter": -1.0, "concordat": 1.0, "freeholds": 4.0, "sanhedrin": 3.0},
        {"charter": "a toll is what a licence costs",
         "concordat": "a toll is a cost of doing business",
         "freeholds": "margin moves on cheap transit",
         "sanhedrin": "recordings cross the Weave"},
        costs=0.5, tint="lumen"),
]

RESOLUTIONS_BY_ID: dict[str, Resolution] = {r.id: r for r in RESOLUTIONS}
