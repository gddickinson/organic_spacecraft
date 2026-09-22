"""The acts themselves: one function per verb, each doing what it was offered as.

`sim/afoot_acts.offer` decides what can be done and at what odds; this does
it, with the same terms (`afoot_acts.lock_terms` and its siblings), so the
forecast on the button is the roll. Every function takes
`(game, walk, who, target, rng)` and returns `{ok, why, text}` plus whatever
the screen needs to know — a talk to open, a deck to look at.

**What is found is banked, not given.** Kit, cargo, evidence and study go
into `walk.found` and reach the chronicle when the party leaves
(`sim/afoot_ends.py`), through the doors that already account for each: a
party that is carried out unconscious does not bring the strongbox with it.
"""

from __future__ import annotations

from . import afoot_acts, afoot_fight, afoot_map, checks
from .afoot_state import actor, say, thing
# Getting about — a lift, the way out, a night's sleep, a prize's bridge —
# split out at the length rule; one table of deeds all the same.
from .afoot_ways import do_claim, do_leave, do_lift, do_rest

#: Stamina a stimulant gives back now, and what it costs afterwards.
STIM_NOW = 5
STIM_AFTER = 3


def _bank(walk, key: str, value) -> None:
    got = walk.found
    if key in ("kit", "intel", "emptied", "spent"):
        got.setdefault(key, []).append(value)
    else:
        kind, amount = value
        bucket = got.setdefault(key, {})
        bucket[kind] = bucket.get(kind, 0) + amount


def _loot(walk, who, holds: list) -> list:
    """Bank what a container or a person held. Returns the words for it."""
    said = []
    for entry in holds:
        if entry.startswith("cargo:"):
            _k, cid, tonnes = entry.split(":")
            _bank(walk, "cargo", (cid, float(tonnes)))
            said.append(f"{float(tonnes):g} t of {cid}")
        elif entry.startswith("evidence:"):
            _k, kind, n = entry.split(":")
            _bank(walk, "evidence", (kind, float(n)))
            said.append(f"{kind} data")
        elif entry.startswith("study:"):
            _bank(walk, "study", ("relic", float(entry.split(":")[1])))
            said.append("notes on it")
        elif entry.startswith("intel:"):
            _bank(walk, "intel", entry.split(":", 1)[1])
            said.append("something worth knowing")
        else:
            _bank(walk, "kit", entry)
            said.append(afoot_acts.item_name(entry))
    return said


# ── doors and locks ────────────────────────────────────────────────────────

def do_open(game, walk, who, target, rng):
    t = thing(walk, target)
    t.state = "open"
    who.mp = max(0, who.mp - 1)
    return {"ok": True, "text": "Open."}


def do_close(game, walk, who, target, rng):
    t = thing(walk, target)
    t.state = "shut"
    who.mp = max(0, who.mp - 1)
    return {"ok": True, "text": "Shut."}


def _crime(game, walk, who, what: str, weight: float = 1.0) -> None:
    afoot_acts.witnessed(game, walk, who, what, weight)


