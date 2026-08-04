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

from ..data.starclasses import SOLAR_MU, mu_of
from . import elements
from .ship import add_cargo, add_heat, apply_damage, cook

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
    #: Heat the burn leaves in the hull. The hard burn's blurb promised the
    #: radiators would complain and nothing ever happened; the four profiles
    #: collapsed to "always hard burn", because saving nineteen days cost about
    #: three hundred credits of reaction mass and 1.2% of a hull that heals.
    heat: float = 0.0


BURNS = [
    # Coasting is always available and always free. Without it a captain with an
    # empty tank could not even reach the ice that would refill it, which is the
    # deadlock the distress beacon exists to catch.
    Burn("coast", "Coast", 3.20, 0.00, 0.06,
         "Let the orbit do the work. It costs nothing but the calendar, and "
         "the calendar is not free."),
    Burn("economy", "Economy transfer", 1.55, 0.55, 0.00,
         "A minimum-energy arc. Cheap, slow, and the textbook answer.",
         heat=0.06),
    Burn("standard", "Standard transfer", 1.00, 1.00, 0.04,
         "The burn the flight plan assumes. Nobody writes home about it.",
         heat=0.18),
    Burn("hard", "Hard burn", 0.58, 2.10, 0.14,
         "Throw reaction mass at the problem. The crew will feel it and the "
         "radiators will complain — and you arrive hot, which matters if "
         "anybody is waiting.",
         heat=0.62),
]
BURNS_BY_ID = {b.id: b for b in BURNS}


def semi_major(body) -> float:
    """The long half-axis of this body's orbit, in AU.

    Was `orbit_radius`, and the rename is the point: an orbit no longer
    *has* a radius. `body.orbit` places the ellipse; `sim/elements` gives it
    a shape, a tilt and a direction, and how far the body actually is from
    the star is now a question about a day (`distance_from_star`).
    """
    return R_INNER + (R_OUTER - R_INNER) * body.orbit


def period_days(body, star_mu: float) -> float:
    """A body's year, in days. Kepler's third law, with the mass put back.

    `T = 2π·sqrt(a³/mu)`, so `T ∝ a^1.5 / sqrt(M)`. The `sqrt(M)` was missing:
    the game had one period function for the whole sector and it quietly
    assumed every star weighed exactly one Sun. A world at one AU took the
    same year round a 0.32-solar M dwarf as round an A-type nearly six times
    heavier, when the real difference is a factor of 2.4 — visible on the helm
    chart, in every launch window, and in where anything is on any given day.

    `star_mu` is required rather than defaulted on purpose. A default is how
    half the call sites end up quietly assuming the Sun while the other half
    do it properly, which is the same two-doors-disagreeing fault this file
    has been bitten by before.
    """
    r = semi_major(body)
    scale = math.sqrt(SOLAR_MU / max(star_mu, 1.0))
    return max(30.0, YEAR_AT_1AU * (r ** 1.5) * scale)


def elements_of(body) -> elements.Elements:
    """This body's orbit. **One door**, so nothing derives a second one.

    Six elements where there used to be a radius. They are not stored: see
    `sim/elements`, which draws them off a stable hash of the body's own
    identity, so an old chronicle grows real orbits the moment it is loaded
    and the save does not gain a byte.
    """
    return elements.of(body, semi_major(body))


def position(body, day: float, star_mu: float) -> tuple:
    """Where a body is, in AU, on a given day, round a star of this mass.

    **Three dimensions now, and not a circle.** This used to be
    `r·cos θ, r·sin θ` with a constant radius, which made every orbit in the
    game the same orbit: circular, in one shared plane, all going the same way
    round. A player looking at the plotting board said so, and they were
    right — there was nothing else to draw.
    """
    return elements.at(elements_of(body), day, period_days(body, star_mu))


def distance_from_star(body, day: float, star_mu: float) -> float:
    """How far out the body actually is today — which now varies over its
    year, and is the number `semi_major` used to be mistaken for."""
    return math.dist(position(body, day, star_mu), (0.0, 0.0, 0.0))


