"""Afoot: the front door to walking a deck.

Every act the Afoot screen offers comes through here, and each returns the
game's usual `{ok, why, ...}`:

- `begin` / `begin_prize` — lay the site out, put the party at the way in,
  cast everybody else, fill the lockers and draw the incidents;
- `move` — walk a party member somewhere. **Calm** (nobody hostile knows
  you are here): the whole path, the others following, rounds passing as
  the steps are taken and the walk stopping the moment anybody notices you.
  **Action**: as far as this round's movement goes, and no further;
- `attack`, `act`, `talk` — the three things a person does besides walk,
  each through its own module (`afoot_fight`, `afoot_acts`, `afoot_talk`);
- `end_turn` — the party is done: everybody else acts, the bleeding bleed,
  the deck does what it does to the unsuited, and a new round begins;
- `surrender` — go quietly with the watch.

`mend` is the one line the daily clock calls: wounds kept from a walk close
a little every day, faster with a medic aboard and faster again with a
sickbay (`core/shiptime`).

All the dice are `game.rng("afoot")`, drawn here and only here: a screen
asks the sim what *would* happen as often as it likes, and nothing moves
until one of these doors is called.
"""

from __future__ import annotations

from . import (afoot_acts, afoot_ai, afoot_ends, afoot_fight, afoot_fire,
               afoot_incidents, afoot_map, afoot_people, afoot_sites,
               afoot_talk)
from .afoot_state import actor, party, say, touch
# Beginning a walk lives in `sim/afoot_begin.py` (split at the length rule);
# re-exported, one name a line, so every caller keeps asking this door.
from .afoot_begin import SHIPS_ISSUE_ARMS  # noqa: F401
from .afoot_begin import SHIPS_ISSUE_SUIT  # noqa: F401
from .afoot_begin import airless  # noqa: F401
# What renown reads of a career on foot (`renown_facts.wave_b`, "afoot:…").
from .afoot_ends import progress  # noqa: F401
from .afoot_begin import begin  # noqa: F401
from .afoot_begin import begin_prize  # noqa: F401
from .afoot_begin import can_begin  # noqa: F401
from .afoot_begin import crossing_for  # noqa: F401
from .afoot_begin import enlist  # noqa: F401
from .afoot_begin import join  # noqa: F401
from .afoot_begin import preview_kit  # noqa: F401

#: Seconds in a round: Traveller's.
ROUND = 6
#: Stamina a kept wound mends a day, before anybody helps it.
MEND_PER_DAY = 1.0


def current(game):
    walk = getattr(game, "afoot", None)
    return walk if walk is not None and not walk.over else None


def boarders(game) -> list:
    """A boarding party: the captain, and the three best with a gun of
    those who can go."""
    from . import lifepath
    ready = [k for k, _n, _w, ok, _why in pool(game)
             if ok and k.startswith("officer:")]

    def aim(key: str) -> int:
        officer = afoot_people.officer_of(game, int(key.split(":")[1]))
        return lifepath.of(game, officer).skill("gun_combat")
    ready.sort(key=lambda k: -aim(k))
    return ["captain"] + ready[:afoot_people.PARTY_MOST - 1]


def sites(game) -> list:
    return afoot_sites.here(game)


def pool(game) -> list:
    return afoot_people.pool(game)


#: Screens a party out on a deck leaves open: the walk itself, anything
#: shooting at you, and the two books. Standing on a place, its own counters
#: too — the Concourse, and the Port's desk and gathering on a quay.
OPEN_ALWAYS = ("afoot", "battle", "help", "codex")
OPEN_AT = {"port": ("concourse", "port"), "kith": ("concourse", "port"),
           "habitat": ("concourse",), "downside": ("concourse",),
           "holding": ("concourse",), "station": ("concourse",),
           "base": ("concourse",)}


def holds(game, view_id: str) -> bool:
    """Does a walk in progress keep the window from this screen?"""
    walk = current(game)
    if walk is None or view_id in OPEN_ALWAYS:
        return False
    return view_id not in OPEN_AT.get(walk.kind, ())


