"""What you know about a system, and how sure you are of it.

Knowing where a star is is not the same as knowing what is in it, and neither
is the same as having charted it. The registry sells the first, a sensor pass
or a bought chart gives the second, being there gives the third, and surveying
every body in it gives the fourth — which is the only one worth anything to a
buyer, and the reason to go back to somewhere you have already been.

Levels are derived from what the galaxy already records, plus a set of bought
charts, so nothing has to be kept in step by hand.
"""

from __future__ import annotations

from ..world.galaxy import distance

#: Rising order. The index is the intel level.
LEVELS = [
    ("Catalogued", "dim",
     "A name, a position and a body count the registry will not stand behind."),
    ("Scanned", "osteo",
     "Read at range or bought as a chart. The bodies are real; what is on them "
     "is guesswork."),
    ("Visited", "lumen",
     "You have been there. What the port trades and who holds it are known."),
    ("Charted", "chloro",
     "Every body surveyed. Complete, saleable, and worth the trip back."),
]
MAX_LEVEL = len(LEVELS) - 1


def ensure(game) -> set:
    """Charts bought rather than flown. Created on first use for old saves."""
    charts = getattr(game, "charts", None)
    if charts is None:
        charts = []
        game.charts = charts
    return charts


def survey_fraction(system) -> float:
    if not system.bodies:
        return 1.0
    return sum(1 for b in system.bodies if b.surveyed) / len(system.bodies)


def in_sensor_range(game, system) -> bool:
    here = game.system
    return distance(system, here) <= game.ship_stats.sensor


def level(game, system) -> int:
    """How well this system is known, 0..3."""
    if system.bodies and all(b.surveyed for b in system.bodies):
        return 3
    if system.visited:
        return 2
    if system.id in ensure(game) or in_sensor_range(game, system):
        return 1
    return 0


def label(game, system) -> tuple[str, str]:
    name, tint, _blurb = LEVELS[level(game, system)]
    return name, tint


def blurb(game, system) -> str:
    return LEVELS[level(game, system)][2]


def chart_price(game, system) -> int:
    """What a broker wants for the survey they already hold."""
    base = 900 + len(system.bodies) * 260
    if system.port:
        base += 400
    return int(base * (1.0 - min(0.3, game.ship_stats.trade)))


def buy_chart(game, system) -> dict:
    """Buy somebody else's scan rather than flying out to make your own."""
    if level(game, system) >= 1:
        return {"ok": False, "why": "You already have at least this much."}
    price = chart_price(game, system)
    if game.credits < price:
        return {"ok": False, "why": f"They want {price:,} credits for it."}
    game.credits -= price
    ensure(game).append(system.id)
    game.add_log(f"Bought the chart for {system.name}.", "good")
    return {"ok": True, "price": price}


# ── what a charted sector is worth ─────────────────────────────────────────

def sellable(game) -> list:
    """Systems charted but not yet sold to anybody."""
    sold = getattr(game, "charts_sold", None)
    if sold is None:
        sold = []
        game.charts_sold = sold
    return [s for s in game.galaxy.systems
            if s.id not in sold and level(game, s) >= 3]


def survey_value(game, system, faction: str | None = None) -> int:
    """What a complete chart of this system fetches from `faction`.

    Priced by what is in the system rather than by how many bodies it has —
    see `sim/charts.py`. The flat rate this used to be made a chart of a system
    with a buried site in it worth the same as five bare rocks, and both worth
    about a fiftieth of any other hour of the game.
    """
    from . import charts as chart_sim
    return chart_sim.value_to(game, system, faction)


def sell_survey(game, system, faction: str | None) -> dict:
    if level(game, system) < 3:
        return {"ok": False, "why": "That system is not fully charted."}
    sold = getattr(game, "charts_sold", None)
    if sold is None:
        sold = game.charts_sold = []
    if system.id in sold:
        return {"ok": False, "why": "You have already sold that survey."}
    value = survey_value(game, system, faction)
    game.credits += value
    sold.append(system.id)
    if faction:
        game.adjust_rep(faction, 2)
    game.add_log(f"Sold the {system.name} survey for {value:,} credits.", "good")
    return {"ok": True, "value": value}


def summary(game) -> dict:
    counts = [0, 0, 0, 0]
    for system in game.galaxy.systems:
        counts[level(game, system)] += 1
    return {"counts": counts, "total": len(game.galaxy.systems),
            "charted": counts[3], "unknown": counts[0]}
