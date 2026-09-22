"""Talking to somebody on a deck: what can be said, what it costs, what it does.

The pattern is `sim/hail.py`'s, brought down to walking pace. `topics` lists
what can be raised with one person — each with whether it can be done, why
not, the odds where there is a throw, and the price where there is one — and
`say_to` does exactly that. **It owns as few rules as it can**: business is
the concourse's own counters (`sim/shore`, `sim/crew`), a harbourmaster's
favours are `sim/officials`, word going round is `sim/rumours`, a Kith gift is
`sim/kith_acts`, and an officer's story is the Despatches board. What is
decided here is only what talking itself does:

- **a disposition moves** one rung on `afoot_folk.MOODS` for a persuasion
  that lands, two for an exceptional one, and one the wrong way for a
  disaster;
- **a bribe is paid out of your purse**, and leaves it. Money is never made
  here; it only goes;
- **a word with one of your own officers** is worth a little loyalty, once a
  month each (`WORD_EVERY`);
- **a struck crewman or a stowaway can sign on** as a hand.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..core.rng import RNG
from ..data.afoot_folk import FOLK_BY_ID, MOODS, TOPICS
from . import afoot_map, afoot_people, checks
from .afoot_state import party, say

#: How close you must be to talk, in squares, and able to see them.
TALK_REACH = 3
#: A word with an officer: what it is worth, and how often it can be had.
WORD_LOYALTY = 2.0
WORD_EVERY = 30
#: What a bribe costs: this much a law level, and never less than the floor.
BRIBE_PER_LAW = 60
BRIBE_FLOOR = 40
#: What a clinician charges to patch a stamina point on the spot.
PATCH_PER_POINT = 25
#: What the word going round costs from an informant who sells it.
WORD_PRICE = 120


@dataclass(frozen=True)
class Topic:
    """One thing that can be raised with somebody."""

    id: str
    label: str
    ok: bool = True
    why: str = ""
    odds: object = None
    cost: int = 0
    #: A screen this hands over to, where it is somebody else's counter.
    goes_to: str = ""


def can_talk(walk, who, other) -> tuple:
    if not who.standing:
        return False, f"{who.name} is down."
    if other.side == "party" or other.status in ("dead", "gone"):
        return False, "There is nobody to talk to."
    if other.status in ("down", "stable"):
        return False, f"{other.name} is in no state to talk."
    if other.deck != who.deck or afoot_map.apart(walk, who, other) > TALK_REACH:
        return False, "Get closer first."
    if not afoot_map.sees(walk, who.deck, who.x, who.y, other.x, other.y):
        return False, "You cannot see them from here."
    return True, ""


def _persuade_terms(game, walk, who, other) -> dict:
    rec = afoot_people.record(game, who)
    skill = max(rec.skill("persuade"), rec.skill("leadership") - 1)
    how = "difficult" if other.mood == "hostile" else "average"
    return {"skill": skill, "score": rec.score("soc"), "how": how,
            "extra": 1 if "good_coat" in who.kit else 0}


def _bribe_terms(game, walk, who, other) -> dict:
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("streetwise"), "score": rec.score("soc"),
            "how": "routine", "extra": 0}


def _papers_terms(game, walk, who, other) -> dict:
    rec = afoot_people.record(game, who)
    extra = 0
    for kid, dm in (("writ", 2), ("passage_papers", 1)):
        if kid in who.kit:
            extra = max(extra, dm)
    skill = rec.skill("admin")
    if "false_papers" in who.kit:
        skill = max(skill, rec.skill("deception") + 2)
    return {"skill": skill, "score": rec.score("edu"),
            "how": "difficult" if walk.law >= 8 else "average",
            "extra": extra}


def _enlist_terms(game, walk, who, other) -> dict:
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("leadership"), "score": rec.score("soc"),
            "how": "routine" if other.mood == "surrendered" else "average",
            "extra": 0}


def _word_terms(game, walk, who, other) -> dict:
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("streetwise"), "score": rec.score("int"),
            "how": "average", "extra": 1 if other.mood == "friendly" else 0}


#: Topics that only mean something to somebody in a particular incident.
INCIDENT_TOPICS = {"settle": "quarrel", "pay": "shakedown", "round": "brawl",
                   "hear": "strike", "bonus": "strike",
                   "confront": "sabotage"}


def _settle_terms(game, walk, who, other) -> dict:
    """Knocking two officers' heads together: Leadership and SOC."""
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("leadership"), "score": rec.score("soc"),
            "how": "average", "extra": 0}


def _confront_terms(game, walk, who, other) -> dict:
    """Facing somebody down at your own works: Streetwise and INT."""
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("streetwise"), "score": rec.score("int"),
            "how": "average", "extra": 0}


def _answer_terms(game, walk, who, other) -> dict:
    """Singing a Kith phrase back: Art and INT, easier the more of that
    phrase's domain is already understood (`sim/afoot_kith`)."""
    from . import afoot_kith
    rec = afoot_people.record(game, who)
    return {"skill": rec.skill("art"), "score": rec.score("int"),
            "how": afoot_kith.difficulty(game, other), "extra": 0}


