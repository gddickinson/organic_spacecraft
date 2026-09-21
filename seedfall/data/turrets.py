"""What it is like to sit behind one of the ship's guns and work it by hand.

Every armament in `data/armaments.py` already says what it *does* — damage, the
range bands it works in, the heat it makes, the traits it carries — and none of
it says what it is like to *aim*. A Point-Defence Cannon and a Fusion Lance
have the same entry in the fire control and could not be less alike at the
trigger: one is a hose you walk onto a target, the other is a single shot that
takes a second to charge and does not miss twice.

This is the other half of a weapon: how fast the mounting swings, how far it
will train before the hull is in the way, how long the round takes to get
there, how quickly it can be fired and how hot that makes it. The numbers the
gun already had are **not** repeated here — `armaments.ARMAMENTS` is still the
one place damage and range live, and `for_part` looks them up.

**The three that decide whether a gun is fun to fire**, and why each is where
it is:

- **`muzzle_kms`** is why you lead a target. A slug battery throws at 4 km/s,
  which at ten kilometres is two and a half seconds of flight — long enough
  that a corvette crossing at 300 m/s is three quarters of a kilometre from
  where the sight says it is. A beam is instant and is marked by a zero.
- **`traverse`** is why position matters. At 38°/s a point-defence mount can
  follow a missile across the sky; at 9°/s a fusion lance cannot follow
  anything, and the pilot has to bring the hull round for you.
- **`arc`** is the hull. A gun in a blister on the beam sees a hemisphere; a
  spinal mount sees a cone, and the whole of the rest of the sky is the ship
  you are standing on.
"""

from __future__ import annotations

from dataclasses import dataclass

from .armaments import ARMAMENTS

#: How a round reads as it crosses the sky. The same four `sim/gunfire.py`
#: draws a turn's volleys with, so a tracer and a battle log agree about what
#: left the tube.
BEAM, ROUND, SEEKING, FLAK = "beam", "round", "seeking", "flak"


@dataclass(frozen=True)
class TurretKind:
    """One gun, as the hands that work it find it."""

    #: The armament this is a seat on — `armaments.ARMAMENTS`'s id.
    part: str
    #: What the seat is called. Not the weapon's name: a captain mans "the
    #: dorsal cannon", and which part is bolted into it is the yard's business.
    seat: str
    #: Degrees a second the mounting swings, across and up.
    traverse: float
    elevate: float
    #: How far it will train off its rest bearing before the hull is in the
    #: way, in degrees; 180 is a blister that sees everything.
    arc: float
    #: How far it will look up and down, in degrees.
    up: float
    down: float
    #: Kilometres a second. **Zero is a beam** — it arrives when it is fired,
    #: and the sight needs no lead.
    muzzle_kms: float
    #: Rounds a minute, how many come out per pull, and the cone they go into.
    rpm: float
    burst: int
    spread: float
    #: What a pull costs in heat, and what a second of not firing gives back.
    heat: float
    cool: float
    #: Rounds in the mounting before it has to be fed, and how long that
    #: takes. **Zero rounds is a gun that draws on the ship** — a beam off the
    #: reactor, which cannot run out and can only overheat.
    rounds: int
    reload_s: float
    #: How the tracer reads.
    look: str
    #: One line at the seat, in the words a gunner would use.
    note: str


