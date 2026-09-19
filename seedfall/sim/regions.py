"""What a region of the sky does to a hull in it — one rule, one function.

The Far Reaches play differently, and each difference is a single function
here, read by the one system it affects and measured by an efficacy check
that switches it off (`tests/test_reaches.py`):

- **The Shoals** blind you: `sensor_scale` (read by `sim/detection`,
  `sim/survey.reach` and the conn's array) and `survey_scale` (the survey's
  resolution), and nobody's law reaches — `lawless`, read by
  `sim/piracy.lawlessness`.
- **The Hollow** is dark: `lit` is false alongside a sunless body, and a
  grown hull's intima makes no air there (`core/shiptime.aboard`).
- **The Cradle** irradiates: `irradiate` takes a dose off the crew's morale
  and puts heat into the hull every day aboard (`core/shiptime.hull`),
  less behind shielding (`Stats.crew_guard`) and a melanised rind.

**A small API for later waves** — the Kith, phenomena, officer arcs, renown:
`region_of(system)`, `opened(game)` and `rule(game, system, key)`. A new
rule is a row in `data/regions.RULES` and a reader; nothing here changes.
"""

from __future__ import annotations

from ..data.regions import (DOSE_MORALE, DOSE_TECH, DOSE_TECH_CUT, HEAT_SHARE,
                            NEUTRAL, REGIONS, RULES, VERGE)


def region_of(system) -> str:
    """Which region a system is in: "verge", "shoals", "hollow" or "cradle"."""
    return getattr(system, "region", VERGE) or VERGE


def opened(game) -> list[str]:
    """The regions relit so far, in the order they were opened."""
    return [r.id for r in getattr(game.galaxy, "regions", ()) or ()]


def rule(game, system, key: str) -> float:
    """What a region says about `key` where `system` is (here, if None).

    The Verge's value (`data/regions.NEUTRAL`) wherever a region does not say
    otherwise, so a reader can multiply or add unconditionally.
    """
    where = game.system if system is None else system
    table = RULES.get(region_of(where), {})
    return float(table.get(key, NEUTRAL.get(key, 0.0)))


def names(game) -> dict:
    """Region id -> display name, the Verge included, for a screen."""
    out = {VERGE: "The Verge"}
    out.update({spec.id: spec.name for spec in REGIONS})
    return out


# ── the Shoals: blind, and lawless ─────────────────────────────────────────

def sensor_scale(game) -> float:
    """What the nebula leaves of the array's reach, where the hull is."""
    return rule(game, None, "sensor")


def survey_scale(game) -> float:
    """What the nebula leaves of a survey's resolution, where the hull is."""
    return rule(game, None, "survey")


def lawless(game, system) -> float:
    """How much lawlessness a region adds to a system, on top of the rest."""
    return rule(game, system, "lawless")


def claimable(game, system) -> bool:
    """May a Verge power annex this ground? Not beyond the rim, for now: the
    Cradle is left for the Kith, and the powers' reach is the Verge's."""
    return rule(game, system, "claimable") > 0


# ── the Hollow: dark ───────────────────────────────────────────────────────

def _held_body(game):
    body_id = getattr(game, "orbit_body", None)
    if body_id is None:
        return None
    return next((b for b in game.system.bodies if b.id == body_id), None)


def light(game) -> float:
    """The star's heat on the hull — nothing at all alongside a rogue world.

    `System.heat` is what the generator lights a system's worlds with; a
    sunless body (`Body.sunless`, the Hollow's rogues) has no star-lit face,
    so a hull holding at one is in the dark whatever the star is doing.
    """
    body = _held_body(game)
    if body is not None and getattr(body, "sunless", False):
        return 0.0
    return float(getattr(game.system, "heat", 1.0) or 0.0)


def lit(game) -> bool:
    """Is there light for a grown hull's intima to make air with?"""
    return light(game) > 0.0


# ── the Cradle: a dose, and heat ───────────────────────────────────────────

def dose(game, stats=None) -> float:
    """Today's radiation, 0 (none) to 1 (an unshielded crew in the Cradle).

    Shielding the fittings already sell — `crew_guard`, from Dsup chromatin
    or a wake cradle — takes its own share off, and a melanised rind
    (`DOSE_TECH`) a further `DOSE_TECH_CUT` of what is left.
    """
    base = rule(game, None, "dose")
    if base <= 0:
        return 0.0
    return base * shield(game, stats)


def shield(game, stats=None) -> float:
    """What of a dose reaches this crew, 0 to 1 — the one door for it, read
    by the Cradle here and by a flare or the nova (`sim/phenomena.dose`)."""
    st = stats if stats is not None else game.ship_stats
    guard = max(0.0, min(0.95, float(getattr(st, "crew_guard", 0.0) or 0.0)))
    cut = DOSE_TECH_CUT if DOSE_TECH in game.research.unlocked else 0.0
    # And what the hull has grown for itself: a melanised rind or a glare
    # mantle (`sim/adaptation`) is the living answer to hard light.
    from .adaptation import dose_multiplier
    return (1.0 - guard) * (1.0 - cut) * dose_multiplier(game.ship)


def irradiate(game, days: float, stats) -> dict:
    """A day aboard in hard light: morale off the crew, heat into the hull.

    Called once a day from `core/shiptime.hull`, after the radiators have
    had their turn, so the heat reads on the gauge the way the crew feels it.
    """
    if days <= 0:
        return {"dose": 0.0, "heat": 0.0}
    taken = dose(game, stats) * days
    if taken > 0:
        ship = game.ship
        ship.morale = max(0.0, ship.morale - DOSE_MORALE * taken)
    # A floor under the hull's heat rather than a daily charge: the light is
    # always there, so the radiators never get her below it. A charge per day
    # stacked past what they shed — measured, an opening NAVIS cooked every
    # day and sat at the ceiling, twice its cap, by day sixty — which is a
    # hull being killed by a view. A floor is a hull that starts every fight and
    # every hard burn hot.
    floor = rule(game, None, "heat") * HEAT_SHARE
    added = 0.0
    if floor > 0:
        from .ship import add_heat
        cap = float(getattr(stats, "heat_cap", 40.0) or 40.0)
        if game.ship.heat < floor * cap:
            added = floor * cap - game.ship.heat
            add_heat(game.ship, added, cap)
    return {"dose": taken, "heat": added}
