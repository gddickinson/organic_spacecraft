"""Where somebody came from, who they know, and what they are still after.

A service record says what a person *did*. It does not say where they were
born, who raised them, who they owe, who is looking for them, or what they
are trying to get out of all this — and those are the things that make a name
on a crew list into somebody you would notice leaving.

Four tables, and they hang off the game that already exists rather than
beside it:

- **Homeworlds** are read in the Verge's own terms, and they line up with the
  trade classifications `data/uwp.py` already earns worlds — somebody from a
  belt is `As`, somebody from a farm is `Ag`. A captain who learns to read a
  profile has learned to read a crew list.
- **Upbringings** are the Verge's actual social facts: the licence regime,
  the Yards' apprenticeships, the Orders' wards, indenture, and the people who
  fell through all of it.
- **Ambitions** are what somebody would leave your ship for, which is the only
  definition that matters.
- **Ties** are the people attached to them. A tie is a *name and a direction*:
  who, and whether they would help or hinder.

`sim/lifepath.py` deals them out of a career's events and terms; nothing here
does anything.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Homeworld:
    """Where they grew up, and what it left them with."""

    id: str
    name: str
    note: str
    #: The trade classification a world like this earns (`data/uwp.py`), so a
    #: crew list and a world profile are read in one vocabulary.
    code: str = ""
    #: What growing up there teaches, and the characteristic it favours.
    skills: tuple = ()
    lean: str = ""


HOMEWORLDS: tuple = (
    Homeworld("belt", "A belt", "Rock, vacuum, and a family claim.", "As",
              ("vacc_suit", "mechanic", "sciences"), "dex"),
    Homeworld("farm", "Dirtside, a holding", "Weather, animals, and long days.",
              "Ag", ("survival", "animals", "mechanic"), "end"),
    Homeworld("highport", "A high port", "Grew up in the concourse.", "Hi",
              ("streetwise", "broker", "admin"), "soc"),
    Homeworld("yard", "A yard town", "Everybody's parents built hulls.", "In",
              ("mechanic", "engineer", "vacc_suit"), "int"),
    Homeworld("water", "A water world", "Boats before walking.", "Wa",
              ("survival", "medic", "athletics"), "end"),
    Homeworld("desert", "A dry world", "Water was counted.", "De",
              ("survival", "recon", "streetwise"), "end"),
    Homeworld("ice", "An ice moon", "Under the crust, under the lamps.", "Ic",
              ("vacc_suit", "sciences", "survival"), "end"),
    Homeworld("ship", "Shipboard", "Born under way; no ground at all.", "",
              ("astrogation", "steward", "vacc_suit"), "dex"),
    Homeworld("garden", "A garden world", "The easy start, and they know it.",
              "Ga", ("persuade", "steward", "animals"), "soc"),
    Homeworld("outpost", "An outpost", "Forty people and one landing field.",
              "Lo", ("survival", "mechanic", "gun_combat"), "end"),
    Homeworld("reach", "Near the Reach", "Close enough to have watched it.",
              "", ("recon", "survival", "xenology"), "int"),
    Homeworld("cradle", "The Cradle's edge", "Grew up hearing the Kith.", "",
              ("xenology", "persuade", "sciences"), "int"),
)
HOMEWORLD_BY_ID = {h.id: h for h in HOMEWORLDS}


@dataclass(frozen=True)
class Upbringing:
    """Who raised them, and what it did."""

    id: str
    name: str
    note: str
    skills: tuple = ()
    lean: str = ""


UPBRINGINGS: tuple = (
    Upbringing("licensed", "A licensed family",
               "Papers for everything, and somebody checked.",
               ("admin", "persuade"), "soc"),
    Upbringing("yardkin", "Yard kin",
               "Handed a spanner before a spoon.", ("mechanic",), "int"),
    Upbringing("ward", "An Orders ward",
               "Raised by the doctrine, and fed by it.",
               ("medic", "xenology"), "edu"),
    Upbringing("indentured", "Indentured",
               "Somebody else owned the years.", ("survival", "deception"),
               "end"),
    Upbringing("company", "A free company",
               "A dozen adults, one hull, no rules worth the name.",
               ("streetwise", "gun_combat"), "dex"),
    Upbringing("orphan", "Orphaned early",
               "Nobody wrote down who by.", ("streetwise", "survival"), "end"),
    Upbringing("scholar", "Schooled properly",
               "Somebody paid for it, and it shows.",
               ("sciences", "admin"), "edu"),
    Upbringing("service", "Service family",
               "Three generations in the same uniform.",
               ("leadership", "gun_combat"), "soc"),
    Upbringing("trade", "A trading house",
               "Learned the margin before the alphabet.",
               ("broker", "persuade"), "int"),
    Upbringing("quarantine", "Behind a quarantine line",
               "The line held. Most of the time.",
               ("survival", "medic"), "end"),
)
UPBRINGING_BY_ID = {u.id: u for u in UPBRINGINGS}


@dataclass(frozen=True)
class Ambition:
    """What they are still after. What they would leave your ship for."""

    id: str
    name: str
    note: str
    #: What moves them toward it: a thing the captain can actually do.
    served_by: str = ""


AMBITIONS: tuple = (
    Ambition("hull", "A hull of their own",
             "Every credit is going somewhere.", "a share of a prize"),
    Ambition("licence", "To be licensed",
             "The Charter's paper, and what it opens.", "Charter standing"),
    Ambition("home", "To go home",
             "There is somewhere, and they are not there.", "a berth that way"),
    Ambition("name", "To be somebody",
             "They want the name said in a room they are not in.", "renown"),
    Ambition("find", "To find who did it",
             "Somebody is owed something.", "news of a rival"),
    Ambition("safe", "Never to be poor again",
             "They have been, and once was enough.", "money in hand"),
    Ambition("weave", "To see the Weave",
             "Properly, with their own eyes.", "a gate opened"),
    Ambition("know", "To understand it",
             "The Bloom, the Kith, the lot.", "research"),
    Ambition("quiet", "A quiet berth and an end to it",
             "Twenty years is enough for anybody.", "a long peace"),
    Ambition("ground", "Ground of their own",
             "A holding with their name on the deed.", "a colony"),
    Ambition("crew", "To keep this crew together",
             "It is the first thing that has worked.", "loyalty"),
    Ambition("even", "To get even",
             "With a power, a house, or one person.", "a grudge settled"),
)
AMBITION_BY_ID = {a.id: a for a in AMBITIONS}


#: The kinds of person attached to somebody, and what having them is worth.
#: `helps` is the direction: a tie that helps is somebody who would answer,
#: and one that does not is somebody who would rather you did not call.
@dataclass(frozen=True)
class TieKind:
    id: str
    name: str
    helps: bool
    #: How the tie reads on a sheet, with `{who}` for the name.
    line: str


TIE_KINDS: tuple = (
    TieKind("parent", "Parent", True, "{who}, who raised them"),
    TieKind("sibling", "Sibling", True, "{who}, their sibling"),
    TieKind("child", "Child", True, "{who}, their child"),
    TieKind("partner", "Partner", True, "{who}, waiting somewhere"),
    TieKind("cousin", "Kin", True, "{who}, kin of some degree"),
    TieKind("mentor", "Mentor", True, "{who}, who taught them the work"),
    TieKind("oldcrew", "Old shipmate", True, "{who}, off a hull years ago"),
    TieKind("ally", "Ally", True, "{who}, who owes them one"),
    TieKind("patron", "Patron", True, "{who}, who has backed them before"),
    TieKind("contact", "Contact", True, "{who}, who hears things"),
    TieKind("debtor", "Debtor", True, "{who}, who owes them money"),
    TieKind("creditor", "Creditor", False, "{who}, who is owed money"),
    TieKind("rival", "Rival", False, "{who}, who wants the same berth"),
    TieKind("enemy", "Enemy", False, "{who}, who has not forgotten"),
    TieKind("hunter", "Hunter", False, "{who}, who is looking for them"),
    TieKind("estranged", "Estranged", False, "{who}, who will not speak"),
)
TIE_BY_ID = {t.id: t for t in TIE_KINDS}

#: Which ties a career tends to leave behind. A picket makes rivals and old
#: shipmates; a drifter makes creditors and people who are looking for them.
CAREER_TIES = {
    "charter": ("mentor", "ally", "rival", "patron", "contact"),
    "yards": ("mentor", "oldcrew", "rival", "debtor", "contact"),
    "hauler": ("contact", "creditor", "patron", "oldcrew", "debtor"),
    "orders": ("mentor", "ally", "estranged", "patron"),
    "prospector": ("oldcrew", "creditor", "rival", "contact"),
    "picket": ("oldcrew", "mentor", "rival", "enemy"),
    "reach": ("oldcrew", "estranged", "enemy", "ally"),
    "drifter": ("creditor", "hunter", "contact", "enemy", "oldcrew"),
}

#: How many ties somebody has, by terms served. Nobody is alone, and nobody
#: knows everybody: a record with fourteen relationships on it is a list
#: rather than a person.
TIES_LEAST, TIES_MOST = 2, 6

#: What a berth was called, before yours. Names are built from these; the
#: hull names in `data/lore.py` belong to ships that exist now.
BERTH_FIRST = (
    "Long", "Quiet", "Second", "Patient", "Hard", "Bright", "Late", "Small",
    "First", "Cold", "Plain", "Steady", "Broken", "Sudden", "Old", "Fair",
)
BERTH_SECOND = (
    "Consent", "Reckoning", "Passage", "Margin", "Account", "Tally",
    "Increment", "Standing", "Warrant", "Errand", "Interest", "Crossing",
    "Ledger", "Remittance", "Compliance", "Arrears",
)

#: What kind of hull a past berth was, so "three berths" is three different
#: lives rather than one repeated.
BERTH_KINDS = (
    "a hauler", "a survey boat", "a picket", "a yard tender", "a tramp",
    "an Orders transport", "a prospector", "a courier", "a quarantine runner",
    "a company hull", "a salvage boat", "a mail packet",
)

#: Why they left. The half of a berth that is worth knowing.
BERTH_ENDINGS = (
    "paid off at the end of a charter",
    "left when the master would not be argued with",
    "was aboard when she was lost",
    "walked off over money",
    "was let go when the run dried up",
    "left on good terms and is still welcome",
    "jumped ship at a port they will not name",
    "stayed until she was broken up",
    "was put ashore sick and never went back",
    "left because somebody else did",
)
