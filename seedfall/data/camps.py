"""What a landing party pitches when it means to stay.

An expedition is a supply clock: days come down in the lander's hold, every
step spends them, and a party that runs out walks home with what is on its
backs and leaves the rest (`expedition.STRANDED_SHARE`). The only building
on the map was the lander, and the only place the clock could be refilled
was orbit.

A camp is a second place on the ground. It comes down in the same hold, it
is pitched on a tile and struck again, and it does three things:

- **It holds days.** Supply left in a camp is not carried, and a party that
  walks back into its own camp picks the days back up. That is what turns
  "how far dare we go" into a route rather than a guess.
- **It sits out weather for nothing.** A gale that pins a party in the open
  costs a day of supply; a gale that pins them in a camp costs the day and
  not the supply.
- **It is somewhere to work.** A day's rest in a camp is worth more to the
  machine and to the injured than a day's rest on regolith.

Each class is a few numbers: what it masses against the supplies it rides
down with, how many it sleeps, how many days of supply it can hold, and
what a day inside it is worth.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CampClass:
    """One class of camp."""

    id: str
    name: str
    #: Whose yard builds it, in the families `data/chassis` already uses.
    family: str
    blurb: str
    mass_t: float
    sleeps: int
    #: Days of supply it will hold for a party that comes back to it.
    holds: int
    #: What a day resting inside is worth against a day in the open.
    rest: float
    cost: dict


#: What a camp is worth back against its build cost — the share a craft and
#: a vehicle both fetch, for the same reason.
SALVAGE = 0.35

CAMPS: tuple = (
    CampClass(
        "bivouac", "BIVOUAC", "fabricated",
        "Two hoops, a skin and a heater. It is the difference between "
        "sitting out a gale and being out in one, and it weighs almost "
        "nothing.",
        0.6, 3, 6, rest=1.4,
        cost={"credits": 2_400, "alloy": 3, "silicon": 1}),
    CampClass(
        "camp", "FIELD CAMP", "fabricated",
        "Four sleeping tubes round a common one, a power cell and a rack "
        "for a fortnight's stores. What a survey that means to cross a "
        "zone twice sets down in the middle of it.",
        2.8, 6, 20, rest=1.8,
        cost={"credits": 11_000, "alloy": 16, "silicon": 6}),
    CampClass(
        "station", "FIELD STATION", "fabricated",
        "A pressure hut with an airlock, a bench, a charging bay and a "
        "month and a half of stores. Struck and re-pitched it is a "
        "chronicle's worth of ground worked properly.",
        7.5, 12, 45, rest=2.2,
        cost={"credits": 34_000, "alloy": 52, "silicon": 18}),
    CampClass(
        "bole", "BOLE", "grown",
        "A grown shelter that arrives as a bud and opens into a hollow "
        "trunk over a day, breathing for whoever is inside it. It eats "
        "biomass and it mends itself, which on a long survey is the whole "
        "argument.",
        3.4, 8, 28, rest=2.0,
        cost={"credits": 16_000, "biomass": 30, "silicon": 4}),
)
CAMPS_BY_ID = {c.id: c for c in CAMPS}

#: Days a party spends pitching a camp or striking it. Both are a day: it
#: is the same work in the other order.
PITCH_DAYS = 1
