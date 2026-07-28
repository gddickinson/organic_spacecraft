"""The Bloom as an antagonist rather than a timer.

It grows through named stages, keeps roaming instars in the field once it is
motile, builds resistance to whatever you keep shooting it with, and has a heart
at Kessel's Reach that Containment has to actually reach and kill.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.bloom import (BEATS, HEART_HP, HEART_NAME, MAX_RESIST,
                          RESIST_DECAY, RESIST_PER_HIT, STAGES, STAGES_BY_ID)
from ..world.galaxy import distance

_uid = itertools.count(1)


@register
@dataclass
class Instar:
    """A mass under way between systems. It has somewhere to be."""
    id: int
    system_id: int
    mass: float
    target_id: int | None = None
    days: float = 0.0


@register
@dataclass
class BloomState:
    stage: int = 0
    resist: dict[str, float] = field(default_factory=dict)
    instars: list = field(default_factory=list)
    heart_hp: float = HEART_HP
    heart_system: int | None = None
    heart_found: bool = False
    beats: list[str] = field(default_factory=list)
    provocation: float = 0.0
    responses: list[str] = field(default_factory=list)

    @property
    def definition(self):
        return STAGES_BY_ID[self.stage]


def ensure(game) -> BloomState:
    """The state, created on first use so old saves keep working."""
    if getattr(game, "bloom_state", None) is None:
        state = BloomState()
        origin = max(game.galaxy.systems, key=lambda s: s.bloom)
        state.heart_system = origin.id
        game.bloom_state = state
    return game.bloom_state


# ── stages ─────────────────────────────────────────────────────────────────

def review_stage(game, burden: float) -> list[tuple[str, str]]:
    """Advance the stage when the burden earns it. Never regresses."""
    state = ensure(game)
    events = []
    for stage in STAGES:
        if burden >= stage.threshold and stage.id > state.stage:
            state.stage = stage.id
            events.append(("bad", stage.herald))
    return events


def beat(game, key: str) -> tuple[str, str] | None:
    """Fire a one-time story line, if it has not fired before."""
    state = ensure(game)
    if key in state.beats or key not in BEATS:
        return None
    state.beats.append(key)
    return ("bad", BEATS[key])


# ── adaptation ─────────────────────────────────────────────────────────────

def resistance(game, family: str) -> float:
    state = ensure(game)
    if state.stage < 3:
        return 0.0
    return min(MAX_RESIST, state.resist.get(family, 0.0))


def record_damage(game, family: str, amount: float) -> None:
    """Every hit teaches it a little, once it is adaptive."""
    state = ensure(game)
    if state.stage < 3 or amount <= 0:
        return
    state.resist[family] = min(MAX_RESIST,
                               state.resist.get(family, 0.0)
                               + RESIST_PER_HIT * amount)


def decay_resistance(game, days: float) -> None:
    """What you stop using, it stops needing to resist."""
    state = ensure(game)
    for key in list(state.resist):
        state.resist[key] = max(0.0, state.resist[key] - RESIST_DECAY * days)
        if state.resist[key] <= 0:
            del state.resist[key]


def worst_resisted(game) -> tuple[str, float] | None:
    state = ensure(game)
    if not state.resist:
        return None
    family = max(state.resist, key=lambda k: state.resist[k])
    return family, state.resist[family]


# ── instars ────────────────────────────────────────────────────────────────

def _spawn_instar(game, rng) -> Instar | None:
    held = [s for s in game.galaxy.systems if s.bloom > 0.4]
    if not held:
        return None
    home = rng.pick(held)
    inst = Instar(id=next(_uid), system_id=home.id,
                  mass=rng.float(0.8, 1.0) + ensure(game).stage * 0.35)
    _retarget(game, inst, rng)
    return inst


def _retarget(game, inst: Instar, rng) -> None:
    """Instars go for your holdings first, then for clean ground."""
    here = game.galaxy.systems[inst.system_id]
    yours = [game.galaxy.systems[c.system_id] for c in game.colonies if c.online]
    pool = yours or [s for s in game.galaxy.systems if s.bloom < 0.3]
    if not pool:
        inst.target_id = None
        return
    pool = sorted(pool, key=lambda s: distance(s, here))
    inst.target_id = pool[0].id if pool else None
    inst.days = 0.0


def tick_instars(game, days: float, rng) -> list[tuple[str, str]]:
    """Move the roaming masses and let them arrive."""
    from .colony import bloom_attack
    state = ensure(game)
    stage = state.definition
    events: list[tuple[str, str]] = []

    while len(state.instars) < stage.instars:
        inst = _spawn_instar(game, rng)
        if inst is None:
            break
        state.instars.append(inst)
        target = (game.galaxy.systems[inst.target_id].name
                  if inst.target_id is not None else "open space")
        events.append(("bad", f"An instar has detached and is under way toward "
                              f"{target}."))

    for inst in list(state.instars):
        if inst.target_id is None:
            _retarget(game, inst, rng)
            continue
        inst.days += days
        here = game.galaxy.systems[inst.system_id]
        target = game.galaxy.systems[inst.target_id]
        travel = max(20.0, distance(here, target) * 9)
        if inst.days < travel:
            continue

        # It arrives.
        inst.system_id = target.id
        inst.days = 0.0
        target.bloom = min(1.0, max(target.bloom, 0.12) + 0.18 * inst.mass)
        lost = bloom_attack(game, target, rng)
        for col in lost:
            events.append(("bad", f"{col.name} was taken by an instar."))
            b = beat(game, "first_colony_lost")
            if b:
                events.append(b)
        if target.port:
            b = beat(game, "first_port_threatened")
            if b:
                events.append(b)
        events.append(("bad", f"An instar has arrived at {target.name}."))
        _retarget(game, inst, rng)
    return events


def instar_at(game, system_id: int) -> Instar | None:
    state = ensure(game)
    return next((i for i in state.instars if i.system_id == system_id), None)


def kill_instar(game, inst: Instar) -> None:
    from . import responses
    responses.provoke(game, "instar")
    state = ensure(game)
    if inst in state.instars:
        state.instars.remove(inst)


# ── the heart ──────────────────────────────────────────────────────────────

def heart_system(game):
    state = ensure(game)
    if state.heart_system is None:
        return None
    return game.galaxy.systems[state.heart_system]


def reveal_heart(game) -> tuple[str, str] | None:
    state = ensure(game)
    if state.heart_found:
        return None
    state.heart_found = True
    return beat(game, "heart_located")


def strike_heart(game, firepower: float, rng) -> dict:
    from . import responses
    responses.provoke(game, "heart")
    """Burn the original germination. It takes several visits."""
    state = ensure(game)
    if state.heart_hp <= 0:
        return {"ok": False, "why": "There is nothing left of it."}
    sysm = heart_system(game)
    if sysm is None or game.location_id != sysm.id:
        return {"ok": False, "why": "You are not at Kessel's Reach."}
    if not state.heart_found:
        return {"ok": False, "why": "You have not found it. Survey the system."}

    cut = firepower * rng.float(0.8, 1.3)
    state.heart_hp = max(0.0, state.heart_hp - cut)
    backlash = round(cut * 0.55 * rng.float(0.7, 1.2))
    return {"ok": True, "cut": cut, "left": state.heart_hp,
            "backlash": backlash, "destroyed": state.heart_hp <= 0}


def heart_dead(game) -> bool:
    return ensure(game).heart_hp <= 0


def summary(game) -> dict:
    state = ensure(game)
    stage = state.definition
    return {"stage": stage, "instars": len(state.instars),
            "heart_hp": state.heart_hp, "heart_found": state.heart_found,
            "resist": dict(state.resist)}
