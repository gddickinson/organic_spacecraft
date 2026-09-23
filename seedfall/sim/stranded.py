"""When a captain cannot move, and what is left to them.

Split out of `sim/actions.py` when that crossed five hundred lines, along a
seam that is a real one rather than a line count: everything left in
`actions` is a thing a captain *chooses* to do — jump, survey, work a body,
dive. These three are the other question entirely, and the one a sandbox has
to be able to answer honestly: **is this chronicle over?**

`is_stranded` is the check, and its docstring is a list of the ways the
answer has been wrong. `distress_call` is the way out that costs something,
and `launch_exodus` is the way out that ends it.
"""

from __future__ import annotations

from .actions import jump_quote
from .ship import add_cargo

from . import mining
from .actions import jump_quote
from .ship import add_cargo


def is_stranded(game) -> bool:
    """No fuel for any reachable system, and no way to make any here.

    Every way out has to be asked of whatever actually grants it, not guessed
    at with a literal. Both of these were guesses:

    * The ice test read `resources["volatiles"] > 0.05`, which is how *rich* a
      body is. Whether a rig may be put on it is `mining.worked_out`, which
      reads how much has been *taken* — a different quantity entirely, so a
      rich body worked to exhaustion read as fuel for ever. Measured: a
      captain at Amber Anchorage with 0 credits and 2.3 tonnes, one body in
      the system holding 0.271 volatiles and worked out, `extract` refusing
      it and this function answering "you can still move".
    * The port test fell back to `or 40` when `buy_price` returned None, and
      None is what it returns when the market holds none to sell. No port in
      the sector is currently dry, so nothing was reaching it — but a way out
      that does not exist must not count as one.
    """
    from ..world.galaxy import in_range
    from . import mining

    reach = in_range(game.galaxy.systems, game.system, game.ship_stats.jump)
    fuel = game.ship.cargo.get("volatiles", 0)
    if any(fuel >= jump_quote(game, s)["fuel"] for s in reach):
        return False
    if game.system.port and game.system.market:
        # A port can sell you fuel, if it has any and you can pay for it —
        # and **what is in the hold is money at a counter.** This read
        # `game.credits` alone, so a captain standing at a market with
        # nothing in the purse and 15,000 credits of silicon aboard was
        # called stranded, and the tow that answered charged them standing
        # to be dragged away from the very quay that would have fixed it.
        from . import market as market_sim
        cheapest = min((jump_quote(game, s)["fuel"] for s in reach), default=99)
        # The counter's quote, like the sellable side below it already was —
        # this function priced escape at the raw price and salvation at the
        # quoted one, which is two answers to the same question.
        price = market_sim.quote_buy(game, game.system, "volatiles")
        sellable = 0.0
        for cid, tonnes in game.ship.cargo.items():
            if cid == "volatiles" or tonnes <= 0:
                continue
            offer = market_sim.quote_sell(game, game.system, cid)
            if offer:
                sellable += offer * tonnes
        if price is not None and (game.credits + sellable) >= price * (cheapest - fuel):
            return False
    # Can we make our own out of ice in this system? Only off a body a rig
    # will actually go on — the same question `extract` asks.
    if game.ship_stats.drink > 0 and any(
            b.resources.get("volatiles", 0) > 0.05 and not mining.worked_out(b)
            for b in game.system.bodies):
        return False
    return bool(reach)


def distress_call(game) -> dict:
    """Broadcast for a tow. Somebody always comes; nobody comes for free."""
    from ..world.galaxy import nearest_port
    if not is_stranded(game):
        return {"ok": False, "why": "You are not stranded — you can still move."}
    port = nearest_port(game.galaxy.systems, game.system, game.galaxy)
    if port is None:
        return {"ok": False, "why": "There is no port left in the Verge to answer."}

    faction = port.port.faction
    days = 20 + game.rng("tow").int(5, 25)
    game.advance_days(days)
    if game.dead:
        return {"ok": True, "dead": True}
    game.location_id = port.id
    port.visited = True
    game.adjust_rep(faction, -12)
    add_cargo(game.ship, "volatiles", 20)
    game.credits = max(0.0, game.credits - 2000)
    game.add_log(f"Answered by {faction}. Towed to {port.name}; they logged it, "
                 "and they will remember.", "warn")
    return {"ok": True, "port": port, "days": days, "faction": faction}


def launch_exodus(game) -> dict:
    """Take the ark and go. This ends the chronicle."""
    ark = (game.ship if game.ship.chassis == "leviathan"
           else next((s for s in game.fleet if s.chassis == "leviathan"), None))
    if ark is None:
        return {"ok": False, "why": "You have no LEVIATHAN. Twelve drums, or nothing."}
    berths = sum(c.pop for c in game.colonies if c.online)
    game.flags["exodus_launched"] = True
    game.add_log("The trunk meristem stood down. The Verge is a light behind you.",
                 "good")
    game.advance_days(1)
    return {"ok": True, "ark": ark, "carried": berths}