def select(game, actor_id: int) -> dict:
    """Take one of the party in hand, and look at the deck they are on."""
    walk = current(game)
    who = actor(walk, actor_id) if walk else None
    if who is None or who.side != "party":
        return {"ok": False, "why": "Not one of yours."}
    walk.selected, walk.viewing = who.id, who.deck
    return {"ok": True}


def view_deck(game, deck: int) -> dict:
    walk = current(game)
    if walk is None or not 0 <= deck < len(walk.decks):
        return {"ok": False, "why": "No such deck."}
    walk.viewing = deck
    return {"ok": True}


# ── seeing ─────────────────────────────────────────────────────────────────

def look(walk) -> None:
    """Mark everything the party can see as seen, and name the rooms."""
    for who in party(walk, standing=True):
        deck = walk.decks[who.deck]
        rows = [list(r) for r in deck.seen]
        for x, y in afoot_map.view(walk, who.deck, who.x, who.y):
            if 0 <= y < len(rows) and 0 <= x < len(rows[y]):
                rows[y][x] = "1"
        deck.seen = ["".join(r) for r in rows]
        for room in walk.rooms:
            if room.deck == who.deck and not room.known and room.holds(
                    who.deck, who.x, who.y):
                room.known = True


def visible(walk, deck: int) -> set:
    """Squares the party can see on a deck this moment."""
    out = set()
    for who in party(walk, standing=True):
        if who.deck == deck:
            out |= afoot_map.view(walk, deck, who.x, who.y)
    return out


# ── moving ─────────────────────────────────────────────────────────────────

def move(game, actor_id: int, x: int, y: int) -> dict:
    walk = current(game)
    who = actor(walk, actor_id) if walk else None
    if who is None or who.side != "party":
        return {"ok": False, "why": "Nobody to move."}
    if not who.standing:
        return {"ok": False, "why": f"{who.name} is down."}
    route = afoot_map.path(walk, who, x, y)
    if not route:
        return {"ok": False, "why": "There is no way there."}
    route = _no_stack(walk, who, route)
    rng = game.rng("afoot")
    events, walked = [], 0
    calm = walk.mode == "calm"
    for n, step in enumerate(route):
        cost = afoot_map.price(walk, who.deck, [step], who)
        if cost > who.mp or (walk.mode == "action" and not _can_stop(
                walk, who, route, n, who.mp - cost)):
            if walk.mode == "action":
                break
            events += _round(game, walk, rng)
            if walk.over or walk.mode == "action" or _stops(events):
                break
            if not who.standing:
                break
        _step(walk, who, step)
        who.mp -= cost
        walked += 1
        if walk.mode == "calm":
            events += _noticed(game, walk, rng)
            if walk.mode == "action":
                break
    # The rest were walking with the leader; being seen stops them where
    # they are, not where they started.
    if calm and walked:
        _follow(game, walk, who, walked)
    look(walk)
    return {"ok": True, "moved": walked, "events": events,
            "over": walk.over}


def _no_stack(walk, who, route: list) -> list:
    """A route that ends on nobody: an ally may be passed, never stood on."""
    while route and _occupied(walk, who, route[-1]):
        route = route[:-1]
    return route


def _occupied(walk, who, square) -> bool:
    return any(a.id != who.id and a.deck == who.deck and (a.x, a.y) == square
               and a.status != "gone"
               and not any(b.carrying == a.id for b in walk.actors)
               for a in walk.actors)


def _can_stop(walk, who, route: list, n: int, left: int) -> bool:
    """In action, is there a free square to stop on at or after step n
    within what movement is left? If not, stop before stepping onto an ally."""
    if not _occupied(walk, who, route[n]):
        return True
    spent = 0
    for later in route[n + 1:]:
        spent += afoot_map.price(walk, who.deck, [later], who)
        if spent > left:
            return False
        if not _occupied(walk, who, later):
            return True
    return False


def _stops(events: list) -> bool:
    return any(e.get("kind") in ("hail", "notice", "down", "attack")
               for e in events)


