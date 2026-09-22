"""What a person on a deck can do from where they stand, and doing it.

`offer` lists every act open to one party member — the things next to them,
the people next to them, and their own stances — each with whether it can be
done, **why not** in the words the captain would use, and the odds when
there is a roll. `perform` does exactly the act offered: it rebuilds the
same arguments and rolls them (`checks.roll` against `checks.chance`), so
the number on the button is the number thrown.

The verbs on things are `data/afoot_things.VERBS`, one function each in
`sim/afoot_deeds.DEEDS`, and nothing else; a check holds the two together.

**Somebody may be watching.** Forcing a lock, emptying a locker or hitting
somebody on a deck with people on it is a crime if anybody who is not yours
sees it (`witnessed`). What was seen is written on the walk and becomes a
charge through `sim/dockets` when the walk ends; a constable who saw it
comes for you now.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..data import afoot_arms as arms
from ..data import kit as kit_table
from ..data.afoot_folk import FOLK_BY_ID
from ..data.afoot_things import (DOORS, LOCKS, RELIC_STAGES, THING_BY_ID,
                                 VERBS)
from . import afoot_map, afoot_people, checks
from .afoot_state import actor_at, party, say, touch

#: Where a living site counts what the crew does as a crime.
LIVING = ("port", "habitat", "downside", "kith", "station", "base")


@dataclass(frozen=True)
class Act:
    """One thing a party member could do now."""

    id: str
    label: str
    ok: bool = True
    why: str = ""
    #: The chance of it working, where there is a roll; None where not.
    odds: object = None
    #: "thing", "actor" or "self", and which.
    on: str = "self"
    target: int = -1
    blurb: str = ""


# ── witnesses ──────────────────────────────────────────────────────────────

def witnessed(game, walk, doer, what: str, weight: float = 1.0) -> list:
    """Who saw that. On a living site a witness makes it a crime.

    Returns the witnesses. Constables among them turn on the party, and
    everybody else who saw it backs away.
    """
    if walk.kind not in LIVING:
        return []
    seen = []
    for npc in walk.actors:
        if (npc.side != "npc" or not npc.standing or npc.deck != doer.deck
                or npc.mood in ("hostile", "surrendered", "fled")):
            continue
        kind = FOLK_BY_ID.get(npc.folk)
        if kind is None or kind.kind != "person":
            continue
        if afoot_map.sees(walk, npc.deck, npc.x, npc.y, doer.x, doer.y):
            seen.append(npc)
    if not seen:
        return []
    walk.seen_doing.append([what, walk.faction, weight,
                            [npc.id for npc in seen]])
    for npc in seen:
        if npc.folk in ("constable", "customs", "bravo"):
            npc.mood, npc.aware = "hostile", True
        elif npc.folk in ("thug", "fence"):
            npc.mood = "wary"
        else:
            npc.mood = "fled"
    for npc in walk.actors:          # the watch hears of it
        if npc.folk == "constable" and npc.deck == doer.deck and \
                npc.standing and npc.mood != "surrendered":
            npc.mood, npc.aware = "hostile", True
    walk.mode = "action"
    say(walk, f"Somebody saw that. {len(seen)} witness"
              f"{'es' if len(seen) != 1 else ''}.", "warn")
    return seen


# ── what is on offer ───────────────────────────────────────────────────────

#: When a verb applies to a thing at all, by its state. A verb that does not
#: apply is not offered — a shut door has no "close", an open one no
#: "unlock" — rather than offered greyed with a reason nobody needed.
APPLIES = {
    "open": lambda t: t.state in ("shut", "locked"),
    "close": lambda t: t.state == "open",
    "unlock": lambda t: t.state == "locked",
    "force": lambda t: t.state == "locked",
    "breach": lambda t: t.state == "locked",
    "search": lambda t: t.state != "searched",
    "hack": lambda t: t.state != "hacked",
    "read": lambda t: t.state not in ("read", "hacked"),
    "take": lambda t: bool(t.holds) and t.state != "claimed",
    "repair": lambda t: t.state != "done",
    "burn": lambda t: t.state != "done",
    "study": lambda t: t.state not in ("done", "studied"),
}


def _near_things(walk, who) -> list:
    return [t for t in walk.things if t.deck == who.deck
            and afoot_map.apart(walk, t, who) <= 1]


def lock_terms(game, who, thing) -> dict:
    rec = afoot_people.record(game, who)
    extra = 2 if "lockpick" in who.kit else 0
    how = LOCKS.get(thing.lock or 1, "average")
    return {"skill": rec.skill("security"), "score": rec.score("dex"),
            "how": how, "extra": extra}


def force_terms(game, who, thing) -> dict:
    rec = afoot_people.record(game, who)
    grade = min(4, (thing.lock or 1) + 1)
    return {"skill": rec.skill("athletics"), "score": rec.score("str"),
            "how": LOCKS[grade], "extra": 0}


def hack_terms(game, walk, who) -> dict:
    rec = afoot_people.record(game, who)
    extra = 2 if "core_slate" in who.kit else 1 if "handcomp" in who.kit else 0
    how = "average" if walk.kind in ("wreck", "prize") else "difficult"
    return {"skill": rec.skill("computers"), "score": rec.score("int"),
            "how": how, "extra": extra}


def study_terms(game, who, thing) -> dict:
    rec = afoot_people.record(game, who)
    skill = "xenology" if thing.kind == "relic" else "sciences"
    extra = 1 if ("xeno_reader" in who.kit and skill == "xenology") else 0
    stage = RELIC_STAGES.get(thing.state) if thing.kind == "relic" else None
    return {"skill": rec.skill(skill), "score": rec.score("int"),
            "how": stage[2] if stage else "average",
            "extra": extra, "what": skill}


def repair_terms(game, who) -> dict:
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("mechanic"), "score": rec.score("int"),
            "how": "average", "extra": 1 if "toolkit" in who.kit else 0}


#: What burns a spore node clean: a torch, a laser, or a charge. Without one
#: it has to be cut apart by hand, which is a hard, strong job.
HEAT = ("cutting_torch", "laser_pistol", "laser_rifle", "cutting_laser")


def burn_terms(game, who) -> dict:
    rec = afoot_people.record(game, who)
    hot = who.weapon in HEAT or any(k in who.kit for k in HEAT)
    return {"skill": rec.skill("survival"), "score": rec.score("str"),
            "how": "easy" if hot else "difficult", "extra": 0}


def rest_price(game, walk, thing) -> int:
    """What a night on this bed costs: nothing aboard or on a wreck, the
    house's price in a lodging room (`sim/shore.ashore_cost`)."""
    from ..data.venues import VENUE_BY_ID
    from . import shore
    room = next((r for r in walk.rooms
                 if r.holds(thing.deck, thing.x, thing.y)), None)
    venue = VENUE_BY_ID.get(getattr(room, "venue", "")) if room else None
    if venue is None or room.kind != "lodging":
        return 0
    return shore.ashore_cost(game, venue)


