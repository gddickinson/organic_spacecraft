"""What a port will do for you besides trade.

Repairs, a paid word, and a fortnight of somebody else's bench time. All three
lived in `PortView` as methods that spent credits directly, so none of them
could be performed or measured without a screen in front of them.
"""

from __future__ import annotations

from . import loyalty as loyalty_sim
from . import rumours as rumour_sim

#: What a fortnight on a port's bench costs, and what it banks.
STUDY_FEE = 4000
STUDY_POINTS = 220
STUDY_DAYS = 14


def repair(game, cost: int) -> dict:
    """Put the hull back to specification. The yard does not do it for love."""
    if game.credits < cost:
        return {"ok": False, "why": f"They want {cost:,} for the work."}
    game.credits -= cost
    for layer in game.ship.layers:
        layer.hp = layer.max
    game.ship.disabled = []
    loyalty_sim.record(game, "repair")
    game.add_log("Hull restored to specification in dock.", "good")
    return {"ok": True, "cost": cost}


def clear_faults(game) -> dict:
    """Bring disabled fittings back on line. Costs nothing but the standing."""
    cleared = len(game.ship.disabled)
    game.ship.disabled = []
    return {"ok": True, "cleared": cleared}


def buy_rumour(game, rumour, paid: bool, rng) -> dict:
    """Pay for a lead, or lean on the bar and hope."""
    kind = rumour.definition
    if paid:
        if game.credits < kind.price:
            return {"ok": False, "why": "Not enough on hand for that."}
        game.credits -= kind.price
    elif not rng.chance(0.45):
        return {"ok": False, "why": "They stopped talking when you got close."}
    rumour_sim.take(game, rumour, paid)
    return {"ok": True, "paid": paid, "price": kind.price if paid else 0}


def commission_study(game) -> dict:
    """Buy a fortnight of a port's bench. Money for time you did not spend."""
    if game.credits < STUDY_FEE:
        return {"ok": False, "why": f"The bench costs {STUDY_FEE:,}."}
    game.credits -= STUDY_FEE
    game.research.banked += STUDY_POINTS
    game.advance_days(STUDY_DAYS)
    return {"ok": True, "fee": STUDY_FEE, "points": STUDY_POINTS,
            "days": STUDY_DAYS}
