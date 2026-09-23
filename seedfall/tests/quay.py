"""Putting a chronicle at a quay, the way the game does.

Checks have always moved a chronicle by writing `game.location_id` and
leaving it there. That was enough while the Port dealt with any hull
anywhere in the system, and it is not any more: `sim/quayside` asks where
the hull actually is, so a chronicle teleported into a system is a hull
adrift in it — with, in one measured case, a billion kilometres between it
and the counter it was buying from.

`stand_at` is what "the captain is dealing at this quay" means now: in the
system, **made fast to its quay** and the crew ashore, which is the state
`sim/crossing` leaves a hull in when the harbourmaster brings her in. Use it
wherever a check teleports in order to trade; use plain `location_id` when
the check is about being *away* from the counter.
"""

from __future__ import annotations

from ..sim import market as market_sim


def stand_at(game, system, note: bool = True):
    """Move the chronicle to `system` and make it fast to the quay there."""
    game.location_id = system.id
    berth = f"port-{system.id}" if getattr(system, "port", None) else ""
    game.berth = game.ashore = berth
    if note and getattr(system, "port", None) and getattr(system, "market", None):
        market_sim.note_prices(game, system,
                               game.rep.get(system.port.faction, 0),
                               game.ship_stats.trade)
    return system


def cast_off(game):
    """The other state: in the system, alongside nothing."""
    game.berth = game.ashore = ""
    return game
