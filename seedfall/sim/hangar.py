"""The hangar deck and the garage: what a hull carries, bought and mended.

`sim/craft.py` flies what a hull already carries and `sim/craft_battle.py`
fights with it. This is where one comes from and where it goes — the yard
side of a cradle, and the only door that adds or removes a craft.

- **A cradle is fitted, not assumed.** A hull has as many as somebody has
  put on it (`Ship.cradles`), and never more than its own crew can work
  (`most`): a launch needs a deck, a hatch and hands to turn her round, and
  a ship's boat is the smallest hull that has any of those.
- **A craft is laid down where its family's hulls are.** A grown WASP comes
  out of a nursery and a welded SHRIKE out of a shipyard, which is
  `shipyard.can_build_here`'s rule and not a second copy of it. You pay the
  class's own cost in credits and matter through `sim/stores`, and the days
  it takes are days.
- **Mending is the thing that was missing.** A craft that came home from an
  engagement at half hull stayed at half hull for the rest of the chronicle.
  A yard puts points back by the point; and a *grown* craft knits herself up
  in her cradle off the hull's own biomass, slowly, which is what being
  grown is for (`knit`, called by the day from `core/shiptime`).
- **Selling is always a loss** (`SALVAGE`, and worse for a wreck), because a
  yard that pays what it charges is a money pump — `shipyard.scrap_value`
  learned that at 146,470 credits a cycle.

The same counter sells **surface vehicles** (`sim/vehicles.py`): they are
bought where their family's hulls are built, stowed in the hold rather than
a cradle, mended by the point of condition, and sold back at the same loss.
A rover is not a craft — it has no cradle and never flies — but the yard
side of one is the yard side of the other, and one door is better than two.
"""

from __future__ import annotations

from ..data import craft as table
from ..data.craft import CRAFT, CRAFT_BY_ID
from ..data.parts import material_value
from . import craft as craft_sim
from . import shipyard, stores

#: Hands a cradle takes to work, and the most any hull will carry. The floor
#: is the boat bay's own (`sim/afoot_program.BOAT_CREW`): a hull too small to
#: crew a ship's boat is too small for a cradle.
CREW_PER_CRADLE, CRADLE_MOST = 30, 4
#: What a yard charges to cut a cradle into a hull, and the days it takes.
CRADLE_COST = {"credits": 9_000, "alloy": 20, "silicon": 6}
CRADLE_DAYS = 7

#: Credits of build cost a day in the slip is worth, and the least any craft
#: takes. A WASP is a fortnight; a SHRIKE most of three weeks.
CREDITS_PER_DAY, LEAST_DAYS = 3_000, 6

#: What a yard charges to put one point of hull back into a craft, and the
#: matter it takes: biomass for something grown, alloy for something welded
#: (the ship's own rate, `sim/ship.FEED_PER_HP`).
MEND_CREDITS, MEND_MATTER = 45, 0.05
#: Points a yard puts back in a day.
MEND_A_DAY = 40

#: Points a grown craft knits back in her own cradle in a day, off the
#: hull's biomass. Welded ones wait for a yard.
KNIT_A_DAY = 1.5


# ── cradles ────────────────────────────────────────────────────────────────