def _step(walk, who, step) -> None:
    for t in walk.things:
        if t.deck == who.deck and (t.x, t.y) == step and \
                t.kind in ("door", "hatch") and t.state == "shut":
            t.state = "open"
            touch(walk)
    who.x, who.y = step
    carried = actor(walk, who.carrying) if who.carrying >= 0 else None
    if carried is not None:
        carried.deck, carried.x, carried.y = who.deck, who.x, who.y


def _noticed(game, walk, rng) -> list:
    events = []
    for npc in walk.actors:
        if npc.hostile and not npc.aware:
            events += afoot_ai.notice(game, walk, npc, rng)
    return events


def _follow(game, walk, leader, steps: int) -> None:
    """In calm, the rest of the party keeps up with whoever is leading."""
    for mate in party(walk, standing=True):
        if mate.id == leader.id or mate.deck != leader.deck:
            continue
        if afoot_map.apart(walk, mate, leader) <= 2:
            continue
        route = afoot_map.path(walk, mate, leader.x, leader.y, near=True)
        for step in _no_stack(walk, mate, route[:steps + 2]):
            _step(walk, mate, step)


# ── fighting, doing, talking ───────────────────────────────────────────────

def attack(game, actor_id: int, target_id: int, burst: bool = False) -> dict:
    """A shot, or with a weapon that has Auto a burst (`afoot_fight`)."""
    walk, who, target, why = _aim(game, actor_id, target_id)
    if why:
        return {"ok": False, "why": why}
    innocent = target.mood not in ("hostile",)
    out = afoot_fight.attack(game, walk, who, target,
                             lambda: game.rng("afoot"), burst=burst)
    if out.get("ok"):
        _answered(game, walk, who, target, innocent, "assault")
    return out


def suppress(game, actor_id: int, target_id: int) -> dict:
    """Suppressing fire: pin them, and anybody beside them (`afoot_fire`)."""
    walk, who, target, why = _aim(game, actor_id, target_id)
    if why:
        return {"ok": False, "why": why}
    innocent = target.mood not in ("hostile",)
    out = afoot_fire.suppress(game, walk, who, target)
    if out.get("ok"):
        _answered(game, walk, who, target, innocent, "affray")
    return out


def throw(game, actor_id: int, target_id: int, grenade: str) -> dict:
    """A grenade at somebody's square (`afoot_fire`)."""
    walk, who, target, why = _aim(game, actor_id, target_id)
    if why:
        return {"ok": False, "why": why}
    innocent = target.mood not in ("hostile",)
    out = afoot_fire.throw(game, walk, who, target, grenade,
                           lambda: game.rng("afoot"))
    if out.get("ok"):
        _answered(game, walk, who, target, innocent, "assault")
    return out


def _aim(game, actor_id: int, target_id: int) -> tuple:
    """(walk, who, target, why not): the refusals every hostile act shares,
    asked before any die is drawn."""
    walk = current(game)
    who, target = actor(walk, actor_id), actor(walk, target_id)
    if who is None or target is None or who.side != "party":
        return walk, who, target, "Nobody to fight."
    if who.acted:
        return walk, who, target, f"{who.name} has acted this round."
    if target.side == "party" or (target.officer >= 0 and walk.kind == "ship"
                                  ) or (target.folk == "hand"
                                        and walk.kind == "ship"):
        return walk, who, target, f"{target.name} is one of yours."
    return walk, who, target, ""


def _answered(game, walk, who, target, innocent: bool, offence: str) -> None:
    """What any hostile act brings down: the noise, the round turning to
    action, a charge if the target was not hostile and anybody saw."""
    if not innocent:
        from . import tutorial_watch
        tutorial_watch.deed(game, "fought_afoot")
    walk.mode = "action"
    arm = afoot_fight.weapon(who)
    afoot_ai.alarm(walk, who.deck, who.x, who.y, arm.loud)
    if innocent:
        afoot_acts.witnessed(game, walk, who, offence, 1.0)
        if target.standing and target.mood not in ("fled", "surrendered"):
            fights = bool(target.weapon) or target.folk in ("thug",)
            target.mood = "hostile" if fights else "fled"
            target.aware = True
    for npc in walk.actors:
        if npc.side == "npc" and npc.mood == "hostile" and npc.faction == \
                target.faction and npc.deck == who.deck:
            npc.aware = True


