"""Scenes the living-hull checks stand a ship in. Not a suite.

Split from `test_adaptation.py` along the seam between *where the hull is*
and *what is claimed about it*: every function here puts a real game into a
real state — at a dim star, alongside a Fleet Hub, in a fight, over an ocean
— through the same fields and doors the game itself uses.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import adaptation as adapt_sim
from ..sim.ship import build_layers, make_ship


def fresh(seed: str, chassis: str | None = None):
    """A new chronicle, optionally in a different hull."""
    game = new_game(seed)
    if chassis is not None:
        ship = make_ship(chassis, [])
        build_layers(ship, game.bonuses)
        game.ship = ship
        game.fleet = [ship]
        game.recompute()
    return game


def under_star(game, dark: bool) -> bool:
    """Move the hull to a system under a dim star, or a glaring one."""
    for system in game.galaxy.systems:
        dim = system.heat < adapt_sim.DARK_BELOW
        bright = system.heat >= adapt_sim.GLARE_FROM
        if (dark and dim) or (not dark and bright):
            game.location_id = system.id
            game.orbit_body = None
            return True
    return False


def under_plain_star(game) -> bool:
    for system in game.galaxy.systems:
        if adapt_sim.DARK_BELOW <= system.heat < adapt_sim.GLARE_FROM:
            game.location_id = system.id
            game.orbit_body = None
            return True
    return False


def at_hub(game) -> bool:
    """Put the hull alongside an anchorage with a gestation bay."""
    from ..sim import anchorage
    for system in game.galaxy.systems:
        for berth in anchorage.in_system(game, system):
            if berth.offers("gestation"):
                game.location_id = system.id
                game.orbit_body = berth.body_id
                return True
    return False


def away_from_hubs(game) -> bool:
    """Alongside nothing, in a system without a port."""
    for system in game.galaxy.systems:
        if system.port is None:
            game.location_id = system.id
            game.orbit_body = None
            return True
    return False


def fight(game, seed: str, turns: int = 30) -> float:
    """A real engagement against a Concordat hull; returns hull hp lost."""
    from ..sim import combat, encounters
    from .captain_ai import orders
    rng = RNG(f"adapt-fight-{seed}")
    before = sum(layer.hp for layer in game.ship.layers)
    battle = combat.start(game.ship, game.ship_stats,
                          encounters.make_enemy(rng, "concordat", 2.0),
                          bonuses=game.bonuses, officers=game.officers,
                          game=game, rng=rng)
    for _ in range(turns):
        if battle.over:
            break
        combat.take_turn(battle, orders(battle), rng)
    return before - sum(layer.hp for layer in game.ship.layers)


def over_ocean(game) -> int | None:
    """Stand over a subsurface ocean with a melt head fitted; its index."""
    for system in game.galaxy.systems:
        for index, body in enumerate(system.bodies):
            if body.biome == "subsurface":
                game.location_id = system.id
                game.orbit_body = None
                if "melt_head" not in game.ship.fitted:
                    game.ship.fitted.append("melt_head")
                game.ship.cargo["volatiles"] = 400
                game.recompute()
                return index
    return None


def emerging(game, adaptation_id: str, ship=None) -> dict:
    """Cross the threshold for one adaptation and let a day find it."""
    ship = ship if ship is not None else game.ship
    grown = adapt_sim.ADAPTATIONS_BY_ID[adaptation_id]
    ship.stress[grown.channel] = float(grown.threshold)
    under_plain_star(game)
    game.advance_days(1)
    return ship.emerging


def stocked(game, tonnes: float = 200.0) -> None:
    """Growth material in the depot, where the stores draw first."""
    for key in ("phosphate", "biomass"):
        game.stores[key] = tonnes
