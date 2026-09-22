"""What each topic does once it is raised — one function per topic.

`sim/afoot_talk.topics` offers and `say_to` dispatches here. Each function
takes `(game, walk, who, other, offered, rng)`, where `offered` is the topic
exactly as it was shown (with its price), and returns what the screen reads:
a `line` in the speaker's voice, and whatever else happened.

The throws are `afoot_talk.terms` — the arguments the odds on the button were
worked out from — handed to `checks.roll`.
"""

from __future__ import annotations

from . import (afoot_holdings, afoot_kith, afoot_people, afoot_talk,
               afoot_trouble, checks, establishments, loyalty)
from .afoot_state import party, say


def _roll(game, walk, who, other, tid: str, rng, what: str):
    got = afoot_talk.terms(game, walk, who, other, tid)
    return checks.roll(rng, got["skill"], got["score"], got["how"],
                       got["extra"], about=tid, what=what)


def _pay(game, amount: int) -> None:
    """Money leaving the purse for somebody on a deck. It goes; it never
    arrives from anywhere."""
    game.credits = max(0.0, float(game.credits) - float(amount))


def on_greet(game, walk, who, other, offered, rng):
    room = next((r for r in walk.rooms if r.id == other.room), None)
    if room is not None:
        room.known = True
    return {"line": afoot_talk.line(game, walk, other)}


def on_place(game, walk, who, other, offered, rng):
    named = []
    for room in walk.rooms:
        if room.deck == other.deck and not room.known:
            room.known = True
            named.append(room.name)
    if named:
        text = "They point you at " + ", ".join(named[:4]) + (
            " and the rest." if len(named) > 4 else ".")
    else:
        text = "Nothing you have not already found."
    say(walk, text, "")
    return {"line": afoot_talk.line(game, walk, other), "text": text}


def on_word(game, walk, who, other, offered, rng):
    if other.folk == "officer":
        return _a_word(game, walk, other)
    if offered.cost:
        _pay(game, offered.cost)
        rumour = _rumour(game)
        return {"line": afoot_talk.line(game, walk, other, "warm"),
                "text": rumour or _gossip(game, rng)}
    roll = _roll(game, walk, who, other, "word", rng, "streetwise")
    if roll.ok:
        rumour = _rumour(game)
        if rumour:
            return {"line": afoot_talk.line(game, walk, other), "text": rumour,
                    "check": roll}
    return {"line": afoot_talk.line(game, walk, other),
            "text": _gossip(game, rng), "check": roll}


def _rumour(game) -> str:
    """A real lead off the quay's board, taken up (`sim/rumours`)."""
    from . import rumours
    system = game.system
    if not getattr(system, "port", None):
        return ""
    board = rumours.board(game, system)
    if not board:
        return ""
    story = board[0]
    rumours.take(game, story, paid=False)
    target = game.galaxy.systems[story.system_id]
    return f"Word is: {story.definition.name.lower()} at {target.name}."


def _gossip(game, rng) -> str:
    rows = [s for s in game.galaxy.systems if s.port and
            s.id != game.location_id]
    if not rows:
        return "Nobody here knows anything you do not."
    houses = [f for s in rows[:16] for f in establishments.here(game, s)]
    if houses and rng.chance(0.4):
        return rng.pick(houses_gossip(rng.pick(houses)))
    other = rng.pick(rows[:16])
    return rng.pick((
        f"They say the quay at {other.name} is short of hands.",
        f"Somebody came in from {other.name} last week looking hunted.",
        f"Prices at {other.name} have gone strange, apparently.",
        f"Nobody has had a straight answer out of {other.name} all season."))


def houses_gossip(found) -> tuple:
    """What the concourse says about one of the trade's houses."""
    name = found.name
    return {"gaming_wheel": (f"Somebody broke the high table at {name} "
                             "last week. They were not seen again.",),
            "grand_hotel": (f"Three powers had rooms at {name} on the same "
                            "night. Nobody will say why.",),
            "shipyard": (f"{name} is laying down hulls faster than it can "
                         "find hands for them.",),
            "pleasure_palace": (f"Half the officers in the Verge owe {name} "
                                "money, the way I hear it.",),
            "smugglers_den": (f"If it went missing, ask at {name}.",),
            }.get(found.kind.id, (f"They say {name} is doing well for "
                                  "itself.",))