def _odds(t: dict) -> float:
    return checks.chance(t["skill"], t["score"], t["how"], t["extra"])


def _thing_acts(game, walk, who, thing) -> list:
    kind = THING_BY_ID.get(thing.kind)
    out = []
    for verb in getattr(kind, "verbs", ()):
        if not APPLIES.get(verb, lambda _t: True)(thing):
            continue
        ok, why, odds = True, "", None
        label = f"{VERBS[verb]} — {thing.name or kind.name.lower()}"
        if verb == "open":
            ok = thing.state == "shut"
            why = "Locked." if thing.state == "locked" else "Not shut."
        elif verb == "close":
            ok = thing.state == "open" and actor_at(
                walk, thing.deck, thing.x, thing.y) is None
            why = "Somebody is in the way, or it is not open."
        elif verb == "unlock":
            ok = thing.state == "locked"
            why = "There is no lock holding it." if not ok else ""
            odds = _odds(lock_terms(game, who, thing)) if ok else None
        elif verb == "force":
            ok = thing.state in ("locked", "shut") and (
                thing.kind not in DOORS or thing.state == "locked")
            why = "Nothing to force."
            odds = _odds(force_terms(game, who, thing)) if ok else None
        elif verb == "breach":
            charges = who.kit.count("breach_charge") - who.spent.count(
                "breach_charge")
            ok = thing.state == "locked" and charges > 0
            why = ("Not locked." if thing.state != "locked"
                   else "Nobody here is carrying a breaching charge.")
        elif verb == "search":
            ok = thing.state not in ("locked", "searched")
            why = "Locked." if thing.state == "locked" else "Already emptied."
        elif verb == "hack":
            ok = thing.state not in ("hacked",)
            why = "Already in."
            odds = _odds(hack_terms(game, walk, who)) if ok else None
        elif verb == "read":
            ok = thing.state not in ("read", "hacked")
            why = "Read already."
        elif verb == "take":
            ok = bool(thing.holds) and walk.kind in ("wreck", "prize")
            why = ("Not yours to take." if walk.kind not in ("wreck", "prize")
                   else "Nothing left.")
        elif verb == "repair":
            ok = thing.state != "done"
            why = "Fixed."
            odds = _odds(repair_terms(game, who)) if ok else None
        elif verb == "burn":
            ok = thing.state != "done"
            why = "Burned out already."
            odds = _odds(burn_terms(game, who)) if ok else None
        elif verb == "study":
            ok = thing.state not in ("done", "studied")
            why = "Nothing more to learn from it."
            odds = _odds(study_terms(game, who, thing)) if ok else None
            stage = RELIC_STAGES.get(thing.state) \
                if thing.kind == "relic" else None
            if stage:
                label += f" ({stage[1]})"
        elif verb == "rest":
            ok = walk.mode == "calm" and "rested" not in walk.incidents
            why = ("Not with somebody hunting you." if walk.mode != "calm"
                   else "You have rested once already.")
            price = rest_price(game, walk, thing)
            if price:
                # A lodging's bed is somebody's to sell: say what, first.
                label += f" — {price:,} cr"
                if ok and game.credits < price:
                    ok, why = False, "You cannot pay for the night."
        elif verb == "lift":
            ok = thing.link >= 0 and (who.x, who.y) == (thing.x, thing.y)
            why = "Stand on it first." if thing.link >= 0 else "It goes nowhere."
        elif verb == "leave":
            ok, why = ready_to_leave(walk, thing)
        elif verb == "serve":
            ok = server(walk, thing) is not None
            why = "Nobody is behind it."
        note = getattr(kind, "note", "")
        if verb in ("search", "hack") and walk.kind in LIVING:
            # Said before it is done, not after: this is somebody's.
            note = ("Not yours. Anything taken here is theft, and anybody "
                    "who sees it is a witness.")
        if verb == "leave" and walk.kind == "prize" and not walk.prize_done:
            # Saying so before it happens: walking off a prize is letting
            # her go.
            note = ("Leaving without claiming or stripping her lets her go "
                    "— her people remember that.")
        out.append(Act(verb, label, ok, "" if ok else why, odds, "thing",
                       thing.id, note))
    return out


