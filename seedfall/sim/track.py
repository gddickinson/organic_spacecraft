"""Contacts in a system: where they have been, where they will be, and how to meet them.

The helm could plot a transfer to a *body* — `flight.intercept` solves the lead
properly, iterating to a fixed point because a body has moved by the time you
arrive. Nothing else in a system could be aimed at: not the traffic, not an
anchorage, not a point of empty space you simply wanted to be at.

This generalises it. Everything in a system is a `Contact` with a position that
is a function of the day, so a track can be drawn backwards as well as forwards
and a burn can be solved for an arrival *date* rather than only for "as soon as
possible".

What is and is not known:

* **Bodies** run on circular orbits with a stable phase, so their past and
  future are exact arithmetic.
* **Traffic** is deterministic too — `traffic.in_system` is seeded on the
  system and the slot, and a hull's position is a triangle wave in the day —
  but only *while it keeps its errand*. Errands are drawn against the sector's
  state, so a quay falling to the Bloom or a war starting can put a hull on a
  different leg. A forecast says so rather than pretending.

Every cost quoted here comes back through `flight`: the same `route` that bends
a leg around the star and the same `_leg` that prices it. A plot that disagreed
with what flying actually charges would be worse than no plot.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import anchorage as anchorage_sim
from . import knock as knock_sim
from ..data.starclasses import mu_of
from . import flight
from . import traffic as traffic_sim

#: How far ahead a forecast is offered by default, in days.
HORIZON = 180

#: What a hull's plot is worth once the Bloom has reshuffled its system's
#: traffic. Not a decay curve — a measurement. Over 735 forecasts across ten
#: chronicles, four systems and horizons out to 270 days, **99.9% came true to
#: the digit**; every failure was the growth crossing one of the thresholds in
#: `traffic` below and redrawing the errands. So a plot is firm until that
#: crossing and soft after it, which is a thing a captain can act on — unlike
#: a number that merely falls with time.
SHUFFLED_CONFIDENCE = 0.35

#: The growth at which `traffic` changes its mind. `_busyness` drops a hull
#: from a system over 0.2; `hostile_ok` lets raiders draw over 0.15. Read from
#: there rather than guessed, and held to it by a check.
SHUFFLE_AT = (0.15, 0.2)


@dataclass(frozen=True)
class Contact:
    """Something in a system that can be tracked and flown to."""

    id: str
    name: str
    kind: str                 # star | body | anchorage | hull | point
    tint: str
    detail: str = ""
    body_index: int | None = None
    hull_id: str | None = None
    at_xy: tuple | None = None      # for a bare point in space
    hostile: bool = False
    #: For an anchorage, what sort: quay, hub, holding or gate. A screen
    #: should not have to read an id to know whether it is looking at a
    #: shipyard or at something older than the Charter.
    berth: str = ""
    #: And for a hull, what it is out here doing — the same idea, and the same
    #: reason. `sim/traffic.ERRANDS` names them. Without it the sky knew a
    #: contact was "a hull" and nothing else, so a patrol boat, a courier and
    #: an ore prospector were drawn with one mesh — and it was the shipyard's.
    errand: str = ""

    @property
    def predictable(self) -> bool:
        """Does this contact hold to arithmetic, or can it change its mind?"""
        return self.kind in ("star", "body", "anchorage", "point")


def _system(game, system=None):
    return system if system is not None else game.system


def contacts(game, system=None) -> list[Contact]:
    """Everything in a system worth putting a cursor on."""
    system = _system(game, system)
    out = [Contact(id="star", name=system.star_name or "the star",
                   kind="star", tint="warn", detail="The primary.")]
    for index, body in enumerate(system.bodies):
        out.append(Contact(
            id=f"body:{index}", name=body.name, kind="body",
            tint=getattr(body, "tint", "") or "chloro",
            detail=f"{body.kind.title()} · orbit "
                   f"{flight.orbit_radius(body):.2f} AU",
            body_index=index))
    for place in anchorage_sim.in_system(game, system):
        # An anchorage's position *is* its body's, which is why `flight`
        # needs no special case for one and neither does this.
        out.append(Contact(
            id=f"quay:{place.id}", name=place.name, kind="anchorage",
            tint="warn" if place.kind == "gate" else "lumen",
            detail=place.what or place.kind.title(),
            body_index=place.body_index, berth=place.kind))
    for hull in traffic_sim.in_system(game, system):
        out.append(Contact(
            id=f"hull:{hull.id}", name=hull.name, kind="hull",
            tint="warn" if hull.hostile else "steel",
            detail=f"{hull.kind_name} — {hull.doing}",
            hull_id=hull.id, hostile=hull.hostile, errand=hull.errand))
    return out


def at(game, contact: Contact, day: float, system=None) -> tuple[float, float]:
    """Where a contact is, in AU, on a given absolute day.

    Nominal place plus whatever it has been shoved by. `sim/knock.py` holds
    the shoves; adding them *here* is what makes a struck quay actually off
    station — on the plot, in an approach, in the readiness board's ranges and
    in every forecast — rather than only in the log line about hitting it.
    A body and a star are not shoved by anything a captain can fly into them,
    which is what `impulse.WORLD_MASS_T` already says, so neither is asked.
    """
    system = _system(game, system)
    if contact.kind == "star":
        return 0.0, 0.0
    if contact.at_xy is not None:
        return contact.at_xy
    if contact.kind in ("body", "anchorage") and contact.body_index is not None:
        x, y = flight.position(system.bodies[contact.body_index], day,
                               mu_of(system))
        if contact.kind == "anchorage":
            dx, dy = knock_sim.offset(game, contact.id, day)
            return x + dx, y + dy
        return x, y
    if contact.kind == "hull":
        x, y = _hull_at(game, contact, day, system)
        dx, dy = knock_sim.offset(game, contact.id, day)
        return x + dx, y + dy
    return 0.0, 0.0


def _hull_at(game, contact: Contact, day: float, system):
    """A hull's position on a day, read the way `traffic` reads it.

    `traffic.in_system` is pure in the system and the day, so asking it about
    a future day *is* the forecast — no second model to drift out of step with
    the first.
    """
    shifted = _AsOf(game, day)
    for hull in traffic_sim.in_system(shifted, system):
        if hull.id == contact.hull_id:
            return traffic_sim.position(shifted, hull, system)
    return at(game, Contact(id="star", name="", kind="star", tint=""), day,
              system)


class _AsOf:
    """The game as it would be on another day, for asking `traffic` about it.

    Everything `traffic.in_system` reads — the day, the systems, the sector's
    state — is read through the game, so a thin stand-in with a different day
    is the whole of what a forecast needs. It is deliberately not a copy: a
    forecast must never be able to write to the chronicle.
    """

    __slots__ = ("_game", "day")

    def __init__(self, game, day: float) -> None:
        self._game = game
        self.day = day

    def __getattr__(self, name):
        if name in ("rng",):
            raise AttributeError(
                "a forecast may not draw on the chronicle's luck")
        return getattr(self._game, name)


def bloom_at(game, system, day: float) -> float:
    """What the growth in a system will be on a day, at its present rate.

    `threat.tick` compounds by `(0.025 + bloom * 0.035) * stage.growth` every
    `SPREAD_INTERVAL`, less whatever a picket burns back. This walks the same
    arithmetic forward without touching the chronicle — it is a projection for
    the plotting board, not a second growth model.
    """
    from . import bloom as bloom_sim
    from .colony import ward_at
    from .threat import SPREAD_INTERVAL

    here = getattr(system, "bloom", 0.0)
    if here <= 0.02 or day <= game.day:
        return here
    stage = bloom_sim.ensure(game).definition
    ward = ward_at(game, system.id)
    for _tick in range(int((day - game.day) / SPREAD_INTERVAL)):
        here = max(0.0, min(1.0, here
                            + (0.025 + here * 0.035) * stage.growth * (1 - ward)
                            - ward * (0.020 + here * 0.030)))
    return here


def confidence(game, contact: Contact, arrive_day: float, system=None) -> float:
    """How much to trust a plot against this contact, 0..1.

    Bodies keep their word: an orbit is arithmetic. A hull keeps its word
    until the growth in its system crosses a threshold that makes `traffic`
    redraw the errands — so what this asks is whether that crossing falls
    before the arrival, not merely how far off the arrival is.
    """
    if contact.predictable:
        return 1.0
    system = _system(game, system)
    now = getattr(system, "bloom", 0.0)
    later = bloom_at(game, system, arrive_day)
    for edge in SHUFFLE_AT:
        if now <= edge < later:
            return SHUFFLED_CONFIDENCE
    # Already past every threshold: the traffic is being redrawn continuously,
    # and a raider is likelier the worse it gets.
    if now > max(SHUFFLE_AT):
        return SHUFFLED_CONFIDENCE
    return 1.0


def path(game, contact: Contact, start: float, end: float,
         steps: int = 40, system=None) -> list[tuple[float, float]]:
    """The contact's positions across a span of days."""
    if steps < 2:
        steps = 2
    span = end - start
    return [at(game, contact, start + span * (i / (steps - 1)), system)
            for i in range(steps)]


