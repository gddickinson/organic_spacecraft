"""Where you may deal from, and what the distance costs.

A play-test asked the question this answers: **where can you trade from?**
The Port priced and bought for any hull anywhere in the system — survey data
sold at the Fleet Hub from seven AU out — while the shipyard wanted you
alongside and the berth lesson said the Port opens once you are. Three
counters, three rules, and one of them was no rule at all.

One rule now, and it is a ladder rather than a gate:

- **Alongside the quay** (`sim/crossing` made you fast to it), the counter is
  open and the cranes are theirs. Nothing here charges you a penny.
- **Anywhere else in this system**, the goods still have to cross the gap,
  and **the gap is what it costs**. Your own boat does it for nothing up to
  what she carries in a visit (`crossing.lift_t` — a DORY's nine tonnes, a
  WASP's one and a bit) and only within her own range; past that the port
  sends lighters, by the tonne, at a rate that rises with the distance. In
  orbit off the quay it is small change; from an AU out it is double; from
  the seven the play-test sold survey data at, it is eight times.
- **Anything that is not cargo** — handing over a bench of survey data, and
  whatever else is added to this door later — wants somebody actually at the
  counter: alongside, or ashore by boat, shuttle or line. That one is a rule
  rather than a price: a bench of sets is carried in by hand.

Mirrors `sim/wharfage.py` deliberately: `fee` is the only place the charge is
worked out, `may_move` the only place a refusal is decided, and `quote` is
what a screen asks so the board and the till cannot come apart.
"""

from __future__ import annotations

import math

#: What the port's lighters charge a tonne alongside-close, and the least a
#: run costs at all. The rate is multiplied by `1 + the distance in AU`, so
#: sitting where the quay can see you is cheap and sitting at the jump
#: radius is not.
LIGHTER_RATE, LIGHTER_LEAST = 7.0, 40


def berth_of(system) -> str:
    """The anchorage id of this system's quay."""
    return f"port-{system.id}" if getattr(system, "port", None) else ""


def alongside(game, system=None) -> bool:
    """Is the hull made fast to this system's quay?"""
    system = system or game.system
    berth = berth_of(system)
    return bool(berth) and getattr(game, "berth", "") == berth


def at_counter(game, system=None) -> tuple:
    """Is anybody at the counter? `(ok, why)`.

    Made fast alongside, or across to the port by whatever way
    (`sim/crossing`) — the crew being *there* is what this asks, which is
    what handing over a bench of survey sets takes.
    """
    system = system or game.system
    if not getattr(system, "port", None):
        return False, "No port here."
    if alongside(game, system):
        return True, ""
    place = f"port-{system.id}"
    if getattr(game, "ashore", "") == place:
        return True, ""
    return False, (f"Nobody is at {system.port.name}'s counter. Come "
                   "alongside, or get the crew across.")


def range_km(game, system=None) -> float:
    """How far the hull is from the quay, in km."""
    system = system or game.system
    if not getattr(system, "port", None):
        return math.inf
    from . import crossing, places
    place = places.by_id(game, f"port-{system.id}")
    return crossing.range_km(game, place) if place is not None else math.inf


def own_lift(game, system=None) -> float:
    """Tonnes your own boat shifts in a visit, or 0 without one.

    Nothing beyond her own range (`data/craft.RANGE_KM`): a ship's boat
    works round the hull, not across a system.
    """
    from ..data.craft import RANGE_KM
    from . import crossing
    if not crossing.has_boat(game):
        return 0.0
    return (crossing.lift_t(game, "boat")
            if range_km(game, system) <= RANGE_KM else 0.0)


def reach_au(game, system=None) -> float:
    """How far the hull is from the quay, in AU. What the rate is scaled by."""
    from .anchorage import KM_PER_AU
    far = range_km(game, system)
    return 0.0 if far == math.inf else far / KM_PER_AU


def may_move(game, tonnes: float, system=None) -> tuple:
    """May this much cargo cross the gap at all? `(ok, why)`.

    In a system with a port, always — a harbour will send lighters out to
    anybody who pays, which is what `fee` is for. The refusal here is only
    for having no counter to deal at.
    """
    system = system or game.system
    if not getattr(system, "port", None):
        return False, "No port here."
    return True, ""


def fee(game, tonnes: float, system=None) -> int:
    """What crossing the gap costs in credits. The one place it is worked out.

    Alongside, nothing. Otherwise your own boat carries what she carries for
    nothing, and the port's lighters take the rest by the tonne.
    """
    system = system or game.system
    if tonnes <= 0 or alongside(game, system):
        return 0
    lightered = max(0.0, float(tonnes) - own_lift(game, system))
    if lightered <= 0.0:
        return 0
    rate = LIGHTER_RATE * (1.0 + reach_au(game, system))
    return max(LIGHTER_LEAST, round(lightered * rate))


def collect(game, tonnes: float, system=None) -> int:
    """Charge it. The one place this money moves."""
    due = fee(game, tonnes, system)
    if due:
        game.credits -= due
        game.add_log(f"Lighterage on {tonnes:g} t: {due:,}.", "")
    return due


def quote(game, system=None) -> dict:
    """Everything a screen needs to say where you are dealing from."""
    system = system or game.system
    port = getattr(system, "port", None)
    close = alongside(game, system)
    far = 0.0 if close else range_km(game, system)
    ok, why = may_move(game, 1.0, system)
    counter, counter_why = at_counter(game, system)
    return {"port": bool(port), "alongside": close, "km": far,
            "au": 0.0 if close else reach_au(game, system),
            "free_t": 0.0 if close else own_lift(game, system),
            "rate": 0.0 if close else
            LIGHTER_RATE * (1.0 + reach_au(game, system)),
            "can_move": ok, "why": why,
            "at_counter": counter, "counter_why": counter_why,
            "line": line(game, system)}


def line(game, system=None) -> str:
    """One sentence for the board."""
    system = system or game.system
    port = getattr(system, "port", None)
    if port is None:
        return "No port here."
    if alongside(game, system):
        return f"Made fast at {port.name}: the counter is open and the " \
               "cranes are theirs."
    far, away = range_km(game, system), reach_au(game, system)
    rate = LIGHTER_RATE * (1.0 + away)
    where = (f"{far:,.0f} km" if away < 0.05 else f"{away:,.2f} AU")
    free = own_lift(game, system)
    return (f"{where} off {port.name}: "
            + (f"your own boat lifts {free:g} t of it free, and " if free
               else "")
            + f"their lighters take the rest at {rate:,.0f} a tonne. "
            "Alongside, the cranes are theirs and cost nothing.")
