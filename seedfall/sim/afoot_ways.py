"""The deeds of getting about: a lift, the way out, a night's sleep, a prize's bridge.

Split from `sim/afoot_deeds.py` at the length rule; `afoot_deeds.DEEDS` is
still the one table every act is looked up in. Same contract: each takes
`(game, walk, who, target, rng)` and does what it was offered as.
"""

from __future__ import annotations

from . import afoot_map, afoot_people
from .afoot_state import actor, actor_at, party, room_at, say, thing

#: A watch of sleep: eight hours, in the walk's seconds.
REST_SECONDS = 8 * 3600


def do_rest(game, walk, who, target, rng):
    """A watch of sleep: stamina back for everybody, and the time it takes.

    In a lodging room the bed is somebody's to sell, and the night goes
    through `sim/shore.ashore` — the one door a night ashore has.
    """
    t = thing(walk, target)
    room = room_at(walk, t.deck, t.x, t.y)
    if room is not None and room.venue and room.kind == "lodging":
        from . import places as places_sim
        from . import shore
        place = places_sim.by_id(game, walk.place_id)
        out = shore.ashore(game, place, room.venue, rng)
        if not out.get("ok"):
            return {"ok": False, "why": out.get("why", "No room.")}
    walk.incidents.append("rested")
    walk.seconds += REST_SECONDS
    medic = max((afoot_people.record(game, a).skill("medic")
                 for a in party(walk, standing=True)), default=-3)
    bonus = max(0, medic) if t.kind == "medbed" else 0
    for mate in party(walk):
        if mate.status in ("dead", "gone"):
            continue
        back = rng.int(1, 6) + bonus
        mate.hp = min(mate.hp_max, mate.hp + back)
        if mate.status in ("down", "stable") and mate.hp > 0:
            mate.status = "up"
    say(walk, "The party sleeps a watch. Everybody is a little better for it.",
        "good")
    return {"ok": True}


def do_lift(game, walk, who, target, rng):
    t = thing(walk, target)
    other = thing(walk, t.link)
    spot = (other.x, other.y)
    if actor_at(walk, other.deck, *spot) is not None:
        free = afoot_map.reach(walk, _ghost(who, other), 2)
        spot = min(free, key=lambda s: afoot_map.distance(*s, other.x,
                                                           other.y),
                   default=None)
        if spot is None:
            return {"ok": False, "why": "There is no room at the other end."}
    riders = [who]
    if walk.mode == "calm":
        # Out of a fight the party travels together: whoever is standing
        # near the lift rides it too, rather than being left a deck behind.
        riders += [m for m in party(walk, standing=True) if m is not who
                   and m.deck == t.deck and afoot_map.distance(
                       m.x, m.y, t.x, t.y) <= LIFT_REACH]
    free = sorted(afoot_map.reach(walk, _ghost(who, other), 3),
                  key=lambda s: afoot_map.distance(*s, other.x, other.y))
    for n, rider in enumerate(riders):
        at = spot if n == 0 else next(
            (s for s in free if actor_at(walk, other.deck, *s) is None), None)
        if at is None:
            continue
        rider.deck, (rider.x, rider.y) = other.deck, at
        carried = actor(walk, rider.carrying) if rider.carrying >= 0 else None
        if carried is not None:
            carried.deck, carried.x, carried.y = rider.deck, rider.x, rider.y
    walk.viewing = who.deck
    who.mp = 0
    said = who.name if len(riders) == 1 else f"{who.name} and the others"
    say(walk, f"{said} ride{'s' if len(riders) == 1 else ''} the lift to "
              f"{walk.decks[who.deck].name}.")
    return {"ok": True, "deck": who.deck}


#: How near the lift the rest of a calm party must be to ride with the
#: leader: the same reach as leaving together.
LIFT_REACH = 4


def _ghost(who, at):
    from .afoot_state import Actor
    return Actor(id=who.id, name="", side=who.side, folk="", deck=at.deck,
                 x=at.x, y=at.y, hp=1, hp_max=1)


def do_leave(game, walk, who, target, rng):
    from . import afoot_ends
    return afoot_ends.leave(game, walk)


def do_claim(game, walk, who, target, rng):
    """Put a prize crew aboard her, from her own bridge."""
    from . import prize
    out = prize.take_hull(game, walk.prize, walk.prize_faction)
    if out.get("ok"):
        walk.prize_done = "taken"
        # Her hold is her own again: it sails with her, not across to yours.
        for stack in walk.things:
            if stack.kind == "cargo":
                stack.state = "claimed"
        say(walk, "Her bridge is yours. The prize crew are on their way over.",
            "good")
    return out
