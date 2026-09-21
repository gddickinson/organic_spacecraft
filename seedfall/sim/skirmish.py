"""A real-time action fought from one gun, in seconds rather than turns.

`sim/combat.py` is the game's engagement: two hulls, a five-band track, and a
captain deciding a turn at a time. It is the right model for *commanding* a
ship and the wrong one for *firing* a gun, because a turn has no room in it
for leading a target.

So this is the other grain. A `Skirmish` is the sky around one hull: a set of
`foes.Contact`s moving under their own behaviour, a `turret.Turret` with
somebody's hands on it, and a clock that runs in tenths of a second. Nothing
in it advances the chronicle — the same ground `sim/battle_state.py` stands on
— so a drill and a boarding action both cost the calendar nothing.

**What the gunner does and what the ship does are separate.** The hull holds
its heading; the sky moves around it. A contact closes, crosses, overshoots
and comes round again on its own, and the gunner's whole job is the arc
between "it is in my cone" and "it is gone". Where the hull goes is the
pilot's, and on this screen the pilot is somebody else.

**Contacts shoot back, and some of what they fire becomes a contact.** A
missile rack does not take hull points off you; it puts a seeker on the plot
with four points of hull and your name on it, and the point-defence gunner's
whole reason to exist is to take it off again before it arrives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import foes, gunsight, turret as turret_sim

#: Half the length of a hull, in kilometres — the scale everything a gunner
#: sees is measured against. `data/mounts.py` puts a mount at a fraction of
#: this, so a gun 0.9 of the way aft is 108 m behind the centre of a working
#: freighter, which is about right for the ships this game flies.
HULL_KM = 0.12

#: How long a tracer is worth drawing after the round has arrived, and how
#: many of them are kept. A gunner firing eight a second fills a list fast,
#: and nothing older than this is on the screen anyway.
TRACER_LIFE = 0.6
TRACERS = 48

#: The clock's own step, in seconds. Fine enough that a point-defence cannon
#: at eight rounds a second gets its own tick for each of them, coarse enough
#: that a minute of action is six hundred steps and not sixty thousand.
STEP = 0.1

#: How hard a seeker hits when it arrives, by kind.
SEEKER_HARM = {"missile": 9.0, "torpedo": 22.0}


@dataclass
class Tracer:
    """One round in the air, kept only so a window can draw it."""

    frm: tuple
    to: tuple
    look: str
    hit: bool
    born: float
    mine: bool = True


@dataclass
class Skirmish:
    """One action, from one seat."""

    turret: turret_sim.Turret
    contacts: list = field(default_factory=list)
    #: The hull the gun is bolted to, and what it has left.
    hull: str = "your hull"
    hp: float = 340.0
    max_hp: float = 340.0
    #: How hard this hull is to hit, 0..0.8 — its evade, from the ship's own
    #: stats where there is a ship and a plain number where there is not.
    evade: float = 0.25
    #: Seconds since it opened, and whether it is finished with.
    clock: float = 0.0
    over: bool = False
    outcome: str = ""
    #: What the gunner has done, for the drill to read.
    killed: list = field(default_factory=list)
    taken: float = 0.0
    tracers: list = field(default_factory=list)
    log: list = field(default_factory=list)
    #: Which of a drill's waves have already arrived, by index. Held here
    #: rather than on the drill, which is a frozen table several actions may
    #: be running from at once.
    waves_in: list = field(default_factory=list)
    #: Damage already carried back to the turn-based engagement this action
    #: was opened off, if it was opened off one. The same shape as
    #: `Conn.charged`: a meter, so neither door can bill the same hit twice.
    banked: float = 0.0
    #: The star's direction, for the picture only.
    star: tuple = (0.45, 0.3, 0.84)
    #: What the sky looks like out of the blister: a world, a station, empty.
    setting: str = "deep"


def open_action(turret, contacts, **rest) -> Skirmish:
    """Put a gunner in a seat with a sky in front of them."""
    return Skirmish(turret=turret, contacts=list(contacts), **rest)


def live(action: Skirmish, hostile=None) -> list:
    """Everything still out there, nearest first.

    `hostile=True` for what may be shot at, `False` for the consorts, None
    for the lot — the sight brackets friends too, which is exactly how a
    gunner avoids hitting one.
    """
    rows = [c for c in action.contacts if not c.dead
            and (hostile is None or c.hostile == hostile)]
    return sorted(rows, key=lambda c: c.range_km)


def find(action: Skirmish, cid: str):
    return next((c for c in action.contacts if c.id == cid and not c.dead),
                None)


def solution(action: Skirmish, contact) -> dict:
    """The sight's whole read on one contact: where it is, where to aim."""
    got = gunsight.solution(action.turret.kind, contact.at, contact.vel)
    got["id"] = contact.id
    got["name"] = contact.name
    got["hostile"] = contact.hostile
    got["radius_km"] = contact.radius_km
    got["in_reach"] = got["range_km"] <= turret_sim.reach_km(action.turret)
    return got


