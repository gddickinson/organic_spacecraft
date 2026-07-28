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


def flee(b: Battle, rng, ops: "Ops") -> Battle:
    if b.player.grappled:
        ops.say(b, "You are held fast. Nothing to do but cut loose or fight.", "warn")
        return b
    chance = clamp(0.22 + b.band * 0.13
                   + (b.player.st.speed - b.enemy.st.speed) * 0.35
                   + b.player.st.evade * 0.5, 0.05, 0.94)
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
    if b.no_parley:
        ops.say(b, "The Bloom has nothing to say. It has no one to say it with.", "bad")
        return b
    strength = hull_pct(b.player.ship) - hull_pct(b.enemy.ship)
    chance = clamp(0.18 + b.player.st.diplomacy + b.rep / 260 + strength * 0.3
                   + (0.25 if b.enemy.resolve < 45 else 0), 0.03, 0.92)
    if rng.chance(chance):
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
