"""Working a body: which seams are down there, and what it costs to reach them.

Seams are derived from the body's own grades rather than stored, so every
existing body in every existing save has them without a migration. The depth a
seam sits at is a stable function of the body and the resource — the same rock
always hides the same thing in the same place.
"""

from __future__ import annotations

from ..core.rng import hash_seed
from ..data.mining import (DEFAULT_METHOD, DEPTH_NAMES, METHODS_BY_ID, MISHAPS,
                           STRIKE_BONUS, STRIKE_CHANCE)

RESOURCES = ("ore", "phosphate", "volatiles", "biomass")


def _depth_of(body, resource: str) -> int:
    """Where this resource sits in this body. Stable, and not random at read.

    Two things are always within reach of an open cut, and both are about not
    stranding anybody: volatiles, because they are the fuel of last resort and
    a captain with no bore and no reaction mass has no way out of that; and
    whatever the body is *for*, because a rock advertised as an ore body that
    turns out to need a deep bore is a survey that lied.
    """
    grade = body.resources.get(resource, 0.0)
    if grade <= 0.0:
        return 0
    spread = hash_seed(f"{body.id}|{resource}|seam") % 100
    # Richer grades tend to sit deeper: the easy stuff was never the good stuff.
    threshold = 45 - grade * 30
    if spread < threshold:
        depth = 0
    else:
        depth = 1 if spread < threshold + 33 else 2

    if resource == "volatiles":
        return min(depth, 1)
    best = max(body.resources.items(), key=lambda kv: kv[1], default=(None, 0))
    if best[0] == resource and best[1] > 0:
        return min(depth, 1)
    return depth


def seams(body) -> list[dict]:
    """Everything in this body worth a rig, with its depth and grade."""
    out = []
    for resource in RESOURCES:
        grade = body.resources.get(resource, 0.0)
        if grade <= 0.01:
            continue
        depth = _depth_of(body, resource)
        out.append({"resource": resource, "grade": grade, "depth": depth,
                    "depth_name": DEPTH_NAMES[depth]})
    out.sort(key=lambda s: (s["depth"], -s["grade"]))
    return out


def reachable(body, method_id: str) -> list[dict]:
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    return [s for s in seams(body) if s["depth"] <= method.reach]


def available(game, body) -> list[tuple]:
    """(method, ok, why) for every way of working this body."""
    st = game.ship_stats
    out = []
    for method in METHODS_BY_ID.values():
        ok, why = True, ""
        if method.needs and getattr(st, method.needs, 0) <= 0:
            ok, why = False, "Nothing fitted that can work it that way."
        elif not reachable(body, method.id):
            ok, why = False, "Nothing this reaches is worth the trouble."
        out.append((method, ok, why))
    out.sort(key=lambda item: METHODS_BY_ID[item[0].id].reach)
    return out


def rate_for(body, method_id: str, resource: str, rig: float) -> float:
    """Tonnes per day this method pulls of one resource."""
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    seam = next((s for s in seams(body) if s["resource"] == resource), None)
    if seam is None or seam["depth"] > method.reach or rig <= 0:
        return 0.0
    left = max(0.0, 1 - body.depleted)
    # Deeper seams pay better for being harder to get at.
    depth_bonus = 1.0 + seam["depth"] * 0.35
    return seam["grade"] * rig * left * method.yield_mul * depth_bonus


def upkeep_for(method_id: str, days: int) -> dict:
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    return {k: v * days for k, v in method.upkeep.items()}


def can_afford(game, method_id: str, days: int) -> tuple[bool, str]:
    for key, need in upkeep_for(method_id, days).items():
        held = game.ship.cargo.get(key, 0) + game.stores.get(key, 0)
        if held < need:
            return False, f"That needs {round(need)} t of {key}; you have {round(held)}."
    return True, ""


def spend_upkeep(game, method_id: str, days: int) -> None:
    from .ship import add_cargo
    for key, need in upkeep_for(method_id, days).items():
        from_ship = min(game.ship.cargo.get(key, 0), need)
        if from_ship > 0:
            add_cargo(game.ship, key, -from_ship)
        rest = need - from_ship
        if rest > 0:
            game.stores[key] = max(0.0, game.stores.get(key, 0) - rest)


def apply_wear(game, method_id: str, days: int) -> float:
    """Hard methods eat the hull. Returns the damage done."""
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    if method.wear <= 0 or not game.ship.layers:
        return 0.0
    outer = game.ship.layers[0]
    damage = outer.max * method.wear * days
    outer.hp = max(0.0, outer.hp - damage)
    return damage


def roll_event(game, body, method_id: str, rng) -> dict | None:
    """A mishap or a strike. Deep work is where both live."""
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    if method.risk > 0 and rng.chance(method.risk):
        mishap = rng.pick(MISHAPS)
        if mishap.damage and game.ship.layers:
            outer = game.ship.layers[0]
            outer.hp = max(0.0, outer.hp - outer.max * mishap.damage)
        if mishap.collapse:
            body.depleted = min(0.98, body.depleted + mishap.collapse)
        return {"kind": "mishap", "mishap": mishap, "spoil": mishap.spoil}
    if rng.chance(STRIKE_CHANCE * (0.4 + method.yield_mul)):
        return {"kind": "strike", "bonus": STRIKE_BONUS}
    return None


def deplete(game, body, method_id: str, days: int, rig: float) -> None:
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    body.depleted = min(0.95, body.depleted
                        + days * 0.0016 * rig * method.depletion_mul)


def raise_rate(body, method_id: str, stats) -> float:
    """Tonnes a day this rig lifts off this body, all seams together."""
    rigs = {"ore": stats.mine, "phosphate": stats.phos,
            "volatiles": stats.drink, "biomass": stats.graze}
    return sum(rate_for(body, method_id, cid, rig) for cid, rig in rigs.items())


def days_of_room(body, method_id: str, stats, room: float, days: int) -> int:
    """How long the working actually lasts before the hold is full.

    A rig used to run the whole spell whether or not there was anywhere to put
    what it raised: `extract` took `min(amount, cargo_free)` and depleted the
    body for the full duration regardless. Measured, that meant sixty days and
    38% of a body's remaining yield spent to recover ten tonnes out of a
    hundred and six, with nothing on the screen to warn you.
    """
    rate = raise_rate(body, method_id, stats)
    if rate <= 0 or room <= 0:
        return 0 if room <= 0 else days
    import math
    return max(1, min(days, math.ceil(room / rate)))


def summary(body, method_id: str) -> dict:
    found = seams(body)
    within = reachable(body, method_id)
    return {"seams": found, "reachable": within,
            "out_of_reach": [s for s in found if s not in within],
            "worked_out": body.depleted}
