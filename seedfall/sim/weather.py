"""The front overhead, and what it costs to move under it.

Weather is held on the expedition rather than on the body, because it is a
condition of *this* trip: it rolls in and out over the days you are down there
and is gone when you lift.
"""

from __future__ import annotations

from ..data.weather import (CLEAR, FRONT_DAYS, TURNOVER, WEATHERS,
                            WEATHERS_BY_ID)


def current(exp):
    """What it is doing right now."""
    return WEATHERS_BY_ID.get(getattr(exp, "weather", None) or "", CLEAR)


def days_left(exp) -> int:
    return max(0, getattr(exp, "weather_until", 0) - exp.days)


def _eligible(biome: str | None) -> list:
    out = []
    for weather in WEATHERS:
        if weather.biomes and biome not in weather.biomes:
            continue
        out.append(weather)
    return out


def set_front(exp, weather_id: str, days: int) -> None:
    exp.weather = weather_id
    exp.weather_until = exp.days + days


def roll(exp, rng, biome: str | None = None) -> str | None:
    """Turn the weather over if it is due. Returns the new condition's id."""
    if days_left(exp) > 0:
        return None
    pool = _eligible(biome)
    weather = rng.weighted([(w.weight, w) for w in pool]) if pool else CLEAR
    if weather.id == getattr(exp, "weather", "clear"):
        # Same again: extend rather than announce it twice.
        set_front(exp, weather.id, rng.int(*FRONT_DAYS))
        return None
    set_front(exp, weather.id, rng.int(*FRONT_DAYS))
    return weather.id


def tick(exp, days: int, rng, biome: str | None = None) -> str | None:
    """Advance the sky by a spell of days. Returns a new condition, if any."""
    changed = None
    for _ in range(max(1, days)):
        if days_left(exp) <= 0 or rng.chance(TURNOVER):
            got = roll(exp, rng, biome)
            changed = got or changed
    return changed


# ── what it does to you ────────────────────────────────────────────────────

def move_cost(exp, base: int) -> int:
    return max(1, base + current(exp).cost)


def danger(exp, base: float) -> float:
    return min(0.92, base * current(exp).danger)


def sight(exp) -> int:
    return current(exp).sight


def pinned(exp) -> bool:
    return current(exp).pinned


def shelter(exp, rng) -> dict:
    """Sit it out. Costs a day and shortens the front."""
    weather = current(exp)
    exp.days += 1
    exp.supply -= 1
    exp.weather_until = min(getattr(exp, "weather_until", 0), exp.days + 1)
    return {"ok": True, "weather": weather}


def note(exp) -> str:
    weather = current(exp)
    if weather.id == "clear":
        return weather.blurb
    left = days_left(exp)
    tail = (f" Expected to hold another {left} day(s)." if left
            else " It is starting to break.")
    return weather.blurb + tail
