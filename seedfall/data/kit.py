"""Everything a person can own, carry, be refused at a customs desk, or lose.

The ship has had a hold since the first commit and nobody aboard has ever
owned anything. A captain with forty thousand credits could not buy a coat.

This is the catalogue: about a hundred and thirty things, in twelve
categories, each with a price, a tech level, and a law level above which a
port will take it off you. **Both of those hook into the world profile that
already exists** — `data/uwp.py` gives every world a tech level and a law
level, so what is on the shelves and what is contraband is a property of
*where you are standing* rather than a shop's inventory list. A railgun is
ordinary at law 2 and four years in a cell at law 9, and the same table says
both.

Five things every entry has:

- **`tl`** — the tech level that can make it. A world below it does not stock
  it, and one well above it sells it cheap.
- **`law`** — the law level at which it becomes contraband. Zero means
  nobody minds; ten means only the Bloom would not care.
- **`cr`** — the price in credits at a routine port, before anything.
- **`mass`** — kilograms, because a person can carry about thirty of them.
- **`gives`** — the skill it helps with, where it helps with one. A toolkit
  is not a decoration.
"""

from __future__ import annotations

from dataclasses import dataclass

#: The categories, in the order a chandler's board lists them.
CATEGORIES = (
    ("weapon", "Weapons", "things that are meant to hurt somebody"),
    ("armour", "Armour", "things that are meant to stop that"),
    ("suit", "Suits and survival", "staying alive where you should not be"),
    ("tool", "Tools", "the work, and what it takes"),
    ("medical", "Medical", "keeping people going"),
    ("comp", "Computing and comms", "knowing, and telling"),
    ("survey", "Survey and science", "finding out what a place is"),
    ("travel", "Travel and transport", "getting about once you are down"),
    ("luxury", "Luxuries", "money, spent on being comfortable"),
    ("keepsake", "Keepsakes", "things worth nothing and kept anyway"),
    ("paper", "Papers", "what you are allowed to be"),
    ("illicit", "Illicit", "what the desk is actually looking for"),
)
CATEGORY_NAME = {c[0]: c[1] for c in CATEGORIES}


@dataclass(frozen=True)
class Item:
    """One thing somebody can own."""

    id: str
    name: str
    category: str
    #: Credits at a routine port, the tech level that makes it, and the law
    #: level at which it stops being legal to carry.
    cr: int
    tl: int
    law: int = 0
    mass: float = 1.0
    #: The skill it helps with, and by how much as a check DM.
    gives: str = ""
    bonus: int = 0
    note: str = ""