TERMS = {"persuade": _persuade_terms, "bribe": _bribe_terms,
         "papers": _papers_terms, "enlist": _enlist_terms,
         "word": _word_terms, "answer": _answer_terms,
         "settle": _settle_terms, "hear": _settle_terms,
         "confront": _confront_terms}


def _odds(t: dict) -> float:
    return checks.chance(t["skill"], t["score"], t["how"], t["extra"])


def bribe_cost(walk, other) -> int:
    return max(BRIBE_FLOOR, BRIBE_PER_LAW * walk.law
               + 10 * other.stats.get("soc", 5))


def topics(game, walk, who, other) -> list:
    """Everything that can be raised with this person, and at what odds."""
    ok, why = can_talk(walk, who, other)
    kind = FOLK_BY_ID.get(other.folk)
    names = list(getattr(kind, "topics", ()) or ())
    if not ok:
        return [Topic("greet", TOPICS["greet"], False, why)]
    if other.tie and "tie" not in names:
        names.append("tie")
    # A topic that belongs to an incident is only raised with the people in
    # it: nobody asks a quiet patron to call off a shakedown.
    names = [t for t in names if INCIDENT_TOPICS.get(t, other.incident)
             == other.incident]
    out = []
    for tid in names:
        got = _topic(game, walk, who, other, tid)
        out.append(got if not got.ok else replace(got, why=""))
    return out


def _topic(game, walk, who, other, tid: str) -> Topic:
    label = TOPICS[tid]
    done = tid in other.talked
    if tid in TERMS:
        terms = TERMS[tid](game, walk, who, other)
        odds = _odds(terms)
    else:
        odds = None
    if tid == "greet":
        return Topic(tid, label)
    if tid == "place":
        return Topic(tid, label, other.mood in ("neutral", "friendly"),
                     "They will not tell you anything.")
    if tid == "word":
        if other.folk == "officer":
            return _officer_word(game, other)
        pay = WORD_PRICE if other.folk == "informant" else 0
        return Topic(tid, label + (f" — {pay} cr" if pay else ""),
                     not done and other.mood != "hostile" and
                     game.credits >= pay,
                     "Asked already." if done else "Not for free, not to you."
                     if other.mood == "hostile" else "You cannot pay for it.",
                     None if pay else odds, pay)
    if tid == "persuade":
        # Once each, like everything else worth rolling for: asking the same
        # person again until the dice agree is not persuasion.
        return Topic(tid, label, not done and other.mood not in ("friendly",),
                     "Asked already." if done else
                     "They are already on your side.", odds)
    if tid == "bribe":
        cost = bribe_cost(walk, other)
        return Topic(tid, f"{label} — {cost:,} cr",
                     not done and game.credits >= cost and
                     other.mood != "friendly",
                     "Paid already." if done else "You cannot afford it."
                     if game.credits < cost else "No need.", odds, cost)
    if tid == "papers":
        return Topic(tid, label, not done, "They have seen them.", odds)
    if tid in ("business", "hire", "favour", "gift"):
        goes = {"business": "business", "hire": "hire", "favour": "favour",
                "gift": "kith"}[tid]
        return Topic(tid, label, other.mood != "hostile",
                     "Not while they are like this.", None, 0, goes)
    if tid == "patch":
        hurt = sum(max(0, a.hp_max - max(0, a.hp)) for a in patchable(walk))
        cost = hurt * PATCH_PER_POINT
        return Topic(tid, f"{label} — {cost:,} cr", hurt > 0 and
                     game.credits >= cost,
                     "Nobody needs it." if not hurt else "You cannot pay.",
                     None, cost)
    if tid == "question":
        return Topic(tid, label, not done, "They have told you what they know.")
    if tid == "enlist":
        room = berths_left(game)
        return Topic(tid, label, not done and room > 0,
                     "Asked already." if done else "There is no berth for "
                     "them.", odds)
    if tid == "sing":
        return Topic(tid, label, not done, "They have answered.")
    if tid == "answer":
        heard = "sing" in other.talked
        return Topic(tid, label, heard and not done,
                     "Asked already." if done else
                     "They have sung you nothing to answer yet.", odds)
    if tid in ("hear", "bonus", "confront"):
        from . import afoot_holdings
        return afoot_holdings.topic(game, walk, other, tid, label, done, odds)
    if tid in INCIDENT_TOPICS:
        from . import afoot_trouble
        return afoot_trouble.topic(game, walk, other, tid, label, done, odds)
    if tid == "passage":
        ready = "answer" in other.talked and other.mood == "friendly"
        return Topic(tid, label, ready and not done,
                     "Sung already." if done else
                     "Answer them well first.")
    if tid == "report":
        return Topic(tid, label)
    if tid == "story":
        return Topic(tid, label, True, "", None, 0, "despatches"
                     if _arc_waiting(game, other) else "")
    if tid == "tie":
        from . import afoot_incidents
        got = afoot_incidents.tie_terms(game, walk, who, other)
        debt = got["debt"]
        name = getattr(got["tie"], "name", "Somebody").lower()
        return Topic(tid, f"{label} ({name})" + (f" — {debt:,} cr owed"
                                                 if debt else ""),
                     not done and game.credits >= debt,
                     "Settled." if done else "You cannot cover it.", None,
                     debt)
    if tid == "join":
        size = len(party(walk))
        return Topic(tid, label, size < afoot_people.PARTY_MOST,
                     f"The party is {size} already.")
    return Topic(tid, label, False, "Nobody knows how to ask that.")


