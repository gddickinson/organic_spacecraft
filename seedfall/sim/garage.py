"""The garage: what rides down with a landing party, bought and mended.

Split out of `sim/hangar.py` when that file reached five hundred lines,
along the seam it already had: a cradle holds what flies *out* and a hold
holds what goes *down*. Everything here is the yard side of a surface
vehicle (`sim/vehicles.py`) or a camp (`sim/camps.py`) — built where its
family's hulls are built, stowed in the hold against the cargo it displaces,
mended by the point, and sold back at the same loss a craft fetches, for the
same reason: a yard that pays what it charges is a money pump.
"""

from __future__ import annotations

from ..data.parts import material_value
from . import shipyard, stores

# ── the garage ─────────────────────────────────────────────────────────────

#: What a yard charges to put one point of condition back into a machine,
#: and the days it takes to do the lot.
VEHICLE_MEND, VEHICLE_DAYS = 900, 2


def vehicle_offers(game) -> list:
    """Every vehicle class, what it costs, and why it cannot be had here."""
    from ..data.vehicles import VEHICLES
    out = []
    for kind in VEHICLES:
        ok, why = can_buy_vehicle(game, kind.id)
        out.append({"kind": kind, "ok": ok, "why": why,
                    "credits": int(kind.cost.get("credits", 0))})
    return out


def can_buy_vehicle(game, class_id: str) -> tuple:
    """May this machine be built for you here?"""
    from ..data.vehicles import VEHICLES_BY_ID
    kind = VEHICLES_BY_ID.get(class_id)
    if kind is None:
        return False, "No such class."
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    # The same family rule hulls and craft are built under.
    here, refusal = shipyard.can_build_here(game, game.system, kind)
    if not here:
        return False, refusal
    from .ship import cargo_free
    if kind.mass_t > cargo_free(game.ship, game.ship_stats):
        return False, (f"A {kind.name} is {kind.mass_t:g} t and the hold has "
                       "no room for it.")
    short = stores.lacking(game, kind.cost)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def buy_vehicle(game, class_id: str, name: str = "") -> dict:
    """Build one and stow it. The yard's side of `vehicles.give`."""
    from . import vehicles as vehicles_sim
    ok, why = can_buy_vehicle(game, class_id)
    if not ok:
        return {"ok": False, "why": why}
    from ..data.vehicles import VEHICLES_BY_ID
    kind = VEHICLES_BY_ID[class_id]
    stores.spend(game, dict(kind.cost))
    held = vehicles_sim.give(game, class_id, name)
    game.add_log(f"{held.name} built at {game.system.name} for "
                 f"{kind.cost.get('credits', 0):,}.", "good")
    return {"ok": True, "vehicle": held,
            "paid": int(kind.cost.get("credits", 0))}


def vehicle_mend_cost(vehicle) -> dict:
    """What a yard charges to make a machine whole."""
    from ..data.vehicles import WHOLE
    from . import vehicles as vehicles_sim
    points = max(0, WHOLE - int(vehicle.condition))
    if not points:
        return {}
    kind = vehicles_sim.kind_of(vehicle)
    matter = "biomass" if kind.family == "grown" else "alloy"
    return {"credits": VEHICLE_MEND * points,
            matter: round(kind.mass_t * 0.15 * points, 2)}


def can_mend_vehicle(game, vehicle) -> tuple:
    if vehicle is None or vehicle.state == "lost":
        return False, "There is no such machine aboard."
    if vehicle.state != "stowed":
        return False, f"{vehicle.name} is on a world. Bring it up first."
    cost = vehicle_mend_cost(vehicle)
    if not cost:
        return False, f"{vehicle.name} is whole."
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    short = stores.lacking(game, cost)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def mend_vehicle(game, vehicle) -> dict:
    """Put its condition back, by the point."""
    from ..data.vehicles import WHOLE
    ok, why = can_mend_vehicle(game, vehicle)
    if not ok:
        return {"ok": False, "why": why}
    cost = vehicle_mend_cost(vehicle)
    points = WHOLE - int(vehicle.condition)
    stores.spend(game, cost)
    vehicle.condition = WHOLE
    game.advance_days(VEHICLE_DAYS)
    game.add_log(f"{vehicle.name} put right: {points} points, "
                 f"{cost.get('credits', 0):,} credits.", "good")
    return {"ok": True, "points": points, "paid": int(cost.get("credits", 0))}


