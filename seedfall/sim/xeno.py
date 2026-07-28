"""Understanding alien technology.

Nothing here is researched. A xenotechnology is *found* — dug out of a world,
bought as somebody else's field notes, or taken off a hull that had it first —
and understood gradually, on a scale of study points. When the understanding is
complete the technology is incorporated: its id joins ``research.unlocked``, so
the shipyard and the codex treat it exactly like anything else you know.
"""

from __future__ import annotations

from ..data.xenotech import (CULTURES, CULTURES_BY_ID, DIG_YIELD, XENOLITH_STUDY,
                             XENOTECH, XENOTECH_BY_ID, XenoTech, by_culture)
from . import loyalty


def study_of(game, tech_id: str) -> float:
    return game.xeno_study.get(tech_id, 0.0)


def is_incorporated(game, tech_id: str) -> bool:
    return tech_id in game.research.unlocked


def is_known(game, tech_id: str) -> bool:
    """Have we seen enough of this to know it exists?"""
    return tech_id in game.xeno_study or is_incorporated(game, tech_id)


def prerequisites_met(game, tech: XenoTech) -> bool:
    return all(is_incorporated(game, r) for r in tech.requires)


def progress(game, tech_id: str) -> float:
    tech = XENOTECH_BY_ID.get(tech_id)
    if tech is None or tech.study <= 0:
        return 0.0
    if is_incorporated(game, tech_id):
        return 1.0
    return min(1.0, study_of(game, tech_id) / tech.study)


def add_study(game, tech_id: str, points: float) -> tuple[float, bool]:
    """Bank understanding. Returns (points actually applied, newly incorporated).

    Study past the prerequisites is held rather than lost: you can dig up the
    Phase Loom before you understand the Null Seam, and the notes keep.
    """
    tech = XENOTECH_BY_ID.get(tech_id)
    if tech is None or is_incorporated(game, tech_id):
        return 0.0, False
    game.xeno_study[tech_id] = study_of(game, tech_id) + points
    loyalty.record(game, "xeno_study", scale=min(2.0, points / 40))
    if game.xeno_study[tech_id] >= tech.study and prerequisites_met(game, tech):
        incorporate(game, tech_id)
        loyalty.record(game, "xeno_incorporated")
        if tech_id == "firstcontact" or tech.id.startswith("abyssal"):
            loyalty.record(game, "first_contact")
        return points, True
    return points, False


def incorporate(game, tech_id: str) -> bool:
    tech = XENOTECH_BY_ID.get(tech_id)
    if tech is None or is_incorporated(game, tech_id):
        return False
    game.research.unlocked.append(tech_id)
    game.xeno_study[tech_id] = float(tech.study)
    return True


def ready_to_incorporate(game) -> list[XenoTech]:
    """Fully studied, but waiting on a prerequisite that has since been met."""
    out = []
    for t in XENOTECH:
        if (not is_incorporated(game, t.id)
                and study_of(game, t.id) >= t.study
                and prerequisites_met(game, t)):
            out.append(t)
    return out


def settle(game) -> list[XenoTech]:
    """Incorporate anything whose moment has arrived. Called from the clock."""
    done = []
    for t in ready_to_incorporate(game):
        if incorporate(game, t.id):
            done.append(t)
    return done


def bonuses(game) -> dict[str, float]:
    """Passive effects of everything incorporated, in research-bonus shape."""
    out: dict[str, float] = {}
    for t in XENOTECH:
        if is_incorporated(game, t.id):
            for k, v in t.bonus.items():
                out[k] = out.get(k, 0.0) + v
    return out


def incorporated(game) -> list[XenoTech]:
    return [t for t in XENOTECH if is_incorporated(game, t.id)]


def known(game) -> list[XenoTech]:
    return [t for t in XENOTECH if is_known(game, t.id)]


def culture_standing(game, culture_id: str) -> tuple[int, int]:
    """(incorporated, total) for a culture — how far you have got with them."""
    techs = by_culture(culture_id)
    return sum(1 for t in techs if is_incorporated(game, t.id)), len(techs)


def dig_value(rng, quality: float, lab: bool) -> float:
    """What one excavation is worth, before anything else is applied."""
    lo, hi = DIG_YIELD
    base = rng.float(lo, hi) * (0.7 + quality * 0.6)
    return base * (1.5 if lab else 1.0)


def analyse_value(count: float, lab: bool, research_rate: float) -> float:
    """Study from taking `count` relics apart in a laboratory."""
    return count * XENOLITH_STUDY * (1.4 if lab else 0.8) * (1 + research_rate * 0.05)


def best_unfinished(game, culture_id: str | None = None) -> XenoTech | None:
    """The technology a dig or a purchase should feed, nearest completion first."""
    pool = [t for t in XENOTECH
            if not is_incorporated(game, t.id)
            and (culture_id is None or t.culture == culture_id)]
    if not pool:
        return None
    pool.sort(key=lambda t: (not prerequisites_met(game, t),
                             -(study_of(game, t.id) / max(1, t.study))))
    return pool[0]


__all__ = ["study_of", "is_incorporated", "is_known", "progress", "add_study",
           "incorporate", "settle", "bonuses", "incorporated", "known",
           "culture_standing", "dig_value", "analyse_value", "best_unfinished",
           "prerequisites_met", "ready_to_incorporate", "CULTURES",
           "CULTURES_BY_ID", "XENOTECH", "XENOTECH_BY_ID", "by_culture"]