def marked(action: Skirmish):
    """The contact the director is on, or None."""
    return find(action, action.turret.locked) if action.turret.locked else None


def aim_now(action: Skirmish) -> dict | None:
    """What the gun is pointing at, whether or not it is locked.

    With a lock it is that contact; without one it is whatever is nearest the
    bore inside a cone, because a gunner who lines up a corvette by hand and
    pulls should hit it. This is the one place "what am I shooting at" is
    decided, so the sight, the trigger and the hit all agree.
    """
    held = marked(action)
    if held is not None:
        return solution(action, held)
    best, closest = None, turret_sim.LOOSE
    for contact in live(action):
        got = solution(action, contact)
        off = gunsight.off_bore(action.turret.bearing, action.turret.elevation,
                                got["aim"][0], got["aim"][1])
        if off < closest:
            best, closest = got, off
    return best


def cycle(action: Skirmish, back: bool = False) -> str:
    """Put the director on the next contact round. Returns what it took."""
    rows = [c for c in live(action, hostile=True)]
    if not rows:
        turret_sim.lock(action.turret, "")
        return ""
    ids = [c.id for c in rows]
    here = ids.index(action.turret.locked) if action.turret.locked in ids \
        else (len(ids) - 1 if back else -1)
    nxt = ids[(here - 1 if back else here + 1) % len(ids)]
    turret_sim.lock(action.turret, nxt)
    return nxt


def nearest_threat(action: Skirmish):
    """The thing most worth shooting at right now: a seeker, then the closest.

    A gunner asked to pick one target picks the one that is about to kill
    them, and a missile eight seconds out beats a station that has been
    sitting there all action.
    """
    seekers = [c for c in live(action, hostile=True)
               if c.behaviour == "home"]
    if seekers:
        return min(seekers, key=lambda c: c.range_km)
    rows = live(action, hostile=True)
    return rows[0] if rows else None


# ── the clock ──────────────────────────────────────────────────────────────

def tick(action: Skirmish, rng, seconds: float = STEP) -> dict:
    """One slice of the action. Returns what a window should say about it.

    The order is the one a gunner would recognise: the sky moves, the gun
    swings onto wherever the director is pointing it, anything that arrived
    arrives, and the other side shoots. The trigger is *not* in here — it is
    pulled by a hand, through `fire`, as often as the gun will answer.
    """
    if action.over:
        return {"over": True}
    action.clock += seconds
    said = []
    for contact in list(action.contacts):
        if contact.dead:
            continue
        foes.steer(contact, seconds, rng)
        foes.cool(contact, seconds)
    # Seekers that got through.
    for contact in live(action, hostile=True):
        if foes.arriving(contact):
            harm = SEEKER_HARM.get(contact.kind, 9.0)
            contact.dead = True
            contact.killed_by = "struck home"
            _wound(action, harm, contact.name)
            said.append(f"{contact.name} struck home — {harm:,.0f} off the hull.")
    _return_fire(action, rng, seconds, said)
    # The gun follows the director, or the hands.
    held = marked(action)
    aim = None
    if held is not None:
        got = solution(action, held)
        aim = got["aim"]
    turret_sim.tick(action.turret, seconds, aim)
    action.tracers = [t for t in action.tracers
                      if action.clock - t.born <= TRACER_LIFE][-TRACERS:]
    if action.turret.locked and marked(action) is None:
        turret_sim.lock(action.turret, "")
    for line in said:
        action.log.append(line)
    return {"over": action.over, "said": said}


def _wound(action: Skirmish, harm: float, by: str) -> None:
    """The hull you are standing on takes a hit."""
    action.hp = max(0.0, action.hp - harm)
    action.taken += harm
    if action.hp <= 0.0 and not action.over:
        finish(action, "lost", f"The hull is gone — {by} finished it.")