#: How near the way out everybody still standing must be to leave together.
#: Four squares: a party of four in a one-square crawlway is a line of four.
LEAVE_REACH = 4


def ready_to_leave(walk, exit_thing) -> tuple:
    """Everybody still standing gathered near the way out."""
    far = [a.name for a in party(walk, standing=True)
           if a.deck != exit_thing.deck or afoot_map.apart(walk, a, exit_thing) > LEAVE_REACH]
    if far:
        return False, "Not everybody is here: " + ", ".join(far) + "."
    return True, ""


def server(walk, counter):
    """Whoever is working behind a counter."""
    return next((a for a in walk.actors if a.side == "npc" and a.standing
                 and a.room == counter.room and a.deck == counter.deck
                 and a.mood not in ("hostile", "fled")
                 and afoot_map.apart(walk, a, counter) <= 1),
                None)


def offer(game, walk, who) -> list:
    """Every act open to one party member from where they stand."""
    if not who.standing or who.side != "party":
        return []
    out, seen = [], set()
    for thing in _near_things(walk, who):
        for act in _thing_acts(game, walk, who, thing):
            if (act.id, act.label) in seen:
                continue            # two squares of one counter: one button
            seen.add((act.id, act.label))
            out.append(act)
    out += _people_acts(game, walk, who)
    out += _self_acts(game, walk, who)
    if who.acted:
        out = [a if a.id in FREE or not a.ok else
               replace(a, ok=False, why="Already acted this round.")
               for a in out]
    return [a if not a.ok else replace(a, why="") for a in out]


