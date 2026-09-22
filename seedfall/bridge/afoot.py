"""A walk on a deck, driven over the bridge the way the Afoot screen drives one.

The same doors as the screen (`sim/afoot`), the same refusals, and a `look`
that says what the screen shows: where the party is, what the one in hand
can do with its odds, who is in sight with a shot and a word, and the deck
around them as a few lines of text a script can read.

**While a party is out, nothing else acts** (`protocol.dispatch` asks
`blocking`): the window will not let a hull jump away from its own boarding
party, and neither will a pipe.
"""

from __future__ import annotations

from ..sim import afoot as afoot_sim
from ..sim import afoot_acts, afoot_fight, afoot_map
from ..sim.afoot_state import party
from . import checks
from .protocol import plain, verb

#: The verbs a walk in progress still answers.
AFOOT_VERBS = ("afoot_sites", "afoot_begin", "afoot_look", "afoot_move",
               "afoot_attack", "afoot_act", "afoot_talk", "afoot_end_turn",
               "afoot_surrender")

#: Squares either side of the one in hand the text map shows.
AROUND = 8


def blocking(game) -> bool:
    return afoot_sim.current(game) is not None


def _walk(game):
    walk = afoot_sim.current(game)
    if walk is None:
        raise checks.Refused("Nobody is out on a deck.")
    return walk


def _actor(walk, actor_id) -> object:
    got = next((a for a in walk.actors if a.id == checks.whole(
        actor_id, "actor", 0, 10 ** 6)), None)
    if got is None:
        raise checks.Refused("Nobody with that id on this walk.")
    return got


@verb("afoot_sites", "Everywhere the party could walk from here, and who "
      "could go.")
def sites(game) -> dict:
    return {"ok": True,
            "sites": [{"key": s.key, "kind": s.kind, "name": s.name,
                       "ok": s.ok, "why": s.why, "law": s.law}
                      for s in afoot_sim.sites(game)],
            "pool": [{"key": k, "name": n, "what": w, "ok": ok, "why": why}
                     for k, n, w, ok, why in afoot_sim.pool(game)]}


@verb("afoot_begin", "Go afoot: a site key, the party's keys joined by "
      "commas, and legal | all | none.", acts=True)
def begin(game, site: str, keys: str = "captain",
          arms: str = "legal") -> dict:
    who = [k.strip() for k in checks.words(keys, "keys", 200).split(",")
           if k.strip()]
    mode = checks.words(arms, "arms", 10)
    if mode not in ("legal", "all", "none"):
        raise checks.Refused("arms is legal, all or none.")
    got = afoot_sim.begin(game, checks.words(site, "site", 80), who, mode)
    got.pop("walk", None)
    return got


@verb("afoot_look", "The walk as the screen shows it: the party, what the "
      "one in hand can do, who is in sight, and the deck around them.")
def look(game) -> dict:
    walk = _walk(game)
    who = next((a for a in walk.actors if a.id == walk.selected), None)
    seen = afoot_sim.visible(walk, who.deck) if who else set()
    sight = []
    for other in walk.actors:
        if other.side != "npc" or (other.x, other.y) not in seen or \
                other.deck != who.deck or other.status == "gone":
            continue
        shot = afoot_fight.terms(game, walk, who, other)
        sight.append({"id": other.id, "name": other.name, "mood": other.mood,
                      "status": other.status, "at": [other.x, other.y],
                      "shot": round(shot["odds"], 3) if shot["ok"] else None,
                      "topics": [t.id for t in afoot_sim.talk_options(
                          game, who.id, other.id) if t.ok]})
    return plain({
        "ok": True, "site": walk.site, "round": walk.round,
        "mode": walk.mode, "selected": walk.selected,
        "party": [{"id": a.id, "name": a.name, "status": a.status,
                   "hp": a.hp, "hp_max": a.hp_max, "mp": a.mp,
                   "deck": a.deck, "at": [a.x, a.y], "weapon": a.weapon}
                  for a in party(walk)],
        "acts": [{"id": a.id, "label": a.label, "ok": a.ok, "why": a.why,
                  "odds": a.odds, "target": a.target}
                 for a in afoot_acts.offer(game, walk, who)] if who else [],
        "sight": sight, "map": _text_map(walk, who),
        "log": [line[1] for line in walk.log[-8:]]})


def _text_map(walk, who) -> list:
    """The deck round the one in hand, one character a square."""
    if who is None:
        return []
    deck = walk.decks[who.deck]
    g = afoot_map.ground(walk, who.deck)
    rows = []
    for y in range(max(0, who.y - AROUND), min(deck.h, who.y + AROUND + 1)):
        row = []
        for x in range(max(0, who.x - AROUND), min(deck.w, who.x + AROUND + 1)):
            cell = deck.at(x, y) if deck.was_seen(x, y) else "?"
            if (x, y) in g.shut or (x, y) in g.locked:
                cell = "+"
            row.append(cell)
        rows.append(row)
    for a in walk.actors:
        if a.deck == who.deck and a.status != "gone":
            ry, rx = a.y - max(0, who.y - AROUND), a.x - max(0, who.x - AROUND)
            if 0 <= ry < len(rows) and 0 <= rx < len(rows[ry]):
                rows[ry][rx] = "@" if a.id == who.id else (
                    "p" if a.side == "party" else "h" if a.hostile else "n")
    return ["".join(r) for r in rows]


@verb("afoot_move", "Walk one of the party to a square: actor, x, y.",
      acts=True)
def move(game, actor: int, x: int, y: int) -> dict:
    walk = _walk(game)
    who = _actor(walk, actor)
    deck = walk.decks[who.deck]
    return afoot_sim.move(game, who.id, checks.whole(x, "x", 0, deck.w - 1),
                          checks.whole(y, "y", 0, deck.h - 1))


@verb("afoot_attack", "Take a shot: actor, target.", acts=True)
def attack(game, actor: int, target: int) -> dict:
    walk = _walk(game)
    got = afoot_sim.attack(game, _actor(walk, actor).id,
                           _actor(walk, target).id)
    got.pop("check", None)
    return got


@verb("afoot_act", "Do one offered act: actor, act, target (from afoot_look).",
      acts=True)
def act(game, actor: int, act: str, target: int = -1) -> dict:
    walk = _walk(game)
    got = afoot_sim.act(game, _actor(walk, actor).id,
                        checks.words(act, "act", 20),
                        checks.whole(target, "target", -1, 10 ** 6))
    got.pop("check", None)
    return got


@verb("afoot_talk", "Raise a topic with somebody: actor, npc, topic.",
      acts=True)
def talk(game, actor: int, npc: int, topic: str = "greet") -> dict:
    walk = _walk(game)
    got = afoot_sim.talk(game, _actor(walk, actor).id, _actor(walk, npc).id,
                         checks.words(topic, "topic", 20))
    got.pop("check", None)
    return got


@verb("afoot_end_turn", "End the party's turn: everybody else acts.",
      acts=True)
def end_turn(game) -> dict:
    _walk(game)
    return afoot_sim.end_turn(game)


@verb("afoot_surrender", "Give yourselves up to the watch.", acts=True)
def surrender(game) -> dict:
    _walk(game)
    return afoot_sim.surrender(game)