def _return_fire(action: Skirmish, rng, seconds: float, said: list) -> None:
    """Everything hostile that can shoot, shooting."""
    for contact in live(action, hostile=True):
        for index, gun in enumerate(contact.guns):
            if not foes.can_shoot(contact, index):
                continue
            contact.ready[index] = gun.every
            if gun.launches:
                _launch(action, contact, gun)
                said.append(f"{contact.name} has launched.")
                continue
            landed = rng.chance(foes.aim_quality(contact, gun,
                                                 action.evade))
            action.tracers.append(Tracer(
                frm=tuple(contact.at), to=(0.0, 0.0, 0.0), look=gun.look,
                hit=landed, born=action.clock, mine=False))
            if landed:
                _wound(action, gun.dmg, contact.name)


def _launch(action: Skirmish, frm, gun) -> None:
    """A rack speaks: a seeker joins the plot with your name on it."""
    kind = gun.launches
    span = frm.range_km or 1.0
    toward = tuple(-c / span for c in frm.at)
    action.contacts.append(foes.make(
        f"{frm.id}-{kind}-{len(action.contacts)}",
        f"{kind.title()} from {frm.name}", kind,
        tuple(p + t * frm.radius_km * 1.4 for p, t in zip(frm.at, toward)),
        behaviour="home", pace=0.55 if kind == "missile" else 0.34,
        fuse=40.0, hostile=True, faction=frm.faction))


# ── the trigger ────────────────────────────────────────────────────────────

def fire(action: Skirmish, rng) -> turret_sim.Shot:
    """Pull it. The one door — the key, the button and the held trigger all
    come here, so a shot costs the same however it was asked for."""
    if action.over:
        return turret_sim.Shot(why="It is over.")
    mark = aim_now(action)
    shot = turret_sim.pull(action.turret, rng, mark)
    if shot.why:
        return shot
    action.tracers.append(Tracer(frm=shot.frm, to=shot.at, look=shot.look,
                                 hit=shot.hit, born=action.clock))
    if not shot.hit or mark is None:
        return shot
    contact = find(action, mark["id"])
    if contact is None:
        return shot
    if not contact.hostile:
        action.log.append(f"You have hit {contact.name}, who is on your side.")
    part = _part_under(contact, shot)
    foes.hurt(contact, shot.damage, "your gun", part=part)
    if contact.dead:
        action.killed.append(contact)
        action.log.append(f"{contact.name} is gone.")
    elif part:
        piece = next((p for p in contact.parts if p.id == part), None)
        if piece is not None and piece.dead:
            action.log.append(
                f"{contact.name}: the {piece.name.lower()} is off — "
                f"{piece.loss}.")
    return shot


def _part_under(contact, shot) -> str:
    """Which fitting the round found, if the contact has any.

    The nearest one to where the round actually went, so a gunner who holds
    the sight on a station's forward turret takes that turret off and not a
    random one. Dead pieces are no longer there to be hit.
    """
    alive = [p for p in contact.parts if not p.dead]
    if not alive:
        return ""
    best, near = "", None
    for piece in alive:
        spot = tuple(c + o * contact.radius_km
                     for c, o in zip(contact.at, piece.at))
        gap = math.dist(spot, shot.at)
        if near is None or gap < near:
            best, near = piece.id, gap
    return best


def finish(action: Skirmish, outcome: str, why: str = "") -> None:
    """End it, once. Everything after this reads the same answer."""
    if action.over:
        return
    action.over = True
    action.outcome = outcome
    action.turret.firing = False
    if why:
        action.log.append(why)


def standing(action: Skirmish) -> dict:
    """Where the action is, in the terms a board would show."""
    hostile = live(action, hostile=True)
    return {
        "clock": action.clock,
        "hostiles": len(hostile),
        "seekers": sum(1 for c in hostile if c.behaviour == "home"),
        "friends": len(live(action, hostile=False)),
        "hull": action.hp / action.max_hp if action.max_hp else 0.0,
        "taken": action.taken,
        "killed": len(action.killed),
        "fired": action.turret.fired,
        "hits": action.turret.hits,
        "accuracy": (action.turret.hits / action.turret.fired
                     if action.turret.fired else 0.0),
    }