def _officer_word(game, other) -> Topic:
    last = (getattr(game, "walked", {}) or {}).get("words", {}).get(
        str(other.officer))
    ready = last is None or game.day - int(last) >= WORD_EVERY
    return Topic("word", "A word with them", ready,
                 "You spoke to them lately; it will not mean as much.")


def berths_left(game) -> int:
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(game.ship.chassis)
    return max(0, int(getattr(chassis, "crew", 0) or 0) - int(game.ship.crew))


def _arc_waiting(game, other) -> bool:
    from . import arcs
    officer = afoot_people.officer_of(game, other.officer)
    return officer is not None and bool(arcs.status(game, officer)["hint"])


# ── saying it ──────────────────────────────────────────────────────────────

def line(game, walk, other, mood: str = "") -> str:
    """What they say, in their own voice."""
    kind = FOLK_BY_ID.get(other.folk)
    mood = mood or {"friendly": "warm", "wary": "cold",
                    "hostile": "hostile"}.get(other.mood, other.mood)
    if other.folk == "harbourmaster" or other.note == "master":
        from . import voice
        key = (f"port:{walk.system_id}" if other.folk == "harbourmaster"
               else f"hull:{walk.site}")
        situation = {"warm": "", "cold": "warn", "hostile": "refuse",
                     "surrendered": "refuse"}.get(mood, "greet")
        # The written line, never a model's: a deck is walked on the window's
        # own thread, and asking a model from here would freeze the screen
        # mid-conversation for as long as the network took.
        return voice.speak(game, key, name=other.name, kind="official"
                           if other.folk == "harbourmaster" else "captain",
                           persona=getattr(kind, "persona", "plain"),
                           situation=situation, wait=False)["line"]
    if other.incident == "tie" and other.tie:
        return _tie_line(game, other, mood)
    lines = dict(getattr(kind, "lines", {}) or {})
    return _next(game, walk, other, mood,
                 lines.get(mood) or lines.get("greet") or ("…",))


def _next(game, walk, other, mood: str, pool) -> str:
    """The next of somebody's lines: from a place of their own in the list,
    and round it in order, so nothing is said twice before all of it is."""
    pool = list(pool)
    start = RNG(f"{game.seed}:line:{walk.site}:{other.id}:{mood}").int(
        0, len(pool) - 1)
    said = pool[(start + other.spoke) % len(pool)]
    other.spoke += 1
    return said


def _tie_line(game, other, mood: str) -> str:
    """Somebody from an officer's past, to the officer, by name."""
    from ..data.afoot_incidents import TIE_LINES
    officer = afoot_people.officer_of(game, int(other.tie.split(":")[0]))
    name = officer.name.split()[0] if officer else "you"
    glad = other.mood in ("friendly",) or mood == "warm"
    pool = TIE_LINES[glad]
    said = pool[other.spoke % len(pool)]
    other.spoke += 1
    return said.format(name=name)


def say_to(game, walk, who, other, tid: str, dice) -> dict:
    """Raise one topic. Refuses anything `topics` would not have offered.
    `dice` draws the dice once the topic is going ahead, never before."""
    offered = next((t for t in topics(game, walk, who, other)
                    if t.id == tid), None)
    if offered is None or not offered.ok:
        return {"ok": False, "why": offered.why if offered else
                "That is not something to ask them."}
    if offered.goes_to:
        return {"ok": True, "goes_to": offered.goes_to, "npc": other.id,
                "line": line(game, walk, other)}
    # In a fight, anything you roll for is what you do with the round.
    rolled = tid in TERMS
    if rolled and walk.mode == "action":
        if who.acted:
            return {"ok": False, "why": f"{who.name} has acted this round."}
        who.acted = True
    from . import afoot_said
    out = afoot_said.SAID[tid](game, walk, who, other, offered, dice())
    if tid not in other.talked:
        other.talked.append(tid)
    out.setdefault("ok", True)
    if out.get("line"):
        say(walk, f"{other.name}: “{out['line']}”", "")
    return out


def patchable(walk) -> list:
    """Who a medic can see to: the living, of flesh. The dead are past it
    and a machine wants a mechanic."""
    return [a for a in party(walk) if a.status not in ("dead", "gone")
            and a.folk != "robot"]


def shift(other, rungs: int) -> str:
    """Move somebody along the ladder of moods. Returns where they end."""
    if other.mood not in MOODS:
        return other.mood
    at = MOODS.index(other.mood)
    other.mood = MOODS[max(0, min(len(MOODS) - 1, at + rungs))]
    if other.mood != "hostile":
        other.aware = False
    return other.mood


def terms(game, walk, who, other, tid: str) -> dict:
    """The throw a topic is rolled with — the same one its odds came from."""
    return TERMS[tid](game, walk, who, other)

