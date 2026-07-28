"""A captain who plays the long game, for the playability checks.

Lifted out of `test_play.py` when that file crossed five hundred lines.
It is the thing that catches deadlocks: it must always be able to make
progress, and when it cannot the game has a hole a player would fall into.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import actions
from ..sim import trade as trade_sim
from ..sim.ship import add_cargo, cargo_free
from ..world.economy import sell_price
from ..world.galaxy import in_range


def _bot(seed: str, years: int = 5):
    """A deliberately simple captain: survey, sell the data, refuel, move on.

    If this cannot stay solvent, the early game is not playable.
    """
    g = new_game(seed)
    r = RNG(f"bot-{seed}")
    while g.day < 365 * years and not g.dead and not g.victory:
        sysm = g.system
        todo = [i for i, b in enumerate(sysm.bodies) if not b.surveyed]
        if todo:
            actions.survey(g, todo[0])
            continue

        if sysm.port and sysm.market:
            rep = g.rep.get(sysm.port.faction, 0)
            data = g.ship.cargo.get("survey", 0)
            if data >= 1:
                price = sell_price(sysm.market, "survey", rep, g.ship_stats.trade) or 250
                g.credits += data * price
                add_cargo(g.ship, "survey", -data)
                g.adjust_rep(sysm.port.faction, min(6, data * 0.4))
            fuel_price = (sell_price(sysm.market, "volatiles", rep, 0) or 40) * 1.35
            want = 70 - g.ship.cargo.get("volatiles", 0)
            afford = int(min(want, g.credits * 0.6 // max(1, fuel_price)))
            if afford > 0:
                g.credits -= afford * fuel_price
                add_cargo(g.ship, "volatiles", afford)

        reach = in_range(g.galaxy.systems, sysm, g.ship_stats.jump)
        reach = [s for s in reach if s.bloom < 0.3] or reach
        if not reach:
            break
        affordable = [s for s in reach
                      if g.ship.cargo.get("volatiles", 0)
                      >= actions.jump_quote(g, s)["fuel"]]
        if not affordable:
            # top up from ice rather than sitting there
            ice = next((i for i, b in enumerate(sysm.bodies)
                        if b.resources.get("volatiles", 0) > 0.1), None)
            if ice is None:
                break
            sysm.bodies[ice].surveyed = True
            # A hold with no room cannot take reaction mass either, so make
            # some. Without this the bot span forever: extract refuses, no
            # time passes, and the year limit is never reached.
            if cargo_free(g.ship, g.ship_stats) < 20:
                spare = max((c for c in g.ship.cargo if c != "volatiles"),
                            key=lambda c: g.ship.cargo[c], default=None)
                if spare is None:
                    break
                trade_sim.jettison(g, spare)
            if not actions.extract(g, ice, 40).get("ok"):
                break
            continue
        target = next((s for s in affordable if not s.visited), r.pick(affordable))
        if not actions.jump_to(g, target.id)["ok"]:
            break
    return g
