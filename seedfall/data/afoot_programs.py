"""What a working ship or station has to have room for.

A hull is not a list of fittings with corridors between them. Before it can
fly with anybody in it, it needs somewhere to fly it from, somewhere to
sleep, eat and wash, air to breathe and water to drink, somewhere to keep
the reaction mass, the stores and the cargo, a way in and a way out in a
hurry — and then whatever its role is on top. `sim/afoot_program.py` reads
these tables with a chassis's own crew, cargo, family and fitted parts and
writes the **program**: every space, sized, and where along the hull it
belongs. The deck plan is laid out from the program; if the hull's outline
cannot hold it, the design grows another deck rather than leaving a space
out.

Zones are positions along the hull's axis, **bow +1 to stern −1**, which is
the frame `data/hullforms.py` mounts every fitting in: the sensors are at
+1.0 on a grown hull because that is where its eye is, the drive at −1.02
because that is where it pushes from.
"""

from __future__ import annotations

#: Where along the axis each sort of space belongs, when nothing more
#: specific says (a fitting's own mount does, `hullforms.FORMS`).
ZONE = {
    "bridge": 0.78, "command": 0.70, "sensors": 0.95, "core": 0.40,
    "cabin": 0.45, "officers": 0.35, "quarters": 0.12, "galley": 0.05,
    "heads": 0.0, "clinic": -0.05, "gym": 0.18, "library": 0.22,
    "lifesupport": -0.10, "reclaim": -0.30, "store": -0.38,
    "workshop": -0.50, "power": -0.45, "drive": -0.92, "tanks": -0.72,
    "hold": -0.35, "magazine": 0.52, "weapons": 0.30, "airlock": 0.0,
    "pods": -0.15, "lab": 0.25, "works": -0.60, "lounge": 0.30,
    "suites": 0.10, "dining": 0.20, "wards": -0.02, "surgery": 0.08,
    "dormitory": 0.0, "hangar": -0.25, "farm": -0.20, "vault": 0.10,
    "barracks": 0.28, "cold": -0.05, "brig": 0.40, "chapel": 0.15,
}

#: What one space of each sort takes, in squares of floor, before the crew
#: or the cargo scale it. A cabin is three squares by three; a galley is a
#: table and a range.
AREA = {
    "bridge": 6, "command": 12, "sensors": 6, "core": 6, "cabin": 8,
    "officers": 10, "galley": 8, "heads": 4, "clinic": 8, "gym": 12,
    "library": 10, "lifesupport": 8, "reclaim": 6, "store": 6,
    "workshop": 8, "power": 8, "drive": 10, "tanks": 8, "hold": 12,
    "magazine": 6, "weapons": 5, "airlock": 5, "pods": 6, "lab": 10,
    "works": 12, "lounge": 14, "suites": 16, "dining": 14, "wards": 16,
    "surgery": 10, "dormitory": 24, "hangar": 24, "farm": 20, "vault": 12,
    "barracks": 16, "cold": 16, "brig": 6, "chapel": 8,
}

#: The weight in a Habitat Girdle's spun berths, in gravities — the card's
#: own "four-tenths of a gravity". The rest of a hull is weightless.
GIRDLE_G = 0.4

#: Squares of berth per person aboard, and the most one berthing room takes
#: before a second is opened. Bunks two high.
BERTH_PER_HEAD = 1.1
BERTHS_MOST = 28

#: How a life-support plant is built, by family: a grown hull breathes
#: through its intima, a welded one through scrubbers, a Dry Choir frame has
#: nothing to breathe and cools its substrate instead, a xeno hull lets
#: something in its walls do it.
AIR_PLANT = {"grown": ("lifesupport", "Intima gallery"),
             "hybrid": ("lifesupport", "Intima and scrubbers"),
             "fabricated": ("lifesupport", "Air plant"),
             "synthetic": ("lifesupport", "Coolant plant"),
             "xeno": ("lifesupport", "Symbiont gallery")}