def _a_word(game, walk, other):
    officer = afoot_people.officer_of(game, other.officer)
    if officer is None:
        return {"line": ""}
    loyalty.shift(officer, afoot_talk.WORD_LOYALTY)
    words = game.walked.setdefault("words", {})
    words[str(officer.id)] = int(game.day)
    say(walk, f"A word with {officer.name}. It is noticed.", "good")
    return {"line": afoot_talk.line(game, walk, other, "warm"),
            "loyalty": afoot_talk.WORD_LOYALTY}


def on_persuade(game, walk, who, other, offered, rng):
    roll = _roll(game, walk, who, other, "persuade", rng, "persuade")
    if roll.ok:
        afoot_talk.shift(other, 2 if roll.exceptional else 1)
    elif roll.disaster:
        afoot_talk.shift(other, -1)
    say(walk, f"{who.name} talks to {other.name}: "
              f"{'it lands' if roll.ok else 'it does not'} — "
              f"{other.mood} now.", "good" if roll.ok else "")
    return {"line": afoot_talk.line(game, walk, other), "check": roll}


def on_bribe(game, walk, who, other, offered, rng):
    _pay(game, offered.cost)
    roll = _roll(game, walk, who, other, "bribe", rng, "streetwise")
    if roll.ok:
        other.mood = "friendly"
        other.aware = False
        # A constable paid off forgets what *they* saw. Anything somebody
        # else saw as well is still a crime.
        if other.folk in ("constable", "customs"):
            forget(walk, other.id)
        say(walk, f"{other.name} pockets it and finds something else to "
                  "look at.", "good")
    else:
        afoot_talk.shift(other, -1)
        say(walk, f"{other.name} takes the money and does nothing for it.",
            "warn")
    return {"line": afoot_talk.line(game, walk, other), "check": roll,
            "paid": offered.cost}


def forget(walk, witness: int) -> None:
    """One witness is no longer one: what only they saw is off the file."""
    kept = []
    for row in walk.seen_doing:
        saw = [w for w in (row[3] if len(row) > 3 else []) if w != witness]
        if saw or len(row) <= 3:
            kept.append(row[:3] + [saw] if len(row) > 3 else row)
    walk.seen_doing[:] = kept


def on_papers(game, walk, who, other, offered, rng):
    roll = _roll(game, walk, who, other, "papers", rng, "admin")
    if roll.ok:
        afoot_talk.shift(other, 1)
        say(walk, f"{other.name} waves the papers through.", "good")
        return {"line": afoot_talk.line(game, walk, other), "check": roll}
    seized = seize(game, walk)
    if seized:
        walk.seen_doing.append(["contraband", walk.faction, 0.6,
                                [other.id]])
        say(walk, "They go through everybody. They take "
                  + ", ".join(seized) + ".", "bad")
    else:
        say(walk, "They go through everybody and find nothing to take.", "")
    return {"line": afoot_talk.line(game, walk, other, "cold"),
            "check": roll, "seized": seized}


def seize(game, walk) -> list:
    """What a stop takes off the party: whatever this law level forbids."""
    from ..data import kit as kit_table
    taken = []
    for mate in party(walk):
        for kid in list(mate.kit):
            item = kit_table.ITEM_BY_ID.get(kid)
            if item is None or kit_table.legal_at(item, walk.law):
                continue
            mate.kit.remove(kid)
            if mate.weapon == kid:
                mate.weapon = ""
            if mate.armour == kid:
                mate.armour = ""
            if mate.folk == "captain":
                walk.found.setdefault("seized", []).append(kid)
            taken.append(item.name)
    return taken


def on_patch(game, walk, who, other, offered, rng):
    _pay(game, offered.cost)
    for mate in afoot_talk.patchable(walk):
        mate.hp = mate.hp_max
        if mate.status in ("down", "stable"):
            mate.status = "up"
    say(walk, f"{other.name} sees to everybody. {offered.cost:,} cr.",
        "good")
    return {"line": afoot_talk.line(game, walk, other), "paid": offered.cost}


def on_question(game, walk, who, other, offered, rng):
    from . import afoot_deeds
    for deck in range(len(walk.decks)):
        afoot_deeds.reveal(walk, deck)
    text = "They tell you the way round her, deck by deck."
    if other.note == "master":
        for box in walk.things:
            if box.kind == "strongbox" and box.state == "locked":
                box.state = "shut"
        text += " The master gives up the strongbox code."
        from ..data.factions import FACTIONS_BY_ID
        power = FACTIONS_BY_ID.get(walk.prize_faction)
        if power is not None:
            walk.found.setdefault("intel", []).append(
                f"{other.name} sailed for {power.name}.")
    say(walk, text, "good")
    return {"line": afoot_talk.line(game, walk, other), "text": text}


