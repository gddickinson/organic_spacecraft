"""Dead hulls adrift in the Verge, and what is still aboard them.

The sector has fought, traded and been overgrown for a long time, and until
now it had left nothing behind: a wreck was a line in the log, a salvage
figure, and gone. These are the hulls that stayed. Each kind is a real hull
class from the registry (`data/hulls_*.py`) that met a particular end, and
what is aboard follows from the end it met:

- `air` — whether anything aboard still breathes. A holed hull is vacuum
  from end to end, and a party without suits cannot walk it.
- `cast` — who is aboard now: archetypes from `data/afoot_folk.py`, as
  (archetype, least, most). Scavengers got here first; the Bloom never left.
- `rooms` — rooms the end added: a relic vault, the Bloom's heart.
- `loot` — how generous the lockers are, against a working hull's one.
- `where` — "verge", "reaches" or "bloom": what a system must be for this
  kind to be found adrift in it.

Which systems have one, and which, is `sim/afoot_sites.derelict`: seeded on
the chronicle and the system alone, so a wreck is where it was on the
chart the next time you look.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Derelict:
    """One way a hull ends up adrift."""

    id: str
    name: str
    chassis: str
    air: bool
    cast: tuple
    rooms: tuple = ()
    loot: float = 1.0
    where: str = "verge"
    #: How often this is the kind found, among those a system allows.
    weight: float = 1.0
    blurb: str = ""
    #: Not a hull but a structure: the establishment (`data/establishments`)
    #: or holding class (`data/colonies`) it was. Laid out as one, dead.
    structure: str = ""


DERELICTS: tuple = (
    Derelict("survey_hulk", "a Charter survey hull", "meridian", False,
             (("scavenger", 0, 2),), loot=1.3, weight=3.0,
             blurb="Holed forty years ago and never recovered. The Charter "
                   "wrote her off; her instruments are still aboard."),
    Derelict("liner_wreck", "a liner that never arrived", "caravel", False,
             (("scavenger", 0, 1),), loot=1.6, weight=2.0,
             blurb="Somebody's passage, and everybody's luggage."),
    Derelict("raider_hulk", "a raider's stripped corvette", "pike", True,
             (("raider", 2, 4),), loot=1.2, weight=2.0,
             blurb="Not as dead as she looks. The lights are on in the "
                   "aft section."),
    Derelict("choir_probe", "a silent Dry Choir probe", "cantor", False,
             (("sentry", 0, 1),), loot=1.0, weight=1.0,
             blurb="No crew, no air, and a core that may still be thinking."),
    Derelict("bloom_freighter", "a freighter the Bloom took", "atlas", True,
             (("thrall", 2, 4), ("creeper", 1, 3)), rooms=("nest",),
             loot=1.1, where="bloom", weight=3.0,
             blurb="The hull is warm. The walls are moving."),
    Derelict("xeno_hulk", "a hulk nobody human built", "revenant", True,
             (("sentry", 0, 2),), rooms=("vault",), loot=0.8,
             where="reaches", weight=3.0,
             blurb="It holds air it was never meant to hold, and something "
                   "in a sealed chamber is still keeping it."),
)

#: The dead that are not hulls, and a hull that died of something catching.
DERELICTS += (
    Derelict("plague_ship", "a hospital ship under quarantine", "lazaret",
             True, (("scavenger", 0, 1),), rooms=("isolation", "isolation"),
             loot=1.5, weight=1.5,
             blurb="Her quarantine flag is still flying. Her medical stores "
                   "are still full, and so is her isolation ward."),
    Derelict("gutted_yard", "a yard that went under mid-hull", "", False,
             (("scavenger", 1, 3),), loot=1.4, weight=1.0,
             structure="shipyard",
             blurb="Bankrupt, stripped, and left in orbit. The slips still "
                   "hold the bones of the last hull."),
    Derelict("dead_habitat", "a habitat ring that went quiet", "", True,
             (("scavenger", 1, 2), ("holdout", 0, 2)), loot=1.2,
             weight=1.5, structure="coral_reef",
             blurb="Two thousand people lived here. The ring still turns, "
                   "and somebody is still living in part of it."),
)
DERELICT_BY_ID = {d.id: d for d in DERELICTS}

#: How often a system has a dead hull adrift in it: one with a quay (the
#: harbour tows its wrecks away) and one without.
ODDS_WITH_PORT = 0.12
ODDS_WITHOUT = 0.35

#: What matching and boarding a dead hull costs in time, in days.
BOARDING_DAYS = 0.25
