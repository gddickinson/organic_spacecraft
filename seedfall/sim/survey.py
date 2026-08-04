"""Performing a survey, and saying what each way of doing it will get you.

Surveying was one button: three days, no cost, no risk, and the same kind of
answer for a comet as for an ocean world. Meanwhile thirteen sensor fittings
and a drone technology existed only to nudge a single `scan` float.

Four methods now, and they are not a ladder — each can see some things and not
others. `preview()` states what a method will cost and, more importantly,
**what it cannot find**, which is the part that makes choosing one a decision.
`test_surveys` performs each and compares.
"""

from __future__ import annotations

import math

from ..data.surveys import CATEGORIES, DEFAULT, METHODS, METHODS_BY_ID
from ..world.planets import survey_body
from . import biology
from . import flight
from . import charts as chart_sim
from . import inquiry
from . import research as research_sim
from .crew import grant_xp
from .ship import add_cargo, cargo_free


def _held(game, commodity: str) -> float:
    return (game.ship.cargo.get(commodity, 0)
            + game.stores.get(commodity, 0))


def reach(game) -> float:
    """How far you can see from where you are.

    Your own array, plus any listening post watching this system. Three colony
    classes advertise sensor reach and `colony.effects` has always tallied it
    per system — nothing ever read the tally, because until surveys the number
    decided nothing. A dish spread across one system does not help you three
    jumps away, which is why this is not folded into `ship_stats`.
    """
    here = (game.colony_fx.get("sensor_by_system", {})
            .get(game.system.id, 0.0) if game.colony_fx else 0.0)
    return max(0.5, game.ship_stats.sensor + here)


def reach_to(game, body) -> float:
    """How far the body is, in the units the sensor rating is quoted in."""
    aim = flight.intercept(game, body, "standard")["aim"]
    # All three: a body on an inclined orbit is genuinely above or below
    # you, and a range worked in two of them quietly reads short.
    return math.dist(aim, flight.ship_position(game))


def work_days(game, method) -> int:
    """The looking itself, sharpened by how good the instruments are."""
    return max(1, round(method.days * (1.35 - 0.5 * game.ship_stats.scan)))


def flight_days(game, method, body) -> int:
    """Getting there, on the profile the ship will actually use.

    On the profile the ship will actually use — see `_profile`.
    """
    burn = _profile(game, method, body)
    return burn["days"] if burn else 0


def _profile(game, method, body):
    """The burn `flight.ensure_at` will actually use, and its quote.

    Returns None when no flight is involved. `ensure_at` drops to a coast when
    there is not enough reaction mass for a standard burn, so forecasting the
    standard burn regardless promised twelve days for a fourteen-day trip.
    """
    if not method.alongside or game.orbit_body == body.id:
        return None
    standard = flight.quote(game, body, "standard")
    if game.ship.cargo.get("volatiles", 0) >= standard["fuel"]:
        return standard
    return flight.quote(game, body, "coast")


def full_cost(game, method, body) -> dict:
    """Everything the method consumes, including getting there.

    The method's own bill is the sounding charges. Flying the hull alongside
    burns reaction mass on top, and a card that quoted four tonnes for a job
    that took seven is the same defect this project keeps finding: a screen
    offering a commitment without stating its consequence.
    """
    cost = dict(method.cost)
    burn = _profile(game, method, body)
    if burn and burn.get("fuel"):
        cost["volatiles"] = cost.get("volatiles", 0) + burn["fuel"]
    return cost


def days_for(game, method, body) -> int:
    """Everything the method will spend: the flight and the looking.

    Kept separate above because `perform` must not spend the flight twice —
    `flight.ensure_at` already advances the clock for it, and adding the whole
    span afterwards charged a close pass eleven days for a seven-day job.
    """
    return work_days(game, method) + flight_days(game, method, body)


def available(game, body) -> list:
    """Every method, whether it can be used here, and why not if not."""
    out = []
    for method in METHODS:
        ok, why = True, ""
        if method.needs_tech and method.needs_tech not in game.research.unlocked:
            ok, why = False, f"Needs {method.needs_tech}."
        elif game.ship_stats.scan < method.needs_scan:
            ok = False
            why = (f"Wants a scan rating of {method.needs_scan:.2f}; yours is "
                   f"{game.ship_stats.scan:.2f}.")
        elif not method.alongside and method.id == "sweep":
            span, far = reach_to(game, body), reach(game)
            if span > far:
                ok = False
                # Quote `reach`, not the raw stat: they can differ at the floor,
                # and a refusal that cites a number it did not use is a lie.
                # Two decimals — at the boundary both rounded to the same
                # figure and the refusal read as a contradiction.
                why = (f"{span:.2f} AU away and your array reaches "
                       f"{far:.2f}.")
        if ok:
            for commodity, amount in method.cost.items():
                if _held(game, commodity) < amount:
                    ok = False
                    why = (f"Short of {commodity}: needs {amount:g}, you have "
                           f"{_held(game, commodity):.0f}.")
                    break
        out.append((method, ok, why))
    return out


