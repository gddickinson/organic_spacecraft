"""The powers put people on the ground, and the ground starts producing.

At turn zero the sector held 161 bodies and **not one settlement**. Every power
owned orbital berths and nothing else; a world rich in phosphate was a number on
a survey screen. So "are there settlements on habitable worlds, and do they
trade?" had the answer no, twice.

A power with a surplus founds one now, out of the treasury (`sim/exchequer.py`),
on a body in a system it holds whose grades are worth working. It grows for a
couple of years, it pays its founder, and **the local market knows**: the good it
works gets commoner there and everything else its people eat gets scarcer, which
is what makes a settled system somewhere to carry cargo *to* as well as from.

The market effect goes through `industry.industrialise`, the single writer of
`Stock.works`. That field began as "what the holder of this berth was licensed to
make"; it means "what is made here" now, whoever is making it, because two
functions writing one number is how they come to disagree.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from ..core.save import register
from ..data.factions import FACTIONS_BY_ID
from ..data.settlements import (DEMAND, FOUND_COST, MATURE_DAYS, NEWBORN,
                                SUPPLY, UPKEEP, WORKABLE, WORTH_SETTLING,
                                YIELD)

_uid = itertools.count(1)


@register
@dataclass
class Settlement:
    """Somebody's people, on a body, working one thing."""
    id: int
    power: str
    system_id: int
    body_id: str
    #: The commodity the ground gives here. Chosen at founding from the body's
    #: own grades, so what a settlement is for is decided by where it is.
    good: str
    founded: int = 0


def held(game) -> list:
    if getattr(game, "settlements", None) is None:
        game.settlements = []
    return game.settlements


def in_system(game, system_id: int) -> list:
    return [s for s in held(game) if s.system_id == system_id]


def of_power(game, power: str) -> list:
    return [s for s in held(game) if s.power == power]


def on_body(game, system_id: int, body_id: str) -> object | None:
    """The settlement on one body, if there is one.

    **Both halves of the key.** `Body.id` is the body's index *within its
    system* — 155 bodies in a sector share six distinct ids — so a lookup on
    `body_id` alone matches a body in every system at once. The first draft did
    that, and six settlements masked the entire sector: `sites_for` went from
    twenty-odd candidates per power to **zero** in the first year, and the
    powers never settled anything again. `Colony` has keyed on the pair since it
    was written, which is the precedent I should have read.
    """
    return next((s for s in held(game)
                 if s.system_id == system_id and s.body_id == body_id), None)


# ── where one could go ─────────────────────────────────────────────────────

def grade_of(body, good: str) -> float:
    return float((getattr(body, "resources", None) or {}).get(good, 0.0))


def worth_working(body) -> str | None:
    """The best thing this ground gives, or None if it gives nothing much.

    Ordered by `WORKABLE`, which puts the valuable concentrate first — a body
    that is rich in two things gets settled for the dearer one.
    """
    for good in WORKABLE:
        if grade_of(body, good) >= WORTH_SETTLING:
            return good
    return None


def sites_for(game, power: str) -> list[tuple[object, object, str]]:
    """Every `(system, body, good)` this power could settle, best grade first.

    Only in systems it holds, only on bodies nobody has taken, and only where
    the ground is worth the trouble. `Body.colony` is the *player's* colony id
    and is left alone: a power settling a body the captain has planted on would
    be a land dispute, and this is not the cycle that models one.
    """
    out = []
    for system in game.galaxy.systems:
        if getattr(system, "faction", None) != power:
            continue
        for body in system.bodies:
            if (body.colony is not None
                    or on_body(game, system.id, body.id) is not None):
                continue
            good = worth_working(body)
            if good is None:
                continue
            out.append((system, body, good))
    out.sort(key=lambda row: (-grade_of(row[1], row[2]), row[1].id))
    return out


# ── founding, growing, earning ─────────────────────────────────────────────