def history(game, contact: Contact, days: float = 90.0, steps: int = 30,
            system=None) -> list[tuple[float, float]]:
    """Where it has been, back to `days` ago (never before the chronicle)."""
    back = max(0.0, game.day - days)
    return path(game, contact, back, game.day, steps, system)


def forecast(game, contact: Contact, days: float = HORIZON, steps: int = 30,
             system=None) -> list[tuple[float, float]]:
    """Where it will be, if nothing changes its mind."""
    return path(game, contact, game.day, game.day + days, steps, system)


def _risk(game, burn, au: float, start, target) -> float:
    """The same sum `flight.intercept` quotes, so the two cannot drift apart."""
    return (burn.risk + min(flight.LONG_LEG_CAP, au * flight.PER_AU)
            + flight._heat_risk(*start, *target) + flight.hot_risk(game))


def solve(game, contact: Contact, burn_id: str = "standard",
          arrive_day: float | None = None, system=None) -> dict:
    """What it takes to be where this contact is, now or on a chosen day.

    With no `arrive_day` this is the soonest meeting: iterate a guessed
    flight time against where the contact will be then, exactly as
    `flight.intercept` does for a body — and for a body it *is*
    `flight.intercept`, so the helm and the plot cannot disagree.

    With one, it is a rendezvous: the leg is measured to where the contact
    will be on that date, and the burn either reaches it in time or does not.
    """
    system = _system(game, system)
    burn = flight.BURNS_BY_ID.get(burn_id, flight.BURNS_BY_ID["standard"])
    if (arrive_day is None and contact.kind in ("body", "anchorage")
            and contact.body_index is not None):
        quoted = flight.intercept(game, system.bodies[contact.body_index],
                                  burn_id)
        return {**quoted, "contact": contact, "feasible": True,
                "arrive_day": quoted["arrival_day"],
                "confidence": 1.0, "wait": 0.0}

    speed = game.ship_stats.speed
    start = flight.ship_position(game)

    if arrive_day is None:
        days = 1.0
        for _pass in range(8):
            target = at(game, contact, game.day + days, system)
            _legs, au = flight.route(*start, *target)
            fresh, _fuel = flight._leg(au, burn, speed)
            if abs(fresh - days) <= 0.5:
                days = fresh
                break
            days = fresh
        arrive = game.day + days
    else:
        arrive = max(game.day, float(arrive_day))

    target = at(game, contact, arrive, system)
    legs, au = flight.route(*start, *target)
    need_days, fuel = flight._leg(au, burn, speed)
    available = arrive - game.day
    feasible = need_days <= available + 1e-6
    return {
        "contact": contact, "burn": burn, "au": au,
        "days": need_days, "fuel": fuel, "aim": target, "legs": legs,
        "arrive_day": arrive, "wait": max(0.0, available - need_days),
        "feasible": feasible, "risk": _risk(game, burn, au, start, target),
        "short_by": max(0.0, need_days - available),
        "confidence": confidence(game, contact, arrive, system),
        "lead": math.hypot(*(t - s for t, s in
                             zip(target, at(game, contact, game.day, system)))),
    }


def windows(game, contact: Contact, burn_id: str = "standard",
            horizon: float = HORIZON, count: int = 12,
            system=None) -> list[dict]:
    """Rendezvous dates across a horizon, cheapest reachable ones first.

    A moving target is not equally dear on every day. Waiting for a hull to
    come back down its leg, or for a body to swing round to your side, is
    often worth more than burning harder — which is the whole reason to plot
    against a date instead of against *now*.
    """
    if count < 2:
        count = 2
    soonest = solve(game, contact, burn_id, None, system)
    first = max(1.0, soonest.get("days", 1.0))
    out = []
    for index in range(count):
        share = index / (count - 1)
        arrive = game.day + first + (horizon - first) * share
        if arrive <= game.day:
            continue
        out.append(solve(game, contact, burn_id, arrive, system))
    return out


def cheapest(game, contact: Contact, burn_id: str = "standard",
             horizon: float = HORIZON, system=None) -> dict | None:
    """The least reaction mass this contact can be met for inside a horizon."""
    live = [w for w in windows(game, contact, burn_id, horizon, 16, system)
            if w["feasible"]]
    return min(live, key=lambda w: w["fuel"]) if live else None
