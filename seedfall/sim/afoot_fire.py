"""Fire that is not one aimed shot: suppressing fire, and things thrown.

Traveller's rules, on the squares:

- **suppressing fire** — a weapon with Auto hosed at a square: nobody is
  hit, but the target and anybody beside them are **pinned** for a round
  (`Actor.pinned`) — they hold their ground and shoot at `arms.PINNED` —
  unless they are brave enough to shrug it off (`Folk.brave` 3 and up);
- **a grenade** — thrown with Athletics and DEX at a square within its
  reach, off target by a square on a miss; a fragmentation grenade hurts
  everybody in its burst, friend or not, a stun grenade puts them on the
  floor, a smoke grenade hangs a cloud (`afoot_things.SMOKE`) that nobody
  sees through for `arms.SMOKE_ROUNDS`. One grenade from a person's own kit
  is spent each time.

`terms` is what a button says; `suppress` and `throw` do exactly that.
"""

from __future__ import annotations

from ..data import afoot_arms as arms
from ..data.afoot_folk import FOLK_BY_ID
from . import afoot_fight, afoot_map, afoot_people, checks
from .afoot_state import Thing, say, uid

#: Nerve at which a person is not pinned by fire that misses them.
UNSHAKEN = 3


def grenades(who) -> list:
    """The grenades this person has left, one id per grenade."""
    out = []
    for g in arms.GRENADES:
        out += [g.id] * max(0, who.kit.count(g.id) - who.spent.count(g.id))
    return out


def suppress(game, walk, who, target) -> dict:
    """Hose the target's square: pin them, and anybody beside them."""
    arm = afoot_fight.weapon(who)
    if not arm.auto:
        return {"ok": False, "why": f"The {arm.name} cannot lay down fire."}
    got = afoot_fight.terms(game, walk, who, target)
    if not got["ok"]:
        return {"ok": False, "why": got["why"]}
    who.acted, who.aim = True, 0
    pinned = []
    for other in walk.actors:
        if other.deck != target.deck or not other.standing or \
                afoot_map.apart(walk, other, target) > 1:
            continue
        kind = FOLK_BY_ID.get(other.folk)
        if other.side == "npc" and getattr(kind, "brave", 0) >= UNSHAKEN:
            continue
        other.pinned = max(other.pinned, 1)
        pinned.append(other.name)
    say(walk, f"{who.name} lays the {arm.name} across them"
              + (f" — {', '.join(pinned)} pinned." if pinned else
                 " and nobody so much as flinches."), "good" if pinned else "")
    return {"ok": True, "pinned": pinned}


def terms(game, walk, who, target, grenade_id: str) -> dict:
    """What throwing this grenade at this person's square would be rolled
    with — and whether it can be thrown at all."""
    grenade = arms.GRENADE_BY_ID.get(grenade_id)
    if grenade is None or grenade_id not in grenades(who):
        return {"ok": False, "why": "Nobody here is carrying one."}
    if not who.standing:
        return {"ok": False, "why": f"{who.name} is down."}
    far = afoot_map.apart(walk, who, target)
    if who.deck != target.deck or far > grenade.reach:
        return {"ok": False, "why": f"Too far to throw — {grenade.reach} "
                                    "squares at most."}
    if not afoot_map.sees(walk, who.deck, who.x, who.y, target.x, target.y):
        return {"ok": False, "why": "No line to throw along."}
    rec = afoot_people.record(game, who)
    extra = -1 if far > grenade.reach // 2 else 0
    if afoot_fight.drifting(walk, who):
        extra += afoot_fight.UNBRACED
    skill, score = rec.skill("athletics"), rec.score("dex")
    return {"ok": True, "why": "", "grenade": grenade, "skill": skill,
            "score": score, "extra": extra,
            "odds": checks.chance(skill, score, "average", extra)}


def throw(game, walk, who, target, grenade_id: str, rng) -> dict:
    """Throw it. It lands where it was thrown, or a square off on a miss.
    `rng` may be a function making the dice, called once the throw is
    allowed."""
    got = terms(game, walk, who, target, grenade_id)
    if not got["ok"]:
        return {"ok": False, "why": got["why"]}
    rng = rng() if callable(rng) else rng
    grenade = got["grenade"]
    roll = checks.roll(rng, got["skill"], got["score"], "average",
                       got["extra"], about="a throw", what="athletics")
    who.acted, who.aim = True, 0
    who.spent.append(grenade.id)
    x, y = target.x, target.y
    wide = afoot_map.span(walk, target.deck)

    def at(px):                 # round a ring's seam
        return px % wide if wide else px
    if not roll.ok:
        dx, dy = rng.pick(afoot_map.STEPS)
        if afoot_map.ground(walk, target.deck).passable(x + dx, y + dy):
            x, y = at(x + dx), y + dy
    say(walk, f"{who.name} throws a {grenade.name}"
              + (" — dead on." if roll.ok else " — it skids off target."),
        "")
    burst = [(at(x + dx), y + dy)
             for dx in range(-grenade.burst, grenade.burst + 1)
             for dy in range(-grenade.burst, grenade.burst + 1)]
    events = []
    if grenade.smoke:
        for sq in burst:
            if afoot_map.ground(walk, target.deck).floor(*sq):
                walk.things.append(Thing(
                    id=uid(walk), kind="smoke", deck=target.deck, x=sq[0],
                    y=sq[1], state=str(arms.SMOKE_ROUNDS), name="smoke"))
        walk.version += 1
        return {"ok": True, "check": roll, "events": events}
    for other in list(walk.actors):
        if other.deck == target.deck and (other.x, other.y) in burst and \
                other.status not in ("dead", "gone"):
            hurt = sum(rng.int(1, 6) for _n in range(grenade.dice))
            events += afoot_fight.hurt(game, walk, other, hurt,
                                       stun=grenade.stun, rng=rng)
    return {"ok": True, "check": roll, "events": events}


def settle(walk) -> None:
    """A round passes: the pinned find their feet, smoke thins."""
    for who in walk.actors:
        if who.pinned > 0:
            who.pinned -= 1
    kept = []
    for t in walk.things:
        if t.kind == "smoke":
            left = int(t.state or 0) - 1
            if left <= 0:
                continue
            t.state = str(left)
        kept.append(t)
    if len(kept) != len(walk.things):
        walk.things[:] = kept
        walk.version += 1