def separation(a, b, day: float, star_mu: float) -> float:
    """AU between two bodies right now."""
    return math.dist(position(a, day, star_mu), position(b, day, star_mu))


#: Where a jump leaves you: inside the system, not beyond its outermost orbit.
#: Parking at the true edge taxed every first survey with a long transfer and
#: made the early game knife-edge.
ARRIVAL_RADIUS = R_OUTER * 0.45

#: The line a leg takes and what standing on it costs live in `sim/path.py`,
#: split out when this file was a recorded length debt. They are imported for
#: this module's own quoting — `intercept` prices the route and the heat, and
#: `path_note` explains them — which is why the names stay reachable here for
#: the screens and checks that have always read them through `flight`.
from .path import (HOT_RADIUS, LONG_ENOUGH, LONG_LEG_CAP, PER_AU,  # noqa: E402
                   WORTH_SAYING, _heat_risk, burn_heat, hot_risk, route)


def ship_position(game) -> tuple[float, float]:
    """Where the ship is in this system, in AU. **The one door for reading it.**

    The sector has always been positioned — `track.at` gives every contact a
    place that moves with the calendar — and the ship was not. It had a body id
    or nothing, and "nothing" was a fixed point on the system's edge. So a
    captain sitting at the quay they started at measured four AU from it,
    `berthing.can_conn` refused every contact in the system, and the conn
    opened on nothing with controls that correctly did nothing.

    Two states, and only one of them is stored:

    - **Alongside a body** — the position *is* the body's, worked out fresh
      from the calendar. A hull in orbit is not parked in space: the world
      takes it with it, so a captain who moors and waits a month is still at
      the quay when they look up. Storing a copy here would be a second door
      that goes stale the moment the clock moves.
    - **Free space** — `game.ship_xy`, written by `stand_off`. A jump's
      arrival is the common case, and it used to be the *only* case, which is
      why "not alongside anything" meant "at one particular point on the edge".

    A save from before there was a position has neither, and falls through to
    that arrival point — which is exactly where it always thought it was.
    """
    body = current_body(game)
    if body is not None:
        return position(body, game.day, mu_of(game.system))
    where = getattr(game, "ship_xy", None)
    if where is not None:
        # A chronicle saved before orbits had a third dimension stored two
        # numbers here. Padding rather than refusing puts that hull exactly
        # where it always thought it was — on the plane, which is where every
        # orbit used to be.
        return (float(where[0]), float(where[1]),
                float(where[2]) if len(where) > 2 else 0.0)
    return 0.0, -ARRIVAL_RADIUS, 0.0


def hold_at(game, body) -> None:
    """Put the hull alongside a body: one of the two writers of where it is.

    Clears the free-space position, because keeping it would leave a stale
    second answer lying around for the next `stand_off` to pick up.
    """
    game.orbit_body = getattr(body, "id", body)
    game.ship_xy = None


def stand_off(game, at=None) -> None:
    """Hold station away from everything — a jump's arrival, or a departure.

    Takes the position it is to hold, so "not alongside anything" stops
    meaning "nowhere in particular". Defaults to the arrival radius, which is
    what a jump into a system means.
    """
    game.orbit_body = None
    game.ship_xy = (
        (float(at[0]), float(at[1]),
         float(at[2]) if len(at) > 2 else 0.0) if at is not None else None)


def current_body(game):
    if not game.orbit_body:
        return None
    return next((b for b in game.system.bodies if b.id == game.orbit_body), None)


def distance_to(game, body) -> float:
    return math.dist(ship_position(game),
                     position(body, game.day, mu_of(game.system)))


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
    here = ship_position(game)
    days, fuel = _leg(distance_to(game, body), burn, speed)

    # Bodies no longer move at one speed. On an eccentric orbit a world
    # hurries through perihelion and loiters at aphelion, so the correction
    # this iteration is chasing can be larger on one date than another — but
    # it still shrinks, and the aim below is read from the truth on the day
    # arrived at whether or not the loop converged.
    passes = 0
    for passes in range(1, 8):
        there = position(body, game.day + days, mu_of(game.system))
        _legs, au = route(here, there)
        new_days, fuel = _leg(au, burn, speed)
        if abs(new_days - days) <= 0.5:
            days = new_days
            break
        days = new_days

    there = position(body, game.day + days, mu_of(game.system))
    legs, au = route(here, there)
    now = position(body, game.day, mu_of(game.system))
    return {"burn": burn, "au": au, "days": days, "fuel": fuel,
            "aim": there, "arrival_day": game.day + days,
            "lead": math.dist(there, now), "passes": passes,
            "legs": legs, "detour": au - math.dist(here, there),
            "risk": (burn.risk + min(LONG_LEG_CAP, au * PER_AU)
                     + _heat_risk(here, there)
                     + hot_risk(game))}


