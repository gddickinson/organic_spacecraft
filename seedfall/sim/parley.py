"""Breaking off, and talking your way out.

The two ways an engagement ends that are not somebody's hull coming apart.
Split out of combat.py when it crossed five hundred lines; these are the least
entangled part of it — they read the battle, decide an outcome and hand back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..core.util import clamp
from ..data.factions import FACTIONS_BY_ID
from . import tactical as tac
from .battle_state import Battle
from .ship import hull_pct, is_destroyed


@dataclass(frozen=True)
class Ops:
    """The resolver's own helpers, handed in rather than imported.

    combat.py owns the log, the damage application and the enemy's turn; this
    module owns two of the ways a fight ends. Passing them in keeps the
    dependency one-way, the same way `enemy_turn` already takes its callables.
    """
    say: Callable
    fire: Callable
    salvo: Callable
    use_ability: Callable
    enemy_turn: Callable
    finish: Callable
    end_of_turn: Callable


#: Resolve below which a hull's nerve is visibly going, and it will listen.
WAVERING_AT = 45.0

#: How much of a power's memory of you carries into a hail, per point of
#: `grudge.feeling` — so a settled hatred of -100 is worth -0.20 on the chance
#: and a debt of gratitude the same the other way.
#:
#: Deliberately smaller than the standing term (rep/260 = 0.38 across its full
#: range): the ledger is what they will admit to and the memory is what they
#: actually feel, and the first is what a hail is conducted in. Measured, a
#: Charter that remembers a destroyed hull and a run blockade sits at -54, which
#: takes eleven points off the chance.
MEMORY_WEIGHT = 0.002


#: What a refused hail or a failed burn hands over: the enemy takes its turn
#: anyway. Not a constant — a statement about the code below, which calls
#: `ops.enemy_turn` on the failing branch of both. The screens have to say so:
#: a one-shot gamble whose losing side is "they shoot you for free" is a
#: different decision from one that merely does nothing.
COSTS_A_TURN = True


def escape_odds(b: Battle) -> dict:
    """The chance of shaking them off, and what each part of it is worth.

    **The one door**, so the button and the burn cannot disagree. `flee` reads
    this; before it existed the sum lived inside `flee` alone and the screen
    offered "Disengage" with no number on it at all — the only act in the game
    with no forecast, alongside its neighbour below.
    """
    if b.player.grappled:
        return {"chance": 0.0, "held": True, "terms": [],
                "why": "You are held fast — cut loose first."}
    room = b.band * 0.13
    legs = (b.player.st.speed - b.enemy.st.speed) * 0.35
    slip = b.player.st.evade * 0.5
    chance = clamp(0.22 + room + legs + slip, 0.05, 0.94)
    terms = [("the room you have", room)]
    if abs(legs) > 0.005:
        terms.append(("the legs on them" if legs > 0 else "they are faster",
                      legs))
    if slip > 0.005:
        terms.append(("how hard you are to hold", slip))
    return {"chance": chance, "held": False, "terms": terms, "why": ""}


def odds(b: Battle) -> dict:
    """The chance they stand down if hailed, and what each part is worth.

    The same door as `hail`, and the reason this module now has one. A hail was
    a hidden one-shot: press it and either the fight ends or the enemy takes a
    free turn, with the probability written nowhere a captain could read it.
    Everything else in the game quotes itself — `stations.order_preview` prints a
    line per helm order on the very panel these two buttons sit on.

    **And it never asked what the power actually remembers.** `b.rep` is the
    standing on the books; `grudge.feeling` is the memory behind it, which the
    game already spends on prices, on whether a desk will talk to you and on
    whether work is posted at all. A captain who burned a Charter hull last year
    should find the Charter harder to talk to, and did not.
    """
    if b.no_parley:
        return {"chance": 0.0, "mute": True, "terms": [],
                "why": "The Bloom has no one to say it with."}
    strength = hull_pct(b.player.ship) - hull_pct(b.enemy.ship)
    standing = b.rep / 260.0
    upper = strength * 0.3
    talker = b.player.st.diplomacy
    wavering = 0.25 if b.enemy.resolve < WAVERING_AT else 0.0
    memory = _memory(b)
    chance = clamp(0.18 + talker + standing + upper + wavering + memory,
                   0.03, 0.92)
    terms = []
    if abs(standing) > 0.005:
        terms.append(("your standing with them", standing))
    if abs(upper) > 0.005:
        terms.append(("you have the upper hand" if upper > 0
                      else "they are winning", upper))
    if talker > 0.005:
        terms.append(("somebody aboard who can talk", talker))
    if wavering:
        terms.append(("their nerve is going", wavering))
    if abs(memory) > 0.005:
        terms.append(("what they remember of you", memory))
    return {"chance": chance, "mute": False, "terms": terms, "why": ""}




def _memory(b: Battle) -> float:
    """What this power's memory of the captain is worth to a hail."""
    game = getattr(b, "game", None)
    faction = getattr(b, "enemy_faction", None)
    if game is None or not faction:
        return 0.0
    from . import grudge
    try:
        return grudge.feeling(game, faction) * MEMORY_WEIGHT
    except Exception:                       # a battle without a real chronicle
        return 0.0


def flee(b: Battle, rng, ops: "Ops") -> Battle:
    told = escape_odds(b)
    if told["held"]:
        ops.say(b, "You are held fast. Nothing to do but cut loose or fight.", "warn")
        return b
    chance = told["chance"]
    if rng.chance(chance):
        return ops.finish(b, "escaped")
    ops.say(b, "The burn is not enough — they are still with you.", "warn")
    broke = ops.enemy_turn(b, rng, ops.say, ops.fire, ops.salvo, ops.use_ability)
    if broke:
        return ops.finish(b, broke)
    if is_destroyed(b.player.ship):
        return ops.finish(b, "lost")
    if not b.over:
        ops.end_of_turn(b, rng)
    return b


def hail(b: Battle, rng, ops: "Ops") -> Battle:
    told = odds(b)
    if told["mute"]:
        ops.say(b, "The Bloom has nothing to say. It has no one to say it with.", "bad")
        return b
    if rng.chance(told["chance"]):
        return ops.finish(b, "parley")
    ops.say(b, "They hear you out and keep firing.", "warn")
    broke = ops.enemy_turn(b, rng, ops.say, ops.fire, ops.salvo, ops.use_ability)
    if broke:
        return ops.finish(b, broke)
    if is_destroyed(b.player.ship):
        return ops.finish(b, "lost")
    if not b.over:
        ops.end_of_turn(b, rng)
    return b
