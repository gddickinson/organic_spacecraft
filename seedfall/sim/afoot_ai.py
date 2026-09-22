"""The other side's turn: who notices, who comes, who shoots, who runs.

Everybody who is not in the party acts once a round, in id order, off the
walk's own dice. What they do follows from their mood and their ways
(`data/afoot_folk.py`):

- **hostile and aware** — pick the nearest party member they can see, close
  to where their weapon reaches, and use it; move *and* shoot in one turn,
  as the ship-scale enemy learned to in the 2026-08 review;
- **hostile and unaware** — keep to their ways, and look. A party member in
  their sight is noticed at once, unless they are sneaking, when it takes a
  Recon throw against the sneaker's Stealth;
- **fled** — make for the nearest way off the deck, and leave by it;
- **surrendered** — stay where they are, hands where you can see them;
- **everybody else** — keep station, wander their room, or walk the
  corridors, as their ways say.

**Standing watch** is the party's answer: a party member on watch takes one
shot at the first hostile that moves where they can see it, before it gets
to act.
"""

from __future__ import annotations

from ..data import afoot_arms as arms
from ..data.afoot_folk import FOLK_BY_ID
from ..data.afoot_things import EXITS, HAZARDS
from . import afoot_fight, afoot_map, afoot_people, checks
from .afoot_state import GROUND, HALL, others, party, say

#: How often a wanderer takes a step in a round.
WANDER = 0.35


def npc_move(game, npc) -> int:
    rec = afoot_people.record(game, npc)
    squares = arms.BASE_MOVE + checks.modifier(rec.score("dex"))
    worn = arms.guard(npc.armour)
    if worn is not None:
        squares -= worn.slow
    kind = FOLK_BY_ID.get(npc.folk)
    if kind is not None and kind.id == "creeper":
        squares = 2
    return max(arms.LEAST_MOVE, squares)


def turn(game, walk, rng) -> list:
    """Every NPC acts once. Returns the events, for the screen."""
    events = []
    decks = {a.deck for a in party(walk)}
    for npc in list(others(walk)):
        if not npc.standing:
            continue
        if npc.deck not in decks:
            if npc.mood == "hostile" and npc.aware:
                _pursue(game, walk, npc, decks)
            continue
        if npc.mood == "fled":
            events += _flee(game, walk, npc)
        elif npc.mood == "hostile":
            if not npc.aware:
                events += notice(game, walk, npc, rng)
            if npc.aware:
                events += _fight(game, walk, npc, rng)
                _lose_track(walk, npc)
            else:
                _keep_ways(game, walk, npc, rng)
        elif npc.mood != "surrendered":
            _keep_ways(game, walk, npc, rng)
    return events


def notice(game, walk, npc, rng) -> list:
    """Does this NPC see anybody from the party? Sneakers get a throw."""
    kind = FOLK_BY_ID.get(npc.folk)
    reach = getattr(kind, "sight", afoot_map.SIGHT)
    for who in party(walk, standing=True):
        if who.deck != npc.deck or not afoot_map.sees(
                walk, npc.deck, npc.x, npc.y, who.x, who.y, reach):
            continue
        if who.stance == "sneak":
            stealth = afoot_people.record(game, who).skill("stealth")
            roll = checks.roll(rng, npc.skills.get("recon", -1),
                               npc.stats.get("int", 7), "average",
                               -(max(0, stealth) + 1), about="notice",
                               what="recon")
            if not roll.ok:
                continue
        npc.aware = True
        if walk.mode != "action":
            walk.mode = "action"
        say(walk, f"{npc.name} has seen {who.name}.", "warn")
        return [{"kind": "notice", "who": npc.id, "saw": who.id}]
    return []


#: Rounds an enemy goes without sight of anybody in the party before it
#: stops knowing where they are.
LOST_AFTER = 4


def _lose_track(walk, npc) -> None:
    kind = FOLK_BY_ID.get(npc.folk)
    reach = getattr(kind, "sight", afoot_map.SIGHT)
    if any(a.deck == npc.deck and afoot_map.sees(
            walk, npc.deck, npc.x, npc.y, a.x, a.y, reach)
           for a in party(walk, standing=True)):
        npc.lost = 0
        return
    npc.lost += 1
    if npc.lost >= LOST_AFTER:
        npc.aware, npc.lost = False, 0
        say(walk, f"{npc.name} has lost you.", "")


