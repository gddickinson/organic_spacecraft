"""Haulers: the hulls a trading house puts on its lines, and where to get one.

A hauler is a real hull in the captain's fleet, of a class built to carry
freight (`data/freightlines.HAULER_TIERS`). You can lay one down at a yard like
any other hull, or **buy one used** from a power's yard: the Concordat's own
cargo hulls, tired but sound, sold with the drive the Yards fit as standard.

Buying is the cheap way in, not a cheap hull. Measured with a scripted captain
who plays the house: an explorer's purse reaches 40,000
around day 600-750 on the three play-test seeds, and a new TENDER all in —
20,400 credits, 30 t of alloy and 6 of silicon bought at the counter — is some
31,000 of it, which left no working capital and no line opened in three years
on any of the three. A used one is `USED_SHARE` of the full bill, and never
less than a breaker pays for her (`shipyard.scrap_value` is 45% of the
cheapest build), so a bought hull broken up is money lost, never made.
"""

from __future__ import annotations

from ..data.chassis import CHASSIS_BY_ID
from ..data.freightlines import HAULER_TIERS
from ..data.parts import material_value
from . import diplomacy as dip
from . import exchequer as exchequer_sim
from .ship import build_layers, is_destroyed, make_ship

#: What a used hull costs, as a share of the full bill of a new one with its
#: drive (credits, and its matter valued as itself).
USED_SHARE = 0.7

#: How much of her integrity a used hull comes with.
USED_HULL = 0.7

#: The drive the Yards sell each of their cargo hulls with. A bare TENDER jumps
#: 4.1 ly, and the nearest neighbour in a generated sector is 4.1 to 6.1 ly
#: away (measured on verge-7): a hull sold without a drive would reach nothing.
USED_FIT = {"tender": ["ion_cluster"], "drayhorse": ["ion_cluster"],
            "kiln": ["ion_cluster"], "caravel": ["ion_cluster"]}


def can_haul(game, ship) -> tuple[bool, str]:
    """May this hull be put on a line? The one rule."""
    chassis = CHASSIS_BY_ID[ship.chassis]
    if chassis.tier not in HAULER_TIERS:
        return False, f"A {chassis.name} is not built to carry freight."
    if ship is game.ship or ship.uid == game.ship.uid:
        return False, "That is your flag."
    if getattr(ship, "escort", False):
        return False, f"{ship.name} is sailing with you."
    if getattr(ship, "line_id", None) is not None:
        return False, f"{ship.name} is already working a line."
    if is_destroyed(ship) or getattr(ship, "crew", 0) < 1:
        return False, f"{ship.name} has nobody aboard to sail her."
    if ship.docked_at is None:
        return False, f"{ship.name} is not berthed anywhere."
    return True, ""


def haulers(game) -> list:
    """Every hull built to haul, and whether each can take a line now."""
    out = []
    for ship in game.fleet:
        if CHASSIS_BY_ID[ship.chassis].tier in HAULER_TIERS:
            ok, why = can_haul(game, ship)
            out.append((ship, ok, why))
    return out


def used_terms(game, chassis_id: str) -> dict:
    """What the yard here asks for one of its used cargo hulls, or why not."""
    from . import shipyard
    fit = USED_FIT.get(chassis_id)
    if fit is None:
        return {"ok": False, "why": "The Yards do not sell that one used."}
    here = game.system
    port = getattr(here, "port", None)
    if (port is None or "shipyard" not in port.services or port.independent
            or port.player_built or port.faction not in dip.POWERS):
        return {"ok": False, "why": "There is no power's yard here selling "
                                    "hulls."}
    chassis = CHASSIS_BY_ID[chassis_id]
    bill = shipyard.cost_of(chassis, fit, fabricator=False)
    worth = bill["credits"] + sum(material_value(k) * n
                                  for k, n in bill.items() if k != "credits")
    price = round(worth * USED_SHARE)
    out = {"ok": True, "why": "", "price": price, "chassis": chassis,
           "fit": list(fit), "hull": USED_HULL, "power": port.faction,
           "port": f"{here.name} {port.name}"}
    if game.credits < price:
        out.update(ok=False, why=(f"The yard wants {price:,} for her and the "
                                  f"purse holds {round(game.credits):,}."))
    return out


def buy_used(game, chassis_id: str) -> dict:
    """Buy a used cargo hull here; she joins the fleet berthed at this quay,
    and the price goes to the power whose yard it is."""
    terms = used_terms(game, chassis_id)
    if not terms["ok"]:
        return terms
    ship = make_ship(chassis_id, terms["fit"],
                     f"{terms['chassis'].name.title()} {len(game.fleet)}")
    build_layers(ship, game.bonuses)
    for layer in ship.layers:
        layer.hp = layer.max * USED_HULL
    ship.docked_at = game.location_id
    game.credits -= terms["price"]
    exchequer_sim.purse(game, terms["power"]).credits += terms["price"]
    game.fleet.append(ship)
    game.add_log(f"Bought {ship.name}, a used {terms['chassis'].name}, from "
                 f"the yard at {terms['port']} for {terms['price']:,}.", "good")
    return {"ok": True, "ship": ship, **terms}