def most(ship) -> int:
    """The most cradles this hull could ever carry."""
    from .afoot_program import BOAT_CREW
    rated = getattr(ship.chassis_def, "crew", 0)
    if rated < BOAT_CREW:
        return 0
    return max(1, min(CRADLE_MOST, 1 + rated // CREW_PER_CRADLE))


def cradles(ship) -> int:
    """How many cradles are on her now."""
    return max(0, min(most(ship), int(getattr(ship, "cradles", 1))))


def room(game) -> int:
    """Empty cradles: what a craft could be bought into."""
    return max(0, cradles(game.ship) - len(craft_sim.aboard(game)))


def can_fit_cradle(game) -> tuple:
    """May a yard cut another cradle into this hull?"""
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    ship = game.ship
    if most(ship) <= 0:
        return False, (f"A {ship.chassis_def.name} has no deck to put one "
                       "on — a cradle wants a hull that could crew a boat.")
    if cradles(ship) >= most(ship):
        return False, (f"She carries {cradles(ship)} cradle"
                       f"{'' if cradles(ship) == 1 else 's'} already, which "
                       "is all a hull this size will take.")
    short = stores.lacking(game, CRADLE_COST)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def fit_cradle(game) -> dict:
    """Cut another cradle into the hull, with its hatch to the deck."""
    ok, why = can_fit_cradle(game)
    if not ok:
        return {"ok": False, "why": why}
    stores.spend(game, CRADLE_COST)
    game.ship.cradles = cradles(game.ship) + 1
    game.advance_days(CRADLE_DAYS)
    game.add_log(f"A second cradle cut into {game.ship.name}'s flank."
                 if game.ship.cradles == 2 else
                 f"Cradle {game.ship.cradles} fitted to {game.ship.name}.",
                 "good")
    return {"ok": True, "cradles": game.ship.cradles, "days": CRADLE_DAYS}


# ── buying one ─────────────────────────────────────────────────────────────

def days_for(kind) -> int:
    """Days in the slip for this class."""
    return max(LEAST_DAYS,
               round(kind.cost.get("credits", 0) / CREDITS_PER_DAY))


def can_buy(game, class_id: str) -> tuple:
    """May this class be laid down for you here?"""
    kind = CRAFT_BY_ID.get(class_id)
    if kind is None:
        return False, "No such class."
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    if room(game) <= 0:
        return False, ("Every cradle she has is full. A yard will fit "
                       "another." if cradles(game.ship)
                       else "She has no cradle to put one in.")
    # A craft is laid down where its family's hulls are: the same rule, asked
    # of the same function, rather than a second copy of it going stale.
    system = game.system
    here, refusal = shipyard.can_build_here(game, system, kind)
    if not here:
        return False, refusal
    short = stores.lacking(game, kind.cost)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def buy(game, class_id: str, name: str = "") -> dict:
    """Lay one down and take her aboard. The yard's side of `craft.give`."""
    ok, why = can_buy(game, class_id)
    if not ok:
        return {"ok": False, "why": why}
    kind = CRAFT_BY_ID[class_id]
    stores.spend(game, dict(kind.cost))
    days = days_for(kind)
    game.advance_days(days)
    craft = craft_sim.give(game, class_id, name)
    game.add_log(f"{craft.name} laid down at {game.system.name} and taken "
                 f"aboard — {days} days and "
                 f"{kind.cost.get('credits', 0):,} credits.", "good")
    return {"ok": True, "craft": craft, "days": days,
            "paid": int(kind.cost.get("credits", 0))}


def offers(game) -> list:
    """Every class, what it costs, and why it cannot be had if it cannot.

    One row a class whether or not it can be built, because "the Verge makes
    four of these and this yard makes one of them" is worth knowing at the
    counter.
    """
    out = []
    for kind in CRAFT:
        ok, why = can_buy(game, kind.id)
        out.append({"kind": kind, "ok": ok, "why": why,
                    "days": days_for(kind),
                    "credits": int(kind.cost.get("credits", 0))})
    return out


# ── mending one ────────────────────────────────────────────────────────────

def mend_cost(craft) -> dict:
    """What a yard charges to make this craft whole."""
    kind = craft_sim.kind_of(craft)
    points = max(0, kind.hull - craft.hp)
    if not points:
        return {}
    matter = "biomass" if kind.family == "grown" else "alloy"
    return {"credits": int(MEND_CREDITS * points),
            matter: round(MEND_MATTER * points, 2)}


def can_mend(game, craft) -> tuple:
    """May she be made whole here?"""
    if craft is None or craft.state == "lost":
        return False, "There is no such craft aboard."
    if craft.state == "down":
        return False, (f"{craft.name} is on a world. A yard cannot reach "
                       "her there.")
    if craft.state == "out":
        return False, f"{craft.name} is out. Nobody mends a craft in flight."
    cost = mend_cost(craft)
    if not cost:
        return False, f"{craft.name} is whole."
    ok, why = shipyard.can_refit_here(game)
    if not ok:
        return False, why
    short = stores.lacking(game, cost)
    if short:
        key, need, have = short[0]
        return False, f"Short of {key}: need {need:g}, have {have:g}."
    return True, ""


def mend(game, craft) -> dict:
    """Put her hull back, by the point, at a yard."""
    ok, why = can_mend(game, craft)
    if not ok:
        return {"ok": False, "why": why}
    kind = craft_sim.kind_of(craft)
    points = kind.hull - craft.hp
    cost = mend_cost(craft)
    stores.spend(game, cost)
    days = max(1, round(points / MEND_A_DAY))
    game.advance_days(days)
    craft.hp = kind.hull
    game.add_log(f"{craft.name} made whole: {points} points, "
                 f"{cost.get('credits', 0):,} credits, {days} day"
                 f"{'' if days == 1 else 's'}.", "good")
    return {"ok": True, "points": points, "days": days,
            "paid": int(cost.get("credits", 0))}


def knit(game, days: float) -> list:
    """What a grown craft does about her own hull, in her cradle.

    The reason a captain buys grown: she comes back from a run at half and
    puts herself back together off the hold, without a yard and without a
    bill. Slow, and it stops the moment the biomass does.
    """
    said = []
    for craft in craft_sim.aboard(game):
        kind = craft_sim.kind_of(craft)
        if kind.family != "grown" or craft.state != "cradled":
            continue
        want = min(kind.hull - craft.hp, KNIT_A_DAY * days)
        if want <= 0:
            continue
        fed = stores.take(game, "biomass", want * MEND_MATTER,
                          hold_first=True)
        got = want - fed / MEND_MATTER if MEND_MATTER else want
        if got <= 0:
            continue
        craft.hp = min(kind.hull, int(round(craft.hp + got)))
        if craft.hp >= kind.hull:
            said.append(f"{craft.name} has knitted herself whole again.")
    return said


# ── selling one ────────────────────────────────────────────────────────────

def worth(craft) -> int:
    """What a yard pays for her: salvage, and less for a wreck."""
    kind = craft_sim.kind_of(craft)
    share = table.SALVAGE * (0.4 + 0.6 * max(0.0, craft.hp / kind.hull))
    value = kind.cost.get("credits", 0) * share
    value += sum(n * material_value(key) * share
                 for key, n in kind.cost.items() if key != "credits")
    return round(value)


def can_sell(game, craft) -> tuple:
    if craft is None or craft.state == "lost":
        return False, "There is no such craft aboard."
    if craft.state == "down":
        return False, f"{craft.name} is on a world. Lift her off first."
    if craft.state == "out":
        return False, f"{craft.name} is out. Bring her in first."
    return shipyard.can_refit_here(game)


def sell(game, craft) -> dict:
    """Off the cradle and off the books, for what a yard will give."""
    ok, why = can_sell(game, craft)
    if not ok:
        return {"ok": False, "why": why}
    paid = worth(craft)
    game.credits += paid
    game.craft = [c for c in (game.craft or []) if c is not craft]
    game.add_log(f"{craft.name} sold off the cradle for {paid:,}.", "")
    return {"ok": True, "paid": paid}


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
