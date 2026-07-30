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


#: Which rig raises which commodity. `raise_rate` walks this, and so does
#: `rig_of` — so a rig that lifts material off a body is a rig that wears it
#: down, by construction rather than by two lists agreeing.
RIGS = (("ore", "mine"), ("phosphate", "phos"),
        ("volatiles", "drink"), ("biomass", "graze"))


def rig_of(stats) -> float:
    """How hard this hull works a body, summed over every rig that raises.

    **The one door, and there were two.** `actions.extract` depleted the body at
    `st.mine + st.drink` while `prospect` forecast at `max(st.mine, st.drink)`, so
    a starting hull — 3.2 mine, 0.8 drink — wore a body down at 4.0 and was told
    3.2, and every days figure on the screen was a fifth too long.

    Worse, neither counted `phos` or `graze`. Both raise material: a hull fitted
    with a phosphate rig and nothing else lifted 0.507 t a day and depleted the
    body by **exactly zero**, so `worked_out` never fired and the seam paid out
    for ever. A harvest tendril alone did the same at 0.316. An infinite source
    is not a slow one.
    """
    return sum(max(0.0, getattr(stats, attr, 0.0) or 0.0)
               for _cid, attr in RIGS)


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


#: Past this, the body is finished: the seams are gone and the rig comes off.
#:
#: The cap used to be the *same* number and nothing read it as an ending, so a
#: worked-out body sat at 95% forever and went on yielding 1.1 t a session
#: without limit — measured at trip 20 and still going at trip 199. A seam
#: that never runs out is a seam nobody ever has to leave, which quietly
#: removes both the reason to prospect and the whole point of a method that
#: works a body gently.
WORKED_OUT = 0.95

#: What a body actually gives up against what the arithmetic says it should.
#:
#: The midpoint estimate — yield falls linearly with what is left, so average
#: it — reads 15% high against a body worked to exhaustion, consistently and
#: for every method including the one with no mishap risk at all. Rather than
#: ship a forecast that flatters itself, it is calibrated against the thing it
#: forecasts. `test_seams` re-measures it, so if the extraction arithmetic
#: moves and this stops being true, something says so.
WORKING_LOSS = 0.85


def worked_out(body) -> bool:
    """Is there anything left worth putting a rig on?"""
    return getattr(body, "depleted", 0.0) >= WORKED_OUT - 1e-9


def deplete(game, body, method_id: str, days: int, rig: float) -> None:
    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    body.depleted = min(WORKED_OUT, body.depleted
                        + days * 0.0016 * rig * method.depletion_mul)


#: How long a step the forecast walks, in days. Small enough that the falling
#: yield is followed closely and large enough that a body four hundred days deep
#: is a few dozen steps rather than a few hundred.
FORECAST_STEP = 5


def prospect(body, method_id: str, stats) -> dict:
    """What this method will get out of this body before it is finished.

    A body used to sit at the depletion cap paying a token tonne a session for
    ever, so there was nothing to forecast and no reason to choose a gentler
    method. Now it ends, and the two figures that matter — how fast, and how
    much in total — pull in opposite directions: measured on one body, a deep
    bore lifts four times a skim's daily rate and recovers barely half of what
    the body holds.

    **It is a dry run, not a formula.** The first version estimated the average
    rate at the midpoint of what was left and multiplied by days and a
    `WORKING_LOSS` fudge. Checked against actually working the body out, it was
    2% low on a bioleach and **45% low on a bore** — the error tracking how fast
    the method depletes, because the faster it goes the fewer steps the average
    is taken over and the less the midpoint means. A forecast whose error
    depends on the option being compared is worse than no forecast, because it
    tilts the comparison it exists to inform.

    So it walks the body down in `FORECAST_STEP` days at a time through
    `raise_rate` and the same depletion arithmetic `deplete` uses, and adds up
    what comes off. It cannot disagree with the act, because it is the act with
    the ship left at home — the same reason `sim/preview.py` flies a throwaway
    twin instead of predicting a burn.
    """
    rig = rig_of(stats)
    left = max(0.0, WORKED_OUT - getattr(body, "depleted", 0.0))
    if rig <= 0 or left <= 0:
        return {"left": left, "days": 0.0, "total": 0.0,
                "rate": 0.0, "finished": left <= 0}

    method = METHODS_BY_ID.get(method_id, METHODS_BY_ID[DEFAULT_METHOD])
    per_day = 0.0016 * rig * method.depletion_mul
    if per_day <= 0:
        return {"left": left, "days": 0.0, "total": 0.0,
                "rate": raise_rate(body, method_id, stats), "finished": False}

    now = raise_rate(body, method_id, stats)
    was = getattr(body, "depleted", 0.0)
    total, days = 0.0, 0.0
    # A hard step bound as well as the depletion test. **A mutation that removed
    # the advance below hung the whole suite**, because the loop's only exit was
    # arithmetic that the mutation stopped happening — and a check that hangs is
    # worse than one that fails, since it tells you nothing and costs everything.
    # `WORKED_OUT / (0.0016 * FORECAST_STEP)` is the most steps the slowest legal
    # rig could need; twice that is head-room and still finite.
    steps, most = 0, int(2 * WORKED_OUT / (0.0016 * FORECAST_STEP))
    try:
        while body.depleted < WORKED_OUT - 1e-9 and steps < most:
            steps += 1
            step = min(FORECAST_STEP,
                       (WORKED_OUT - body.depleted) / per_day)
            if step <= 0:
                break
            total += raise_rate(body, method_id, stats) * step
            days += step
            body.depleted = min(WORKED_OUT, body.depleted + step * per_day)
    finally:
        body.depleted = was
    return {"left": left, "days": days, "total": total,
            "rate": now, "finished": False}


def raise_rate(body, method_id: str, stats) -> float:
    """Tonnes a day this rig lifts off this body, all seams together."""
    return sum(rate_for(body, method_id, cid,
                        max(0.0, getattr(stats, attr, 0.0) or 0.0))
               for cid, attr in RIGS)


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
