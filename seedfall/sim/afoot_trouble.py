"""Trouble on a walk: a quarrel aboard, a shakedown, a brawl.

Three incidents (`data/afoot_incidents.py`), each with a reason the game
already keeps, a way to meet it head on and a way to let it be:

- **quarrel** — two officers at their stations whose convictions collide
  (`data/convictions`: the same act moves them opposite ways) are at it in
  one compartment. Knock their heads together — Leadership and SOC — and
  both think better of you; bungle it and both think worse; walk past and
  both remember that too;
- **shakedown** — the law is thin (`THIN_LAW`), and hard cases want a toll
  for walking through. Pay it, talk them round or buy them off, or after
  two rounds of standing there they come for it;
- **brawl** — the law is thin, there is a bar, and somebody in it squares up
  to whoever comes near. Talk them down or stand them a drink; hit back and
  it is no crime — they swung first.

`afoot_incidents` draws and ticks these alongside its own; the topics are
answered here (`afoot_said.SAID`).
"""

from __future__ import annotations

from ..data import afoot_incidents as table
from ..data.convictions import CONVICTIONS_BY_ID
from . import afoot_map, afoot_people, checks, loyalty
from .afoot_state import party, say

#: Rooms a brawl starts in.
BARS = ("eatery", "entertainment", "lounge", "vice", "gaming")
#: Rounds hard cases wait, having named their toll, before they take it.
PATIENCE = 2


def clash(a: str, b: str) -> str:
    """The act two convictions would disagree over, or ""."""
    ca, cb = CONVICTIONS_BY_ID.get(a), CONVICTIONS_BY_ID.get(b)
    if ca is None or cb is None:
        return ""
    return next((e for e, v in ca.reacts.items()
                 if v * cb.reacts.get(e, 0) < 0), "")


def _pair(game, walk):
    """Two officers at their stations who would quarrel, or None."""
    here = [a for a in walk.actors if a.side == "npc" and a.officer >= 0
            and a.standing and not a.incident]
    for n, a in enumerate(here):
        oa = afoot_people.officer_of(game, a.officer)
        for b in here[n + 1:]:
            ob = afoot_people.officer_of(game, b.officer)
            if oa and ob and clash(oa.conviction, ob.conviction):
                return a, b
    return None


def holds(game, walk, site, iid: str) -> bool:
    if iid == "quarrel":
        return _pair(game, walk) is not None
    if iid == "shakedown":
        return site.law <= table.THIN_LAW and not site.mine
    if iid == "brawl":
        return site.law <= table.BRAWL_LAW and not site.mine and any(
            r.kind in BARS for r in walk.rooms)
    return False


def spawn(game, walk, site, iid: str, rng) -> bool:
    from .afoot_cast import folk, free_spot
    if iid == "quarrel":
        a, b = _pair(game, walk)
        room = next((r for r in walk.rooms if r.id == a.room), None)
        spot = free_spot(walk, a.deck, room, rng, near=(a.x, a.y))
        if spot is not None:
            b.deck, (b.x, b.y) = a.deck, spot
        for one, other in ((a, b), (b, a)):
            one.incident, one.note = "quarrel", f"quarrel:{other.id}"
        walk.goals.append(["quarrel", f"Settle it between {a.name} and "
                                      f"{b.name}", False])
        return True
    if iid == "shakedown":
        entry = next((t for t in walk.things
                      if t.kind in ("airlock", "gangway")), None)
        near = (entry.x + 5, entry.y) if entry else None
        deck = entry.deck if entry else 0
        for _n in range(1 + rng.int(0, 1)):
            spot = free_spot(walk, deck, None, rng, near=near)
            if spot is None:
                return False
            hard = folk(walk, rng, "thug", deck, *spot, faction="")
            hard.incident, hard.mood = "shakedown", "wary"
        return True
    if iid == "brawl":
        room = rng.pick([r for r in walk.rooms if r.kind in BARS])
        spot = free_spot(walk, room.deck, room, rng)
        if spot is None:
            return False
        drunk = folk(walk, rng, "thug", room.deck, *spot, room=room.id,
                     faction="")
        drunk.incident, drunk.mood, drunk.weapon = "brawl", "wary", ""
        return True
    return False


def toll(walk) -> int:
    return table.TOLL_PER_LEVEL * max(1, 4 - walk.law)


