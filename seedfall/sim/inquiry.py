"""Running a research programme: what it eats, and how hard you push it.

Evidence is the stock; the approach is the throttle. A programme converts
evidence into progress every day, and stalls when the bench runs out of the
particular thing it needs — which is the point, because the four kinds come
from four different parts of the game.
"""

from __future__ import annotations

from ..data.inquiry import (APPROACHES_BY_ID, BRANCH_MIX, BREAKTHROUGH_GAIN,
                            DEFAULT_APPROACH, DEFAULT_MIX, EVIDENCE_BY_ID,
                            CONFIRM_DAYS_PER_COST, MAX_SHARE, SETBACK_LOSS,
                            STARVED_FLOOR)
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


def needs(tech_id: str, res=None) -> dict:
    """How much of each kind a programme will consume end to end.

    It said that and did not do it. `draw()` spent `total / 60` a day while a
    careful programme runs about 128 days, so the bench actually ate 2.1x what
    the screen advertised — measured at "wanted 26, used 56" on every track.
    The sixty was a duration nobody had checked against the real one.

    Pass the `Research` to price it for the approach in hand: running parallel
    tracks costs three benches' worth of material and the readout should say so.
    """
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return {}
    mix = mix_for(tech_id)
    pull = approach_of(res).draw if res is not None else 1.0
    return {kind: tech.cost * min(MAX_SHARE, share) * 0.5 * pull
            for kind, share in mix.items()}


def span_of(tech_id: str, res, rate: float) -> float:
    """Days a programme is expected to run at this rate, for pacing the draw."""
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return 60.0
    approach = approach_of(res)
    return max(1.0, tech.cost / max(0.01, rate * approach.speed))


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


def draw(res, tech_id: str, days: float,
         rate: float = 1.0) -> tuple[float, list[str]]:
    """Spend evidence for a spell's work. Returns (fraction served, missing).

    A programme runs at the pace of its scarcest input, so a bench with charts
    and no specimens gets some of the way and then waits — which is a nudge to
    go and do something else, not a dead end.
    """
    wanted = needs(tech_id, res)
    if not wanted:
        return 1.0, []
    # Paced over how long the programme will actually run, so what the bench
    # consumes end to end is what `needs()` said it would.
    span = span_of(tech_id, res, rate)
    served, missing = [], []
    for kind, total in wanted.items():
        per_day = total / span
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


def unconfirmed(res, rng) -> bool:
    """Did this result come out of work nobody replicated?

    The whole cost of `push`. Before this it was the fastest approach by a
    third with its setback risk already inside that figure — four ways to run
    a programme and one answer.
    """
    return rng.chance(approach_of(res).provisional)


def confirm_cost(res, tech_id: str) -> float:
    """Days on the bench to check a provisional result.

    Cheaper than the programme was, and not free — going back over unchecked
    work is the price of having skipped it.
    """
    tech = TECH_BY_ID.get(tech_id)
    if tech is None:
        return 0.0
    return max(10.0, tech.cost * CONFIRM_DAYS_PER_COST)


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