def found(game, system, body, power: str) -> object | None:
    """Put people on this body. Returns the settlement, or None if it cannot."""
    if body.colony is not None or on_body(game, system.id, body.id) is not None:
        return None
    good = worth_working(body)
    if good is None:
        return None
    made = Settlement(id=next(_uid), power=power, system_id=system.id,
                      body_id=body.id, good=good, founded=game.day)
    held(game).append(made)
    # The market has to hear about it, and only one function tells it.
    from . import industry
    industry.industrialise(game, system)
    return made


def maturity(game, settlement) -> float:
    """How much of its output this settlement manages, `NEWBORN`..1."""
    age = max(0, game.day - settlement.founded)
    share = min(1.0, age / MATURE_DAYS)
    return NEWBORN + (1.0 - NEWBORN) * share


def yield_of(game, settlement) -> float:
    """What it pays its founder a day, net of what holding it costs."""
    return YIELD * maturity(game, settlement) - UPKEEP


def payback_days() -> float:
    """How long a settlement takes to earn back what founding it cost.

    **Counting the years it loses money**, which is the part a mature-yield
    figure misses. A settlement manages `NEWBORN` of its output on the day it is
    founded, and at 25% of 46 a day against 14 of upkeep that is **−2.5 a day**:
    it costs its founder money until it is about a third grown. Measured, two
    fresh settlements moved a power's income *down*, from 724 a day to 720.

    So the honest figure integrates the ramp rather than dividing the cost by the
    mature rate — 1,000 days by that reckoning against **1,485** in fact, which
    is the difference between settling looking better than founding a berth and
    looking worse. `exchequer.payback` reads this, so the choice a power makes is
    made on the true number.
    """
    day_one = YIELD * NEWBORN - UPKEEP
    grown = YIELD - UPKEEP
    if grown <= 0:
        return float("inf")
    # Cumulative over the ramp: the average of the two rates, for MATURE_DAYS.
    banked = (day_one + grown) * 0.5 * MATURE_DAYS
    if banked >= FOUND_COST:
        # It pays for itself before it finishes growing; solve the quadratic.
        rate = (grown - day_one) / MATURE_DAYS
        from math import sqrt
        return (-day_one + sqrt(day_one ** 2 + 2 * rate * FOUND_COST)) / rate
    return MATURE_DAYS + (FOUND_COST - banked) / grown


def income(game, power: str) -> float:
    return sum(yield_of(game, s) for s in of_power(game, power))


# ── what the market makes of it ────────────────────────────────────────────

def supply_at(game, system) -> dict:
    """The multipliers this system's settlements put on its market.

    Read by `industry.industrialise`, which owns `Stock.works`. Two effects and
    both matter: what they work gets commoner, and everything else they eat gets
    scarcer, so a settled system is a place to carry cargo *to*.
    """
    here = in_system(game, system.id)
    if not here:
        return {}
    out: dict = {}
    for settlement in here:
        grown = maturity(game, settlement)
        lift = 1.0 + (SUPPLY - 1.0) * grown
        out[settlement.good] = out.get(settlement.good, 1.0) * lift
    made = {s.good for s in here}
    for good in WORKABLE:
        if good in made:
            continue
        # One eater's worth per settlement, so a busy system is hungrier.
        out[good] = out.get(good, 1.0) * (DEMAND ** len(here))
    return out


# ── what the screens read ──────────────────────────────────────────────────

def note(game, settlement) -> str:
    """One line: whose it is, what it works, how far along."""
    power = FACTIONS_BY_ID.get(settlement.power)
    grown = maturity(game, settlement)
    years = max(0, game.day - settlement.founded) / 365.0
    stage = ("newly planted" if grown < 0.4 else
             "established" if grown < 0.95 else "long settled")
    return (f"{power.short if power else settlement.power} · works "
            f"{settlement.good} · {stage}"
            + (f", {years:.0f} years in" if years >= 1 else ""))


def summary(game) -> dict:
    got = held(game)
    return {
        "count": len(got),
        "powers": sorted({s.power for s in got}),
        "systems": len({s.system_id for s in got}),
        "goods": sorted({s.good for s in got}),
        "cost": FOUND_COST,
    }
