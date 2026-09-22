"""Incidents on a walk: deciding which happen, putting them on the deck, and settling them.

The table is `data/afoot_incidents.py`. `draw` runs once when a walk begins,
off the walk's own dice: an incident happens when its condition holds —
read off state the game already keeps — and its odds come up. `tick` runs
every round, for the incidents that come *to* you: a constable who has seen
a pistol walks up and asks to see the papers for it.

**A tie is a person.** `person.of(game, officer).ties` has dealt every officer
a parent, a creditor, an old shipmate since the muster book was written; a
tie met on a concourse is that same person, by name, and settling with them
moves the officer whose past they are.
"""

from __future__ import annotations

from ..data import afoot_incidents as table
from ..data import kit as kit_table
from . import afoot_map, afoot_people, loyalty
from .afoot_cast import folk, free_spot
from .afoot_state import party, say


def draw(game, walk, site, rng) -> list:
    """Which incidents this walk has, each put on the deck."""
    fired = []
    for incident in table.INCIDENTS:
        if site.kind not in incident.sites:
            continue
        if not _holds(game, walk, site, incident.id):
            continue
        if not rng.chance(incident.odds):
            continue
        if _spawn(game, walk, site, incident.id, rng):
            walk.incidents.append(incident.id)
            fired.append(incident.id)
    return fired


def _holds(game, walk, site, iid: str) -> bool:
    if iid == "stop":
        return site.law >= 3 and bool(_forbidden(walk))
    if iid == "tie":
        return any(_ties(game, a) for a in party(walk) if a.officer >= 0)
    if iid == "hunter":
        from . import warrants
        return warrants.bounty(game, game.system) > 0
    if iid == "stowaway":
        return bool(getattr(game.system, "port", None)) and not _met(
            game, f"stowaway:{site.key}")
    if iid == "fault":
        from .ship import hull_pct
        return hull_pct(game.ship) < 0.95
    return False


def _forbidden(walk) -> list:
    """What the party is carrying openly that this law level forbids."""
    out = []
    for mate in party(walk):
        for kid in (mate.weapon, mate.armour):
            item = kit_table.ITEM_BY_ID.get(kid)
            if item is not None and not kit_table.legal_at(item, walk.law):
                out.append(item)
    return out


def _ties(game, who) -> list:
    """The people from an officer's past who might turn up — less anybody
    already met this season, settled or walked past."""
    from . import person
    officer = afoot_people.officer_of(game, who.officer)
    if officer is None:
        return []
    return [t for t in person.of(game, officer).ties
            if not _met(game, f"tie:{officer.id}:{t.kind}")]


def _met(game, key: str) -> bool:
    """Has this already happened this season?"""
    from .afoot_cast import RESTOCK
    when = (game.walked.get("met") or {}).get(key)
    return when is not None and int(game.day) - int(when) < RESTOCK


def meet(game, key: str) -> None:
    """Remember that this happened today, so it does not happen again
    tomorrow for the asking."""
    game.walked.setdefault("met", {})[key] = int(game.day)


def _far_room(walk, rng):
    rooms = sorted(walk.rooms, key=lambda r: -(r.deck * 100 + r.x))
    return rooms[0] if rooms else None


def _spawn(game, walk, site, iid: str, rng) -> bool:
    entry = next((t for t in walk.things if t.kind in ("airlock", "gangway")),
                 None)
    if iid == "stop":
        spot = free_spot(walk, 0, None, rng, near=(entry.x + 6, entry.y)
                     if entry else None)
        if spot is None:
            return False
        cop = folk(walk, rng, "constable", 0, *spot, faction=site.faction)
        cop.incident, cop.mood = "stop", "wary"
        return True
    if iid == "tie":
        mates = [a for a in party(walk) if a.officer >= 0 and _ties(game, a)]
        mate = rng.pick(mates)
        tie = rng.pick(_ties(game, mate))
        room = rng.pick(walk.rooms)
        spot = free_spot(walk, room.deck, room, rng)
        if spot is None:
            return False
        who = folk(walk, rng, "patron", room.deck, *spot, room=room.id,
                   faction=site.faction, name=tie.who)
        who.tie = f"{mate.officer}:{tie.kind}"
        who.incident = "tie"
        who.mood = "friendly" if tie.helps else "wary"
        who.note = tie.line
        walk.goals.append(["tie", f"See {who.name} — {mate.name} knows them",
                           False])
        return True
    if iid == "hunter":
        room = _far_room(walk, rng)
        spot = free_spot(walk, room.deck, room, rng) if room else None
        if spot is None:
            return False
        hunter = folk(walk, rng, "bravo", room.deck, *spot, room=room.id)
        hunter.incident = "hunter"
        return True
    if iid == "stowaway":
        hold = next((r for r in walk.rooms if r.kind == "hold"), None)
        spot = free_spot(walk, hold.deck, hold, rng) if hold else None
        if spot is None:
            return False
        folk(walk, rng, "stowaway", hold.deck, *spot,
             room=hold.id).incident = "stowaway"
        meet(game, f"stowaway:{site.key}")
        return True
    if iid == "fault":
        from .afoot_state import Thing, uid
        room = next((r for r in walk.rooms if r.kind in (
            "engineering", "drive", "power")), None)
        spot = free_spot(walk, room.deck, room, rng) if room else None
        if spot is None:
            return False
        walk.things.append(Thing(id=uid(walk), kind="fault", deck=room.deck,
                                 x=spot[0], y=spot[1], room=room.id,
                                 name="the failing junction"))
        walk.goals.append(["fault", "Find the fault and fix it", False])
        return True
    return False


