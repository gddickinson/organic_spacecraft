"""The Bloom as an antagonist rather than a timer.

It grows through named stages, keeps roaming instars in the field once it is
motile, builds resistance to whatever you keep shooting it with, and has a heart
at Kessel's Reach that Containment has to actually reach and kill.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from ..core.save import register
from ..data.bloom import (BEATS, HEART_HP, MAX_RESIST, RESIST_DECAY,
                          RESIST_PER_HIT, STAGE_BY_ANSWERS, STAGES,
                          STAGES_BY_ID)
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
    #: What the *captain* has cost it, undecayed and never NPC-fed — the
    #: record `threat._stood_through_it` reads. `provocation` cannot serve:
    #: the powers' own containment flotillas provoke on the clock, so a
    #: level test handed Ruin to total passivity.
    fought: float = 0.0
    #: Damage dealt to it per weapon family, from the first shot — what
    #: "adapting everywhere at once" adapts against (`responses.check`).
    hurt: dict[str, float] = field(default_factory=dict)

    @property
    def definition(self):
        return STAGES_BY_ID[self.stage]


def ensure(game) -> BloomState:
    """The state, created on first use so old saves keep working.

    The heart is pinned by the generator's own rule — the far corner,
    `max(x + y)`, which is where `world/galaxy._seed_bloom` put Kessel's
    Reach — rather than by whichever system happens to read the highest
    bloom today. On an old save loaded mid-campaign several systems can sit
    at 1.0, and the live reading landed the heart on the first of them in
    list order while every screen still called it Kessel's Reach.
    """
    if getattr(game, "bloom_state", None) is None:
        state = BloomState()
        origin = max(game.galaxy.systems, key=lambda s: s.x + s.y)
        state.heart_system = origin.id
        game.bloom_state = state
    return game.bloom_state


# ── stages ─────────────────────────────────────────────────────────────────

def review_stage(game, burden: float) -> list[tuple[str, str]]:
    """Advance the stage when the burden — or the answering — earns it.

    Never regresses. Burden alone made the antagonist unreachable: it only
    climbs when nobody fights, so an engaged captain killed the Bloom at
    stage 0 and never met adaptation, roaming instars or the hunt. What it
    has answered (`data/bloom.STAGE_BY_ANSWERS`) carries the stage too now —
    a captain who burns it back meets the Adaptive Bloom *because* they
    burned it back, which is what the herald has claimed all along ("It is
    learning by dying").
    """
    state = ensure(game)
    events = []
    answered = len(state.responses or [])
    floor = STAGE_BY_ANSWERS[min(answered, len(STAGE_BY_ANSWERS) - 1)]
    for stage in STAGES:
        if (burden >= stage.threshold or stage.id <= floor) \
                and stage.id > state.stage:
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
    """Every hit teaches it a little, once it is adaptive.

    What the hit was made *with* is remembered from the first shot, whatever
    the stage — it is what "adapting everywhere at once" adapts against when
    the harden response fires before any resistance exists.
    """
    state = ensure(game)
    if amount <= 0:
        return
    state.hurt[family] = state.hurt.get(family, 0.0) + amount
    if state.stage < 3:
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


def most_hurt(game) -> str | None:
    """The weapon family that has cost it the most, resisted or not."""
    state = ensure(game)
    if not state.hurt:
        return None
    return max(state.hurt, key=lambda k: state.hurt[k])


# ── instars ────────────────────────────────────────────────────────────────

def _spawn_instar(game, rng, from_heart: bool = False) -> Instar | None:
    """A mass detaches. `from_heart` lets it come from the origin itself.

    A cleaned sector is not a dead one while the heart lives, and without
    that the responses which detach masses ("a seeding wave", "it is coming
    for you") printed their text over an empty list precisely when a
    fighting captain had earned them.

    **Only the responses may use it.** The routine top-up in `tick_instars`
    keeps a stage's masses in the field *every tick*, so letting that reach
    the heart turned the origin into a permanent re-infestation engine:
    measured over the climax, nineteen strikes at the heart put the sector
    from clean back to two systems at 1.00 and containment out of reach.
    A wave is an event; the top-up is a standing condition.
    """
    state = ensure(game)
    held = [s for s in game.galaxy.systems if s.bloom > 0.4]
    if (not held and from_heart and state.heart_hp > 0
            and state.heart_system is not None):
        held = [game.galaxy.systems[state.heart_system]]
    if not held:
        return None
    home = rng.pick(held)
    inst = Instar(id=next(_uid), system_id=home.id,
                  mass=rng.float(0.8, 1.0) + state.stage * 0.35)
    _retarget(game, inst)
    return inst


def _retarget(game, inst: Instar) -> None:
    """Instars go for your holdings first, then for clean ground.

    Never for the system it is standing in: the nearest of the pool could be
    exactly that, and the mass then "arrived" every twenty days for ever,
    re-seeding the growth and re-rolling the colony attack each time.
    """
    # A hunting Bloom goes for the hull itself, wherever it stands — the
    # sentence the System screen prints ("it is sending masses after your
    # hull specifically") was read by that one label and by nothing here,
    # so it stopped being true after the first two masses. The rule above
    # still holds: never the system the mass is standing in.
    from . import responses as response_sim
    if (response_sim.hunting(game)
            and game.location_id != inst.system_id):
        inst.target_id = game.location_id
        inst.days = 0.0
        return
    here = game.galaxy.systems[inst.system_id]
    yours = [game.galaxy.systems[c.system_id] for c in game.colonies if c.online]
    pool = [s for s in (yours or [t for t in game.galaxy.systems
                                  if t.bloom < 0.3])
            if s.id != inst.system_id]
    if not pool:
        inst.target_id = None
        return
    pool = sorted(pool, key=lambda s: distance(s, here))
    inst.target_id = pool[0].id
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
            _retarget(game, inst)
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
        _retarget(game, inst)
    return events


def instar_at(game, system_id: int) -> Instar | None:
    state = ensure(game)
    return next((i for i in state.instars if i.system_id == system_id), None)


def engage_instar(game, inst: "Instar") -> dict:
    """An encounter against a roaming mass, scaled by how big it has grown.

    Instars arrived, seeded a system, ate colonies and moved on, and there was
    no way to do anything about one: `kill_instar` was called by nothing at all
    and the provocation table paid seventy for a kill that could not happen.
    """
    from . import encounters
    rng = game.rng(f"instar-{inst.id}")
    enemy = encounters.make_enemy(rng, "bloom", 1.0 + inst.mass * 1.4)
    return {
        "enemy": enemy, "no_parley": True, "instar": inst.id,
        "intro": ("The mass does not manoeuvre so much as decide where it "
                  "would rather be. It has no bridge to hail and nothing that "
                  "wants anything."),
    }


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
    """Burn the original germination. It takes several visits.

    The provocation lands after the guards: it used to be paid first — 260,
    the largest value in the table — so a strike refused for being in the
    wrong system still enraged it. Only a burn that happens is answered.
    """
    from . import responses
    state = ensure(game)
    if state.heart_hp <= 0:
        return {"ok": False, "why": "There is nothing left of it."}
    sysm = heart_system(game)
    if sysm is None or game.location_id != sysm.id:
        return {"ok": False, "why": "You are not at Kessel's Reach."}
    if not state.heart_found:
        return {"ok": False, "why": "You have not found it. Survey the system."}

    responses.provoke(game, "heart")
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
