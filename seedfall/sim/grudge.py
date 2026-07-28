"""What a power's memory of you actually costs you, and why.

Standing is one number that decays. A grudge is a *specific* thing with a date
on it, and this is where those specifics start changing behaviour rather than
only colouring what an envoy says.

Three things it does, each of which a screen can explain:

- **A quay prices you by its memory.** A power that remembers you well shaves
  its margin; one that remembers a seizure or a kill widens it.
- **A power that holds enough against you stops offering work**, which is a
  harder wall than a poor price and is why the threshold is well past the
  point of mild annoyance.
- **Grudges travel.** Powers that are close on the relations matrix pick up a
  share of each other's feeling about you, which is what makes the matrix
  something you have to think about rather than a readout.

The rule that keeps it honest: `because()` names the memories responsible for
whatever `feeling()` returns, so nothing in the game can dislike you for a
reason it cannot state. `test_grudges` performs each effect and compares.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..data.personas import FACTION_PERSONA
from . import diplomacy as dip_sim
from . import memory as memory_sim

#: How much of an ally's feeling about you rubs off, at full warmth.
INHERIT = 0.35

#: Relations at or above this count as close enough to share a grudge.
CLOSE = 35.0

#: Feeling below this and a power stops posting work to you.
COLD_SHOULDER = -55.0

#: The widest a memory alone may move a price, as a share.
PRICE_SWING = 0.18


def key_for(faction_id: str) -> str:
    return f"faction:{faction_id}"


def mind_of(game, faction_id: str):
    faction = FACTIONS_BY_ID.get(faction_id)
    return memory_sim.mind_for(
        game, key_for(faction_id),
        name=faction.name if faction else faction_id, kind="faction",
        persona=FACTION_PERSONA.get(faction_id, "envoy"))


def direct(game, faction_id: str) -> float:
    """What this power holds against you itself. −100..100."""
    return mind_of(game, faction_id).impression()


def inherited(game, faction_id: str) -> list:
    """(power, how much of theirs rubs off) for everyone close to this one."""
    state = dip_sim.ensure(game)
    out = []
    for other in dip_sim.POWERS:
        if other == faction_id:
            continue
        warmth = state.relations.get(dip_sim._key(faction_id, other), 0.0)
        if warmth < CLOSE:
            continue
        share = INHERIT * min(1.0, (warmth - CLOSE) / (100.0 - CLOSE) + 0.35)
        theirs = direct(game, other)
        if abs(theirs) < 1.0:
            continue
        out.append((other, theirs * share))
    return out


def feeling(game, faction_id: str) -> float:
    """Everything this power feels about you: its own memory, plus its friends'."""
    total = direct(game, faction_id)
    for _other, share in inherited(game, faction_id):
        total += share
    return max(-100.0, min(100.0, total))


def because(game, faction_id: str, limit: int = 4) -> list:
    """The memories responsible, worst or best first. Never empty-handed.

    This is the point of the whole module. A power that will not trade with
    you must be able to say which day it decided that.
    """
    mind = mind_of(game, faction_id)
    own = [m for m in mind.memories
           if m.about == "player" and abs(m.weight()) >= 1.0
           and m.salience >= memory_sim.FLOOR]
    sour = feeling(game, faction_id) < 0
    own.sort(key=lambda m: m.weight() if sour else -m.weight())
    out = [{"day": m.day, "kind": m.kind, "text": m.text,
            "weight": round(m.weight(), 1), "whose": faction_id}
           for m in own[:limit]]
    # Inherited feeling is listed whichever way it runs. The first version
    # only showed it when it agreed with the overall sign, which hid the most
    # useful fact on the screen: a power that likes you but is close to one
    # that does not, and is cooler than its own memories explain.
    for other, share in inherited(game, faction_id):
        if abs(share) < 1.0:
            continue
        friend = FACTIONS_BY_ID.get(other)
        name = friend.name if friend else other
        out.append({"day": game.day, "kind": "inherited",
                    "text": (f"they are close to {name}, who feels the same"
                             if (share < 0) == sour else
                             f"they are close to {name}, who does not agree"),
                    "weight": round(share, 1), "whose": other})
    return out[:limit + 2]


# ── what it changes ────────────────────────────────────────────────────────

def price_bias(game, faction_id: str) -> float:
    """A multiplier on what this power's quays charge you. 1.0 is neutral.

    Bounded on purpose: memory should be felt and should not replace the
    market. At the extremes it is a fifth either way, which is the difference
    between a run being worth making and not.
    """
    if not faction_id:
        return 1.0
    swing = feeling(game, faction_id) / 100.0
    return 1.0 - PRICE_SWING * swing


def will_deal(game, faction_id: str) -> tuple:
    """Whether this power still posts work to you, and what it would say."""
    held = feeling(game, faction_id)
    if held > COLD_SHOULDER:
        return True, ""
    faction = FACTIONS_BY_ID.get(faction_id)
    reasons = because(game, faction_id, limit=1)
    named = reasons[0]["text"] if reasons else "what you have done"
    return False, (f"{faction.name if faction else faction_id} is not "
                   f"putting work your way. There is the matter of {named}.")


def hostile_open(game, faction_id: str) -> bool:
    """Whether a hull of this power opens fire rather than hailing."""
    return feeling(game, faction_id) <= COLD_SHOULDER * 1.3


def standing_note(game, faction_id: str) -> str:
    """One line for a screen: how they feel, and the plainest reason."""
    held = feeling(game, faction_id)
    if abs(held) < 6:
        return "They have nothing much on you either way."
    reasons = because(game, faction_id, limit=1)
    lead = ("They think well of you" if held > 0
            else "They hold something against you")
    if not reasons:
        return f"{lead}, though nothing in particular stands out."
    return f"{lead}: {reasons[0]['text']}."


def summary(game) -> list:
    """Every power, what it feels, and why — for the diplomacy screen."""
    out = []
    for faction_id in dip_sim.POWERS:
        held = feeling(game, faction_id)
        deals, why = will_deal(game, faction_id)
        out.append({
            "faction": faction_id,
            "name": getattr(FACTIONS_BY_ID.get(faction_id), "name", faction_id),
            "feeling": round(held, 1),
            "direct": round(direct(game, faction_id), 1),
            "inherited": [(o, round(v, 1)) for o, v in
                          inherited(game, faction_id)],
            "deals": deals, "why": why,
            "because": because(game, faction_id),
            "prices": round(price_bias(game, faction_id), 3),
        })
    return out


# ── writing the political memories ─────────────────────────────────────────

def note(game, faction_id: str, kind: str, text: str, salience: float = 1.0,
         tags=()) -> None:
    """Record something a power would remember about you. The ordinary way in."""
    if not faction_id:
        return
    faction = FACTIONS_BY_ID.get(faction_id)
    memory_sim.note(game, key_for(faction_id), kind, text, salience,
                    tags=list(tags) or ["politics", faction_id],
                    name=faction.name if faction else faction_id,
                    entity="faction")
