"""Hurting people: the shot, the wound, the bleeding, the patching up, the nerve.

Traveller's personal combat, on squares, and all of it through
`sim/checks.py`:

    2D6 + skill + DEX DM (STR hand to hand) + the weapon's own kit bonus
        + range + aim + cover  ≥  8

and the damage is the weapon's dice plus the attack's **Effect**, less the
target's armour. `terms` is the forecast and `attack` is the act, and they
are the same arithmetic: `terms` builds the arguments, `checks.chance` turns
them into the odds on the screen, and `attack` hands the same arguments to
`checks.roll`. There is no second formula to drift.

**Going down.** At no stamina somebody is down and bleeding a point a round;
at minus their endurance they are dead. First aid stops the bleeding and
gets a little back. A stun weapon puts people down without ever killing
them. **The captain is never killed** — the chronicle is theirs, and a
captain who goes down is carried out by somebody (`sim/afoot_ends.py`) at a
price the rest of the game already knows how to charge.

**Nerve.** Somebody on the other side who is badly hurt, or who sees a
friend fall, throws 2D6 + their archetype's bravery + Leadership against 8.
A person who fails gives up where they stand if there is nobody left to run
to, and runs if there is.
"""

from __future__ import annotations

from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..data.afoot_folk import FOLK_BY_ID
from . import afoot_map, afoot_people, checks
from .afoot_state import say

#: What a downed target is worth to hit: they are not moving.
DOWNED = 2
#: What the attacker loses when badly hurt themselves.
HURTING = -1
#: The most aim anybody can take: two rounds of it.
AIM_MOST = 2
#: A hit this many times somebody's endurance kills them where they stand.
SHATTERING = 2
#: Shooting weightless with nothing to brace against: a DM, and a gun with
#: any kick puts the shooter adrift for the rest of the round. Zero-G skill
#: or magnetic boots are something to brace against (`afoot_map.at_home`).
UNBRACED = -2


def weapon(actor) -> arms.Arm:
    return arms.arm(actor.weapon)


def terms(game, walk, attacker, target) -> dict:
    """Everything a shot would be rolled with, and whether it can be taken."""
    out = {"ok": False, "why": "", "odds": 0.0}
    if not attacker.standing:
        out["why"] = f"{attacker.name} is down."
        return out
    if target.status in ("dead", "gone"):
        out["why"] = "There is nobody there to hit."
        return out
    if attacker.deck != target.deck:
        out["why"] = "They are on another deck."
        return out
    arm = weapon(attacker)
    far = afoot_map.apart(walk, attacker, target)
    band, dm = arms.band(arm, far)
    if dm is None:
        out["why"] = (f"Out of reach — {far} squares, and "
                      f"{arm.name} reaches {1 if arm.melee else arm.long * 2}.")
        return out
    if not afoot_map.sees(walk, attacker.deck, attacker.x, attacker.y,
                          target.x, target.y):
        out["why"] = "No line to them."
        return out
    rec = afoot_people.record(game, attacker)
    skill = rec.skill(arm.skill)
    score = rec.score("str" if arm.melee else "dex")
    item = kit_table.ITEM_BY_ID.get(attacker.weapon)
    kit_dm = item.bonus if item is not None and item.gives == arm.skill else 0
    cover = 0 if arm.melee else afoot_map.cover_for(
        walk, target.deck, target.x, target.y, attacker.x, attacker.y)
    extra = dm + kit_dm + min(AIM_MOST, attacker.aim) - cover
    if drifting(walk, attacker):
        extra += UNBRACED
    if attacker.pinned > 0:
        extra += arms.PINNED
    if not target.standing:
        extra += DOWNED
    if attacker.hp * 2 < attacker.hp_max:
        extra += HURTING
    out.update(ok=True, skill=skill, score=score, how="average", extra=extra,
               band=band, cover=cover, arm=arm, far=far,
               odds=checks.chance(skill, score, "average", extra))
    return out


def drifting(walk, who) -> bool:
    """Weightless, and nothing to brace against."""
    deck = walk.decks[who.deck]
    return deck.g < afoot_map.WEIGHTLESS and not afoot_map.at_home(who)


