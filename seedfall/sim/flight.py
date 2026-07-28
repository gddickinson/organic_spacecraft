"""The helm — moving inside a system.

A jump puts you at the edge of a system, not next to the thing you came to look
at. Bodies are on real orbits that keep moving while you do, so the distance to
a target depends on when you leave, and the burn you choose trades reaction mass
against days. Nothing here is arcade: you plot a transfer, you commit, and the
sky is somewhere else when you arrive.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.rng import RNG
from .ship import add_cargo, apply_damage

#: Orbital radius in AU for a body's normalised orbit slot (0 inner, 1 outer).
R_INNER, R_OUTER = 0.4, 9.0

#: Days for a one-AU circular orbit, scaled by Kepler's third law from there.
YEAR_AT_1AU = 365.0


@dataclass(frozen=True)
class Burn:
    id: str
    name: str
    speed: float     # multiplier on transit time (lower is faster)
    fuel: float      # multiplier on reaction mass
    risk: float      # extra chance of something going wrong
    blurb: str


BURNS = [
    # Coasting is always available and always free. Without it a captain with an
    # empty tank could not even reach the ice that would refill it, which is the
    # deadlock the distress beacon exists to catch.
    Burn("coast", "Coast", 3.20, 0.00, 0.06,
         "Let the orbit do the work. It costs nothing but the calendar, and "
         "the calendar is not free."),
    Burn("economy", "Economy transfer", 1.55, 0.55, 0.00,
         "A minimum-energy arc. Cheap, slow, and the textbook answer."),
    Burn("standard", "Standard transfer", 1.00, 1.00, 0.04,
         "The burn the flight plan assumes. Nobody writes home about it."),
    Burn("hard", "Hard burn", 0.58, 2.10, 0.14,
         "Throw reaction mass at the problem. The crew will feel it and the "
         "radiators will complain."),
]
BURNS_BY_ID = {b.id: b for b in BURNS}


def orbit_radius(body) -> float:
    return R_INNER + (R_OUTER - R_INNER) * body.orbit


def period_days(body) -> float:
    r = orbit_radius(body)
    return max(30.0, YEAR_AT_1AU * (r ** 1.5))


def _phase(body) -> float:
    """A stable starting angle, derived rather than stored."""
    return (hash((body.name, body.id)) % 3600) / 3600.0 * math.tau


def position(body, day: int) -> tuple[float, float]:
    """Where a body is, in AU, on a given day."""
    r = orbit_radius(body)
    angle = _phase(body) + math.tau * (day / period_days(body))
    return r * math.cos(angle), r * math.sin(angle)


def separation(a, b, day: int) -> float:
    """AU between two bodies right now."""
    ax, ay = position(a, day)
    bx, by = position(b, day)
    return math.hypot(ax - bx, ay - by)


#: Where a jump leaves you: inside the system, not beyond its outermost orbit.
#: Parking at the true edge taxed every first survey with a long transfer and
#: made the early game knife-edge.
ARRIVAL_RADIUS = R_OUTER * 0.45


def ship_position(game) -> tuple[float, float]:
    """Where the ship is: at a body, or holding where the jump left you."""
    body = current_body(game)
    if body is not None:
        return position(body, game.day)
    return 0.0, -ARRIVAL_RADIUS


def current_body(game):
    if not game.orbit_body:
        return None
    return next((b for b in game.system.bodies if b.id == game.orbit_body), None)


def distance_to(game, body) -> float:
    sx, sy = ship_position(game)
    bx, by = position(body, game.day)
    return math.hypot(sx - bx, sy - by)


def quote(game, body, burn_id: str = "standard") -> dict:
    """Days and reaction mass for a transfer, at the chosen burn."""
    burn = BURNS_BY_ID.get(burn_id, BURNS_BY_ID["standard"])
    au = distance_to(game, body)
    speed = max(0.3, game.ship_stats.speed)
    days = max(1, round((1.2 + au * 1.0) * burn.speed / speed))
    fuel = round((0.4 + au * 0.5) * burn.fuel)
    if burn.fuel > 0:
        fuel = max(1, fuel)
    return {"burn": burn, "au": au, "days": days, "fuel": fuel,
            "risk": burn.risk + min(0.10, au * 0.012)}


def options(game, body) -> list[dict]:
    return [quote(game, body, b.id) for b in BURNS]


def travel_to(game, body_index: int, burn_id: str = "standard") -> dict:
    """Fly to a body. Spends days and reaction mass; may go wrong."""
    body = game.system.bodies[body_index]
    if game.orbit_body == body.id:
        return {"ok": True, "already": True, "days": 0, "fuel": 0, "body": body}

    q = quote(game, body, burn_id)
    have = game.ship.cargo.get("volatiles", 0)
    if have < q["fuel"]:
        return {"ok": False,
                "why": f"That burn needs {q['fuel']} t of reaction mass; you "
                       f"have {int(have)}. You can always coast."}

    add_cargo(game.ship, "volatiles", -q["fuel"])
    game.advance_days(q["days"])
    if game.dead:
        return {"ok": True, "dead": True}
    game.orbit_body = body.id

    out = {"ok": True, "already": False, "days": q["days"], "fuel": q["fuel"],
           "body": body, "burn": q["burn"], "incident": None}
    r = game.rng("burn")
    if r.chance(q["risk"]):
        out["incident"] = _incident(game, r, q["burn"])
    game.add_log(f"{q['burn'].name} to {body.name}: {q['days']} days, "
                 f"{q['fuel']} t of reaction mass.", "")
    return out


_INCIDENTS = [
    ("Dust at closing speed", "A stream of grains the survey did not plot. The "
     "epidermis takes it, which is what it is for.", "damage"),
    ("Radiator flutter", "A bloom lobe fails to deploy cleanly and the hull runs "
     "hot for a week.", "heat"),
    ("Attitude fault", "The platform drifts mid-burn and the correction costs "
     "reaction mass nobody budgeted.", "fuel"),
    ("Debris field", "Somebody else's bad day, spread across four hundred "
     "kilometres of the approach.", "damage"),
]


def _incident(game, rng, burn: Burn) -> dict:
    name, text, effect = rng.pick(_INCIDENTS)
    detail = ""
    if effect == "damage":
        dmg = rng.int(10, 40)
        apply_damage(game.ship, dmg)
        detail = f"{dmg} points off the hull."
    elif effect == "heat":
        game.ship.heat += rng.int(10, 26)
        detail = "The hull is running hot."
    else:
        lost = rng.int(2, 8)
        add_cargo(game.ship, "volatiles", -min(lost, game.ship.cargo.get("volatiles", 0)))
        detail = f"{lost} t of reaction mass gone."
    game.add_log(f"{name}: {detail}", "warn")
    return {"name": name, "text": text, "detail": detail}


def ensure_at(game, body_index: int) -> dict:
    """Fly to a body if we are not already there, on the standard profile.

    Local work — surveying, digging, landing — assumes the ship is alongside.
    Actions call this so a player who never opens the helm still gets a
    coherent transit, and the helm remains the place to choose a better one.
    """
    body = game.system.bodies[body_index]
    if game.orbit_body == body.id:
        return {"ok": True, "already": True, "days": 0, "fuel": 0}
    q = quote(game, body, "standard")
    if game.ship.cargo.get("volatiles", 0) >= q["fuel"]:
        return travel_to(game, body_index, "standard")
    return travel_to(game, body_index, "coast")


def arrive_in_system(game) -> None:
    """A jump drops you at the edge, not alongside anything."""
    game.orbit_body = None