def alarm(walk, deck: int, x: int, y: int, loud: int) -> None:
    """A noise: every hostile within earshot knows somebody is here."""
    for npc in others(walk):
        if npc.deck == deck and npc.mood == "hostile" and \
                afoot_map.distance(npc.x, npc.y, x, y,
                                   afoot_map.span(walk, deck)) <= loud:
            npc.aware = True


def _targets(walk, npc) -> list:
    kind = FOLK_BY_ID.get(npc.folk)
    killer = kind is not None and kind.kind == "bloom"
    rows = [a for a in party(walk) if a.deck == npc.deck
            and (a.standing or (killer and a.status in ("down", "stable")))]
    return sorted(rows, key=lambda a: (not a.standing, afoot_map.apart(walk, npc, a), a.id))


def _fight(game, walk, npc, rng) -> list:
    events = []
    targets = _targets(walk, npc)
    if not targets:
        return events
    arm = arms.arm(npc.weapon)
    for target in targets:
        got = afoot_fight.terms(game, walk, npc, target)
        if got["ok"] and (not arm.melee or got["far"] <= 1):
            return events + _shoot(game, walk, npc, target, rng)
    target = targets[0]
    if npc.pinned > 0:
        return events          # pinned: they keep their head down
    events += _approach(game, walk, npc, target, arm, rng)
    if not npc.standing:
        return events
    for target in _targets(walk, npc):
        got = afoot_fight.terms(game, walk, npc, target)
        if got["ok"]:
            events += _shoot(game, walk, npc, target, rng)
            break
    return events


def _shoot(game, walk, npc, target, rng) -> list:
    # Anything with Auto is fired in bursts by the people who carry it.
    out = afoot_fight.attack(game, walk, npc, target, rng,
                             burst=bool(arms.arm(npc.weapon).auto))
    alarm(walk, npc.deck, npc.x, npc.y, arms.arm(npc.weapon).loud)
    return [{"kind": "attack", "who": npc.id, "at": target.id,
             "hit": out.get("hit", False)}] + out.get("events", [])


def _approach(game, walk, npc, target, arm, rng) -> list:
    """Close until the weapon reaches, stopping to take watch fire."""
    route = afoot_map.path(walk, npc, target.x, target.y, near=True)
    budget = npc_move(game, npc)
    want = 1 if arm.melee else max(1, arm.short)
    events = []
    for step in route:
        if budget <= 0:
            break
        if afoot_map.apart(walk, npc, target) <= want \
                and afoot_map.sees(walk, npc.deck, npc.x, npc.y,
                                   target.x, target.y):
            break
        cost = afoot_map.price(walk, npc.deck, [step])
        if cost > budget:
            break
        _open_on_way(walk, npc.deck, step)
        npc.x, npc.y = step
        budget -= cost
        events += watch_fire(game, walk, npc, rng)
        if not npc.standing:
            break
    return events


def _open_on_way(walk, deck: int, step: tuple) -> None:
    from .afoot_state import things_at, touch
    for t in things_at(walk, deck, *step):
        if t.kind in ("door", "hatch") and t.state in ("shut", "locked"):
            t.state = "open"
            touch(walk)


def watch_fire(game, walk, mover, rng) -> list:
    """Anybody standing watch who can see the mover takes their shot."""
    events = []
    if mover.side != "npc" or mover.mood != "hostile":
        return events
    for who in party(walk, standing=True):
        if who.stance != "watch" or who.deck != mover.deck:
            continue
        got = afoot_fight.terms(game, walk, who, mover)
        if not got["ok"]:
            continue
        who.stance = ""
        say(walk, f"{who.name} was watching for that.", "")
        out = afoot_fight.attack(game, walk, who, mover, rng)
        events += [{"kind": "watch", "who": who.id, "at": mover.id}]
        events += out.get("events", [])
        if not mover.standing:
            break
    return events


def _pursue(game, walk, npc, decks: set) -> None:
    """An enemy who knows where you went follows you by the lift."""
    lifts = [t for t in walk.things if t.kind == "lift" and t.deck == npc.deck
             and t.link >= 0]
    if not lifts:
        return
    lift = min(lifts, key=lambda t: afoot_map.apart(walk, npc, t))
    if (npc.x, npc.y) != (lift.x, lift.y):
        _walk_to(game, walk, npc, lift.x, lift.y)
        return
    other = next((t for t in walk.things if t.id == lift.link), None)
    if other is None:
        return
    from .afoot_state import actor_at
    if actor_at(walk, other.deck, other.x, other.y) is None:
        npc.deck, npc.x, npc.y = other.deck, other.x, other.y
        say(walk, "The lift is moving. Somebody is coming up after you.",
            "warn")