def on_enlist(game, walk, who, other, offered, rng):
    roll = _roll(game, walk, who, other, "enlist", rng, "leadership")
    if not roll.ok:
        say(walk, f"{other.name} will not sign.", "")
        return {"line": afoot_talk.line(game, walk, other, "cold"),
                "check": roll}
    other.status = "gone"
    other.note = "enlisted"
    hands = walk.found.setdefault("hands", {})
    hands["signed"] = hands.get("signed", 0) + 1
    say(walk, f"{other.name} signs on as a hand.", "good")
    return {"line": afoot_talk.line(game, walk, other, "warm"),
            "check": roll}


def on_report(game, walk, who, other, offered, rng):
    officer = afoot_people.officer_of(game, other.officer)
    text = report_line(game, officer) if officer else "All quiet."
    return {"line": afoot_talk.line(game, walk, other), "text": text}


def report_line(game, officer) -> str:
    """What an officer says about their own part of the ship."""
    from .ship import hull_pct
    role = getattr(officer, "role", "")
    if role == "engineer":
        return (f"Hull is at {hull_pct(game.ship):.0%}. "
                f"{'She holds air.' if not game.ship.disabled else 'Things are down: ' + ', '.join(game.ship.disabled) + '.'}")
    if role == "science":
        from ..data.tech import TECH_BY_ID
        current = getattr(game.research, "current", None)
        tech = TECH_BY_ID.get(current) if current else None
        if tech is None:
            return "The bench is idle. Give me something to work on."
        return f"The bench is on {tech.name.lower()}."
    if role == "medic":
        hurt = len([k for k, v in (game.wounds or {}).items() if v > 0])
        return (f"{hurt} of us still mending." if hurt
                else "Everybody is well enough.")
    if role == "nav":
        return f"We can jump {game.ship_stats.jump:.1f} light years."
    if role == "comms":
        unread = sum(1 for s in game.signals if not getattr(s, "read", True))
        return f"{unread} despatches nobody has read."
    return f"{len(game.ship_stats.weapons)} mounts, all answering."


def on_story(game, walk, who, other, offered, rng):
    """An officer tells you a berth they had before yours, in their own
    words — and if their story has somewhere to go, says so."""
    from . import arcs, person
    officer = afoot_people.officer_of(game, other.officer)
    if officer is None:
        return {"line": afoot_talk.line(game, walk, other)}
    berths = list(person.of(game, officer).berths)
    told = arcs.status(game, officer)
    if berths:
        berth = berths[other.spoke % len(berths)]
        other.spoke += 1
        years = f"{berth.years} year{'s' if berth.years != 1 else ''}"
        line = (f"{years.capitalize()} on the {berth.ship}, {berth.kind}. "
                f"I {berth.ended}.")
    else:
        line = "Nothing worth the telling, Captain. Not yet."
    text = (f"There is more to it: {other.name} {told['hint']}."
            if told.get("hint") else "")
    return {"line": line, "text": text}


def on_join(game, walk, who, other, offered, rng):
    from . import afoot
    afoot.join(game, walk, other)
    say(walk, f"{other.name} comes along.", "good")
    return {"line": afoot_talk.line(game, walk, other, "warm")}


def on_tie(game, walk, who, other, offered, rng):
    from . import afoot_incidents
    return afoot_incidents.settle(game, walk, who, other)


#: Every topic that is answered here, by id. One door each.
SAID = {
    "greet": on_greet,
    "place": on_place,
    "word": on_word,
    "persuade": on_persuade,
    "bribe": on_bribe,
    "papers": on_papers,
    "patch": on_patch,
    "question": on_question,
    "enlist": on_enlist,
    "sing": afoot_kith.on_sing,
    "answer": afoot_kith.on_answer,
    "passage": afoot_kith.on_passage,
    "settle": afoot_trouble.on_settle,
    "pay": afoot_trouble.on_pay,
    "round": afoot_trouble.on_round,
    "hear": afoot_holdings.on_hear,
    "bonus": afoot_holdings.on_bonus,
    "confront": afoot_holdings.on_confront,
    "report": on_report,
    "story": on_story,
    "join": on_join,
    "tie": on_tie,
}
