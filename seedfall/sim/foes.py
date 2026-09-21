"""What is out there when you are behind a gun, and what it is doing about you.

A `Contact` is anything a gunner can see: a corvette making a run, a hub's
point-defence blister, a planetary battery that cannot move and does not have
to, a mining rig that would rather not be here, a missile with your name on
it, or a consort holding station off your beam.

They are all one record on purpose. The sight has to bracket them all, the
director has to lead them all, and the gun has to be able to kill any of them
— so "can this be shot at" is a field and not a class hierarchy. What differs
is `behaviour`, which is one function per way of moving, and `guns`, which is
what it does back.

**Everything is in the player hull's frame, in kilometres**, and velocities
are km/s. The hull does not move in that frame by definition; the sky moves
around it, which is both what a gunner sees out of the blister and what makes
the arithmetic simple enough to be right.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

#: How the kinds read, and what each is worth to a gunner. The tuple is
#: `(hull points, radius in km, what it is worth killing)` — the last one is
#: the drill's score, and it is *not* the hull points: a missile has four
#: points and stopping one is the whole job, while a mining rig has six
#: hundred and shooting it is barely gunnery at all.
KINDS = {
    "hull": (90.0, 0.11, 60),
    "corvette": (48.0, 0.07, 45),
    "drone": (14.0, 0.03, 25),
    "missile": (4.0, 0.015, 40),
    "torpedo": (9.0, 0.03, 60),
    "station": (900.0, 1.10, 200),
    "blister": (36.0, 0.05, 35),
    "battery": (150.0, 0.22, 90),
    "rig": (320.0, 0.55, 70),
    "dome": (260.0, 0.40, 80),
    "buoy": (12.0, 0.06, 5),
    "consort": (120.0, 0.12, 0),
}

#: What a contact's own guns are like. Reach is in kilometres, `every` is
#: seconds between shots, and `dmg` is what it takes off the hull you are
#: standing on. Deliberately thinner than the player's armament table: these
#: are the *other* side of the engagement and their job is to make the sky
#: dangerous, not to be a second weapons catalogue.
@dataclass(frozen=True)
class Gun:
    name: str
    dmg: float
    reach_km: float
    every: float
    look: str = "round"
    #: Fires a seeker that becomes a contact of its own rather than resolving
    #: on the spot — which is what gives a point-defence gunner something to
    #: do.
    launches: str = ""


LIGHT = Gun("autocannon", 3.0, 6.0, 1.4, "flak")
MEDIUM = Gun("slug gun", 7.0, 11.0, 2.6)
HEAVY = Gun("mass driver", 16.0, 18.0, 4.5)
SIEGE = Gun("siege battery", 34.0, 26.0, 6.5, "beam")
LANCE = Gun("beam lance", 12.0, 14.0, 3.0, "beam")
RACK = Gun("missile rack", 0.0, 22.0, 7.0, "seeking", launches="missile")
TUBES = Gun("torpedo tubes", 0.0, 24.0, 11.0, "seeking", launches="torpedo")


#: What a subsystem does for the thing it is bolted to, and what killing it
#: takes away. Lifted straight from the shape FreeSpace 2 made standard: a
#: capital ship is not a hit-point bar, it is a set of *places* — and the
#: gunnery in "attack the station" is choosing which of them to take off it
#: first, not holding the trigger down until a number reaches zero.
#:
#: `share` is how much of the whole thing's hull the piece is worth, so a
#: rig's refinery is most of it and a blister is a tenth.
SUBSYSTEMS = {
    "turret": ("Turret", 0.10, "its guns fall silent"),
    "sensor": ("Sensor mast", 0.08, "its shooting goes wild"),
    "reactor": ("Reactor", 0.18, "it loses power and burns"),
    "engine": ("Drive", 0.12, "it can no longer move"),
    "magazine": ("Magazine", 0.10, "it cannot reload"),
    "refinery": ("Refinery", 0.30, "the workings stop"),
    "dock": ("Docking gantry", 0.14, "nothing can put in"),
    "hab": ("Habitat ring", 0.20, "the people are in the open"),
}


@dataclass
class Subsystem:
    """One place on a contact that can be shot off it on its own."""

    id: str
    kind: str
    name: str = ""
    hp: float = 0.0
    max_hp: float = 0.0
    #: Where it sits on the contact, as a fraction of its radius in the
    #: contact's own frame — so a gunner can see which end to shoot at.
    at: tuple = (0.0, 0.0, 0.0)
    dead: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            self.name = SUBSYSTEMS.get(self.kind, ("Fitting", 0.1, ""))[0]

    @property
    def share(self) -> float:
        return max(0.0, min(1.0, self.hp / self.max_hp)) if self.max_hp else 0.0

    @property
    def loss(self) -> str:
        return SUBSYSTEMS.get(self.kind, ("", 0.0, "it is hurt"))[2]


def fit(contact: "Contact", *kinds: str) -> "Contact":
    """Give a contact the places that can be shot off it, and hand it back.

    Their hull comes out of the whole, so a station with four turrets, a
    sensor mast and a reactor is *mostly* its fittings — which is the point:
    a gunner who takes the turrets off it first is not doing less damage,
    they are doing the damage that stops it shooting back.
    """
    made, spread = [], len(kinds) or 1
    for index, kind in enumerate(kinds):
        share = SUBSYSTEMS.get(kind, ("", 0.1, ""))[1]
        angle = math.tau * index / spread
        made.append(Subsystem(
            id=f"{contact.id}:{kind}{index}", kind=kind,
            hp=contact.max_hp * share, max_hp=contact.max_hp * share,
            at=(math.cos(angle) * 0.7, math.sin(angle) * 0.7,
                0.35 if index % 2 else -0.2)))
    contact.parts = tuple(made)
    return contact


@dataclass
class Contact:
    """One thing in the sky, and what it is doing."""

    id: str
    name: str
    kind: str = "hull"
    #: Where it is and how it is moving, in the player hull's frame, km.
    at: tuple = (0.0, 12.0, 0.0)
    vel: tuple = (0.0, 0.0, 0.0)
    hp: float = 0.0
    max_hp: float = 0.0
    radius_km: float = 0.0
    hostile: bool = True
    faction: str = ""
    #: How it moves: run · strafe · stand · home · fixed · escort.
    behaviour: str = "stand"
    #: How close it wants to be, in km, and how fast it moves when it has a
    #: choice. A fixed contact ignores both.
    stand_km: float = 8.0
    pace: float = 0.25
    guns: tuple = ()
    #: Seconds until each gun speaks again, by index.
    ready: list = field(default_factory=list)
    dead: bool = False
    #: What killed it, for the drill's account of itself.
    killed_by: str = ""
    #: Seconds a seeker has left before it runs out of fuel and is gone.
    fuse: float = 0.0
    #: The places that can be shot off it on their own — see `fit`.
    parts: tuple = ()

    def __post_init__(self) -> None:
        points, radius, _worth = KINDS.get(self.kind, KINDS["hull"])
        if not self.max_hp:
            self.max_hp = points
        if not self.hp:
            self.hp = self.max_hp
        if not self.radius_km:
            self.radius_km = radius
        if not self.ready:
            self.ready = [0.0 for _g in self.guns]

    @property
    def worth(self) -> int:
        return KINDS.get(self.kind, KINDS["hull"])[2]

    @property
    def range_km(self) -> float:
        return math.dist(self.at, (0.0, 0.0, 0.0))

    @property
    def share(self) -> float:
        """How much of it is left, 0..1."""
        return max(0.0, min(1.0, self.hp / self.max_hp)) if self.max_hp else 0.0


def make(cid: str, name: str, kind: str, at, **rest) -> Contact:
    """One contact, with the kind's own weight and size unless told otherwise."""
    return Contact(id=cid, name=name, kind=kind, at=tuple(at), **rest)