def tick(game, walk) -> list:
    """Shakedowns name their price and wait; a brawler swings at whoever
    comes within reach."""
    events = []
    for npc in walk.actors:
        if not npc.standing or npc.mood in ("hostile", "fled", "friendly"):
            continue
        near = [a for a in party(walk, standing=True) if a.deck == npc.deck
                and afoot_map.apart(walk, a, npc) <= 2]
        if npc.incident == "brawl" and any(afoot_map.apart(walk, a, npc) <= 1 for a in near):
            npc.mood, npc.aware = "hostile", True
            walk.mode = "action"
            say(walk, f"{npc.name} squares up to {near[0].name} and swings.",
                "bad")
            events.append({"kind": "brawl", "who": npc.id})
        elif npc.incident == "shakedown":
            events += _shakedown(walk, npc, near)
    return events


def _shakedown(walk, npc, near) -> list:
    if "hailed" not in npc.talked:
        if near:
            npc.talked.append("hailed")
            say(walk, f"{npc.name}: “Toll for walking through here. "
                      f"{toll(walk):,} cr, and nobody gets hurt.”", "warn")
            return [{"kind": "hail", "who": npc.id}]
        return []
    if npc.mood == "neutral":
        npc.incident = ""                    # talked round
        return []
    npc.talked.append("waited")
    if npc.talked.count("waited") <= PATIENCE:
        return []
    for other in walk.actors:
        if other.incident == "shakedown" and other.standing:
            other.mood, other.aware = "hostile", True
    walk.mode = "action"
    say(walk, f"{npc.name}: “Right. We'll take it, then.”", "bad")
    return [{"kind": "shakedown", "who": npc.id}]


def topic(game, walk, other, tid: str, label: str, done: bool, odds):
    """How one of the incidents' own topics is offered."""
    from .afoot_talk import Topic
    if tid == "settle":
        return Topic(tid, label, not done, "You have had your say.", odds)
    if tid == "pay":
        cost = toll(walk)
        hailed = "hailed" in other.talked
        return Topic(tid, f"{label} — {cost:,} cr", hailed and not done
                     and game.credits >= cost,
                     "They have not named a price." if not hailed else
                     "You cannot cover it.", None, cost)
    cost = table.ROUND_COST
    return Topic(tid, f"{label} — {cost} cr", not done
                 and game.credits >= cost, "You cannot cover it.", None, cost)


def on_settle(game, walk, who, other, offered, rng):
    """Knock two officers' heads together."""
    from .afoot_state import actor
    from .afoot_talk import terms
    partner = actor(walk, int(other.note.split(":")[1]))
    got = terms(game, walk, who, other, "settle")
    roll = checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about="a quarrel", what="leadership")
    shift = table.QUARREL_SETTLED if roll.ok else table.QUARREL_BUNGLED
    for one in (other, partner):
        if one is None:
            continue
        officer = afoot_people.officer_of(game, one.officer)
        if officer is not None:
            loyalty.shift(officer, shift)
        one.incident, one.note = "", ""
        if "settle" not in one.talked:
            one.talked.append("settle")
    for goal in walk.goals:
        if goal[0] == "quarrel":
            goal[2] = True
    text = (f"{who.name} knocks their heads together, and it takes." if
            roll.ok else f"{who.name} steps in, and makes it worse.")
    say(walk, text, "good" if roll.ok else "warn")
    return {"text": text, "check": roll, "line": ""}


def on_pay(game, walk, who, other, offered, rng):
    """Pay the toll: they have what they wanted, and they go."""
    game.credits = max(0.0, float(game.credits) - offered.cost)
    for hard in walk.actors:
        if hard.incident == "shakedown":
            hard.incident, hard.mood = "", "friendly"
    say(walk, f"{other.name} counts it and steps aside. "
              f"{offered.cost:,} cr.", "")
    return {"line": "Pleasure doing business.", "paid": offered.cost}


def on_round(game, walk, who, other, offered, rng):
    """Stand a drink: nobody swings at a friend's round."""
    game.credits = max(0.0, float(game.credits) - offered.cost)
    other.incident, other.mood = "", "friendly"
    say(walk, f"{who.name} buys {other.name} a drink, and the moment "
              "passes.", "good")
    return {"line": "…Yeah. All right. Cheers.", "paid": offered.cost}


def left(game, walk) -> None:
    """A quarrel walked past is remembered by both of them."""
    for one in walk.actors:
        if one.incident != "quarrel":
            continue
        officer = afoot_people.officer_of(game, one.officer)
        if officer is not None:
            loyalty.shift(officer, table.QUARREL_LEFT)
