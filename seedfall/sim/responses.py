"""The Bloom answering back, and the choice between burning and looking.

Provocation is the middle of the arc: a running count of what you have cost it,
which it spends on growing harder, detaching masses and eventually coming after
the hull that has been doing the burning. Studying a mass is the other half —
the only way to learn anything from it is to leave it there a while longer.
"""

from __future__ import annotations

from ..data.responses import (DECAY_PER_DAY, PROVOCATION, RESPONSES,
                              RESPONSES_BY_ID, STUDY, STUDY_FLOOR)
from . import bloom as bloom_sim


def state(game):
    return bloom_sim.ensure(game)


def level(game) -> float:
    return float(getattr(state(game), "provocation", 0.0))


def fired(game) -> list:
    return list(getattr(state(game), "responses", []))


def provoke(game, kind: str, scale: float = 1.0) -> float:
    """Report something you did to it. Returns the new level."""
    st = state(game)
    if getattr(st, "provocation", None) is None:
        st.provocation = 0.0
    st.provocation += PROVOCATION.get(kind, 0.0) * scale
    return st.provocation


def decay(game, days: float) -> None:
    st = state(game)
    current = getattr(st, "provocation", 0.0) or 0.0
    st.provocation = max(0.0, current - DECAY_PER_DAY * days)


def growth_multiplier(game) -> float:
    """How much faster it grows for everything it has answered."""
    out = 1.0
    for rid in fired(game):
        response = RESPONSES_BY_ID.get(rid)
        if response:
            out *= response.growth
    return out


def hunting(game) -> bool:
    return any(RESPONSES_BY_ID[r].hunts for r in fired(game)
               if r in RESPONSES_BY_ID)


def pending(game) -> list:
    """Responses whose threshold has been passed and which have not fired."""
    done = set(fired(game))
    here = level(game)
    return [r for r in RESPONSES if r.at <= here and r.id not in done]


def check(game, rng) -> list[tuple[str, str]]:
    """Fire anything the provocation has earned. Returns log events."""
    st = state(game)
    if getattr(st, "responses", None) is None:
        st.responses = []
    events: list[tuple[str, str]] = []

    for response in pending(game):
        st.responses.append(response.id)
        events.append(("bad" if response.tint == "bad" else "warn",
                       f"{response.name}. {response.text}"))
        if response.adapts:
            worst = bloom_sim.worst_resisted(game)
            family = worst[0] if worst else None
            if family:
                bloom_sim.record_damage(game, family, 900)
                events.append(("warn", f"It has hardened against {family} "
                                       "work specifically."))
        for _ in range(response.instars):
            inst = bloom_sim._spawn_instar(game, rng)
            if inst is not None:
                st.instars.append(inst)
                if response.hunts:
                    inst.target_id = game.location_id
    return events


# ── studying a mass instead of burning it ──────────────────────────────────

def can_study(game, system) -> tuple[bool, str]:
    if system.bloom < STUDY_FLOOR:
        return False, "There is not enough growth here to learn anything from."
    if game.ship_stats.scan <= 0:
        return False, "Nothing fitted that could take a useful reading."
    return True, ""


def study_value(game, system) -> dict:
    mass = system.bloom
    return {"xenolith": STUDY.xenolith * mass * (1 + game.ship_stats.scan),
            "readings": STUDY.readings * mass * (1 + game.ship_stats.scan),
            "growth": STUDY.growth * mass}


def study(game, system) -> dict:
    """Take readings from a living mass. It grows while you watch.

    The tension the setting has always described and the game never made you
    feel: the thing worth understanding is the thing worth destroying, and you
    cannot do both to the same mass.
    """
    ok, why = can_study(game, system)
    if not ok:
        return {"ok": False, "why": why}

    from . import inquiry
    from .ship import add_cargo

    value = study_value(game, system)
    game.advance_days(9)
    if game.dead:
        return {"ok": True, "dead": True}

    add_cargo(game.ship, "xenolith", value["xenolith"])
    inquiry.add(game.research, "reading", value["readings"])
    system.bloom = min(1.0, system.bloom + value["growth"])
    game.discovered["anomalies"] = game.discovered.get("anomalies", 0) + 1
    game.add_log(
        f"Nine days alongside the mass at {system.name}: "
        f"{round(value['xenolith'])} t of xenolith and "
        f"{round(value['readings'])} of readings. It is larger than it was.",
        "good")
    return {"ok": True, **value}


def summary(game) -> dict:
    here = level(game)
    done = fired(game)
    upcoming = [r for r in RESPONSES if r.id not in done]
    return {"level": here, "fired": done,
            "next": upcoming[0] if upcoming else None,
            "growth": growth_multiplier(game), "hunting": hunting(game)}
