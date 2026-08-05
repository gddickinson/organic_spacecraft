"""Research.

Points accrue from surveys, laboratories, CHORUS nodes and simply paying
attention; a project completes when its cost is met.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..core.save import register
from ..data.tech import (STARTING_TECH, TECH_BY_ID, bonuses, can_research,
                         researchable)
from . import inquiry


@register
@dataclass
class Research:
    unlocked: list[str] = field(default_factory=lambda: list(STARTING_TECH))
    current: str | None = None
    progress: float = 0.0
    points: float = 0.0
    banked: float = 0.0
    evidence: dict = field(default_factory=dict)
    approach: str = "careful"
    #: Technologies unlocked on unreplicated results. They work, and they do
    #: not work fully, until somebody goes back and confirms them. See
    #: `data/tech.PROVISIONAL_WORTH` and `sim/inquiry.confirm`.
    provisional: list[str] = field(default_factory=list)
    #: The tech currently being confirmed, and how far along.
    confirming: str | None = None
    confirm_days: float = 0.0
    #: Points the *tree* cannot use, waiting for the standing programmes to
    #: take them. Distinct from `banked`, which is a day's work waiting for a
    #: project the captain has not chosen yet — see `tick`.
    spare: float = 0.0
    #: Which inputs the bench ran short of last tick, for the readout only.
    starved: list = field(default_factory=list, metadata={"transient": True})
    last_event: str | None = field(default=None, metadata={"transient": True})


def set_project(res: Research, tech_id: str) -> bool:
    if not can_research(tech_id, res.unlocked):
        return False
    if res.current and res.current != tech_id:
        res.progress = 0.0
    res.current = tech_id
    return True


def tick(res: Research, days: float, rate: float, rng=None) -> str | None:
    """Spend a day's work. Returns the tech id if something completed.

    Progress is the day's points multiplied by how well the bench is supplied:
    a programme with charts and no specimens gets part of the way and waits.
    """
    gained = rate * days
    res.points += gained
    if not res.current:
        # Two different reasons for having no project, and they are not the
        # same thing. With nodes still open the captain simply has not chosen
        # yet, and the day banks against whatever they pick. With the tree
        # exhausted there is nothing to pick, and banking is a slow leak into
        # a number the screen displays and nothing can spend — 146,040 points
        # over the ten years after the tree closed. Those go to the bench's
        # standing work instead. See `sim/programmes.py`.
        if researchable(res.unlocked):
            res.banked += gained
        else:
            res.spare += gained + res.banked
            res.banked = 0.0
        return None

    served, missing = inquiry.draw(res, res.current, days, rate)
    approach = inquiry.approach_of(res)
    # **Banked points are worked, not simply added.** They used to be poured
    # in raw while the day's own points were throttled by what the bench is
    # actually supplied with (`served`, floored at 0.35) — so *not choosing*
    # a project was worth more than running one, and a lump saved up while
    # idle cascaded through node after node on consecutive days. Measured
    # over five seeds and 2,100 days on identical totals: always-on 12
    # techs, bank-then-dump 16 to 17. Evidence gates the whole day's work
    # or it gates none of it.
    res.progress += (gained + res.banked) * approach.speed * served
    res.banked = 0.0
    res.starved = list(missing)

    if rng is not None:
        event = inquiry.roll(res, rng, days)
        if event:
            inquiry.apply_event(res, event, res.current)
            res.last_event = event

    t = TECH_BY_ID.get(res.current)
    if t and res.progress >= t.cost:
        res.progress -= t.cost
        res.unlocked.append(t.id)
        # An approach that skips the confirmations sometimes hands you a
        # result nobody has replicated. It unlocks; it does not deliver all
        # of what it promises until somebody checks the work.
        if rng is not None and inquiry.unconfirmed(res, rng):
            res.provisional.append(t.id)
            res.last_event = "provisional"
        res.current = None
        return t.id
    return None


def confirm_tick(res: Research, days: float) -> str | None:
    """Spend a spell checking a provisional result. Returns it when sound."""
    if not res.confirming or res.confirming not in res.provisional:
        res.confirming = None
        return None
    res.confirm_days = max(0.0, res.confirm_days - days)
    if res.confirm_days > 0:
        return None
    done = res.confirming
    res.provisional.remove(done)
    res.confirming = None
    return done


def take_spare(res: Research) -> float:
    """Hand over the points the tree could not use, and forget them.

    Taken rather than read, so there is exactly one consumer and no chance of
    the same day's work being spent twice — the shape of fault that produced a
    free treaty and a phantom haggle payment elsewhere in this project.
    """
    got = max(0.0, res.spare)
    res.spare = 0.0
    return got


def grant(res: Research, amount: float) -> None:
    """A direct grant — from an anomaly, a sold data set, a helpful stranger."""
    if res.current:
        res.progress += amount
    else:
        res.banked += amount
    res.points += amount


def progress_pct(res: Research) -> float:
    t = TECH_BY_ID.get(res.current) if res.current else None
    return min(1.0, res.progress / t.cost) if t and t.cost else 0.0


def days_remaining(res: Research, rate: float) -> float:
    t = TECH_BY_ID.get(res.current) if res.current else None
    if not t or rate <= 0:
        return math.inf
    return math.ceil((t.cost - res.progress) / rate)


__all__ = ["Research", "set_project", "tick", "grant", "progress_pct",
           "days_remaining", "researchable", "can_research", "bonuses", "inquiry"]