#: Acts that do not use up the round's action.
FREE = ("open", "close", "sneak", "walk", "lift", "leave", "drop")


def _people_acts(game, walk, who) -> list:
    from . import afoot_fight
    out = []
    for other in walk.actors:
        if other.id == who.id or other.deck != who.deck or \
                other.status == "gone":
            continue
        far = afoot_map.apart(walk, who, other)
        if other.side == "party" and far <= 1:
            if other.status in ("down", "stable") or other.hp < other.hp_max:
                got = afoot_fight.aid_terms(game, walk, who, other)
                out.append(Act("aid", f"First aid — {other.name}", got["ok"],
                               got["why"], got["odds"], "actor", other.id))
            if other.status in ("down", "stable") and who.carrying < 0:
                out.append(Act("carry", f"Carry {other.name}", True, "",
                               None, "actor", other.id))
        beaten = other.status in ("dead", "down", "stable") \
            or other.mood == "surrendered"
        if other.side == "npc" and far <= 1 and beaten:
            if "searched" not in other.talked:
                out.append(Act("frisk", f"Search {other.name}", True, "",
                               None, "actor", other.id))
    if who.carrying >= 0:
        out.append(Act("drop", "Put them down", True, "", None, "self"))
    return out


def _self_acts(game, walk, who) -> list:
    out = [Act("sneak", "Stop sneaking" if who.stance == "sneak"
               else "Sneak", True, "", None, "self",
               blurb="Half pace, and only a Recon throw sees you.")]
    arm = arms.arm(who.weapon)
    seen = [a for a in walk.actors if a.hostile and a.deck == who.deck
            and afoot_map.sees(walk, who.deck, who.x, who.y, a.x, a.y)]
    out.append(Act("aim", "Aim", bool(seen) and who.aim < 2,
                   "Nobody to aim at." if not seen else "Aimed as well as "
                   "anybody can.", None, "self",
                   blurb="+1 on the next shot; twice at most."))
    out.append(Act("watch", "Stand watch", who.stance != "watch",
                   "Already watching.", None, "self",
                   blurb=f"Use the {arm.name} on the first enemy that moves "
                         "in reach."))
    if walk.kind == "prize" and not walk.prize_done:
        here = next((r for r in walk.rooms if r.holds(who.deck, who.x, who.y)),
                    None)
        from . import prize
        can, why = prize.can_take_hull(game, walk.prize)
        if here is not None and here.kind in ("bridge", "core"):
            out.append(Act("claim", "Put a prize crew aboard her", can, why,
                           None, "self",
                           blurb=f"{prize.crew_needed(walk.prize)} hands "
                                 "cross over, and she sails in company."))
    stims = who.kit.count("stims") - who.spent.count("stims")
    if stims > 0 and who.hp < who.hp_max:
        out.append(Act("stims", "Take stimulants", True, "", None, "self",
                       blurb="Five stamina back, now; paid for later."))
    return out


# ── doing it ───────────────────────────────────────────────────────────────

def perform(game, walk, who, act_id: str, target: int, dice) -> dict:
    """Do one offered act. Refuses anything `offer` would not have offered.

    `dice` draws the round's dice, and is only called once the act is going
    ahead: a refused press spends no luck, so pressing it again is not a
    reroll."""
    offered = next((a for a in offer(game, walk, who)
                    if a.id == act_id and a.target == target), None)
    if offered is None:
        return {"ok": False, "why": "That is not something they can do here."}
    if not offered.ok:
        return {"ok": False, "why": offered.why}
    from . import afoot_deeds
    fn = afoot_deeds.DEEDS.get(act_id)
    if fn is None:
        return {"ok": False, "why": "Nobody knows how."}
    out = fn(game, walk, who, target, dice())
    if act_id not in FREE and out.get("ok"):
        who.acted = True
    touch(walk)
    return out


def item_name(kit_id: str) -> str:
    item = kit_table.ITEM_BY_ID.get(kit_id)
    return item.name if item is not None else kit_id
