"""Scenes the Afoot checks stand a party in: a quay, a drum, a wreck, a prize.

A fresh chronicle holds a hull and a quay and nothing else walkable, so a
check that only walked a fresh sector would be asserting about two kinds of
site and claiming seven. These put the rest into the sector: a settled drum
and a holding (`settle`), a dead hull of a chosen kind (`at_wreck`), and a
struck hull to board (`struck`).
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import afoot_sites
from ..sim import flight


def fresh(seed: str = "afoot"):
    return new_game(seed)


def at_wreck(kinds=("raider_hulk",), seeds: int = 60):
    """A chronicle moved to a system with a dead hull of one of these kinds."""
    for n in range(seeds):
        game = new_game(f"afoot-wreck-{'-'.join(kinds)}-{n}")
        for system in game.galaxy.systems:
            site = afoot_sites.derelict(game, system)
            if site is not None and site.wreck in kinds:
                game.location_id = system.id
                flight.stand_off(game)
                game.recompute()
                return game, site
    raise AssertionError(f"no {kinds} wreck in {seeds} sectors")


def at_establishment(kinds=("grand_hotel",), seeds: int = 30):
    """A chronicle standing off one of the trade's stations or bases."""
    from ..sim import places
    for n in range(seeds):
        game = new_game(f"afoot-est-{'-'.join(kinds)}-{n}")
        for system in game.galaxy.systems:
            place = next((p for p in places.in_system(game, system)
                          if p.look in kinds), None)
            if place is None:
                continue
            game.location_id = system.id
            flight.stand_off(game)
            game.orbit_body = place.body_id
            game.recompute()
            return game, afoot_sites._from_place(game, place)
    raise AssertionError(f"no {kinds} in {seeds} sectors")


def struck(game, chassis: str = "pike", cargo=None):
    """A hull that has struck to you, with something in her hold."""
    from ..sim.ship import build_layers, make_ship
    from ..sim import afoot_program
    from ..core.rng import RNG
    from ..data.chassis import CHASSIS_BY_ID
    fit = afoot_program.typical_fit(RNG("struck"), CHASSIS_BY_ID[chassis])
    hull = make_ship(chassis, fit, "Brass Nail")
    build_layers(hull)
    hull.crew = 6
    hull.cargo = dict(cargo or {"alloy": 12.0, "silicon": 3.0})
    return hull


def settle(game):
    """A drum and a holding of yours alongside the starting quay's world."""
    from ..sim import colony as colony_sim
    system = game.system
    bodies = [b for b in system.bodies]
    drum = colony_sim.Colony(
        id=9101, class_id="arca_drum", name="The Drum",
        system_id=system.id, body_id=game.orbit_body or bodies[0].id,
        need=0, online=True)
    rig = colony_sim.Colony(
        id=9102, class_id="fab_yard", name="The Yard",
        system_id=system.id, body_id=game.orbit_body or bodies[0].id,
        need=0, online=True)
    game.colonies.extend([drum, rig])
    return game


def everybody(game) -> list:
    """Every key that can walk, up to a full party, captain first."""
    from ..sim import afoot_people
    keys = [k for k, _n, _w, ok, _why in afoot_people.pool(game) if ok]
    return keys[:afoot_people.PARTY_MOST]
