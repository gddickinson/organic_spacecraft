"""What is open on your own hull: the sickbay, the wardroom, the vat deck.

A hull is somewhere people live, and the concourse model could not see it.
`sim/places.py` knew four kinds of place — a quay, a habitat, a holding, a
works on the ground — and a LAZARET is a hospital with a drive that could
not offer anybody so much as a check-up, because a clinic asks a *place* and
a ship was not one.

So a ship is a place too, and these are its doors. They are gated the same
way everything else is — on how much of a place the hull is — and the rating
comes off the tier on its card rather than off its tonnage: a Hospital hull
is a hospital, a Liner has a wardroom and a gym, and a scout has a locker
with a first-aid kit in it.

**A door is aboard or ashore, never both.** `Venue.aboard` says which, and
`open_to` checks it against the place's kind — otherwise a grand hotel would
appear in a cutter's crew quarters the moment the crew got large enough.
"""

from __future__ import annotations

from .venue_types import Venue

#: How much of a place a hull is, by the tier printed on its card. Anything
#: not named here is whatever its crew earns it and no more — a working ship
#: with twenty hands aboard has a mess and a medicine chest.
#:
#: These are ratings on the starport scale, so one number gates a venue
#: whether it is a Charter emporium or a wardroom.
ABOARD_RATING = {
    "Hospital": 4,
    "Ark": 4,
    "Liner": 3,
    "Colony": 3,
    "Capital": 3,
    "Carrier": 2,
    "Dreadnought": 2,
    "Battleship": 2,
    "Research": 2,
    "Freighter": 1,
    "Cruiser": 1,
    "Monitor": 1,
    "Siege": 1,
    "Destroyer": 1,
    "Ship": 1,
}

#: The least crew a hull needs before anything aboard counts as a door at
#: all. Four people and a bunk is not a concourse.
ABOARD_LEAST_CREW = 12


ABOARD: tuple = (
    Venue("slop_chest", "The slop chest", "chandler", 0, 1, 0, aboard=True,
          note="Whatever the last port sold you, at what it cost.",
          offers=("shelf",)),
    Venue("mess_deck", "The mess deck", "eatery", 4, 1, 0, aboard=True,
          morale=0.01,
          note="What the vats made, again. Everybody is here anyway.",
          offers=("meal",)),
    Venue("wardroom", "The wardroom", "eatery", 18, 3, 0, aboard=True,
          morale=0.04, loyalty=1.0,
          note="A table that is not the mess deck, and an evening that is "
               "not a watch.", favours="steward", offers=("meal",)),
    Venue("ship_sickbay", "The sickbay", "clinic", 0, 1, 0, aboard=True,
          note="A bunk, a chest, and whoever is least bad at it.",
          favours="medic", offers=("care",)),
    Venue("ship_surgery", "The ship's surgery", "clinic", 0, 3, 0, tech=9,
          aboard=True,
          note="A proper theatre, bolted to a deck that moves.",
          favours="medic", offers=("care", "surgery")),
    Venue("vat_deck", "The vat deck", "clinic", 0, 4, 0, tech=10, aboard=True,
          note="Tissue grown on the way, from the person it is going into.",
          favours="medic", offers=("graft", "surgery")),
    Venue("ship_racks", "The cold racks", "clinic", 0, 3, 0, tech=9,
          aboard=True,
          note="Berths that do not eat. The oldest answer to a long "
               "crossing.", offers=("ice",)),
    Venue("ship_gym", "The gym", "sport", 6, 2, 0, aboard=True,
          morale=0.02, loyalty=0.5,
          note="Two machines, bolted down, and a queue for both.",
          favours="athletics", offers=("train",)),
    Venue("ship_library", "The ship's library", "arts", 0, 3, 0, aboard=True,
          morale=0.02,
          note="Somebody's collection, left aboard and never claimed.",
          favours="teaching", offers=("train", "data")),
    Venue("ship_workshop", "The workshop", "tech", 0, 2, 0, tech=9,
          aboard=True,
          note="A bench, a fabricator, and everything that came off "
               "something else.", favours="mechanic", offers=("shelf",)),
)


def rating(tier: str, crew: int) -> int:
    """How much of a place a hull is: `0` when it is only a ship.

    A hull has to carry enough people to be anywhere at all, and then it is
    whatever its tier says — so a hundred-and-twenty-berth hospital is a
    hospital and a forty-crew cruiser has a sickbay and a mess.
    """
    if crew < ABOARD_LEAST_CREW:
        return 0
    return max(1, ABOARD_RATING.get(tier, 1))
