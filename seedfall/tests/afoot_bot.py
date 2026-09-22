"""A party leader good enough to test the decks with.

Plays a walk the way the screens teach: in calm, explore — walk into every
room, greet whoever is there, search what may be searched — and in action,
fight: patch up anybody down within reach, take the best shot on offer, and
close in when there is none. When there is nothing left to do it carries
the fallen to the way out and leaves.

It presses only the doors the screen presses (`sim/afoot`), so anything it
can do a player can, and anything that jams it would jam a player.
"""

from __future__ import annotations

from ..sim import afoot, afoot_acts, afoot_fight, afoot_map
from ..sim.afoot_state import others, party

#: Rounds before the bot gives up on a walk and calls it jammed.
PATIENCE = 400


def play(game, rounds: int = PATIENCE, loot: bool = True,
         talk: bool = True) -> dict:
    """Play the walk in progress to its end. Returns what happened."""
    seen = {"rounds": 0, "talked": 0, "searched": 0, "shots": 0, "aid": 0,
            "outcome": ""}
    walk = afoot.current(game)
    visited: set = set()
    greeted: set = set()
    tried: set = set()
    while walk is not None and not walk.over and seen["rounds"] < rounds:
        if walk.mode == "action":
            _fight(game, walk, seen)
        else:
            _explore(game, walk, seen, visited, greeted, tried, loot, talk)
        if walk.over:
            break
        afoot.end_turn(game)
        seen["rounds"] += 1
    seen["outcome"] = walk.outcome if walk is not None else ""
    seen["jammed"] = walk is not None and not walk.over
    return seen


# ── in action ──────────────────────────────────────────────────────────────

def _fight(game, walk, seen) -> None:
    for mate in party(walk, standing=True):
        if walk.over or walk.mode != "action":
            return
        if _aid(game, walk, mate, seen):
            continue
        foes = [a for a in walk.actors if a.hostile and a.deck == mate.deck]
        if not foes:
            continue
        shots = [(afoot_fight.terms(game, walk, mate, f), f) for f in foes]
        best = max(shots, key=lambda s: s[0]["odds"] if s[0]["ok"] else -1)
        if not best[0]["ok"] or best[0]["odds"] < 0.28:
            target = min(foes, key=lambda f: afoot_map.distance(
                mate.x, mate.y, f.x, f.y))
            route = afoot_map.path(walk, mate, target.x, target.y, near=True)
            if route:
                cut = route[:max(1, mate.mp)]
                afoot.move(game, mate.id, *cut[-1])
            shots = [(afoot_fight.terms(game, walk, mate, f), f) for f in foes
                     if f.standing]
            if not shots:
                continue
            best = max(shots, key=lambda s: s[0]["odds"] if s[0]["ok"] else -1)
        if best[0]["ok"] and not mate.acted:
            afoot.attack(game, mate.id, best[1].id)
            seen["shots"] += 1


def _aid(game, walk, mate, seen) -> bool:
    for act in afoot_acts.offer(game, walk, mate):
        if act.id == "aid" and act.ok:
            downed = next(a for a in walk.actors if a.id == act.target)
            if downed.status in ("down", "stable"):
                afoot.act(game, mate.id, "aid", act.target)
                seen["aid"] += 1
                return True
    return False


# ── in calm ────────────────────────────────────────────────────────────────

def _explore(game, walk, seen, visited, greeted, tried, loot,
             talk) -> None:
    leader = next(iter(party(walk, standing=True)), None)
    if leader is None:
        return
    afoot.select(game, leader.id)
    for mate in party(walk, standing=True):
        if _aid(game, walk, mate, seen):
            return
    if talk and _greet(game, walk, leader, greeted, seen):
        return
    if loot and _search(game, walk, leader, seen, tried):
        return
    goal = _next_room(walk, leader, visited)
    if goal is not None:
        visited.add(goal.id)
        spot = _inside(walk, goal)
        if spot is not None:
            afoot.move(game, leader.id, *spot)
        return
    _home(game, walk, leader)


