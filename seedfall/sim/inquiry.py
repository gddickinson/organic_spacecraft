"""Running a research programme: what it eats, and how hard you push it.

Evidence is the stock; the approach is the throttle. A programme converts
evidence into progress every day, and stalls when the bench runs out of the
particular thing it needs — which is the point, because the four kinds come
from four different parts of the game.
"""

from __future__ import annotations

from ..data.inquiry import (APPROACHES_BY_ID, BRANCH_MIX, BREAKTHROUGH_GAIN,
                            DEFAULT_APPROACH, DEFAULT_MIX, EVIDENCE_BY_ID,
                            MAX_SHARE, SETBACK_LOSS, STARVED_FLOOR)
from ..data.tech import TECH_BY_ID


def store(res) -> dict:
    """The evidence lockers. Created on first use so old saves keep working."""
    if getattr(res, "evidence", None) is None:
        res.evidence = {}
    return res.evidence


def held(res, kind: str) -> float:
    return store(res).get(kind, 0.0)


def add(res, kind: str, amount: float) -> float:
    if kind not in EVIDENCE_BY_ID or amount <= 0:
        return 0.0
    locker = store(res)
    locker[kind] = locker.get(kind, 0.0) + amount
    return locker[kind]


def mix_for(tech_id: str) -> dict:
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return dict(DEFAULT_MIX)
    return dict(BRANCH_MIX.get(tech.branch, DEFAULT_MIX))


def needs(tech_id: str) -> dict:
    """How much of each kind a programme will consume end to end."""
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return {}
    mix = mix_for(tech_id)
    return {kind: tech.cost * min(MAX_SHARE, share) * 0.5
            for kind, share in mix.items()}


def approach_of(res):
    return APPROACHES_BY_ID.get(getattr(res, "approach", None) or "",
                                APPROACHES_BY_ID[DEFAULT_APPROACH])


def set_approach(res, approach_id: str) -> bool:
    if approach_id not in APPROACHES_BY_ID:
        return False
    res.approach = approach_id
    return True


def has_precedent(game) -> bool:
    """Whether there is anything to reverse-engineer: alien work or salvage."""
    if getattr(game, "xeno_study", None):
        return True
    return held(game.research, "hardware") >= 40


def available(game) -> list[tuple]:
    """(approach, ok, why) for the ways of running the current programme."""
    out = []
    for approach in APPROACHES_BY_ID.values():
        ok, why = True, ""
        if approach.needs_precedent and not has_precedent(game):
            ok, why = False, ("Nothing on the bench to take apart — you need "
                              "alien work in hand or salvaged hardware.")
        out.append((approach, ok, why))
    return out


def draw(res, tech_id: str, days: float) -> tuple[float, list[str]]:
    """Spend evidence for a spell's work. Returns (fraction served, missing).

    A programme runs at the pace of its scarcest input, so a bench with charts
    and no specimens gets some of the way and then waits — which is a nudge to
    go and do something else, not a dead end.
    """
    approach = approach_of(res)
    wanted = needs(tech_id)
    if not wanted:
        return 1.0, []
    served, missing = [], []
    for kind, total in wanted.items():
        per_day = total / 60.0 * approach.draw
        want = per_day * days
        if want <= 0:
            continue
        have = held(res, kind)
        taken = min(have, want)
        store(res)[kind] = have - taken
        served.append(taken / want if want else 1.0)
        if taken < want * 0.999:
            missing.append(kind)
    fraction = sum(served) / len(served) if served else 1.0
    fed = STARVED_FLOOR + (1.0 - STARVED_FLOOR) * fraction
    return fed, missing


def roll(res, rng, days: float) -> str | None:
    """A setback or a breakthrough. Both scale with how hard you are pushing."""
    approach = approach_of(res)
    seasons = days / 90.0
    if approach.setback and rng.chance(min(0.85, approach.setback * seasons)):
        return "setback"
    if approach.breakthrough and rng.chance(min(0.85,
                                                approach.breakthrough * seasons)):
        return "breakthrough"
    return None


def apply_event(res, event: str, tech_id: str) -> float:
    """Move the programme for a setback or a breakthrough. Returns the delta."""
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return 0.0
    if event == "setback":
        lost = res.progress * SETBACK_LOSS
        res.progress = max(0.0, res.progress - lost)
        return -lost
    gain = tech.cost * BREAKTHROUGH_GAIN
    res.progress += gain
    return gain


def summary(res) -> dict:
    locker = store(res)
    return {kind: locker.get(kind, 0.0) for kind in EVIDENCE_BY_ID}