def preview(game, body, method_id: str) -> dict:
    """What this way of looking will cost, and what it will and will not see.

    The second half is the point. A method that cannot find a buried site has
    to say so *before* you spend nine days not finding one.
    """
    method = METHODS_BY_ID.get(method_id)
    if method is None:
        return {}
    blind = [c for c in CATEGORIES if c not in method.finds]
    return {
        "method": method,
        "days": days_for(game, method, body),
        "cost": full_cost(game, method, body),
        "flies": method.alongside and game.orbit_body != body.id,
        "finds": list(method.finds),
        "blind": blind,
        "quality": round(min(1.0, game.ship_stats.scan * method.quality), 3),
    }


def look_bonus(game, body) -> float:
    """What the ship's orbit height is worth to a survey of this body.

    One, unless the ship is actually holding an orbit around the body being
    surveyed — a chart of somewhere you are not standing is not improved by
    how close you are standing to somewhere else.
    """
    from .orbits import look_factor
    held = float(getattr(game, "orbit_alt_km", 0.0) or 0.0)
    if held <= 0 or game.orbit_body != body.id:
        return 1.0
    return look_factor(float(getattr(body, "radius_km", 0.0)), held)


def perform(game, body_index: int, method_id: str = DEFAULT) -> dict:
    """Survey a body the chosen way. Returns what turned up."""
    method = METHODS_BY_ID.get(method_id)
    if method is None:
        return {"ok": False, "why": "No such survey."}
    body = game.system.bodies[body_index]
    ok, why = next(((o, w) for m, o, w in available(game, body)
                    if m.id == method_id), (False, "Unavailable."))
    if not ok:
        return {"ok": False, "why": why}

    span = days_for(game, method, body)
    if method.alongside:
        flight.ensure_at(game, body_index)     # spends the flight itself
    for commodity, amount in method.cost.items():
        taken = min(amount, game.ship.cargo.get(commodity, 0))
        add_cargo(game.ship, commodity, -taken)
        if taken < amount:
            game.stores[commodity] = max(
                0.0, game.stores.get(commodity, 0) - (amount - taken))
    game.advance_days(work_days(game, method))

    # How close you are holding is part of how well you see. The other half
    # of the trade the orbit height buys: a low orbit resolves about a fifth
    # more than a standard one and costs about a seventh more to leave.
    quality = min(1.0, game.ship_stats.scan * method.quality * look_bonus(game, body))
    found = survey_body(body, quality, game.rng("survey"), finds=method.finds)
    # Priced for the captain who found it, not for the body it was on.
    found["catch"] = biology.harvest(game, found["lifeforms"])
    found["research"] += found["catch"]["research"]
    found["ok"] = True
    found["method"] = method
    found["days"] = span

    research_sim.grant(game.research, found["research"])
    inquiry.add(game.research, "survey", found["research"] * 0.9)
    inquiry.add(game.research, "specimen", len(found["lifeforms"]) * 9)
    grant_xp(game.officers, "science", 25, game=game)

    free = cargo_free(game.ship, game.ship_stats)
    data = min(found["data"], int(free / 0.1))
    if data > 0:
        add_cargo(game.ship, "survey", data)

    # Dating the chart the day it was finished, which is what lets it go
    # stale. This lived only in `actions.survey`, the single-method call the
    # four survey methods replaced — and the screen calls *this* one. So no
    # chart was ever stamped, `freshness` returned 1.0 for ever, and
    # `FRESH_DAYS` and `STALE_FLOOR` decided nothing at all: a chart made in
    # year one sold in year ten for the same money.
    system = game.system
    system.scanned = bool(system.bodies) and all(b.surveyed
                                                 for b in system.bodies)
    if system.scanned:
        chart_sim.stamp(game, system)
    return found


def watching(game) -> float:
    """Extra reach a listening post in this system is lending you."""
    return (game.colony_fx.get("sensor_by_system", {})
            .get(game.system.id, 0.0) if game.colony_fx else 0.0)


def note(game, body) -> str:
    """One line for the screen: what this body still has left to give up."""
    if not body.surveyed:
        return "Nothing has looked at this properly yet."
    missing = []
    if body.relic and not body.relic_found:
        missing.append("something under the surface")
    if any(not lf.catalogued for lf in body.lifeforms):
        missing.append("life nobody has catalogued")
    if body.anomaly and not body.anomaly.found:
        missing.append("something that does not fit")
    if not missing:
        return "Surveyed, and it has nothing further to say."
    return "Surveyed — but a deeper look might still turn up " + \
        ", ".join(missing) + "."
