"""What somebody did before they came aboard: eight careers of the Verge.

*Traveller* generates a character by playing out their life before the game
starts — four-year terms, a roll to survive each one, a roll to be promoted,
a skill learned, and sometimes a mishap that throws them out of the service
early. It is the best character generator ever written for one reason: **it
produces a history, not a build**. The numbers come out of the story instead
of the story being written round the numbers.

These are the Verge's own careers rather than the Imperium's. Every one is a
thing a player has already met somewhere in this game — the licence regime,
the Yards, the haulers, the Orders, the prospectors, the pickets, the ones
who came back from Kessel's Reach, and the ones who never held a berth at
all.

The generator is `sim/lifepath.py`; nothing here does anything. **Skills are
strings on purpose**: they are looked up by name, several careers teach the
same one, and a captain reads "Gunnery 2" without needing a table.
"""

from __future__ import annotations

from .career_types import Career
from .careers_civil import CIVIL


#: Every skill anybody in the Verge can hold a level in, and what it is for.
#: One flat list rather than a tree: Traveller's specialities are a fine idea
#: for a table and a poor one for a screen, and the game has twelve stations
#: to cover rather than a galaxy's worth.
SKILLS = {
    "astrogation": "plotting a crossing, and knowing what it will cost",
    "pilot": "hands on a hull at close quarters",
    "gunnery": "a mounting, a target, and the lead between them",
    "engineer": "drives, reactors and the heat they make",
    "mechanic": "the parts of a ship you can reach with a spanner",
    "medic": "keeping a crew alive between ports",
    "sciences": "surveys, samples and what they turn out to mean",
    "xenology": "what the four cultures left, and what it meant to them",
    "broker": "what a cargo is worth, and to whom",
    "steward": "feeding and holding together the people aboard",
    "admin": "papers, licences and the people who check them",
    "persuade": "getting somebody to do what you want anyway",
    "leadership": "getting a crew to do it when it is hard",
    "tactics": "an engagement, read before it happens",
    "gun_combat": "a weapon, in your own hands, at close range",
    "recon": "seeing what is there before it sees you",
    "survival": "a world that would rather you were not on it",
    "streetwise": "who to ask, and what not to ask them",
    "deception": "being taken for somebody you are not",
    "vacc_suit": "working outside, for a long time, safely",
    # ── the rest of a life ─────────────────────────────────────────────────
    # Not every skill is a station on a bridge. These are the ones people
    # actually have, and the reason a crew list reads as a dozen different
    # lives rather than a dozen job titles.
    "animals": "beasts, and the people who keep them",
    "athletics": "running, climbing, and carrying it up a ladder",
    "art": "making something nobody needed, well",
    "carouse": "a long evening, and what comes out of one",
    "drive": "anything with wheels or tracks on a surface",
    "flyer": "anything with wings or lift in an atmosphere",
    "electronics": "boards, sensors, and the things that talk to them",
    # ── the concourse's own trades ─────────────────────────────────────────
    # A sector with body shops, hospitals, courts and constabularies in it
    # needs people who can do those things, and a crew that can tell when
    # somebody else is doing them badly.
    "cybernetics": "what is fitted into people, and how to take it out",
    "pharmacy": "drugs, anagathics, and what they actually do",
    "security": "locks, watches, and the people who get past both",
    "teaching": "making somebody else able to do it",
    "computers": "what the ship's core will and will not do for you",
    "explosives": "cutting charges, and where to put them",
    "gambler": "the odds, and the people who ignore them",
    "investigate": "finding out, from what is left lying about",
    "language": "somebody else's, well enough to be trusted",
    "law": "what the statute actually says, and who enforces it",
    "navigation": "a surface, a horizon, and no beacon",
    "seafarer": "water, in hulls that float on it",
    "stealth": "not being where they are looking",
    "trade": "a craft with a name — smith, cook, cutter, grower",
    "diplomat": "two parties, and getting them to sign",
    "jack": "a little of everything, badly, which is often enough",
    "zero_g": "working and fighting where there is no down",
}