#: What a role adds on top of a working ship, by chassis tier. Each row is
#: (kind, name, count, area, zone or None). The tiers are the cards' own.
ROLE = {
    "Pod": (("cold", "Torpor gland", 1, 4, -0.1),),
    "Sentinel": (("sensors", "Dish gallery", 1, 10, -0.6),),
    "Uncrewed": (("works", "Root chamber", 1, 14, -0.95),
                 ("works", "Ore gut", 1, 12, -0.55),
                 ("lab", "Seed foundry", 1, 12, -0.25)),
    "Harvester": (("works", "Harvest bell", 1, 16, -0.85),
                  ("works", "Volatile still", 1, 10, -0.5)),
    "Freighter": (("hold", "Hold module", 2, 20, None),),
    "Guardian": (("magazine", "Carapace stores", 1, 8, 0.2),),
    "Research": (("lab", "Laboratory", 2, 12, None),
                 ("sensors", "Instrument bay", 1, 10, 0.7)),
    "Survey": (("lab", "Survey laboratory", 1, 12, None),
               ("sensors", "Instrument bay", 1, 12, 0.7)),
    "Diver": (("works", "Pressure lock", 1, 8, -0.2),
              ("hangar", "Submersible bay", 1, 14, -0.55)),
    "Liner": (("suites", "Passenger cabins", 3, 22, None),
              ("lounge", "Passenger lounge", 1, 18, 0.3),
              ("dining", "Dining saloon", 1, 16, 0.18)),
    "Vault": (("vault", "Archive vault", 2, 16, None),),
    "Ark": (("dormitory", "Habitation ring", 3, 30, None),
            ("farm", "Growing deck", 2, 30, None),
            ("chapel", "The quiet room", 1, 10, 0.1),
            ("library", "The school", 1, 14, 0.2)),
    "Tug": (("workshop", "Repair shop", 1, 16, -0.3),
            ("works", "Tow winch", 1, 8, -0.9)),
    "Courier": (("store", "Mail hold", 1, 6, -0.4),),
    "Runner": (("hold", "Hidden hold", 1, 8, -0.5),),
    "Corvette": (("barracks", "Marines' berth", 1, 10, 0.3),
                 ("brig", "Brig", 1, 5, 0.4)),
    "Industrial": (("works", "Refinery hall", 2, 18, -0.4),
                   ("hold", "Ore bunker", 1, 18, -0.6)),
    "Hospital": (("wards", "Ward", 3, 20, None),
                 ("surgery", "Operating theatre", 2, 10, 0.1),
                 ("lab", "Pharmacy", 1, 8, 0.2)),
    "Cruiser": (("command", "Combat information centre", 1, 10, 0.55),
                ("barracks", "Marines' berth", 1, 12, 0.3)),
    "Destroyer": (("command", "Combat information centre", 1, 10, 0.55),
                  ("magazine", "Missile magazine", 1, 12, 0.4)),
    "Monitor": (("command", "Combat information centre", 1, 12, 0.5),
                ("magazine", "Main magazine", 2, 10, 0.35)),
    "Siege": (("command", "Fire direction centre", 1, 12, 0.5),
              ("magazine", "Shell room", 2, 12, 0.35)),
    "Battleship": (("command", "Combat information centre", 1, 14, 0.5),
                   ("magazine", "Main magazine", 2, 12, 0.35),
                   ("barracks", "Marine barracks", 1, 18, 0.25)),
    "Dreadnought": (("command", "Flag bridge", 1, 14, 0.6),
                    ("magazine", "Main magazine", 2, 12, 0.35),
                    ("barracks", "Marine barracks", 1, 18, 0.25)),
    "Skiff": (("works", "Cutting bay", 1, 10, -0.5),),
    "Breaker": (("works", "Breaking bay", 2, 20, -0.4),
                ("hold", "Scrap hold", 1, 20, -0.6)),
    "Cutter": (("hold", "Trade hold", 1, 14, -0.4),
               ("brig", "Strongroom", 1, 5, 0.3)),
    "Probe": (),
    "Carrier": (("hangar", "Drone hangar", 2, 26, -0.2),
                ("workshop", "Drone shop", 1, 12, -0.4)),
    "Capital": (("core", "Analysis vault", 2, 12, 0.3),),
    "Derelict": (("vault", "Sealed chamber", 1, 10, 0.1),),
    "Drifter": (("lounge", "Singing chamber", 1, 10, 0.2),),
    "Colony": (("lounge", "Singing hall", 1, 20, 0.1),
               ("farm", "Light garden", 1, 18, -0.2)),
}

#: What every inhabited structure needs whatever else it is: somewhere it
#: is run from, air, power, water, stores, a way to mend it, and somewhere
#: for the people who keep it running to sleep and eat.
STATION_CORE = (("command", "Station control", 1, 12),
                ("lifesupport", "Life support", 1, 10),
                ("power", "Power plant", 1, 10),
                ("reclaim", "Water reclamation", 1, 8),
                ("store", "Stores", 1, 8),
                ("workshop", "Maintenance", 1, 8))

#: What each of `works3d`'s structural traits is, as a working space: a
#: holding with roots has a drill hall, one with a bell a condenser. The
#: trait vocabulary is `data/works3d.traits_of`'s; every trait it can emit
#: has a row, and a check holds the two together.
TRAIT_SPACE = {
    "roots": (("works", "Drill hall", 1, 16), ("works", "Ore sorting", 1, 10)),
    "bell": (("works", "Condenser bell", 1, 16),),
    "scoop": (("works", "Intake hall", 1, 14),),
    "stacks": (("fabhall", "Fabrication hall", 1, 20),
               ("works", "Smelter floor", 1, 16)),
    "fronds": (("farm", "Light gallery", 2, 18),),
    "dish": (("sensors", "Dish control", 1, 10),),
    "masts": (("sensors", "Mast room", 2, 6),),
    "vault": (("vault", "The vault", 1, 18),),
    "guns": (("weapons", "Battery", 2, 8), ("magazine", "Magazine", 1, 8)),
    "bunker": (("barracks", "Barracks", 1, 18), ("brig", "The cells", 1, 6)),
    "vanes": (("works", "Vane control", 1, 8),),
    "wards": (("wards", "Ward block", 3, 18), ("surgery", "Theatre", 1, 10)),
    "bay": (("clinic", "Sickbay", 1, 10),),
    "womb": (("works", "Gestation womb", 1, 26),),
    "cradle": (("slipway", "Slipway", 1, 30),
               ("workshop", "Yard shop", 1, 12)),
    "arm": (("airlock", "Docking lock", 1, 6),),
    "gantry": (("airlock", "Boom lock", 1, 6),),
    "shards": (("vault", "Resonant chamber", 2, 12),),
    "mirror": (("works", "Collector control", 1, 12),),
    "dome": (("park", "The dome", 1, 30),),
    "drum": (("park", "The green", 1, 30),),
    "tower": (("park", "Sky garden", 1, 16),),
    "ring": (("park", "Promenade garden", 1, 14),),
    "quarters": (("quarters", "Quarters", 1, 14),),
}