def kicks(arm) -> bool:
    """A gun with recoil: anything fired that is not a laser."""
    return not arm.melee and not arm.laser


def damage_range(attacker, target) -> tuple:
    """Least and most a hit does, after armour, before the Effect."""
    arm = weapon(attacker)
    guard = arms.guard(target.armour)
    stop = 0
    if guard is not None:
        stop = guard.protect + (guard.vs_laser if arm.laser else 0)
    stop = max(0, stop - arm.pierce)
    return (max(0, arm.dice + arm.plus - stop),
            max(0, arm.dice * 6 + arm.plus - stop))


def attack(game, walk, attacker, target, rng, burst: bool = False) -> dict:
    """Take the shot — or, with a weapon that has Auto, a burst, which adds
    its Auto to the damage. Returns `{ok, why, hit, damage, check, events}`.

    `rng` is the dice, or a function that makes them: called only once the
    shot is allowed, so a refusal spends no luck."""
    got = terms(game, walk, attacker, target)
    if not got["ok"]:
        return {"ok": False, "why": got["why"]}
    arm = got["arm"]
    if burst and not arm.auto:
        return {"ok": False, "why": f"The {arm.name} fires one at a time."}
    rng = rng() if callable(rng) else rng
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="attack", what=arm.skill)
    attacker.acted = True
    attacker.aim = 0
    events = []
    if kicks(arm) and drifting(walk, attacker):
        attacker.mp = 0
        say(walk, f"The kick of the {arm.name} sets {attacker.name} "
                  "drifting.", "warn")
    if not roll.ok:
        say(walk, f"{attacker.name} {'swings at' if arm.melee else 'fires at'} "
                  f"{target.name} and misses ({roll.rolled}{roll.total - roll.rolled:+d}).",
            "")
        return {"ok": True, "hit": False, "damage": 0, "check": roll,
                "events": events}
    dice = sum(rng.int(1, 6) for _n in range(arm.dice)) + arm.plus + (
        arm.auto if burst else 0)
    guard = arms.guard(target.armour)
    stop = 0
    if guard is not None:
        stop = guard.protect + (guard.vs_laser if arm.laser else 0)
    stop = max(0, stop - arm.pierce)
    dealt = max(0, dice + roll.effect - stop)
    say(walk, f"{attacker.name} hits {target.name} with the {arm.name} — "
              f"{dealt} through {'armour' if stop else 'nothing'}"
              f"{f' ({stop} stopped)' if stop else ''}.",
        "bad" if target.side == "party" else "good")
    events += hurt(game, walk, target, dealt, stun=arm.stun, rng=rng)
    return {"ok": True, "hit": True, "damage": dealt, "check": roll,
            "events": events}


def hurt(game, walk, target, amount: int, stun: bool = False,
         rng=None) -> list:
    """Take stamina off somebody, and say what that does to them."""
    events = []
    if amount <= 0 or target.status in ("dead", "gone"):
        return events
    rec = afoot_people.record(game, target)
    end = rec.score("end")
    floor = -end
    if stun:
        floor = -1
    if target.folk == "captain":
        floor = max(floor, -end + 1)
    if target.status == "up" and amount < SHATTERING * end:
        # **Going down is not dying.** The hit that drops somebody leaves
        # them down and bleeding, with rounds in hand for a friend to reach
        # them; only a hit of twice their endurance kills outright, and after
        # that it is the bleeding, or being hit again.
        floor = max(floor, -end + 1)
    before = target.hp
    target.hp = max(floor, target.hp - amount)
    if stun:
        target.numb += before - target.hp
    if target.hp > 0:
        return events
    kind = FOLK_BY_ID.get(target.folk)
    fragile = kind is not None and kind.kind in ("machine", "bloom")
    if target.hp <= -end or (fragile and target.side == "npc"):
        target.status = "dead"
        target.carrying = -1
        what = ("is broken" if kind and kind.kind == "machine"
                else "is dead")
        say(walk, f"{target.name} {what}.", "bad" if target.side == "party"
            else "warn")
        events.append({"kind": "dead", "who": target.id})
    elif target.status == "up":
        target.status = "stable" if stun else "down"
        target.carrying = -1
        say(walk, f"{target.name} goes down"
                  f"{', out cold' if stun else ' and is bleeding'}.",
            "bad" if target.side == "party" else "warn")
        events.append({"kind": "down", "who": target.id})
    if target.side == "npc" and rng is not None:
        events += shaken(game, walk, target, rng)
    return events