CAREERS_CORE: tuple = (
    Career(
        "charter", "Charter Service",
        "The licence regime's own: forms, inspections and a uniform.",
        qualify=("soc", 6), survive=("end", 5), advance=("edu", 7),
        ranks=("Rating", "Able", "Petty officer", "Warrant", "Lieutenant",
               "Commander"),
        skills=("admin", "vacc_suit", "gun_combat", "leadership",
                "astrogation", "engineer"),
        officer_skills=("leadership", "admin", "tactics"),
        mishaps=(
            "Signed off an inspection that did not hold. Somebody drowned.",
            "Took the blame for a licence nobody would own.",
            "Invalided out after a decompression on the quay.",
            "Refused an order in front of the wrong officer."),
        events=(
            "Seconded to a survey and came back with a taste for it.",
            "Served under an officer worth learning from.",
            "Spent a year on the paperwork of somebody else's disaster.",
            "Found a discrepancy that was not a mistake."),
        benefits=("a Charter reference", "back pay", "a licence of your own",
                  "a name people answer"),
        station="comms"),

    Career(
        "yards", "Concordat Yards",
        "Fabricated hulls, and the people who put them together.",
        qualify=("int", 6), survive=("dex", 5), advance=("int", 7),
        ranks=("Hand", "Fitter", "Leading fitter", "Foreman", "Yard master"),
        skills=("mechanic", "engineer", "vacc_suit", "sciences", "admin",
                "gunnery"),
        officer_skills=("leadership", "engineer", "admin"),
        mishaps=(
            "A drive test went wrong and took two fingers with it.",
            "Laid off when the slipway closed.",
            "Blamed for a weld that opened at pressure.",
            "Walked out over what they were being asked to certify."),
        events=(
            "Built a hull from the keel and watched it fly.",
            "Learned a trick nobody writes down.",
            "Worked a refit that had to be finished in four days.",
            "Caught a fault nobody else had seen."),
        benefits=("a toolkit worth having", "a share in a hull",
                  "Yards contacts", "a reputation for sound work"),
        station="engineer"),

    Career(
        "hauler", "Freehold Hauler",
        "Somebody else's cargo, somebody else's schedule, your risk.",
        qualify=("int", 5), survive=("end", 5), advance=("soc", 7),
        ranks=("Crew", "Hand", "Mate", "Master", "Owner"),
        skills=("broker", "pilot", "astrogation", "steward", "streetwise",
                "mechanic"),
        officer_skills=("leadership", "broker", "persuade"),
        mishaps=(
            "The cargo was not what the manifest said. The port disagreed.",
            "Lost a hull to a boarding and walked away with the log.",
            "Ruined by one bad run and a bank that would not wait.",
            "Put a ship on a rock and never quite explained how."),
        events=(
            "Made a run nobody thought was worth the fuel, and it was.",
            "Learned which quays weigh the cargo and which weigh you.",
            "Carried something that should not have been carried.",
            "Talked a port official round over four hours and a bottle."),
        benefits=("a trade contact", "capital", "a cargo lot",
                  "a share in a hull"),
        station="comms"),

    Career(
        "orders", "The Orders",
        "The Sanhedrin's doctrine, and the care it asks of its own.",
        qualify=("edu", 6), survive=("int", 5), advance=("edu", 7),
        ranks=("Postulant", "Brother", "Reader", "Preceptor", "Elder"),
        skills=("medic", "sciences", "xenology", "persuade", "admin",
                "steward"),
        officer_skills=("leadership", "persuade", "xenology"),
        mishaps=(
            "Asked a question the Orders would not have asked.",
            "Broke under what they were shown at a dig.",
            "Nursed a ward through something that took most of it with them.",
            "Was sent away, and has never said why."),
        events=(
            "Read a recording nobody else could make sense of.",
            "Sat a long vigil and came out of it different.",
            "Was trusted with a thing the Orders do not write down.",
            "Argued doctrine with an Elder and was not wrong."),
        benefits=("a letter that opens doors", "a reading of your own",
                  "the Orders' regard", "a case of instruments"),
        station="medic"),

    Career(
        "prospector", "Prospector",
        "Rocks, a sampling head, and a very long way from anybody.",
        qualify=("end", 5), survive=("end", 6), advance=("int", 7),
        ranks=("Hand", "Driller", "Claim holder", "Operator", "Magnate"),
        skills=("sciences", "vacc_suit", "mechanic", "survival", "recon",
                "pilot"),
        officer_skills=("leadership", "broker", "sciences"),
        mishaps=(
            "A working collapsed. They were the one who got out.",
            "Staked everything on a body that assayed at nothing.",
            "Came back from a long solo run not quite right.",
            "Lost a claim to somebody with better lawyers."),
        events=(
            "Hit a seam that paid for the next four years.",
            "Survived eleven days on a rock with a failing scrubber.",
            "Learned to read a body from orbit and be right.",
            "Found something in the strata that was not ore."),
        benefits=("a claim", "survey gear", "capital",
                  "a nose for a good body"),
        station="science"),

    Career(
        "picket", "The Picket",
        "Somebody has to be out at the edge when the Bloom moves.",
        qualify=("end", 6), survive=("end", 6), advance=("tactics", 7),
        ranks=("Rating", "Gunner", "Chief", "Sub-lieutenant", "Captain"),
        skills=("gunnery", "tactics", "gun_combat", "vacc_suit", "pilot",
                "recon"),
        officer_skills=("leadership", "tactics", "gunnery"),
        mishaps=(
            "Their picket was overrun. They were pulled out of the wreck.",
            "Fired on something they were told afterwards was a freighter.",
            "Held a watch too long and has not slept properly since.",
            "Court-martialled, and the finding is sealed."),
        events=(
            "Stood a watch that turned into an engagement.",
            "Shot down something nobody believed was out there.",
            "Learned the whole of a gun, and can strip one blind.",
            "Was decorated, and does not talk about it."),
        benefits=("a weapon of your own", "a pension", "picket contacts",
                  "a decoration"),
        station="tactical"),

    Career(
        "reach", "Kessel's Reach",
        "They were there when it germinated, and they came back.",
        qualify=("end", 8), survive=("end", 7), advance=("int", 8),
        ranks=("Survivor", "Witness", "Veteran"),
        skills=("survival", "gun_combat", "recon", "medic", "xenology",
                "vacc_suit"),
        officer_skills=("leadership", "tactics", "xenology"),
        mishaps=(
            "Lost everyone they went in with.",
            "Carries something in their blood the medics cannot name.",
            "Will not go within a jump of the Reach, for any money.",
            "Came back, and something else came back with them."),
        events=(
            "Walked out of a system nobody else walked out of.",
            "Saw the thing whole, and can describe it.",
            "Held a line for nine days at a quarantine boundary.",
            "Learned what the Bloom does when it is hungry."),
        benefits=("what they carried out", "a pension nobody questions",
                  "an unmatched account of it", "the Charter's ear"),
        station="tactical"),

    Career(
        "drifter", "Drifter",
        "No berth, no service, no record. It teaches its own things.",
        qualify=("end", 2), survive=("end", 4), advance=("soc", 9),
        ranks=("Nobody", "Known", "Somebody"),
        skills=("streetwise", "deception", "survival", "gun_combat",
                "mechanic", "persuade"),
        mishaps=(
            "Picked up on a charge that stuck for three years.",
            "Beaten badly enough to change what they can do.",
            "Trusted somebody, once.",
            "Woke up on a different world with no idea how."),
        events=(
            "Learned which quays will let a stranger sleep.",
            "Worked six berths in four years and was good at all of them.",
            "Did somebody a favour that is still owed.",
            "Found out what they are actually good at."),
        benefits=("a favour owed", "a hiding place", "what they carry",
                  "no questions asked"),
        station="engineer"),
)

