"""Single-seat craft: the small hulls one person flies out of a big one.

A player asked for fighters — a hull a pilot straps into, flown from its own
cockpit, launched off a carrier or a station, and used for the three things
small craft have always been used for: **fighting**, **looking**, and
**fetching**.

They are not ships in the fleet. A craft has no crew, no jump drive and no
hold worth the name; it rides in a cradle on the outside of a hull, with a
hatch through to the cradle deck so a pilot walks out to it in shirtsleeves
(`sim/afoot_program`), and everything it does it does inside one system.

Each class is a few numbers and nothing derived:

- `hull` and `armour` — what it can take, in the same points a ship's layer
  keeps;
- `guns` — the fixed mounts, as (name, dice): a craft fires what it is
  pointed at and has no turrets to traverse;
- `thrust_g`, `rcs`, `slew` — what makes it a fighter rather than a barge:
  the acceleration, the thruster authority and how fast it comes round, fed
  straight into the same `sim/conn` flight the ship's own conn uses;
- `sensor` — how far its array reaches, which is what makes a scout;
- `seats` and `hold_t` — who and what it can carry, which is what makes a
  tender;
- `needs` — the Pilot skill its controls are certified for. A craft with a
  lighter certificate is what a green officer learns in;
- `lands` and `days` — whether it is built to set down on a world at all,
  and how long it keeps a party alive once it has. (The vehicle bays and the
  mast that reaches back to the hull come with the vehicles and the camps
  they are for; a field nothing reads is a field this project deletes.)

**Landing is the same arithmetic the hull's own is** (`sim/landing.py`): a
starship cannot land on a world because a rocky world pulls a hundred and
forty times harder than its drive can push, which is why a party goes down
in a lander and the ship stays in orbit — a decision the code made long
before there was a lander to make it with. A craft's `thrust_g` against the
body's own `gravity` is what decides, with a reserve for the way back up, so
a WASP sets down on a moon and a heavy world wants something built for it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CraftClass:
    """One class of single-seat craft."""

    id: str
    name: str
    #: Whose yard builds it, in the families `data/chassis` already uses.
    family: str
    #: fighter | scout | tender — what it is *for*, which is what the
    #: hangar screen sorts by and what an errand asks for.
    role: str
    blurb: str
    mass_t: float
    hull: int
    armour: int
    guns: tuple
    #: Acceleration under the main drive, in gravities; thruster authority in
    #: m/s a tick; and how fast she comes round, in degrees a second.
    thrust_g: float
    rcs: float
    slew: float
    sensor: float
    #: Reaction mass she carries, in tonnes — the whole of her endurance.
    fuel_t: float
    seats: int
    hold_t: float
    #: The Pilot skill her controls are certified for.
    needs: int
    cost: dict
    #: Built to set down on a world and lift off it again — legs, a sealed
    #: hull and something to keep the heat off. `sim/descent.py` is the act.
    lands: bool = False
    #: Days she keeps her seats alive on the ground: air, water and food.
    days: float = 0.0


#: The Pilot rating nobody may take a craft out without — **trained on the
#: type**, which is level 0 the way this game counts skills (untrained is
#: `checks.UNTRAINED`). A captain holds it, and so does a navigator: they
#: are the officer who flies. A heavier craft asks for a rating above it.
PILOT_SKILL = 0

#: What a craft is worth as salvage, against its build cost.
SALVAGE = 0.35

CRAFT: tuple = (
    CraftClass(
        "wasp", "WASP", "grown", "fighter",
        "A grown interceptor the size of a cutter's launch: two stingers, a "
        "single seat, and enough thrust to be somewhere else. Cradled on the "
        "hull's flank with a hatch through to the cradle deck.",
        18.0, 120, 3, (("stinger", 2), ("stinger", 2)),
        thrust_g=2.4, rcs=1.1, slew=22.0, sensor=2.0, fuel_t=6.0,
        seats=1, hold_t=0.4, needs=PILOT_SKILL,
        cost={"credits": 42_000, "biomass": 30, "silicon": 8},
        lands=True, days=1.0),
    CraftClass(
        "shrike", "SHRIKE", "fabricated", "fighter",
        "A Yards fighter: a welded spar, an armoured tub for the pilot and a "
        "pair of slug cannon. Heavier than a WASP and it stays hit.",
        26.0, 160, 6, (("cannon", 3), ("cannon", 3)),
        thrust_g=2.0, rcs=0.9, slew=17.0, sensor=2.0, fuel_t=8.0,
        seats=1, hold_t=0.6, needs=PILOT_SKILL + 1,
        cost={"credits": 58_000, "alloy": 40, "silicon": 12},
        lands=True, days=1.0),
    CraftClass(
        "mote", "MOTE", "fabricated", "scout",
        "All array and tankage, one gun for manners. What a captain sends to "
        "look at something they would rather not close with.",
        14.0, 90, 2, (("popgun", 1),),
        thrust_g=1.6, rcs=1.0, slew=20.0, sensor=5.0, fuel_t=12.0,
        seats=1, hold_t=0.3, needs=PILOT_SKILL,
        cost={"credits": 36_000, "alloy": 22, "silicon": 18},
        lands=True, days=4.0),
    CraftClass(
        "dory", "DORY", "fabricated", "tender",
        "A ship's boat with a stick: three seats behind the pilot and a hold "
        "for what three people are carrying. Unarmed, and everybody's.",
        22.0, 110, 2, (),
        thrust_g=1.2, rcs=0.8, slew=14.0, sensor=1.5, fuel_t=10.0,
        seats=4, hold_t=3.0, needs=PILOT_SKILL,
        cost={"credits": 30_000, "alloy": 26, "silicon": 6},
        lands=True, days=3.0),
)

#: The landers: what puts a party on a world and brings it back up. A hull
#: cannot (`sim/landing.py`), so these are how anybody stands on a planet.
LANDERS: tuple = (
    CraftClass(
        "isopod", "ISOPOD", "grown", "lander",
        "A grown lander: a segmented shell on six folding legs, sealed "
        "against anything a world can breathe at it, with a hold that opens "
        "into a ramp. Eight aboard, two vehicles under the plates, and "
        "enough of itself to keep them all alive for two months. Her hold takes a "
        "proper survey's supplies and a vehicle on top, and not the season "
        "on the ground a PINNACE carries.",
        40.0, 150, 5, (),
        thrust_g=2.2, rcs=1.0, slew=11.0, sensor=2.5, fuel_t=16.0,
        seats=8, hold_t=28.0, needs=PILOT_SKILL,
        cost={"credits": 54_000, "biomass": 60, "silicon": 14},
        lands=True, days=60.0),
    CraftClass(
        "pinnace", "PINNACE", "fabricated", "lander",
        "The Yards' answer: a welded box with wings it does not need, an "
        "airlock at each end and a crane over the hold. Slower down and "
        "harder to get back up, and it will carry a camp, three vehicles "
        "and twelve people while it does it.",
        62.0, 190, 8, (("popgun", 1),),
        thrust_g=1.8, rcs=0.8, slew=9.0, sensor=2.0, fuel_t=22.0,
        seats=12, hold_t=34.0, needs=PILOT_SKILL,
        cost={"credits": 68_000, "alloy": 70, "silicon": 20},
        lands=True, days=90.0),
    CraftClass(
        "cataphract", "CATAPHRACT", "fabricated", "lander",
        "Built for the worlds nothing else will leave again: a pressure "
        "hull, drives sized for two and a half gravities, and a shell that "
        "shrugs off an atmosphere that eats paint. Deep gravity wells, gas "
        "giants' moons, and the one hull in the Verge that has been down to "
        "a giant's cloud deck and come back.",
        110.0, 260, 12, (("cannon", 2),),
        thrust_g=3.4, rcs=1.2, slew=8.0, sensor=3.0, fuel_t=40.0,
        seats=10, hold_t=26.0, needs=PILOT_SKILL + 1,
        cost={"credits": 140_000, "alloy": 160, "silicon": 40},
        lands=True, days=45.0),
)

CRAFT = CRAFT + LANDERS
CRAFT_BY_ID = {c.id: c for c in CRAFT}

#: What a hull is given to put a party on a world with, at the start.
STARTING_LANDER = "isopod"

#: The reserve a craft keeps over a world's own pull before it will set
#: down: it has to hold the fall *and* get off again with a hold full.
#: Measured against `world/planets` — rocky and ice worlds run 0.09 to 1.30
#: g and gas giants 2.0 to 2.9, so a WASP (2.4 g) sets down on anything but
#: a giant, a DORY (1.2) on light worlds and moons, and a CATAPHRACT (3.4)
#: on the giants nothing else will leave again.
LIFT_RESERVE = 1.35

#: What a hull carries when a captain is given one at the start.
STARTING_CRAFT = "wasp"

#: What each role is for, in the words the screens use.
ROLES = {
    "fighter": "a gun platform with a seat in it",
    "scout": "an array with a seat in it",
    "tender": "a boat with a seat in front",
    "lander": "a hold and a camp, with legs",
}

#: How far a craft may work from the hull it flew off, in km. Past this the
#: cradle is a long swim and the errand is refused: a craft has hours of air
#: and no jump drive.
RANGE_KM = 120_000.0

#: What a sortie costs the hull that launched it, in reaction mass: the
#: cradle's own handling, not the craft's tank.
LAUNCH_T = 0.2
