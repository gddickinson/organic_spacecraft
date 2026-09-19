"""What a port will do for you besides trade.

Repairs, a paid word, and a fortnight of somebody else's bench time. All three
lived in `PortView` as methods that spent credits directly, so none of them
could be performed or measured without a screen in front of them.
"""

from __future__ import annotations

from . import assembly
from . import loyalty as loyalty_sim
from . import rumours as rumour_sim

#: What a fortnight on a port's bench costs, and what it banks.
STUDY_FEE = 4000
STUDY_POINTS = 220
STUDY_DAYS = 14


#: What a yard charges for each point of hull it puts back. Plate is cut and
#: welded by somebody holding a torch; a grown hull is fed and coaxed, and the
#: tissue does most of the work.
REPAIR_RATE_FABRICATED = 26
REPAIR_RATE_GROWN = 15


def repair_quote(game) -> dict:
    """What the drydock would charge to close every breach, and for how much.

    **The price was the screen's.** `PortView._services` worked it out and
    handed it to `repair` as an argument, so the till charged whatever figure
    the caller brought — a rule living in a button, and a door any other
    caller could have walked through with its own number.
    """
    damage = sum(layer.max - layer.hp for layer in game.ship.layers)
    rate = (REPAIR_RATE_FABRICATED if game.ship_stats.family == "fabricated"
            else REPAIR_RATE_GROWN)
    rate *= assembly.effect(game, "repairs", 1.0)     # Harbour Dues Reform
    return {"damage": damage, "cost": round(damage * rate)}


def repair(game) -> dict:
    """Put the hull back to specification. The yard does not do it for love."""
    quote = repair_quote(game)
    cost = quote["cost"]
    if quote["damage"] < 1:
        return {"ok": False, "why": "There is nothing to repair.", "text": ""}
    if game.credits < cost:
        return {"ok": False, "why": f"They want {cost:,} for the work.",
                "text": ""}
    game.credits -= cost
    for layer in game.ship.layers:
        layer.hp = layer.max
    game.ship.disabled = []
    loyalty_sim.record(game, "repair")
    text = "Hull restored to specification in dock."
    game.add_log(text, "good")
    return {"ok": True, "why": "", "text": text, "cost": cost}


def clear_faults(game) -> dict:
    """Bring disabled fittings back on line. Costs nothing but the standing."""
    cleared = len(game.ship.disabled)
    game.ship.disabled = []
    return {"ok": True, "cleared": cleared}


def buy_rumour(game, rumour, paid: bool, rng=None) -> dict:
    """Pay for a lead, or lean on the bar and hope.

    The luck of listening is drawn here when the caller brings none — the
    port screen used to draw it itself, which is a roll in the wrong layer.
    """
    rng = rng if rng is not None else game.rng(f"listen-{rumour.id}")
    # The price follows the source (`rumours.price_of`), so the counter charges
    # for a story worth having rather than for a story told loudly.
    price = rumour_sim.price_of(game, rumour)
    if paid:
        if game.credits < price:
            return {"ok": False, "why": "Not enough on hand for that."}
        game.credits -= price
    elif not rng.chance(0.45):
        return {"ok": False, "why": "They stopped talking when you got close."}
    rumour_sim.take(game, rumour, paid)
    return {"ok": True, "paid": paid, "price": price if paid else 0}


def commission_study(game) -> dict:
    """Buy a fortnight of a port's bench. Money for time you did not spend."""
    if game.credits < STUDY_FEE:
        return {"ok": False, "why": f"The bench costs {STUDY_FEE:,}."}
    game.credits -= STUDY_FEE
    game.research.banked += STUDY_POINTS
    game.advance_days(STUDY_DAYS)
    return {"ok": True, "fee": STUDY_FEE, "points": STUDY_POINTS,
            "days": STUDY_DAYS}