def hurt(contact: Contact, amount: float, by: str = "the gun",
         part: str = "") -> float:
    """Take damage off a contact, or off one named place on it.

    A hit on a subsystem costs the whole thing too — a turret blown off a
    station is a hole in the station — but the piece takes it first and dies
    first, which is what makes aiming at one worth the trouble.
    """
    if contact.dead or amount <= 0.0:
        return 0.0
    if part:
        piece = next((p for p in contact.parts
                      if p.id == part and not p.dead), None)
        if piece is not None:
            gone = min(piece.hp, amount)
            piece.hp -= gone
            if piece.hp <= 0.0:
                piece.dead = True
    took = min(contact.hp, amount)
    contact.hp -= took
    if contact.hp <= 0.0:
        contact.dead = True
        contact.killed_by = by
    return took


def working(contact: Contact, kind: str) -> int:
    """How many of a kind of fitting are still on it."""
    return sum(1 for p in contact.parts if p.kind == kind and not p.dead)


def silenced(contact: Contact) -> bool:
    """Has it lost every turret it had? Then it cannot shoot at all."""
    turrets = [p for p in contact.parts if p.kind == "turret"]
    return bool(turrets) and not any(not p.dead for p in turrets)


def blinded(contact: Contact) -> float:
    """What losing its sensors does to its aim, as a multiplier.

    A mast is the difference between a battery that tracks you and one that
    fires where you were. Nothing at all when it never had one — a missile
    does not carry a sensor mast, it *is* one.
    """
    masts = [p for p in contact.parts if p.kind == "sensor"]
    if not masts:
        return 1.0
    alive = sum(1 for p in masts if not p.dead)
    return 0.35 + 0.65 * (alive / len(masts))


def crippled(contact: Contact) -> bool:
    """Has it lost the drive it needs to move at all?"""
    drives = [p for p in contact.parts if p.kind == "engine"]
    return bool(drives) and not any(not p.dead for p in drives)


