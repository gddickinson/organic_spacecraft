"""Loyalty — how the bridge feels about the way you run the ship.

Everything here hangs off one call. `record()` reports something the ship did;
each officer feels it through their own convictions, and the number that comes
out changes how well they hold a station and whether they stay at all. Nothing
else needs to know which officer believes what.
"""

from __future__ import annotations

from ..data.convictions import (BANDS, CEILING, CONVICTIONS, CONVICTIONS_BY_ID,
                                FLOOR, RESTLESS, START, UNIVERSAL, WALKOUT)


def conviction_of(officer):
    return CONVICTIONS_BY_ID.get(getattr(officer, "conviction", None) or "")


def loyalty_of(officer) -> float:
    """Officers from older saves signed on before anyone asked them."""
    value = getattr(officer, "loyalty", None)
    return START if value is None else value


def band(officer) -> tuple[str, str]:
    value = loyalty_of(officer)
    out = BANDS[0]
    for edge, name, tint in BANDS:
        if value >= edge:
            out = (edge, name, tint)
    return out[1], out[2]


def shift(officer, delta: float) -> float:
    officer.loyalty = max(FLOOR, min(CEILING, loyalty_of(officer) + delta))
    return officer.loyalty


def feels(officer, event: str) -> float:
    """How much this one officer cares about this event."""
    total = UNIVERSAL.get(event, 0.0)
    conviction = conviction_of(officer)
    if conviction is not None:
        total += conviction.reacts.get(event, 0.0)
    return total


def record(game, event: str, scale: float = 1.0) -> list[tuple]:
    """Report something the ship did. Returns (officer, delta) for those who felt it."""
    moved = []
    for officer in getattr(game, "officers", []):
        delta = feels(officer, event) * scale
        # **No dead-band**, and this is tidying rather than the fix. There
        # was one at 0.005, which looked like the reason `tick` carried a
        # `max(0.25, ...)` floor on its scale — a threshold that swallows a
        # thirtieth of a month's credit would certainly need one. Measured, it
        # does not: `feels` is large enough that a thirtieth still clears
        # 0.005, so putting the dead-band back changes nothing. It goes anyway
        # because an arbitrary threshold on a rate is what this whole class of
        # defect is made of, but the floor above was the thing that mattered.
        if not delta:
            continue
        shift(officer, delta)
        moved.append((officer, delta))
    return moved


def served(game, faction: str | None, scale: float = 1.0) -> list[tuple]:
    """The ship did a power's work. Its partisans aboard take it personally.

    Each of the four convictions with a cause has a signature event —
    `licence_served`, `free_served` and so on — worth more to them than
    anything else they believe, and **nothing ever recorded one**. A Charter
    partisan could spend a decade running Charter commissions and feel it only
    as the same `commission_done` everybody else felt.

    Only convictions with an `aligned` power are reachable this way, which is
    the two that have one. The other two are served by burning the Bloom and
    by studying xenotech, and those events already fire.
    """
    if not faction:
        return []
    moved = []
    for conviction in CONVICTIONS:
        if conviction.aligned != faction:
            continue
        event = f"{conviction.id}_served"
        if event not in conviction.reacts:
            continue
        for officer in getattr(game, "officers", []):
            if conviction_of(officer) is not conviction:
                continue
            delta = conviction.reacts[event] * scale
            shift(officer, delta)
            moved.append((officer, delta))
    return moved


def align(game, faction: str, delta: float) -> None:
    """Standing with a power drags its partisans along with it."""
    for officer in getattr(game, "officers", []):
        conviction = conviction_of(officer)
        if conviction is not None and conviction.aligned == faction:
            shift(officer, delta * 0.25)


# ── what it buys you, and what it costs ────────────────────────────────────

def effective_level(officer) -> float:
    """The level an officer actually works at.

    A devoted officer gives you more than they are paid for; a restless one is
    going through the motions. This is the number the crew stations read, so
    loyalty is felt at the helm rather than only on a roster screen.
    """
    value = loyalty_of(officer)
    if value >= 85:
        factor = 1.2
    elif value >= 68:
        factor = 1.08
    elif value >= RESTLESS:
        factor = 1.0
    elif value >= WALKOUT:
        factor = 0.72
    else:
        factor = 0.45
    return officer.level * factor