ITEMS: tuple = (
    # ── weapons ────────────────────────────────────────────────────────────
    Item("blade", "Blade", "weapon", 60, 1, 8, 1.0, "gun_combat", 0,
         "A knife is a tool until somebody says it is not."),
    Item("cutlass", "Cutlass", "weapon", 200, 2, 8, 1.5, "gun_combat", 1,
         "Ship's issue on half the haulers in the Verge."),
    Item("stunner", "Stunner", "weapon", 500, 8, 5, 0.8, "gun_combat", 1,
         "Nobody dies. Most ports still count it."),
    Item("autopistol", "Autopistol", "weapon", 250, 5, 5, 1.0, "gun_combat", 1,
         "Old, loud, and everywhere."),
    Item("snub_pistol", "Snub pistol", "weapon", 180, 8, 5, 0.5,
         "gun_combat", 1, "Low recoil; made for a corridor with air in it."),
    Item("laser_pistol", "Laser pistol", "weapon", 1_000, 9, 6, 1.5,
         "gun_combat", 1, "No recoil, no ammunition, a battery you can hear."),
    Item("shotgun", "Shotgun", "weapon", 200, 4, 7, 3.5, "gun_combat", 1,
         "The boarding weapon, and everybody knows it."),
    Item("carbine", "Carbine", "weapon", 400, 6, 6, 3.0, "gun_combat", 2,
         "Short, and it will go through a bulkhead."),
    Item("rifle", "Rifle", "weapon", 300, 5, 6, 4.0, "gun_combat", 2,
         "For a horizon, which a ship does not have."),
    Item("laser_rifle", "Laser rifle", "weapon", 3_500, 9, 6, 5.0,
         "gun_combat", 2, "Charge pack on the back; a serious thing."),
    Item("gauss_rifle", "Gauss rifle", "weapon", 1_500, 12, 4, 4.0,
         "gun_combat", 3, "Needles at two kilometres a second."),
    Item("cutting_torch", "Cutting torch", "weapon", 400, 6, 7, 6.0,
         "mechanic", 1, "A tool that has opened more doors than locks."),
    Item("breach_charge", "Breaching charge", "weapon", 300, 6, 3, 2.0,
         "explosives", 2, "One door, once."),
    Item("frag_grenade", "Fragmentation grenade", "weapon", 150, 6, 1, 0.5,
         "athletics", 0, "Everybody in the room, friend or not."),
    Item("stun_grenade", "Stun grenade", "weapon", 120, 7, 4, 0.4,
         "athletics", 0, "A flash, a bang, and a room full of people "
         "on the floor."),
    Item("smoke_grenade", "Smoke grenade", "weapon", 40, 4, 7, 0.4,
         "athletics", 0, "Nobody sees through it, including you."),
    Item("shock_baton", "Shock baton", "weapon", 120, 7, 7, 1.2,
         "gun_combat", 0, "What a port's own people carry."),

    # ── armour ─────────────────────────────────────────────────────────────
    Item("jack", "Jack", "armour", 100, 1, 9, 2.0, "", 0,
         "Layered hide. Better than nothing, and it looks like a coat."),
    Item("mesh", "Mesh", "armour", 150, 7, 8, 2.0, "", 0,
         "Under a shirt, and nobody is any the wiser."),
    Item("flak", "Flak jacket", "armour", 400, 7, 6, 4.0, "", 0,
         "Heavy, hot, and it has saved a great many people."),
    Item("cloth", "Ablative cloth", "armour", 250, 8, 7, 3.0, "", 0,
         "Takes a laser once and is then a shirt."),
    Item("carapace_suit", "Carapace suit", "armour", 12_000, 11, 4, 12.0,
         "", 0, "Plate. You will be noticed wearing it."),
    Item("grown_weave", "Grown weave", "armour", 3_000, 11, 7, 3.0, "", 0,
         "Spidroin, laid by something that was fed on your own tissue."),

    # ── suits and survival ─────────────────────────────────────────────────
    Item("vacc_suit", "Vacc suit", "suit", 6_000, 8, 0, 14.0, "vacc_suit", 1,
         "Eight hours, if the scrubber is honest."),
    Item("hostile_suit", "Hostile-environment suit", "suit", 18_000, 10, 0,
         20.0, "vacc_suit", 2, "Corrosive atmospheres, and it still leaks."),
    Item("softsuit", "Emergency softsuit", "suit", 800, 8, 0, 5.0,
         "vacc_suit", 0, "Twenty minutes. Better than the alternative."),
    Item("respirator", "Respirator", "suit", 100, 6, 0, 1.0, "", 0,
         "A tainted atmosphere, and a filter that needs changing."),
    Item("cold_kit", "Cold-weather kit", "suit", 300, 3, 0, 6.0, "survival", 1,
         "For a world where the night is the problem."),
    Item("survival_pack", "Survival pack", "suit", 400, 5, 0, 9.0,
         "survival", 1, "Ten days, if you are careful and lucky."),
    Item("rebreather", "Rebreather", "suit", 700, 8, 0, 3.0, "vacc_suit", 1,
         "Scrubs and returns. For long work outside."),
    Item("grav_belt", "Grav belt", "suit", 25_000, 12, 3, 8.0, "athletics", 2,
         "Expensive, and it will drop you if the cell goes."),
    Item("mag_boots", "Magnetic boots", "suit", 300, 8, 0, 3.0, "zero_g", 1,
         "The difference between working and drifting."),

    # ── tools ──────────────────────────────────────────────────────────────
    Item("toolkit", "Engineer's toolkit", "tool", 1_000, 6, 0, 12.0,
         "mechanic", 1, "Somebody's whole trade in a case."),
    Item("fine_tools", "Fine instruments", "tool", 2_000, 9, 0, 4.0,
         "electronics", 1, "Boards, probes, and very small screwdrivers."),
    Item("heavy_tools", "Heavy tools", "tool", 3_000, 6, 0, 40.0,
         "mechanic", 2, "You do not carry these; you bring the ship."),
    Item("welding_rig", "Welding rig", "tool", 1_400, 6, 0, 16.0,
         "mechanic", 1, "Hull work, and it is not subtle."),
    Item("cutting_laser", "Cutting laser", "tool", 5_000, 9, 5, 10.0,
         "mechanic", 2, "Yard tool. Also a weapon, and the desk knows it."),
    Item("bioscanner", "Bio-scanner", "tool", 3_000, 10, 0, 2.0, "medic", 1,
         "What is alive, and how nearly."),
    Item("lockpick", "Lock rig", "tool", 900, 9, 4, 1.0, "stealth", 2,
         "For doors that were not meant for you."),
    Item("rope_rig", "Climbing rig", "tool", 200, 3, 0, 8.0, "athletics", 1,
         "Cable, jumars, and something to tie it to."),
    Item("portable_gen", "Portable generator", "tool", 2_500, 8, 0, 25.0,
         "engineer", 1, "A week of power, wherever you set it down."),
    Item("field_press", "Field press", "tool", 6_000, 10, 0, 30.0,
         "trade", 2, "Makes the part you did not bring."),

    # ── medical ────────────────────────────────────────────────────────────
    Item("medkit", "Medical kit", "medical", 1_000, 8, 0, 5.0, "medic", 1,
         "Enough to get somebody to a proper table."),
    Item("field_surgery", "Field surgery", "medical", 8_000, 10, 0, 30.0,
         "medic", 2, "A proper table, if you have somewhere to put it."),
    Item("trauma_pack", "Trauma pack", "medical", 400, 8, 0, 2.0, "medic", 1,
         "One person, once, badly hurt."),
    Item("antitox", "Broad antitoxin", "medical", 300, 9, 0, 0.5, "", 0,
         "For a tainted atmosphere you were told about too late."),
    Item("stims", "Stimulants", "medical", 200, 8, 6, 0.2, "", 0,
         "Two more days. You will pay for both."),
    Item("slow_drug", "Slow drug", "medical", 1_200, 11, 5, 0.2, "", 0,
         "A month of subjective time in a day. Most survive it."),
    Item("anagathic", "Anagathic course", "medical", 90_000, 13, 7, 0.5,
         "", 0, "Years, bought. The Orders have opinions."),
    Item("prosthetic", "Prosthetic limb", "medical", 14_000, 10, 0, 6.0,
         "", 0, "Better than the original at some things."),

    # ── computing and comms ────────────────────────────────────────────────
    Item("handcomp", "Hand computer", "comp", 400, 8, 0, 0.5, "computers", 1,
         "Everything you know, in a pocket."),
    Item("core_slate", "Core slate", "comp", 4_000, 11, 0, 1.5, "computers", 2,
         "Talks to a ship's core as if it belonged there."),
    Item("comm", "Personal comm", "comp", 100, 7, 0, 0.3, "", 0,
         "A few kilometres, in the clear."),
    Item("tight_beam", "Tight-beam set", "comp", 3_000, 10, 3, 4.0, "", 0,
         "Point it at them and nobody else hears."),
    Item("jammer", "Jammer", "comp", 8_000, 11, 2, 5.0, "electronics", 2,
         "Everybody hears nothing, which is also a signal."),
    Item("translator", "Translator", "comp", 2_000, 11, 0, 0.4, "language", 2,
         "Four cultures and it is wrong about all of them, politely."),
    Item("recorder", "Recorder", "comp", 250, 7, 4, 0.4, "investigate", 1,
         "What was said, and who by."),
    Item("false_transponder", "False transponder", "comp", 20_000, 12, 1, 6.0,
         "deception", 3, "Be a different hull. Briefly."),

    # ── survey and science ─────────────────────────────────────────────────
    Item("survey_kit", "Survey kit", "survey", 2_500, 9, 0, 14.0,
         "sciences", 1, "Cores, assays, and somewhere to write it down."),
    Item("geoscanner", "Geo-scanner", "survey", 5_000, 10, 0, 8.0,
         "sciences", 2, "What is under the regolith, and how much."),
    Item("sample_case", "Sample case", "survey", 800, 9, 0, 7.0,
         "sciences", 1, "Sealed, cold, and it will hold whatever you found."),
    Item("xeno_reader", "Xenolith reader", "survey", 12_000, 12, 0, 6.0,
         "xenology", 2, "For recordings nobody has a key to."),
    Item("drone_eye", "Survey drone", "survey", 4_000, 10, 0, 9.0, "recon", 2,
         "Looks over the ridge so you do not have to."),
    Item("optics", "Long optics", "survey", 600, 6, 0, 3.0, "recon", 1,
         "A horizon, closer."),
    Item("motion_sensor", "Motion sensor", "survey", 1_200, 9, 3, 2.0,
         "recon", 2, "Something is moving, and it is that way."),

    # ── travel and transport ───────────────────────────────────────────────
    Item("ground_car", "Ground car", "travel", 4_000, 5, 0, 900.0, "drive", 1,
         "Four wheels and a roof, mostly."),
    Item("crawler", "All-terrain crawler", "travel", 25_000, 7, 0, 4_000.0,
         "drive", 2, "Goes where a car will not, slowly."),
    Item("air_raft", "Air/raft", "travel", 60_000, 8, 2, 4_000.0, "flyer", 2,
         "The thing everybody wants and nobody can berth."),
    Item("skiff", "Water skiff", "travel", 3_000, 4, 0, 600.0, "seafarer", 1,
         "For a world that is mostly water."),
    Item("g_sled", "Grav sled", "travel", 9_000, 11, 0, 200.0, "drive", 1,
         "Moves a tonne, badly, for a short way."),
    Item("suit_thruster", "Suit thruster pack", "travel", 7_000, 10, 3, 18.0,
         "zero_g", 2, "Twenty minutes of being your own small ship."),

    # ── luxuries ───────────────────────────────────────────────────────────
    Item("good_coat", "A good coat", "luxury", 800, 3, 0, 2.0, "persuade", 1,
         "People answer a coat."),
    Item("dress_clothes", "Dress clothes", "luxury", 2_000, 4, 0, 3.0,
         "diplomat", 1, "For rooms that have a list."),
    Item("watch", "A proper watch", "luxury", 3_000, 5, 0, 0.2, "", 0,
         "Mechanical, and it has outlived two owners."),
    Item("cabin_fittings", "Cabin fittings", "luxury", 6_000, 8, 0, 60.0,
         "", 0, "A berth that is somewhere to be rather than sleep."),
    Item("cellar", "A small cellar", "luxury", 4_000, 2, 0, 40.0, "carouse", 1,
         "Six cases, and the knowledge of what is in them."),
    Item("instrument", "A musical instrument", "luxury", 1_500, 2, 0, 4.0,
         "art", 1, "Somebody aboard will ask you to stop."),
    Item("art_piece", "A piece of art", "luxury", 12_000, 1, 0, 8.0, "art", 0,
         "It appreciates, which is more than most of the crew."),
    Item("tea_service", "A tea service", "luxury", 900, 2, 0, 5.0,
         "steward", 1, "It is not about the tea."),
    Item("good_bed", "A real bed", "luxury", 2_500, 6, 0, 90.0, "", 0,
         "Four hours of this beats eight of the other."),
    Item("private_stock", "Private stock", "luxury", 1_100, 3, 0, 20.0,
         "carouse", 0, "For the people you actually like."),

    # ── keepsakes ──────────────────────────────────────────────────────────
    Item("locket", "A locket", "keepsake", 40, 1, 0, 0.1, "", 0,
         "Somebody's face, and they do not say whose."),
    Item("service_medal", "A service medal", "keepsake", 0, 5, 0, 0.1,
         "", 0, "Given for something they will not describe."),
    Item("old_log", "An old ship's log", "keepsake", 0, 7, 0, 1.0,
         "investigate", 0, "A hull that is not flying any more."),
    Item("hometown_dirt", "A jar of home", "keepsake", 0, 1, 0, 0.5, "", 0,
         "Soil, dust, or ice. It is not for anything."),
    Item("letters", "A bundle of letters", "keepsake", 0, 1, 0, 0.3, "", 0,
         "Paper, which means somebody meant it."),
    Item("kith_token", "A Kith token", "keepsake", 0, 0, 0, 0.2, "xenology", 1,
         "Given, not taken. They are particular about that."),
    Item("first_tool", "Their first tool", "keepsake", 0, 3, 0, 0.6,
         "mechanic", 0, "Worn to the shape of one hand."),
    Item("dead_watch", "A stopped watch", "keepsake", 0, 4, 0, 0.2, "", 0,
         "It stopped at something. They know when."),

    # ── papers ─────────────────────────────────────────────────────────────
    Item("passage_papers", "Passage papers", "paper", 200, 6, 0, 0.1,
         "admin", 1, "You are allowed to be here."),
    Item("gun_licence", "Weapons licence", "paper", 1_500, 6, 0, 0.1,
         "law", 2, "Carry the thing legally, on this world, this year."),
    Item("masters_ticket", "Master's ticket", "paper", 8_000, 8, 0, 0.1,
         "pilot", 1, "You may command a hull, and it is written down."),
    Item("trade_licence", "Trading licence", "paper", 5_000, 6, 0, 0.1,
         "broker", 1, "The Charter's blessing on your margin."),
    Item("letter_credit", "Letter of credit", "paper", 0, 5, 0, 0.1,
         "broker", 1, "Money that is not aboard, which is safer."),
    Item("writ", "A writ of passage", "paper", 12_000, 7, 0, 0.1, "admin", 2,
         "A power says you may. Most desks accept it."),
    Item("false_papers", "False papers", "paper", 9_000, 8, 1, 0.1,
         "deception", 2, "Good ones. Not perfect ones."),
    Item("salvage_claim", "A salvage claim", "paper", 0, 6, 0, 0.1,
         "law", 1, "Somebody's wreck, and your name on it."),
    Item("deed", "A deed", "paper", 0, 4, 0, 0.1, "", 0,
         "Ground, somewhere, with their name on it."),

    # ── illicit ────────────────────────────────────────────────────────────
    Item("contraband_case", "A sealed case", "illicit", 0, 8, 1, 8.0, "", 0,
         "They were not told what is in it, and did not ask."),
    Item("spore_sample", "A spore sample", "illicit", 40_000, 11, 1, 1.0,
         "sciences", 0, "Every treaty in the sector. Three factions field it."),
    Item("unlicensed_seed", "An unlicensed seed", "illicit", 120_000, 12, 1,
         120.0, "", 0, "The thing the whole regime exists to stop."),
    Item("stolen_core", "A stolen core", "illicit", 30_000, 12, 2, 12.0,
         "computers", 1, "Somebody's whole chronicle, and they want it back."),
    Item("smuggler_hold", "A hidden hold", "illicit", 15_000, 9, 2, 0.0,
         "deception", 2, "Four tonnes the manifest does not mention."),
    Item("blackmarket_key", "A black-market key", "illicit", 6_000, 9, 3, 0.1,
         "streetwise", 2, "Which door, and what to say at it."),
)