#: Every gun a captain can sit behind, in the order a gunnery school would
#: teach them: the one you learn on first.
#:
#: **Traverse is the axis these are balanced on.** Damage is the armament's
#: and is not restated; what makes a choice here is how much sky the mounting
#: covers a second against how much a hit is worth. The point-defence cannon
#: does eight and swings at 38°/s; the fusion lance does a hundred and ten and
#: swings at seven, so it kills whatever the pilot puts in front of it and
#: nothing else. Everything between those two is a real decision.
TURRETS: tuple = (
    TurretKind(
        "pdc", "Point-defence cannon", 38.0, 30.0, 180.0, 85.0, 70.0,
        3.2, 480.0, 3, 1.6, 2.0, 7.0, 900, 4.0, FLAK,
        "Radar-cued and hungry. Walk it onto the target and hold it there."),
    TurretKind(
        "slug_battery", "Slug battery", 22.0, 18.0, 150.0, 70.0, 60.0,
        4.0, 90.0, 1, 0.5, 5.0, 4.5, 240, 5.0, ROUND,
        "Slag at four kilometres a second. Lead it, and it is free."),
    TurretKind(
        "mag_lance", "Magnetite lance", 26.0, 20.0, 150.0, 65.0, 55.0,
        0.0, 45.0, 1, 0.0, 7.0, 4.0, 0, 0.0, BEAM,
        "It arrives when you fire it, and it puts their computers to sleep."),
    TurretKind(
        "lixiviant", "Lixiviant sprayer", 30.0, 24.0, 160.0, 75.0, 65.0,
        1.1, 150.0, 2, 3.0, 3.0, 5.0, 300, 4.5, ROUND,
        "Close work. It does nothing to a hull and everything to what is on it."),
    TurretKind(
        "photic_flash", "Photic flash organ", 34.0, 28.0, 180.0, 85.0, 80.0,
        0.0, 30.0, 1, 0.0, 4.0, 5.0, 0, 0.0, BEAM,
        "It hurts nobody. The next thing they shoot at you misses."),
    TurretKind(
        "railgun", "Railgun", 14.0, 11.0, 110.0, 45.0, 35.0,
        12.0, 24.0, 1, 0.15, 12.0, 3.0, 60, 7.0, ROUND,
        "Eight megajoules, once every two and a half seconds. Make it count."),
    TurretKind(
        "mass_driver", "Mass driver", 12.0, 9.0, 100.0, 40.0, 30.0,
        9.0, 20.0, 1, 0.2, 13.0, 2.8, 48, 8.0, ROUND,
        "A quarry gun. Slow to train, and it takes the front off things."),
    TurretKind(
        "particle_beam", "Particle beam", 16.0, 13.0, 120.0, 50.0, 40.0,
        0.0, 36.0, 1, 0.0, 16.0, 2.6, 0, 0.0, BEAM,
        "It treats an ablative bumper as a suggestion, and it cooks the ship."),
    TurretKind(
        "fusion_lance", "Fusion lance", 7.0, 6.0, 70.0, 30.0, 22.0,
        0.0, 15.0, 1, 0.0, 26.0, 2.2, 0, 0.0, BEAM,
        "Four seconds between shots. The pilot brings you the target."),
    TurretKind(
        "missile_rack", "Missile rack", 40.0, 34.0, 180.0, 88.0, 80.0,
        0.9, 20.0, 1, 0.0, 6.0, 4.0, 24, 9.0, SEEKING,
        "Point it near enough and let go; the round does the rest."),
    TurretKind(
        "spore_swarm", "Spore pod launcher", 32.0, 26.0, 170.0, 80.0, 70.0,
        0.7, 24.0, 1, 0.0, 5.0, 4.5, 30, 8.0, SEEKING,
        "Every treaty in the sector bans these. Three factions field them."),
    TurretKind(
        "breach_torpedo", "Breach torpedo", 20.0, 16.0, 140.0, 60.0, 50.0,
        0.6, 10.0, 1, 0.0, 9.0, 3.4, 12, 11.0, SEEKING,
        "One torpedo, one hole. It is slow, and it is patient."),
    TurretKind(
        "coherent_beam", "Coherent beam", 24.0, 19.0, 130.0, 55.0, 45.0,
        0.0, 40.0, 1, 0.0, 11.0, 3.2, 0, 0.0, BEAM,
        "Steady as a lamp. Hold it on one plate and the plate goes."),
    TurretKind(
        "xeno_resonator", "Xenolith resonator", 18.0, 15.0, 140.0, 60.0, 50.0,
        0.0, 18.0, 1, 0.0, 10.0, 3.0, 0, 0.0, BEAM,
        "Nobody is sure what it does to a hull until it has done it."),
)

TURRET_BY_PART = {t.part: t for t in TURRETS}

#: What a seat is when the armament bolted into it has no entry of its own.
#: A mounting is a mounting: it swings, it has an arc, and the gun in it does
#: whatever `armaments` says it does.
DEFAULT = TurretKind(
    "", "Gun mounting", 24.0, 19.0, 150.0, 65.0, 55.0,
    3.0, 60.0, 1, 0.8, 6.0, 4.0, 200, 5.0, ROUND,
    "A mounting with something in it. Work it like any other.")


def for_part(part_id: str) -> TurretKind:
    """The seat for this armament. Never None — see `DEFAULT`."""
    return TURRET_BY_PART.get(part_id, DEFAULT)


def weapon_for(part_id: str):
    """The armament itself, for the damage and the range it keeps there.

    **One place for a number.** The turret says how the gun is worked and
    `data/armaments.py` says what it does; a second copy of the damage here
    is the fault this project has been bitten by more than any other.
    """
    part = next((p for p in ARMAMENTS if p.id == part_id), None)
    return part.wpn if part is not None else None


def seconds_between(kind: TurretKind) -> float:
    """How long the gun makes you wait between pulls."""
    return 60.0 / max(1.0, kind.rpm) * max(1, kind.burst)


def manned() -> tuple:
    """Every armament a captain can take the seat of, by id."""
    return tuple(t.part for t in TURRETS)
