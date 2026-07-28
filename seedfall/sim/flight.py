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

from ..core.rng import RNG, hash_seed
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
    """A stable starting angle, derived rather than stored.

    Python randomises ``hash()`` of a string per process, so deriving the phase
    from it put every planet somewhere new on every launch — the same seed grew
    the same galaxy and then scattered its orbits. ``hash_seed`` is stable.
    """
    return (hash_seed(f"{body.id}|{body.name}") % 3600) / 3600.0 * math.tau


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

#: Inside this radius a leg is running through the star's heat, in AU.
HOT_RADIUS = 1.2


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


def _leg(au: float, burn: Burn, speed: float) -> tuple[int, int]:
    days = max(1, round((1.2 + au * 1.0) * burn.speed / max(0.3, speed)))
    fuel = round((0.4 + au * 0.5) * burn.fuel)
    if burn.fuel > 0:
        fuel = max(1, fuel)
    return days, fuel


def intercept(game, body, burn_id: str = "standard") -> dict:
    """Solve for where the target will be when you actually get there.

    A transfer quoted against where a body is *now* is a transfer to empty
    space: by arrival it has moved, and an inner body moves a long way. This
    iterates to a fixed point — guess a flight time, see where the body will be
    then, re-time the leg for that distance, repeat. It converges in a few
    passes because the correction shrinks each time.
    """
    burn = BURNS_BY_ID.get(burn_id, BURNS_BY_ID["standard"])
    speed = game.ship_stats.speed
    sx, sy = ship_position(game)
    days, fuel = _leg(distance_to(game, body), burn, speed)

    passes = 0
    for passes in range(1, 8):
        tx, ty = position(body, game.day + days)
        _legs, au = route(sx, sy, tx, ty)
        new_days, fuel = _leg(au, burn, speed)
        if abs(new_days - days) <= 0.5:
            days = new_days
            break
        days = new_days

    tx, ty = position(body, game.day + days)
    legs, au = route(sx, sy, tx, ty)
    nx, ny = position(body, game.day)
    return {"burn": burn, "au": au, "days": days, "fuel": fuel,
            "aim": (tx, ty), "arrival_day": game.day + days,
            "lead": math.hypot(tx - nx, ty - ny), "passes": passes,
            "legs": legs, "detour": au - math.hypot(tx - sx, ty - sy),
            "risk": burn.risk + min(0.10, au * 0.012) + _heat_risk(sx, sy, tx, ty)}


def quote(game, body, burn_id: str = "standard") -> dict:
    """Days and reaction mass for a transfer, aimed where the body will be."""
    return intercept(game, body, burn_id)


def _closest_approach(sx: float, sy: float, tx: float, ty: float) -> float:
    """How near the star the straight leg passes, in AU."""
    dx, dy = tx - sx, ty - sy
    span = dx * dx + dy * dy
    if span <= 1e-9:
        return math.hypot(sx, sy)
    t = max(0.0, min(1.0, -(sx * dx + sy * dy) / span))
    return math.hypot(sx + dx * t, sy + dy * t)


def route(sx: float, sy: float, tx: float, ty: float) -> tuple[list, float]:
    """The legs actually flown, and their total length in AU.

    You cannot fly through a star. When the direct line would pass inside the
    hot radius — which it does for any target on the far side of the system —
    the helm bends the course around it, and the detour is what an opposite
    conjunction costs you. Reaching a body that genuinely lives down there is
    still allowed: the clearance never closes tighter than the destination.
    """
    clear = min(HOT_RADIUS, math.hypot(sx, sy), math.hypot(tx, ty))
    near = _closest_approach(sx, sy, tx, ty)
    direct = math.hypot(tx - sx, ty - sy)
    if near >= clear or clear <= 1e-6:
        return [(sx, sy), (tx, ty)], direct

    # Push the tightest point of the leg out to the clearance radius. If it
    # runs dead through the star there is no side to favour, so take the
    # perpendicular and go around the short way.
    mx, my = _closest_point(sx, sy, tx, ty)
    length = math.hypot(mx, my)
    if length < 1e-6:
        mx, my = -(ty - sy), (tx - sx)
        length = math.hypot(mx, my) or 1.0
    wx, wy = mx / length * clear, my / length * clear
    legs = [(sx, sy), (wx, wy), (tx, ty)]
    total = math.hypot(wx - sx, wy - sy) + math.hypot(tx - wx, ty - wy)
    return legs, total


def _closest_point(sx: float, sy: float, tx: float, ty: float) -> tuple[float, float]:
    dx, dy = tx - sx, ty - sy
    span = dx * dx + dy * dy
    if span <= 1e-9:
        return sx, sy
    t = max(0.0, min(1.0, -(sx * dx + sy * dy) / span))
    return sx + dx * t, sy + dy * t


def _heat_risk(sx: float, sy: float, tx: float, ty: float) -> float:
    """Working close to the star is hot however carefully you route."""
    deep = min(math.hypot(sx, sy), math.hypot(tx, ty))
    if deep >= HOT_RADIUS:
        return 0.0
    return min(0.18, (HOT_RADIUS - deep) * 0.16)


def path_note(game, body, burn_id: str = "standard") -> str | None:
    """A warning about the leg itself, if it deserves one."""
    q = intercept(game, body, burn_id)
    notes = []
    if q["detour"] > 0.05:
        notes.append(f"The star is in the way: the course bends around it, "
                     f"adding {q['detour']:.2f} AU.")
    sx, sy = ship_position(game)
    deep = min(math.hypot(sx, sy), math.hypot(*q["aim"]))
    if deep < HOT_RADIUS:
        notes.append(f"You will be working {deep:.2f} AU from the star. The "
                     "radiators will not enjoy it and neither will the crew.")
    return " ".join(notes) or None


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