def departure_factor(game) -> float:
    """What the orbit the ship is holding does to the cost of leaving it.

    Deeper in a well is dearer to climb out of: the speed you must find to
    escape is `sqrt(2·mu/r)`, so this is the square root of the ratio of the
    radii and `mu` cancels out. A low orbit runs about a seventh dearer than
    a standard one and a high orbit about a quarter cheaper — which is the
    price of the closer look a low orbit buys, and the whole reason the
    height is worth choosing.
    """
    from .orbits import departure_factor as by_radius
    body = current_body(game)
    held = float(getattr(game, "orbit_alt_km", 0.0) or 0.0)
    if body is None or held <= 0:
        return 1.0
    return by_radius(float(getattr(body, "radius_km", 0.0)), held)


def quote(game, body, burn_id: str = "standard") -> dict:
    """Days and reaction mass for a transfer, aimed where the body will be.

    The fuel carries the cost of climbing out of whatever orbit the ship is
    holding — in the *quote*, so the forecast the helm shows and the mass the
    transfer actually spends are the same number rather than two.
    """
    out = intercept(game, body, burn_id)
    lift = departure_factor(game)
    if out["fuel"] and lift != 1.0:
        out["fuel"] = max(1, round(out["fuel"] * lift))
    out["departure_lift"] = lift
    return out


def path_note(game, body, burn_id: str = "standard") -> str | None:
    """A warning about the leg itself, if it deserves one."""
    q = intercept(game, body, burn_id)
    notes = []
    # The distance surcharge. Found by a check asking the general question —
    # "does anything cost more than its profile without the screen saying
    # why" — rather than by looking for it: two surcharges had words written
    # for them and this third one never had.
    span = min(LONG_LEG_CAP, q["au"] * PER_AU)
    if span >= LONG_ENOUGH:
        notes.append(f"It is {q['au']:.1f} AU on this arc, which is "
                     f"+{span:.2f} on the risk before anything else"
                     + (" — as far as distance alone can make it."
                        if span >= LONG_LEG_CAP - 1e-9 else "."))
    if q["detour"] > 0.05:
        notes.append(f"The star is in the way: the course bends around it, "
                     f"adding {q['detour']:.2f} AU.")
    # Where you will be *working*, which is where you are going — not the
    # nearer of there and here. Taking the minimum meant a ship parked at 0.40
    # AU reported "you will be working 0.40 AU from the star" for every body
    # in the system, including one nine AU out that it was leaving the heat to
    # reach. A warning attached to a choice has to distinguish between the
    # choices, or it is furniture.
    deep = math.hypot(*q["aim"])
    if deep < HOT_RADIUS:
        notes.append(f"You will be working {deep:.2f} AU from the star. The "
                     "radiators will not enjoy it and neither will the crew.")
    else:
        # `_heat_risk` takes the *nearer* of the two ends, so a hull parked
        # deep pays the surcharge on every departure — including one nine AU
        # outward. Only the arrival half was ever explained, so a captain
        # sitting close in saw every burn on the board priced above its
        # profile with nothing on the screen accounting for it.
        here = math.hypot(*ship_position(game))
        if here < HOT_RADIUS:
            notes.append(f"You are starting {here:.2f} AU from the star, so "
                         "the first part of any burn out of here runs hot "
                         "whichever way you go.")
    # The heat already in the hull, which `hot_risk` charges against *every*
    # burn on the board. It was charged silently: a captain fresh off a run of
    # hard burns saw coast at 0.34 where the profile says 0.06, and nothing on
    # the screen accounted for the difference.
    cap = getattr(game.ship_stats, "heat_cap", 0) or 1
    share = game.ship.heat / cap
    if share >= WORTH_SAYING:
        added = hot_risk(game)
        notes.append(f"You are carrying {game.ship.heat:.0f} of heat against "
                     f"a rated {cap:.0f}. That is +{added:.2f} on every burn "
                     "here, this one included, until she sheds it."
                     + (" She is over the cap and cooking." if share > 1
                        else ""))
    return " ".join(notes) or None