# ── how each kind moves ────────────────────────────────────────────────────

def _toward(at, want_km: float, pace: float) -> tuple:
    """A velocity that closes to `want_km` and holds there."""
    span = math.dist(at, (0.0, 0.0, 0.0))
    if span < 1e-6:
        return (0.0, 0.0, 0.0)
    unit = tuple(-c / span for c in at)
    gap = span - want_km
    if abs(gap) < 0.2:
        return (0.0, 0.0, 0.0)
    push = pace if gap > 0 else -pace
    return tuple(c * push for c in unit)


def _across(at, pace: float) -> tuple:
    """A velocity across the line of sight — the hardest thing to lead."""
    span = math.dist(at, (0.0, 0.0, 0.0))
    if span < 1e-6:
        return (0.0, 0.0, 0.0)
    unit = tuple(c / span for c in at)
    # Any vector not along the line of sight; the world's vertical unless the
    # contact is directly above, in which case the nose does instead.
    seed = (0.0, 1.0, 0.0) if abs(unit[2]) > 0.9 else (0.0, 0.0, 1.0)
    side = (unit[1] * seed[2] - unit[2] * seed[1],
            unit[2] * seed[0] - unit[0] * seed[2],
            unit[0] * seed[1] - unit[1] * seed[0])
    length = math.dist(side, (0.0, 0.0, 0.0)) or 1.0
    return tuple(c / length * pace for c in side)


def steer(contact: Contact, seconds: float, rng) -> None:
    """One slice of a second of whatever this contact is doing.

    Six behaviours, and the difference between them is the whole difficulty
    of the drill: a contact that *stands* is target practice, one that
    *strafes* has to be led, and one that *runs* is only in your arc for the
    few seconds of its pass.
    """
    if contact.dead:
        return
    if crippled(contact):
        contact.vel = (0.0, 0.0, 0.0)
        return
    how = contact.behaviour
    if how == "fixed":
        contact.vel = (0.0, 0.0, 0.0)
    elif how == "stand":
        contact.vel = _toward(contact.at, contact.stand_km, contact.pace)
    elif how == "strafe":
        close = _toward(contact.at, contact.stand_km, contact.pace * 0.4)
        across = _across(contact.at, contact.pace)
        contact.vel = tuple(a + b for a, b in zip(close, across))
    elif how == "run":
        # In hard, past, and round again. The pass is the whole of it: a
        # gunner gets the seconds between "inside my arc" and "gone".
        span = contact.range_km
        if span <= max(0.8, contact.radius_km * 4):
            contact.behaviour = "away"
            contact.vel = tuple(-c for c in contact.vel) or (0.0, -1.0, 0.0)
        else:
            contact.vel = _toward(contact.at, 0.0, contact.pace)
    elif how == "away":
        if contact.range_km >= contact.stand_km * 1.6:
            contact.behaviour = "run"
        else:
            span = contact.range_km or 1.0
            contact.vel = tuple(c / span * contact.pace for c in contact.at)
    elif how == "home":
        span = contact.range_km or 1.0
        contact.vel = tuple(-c / span * contact.pace for c in contact.at)
        contact.fuse = max(0.0, contact.fuse - seconds)
        if contact.fuse <= 0.0 and contact.range_km > 0.3:
            contact.dead = True
            contact.killed_by = "burnt out"
    elif how == "escort":
        contact.vel = _toward(contact.at, contact.stand_km, contact.pace * 0.5)
        if rng.chance(0.02):
            contact.vel = _across(contact.at, contact.pace * 0.4)
    contact.at = tuple(p + v * seconds for p, v in zip(contact.at, contact.vel))


def arriving(contact: Contact) -> bool:
    """Has a seeker reached the hull it was aimed at?"""
    return (contact.behaviour == "home" and not contact.dead
            and contact.range_km <= 0.35)


def can_shoot(contact: Contact, index: int) -> bool:
    """Is this gun loaded, in reach, and pointing at something it can hit?"""
    if contact.dead or not contact.hostile or index >= len(contact.guns):
        return False
    if silenced(contact):
        return False
    gun = contact.guns[index]
    return (contact.ready[index] <= 0.0
            and contact.range_km <= gun.reach_km)


def cool(contact: Contact, seconds: float) -> None:
    """Count every gun's clock down."""
    contact.ready = [max(0.0, t - seconds) for t in contact.ready]


def aim_quality(contact: Contact, gun: Gun, evade: float) -> float:
    """How likely this contact's shot is to land on the hull you are on.

    Falls off with range across the gun's own reach and with whatever the
    hull does to make itself hard to hit. Deliberately generous at close
    quarters: a corvette at two kilometres should be frightening.
    """
    share = min(1.0, contact.range_km / max(0.5, gun.reach_km))
    return max(0.04, (0.86 - 0.42 * share) * blinded(contact)
               * (1.0 - max(0.0, min(0.8, evade))))

