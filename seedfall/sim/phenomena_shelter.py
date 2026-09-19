"""Shelter from a flare: the ship's position against the star.

A flare is light, and light is stopped by mass. Four answers, in the order a
captain would reach for them:

- **At a berth** — alongside a quay, a hub or a holding of yours: the
  structure's own mass stands between the crew and the star. All of it.
- **In a body's lee** — holding at a body and keeping station on its night
  side (`keep_lee`), which costs reaction mass a day while there is something
  to hide from (`data/phenomena.LEE_FUEL`). All of it, while the mass lasts.
- **Holding orbit** — a hull going round a world spends part of each orbit
  behind it: `asin(R / r) / π` of it, which is about a third at a standard
  orbit of an Earth-sized world, nearly half at a low one, and nothing worth
  the name at a comet.
- **Free space** — the geometry itself, off `flight.ship_position`: inside a
  body's umbra, or out in the light. A conn flown into a shadow is sheltered.

`of` is read by `phenomena.dose`, the Sky strip and the Pilot and Helm
screens' indicator, so what the screen says is what the crew takes.
"""

from __future__ import annotations

import math

from ..data import phenomena as data
from ..data.starclasses import mu_of
from ..data.starclasses import of as star_of
from .orbits import KM_PER_AU


def of(game) -> dict:
    """How much of a flare the hull is out of, and why."""
    here = _held(game)
    if here is not None:
        berth = _berth(game)
        if berth:
            return {"share": 1.0, "how": "berth", "by": berth,
                    "text": f"Alongside {berth}: the berth's mass stands "
                            "between the crew and the star."}
        sky = getattr(game, "sky", None)
        if (sky is not None and sky.lee == here.id
                and game.ship.cargo.get("volatiles", 0.0) >= data.LEE_FUEL):
            return {"share": 1.0, "how": "lee", "by": here.name,
                    "text": f"Keeping station in the shadow of {here.name}."}
        share = orbit_shade(game, here)
        return {"share": share, "how": "orbit", "by": here.name,
                "text": f"Holding orbit at {here.name}: behind it "
                        f"{round(share * 100)}% of each orbit."}
    body = _umbra(game)
    if body is not None:
        return {"share": 1.0, "how": "shadow", "by": body.name,
                "text": f"In the shadow of {body.name}."}
    return {"share": 0.0, "how": "", "by": "",
            "text": "In the open, with nothing between the crew and the star."}


def _held(game):
    body_id = getattr(game, "orbit_body", None)
    if body_id is None:
        return None
    return next((b for b in game.system.bodies if b.id == body_id), None)


def _berth(game) -> str:
    from . import anchorage
    for place in anchorage.in_system(game):
        if place.here and place.kind in ("quay", "hub", "holding"):
            return place.name
    return ""


def orbit_shade(game, body) -> float:
    """Share of an orbit spent behind the body it goes round."""
    from .orbits import DEFAULT_HEIGHT, height_km
    radius = float(getattr(body, "radius_km", 0.0) or 0.0)
    held = float(getattr(game, "orbit_alt_km", 0.0) or 0.0)
    if held <= 0:
        held = height_km(radius, DEFAULT_HEIGHT)
    if radius <= 0 or held <= 0:
        return 0.0
    return math.asin(min(1.0, radius / held)) / math.pi


def _umbra(game):
    """The body whose shadow the hull is in, in free space, or None."""
    from . import flight
    at = flight.ship_position(game)
    star_km = star_of(game.system).radius_km
    mu = mu_of(game.system)
    for body in game.system.bodies:
        pos = flight.position(body, game.day, mu)
        if in_umbra(at, pos, body.radius_km, star_km):
            return body
    return None


def in_umbra(ship, body, body_km: float, star_km: float) -> bool:
    """Is a point behind a body, inside the cone its shadow makes?"""
    far = math.sqrt(sum(c * c for c in body))
    if far <= 0:
        return False
    axis = tuple(c / far for c in body)
    rel = tuple(s - b for s, b in zip(ship, body))
    along = sum(r * a for r, a in zip(rel, axis))
    if along <= 0:
        return False
    across = math.sqrt(max(0.0, sum(r * r for r in rel) - along * along))
    radius = body_km / KM_PER_AU
    if star_km > body_km:
        # The umbra is a cone: it closes `far · R / (R* − R)` behind the body.
        length = far * body_km / (star_km - body_km)
        radius *= max(0.0, 1.0 - along / length)
    return across < radius


def lee_quote(game) -> dict:
    """Whether the hull can keep to a shadow here, and what it costs."""
    body = _held(game)
    if body is None:
        return {"ok": False, "why": "Not alongside anything to hide behind.",
                "fuel": 0.0}
    if of(game)["how"] in ("berth", "lee"):
        return {"ok": False, "why": "Already out of the light.", "fuel": 0.0}
    if game.ship.cargo.get("volatiles", 0.0) < data.LEE_FUEL:
        return {"ok": False, "why": "No reaction mass to keep station on.",
                "fuel": data.LEE_FUEL}
    return {"ok": True, "why": "", "fuel": data.LEE_FUEL, "body": body.name}


def keep_lee(game) -> dict:
    """Keep station in the shadow of the body the hull is holding at."""
    said = lee_quote(game)
    if not said["ok"]:
        return said
    from .phenomena import state
    state(game).lee = game.orbit_body
    text = (f"Keeping to the shadow of {said['body']}: "
            f"{data.LEE_FUEL:g} t of reaction mass a day while there is "
            "something to hide from.")
    game.add_log(text, "")
    return {**said, "text": text}


def spend_lee(game, days: float) -> float:
    """Pay for a day in the lee while a flare is live. Returns tonnes."""
    if of(game)["how"] != "lee" or days <= 0:
        return 0.0
    from .ship import add_cargo
    burn = min(game.ship.cargo.get("volatiles", 0.0), data.LEE_FUEL * days)
    add_cargo(game.ship, "volatiles", -burn)
    return burn
