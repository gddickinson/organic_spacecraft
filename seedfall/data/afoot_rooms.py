"""What a room is: how big, what stands in it, and who works there.

A deck plan is laid out from a list of rooms (`sim/afoot_plans.py`), and the
list is read off what the site already is. **A concourse's rooms are its
open doors** — the fifteen kinds of venue in `data/venue_types.py` each have
a room kind here with the same id — so a class-A capital has an opera house
and a bank to walk into, and a frontier rock has a shed, a bunkroom and a
chop shop, for exactly the reasons its concourse board lists them. **A
hull's rooms are its fittings and its complement**: a bridge, berths for the
crew it carries, a hold as big as its cargo, a room for each drive, core and
gun it has fitted.

Furniture is stamped from `kit`: `(thing kind, least, most, where)`, where
*where* is one of

- `back` — along the wall opposite the door (a counter, a bank of consoles);
- `walls` — against the side walls (beds, lockers, racks);
- `centre` — in the middle (machinery, a relic);
- `scatter` — anywhere the floor allows (tables, crates);
- `corners` — in the corners (pillars, strongboxes).

`staff` stand at the back of the room and keep station; `crowd` wanders in
it. Both are archetype ids in `data/afoot_folk.py`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoomKind:
    """One sort of room."""

    id: str
    name: str
    #: Interior width and height, least and most, in squares.
    size: tuple
    kit: tuple = ()
    staff: tuple = ()
    crowd: str = ""
    crowd_most: int = 0
    #: What its lockers and crates hold (`LOOT`).
    loot: str = ""
    tint: str = "dim"


def _k(rid, name, w, h, kit=(), staff=(), crowd="", most=0, loot="",
       tint="dim"):
    return RoomKind(rid, name, (w[0], w[1], h[0], h[1]), tuple(kit),
                    tuple(staff), crowd, most, loot, tint)


ROOMS: tuple = (
    # ── the concourse: one per kind of venue (`data/venue_types.KINDS`) ────
    _k("chandler", "Chandlery", (7, 10), (5, 6),
       [("counter", 1, 1, "back"), ("rack", 2, 4, "walls"),
        ("locker", 0, 1, "corners")], ("keeper",), "patron", 2, "shop",
       "steel"),
    _k("market", "Market", (8, 12), (6, 7),
       [("table", 3, 5, "scatter"), ("counter", 1, 1, "back")],
       ("keeper",), "patron", 4, "shop", "osteo"),
    _k("tech", "Tech shop", (7, 9), (5, 6),
       [("counter", 1, 1, "back"), ("bench", 1, 2, "walls"),
        ("console", 1, 1, "walls")], ("keeper",), "patron", 1, "tech",
       "lumen"),
    _k("bank", "Counting house", (7, 9), (5, 6),
       [("counter", 1, 1, "back"), ("strongbox", 1, 2, "corners"),
        ("console", 1, 1, "walls")], ("clerk",), "patron", 1, "office",
       "osteo"),
    _k("office", "Office", (7, 10), (5, 6),
       [("desk", 2, 3, "scatter"), ("console", 1, 1, "walls")],
       ("clerk",), "patron", 1, "office", "steel"),
    _k("law", "Law office", (8, 10), (6, 6),
       [("desk", 2, 2, "scatter"), ("console", 1, 1, "walls"),
        ("locker", 1, 1, "corners")], ("clerk",), "", 0, "evidence", "warn"),
    _k("transport", "Transit hall", (8, 12), (5, 6),
       [("table", 1, 3, "scatter"), ("counter", 1, 1, "back")],
       ("clerk",), "patron", 3, "", "steel"),
    _k("lodging", "Lodging", (8, 11), (6, 7),
       [("bed", 3, 6, "walls"), ("counter", 1, 1, "back"),
        ("locker", 1, 2, "corners")], ("keeper",), "patron", 1, "home",
       "chloro"),
    _k("eatery", "Eating house", (8, 12), (6, 7),
       [("counter", 1, 1, "back"), ("table", 3, 5, "scatter")],
       ("keeper",), "patron", 4, "", "osteo"),
    _k("clinic", "Clinic", (8, 10), (6, 6),
       [("medbed", 2, 4, "walls"), ("counter", 1, 1, "back"),
        ("locker", 1, 1, "corners")], ("clinician",), "patron", 1,
       "medical", "lumen"),
    _k("sport", "Sports hall", (9, 12), (7, 7),
       [("bench", 1, 2, "walls"), ("pillar", 0, 2, "corners")],
       (), "patron", 4, "", "chloro"),
    _k("arts", "Hall", (10, 13), (7, 7),
       [("table", 2, 4, "scatter"), ("pillar", 2, 2, "corners")],
       ("keeper",), "patron", 4, "", "xeno"),
    _k("entertainment", "House", (9, 12), (7, 7),
       [("counter", 1, 1, "back"), ("table", 3, 5, "scatter")],
       ("keeper",), "patron", 5, "", "xeno"),
    _k("temple", "House of the Orders", (8, 10), (7, 7),
       [("bench", 2, 4, "scatter"), ("pillar", 2, 2, "corners")],
       ("keeper",), "patron", 2, "", "ink"),
    _k("vice", "Back room", (7, 9), (6, 6),
       [("counter", 1, 1, "back"), ("table", 1, 2, "scatter"),
        ("strongbox", 1, 1, "corners")], ("fence",), "thug", 2, "vice",
       "warn"),
    # ── a hull ─────────────────────────────────────────────────────────────
    _k("bridge", "Bridge", (7, 9), (5, 5),
       [("console", 3, 4, "back"), ("console", 1, 2, "walls")], (), "", 0,
       "", "lumen"),
    _k("quarters", "Berths", (7, 10), (5, 6),
       [("bed", 3, 6, "walls"), ("locker", 1, 3, "corners")], (), "", 0,
       "home", "dim"),
    _k("engineering", "Engineering", (8, 11), (6, 6),
       [("machinery", 2, 3, "centre"), ("console", 1, 1, "walls")], (), "",
       0, "tools", "osteo"),
    _k("drive", "Drive room", (7, 9), (5, 5),
       [("machinery", 2, 2, "centre"), ("console", 1, 1, "walls")], (), "",
       0, "tools", "osteo"),
    _k("power", "Power plant", (6, 8), (5, 5),
       [("machinery", 1, 2, "centre")], (), "", 0, "tools", "osteo"),
    _k("sensors", "Sensor gallery", (6, 8), (5, 5),
       [("console", 2, 2, "walls"), ("bench", 1, 1, "back")], (), "", 0,
       "tech", "lumen"),
    _k("core", "Core room", (6, 7), (5, 5),
       [("console", 2, 3, "walls"), ("machinery", 1, 1, "centre")], (), "",
       0, "tech", "lumen"),
    _k("weapons", "Gun deck", (7, 9), (5, 5),
       [("rack", 1, 2, "walls"), ("locker", 1, 2, "corners"),
        ("machinery", 1, 1, "centre")], (), "", 0, "armoury", "warn"),
    _k("hold", "Hold", (10, 14), (6, 8),
       [("cargo", 2, 5, "scatter"), ("crate", 2, 4, "scatter")], (), "", 0,
       "hold", "osteo"),
    _k("lab", "Laboratory", (8, 10), (6, 6),
       [("bench", 2, 4, "walls"), ("console", 1, 1, "back")], (), "", 0,
       "lab", "lumen"),
    _k("airlock", "Airlock", (4, 5), (4, 4),
       [("locker", 1, 1, "walls")], (), "", 0, "suits", "lumen"),
    _k("cabin", "Master's cabin", (6, 8), (5, 5),
       [("bed", 1, 1, "walls"), ("desk", 1, 1, "scatter"),
        ("strongbox", 1, 1, "corners")], (), "", 0, "cabin", "osteo"),
    _k("utility", "Plant space", (6, 8), (5, 5),
       [("machinery", 1, 2, "centre"), ("crate", 0, 2, "scatter")], (), "",
       0, "tools", "dim"),
    # ── a station, a drum, a holding ───────────────────────────────────────
    _k("docks", "Docks", (12, 16), (7, 8),
       [("crate", 3, 6, "scatter"), ("cargo", 2, 3, "scatter"),
        ("pillar", 2, 2, "corners")], (), "dockhand", 4, "hold", "osteo"),
    _k("customs", "Customs hall", (7, 9), (5, 5),
       [("desk", 1, 2, "back"), ("console", 1, 1, "walls"),
        ("locker", 1, 1, "corners")], ("customs",), "", 0, "evidence",
       "warn"),
    _k("harbour", "Harbour office", (7, 8), (5, 5),
       [("desk", 1, 1, "back"), ("console", 1, 1, "walls")],
       ("harbourmaster",), "", 0, "office", "steel"),
    _k("admin", "Administration", (8, 10), (6, 6),
       [("desk", 2, 4, "scatter"), ("console", 1, 2, "walls")],
       ("clerk",), "", 0, "office", "steel"),
    _k("cells", "Cells", (6, 8), (5, 5),
       [("bed", 2, 2, "walls")], ("constable",), "", 0, "", "warn"),
    _k("park", "Park", (10, 14), (7, 8),
       [("plant", 4, 8, "scatter"), ("bench", 1, 2, "walls")], (),
       "resident", 4, "", "chloro"),
    _k("homes", "Residences", (7, 9), (5, 6),
       [("bed", 1, 2, "walls"), ("table", 1, 1, "scatter"),
        ("locker", 1, 1, "corners")], (), "resident", 2, "home", "dim"),
    _k("works", "Works floor", (10, 13), (7, 7),
       [("machinery", 2, 4, "centre"), ("console", 1, 1, "walls"),
        ("crate", 1, 2, "scatter")], ("overseer",), "worker", 3, "tools",
       "osteo"),
    _k("bunkhouse", "Bunkhouse", (8, 10), (6, 6),
       [("bed", 4, 6, "walls"), ("locker", 1, 2, "corners"),
        ("table", 1, 1, "scatter")], (), "worker", 2, "home", "dim"),
    _k("store", "Storeroom", (6, 8), (5, 5),
       [("crate", 2, 4, "scatter"), ("locker", 1, 1, "corners")], (), "", 0,
       "tools", "dim"),
    # ── the dead and the strange ───────────────────────────────────────────
    _k("vault", "Relic vault", (7, 9), (6, 6),
       [("relic", 1, 1, "centre"), ("pillar", 2, 4, "corners"),
        ("console", 0, 1, "walls")], (), "", 0, "", "xeno"),
    _k("nest", "Bloom heart", (8, 10), (7, 7),
       [("spore_node", 1, 1, "centre"), ("spores", 3, 6, "scatter")], (),
       "", 0, "", "warn"),
    _k("song_hall", "Singing hall", (10, 13), (7, 8),
       [("plant", 3, 6, "scatter"), ("pillar", 2, 2, "corners")],
       ("kith_elder",), "kith", 4, "", "xeno"),
)

#: Venues whose room is staffed by somebody other than the kind's usual
#: hand: a hiring hall has an agent at the desk, a constabulary a constable.
VENUE_STAFF = {
    "hiring_hall": ("agent",), "crew_agency": ("agent",),
    "hiring_stone": ("agent",), "constabulary": ("constable",),
    "fence": ("fence",), "den": ("fence",), "smugglers_rest": ("fence",),
    "black_clinic": ("clinician",), "chop_shop": ("clinician",),
    "kith_gathering": ("kith_elder",), "kith_table": ("kith_elder",),
    "data_haven": ("informant",), "fight_pit": ("keeper",),
    "blood_pit": ("keeper",),
}

#: Which room a fitted part puts aboard, by slot and then by id. A defence
#: slot is armour in the hull wall and makes no room of its own.
SLOT_ROOM = {"drive": "drive", "power": "power", "sensor": "sensors",
             "compute": "core", "weapon": "weapons"}
UTILITY_ROOM = {
    "cargo_villi": "hold", "cryo_hold": "hold", "void_hold": "hold",
    "crew_girdle": "quarters", "torpor_gland": "quarters",
    "polyp_lab": "lab", "seed_bay": "lab", "chorus_node": "core",
    "mining_root": "works", "ore_crusher": "works", "smelter_bay": "works",
    "separation_gut": "works", "harvest_tendril": "works",
    "melt_head": "works", "drydock_arm": "works", "siphon_bell": "works",
}

#: What a room's containers hold, by the loot id on its kind: which
#: `data/kit.py` categories are drawn, and how many tries a container gets.
LOOT = {
    "shop": (("tool", "survey", "suit", "comp"), 1),
    "tech": (("comp", "tool"), 1),
    "office": (("paper", "comp", "luxury"), 1),
    "evidence": (("weapon", "illicit", "paper"), 2),
    "home": (("luxury", "keepsake", "comp", "medical"), 1),
    "medical": (("medical",), 2),
    "vice": (("illicit", "weapon", "paper"), 2),
    "tools": (("tool",), 1),
    "armoury": (("weapon", "armour"), 2),
    "hold": (("travel", "tool", "suit"), 1),
    "lab": (("survey", "medical"), 1),
    "suits": (("suit",), 1),
    "cabin": (("luxury", "paper", "weapon", "keepsake"), 2),
}


# The rooms a working hull and a working station are made of, and the ones
# people pay for, live in `data/afoot_rooms_more.py` (split at the length
# rule), and are one table with these.
from .afoot_rooms_more import MORE  # noqa: E402

ROOMS = ROOMS + MORE
ROOM_BY_ID = {r.id: r for r in ROOMS}