def vehicle_worth(vehicle) -> int:
    """What a yard pays for a machine: salvage, scaled by condition."""
    from ..data.vehicles import SALVAGE, WHOLE
    from . import vehicles as vehicles_sim
    kind = vehicles_sim.kind_of(vehicle)
    share = SALVAGE * (0.4 + 0.6 * max(0.0, vehicle.condition / WHOLE))
    value = kind.cost.get("credits", 0) * share
    value += sum(n * material_value(key) * share
                 for key, n in kind.cost.items() if key != "credits")
    return round(value)


def can_sell_vehicle(game, vehicle) -> tuple:
    if vehicle is None or vehicle.state == "lost":
        return False, "There is no such machine aboard."
    if vehicle.state != "stowed":
        return False, f"{vehicle.name} is on a world. Bring it up first."
    return shipyard.can_refit_here(game)


def sell_vehicle(game, vehicle) -> dict:
    """Off the books, for what a yard will give."""
    ok, why = can_sell_vehicle(game, vehicle)
    if not ok:
        return {"ok": False, "why": why}
    paid = vehicle_worth(vehicle)
    game.credits += paid
    game.vehicles = [v for v in (game.vehicles or []) if v is not vehicle]
    game.add_log(f"{vehicle.name} sold for {paid:,}.", "")
    return {"ok": True, "paid": paid}


# ── and the camps ──────────────────────────────────────────────────────────

def camp_offers(game) -> list:
    """Every camp class, what it costs, and why it cannot be had here."""
    from ..data.camps import CAMPS
    out = []
    for kind in CAMPS:
        ok, why = can_buy_camp(game, kind.id)
        out.append({"kind": kind, "ok": ok, "why": why,
                    "credits": int(kind.cost.get("credits", 0))})
    return out


def can_buy_camp(game, class_id: str) -> tuple:
    from ..data.camps import CAMPS_BY_ID
    kind = CAMPS_BY_ID.get(class_id)
    if kind is None:
        return False, "No such class."
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    here, refusal = shipyard.can_build_here(game, game.system, kind)
    if not here:
        return False, refusal
    from .ship import cargo_free
    if kind.mass_t > cargo_free(game.ship, game.ship_stats):
        return False, (f"A {kind.name} is {kind.mass_t:g} t and the hold has "
                       "no room for it.")
    short = stores.lacking(game, kind.cost)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def buy_camp(game, class_id: str, name: str = "") -> dict:
    """Build one and stow it. The yard's side of `camps.give`."""
    from . import camps as camps_sim
    ok, why = can_buy_camp(game, class_id)
    if not ok:
        return {"ok": False, "why": why}
    from ..data.camps import CAMPS_BY_ID
    kind = CAMPS_BY_ID[class_id]
    stores.spend(game, dict(kind.cost))
    held = camps_sim.give(game, class_id, name)
    game.add_log(f"{held.name} stowed at {game.system.name} for "
                 f"{kind.cost.get('credits', 0):,}.", "good")
    return {"ok": True, "camp": held,
            "paid": int(kind.cost.get("credits", 0))}


def camp_worth(camp) -> int:
    """What a yard pays for a camp back."""
    from ..data.camps import SALVAGE
    from . import camps as camps_sim
    kind = camps_sim.kind_of(camp)
    value = kind.cost.get("credits", 0) * SALVAGE
    value += sum(n * material_value(key) * SALVAGE
                 for key, n in kind.cost.items() if key != "credits")
    return round(value)


def can_sell_camp(game, camp) -> tuple:
    if camp is None or camp.state == "lost":
        return False, "There is no such camp aboard."
    if camp.state != "stowed":
        return False, f"{camp.name} is on a world. Bring it up first."
    return shipyard.can_refit_here(game)


def sell_camp(game, camp) -> dict:
    ok, why = can_sell_camp(game, camp)
    if not ok:
        return {"ok": False, "why": why}
    paid = camp_worth(camp)
    game.credits += paid
    game.camps = [c for c in (game.camps or []) if c is not camp]
    game.add_log(f"{camp.name} sold for {paid:,}.", "")
    return {"ok": True, "paid": paid}