def act(game, actor_id: int, act_id: str, target: int = -1) -> dict:
    walk = current(game)
    who = actor(walk, actor_id) if walk else None
    if who is None:
        return {"ok": False, "why": "Nobody to act."}
    out = afoot_acts.perform(game, walk, who, act_id, target,
                             lambda: game.rng("afoot"))
    if not walk.over:
        look(walk)
    return out


def talk_options(game, actor_id: int, npc_id: int) -> list:
    walk = current(game)
    return afoot_talk.topics(game, walk, actor(walk, actor_id),
                             actor(walk, npc_id))


def talk(game, actor_id: int, npc_id: int, topic: str) -> dict:
    walk = current(game)
    who, other = actor(walk, actor_id), actor(walk, npc_id)
    if who is None or other is None:
        return {"ok": False, "why": "Nobody to talk to."}
    out = afoot_talk.say_to(game, walk, who, other, topic,
                            lambda: game.rng("afoot"))
    if out.get("ok"):
        from . import tutorial_watch
        tutorial_watch.deed(game, "talked_afoot")
    return out


# ── the round ──────────────────────────────────────────────────────────────

def end_turn(game) -> dict:
    walk = current(game)
    if walk is None:
        return {"ok": False, "why": "Nobody is out."}
    events = _round(game, walk, game.rng("afoot"))
    return {"ok": True, "events": events, "over": walk.over}


def _round(game, walk, rng) -> list:
    """Everybody else's turn, and the start of the party's next."""
    events = afoot_ai.turn(game, walk, rng)
    events += afoot_ai.weather(game, walk)
    events += afoot_fight.bleed(game, walk)
    afoot_fire.settle(walk)
    events += afoot_incidents.tick(game, walk)
    walk.round += 1
    walk.seconds += ROUND
    for who in party(walk):
        who.acted = False
        if who.stance == "watch":
            who.stance = ""
        if who.standing:
            who.mp = afoot_people.move_of(game, who)
    if walk.mode == "action" and not threatened(walk):
        walk.mode = "calm"
        say(walk, "Quiet again.", "")
    look(walk)
    if not party(walk, standing=True):
        out = afoot_ends.wiped(game, walk)
        events.append({"kind": "over", "outcome": out["outcome"]})
    return events


def threatened(walk) -> bool:
    """Is anybody who knows the party is here, and means it harm, on a deck
    the party is on? An enemy two decks away is a worry, not a fight."""
    decks = {a.deck for a in party(walk, standing=True)}
    return any(a.hostile and a.aware and a.deck in decks
               for a in walk.actors)


def surrender(game) -> dict:
    walk = current(game)
    if walk is None:
        return {"ok": False, "why": "Nobody is out."}
    return afoot_ends.give_up(game, walk)


# ── between walks ──────────────────────────────────────────────────────────

def mend(game, days: float) -> None:
    """Wounds kept from a walk close by the day: faster with a medic, and
    faster again with a sickbay aboard."""
    wounds = getattr(game, "wounds", None)
    if not wounds or days <= 0:
        return
    from . import lifepath
    medic, _who = lifepath.skill_aboard(game, "medic")
    rate = MEND_PER_DAY + max(0, medic) * 0.5
    if any(v.kind == "clinic" for v in _aboard_doors(game)):
        rate += 1.0
    for key in list(wounds):
        left = float(wounds[key]) - rate * days
        if left <= 0:
            del wounds[key]
        else:
            wounds[key] = round(left, 2)


def _aboard_doors(game) -> list:
    from . import places, shore
    place = places.ship(game)
    return shore.open_here(game, place) if place is not None else []
