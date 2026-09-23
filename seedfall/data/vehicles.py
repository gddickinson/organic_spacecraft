"""What a landing party crosses ground in.

`sim/expedition.py` has always had a rover: a number from nought to ten that
hazards knocked down, a day's work put back, and which bought exactly one
thing — a day off the cost of a step while it was above eight. It was not a
machine. It had no class, no mass, no seats, no reach, and no opinion about
the nine terrains a party walks over, so a dune sea and a scarp were the same
problem to it and a party that owned nothing crossed them just as well.

A vehicle here is a thing you buy, carry down in a lander's hold, drive, wear
out and mend. Each class is a few numbers and nothing derived:

- `crosses` — the terrains (`data/expedition.TERRAIN`) it is *made* for: a
  day off the step, the way tracks are off-road or a hull is on ice;
- `refuses` — the terrains it simply cannot enter, so the party leaves it at
  the camp and walks, which is what a scarp does to wheels;
- `mass_t` — what it takes out of the lander's hold, against the supplies it
  is competing with;
- `seats` and `hold_t` — who rides and what rides with them;
- `needs_air` — whether it flies or floats on something, and so is dead
  weight on an airless world (`sim/profile` says which those are);
- `wear` — how hard it is on itself, as the share of a hazard's toll it
  actually takes;
- `needs` — the Drive rating its controls want, on the same ladder
  `data/craft.PILOT_SKILL` uses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleClass:
    """One class of surface vehicle."""

    id: str
    name: str
    #: Whose yard builds it, in the families `data/chassis` already uses.
    family: str
    blurb: str
    mass_t: float
    seats: int
    hold_t: float
    #: Terrain ids it is made for, and those it cannot enter at all.
    crosses: tuple
    refuses: tuple
    #: Dead weight where there is nothing to fly or float on.
    needs_air: bool
    #: The share of a hazard's toll this machine actually takes.
    wear: float
    #: The Drive rating its controls are certified for.
    needs: int
    cost: dict


#: What a machine asks of whoever drives it, on the skill ladder
#: `data/careers.SKILLS` already carries a **drive** entry for — "anything
#: with wheels or tracks on a surface", a skill people have had since the
#: lifepath was written and nothing has ever read.
#:
#: Wheels, tracks and legs ask nothing: `ANYBODY` is `checks.UNTRAINED`, so
#: a party with a rover and no driver among them still gets in and drives
#: it badly. A lift fan is a certificate (`DRIVE_SKILL`, trained) and a
#: three-seat flyer over broken ground is a rating above that.
ANYBODY, DRIVE_SKILL = -3, 0

#: What a vehicle is worth back against its build cost, the same share a
#: craft fetches (`data/craft.SALVAGE`) and for the same reason.
SALVAGE = 0.35

#: Condition runs nought to ten, as `Expedition.rover` always has. This is
#: what a machine comes out of the yard at, and what it is worth mending to.
WHOLE = 10

#: A day off the step on ground a machine is made for; a day *on* where a
#: party is walking because their machine would not go there. Sized against
#: `data/expedition.TERRAIN`, whose costs are one to three days.
GOOD_GROUND, ON_FOOT = 1, 1

VEHICLES: tuple = (
    VehicleClass(
        "rover", "ROVER", "fabricated",
        "Six wheels, a roll cage and a bench. What every yard in the Verge "
        "sells and what every survey has had one of since the first of "
        "them: quick over flat ground, useless against a wall.",
        3.5, 4, 1.5,
        crosses=("plain", "basin", "dunes"),
        refuses=("scarp", "crevasse"),
        needs_air=False, wear=1.0, needs=ANYBODY,
        cost={"credits": 9_000, "alloy": 14, "silicon": 4}),
    VehicleClass(
        "crawler", "CRAWLER", "fabricated",
        "Tracks, a winch and a heated cab. It will go up a scarp at walking "
        "pace and across a crevasse field on its belly, and it will take "
        "all day about it.",
        9.0, 6, 4.0,
        crosses=("ridge", "scarp", "shelf", "crevasse"),
        refuses=(),
        needs_air=False, wear=0.6, needs=ANYBODY,
        cost={"credits": 19_000, "alloy": 34, "silicon": 8}),
    VehicleClass(
        "skiff", "SKIFF", "fabricated",
        "A ground-effect hull that floats a metre over whatever it is "
        "crossing, which makes a dune sea a road and a standing forest a "
        "wall. Needs something to push against.",
        5.0, 4, 2.0,
        crosses=("dunes", "basin", "plain", "shelf"),
        refuses=("forest", "scarp"),
        needs_air=True, wear=1.2, needs=DRIVE_SKILL,
        cost={"credits": 16_000, "alloy": 20, "silicon": 10}),
    VehicleClass(
        "kite", "KITE", "fabricated",
        "A fan-lift flyer with three seats and a hook. Nothing on the "
        "ground is in its way at all — and on a world with no air it is a "
        "very expensive tent.",
        6.0, 3, 0.8,
        crosses=("plain", "ridge", "crevasse", "vent", "basin", "forest",
                 "shelf", "scarp", "dunes"),
        refuses=(),
        needs_air=True, wear=1.4, needs=DRIVE_SKILL + 1,
        cost={"credits": 28_000, "alloy": 22, "silicon": 22}),
    VehicleClass(
        "strider", "STRIDER", "grown",
        "Grown legs on a grown frame, six of them, with a howdah between "
        "the shoulders. It eats what the hold eats, it does not care "
        "whether there is air, and it will climb anything a person could "
        "climb if a person were four metres tall.",
        7.0, 2, 2.5,
        crosses=("ridge", "scarp", "forest", "crevasse", "vent"),
        refuses=(),
        needs_air=False, wear=0.5, needs=ANYBODY,
        cost={"credits": 22_000, "biomass": 40, "silicon": 6}),
)
VEHICLES_BY_ID = {v.id: v for v in VEHICLES}

#: What a hull is given to cross ground with at the start: the plain rover
#: that has been implied by `Expedition.rover` since the first landing.
STARTING_VEHICLE = "rover"