def _greet(game, walk, leader, greeted, seen) -> bool:
    for npc in others(walk):
        if npc.id in greeted or npc.deck != leader.deck or not npc.standing:
            continue
        if afoot_map.distance(leader.x, leader.y, npc.x, npc.y) > 3:
            continue
        greeted.add(npc.id)
        topics = afoot.talk_options(game, leader.id, npc.id)
        if any(t.id == "greet" and t.ok for t in topics):
            afoot.talk(game, leader.id, npc.id, "greet")
            seen["talked"] += 1
            return True
    return False


def _search(game, walk, leader, seen, tried) -> bool:
    if walk.kind not in ("wreck", "prize"):
        return False
    for act in afoot_acts.offer(game, walk, leader):
        if act.id in ("search", "take") and act.ok:
            afoot.act(game, leader.id, act.id, act.target)
            seen["searched"] += 1
            return True
    boxes = [t for t in walk.things if t.deck == leader.deck
             and t.kind in ("locker", "crate", "desk", "bench", "cargo")
             and t.state not in ("searched", "locked") and t.holds
             and t.id not in tried]
    if boxes:
        box = min(boxes, key=lambda t: afoot_map.distance(
            leader.x, leader.y, t.x, t.y))
        tried.add(box.id)
        route = afoot_map.path(walk, leader, box.x, box.y, near=True)
        if route:
            afoot.move(game, leader.id, *route[-1])
            for act in afoot_acts.offer(game, walk, leader):
                if act.id in ("search", "take") and act.ok and \
                        act.target == box.id:
                    afoot.act(game, leader.id, act.id, act.target)
                    seen["searched"] += 1
            return True
    return False


def _next_room(walk, leader, visited):
    rooms = [r for r in walk.rooms if r.id not in visited
             and r.deck == leader.deck]
    if not rooms:
        return None
    return min(rooms, key=lambda r: afoot_map.distance(
        leader.x, leader.y, r.x + r.w // 2, r.y + r.h // 2))


def _inside(walk, room):
    g = afoot_map.ground(walk, room.deck)
    return next((c for c in room.cells() if g.passable(*c)), None)


def _home(game, walk, leader) -> None:
    """Carry anybody down, gather at the way out, and leave."""
    for mate in party(walk, standing=True):
        downed = [a for a in party(walk) if a.status in ("down", "stable")
                  and not any(b.carrying == a.id for b in walk.actors)]
        if downed and mate.carrying < 0:
            target = downed[0]
            if afoot_map.distance(mate.x, mate.y, target.x, target.y) > 1:
                route = afoot_map.path(walk, mate, target.x, target.y,
                                       near=True)
                if route:
                    afoot.move(game, mate.id, *route[-1])
            afoot.act(game, mate.id, "carry", target.id)
    exits = [t for t in walk.things if t.kind in ("airlock", "gangway")]
    if not exits:
        return
    door = exits[0]
    if leader.deck != door.deck:
        lift = next((t for t in walk.things if t.kind == "lift"
                     and t.deck == leader.deck and t.link >= 0
                     and _toward(walk, t, door.deck)), None)
        if lift is None:
            return
        if (leader.x, leader.y) != (lift.x, lift.y):
            afoot.move(game, leader.id, lift.x, lift.y)
        if (leader.x, leader.y) == (lift.x, lift.y):
            afoot.act(game, leader.id, "lift", lift.id)
        return
    for mate in party(walk, standing=True):
        if mate.deck == door.deck and afoot_map.distance(
                mate.x, mate.y, door.x, door.y) > 1:
            _close_in(game, walk, mate, door)
    for act in afoot_acts.offer(game, walk, leader):
        if act.id == "leave" and act.ok:
            afoot.act(game, leader.id, "leave", act.target)
            return


def _toward(walk, lift, deck: int) -> bool:
    other = next((t for t in walk.things if t.id == lift.link), None)
    return other is not None and abs(other.deck - deck) < abs(lift.deck - deck)


def _close_in(game, walk, mate, door) -> None:
    """Get as near the way out as the squares allow."""
    route = afoot_map.path(walk, mate, door.x, door.y, near=True)
    if route:
        afoot.move(game, mate.id, *route[-1])
        return
    spots = afoot_map.reach(walk, mate, 40)
    best = min(spots, key=lambda s: (afoot_map.distance(*s, door.x, door.y),
                                     spots[s]), default=None)
    if best is not None and best != (mate.x, mate.y):
        afoot.move(game, mate.id, *best)
