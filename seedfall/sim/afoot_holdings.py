"""Your own holdings, walked: the works failing, the hands out, a stranger in the plant.

A holding used to be somewhere you could walk and meet your own people, and
nothing happened. Now its works can be in trouble when you come down
(`data/afoot_incidents.py`, on your own ground only):

- **breakdown** — something in the works is failing: find it and fix it by
  hand (a Mechanic check on the fault);
- **strike** — the hands have downed tools: hear them out (Leadership and
  SOC), or pay the bonus they want (`STRIKE_BONUS`);
- **sabotage** — a stranger is in the plant: ask them what they are doing
  (Streetwise and INT) and they give it up — or it comes to a fight, and a
  saboteur put down or run off is as good as one who talked.

**It moves the holding's yield.** Set right by hand, the works run sweeter
for `WORKS_DAYS` (`WORKS_BOOST`); walked away from, they run worse
(`WORKS_SLUMP`). `factor` is what the daily colony tick reads; nothing else
about a holding changes, and nothing is conjured — a yield that runs a
quarter better is still the holding's own.
"""

from __future__ import annotations

from ..data import afoot_incidents as table
from . import checks
from .afoot_state import Thing, say, uid

#: The rooms trouble at the works happens in.
WORKS = ("works", "fabhall", "slipway", "farm", "power")
#: Goals each trouble sets on the walk.
GOALS = {"breakdown": "The works are failing: find it and fix it",
         "strike": "The hands are out: hear them",
         "sabotage": "A stranger in the works: find them"}


def colony_of(game, walk):
    """The holding of yours this walk is on, or None."""
    key = str(walk.site)
    if not key.startswith("place:holding-"):
        return None
    cid = key.split("place:holding-", 1)[1]
    return next((c for c in getattr(game, "colonies", []) or []
                 if str(c.id) == cid), None)


def factor(game, colony) -> float:
    """What the works are running at, from what was last done about them on
    foot: 1.0 unless a walk set them right, or left them."""
    got = ((getattr(game, "walked", {}) or {}).get("holdings", {})
           .get(str(getattr(colony, "id", ""))))
    if not got or float(game.day) >= float(got[1]):
        return 1.0
    return 1.0 + float(got[0])


def _mark(game, walk, delta: float) -> None:
    colony = colony_of(game, walk)
    if colony is not None:
        game.walked.setdefault("holdings", {})[str(colony.id)] = [
            delta, float(game.day) + table.WORKS_DAYS]


def holds(game, walk, site, iid: str) -> bool:
    return (site.mine and colony_of(game, walk) is not None
            and any(r.kind in WORKS for r in walk.rooms))


def spawn(game, walk, site, iid: str, rng) -> bool:
    from .afoot_cast import folk, free_spot
    room = rng.pick([r for r in walk.rooms if r.kind in WORKS])
    spot = free_spot(walk, room.deck, room, rng)
    if spot is None:
        return False
    if iid == "breakdown":
        walk.things.append(Thing(id=uid(walk), kind="fault", deck=room.deck,
                                 x=spot[0], y=spot[1], room=room.id,
                                 name="the failing works"))
    elif iid == "strike":
        for _n in range(2 + rng.int(0, 1)):
            here = free_spot(walk, room.deck, room, rng)
            if here is not None:
                hand = folk(walk, rng, "worker", room.deck, *here,
                            room=room.id, mood="wary")
                hand.incident = "strike"
    else:
        folk(walk, rng, "saboteur", room.deck, *spot, room=room.id,
             faction="").incident = "sabotage"
    walk.goals.append([iid, GOALS[iid], False])
    return True


def topic(game, walk, other, tid: str, label: str, done: bool, odds):
    from .afoot_talk import Topic
    if tid == "bonus":
        cost = table.STRIKE_BONUS
        return Topic(tid, f"{label} — {cost:,} cr", not done
                     and game.credits >= cost, "You cannot cover it.", None,
                     cost)
    return Topic(tid, label, not done, "Asked already.", odds)


def resolved(game, walk, iid: str) -> None:
    """Set right by hand: the goal done, and the works running sweeter."""
    for goal in walk.goals:
        if goal[0] == iid and not goal[2]:
            goal[2] = True
            _mark(game, walk, table.WORKS_BOOST)
            say(walk, "The works will run the better for it.", "good")
    for who in walk.actors:
        if who.incident == iid:
            who.incident = ""


def on_hear(game, walk, who, other, offered, rng):
    from .afoot_talk import shift, terms
    got = terms(game, walk, who, other, "hear")
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a strike", what="leadership")
    if roll.ok:
        for hand in walk.actors:
            if hand.incident == "strike":
                shift(hand, 1)
        resolved(game, walk, "strike")
        text = f"{who.name} hears them out, and they go back to it."
    else:
        text = f"{who.name} hears them out, and it does not help."
    say(walk, text, "good" if roll.ok else "warn")
    return {"text": text, "check": roll, "line": ""}


def on_bonus(game, walk, who, other, offered, rng):
    game.credits = max(0.0, float(game.credits) - offered.cost)
    resolved(game, walk, "strike")
    return {"line": "That'll do. Back to it, all of you.",
            "paid": offered.cost}


def on_confront(game, walk, who, other, offered, rng):
    from .afoot_talk import terms
    got = terms(game, walk, who, other, "confront")
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a stranger", what="streetwise")
    if roll.ok:
        other.mood = "surrendered"
        resolved(game, walk, "sabotage")
        text = (f"{other.name} gives it up: paid to foul the line, and "
                "glad to be caught before anybody got hurt.")
    else:
        other.mood, other.aware = "hostile", True
        walk.mode = "action"
        text = f"{other.name} goes for a gun."
    say(walk, text, "good" if roll.ok else "bad")
    return {"text": text, "check": roll, "line": ""}


def left(game, walk) -> None:
    """Walking away: a saboteur put down or run off counts as dealt with;
    any other trouble left standing runs the works worse for a month."""
    for goal in walk.goals:
        if goal[0] == "sabotage" and not goal[2] and not any(
                a.incident == "sabotage" and a.standing
                and a.mood not in ("surrendered", "fled")
                for a in walk.actors):
            resolved(game, walk, "sabotage")
    if any(goal[0] in GOALS and not goal[2] for goal in walk.goals):
        _mark(game, walk, table.WORKS_SLUMP)