def tick(game, walk) -> list:
    """Incidents that come to you: the stop, when the constable arrives."""
    events = []
    for npc in walk.actors:
        if npc.incident != "stop" or not npc.standing or \
                npc.mood in ("hostile", "fled", "friendly"):
            continue
        if "hailed" in npc.talked:
            events += _waiting(walk, npc)
            continue
        near = [a for a in party(walk, standing=True) if a.deck == npc.deck
                and afoot_map.distance(a.x, a.y, npc.x, npc.y) <= 2]
        if near:
            npc.talked.append("hailed")
            say(walk, f"{npc.name}: “Papers. All of you. What's that you're "
                      "carrying?”", "warn")
            events.append({"kind": "hail", "who": npc.id, "to": near[0].id})
        else:
            target = min(party(walk, standing=True) or [npc],
                         key=lambda a: afoot_map.distance(a.x, a.y,
                                                          npc.x, npc.y))
            if target is not npc and target.deck == npc.deck:
                npc.post = [target.deck, target.x, target.y]
    return events


#: Rounds a constable who has asked for papers waits before an answer that
#: does not come is an answer.
STOP_PATIENCE = 2


def _waiting(walk, npc) -> list:
    """A stop that was asked and not answered. Show papers, pay, or talk
    them round — or walk on, and it is evasion, and they come after you."""
    if "papers" in npc.talked or "bribe" in npc.talked:
        return []
    npc.talked.append("waited")
    if npc.talked.count("waited") <= STOP_PATIENCE:
        return []
    npc.mood, npc.aware = "hostile", True
    walk.mode = "action"
    walk.seen_doing.append(["evasion", walk.faction, 0.6, [npc.id]])
    say(walk, f"{npc.name}: “Right. Stop there. You're coming with me.”",
        "bad")
    return [{"kind": "stop_ignored", "who": npc.id}]


# ── settling with somebody from before ─────────────────────────────────────

def tie_terms(game, walk, who, other) -> dict:
    """What settling with a tie will cost, and what it will do."""
    oid, kind = other.tie.split(":", 1)
    officer = afoot_people.officer_of(game, int(oid))
    from ..data.backgrounds import TIE_BY_ID
    tie = TIE_BY_ID.get(kind)
    debt = 0
    if kind == "creditor":
        from ..core.rng import RNG
        debt = RNG(f"{game.seed}:debt:{other.tie}").int(table.DEBT_LEAST,
                                                         table.DEBT_MOST)
    return {"officer": officer, "tie": tie, "debt": debt, "kind": kind}


def settle(game, walk, who, other) -> dict:
    """Make it right with them — pay what is owed, or simply stop and talk."""
    got = tie_terms(game, walk, who, other)
    officer = got["officer"]
    if officer is None:
        return {"line": "They have nobody here to see."}
    if got["debt"]:
        if game.credits < got["debt"]:
            return {"ok": False, "why": "You cannot cover it."}
        game.credits = max(0.0, float(game.credits) - got["debt"])
    loyalty.shift(officer, table.TIE_LOYALTY)
    meet(game, f"tie:{other.tie}")
    for goal in walk.goals:
        if goal[0] == "tie":
            goal[2] = True
    other.mood = "friendly"
    text = (f"{officer.name} and {other.name} settle it"
            + (f" — {got['debt']:,} cr, paid." if got["debt"] else ".")
            + f" {officer.name} will remember you stood by.")
    say(walk, text, "good")
    return {"line": "", "text": text, "paid": got["debt"]}


def snubbed(game, walk) -> None:
    """Leaving without seeing somebody who came to find one of yours."""
    for npc in walk.actors:
        if npc.incident != "tie" or "tie" in npc.talked:
            continue
        officer = afoot_people.officer_of(game, int(npc.tie.split(":")[0]))
        meet(game, f"tie:{npc.tie}")
        if officer is not None:
            loyalty.shift(officer, table.TIE_SNUB)
            game.add_log(f"{officer.name} saw {npc.name} on the concourse, and "
                         "you walked on by.", "warn")