def _flee(game, walk, npc) -> list:
    exits = [t for t in walk.things if t.deck == npc.deck
             and (t.kind in EXITS or t.kind == "lift")]
    if not exits:
        npc.mood = "surrendered"
        return []
    goal = min(exits, key=lambda t: afoot_map.apart(walk, npc, t))
    if (npc.x, npc.y) == (goal.x, goal.y):
        npc.status = "gone"
        say(walk, f"{npc.name} is gone.", "")
        return [{"kind": "gone", "who": npc.id}]
    route = afoot_map.path(walk, npc, goal.x, goal.y)
    budget = npc_move(game, npc)
    for step in route:
        cost = afoot_map.price(walk, npc.deck, [step])
        if cost > budget:
            break
        _open_on_way(walk, npc.deck, step)
        npc.x, npc.y = step
        budget -= cost
    return []


def _keep_ways(game, walk, npc, rng) -> None:
    kind = FOLK_BY_ID.get(npc.folk)
    ways = getattr(kind, "ways", "wander")
    if npc.incident == "stop" and npc.post and "hailed" not in npc.talked:
        # Sent for somebody: walk up to them (`afoot_incidents.tick` keeps
        # the post on whoever it is), not round the corridors.
        _walk_to(game, walk, npc, npc.post[1], npc.post[2], near=True)
        return
    if ways in ("still",) or (ways in ("keep", "guard") and _at_post(npc)):
        return
    if ways in ("keep", "guard"):
        _walk_to(game, walk, npc, npc.post[1], npc.post[2])
        return
    if ways == "patrol" or ways == "hunt":
        g = afoot_map.ground(walk, npc.deck)
        if _at_post(npc) or not npc.post:
            halls = [(x, y) for y in range(g.deck.h) for x in range(g.deck.w)
                     if g.deck.at(x, y) == HALL and g.passable(x, y)]
            if halls:
                spot = rng.pick(halls)
                npc.post = [npc.deck, spot[0], spot[1]]
        _walk_to(game, walk, npc, npc.post[1], npc.post[2])
        return
    if not rng.chance(WANDER):
        return
    room = next((r for r in walk.rooms if r.id == npc.room), None)
    steps = [(npc.x + dx, npc.y + dy) for dx, dy in afoot_map.STEPS]
    free = afoot_map.reach(walk, npc, 1)
    steps = [s for s in steps if s in free and (
        room is None or room.holds(npc.deck, *s))]
    if steps:
        npc.x, npc.y = rng.pick(steps)


def _at_post(npc) -> bool:
    return bool(npc.post) and (npc.deck, npc.x, npc.y) == tuple(npc.post)


def _walk_to(game, walk, npc, x: int, y: int, near: bool = False) -> None:
    budget = npc_move(game, npc)
    for step in afoot_map.path(walk, npc, x, y, near=near):
        cost = afoot_map.price(walk, npc.deck, [step])
        if cost > budget:
            break
        _open_on_way(walk, npc.deck, step)
        npc.x, npc.y = step
        budget -= cost


# ── the air and the ground ─────────────────────────────────────────────────

def weather(game, walk) -> list:
    """What the deck does to the party this round: vacuum, spores."""
    events = []
    for who in party(walk):
        if who.status in ("dead", "gone"):
            continue
        if not afoot_people.breathes(game, who):
            continue
        worn = arms.guard(who.armour)
        sealed = worn is not None and worn.sealed
        filters = worn is not None and worn.filters
        deck = walk.decks[who.deck]
        hurt = 0
        # No air aboard, or out on the open ground of a world with none.
        outside = not deck.outside_air and deck.at(who.x, who.y) == GROUND
        if (not deck.air or outside) and not sealed:
            hurt = HAZARDS["breach"][1]
        for t in walk.things:
            if t.deck == who.deck and (t.x, t.y) == (who.x, who.y) \
                    and t.kind in HAZARDS:
                need, cost = HAZARDS[t.kind]
                if not (sealed if need == "sealed" else filters):
                    hurt = max(hurt, cost)
        if hurt:
            say(walk, f"{who.name} is choking.", "bad")
            events += afoot_fight.hurt(game, walk, who, hurt)
    return events
