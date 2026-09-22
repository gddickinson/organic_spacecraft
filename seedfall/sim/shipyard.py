"""The shipyard: validating a design, costing it, and waiting for it.

A fabricated hull is welded in weeks for a great deal of money. A grown hull is
gestated over months or years for very little money and a great deal of
phosphate. A GRAVID nursery in-system roughly halves the wait, which is the
entire reason anyone builds one.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.save import register
from ..core import ids
from ..data.chassis import (BUILD_NEED, CHASSIS_BY_ID, Chassis,
                            accepts_family)
from ..data.colonies import COLONIES_BY_ID
from ..data.parts import material_value, part, part_value
from . import colony, stores
from .ship import Ship, build_layers, make_ship, stats



@register
@dataclass
class BuildJob:
    id: int
    chassis_id: str
    fitted: list[str]
    name: str
    system_id: int
    system_name: str
    need: int
    days: float = 0.0


def slot_usage(fitted) -> dict[str, int]:
    used: dict[str, int] = {}
    for pid in fitted:
        p = part(pid)
        if p:
            used[p.slot] = used.get(p.slot, 0) + 1
    return used


def validate(chassis: Chassis, fitted) -> tuple[bool, list[str], bool]:
    """Returns ``(ok, errors, brownout)``. A power deficit is legal but costly."""
    errs: list[str] = []
    for slot, n in slot_usage(fitted).items():
        cap = chassis.slots.get(slot, 0)
        if n > cap:
            errs.append(f"{n} {slot} parts fitted; the hull has {cap}.")
    for pid in fitted:
        p = part(pid)
        if p is None:
            errs.append(f"Unknown part {pid}.")
        elif not accepts_family(chassis, p.family):
            errs.append(f"{p.name} will not graft to a {chassis.family} hull.")

    mock = Ship(uid=0, name="", chassis=chassis.id, fitted=list(fitted))
    s = stats(mock)
    brownout = s.draw > s.power
    return (not errs), errs, brownout


#: What a yard of your own takes off the price of a fabricated fitting. Not
#: all of it — somebody still has to be paid, and the alloy and silicon are
#: charged in full either way. You are making it instead of buying it.
FABRICATED_OFF = 0.7


def cost_of(chassis: Chassis, fitted, fabricator: bool = False) -> dict:
    """Full bill of materials for a hull plus its fittings.

    `fabricator` is whether the system it is being laid down in has a yard of
    yours in it. The credits on fabricated fittings come off; the metal does
    not, because the metal still has to exist.
    """
    cost: dict[str, float] = {"credits": 0}
    for key, n in chassis.cost.items():
        cost[key] = cost.get(key, 0) + n
    for pid in fitted:
        p = part(pid)
        if not p:
            continue
        made = fabricator and getattr(p, "family", None) == "fabricated"
        for key, n in p.cost.items():
            if made and key == "credits":
                n = n * (1 - FABRICATED_OFF)
            cost[key] = cost.get(key, 0) + n
    cost["credits"] = round(cost["credits"])
    return cost


def build_days(chassis: Chassis, game, system_id: int) -> int:
    """Days in the cradle or the slip, after nursery help and research."""
    speed = 1 + game.bonuses.get("growth", 0)
    helped = any(c.online and c.system_id == system_id
                 and COLONIES_BY_ID[c.class_id].effects.get("gestation")
                 for c in game.colonies)
    if helped and chassis.family not in ("fabricated", "synthetic"):
        speed += 0.9
    if chassis.family in ("fabricated", "synthetic"):
        speed += 0.4
    return max(4, round(chassis.grow / speed))


def affordable(game, cost: dict) -> tuple[bool, list[tuple[str, float, float]]]:
    """Do we have the money and the matter? Hold and depot both count."""
    missing = [(key, n, int(have)) for key, n, have in stores.lacking(game, cost)]
    return (not missing), missing


_BUILD_REFUSAL = {
    "shipyard": "This hull is welded, not grown — it needs a shipyard or a "
                "fabricator yard.",
    "gestation": "Grown hulls need a nursery — a fleet hub, or a GRAVID of your own.",
    "xenoyard": "Nobody in the Verge knows how to lay this down. You need a "
                "reactivated xeno array of your own.",
}
#: A derelict class breakers know how to wake (`data/establishments`), and
#: what they say where there are none.
_REACTIVATE_REFUSAL = ("Nobody here can wake one. A breakers' yard puts a "
                       "derelict like this back together, or a reactivated "
                       "xeno array of your own will.")


def can_build_here(game, system, chassis: Chassis) -> tuple[bool, str]:
    """Where can this hull be laid down?"""
    if system is None:
        return False, "Nowhere to build."
    need = BUILD_NEED.get(chassis.family, "shipyard")
    services = system.port.services if system.port else ()

    def colony_offers(key: str) -> bool:
        return any(c.online and c.system_id == system.id
                   and COLONIES_BY_ID[c.class_id].effects.get(key)
                   for c in game.colonies)

    if need == "xenoyard":
        from . import establishments, kith
        # A Kith hull is grown at a gathering; a derelict class is woken by
        # breakers; anything else wants an array of your own.
        if colony_offers("xenoyard") or kith.grows(game, system, chassis) \
                or establishments.reactivates_here(game, system, chassis.id):
            return True, ""
        from ..data.establishments import ESTABLISHMENTS
        woken = any(chassis.id in e.reactivates for e in ESTABLISHMENTS)
        return False, (_REACTIVATE_REFUSAL if woken
                       else _BUILD_REFUSAL["xenoyard"])
    if need in services or colony_offers("build_here"):
        return True, ""
    from . import establishments          # a yard or a nursery in orbit here
    if establishments.builds_here(game, system, need):
        return True, ""
    return False, _BUILD_REFUSAL[need]


def start_build(game, chassis_id: str, fitted, system, name: str | None = None):
    chassis = CHASSIS_BY_ID[chassis_id]
    ok, errs, _ = validate(chassis, fitted)
    if not ok:
        return None, errs[0]
    here, why = can_build_here(game, system, chassis)
    if not here:
        return None, why
    if chassis.tech and chassis.tech not in game.research.unlocked:
        return None, "That hull is not yet researched."
    # **A cradle is seed going in the ground.** `colony.found` asked the
    # licence and this did not, so a captain whose licence had been
    # suspended — "no settlement, no lineage, until it is restored", in the
    # forum's own words — could still lay down grown hulls, and Lineage is
    # four of them. Welded hulls are not seed and are not asked.
    if BUILD_NEED.get(chassis.family) == "gestation":
        from . import enforce as enforce_sim
        licensed, refusal = enforce_sim.may_seed(game)
        if not licensed:
            return None, refusal
    cost = cost_of(chassis, fitted, colony.fabricating(game, system.id))
    can, missing = affordable(game, cost)
    if not can:
        key, need, have = missing[0]
        return None, f"Short of {key}: need {need:g}, have {have}."

    stores.spend(game, cost)
    job = BuildJob(id=ids.next_id("build", game), chassis_id=chassis_id, fitted=list(fitted),
                   name=name or chassis.name, system_id=system.id,
                   system_name=system.name, need=build_days(chassis, game, system.id))
    game.building.append(job)
    # The chronicle hears it from the act, not from the yard screen that
    # happened to press it (`ui/yard_view` wrote this line itself).
    game.add_log(f"{job.name} laid down at {job.system_name}. "
                 f"Ready in {job.need} days.", "good")
    return job, ""


def tick_builds(game, days: float) -> list[Ship]:
    """Advance the slips. Completed hulls join the fleet where they were built."""
    done = []
    for job in game.building:
        job.days += days
        if job.days >= job.need:
            done.append(job)
    if not done:
        return []
    game.building = [j for j in game.building if j not in done]
    launched = []
    for job in done:
        ship = make_ship(job.chassis_id, job.fitted, job.name)
        build_layers(ship, game.bonuses)
        ship.docked_at = job.system_id
        ship.launched_on = game.day
        game.fleet.append(ship)
        launched.append(ship)
    return launched


def refit_cost(chassis: Chassis, old_fitted, new_fitted,
               fabricator: bool = False):
    """You pay for what you add; removed parts sell back at half.

    A yard of your own takes the same share off a fabricated fitting here as
    it does on a new hull — it is the same question, and two answers to it is
    how this project has produced a free treaty and a phantom haggle before.
    """
    removed = list(old_fitted)
    added = []
    for pid in new_fitted:
        if pid in removed:
            removed.remove(pid)
        else:
            added.append(pid)
    cost: dict[str, float] = {"credits": 0}
    for pid in added:
        p = part(pid)
        if not p:
            continue
        made = fabricator and getattr(p, "family", None) == "fabricated"
        for key, n in p.cost.items():
            if made and key == "credits":
                n = n * (1 - FABRICATED_OFF)
            cost[key] = cost.get(key, 0) + n
    refund = round(sum(part_value(part(pid)) * 0.5 for pid in removed if part(pid)))
    cost["credits"] = max(0, cost.get("credits", 0) - refund)
    return cost, added, removed, refund


def can_refit_here(game) -> tuple[bool, str]:
    """Is the hull somewhere that can actually open it up?

    This rule lived only in the button. `apply_refit` validated the design and
    the cost and nothing else, so the remote bridge — or any other caller —
    could strip a hull in deep space. And the button's own version was wrong
    twice over: it tested "this system contains a port", which since
    anchorages is not the same as being alongside one, and it accepted any
    port at all rather than one with a yard. You could re-hull at an outpost
    that sells groceries, from four AU away.
    """
    from . import anchorage
    # Alongside a yard of the trade's own (`sim/establishments`) is alongside
    # a yard (breakers' slips refit anything) — and a nursery opens up the
    # hulls it grows, though it will not touch a welded one.
    chassis = CHASSIS_BY_ID.get(getattr(game.ship, "chassis", ""))
    need = BUILD_NEED.get(getattr(chassis, "family", ""), "shipyard")
    if any(a.here and a.kind == "station" and (
            a.offers("shipyard") or (need != "shipyard" and a.offers(need)))
           for a in anchorage.in_system(game)):
        return True, ""
    here = anchorage.docked_at(game)
    if here is None:
        yards = anchorage.offering(game, "shipyard")
        if yards:
            return False, (f"You are not alongside anything. {yards[0].name} "
                           "is in this system.")
        return False, "You are not alongside a yard."
    if not here.offers("shipyard"):
        yards = [a for a in anchorage.offering(game, "shipyard")
                 if a.id != here.id]
        return False, (f"{here.name} has no yard"
                       + (f"; {yards[0].name} does." if yards else
                          " and nothing in this system does."))
    return True, ""


def apply_refit(game, ship: Ship, new_fitted) -> tuple[bool, str]:
    chassis = CHASSIS_BY_ID[ship.chassis]
    where, why = can_refit_here(game)
    if not where:
        return False, why
    ok, errs, _ = validate(chassis, new_fitted)
    if not ok:
        return False, errs[0]
    cost, *_ = refit_cost(chassis, ship.fitted, new_fitted,
                          colony.fabricating(game, game.location_id))
    can, missing = affordable(game, cost)
    if not can:
        key, need, have = missing[0]
        return False, f"Short of {key}: need {need:g}, have {have}."
    stores.spend(game, cost)

    fractions = [l.hp / l.max if l.max else 1 for l in ship.layers]
    ship.fitted = list(new_fitted)
    ship.disabled = []
    build_layers(ship, game.bonuses)
    for i, L in enumerate(ship.layers):
        if i < len(fractions):
            L.hp = round(L.max * fractions[i])
    game.add_log("Refit complete.", "good")
    return True, ""


#: Share of a hull's worth the breaker pays. One number for credits and
#: matter alike — a yard that paid different shares invites arbitrage between
#: the two sides of the bill.
SCRAP_SHARE = 0.45


def scrap_value(ship: Ship) -> int:
    """What a breaker pays for the whole hull. Always less than building it.

    Two rules, both learned from a measured exploit (+146,470 credits per
    build-and-scrap cycle at a fabricator port):

    - The bill is priced **as if the fabricator discount was taken**, whoever
      actually built her. `Ship` records no provenance, so the breaker
      assumes the cheapest possible build — a hull can never be worth more
      broken up than it cost to lay down.
    - Returned matter is valued as *itself* (`data/parts.material_value`),
      not at a flat rate that paid 143% of base for ore and 7% for silicon.
    """
    chassis = CHASSIS_BY_ID[ship.chassis]
    cost = cost_of(chassis, ship.fitted, fabricator=True)
    v = cost.get("credits", 0) * SCRAP_SHARE
    v += sum(n * material_value(key) * SCRAP_SHARE
             for key, n in cost.items() if key != "credits")
    return round(v)


def scrap(game, ship) -> dict:
    """Break a hull up for what it is worth. Was done from the yard screen."""
    if ship is game.ship:
        return {"ok": False, "why": "You are standing in it."}
    if getattr(ship, "line_id", None) is not None:
        return {"ok": False, "why": f"{ship.name} is working a freight line."}
    value = scrap_value(ship)
    game.credits += value
    game.fleet = [s for s in game.fleet if s is not ship]
    game.add_log(f"{ship.name} was broken up for {value:,}.", "")
    return {"ok": True, "value": value}
