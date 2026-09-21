"""A gun with somebody sitting behind it: where it points, and what a pull costs.

The game has had guns since the first engagement and has never had a *gunner*.
`sim/gunnery.py` chooses which mounts speak in a turn and `sim/shooting.py`
resolves what they did; between the choice and the result there was nothing at
all, because a turn-based volley has no room for anything. This is that room.

A `Turret` is a mounting with a bearing, an elevation, a temperature and a
magazine, and it moves in seconds rather than turns. Three ways to point it,
and a gunner uses all three in one engagement:

- **The stick.** `swing_x` and `swing_y` are -1..1, held by a hand or a key,
  and each tick moves the gun at the mounting's own rate. This is how you
  cover a sky you have not found anything in yet.
- **The lock.** `locked` names a contact, and the mounting is driven onto
  `gunsight.solution`'s *lead* point — not the target, the place the target
  will be when the round arrives. A director is what a gun crew has instead
  of superhuman reflexes, and it is still the gunner who decides when to fire.
- **A laid order.** `order` puts the aim somewhere and lets the mounting find
  it, which is what the ship's computer does at a seat nobody is sitting in.

**Nothing here is saved.** A drill and a boarding action are both things you
are in the middle of for seconds, not days, and the chronicle's clock does not
move while either is happening — the same ground `sim/battle_state.py` stands
on for keeping a battle off the `Game`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..data import turrets as kinds
from . import gunsight

#: Heat at which the mounting stops answering the trigger, and the fraction it
#: has to fall back to before it will fire again.
#:
#: **Derived from the guns, not chosen.** The hottest thing a captain can sit
#: behind is the fusion lance at 26 a pull against 2.2 a second of cooling, so
#: a hundred is four pulls held down and about forty seconds to clear — long
#: enough that holding the trigger is a decision, short enough that the fight
#: is not over before the gun is. A point-defence cannon at 2 a pull never
#: reaches it, which is what a point-defence cannon is for.
COOKED = 100.0
CLEARED = 0.55

#: How far off the aim the mounting may be and still let the trigger work.
#: A gun that refused every shot that was not perfect would refuse the snap
#: shots that are most of gunnery; this is the bar for "pointing at it".
LOOSE = 12.0


@dataclass
class Shot:
    """One pull of the trigger, and what it did. Drawn, then thrown away."""

    at: tuple = (0.0, 0.0, 0.0)          # where it was aimed, hull frame
    frm: tuple = (0.0, 0.0, 0.0)         # the muzzle
    target: str = ""
    look: str = kinds.ROUND
    hit: bool = False
    damage: float = 0.0
    off: float = 0.0                     # degrees off the aim
    range_km: float = 0.0
    seconds: float = 0.0                 # time of flight; 0 for a beam
    why: str = ""                        # empty unless the pull was refused


@dataclass
class Turret:
    """One mounting on one hull, and the state of the hands on it."""

    part: str = "pdc"
    #: What this seat is called on the ship, and where it sits on the hull in
    #: half-lengths (`data/mounts.py`'s frame). The position is why a dorsal
    #: gun sees over the spine and a ventral one does not.
    seat: str = ""
    at: tuple = (0.0, 0.0, 0.9)
    #: Whose hull it is bolted to. Empty is your own; a name is somebody
    #: else's, which is how a captain takes over a consort's gun.
    hull: str = ""
    #: Where it points now, and where it is being told to point.
    bearing: float = 0.0
    elevation: float = 0.0
    want_bearing: float = 0.0
    want_elevation: float = 0.0
    #: The stick, -1..1 on each axis, held between ticks.
    swing_x: float = 0.0
    swing_y: float = 0.0
    #: The contact the director is on, by id. Empty is hands-only.
    locked: str = ""
    #: The trigger, held down.
    firing: bool = False
    #: Temperature, seconds until the next pull, and the magazine.
    heat: float = 0.0
    cooldown: float = 0.0
    rounds: int = 0
    reloading: float = 0.0
    #: Cooked off and waiting to come back below `CLEARED`.
    jammed: bool = False
    #: What this seat has done, for the drill to score.
    fired: int = 0
    hits: int = 0
    dealt: float = 0.0
    log: list = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.rounds:
            self.rounds = self.kind.rounds
        if not self.seat:
            self.seat = self.kind.seat

    @property
    def kind(self):
        return kinds.for_part(self.part)

    @property
    def weapon(self):
        return kinds.weapon_for(self.part)


def make(part: str, seat: str = "", at=(0.0, 0.0, 0.9), hull: str = "") -> Turret:
    """A seat, fed and cold, pointing where the hull is pointing."""
    return Turret(part=part, seat=seat, at=tuple(at), hull=hull)


def reach_km(turret: Turret) -> float:
    """How far this gun is specified to shoot, in kilometres.

    Off the armament's own range bands through `sim/tactical.BAND_UNITS`, so
    a weapon that works to band 3 in a turn-based engagement works to the same
    distance here. Two range models that disagreed about one gun would be
    exactly the sort of second copy this project keeps being bitten by.
    """
    from .tactical import BAND_UNITS
    weapon = turret.weapon
    top = weapon.bands[1] if weapon is not None else 2
    return (top + 1) * BAND_UNITS / 24.0


def damage(turret: Turret) -> float:
    """What one round off this mounting is worth, from the armament."""
    weapon = turret.weapon
    return float(weapon.dmg) if weapon is not None else 6.0


def order(turret: Turret, bearing: float, elevation: float) -> None:
    """Lay the gun somewhere and let the mounting find it."""
    turret.want_bearing, turret.want_elevation = gunsight.clamp(
        turret.kind, bearing, elevation)


def lock(turret: Turret, contact_id: str) -> None:
    """Put the director on a contact, or take it off with an empty id."""
    turret.locked = contact_id or ""


def stick(turret: Turret, across: float, up: float) -> None:
    """The hands on the mounting, -1..1 each. Any push drops the lock.

    **Taking hold of the gun takes it off the director**, because the
    alternative is a gunner fighting their own computer for the mounting and
    losing — the director is faster than they are and puts it straight back.
    """
    across = max(-1.0, min(1.0, across))
    up = max(-1.0, min(1.0, up))
    if (across or up) and turret.locked:
        turret.locked = ""
    turret.swing_x, turret.swing_y = across, up


def can_fire(turret: Turret) -> tuple:
    """May the trigger do anything right now, and if not, why not."""
    if turret.jammed:
        return False, f"Cooked — {turret.heat:.0f}° and falling."
    if turret.reloading > 0.0:
        return False, f"Feeding — {turret.reloading:.1f} s."
    if turret.cooldown > 0.0:
        return False, ""
    if turret.kind.rounds and turret.rounds <= 0:
        return False, "Empty."
    return True, ""


def feed(turret: Turret) -> tuple:
    """Start a reload by hand. Refused when there is nothing to feed."""
    if not turret.kind.rounds:
        return False, "It runs off the reactor; there is nothing to feed."
    if turret.rounds >= turret.kind.rounds:
        return False, "The mounting is full."
    turret.reloading = turret.kind.reload_s
    return True, f"Feeding the {turret.seat.lower()}."


def tick(turret: Turret, seconds: float, aim=None) -> None:
    """One slice of a second: swing, cool, feed, and count the trigger down.

    `aim` is `(bearing, elevation)` from the director when the gun is locked
    on something; None leaves it on the stick or the laid order.
    """
    if seconds <= 0.0:
        return
    kind = turret.kind
    if aim is not None:
        turret.want_bearing, turret.want_elevation = gunsight.clamp(
            kind, aim[0], aim[1])
    elif turret.swing_x or turret.swing_y:
        turret.want_bearing, turret.want_elevation = gunsight.clamp(
            kind,
            turret.want_bearing + kind.traverse * turret.swing_x * seconds,
            turret.want_elevation + kind.elevate * turret.swing_y * seconds)
    turret.bearing, turret.elevation = gunsight.swing(
        kind, turret.bearing, turret.elevation,
        turret.want_bearing, turret.want_elevation, seconds)
    turret.heat = max(0.0, turret.heat - kind.cool * seconds)
    if turret.jammed and turret.heat <= COOKED * CLEARED:
        turret.jammed = False
    turret.cooldown = max(0.0, turret.cooldown - seconds)
    if turret.reloading > 0.0:
        turret.reloading = max(0.0, turret.reloading - seconds)
        if turret.reloading <= 0.0:
            turret.rounds = kind.rounds


def muzzle(turret: Turret) -> tuple:
    """Where the round leaves the ship, in the hull's frame, in kilometres.

    The mounting's own place on the hull, nudged along the bore so a tracer
    starts at the end of the barrel rather than inside the ship. Half-lengths
    are turned into kilometres at `HULL_KM`, which is the scale everything in
    a skirmish is measured in.
    """
    from .skirmish import HULL_KM
    bore = gunsight.vector(turret.bearing, turret.elevation)
    seat = tuple(c * HULL_KM for c in turret.at)
    return tuple(s + b * HULL_KM * 1.2 for s, b in zip(seat, bore))


def pull(turret: Turret, rng, mark=None) -> Shot:
    """Fire, if it will fire. `mark` is the solution the sight is showing.

    Returns a `Shot` either way: a refused pull comes back with `why` set and
    nothing spent, because a trigger that does nothing and says nothing is
    the complaint this whole layer exists to answer.
    """
    kind = turret.kind
    ok, why = can_fire(turret)
    if not ok:
        return Shot(why=why or "Not yet.", look=kind.look)
    bore = gunsight.vector(turret.bearing, turret.elevation)
    turret.fired += 1
    turret.cooldown = kinds.seconds_between(kind)
    turret.heat += kind.heat
    if turret.heat >= COOKED:
        turret.jammed = True
        turret.log.append(f"{turret.seat} has cooked off.")
    if kind.rounds:
        turret.rounds = max(0, turret.rounds - kind.burst)
        if turret.rounds <= 0:
            turret.reloading = kind.reload_s
    if mark is None:
        return Shot(frm=muzzle(turret), at=tuple(c * reach_km(turret)
                                                 for c in bore),
                    look=kind.look, seconds=gunsight.flight_time(
                        kind, reach_km(turret)))
    off = gunsight.off_bore(turret.bearing, turret.elevation,
                            mark["aim"][0], mark["aim"][1])
    spread = rng.float(0.0, max(0.01, kind.spread))
    chance = gunsight.hit_chance(kind, off + spread, mark["range_km"],
                                 reach_km(turret))
    hit = rng.chance(chance)
    if hit:
        turret.hits += 1
        turret.dealt += damage(turret)
    return Shot(frm=muzzle(turret), at=mark["mark"], target=mark.get("id", ""),
                look=kind.look, hit=hit, damage=damage(turret) if hit else 0.0,
                off=off, range_km=mark["range_km"], seconds=mark["seconds"])


def readout(turret: Turret) -> list:
    """The seat's own instruments: `(label, value, tint)` rows."""
    kind = turret.kind
    ok, why = can_fire(turret)
    rows = [
        ("Bearing", f"{turret.bearing:+.1f}°", ""),
        ("Elevation", f"{turret.elevation:+.1f}°", ""),
        ("Arc", f"±{kind.arc:.0f}°  ·  {kind.down:.0f}° to {kind.up:.0f}°", "dim"),
        ("Reach", f"{reach_km(turret):,.1f} km", ""),
        ("Round", f"{kind.muzzle_kms:,.1f} km/s" if kind.muzzle_kms
         else "beam — arrives at once", "dim"),
        ("Heat", f"{turret.heat:.0f} of {COOKED:.0f}",
         "bad" if turret.jammed else "warn" if turret.heat > COOKED * 0.6
         else ""),
    ]
    if kind.rounds:
        rows.append(("Magazine", f"{turret.rounds} of {kind.rounds}",
                     "warn" if turret.rounds <= kind.rounds * 0.2 else ""))
    if turret.reloading > 0.0:
        rows.append(("Feeding", f"{turret.reloading:.1f} s", "warn"))
    rows.append(("Trigger", "ready" if ok else (why or "not yet"),
                 "" if ok else "warn"))
    if turret.fired:
        rows.append(("This action", f"{turret.hits} of {turret.fired} landed"
                     f"  ·  {turret.dealt:,.0f} dealt", "good"))
    return rows
