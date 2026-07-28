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
        res.banked += gained
        return None

    served, missing = inquiry.draw(res, res.current, days)
    approach = inquiry.approach_of(res)
    res.progress += (gained * approach.speed * served) + res.banked
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
        res.current = None
        return t.id
    return None


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