def restless(game) -> list:
    return [o for o in getattr(game, "officers", [])
            if WALKOUT <= loyalty_of(o) < RESTLESS]


def walkouts(game) -> list:
    """Officers who have had enough. They are removed from the roster."""
    leaving = [o for o in getattr(game, "officers", [])
               if loyalty_of(o) < WALKOUT]
    for officer in leaving:
        game.officers = [o for o in game.officers if o.id != officer.id]
    return leaving


#: How far loyalty is pulled toward the ship's mood each day.
#:
#: Deliberately weak — see `drift`. Applied as a compounding rate so that a
#: month asked for in one call and a month asked for a day at a time land in
#: the same place.
DRIFT_PER_DAY = 0.0022


def drift(game, days: float) -> None:
    """Loyalty creeps toward the ship's mood when nothing else happens.

    Deliberately weak. A strong pull here flattens every officer onto the same
    number within a year and throws away the convictions entirely — what you
    did has to matter more than the ambient weather.
    """
    target = 40 + getattr(game.ship, "morale", 0.7) * 32
    # **Compounding, not linear**, and this too is tidying rather than the
    # fix. A pull of 0.22% *a day* over `days` is `1 - (1 - r)**days`, and the
    # old `min(0.35, r * days)` was neither — but the gap it caused is small:
    # thirty separate days came to 6.40% against 6.60% for one call of thirty,
    # about 0.13 of a point on an officer. Worth having because the
    # compounding form composes exactly and saturates on its own, so the
    # ceiling it used to need is gone; not worth claiming as the repair.
    pull = 1.0 - (1.0 - DRIFT_PER_DAY) ** max(0.0, days)
    for officer in getattr(game, "officers", []):
        value = loyalty_of(officer)
        officer.loyalty = value + (target - value) * pull


def tick(game, days: float, paid: bool) -> list[tuple[str, str]]:
    """The daily pass. Returns log events."""
    events: list[tuple[str, str]] = []
    if not getattr(game, "officers", []):
        return events
    # A payday is a monthly thing, so a span is that many paydays — no floor,
    # or a day at a time credits a full month's worth thirty times over. The
    # ceiling stays: it is what stops one enormous jump swamping a career, and
    # with the span chopped (#116) it is never reached.
    record(game, "payday" if paid else "missed_pay",
           scale=min(3.0, days / 30))
    drift(game, days)

    for officer in walkouts(game):
        events.append(("bad", f"{officer.name} has left the ship at the first "
                              "port that would take them."))
    for officer in restless(game):
        if getattr(officer, "_warned", False):
            continue
        officer._warned = True
        events.append(("warn", f"{officer.name} wants a word about how things "
                               "are being run."))
    for officer in getattr(game, "officers", []):
        if loyalty_of(officer) >= RESTLESS:
            officer._warned = False
    return events


def summary(game) -> dict:
    officers = getattr(game, "officers", [])
    if not officers:
        return {"mean": 0.0, "restless": 0, "count": 0}
    values = [loyalty_of(o) for o in officers]
    return {"mean": sum(values) / len(values),
            "restless": len([v for v in values if v < RESTLESS]),
            "count": len(officers)}


def assign(rng, officer) -> None:
    """Give a new officer something to believe, weighted by what they do."""
    leaning = {
        "science": ("xenophile", "licence"),
        "nav": ("free", "shipmate"),
        "engineer": ("builder", "shipmate"),
        "tactical": ("burner", "purse"),
        "medical": ("shipmate", "licence"),
        "quartermaster": ("purse", "free"),
    }
    pool = leaning.get(officer.role, ())
    if pool and rng.chance(0.6):
        officer.conviction = rng.pick(list(pool))
    else:
        officer.conviction = rng.pick([c.id for c in CONVICTIONS])
    officer.loyalty = START + rng.float(-8, 8)