def bleed(game, walk) -> list:
    """A round passes for everybody bleeding: a point each."""
    events = []
    for who in walk.actors:
        if who.status == "down":
            events += hurt(game, walk, who, 1)
    return events


# ── first aid ──────────────────────────────────────────────────────────────

def aid_terms(game, walk, medic, patient) -> dict:
    """What patching somebody up would be rolled with."""
    out = {"ok": False, "why": "", "odds": 0.0}
    if not medic.standing:
        out["why"] = f"{medic.name} is down."
        return out
    if afoot_map.apart(walk, medic, patient) > 1 \
            or medic.deck != patient.deck:
        out["why"] = "Get next to them first."
        return out
    if patient.status in ("dead", "gone"):
        out["why"] = "Past helping."
        return out
    if patient.hp >= patient.hp_max:
        out["why"] = "Nothing to patch."
        return out
    if "aided" in patient.talked and patient.status == "up":
        out["why"] = "Already patched once; the rest needs a proper table."
        return out
    rec = afoot_people.record(game, medic)
    bonus, spends = 0, ""
    for kid, dm in (("trauma_pack", 2), ("medkit", 1)):
        if kid in medic.kit and medic.spent.count(kid) < (2 if kid == "medkit"
                                                          else 1):
            bonus, spends = dm, kid
            break
    out.update(ok=True, skill=rec.skill("medic"), score=rec.score("edu"),
               how="average", extra=bonus, spends=spends,
               odds=checks.chance(rec.skill("medic"), rec.score("edu"),
                                  "average", bonus))
    return out


def first_aid(game, walk, medic, patient, rng) -> dict:
    got = aid_terms(game, walk, medic, patient)
    if not got["ok"]:
        return {"ok": False, "why": got["why"]}
    if got["spends"]:
        medic.spent.append(got["spends"])
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="first aid", what="medic")
    medic.acted = True
    if not roll.ok:
        say(walk, f"{medic.name} works on {patient.name} and cannot stop it.",
            "warn")
        return {"ok": True, "healed": 0, "check": roll}
    back = max(1, rng.int(1, 6) + roll.effect)
    patient.hp = min(patient.hp_max, max(patient.hp, 0) + back)
    if patient.status in ("down", "stable"):
        patient.status = "up" if patient.hp > 0 else "stable"
    patient.talked.append("aided")
    say(walk, f"{medic.name} patches {patient.name} up — {back} back.",
        "good")
    return {"ok": True, "healed": back, "check": roll}


# ── nerve ──────────────────────────────────────────────────────────────────

def shaken(game, walk, hurt_one, rng) -> list:
    """Everybody on the hurt one's side who saw it throws for their nerve."""
    events = []
    for npc in walk.actors:
        if (npc.side != "npc" or not npc.standing or npc.mood != "hostile"
                or npc.faction != hurt_one.faction):
            continue
        near = npc is hurt_one or afoot_map.sees(
            walk, npc.deck, npc.x, npc.y, hurt_one.x, hurt_one.y)
        if not near:
            continue
        badly = npc.hp * 2 < npc.hp_max or npc is not hurt_one
        if not badly:
            continue
        kind = FOLK_BY_ID.get(npc.folk)
        brave = getattr(kind, "brave", 0)
        lead = npc.skills.get("leadership", 0)
        roll = checks.roll(rng, lead, npc.stats.get("end", 7), "average",
                           brave, about="nerve", what="leadership")
        if roll.ok:
            continue
        cornered = not any(t.kind in ("airlock", "gangway", "lift")
                           for t in walk.things if t.deck == npc.deck)
        if cornered or npc.folk in ("holdout", "prisoner", "raider"):
            npc.mood = "surrendered"
            say(walk, f"{npc.name} throws down and gives up.", "good")
            events.append({"kind": "surrender", "who": npc.id})
        else:
            npc.mood = "fled"
            say(walk, f"{npc.name} breaks and runs.", "good")
            events.append({"kind": "flee", "who": npc.id})
    return events