def options(game, body) -> list[dict]:
    return [quote(game, body, b.id) for b in BURNS]


def travel_to(game, body_index: int, burn_id: str = "standard") -> dict:
    """Fly to a body. Spends days and reaction mass; may go wrong."""
    body = game.system.bodies[body_index]
    if game.orbit_body == body.id:
        return {"ok": True, "already": True, "days": 0, "fuel": 0, "body": body}

    # A live conn is settled before the hull is moved out from under it —
    # `berthing.secure_underway`, the same door `transit.begin` knocks on.
    from . import berthing as berth_sim
    berth_sim.secure_underway(game)

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
    hold_at(game, body)
    # The heat goes in on arrival, not departure: it is the braking burn that
    # leaves you hot. Adding it at the start let the radiators shed the lot
    # during the crossing, which is the opposite of the point.
    burnt = burn_heat(q["burn"], game.ship_stats)
    if burnt:
        add_heat(game.ship, burnt, game.ship_stats.heat_cap)
        # The same ceiling the guns work under. Without it a hurried captain
        # bouncing between two bodies reached 5.4x the cap, and every penalty
        # that scales with the excess — the daily cooking of the hull, and the
        # resolve loss the moment anybody shot at them — scaled with it.
        cook(game.ship, game.ship_stats.heat_cap)

    out = {"ok": True, "already": False, "days": q["days"], "fuel": q["fuel"],
           "body": body, "burn": q["burn"], "incident": None,
           "heat": round(burnt, 1), "hot": game.ship.heat > game.ship_stats.heat_cap}
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
        add_heat(game.ship, rng.int(10, 26), game.ship_stats.heat_cap)
        detail = "The hull is running hot."
    else:
        # Report what was actually taken, not what was rolled. A hull with
        # three tonnes aboard and an eight-tonne fault was told "8 t of
        # reaction mass gone" and had lost three — one in five of these.
        want = rng.int(2, 8)
        lost = min(want, game.ship.cargo.get("volatiles", 0))
        add_cargo(game.ship, "volatiles", -lost)
        detail = (f"{lost:g} t of reaction mass gone."
                  if lost > 0 else "The tank was already dry.")
    game.add_log(f"{name}: {detail}", "warn")
    return {"name": name, "text": text, "detail": detail}


def ensure_at(game, body_index: int) -> dict:
    """Fly to a body if we are not already there, on the standard profile.

    Local work — surveying, digging, landing — assumes the ship is alongside.
    Actions call this so a player who never opens the helm still gets a
    coherent transit, and the helm remains the place to choose a better one.
    """
    # **Local work is not done from the conn.** Every caller of this spends
    # days on the far side of it — a survey, a dig, an extraction, a landing
    # — and a captain cannot be hand-flying and running a nine-day deep
    # survey at the same time. The flight is secured and billed first
    # (through the one door), whether or not the ship has to move: measured,
    # a survey with a live free flight left the conn open with its own
    # elapsed while the world advanced three days around it.
    from . import berthing as berth_sim
    berth_sim.secure_underway(game)
    body = game.system.bodies[body_index]
    if game.orbit_body == body.id:
        return {"ok": True, "already": True, "days": 0, "fuel": 0}
    q = quote(game, body, "standard")
    if game.ship.cargo.get("volatiles", 0) >= q["fuel"]:
        return travel_to(game, body_index, "standard")
    return travel_to(game, body_index, "coast")


def arrive_in_system(game) -> None:
    """A jump drops you at the edge, not alongside anything."""
    stand_off(game)