def do_unlock(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.lock_terms(game, who, t)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a lock", what="security")
    if roll.ok:
        t.state = "shut"
        say(walk, f"{who.name} works the lock open.", "good")
    else:
        say(walk, f"{who.name} cannot get the lock to give.", "")
    if walk.kind in afoot_acts.LIVING:
        _crime(game, walk, who, "theft", 0.6)
    return {"ok": True, "done": roll.ok, "check": roll}


def do_force(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.force_terms(game, who, t)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="forcing", what="athletics")
    from . import afoot_ai
    afoot_ai.alarm(walk, who.deck, who.x, who.y, 6)
    if roll.ok:
        t.state = "broken" if t.kind in ("door", "hatch") else "shut"
        say(walk, f"{who.name} forces the {t.kind}.", "good")
    else:
        say(walk, f"{who.name} throws a shoulder at it and it holds.", "")
    if walk.kind in afoot_acts.LIVING:
        _crime(game, walk, who, "theft", 0.8)
    return {"ok": True, "done": roll.ok, "check": roll}


def do_breach(game, walk, who, target, rng):
    t = thing(walk, target)
    who.spent.append("breach_charge")
    t.state = "broken"
    from . import afoot_ai
    afoot_ai.alarm(walk, who.deck, t.x, t.y, 20)
    for other in list(walk.actors):
        if other.deck == t.deck and other.id != who.id and \
                afoot_map.apart(walk, other, t) <= 1:
            afoot_fight.hurt(game, walk, other, rng.int(2, 12), rng=rng)
    say(walk, f"{who.name} blows the {t.kind}.", "warn")
    if walk.kind in afoot_acts.LIVING:
        _crime(game, walk, who, "affray", 1.0)
    return {"ok": True, "done": True}


# ── what is in things ──────────────────────────────────────────────────────

def do_search(game, walk, who, target, rng):
    t = thing(walk, target)
    t.state = "searched"
    got = _loot(walk, who, list(t.holds))
    t.holds = []
    _bank(walk, "emptied", t.id)
    if got:
        say(walk, f"{who.name} finds {', '.join(got)}.", "good")
    else:
        say(walk, f"{who.name} turns it out. Nothing worth the carrying.", "")
    if walk.kind in afoot_acts.LIVING and got:
        _crime(game, walk, who, "theft", 0.5)
    return {"ok": True, "found": got}


def do_frisk(game, walk, who, target, rng):
    other = actor(walk, target)
    other.talked.append("searched")
    holds = [i for i in (other.weapon, other.armour, *other.kit)
             if i and not i.startswith("npc_")]
    if other.status != "dead" and other.weapon and not \
            other.weapon.startswith("npc_"):
        other.weapon = ""
    got = _loot(walk, who, holds)
    say(walk, f"{who.name} goes through {other.name}'s pockets"
              + (f": {', '.join(got)}." if got else " and finds nothing."),
        "good" if got else "")
    if walk.kind in afoot_acts.LIVING and got:
        _crime(game, walk, who, "theft", 0.5)
    return {"ok": True, "found": got}


def do_take(game, walk, who, target, rng):
    t = thing(walk, target)
    if walk.kind == "prize" and walk.prize_done == "taken":
        return {"ok": False, "why": "She is yours now; her hold sails with "
                                    "her."}
    if walk.kind == "prize":
        from . import prize
        out = prize.strip_hull(game, walk.prize)
        walk.prize_done = "stripped"
        for stack in walk.things:
            if stack.kind == "cargo":
                stack.holds = []
        say(walk, "The hold is broken open and swayed across to your own.",
            "good")
        return {"ok": True, "moved": out.get("moved", {})}
    got = _loot(walk, who, list(t.holds))
    t.holds = []
    t.state = "searched"
    _bank(walk, "emptied", t.id)
    say(walk, f"{who.name} tags {', '.join(got)} for the hold.", "good")
    return {"ok": True, "found": got}


def do_hack(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.hack_terms(game, walk, who)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a console", what="computers")
    if walk.kind in afoot_acts.LIVING:
        _crime(game, walk, who, "theft", 0.4)
    if not roll.ok:
        say(walk, f"{who.name} gets nowhere with it.", "")
        return {"ok": True, "done": False, "check": roll}
    t.state = "hacked"
    reveal(walk, t.deck)
    opened = 0
    for door in walk.things:
        if door.deck == t.deck and door.kind in ("door", "hatch") and \
                door.state == "locked" and door.lock <= 2:
            door.state = "shut"
            opened += 1
    got_data = _loot(walk, who, list(t.holds))
    t.holds = []
    _bank(walk, "spent", (t.id, t.state))
    say(walk, f"{who.name} is into it: the deck plan, "
              f"{opened} lock{'s' if opened != 1 else ''} released"
              + (f", and {', '.join(got_data)}" if got_data else "") + ".",
        "good")
    return {"ok": True, "done": True, "check": roll}


def do_read(game, walk, who, target, rng):
    t = thing(walk, target)
    t.state = "read"
    for room in walk.rooms:
        if room.deck == t.deck:
            room.known = True
    got = _loot(walk, who, list(t.holds))
    t.holds = []
    _bank(walk, "spent", (t.id, t.state))
    say(walk, f"{who.name} reads the directory off it"
              + (f", and {', '.join(got)}." if got else "."), "")
    return {"ok": True}


def reveal(walk, deck: int) -> None:
    """Everything on a deck, seen and named."""
    d = walk.decks[deck]
    d.seen = ["1" * d.w for _ in range(d.h)]
    for room in walk.rooms:
        if room.deck == deck:
            room.known = True


def do_repair(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.repair_terms(game, who)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a repair", what="mechanic")
    if roll.ok:
        t.state = "done"
        say(walk, f"{who.name} has it fixed.", "good")
        if t.kind == "fault":
            _mend_fault(game, walk)
    elif roll.disaster:
        say(walk, f"It bites {who.name}.", "bad")
        afoot_fight.hurt(game, walk, who, rng.int(1, 6))
    else:
        say(walk, f"{who.name} cannot find the fault in it yet.", "")
    return {"ok": True, "done": roll.ok, "check": roll}


def _mend_fault(game, walk) -> None:
    """A fault fixed aboard your own hull puts back part of what the worst
    hurt layer is missing (`data/afoot_incidents.FAULT_MENDS`)."""
    from ..data.afoot_incidents import FAULT_MENDS
    for goal in walk.goals:
        if goal[0] == "fault":
            goal[2] = True
    if any(goal[0] == "breakdown" for goal in walk.goals):
        from . import afoot_holdings
        afoot_holdings.resolved(game, walk, "breakdown")
    if walk.kind != "ship":
        return
    hurt = [layer for layer in game.ship.layers if layer.hp < layer.max]
    if not hurt:
        return
    worst = min(hurt, key=lambda layer: layer.hp / max(1.0, layer.max))
    back = (worst.max - worst.hp) * FAULT_MENDS
    worst.hp = min(worst.max, worst.hp + back)
    say(walk, f"The {worst.name.lower()} is holding better: {back:.0f} back.",
        "good")


def do_burn(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.burn_terms(game, who)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="the node", what="survival")
    if not roll.ok:
        say(walk, f"{who.name} cuts into it and it closes up again.", "warn")
        return {"ok": True, "done": False, "check": roll}
    t.state = "done"
    for spore in [s for s in walk.things if s.kind == "spores"
                  and s.deck == t.deck]:
        walk.things.remove(spore)
    _bank(walk, "burned", ("nest", 1))
    _bank(walk, "spent", (t.id, t.state))
    say(walk, f"{who.name} burns the node out. The walls stop moving.",
        "good")
    return {"ok": True, "done": True, "check": roll}


def do_study(game, walk, who, target, rng):
    t = thing(walk, target)
    got = afoot_acts.study_terms(game, who, t)
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="study", what=got["what"])
    if not roll.ok:
        say(walk, f"{who.name} looks at it for a long time and learns "
                  "nothing that will stay learned.", "")
        return {"ok": True, "done": False, "check": roll}
    if t.kind == "relic":
        return _relic(game, walk, who, t, roll)
    t.state = "studied"
    _bank(walk, "spent", (t.id, t.state))
    if t.kind == "spore_node":
        _bank(walk, "evidence", ("specimen", 8 + max(0, roll.effect)))
        say(walk, f"{who.name} takes samples off the node.", "good")
    else:
        worth = sum(float(h.split(":")[1]) for h in t.holds
                    if h.startswith("study:")) or 20.0
        worth *= 1.0 + max(0, roll.effect) / 6.0
        _bank(walk, "study", ("relic", round(worth, 1)))
        t.holds = []
        say(walk, f"{who.name} works out part of what it was for.", "good")
    return {"ok": True, "done": True, "check": roll}


def _relic(game, walk, who, t, roll):
    """One stage of a relic (`afoot_things.RELIC_STAGES`): a first reading,
    the chamber answering — whatever keeps it stands down — and what it
    was for, the richest of the three."""
    from ..data.afoot_things import RELIC_STAGES
    after, called, _how = RELIC_STAGES[t.state]
    first = sum(float(h.split(":")[1]) for h in t.holds
                if h.startswith("study:")) or 20.0
    worth = first * (1.0 + max(0, roll.effect) / 6.0)
    if after == "read":
        _bank(walk, "study", ("relic", round(worth, 1)))
        text = f"{who.name} takes a first reading off it."
    elif after == "attuned":
        stood = 0
        for npc in walk.actors:
            if npc.deck == t.deck and npc.folk == "sentry" and npc.standing:
                npc.mood, npc.aware = "surrendered", False
                stood += 1
        _bank(walk, "study", ("relic", round(worth / 2, 1)))
        text = (f"{who.name} finds the note it answers to. The chamber "
                "answers back" + (f", and {stood} sentr"
                                  f"{'ies' if stood != 1 else 'y'} stand "
                                  "down." if stood else "."))
    else:
        _bank(walk, "study", ("relic", round(worth * 2, 1)))
        _bank(walk, "evidence", ("specimen", 12 + max(0, roll.effect)))
        t.holds = []
        text = f"{who.name} works out what it was for. It was not for us."
    t.state = after
    _bank(walk, "spent", (t.id, t.state))
    say(walk, text, "good")
    return {"ok": True, "done": True, "check": roll, "stage": called}


def do_serve(game, walk, who, target, rng):
    t = thing(walk, target)
    server = afoot_acts.server(walk, t)
    return {"ok": True, "talk": server.id if server else -1}


# ── people ─────────────────────────────────────────────────────────────────

def do_aid(game, walk, who, target, rng):
    return afoot_fight.first_aid(game, walk, who, actor(walk, target), rng)


def do_carry(game, walk, who, target, rng):
    other = actor(walk, target)
    who.carrying = other.id
    other.deck, other.x, other.y = who.deck, who.x, who.y
    say(walk, f"{who.name} gets {other.name} over a shoulder.", "")
    return {"ok": True}


def do_drop(game, walk, who, target, rng):
    other = actor(walk, who.carrying)
    who.carrying = -1
    if other is None:
        return {"ok": True}
    near = sorted(afoot_map.reach(walk, who, 2),
                  key=lambda s: afoot_map.distance(
                      *s, who.x, who.y, afoot_map.span(walk, who.deck)))
    spot = next((s for s in near if s != (who.x, who.y)), (who.x, who.y))
    other.x, other.y = spot
    say(walk, f"{who.name} puts {other.name} down.", "")
    return {"ok": True}


# ── stances ────────────────────────────────────────────────────────────────

def do_sneak(game, walk, who, target, rng):
    who.stance = "" if who.stance == "sneak" else "sneak"
    return {"ok": True}


def do_aim(game, walk, who, target, rng):
    who.aim = min(afoot_fight.AIM_MOST, who.aim + 1)
    return {"ok": True}


def do_watch(game, walk, who, target, rng):
    who.stance = "watch"
    say(walk, f"{who.name} stands watch.", "")
    return {"ok": True}


def do_stims(game, walk, who, target, rng):
    who.spent.append("stims")
    who.hp = min(who.hp_max, who.hp + STIM_NOW)
    _bank(walk, "strain", (str(who.officer), STIM_AFTER))
    say(walk, f"{who.name} takes a stimulant.", "")
    return {"ok": True}


#: Every act, by the id `afoot_acts.offer` gives it. One door each.
DEEDS = {
    "open": do_open,
    "close": do_close,
    "unlock": do_unlock,
    "force": do_force,
    "breach": do_breach,
    "search": do_search,
    "frisk": do_frisk,
    "take": do_take,
    "hack": do_hack,
    "read": do_read,
    "repair": do_repair,
    "burn": do_burn,
    "study": do_study,
    "rest": do_rest,
    "lift": do_lift,
    "leave": do_leave,
    "serve": do_serve,
    "aid": do_aid,
    "carry": do_carry,
    "drop": do_drop,
    "sneak": do_sneak,
    "aim": do_aim,
    "watch": do_watch,
    "stims": do_stims,
    "claim": do_claim,
}