ITEM_BY_ID = {i.id: i for i in ITEMS}
BY_CATEGORY = {cid: tuple(i for i in ITEMS if i.category == cid)
               for cid, _n, _note in CATEGORIES}

#: How much a person can carry before it is a problem, in kilograms. Anything
#: heavier than this is kept aboard rather than about their person — which is
#: why an air/raft is owned and not carried.
CARRIED = 30.0


def legal_at(item: Item, law: int) -> bool:
    """May this be carried openly on a world at this law level?"""
    return item.law <= 0 or law < item.law


def stocked_at(item: Item, tech: int) -> bool:
    """Would a port at this tech level have it on the shelf?

    One level of grace: a world makes what it can make and imports a little
    above itself, which is why a frontier chandler has one good vacc suit.
    """
    return item.tl <= tech + 1


def price_at(item: Item, tech: int) -> int:
    """What it costs here. Cheap where it is made, dear where it is not.

    Ten per cent a tech level either way, and never less than a third or
    more than three times — a world does not sell a thing it cannot make for
    nothing, and it does not charge a fortune for its own output.
    """
    if item.cr <= 0:
        return 0
    gap = tech - item.tl
    shift = max(0.34, min(3.0, 1.0 - gap * 0.10))
    return max(1, int(item.cr * shift))