#: Every life somebody in the Verge can have had: the eight that are ways of
#: being aboard something, and the six that are not (`data/careers_civil.py`).
#: A sector with hospitals, courts and brokerages in it has people who worked
#: in them, and they end up on bridges.
CAREERS: tuple = CAREERS_CORE + CIVIL

CAREER_BY_ID = {c.id: c for c in CAREERS}

#: Which careers a ship's station draws its people from, best first. A
#: navigator who came up through the Yards is a real person; one whose whole
#: history has nothing to do with navigation is a dice roll wearing a name.
BY_STATION = {
    "science": ("prospector", "orders", "charter", "clinician"),
    "nav": ("charter", "hauler", "yards", "factor"),
    "engineer": ("yards", "drifter", "charter", "syndicate"),
    "medic": ("clinician", "orders", "reach", "charter"),
    "comms": ("hauler", "charter", "factor", "magistrate", "entertainer"),
    "tactical": ("picket", "constable", "reach", "drifter", "syndicate"),
}

#: What the station on the door actually asks of the person behind it, and
#: the skill beside it that goes with the job.
#:
#: **A Chief Engineer with Engineer untrained is a bug you can read.** The
#: life path deals skills out of a career, and a career is only *weighted*
#: towards a station — so a yards officer could come out of four terms with
#: Vacc Suit 2, Admin 1 and nothing at all about a drive, and the crew list
#: said "Chief Engineer" over it. The ship hired them for this; they know it.
STATION_SKILLS = {
    "science": ("sciences", "investigate"),
    # A navigator holds a pilot's ticket: they are the officer who flies,
    # and a ship that carries a launch (`sim/craft.py`) needs somebody
    # besides the captain who may take it out.
    "nav": ("astrogation", "navigation", "pilot"),
    "engineer": ("engineer", "mechanic"),
    "medic": ("medic", "sciences"),
    "comms": ("electronics", "persuade"),
    "tactical": ("gunnery", "tactics"),
}

#: How long a term is, in years, and how old somebody is when they start.
TERM_YEARS = 4
ENTRY_AGE = 18

#: When ageing starts to cost, and what it costs. Traveller begins at 34 —
#: the end of the fourth term — and so does this.
AGEING_FROM = 34
