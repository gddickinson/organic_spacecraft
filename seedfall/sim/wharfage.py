"""The due on cargo crossing a quay — one door for the rate and for the act.

`rate` is the only place the charge is worked out, `due_on` the only place it is
applied to a value, and `collect` the only place money moves. The screen asks
`quote`, which asks all three. So the line on the market board, the figure in
the ship's log and the credit in the power's purse cannot come apart — which is
the failure this project has found more often than any other, and found again
this cycle in the port screen's own price columns.

Nothing here reaches for Qt, and nothing here decides *whether* a trade happens:
`sim/trade.py` still owns the transaction and calls in.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID, standing
from ..data.wharfage import LEVEL_STEP, RELIEF, RELIEF_AT, WHARFAGE
from . import diplomacy as dip
from . import exchequer as exchequer_sim


def holder(game, system) -> str | None:
    """The power that takes a due here, or None if nobody does.

    A free port is free. `exchequer.holdings` already refuses to pay a power for
    an independent freehold or for a Free Port the captain built, so charging a
    due into one would be money leaving the sector — and the captain being
    charged rent on their own quay.
    """
    port = getattr(system, "port", None)
    if port is None or port.independent or port.player_built:
        return None
    return port.faction if port.faction in dip.POWERS else None


def rate(game, system) -> float:
    """The share of a transaction this quay takes, standing included."""
    if holder(game, system) is None:
        return 0.0
    port = system.port
    base = WHARFAGE * (1.0 + LEVEL_STEP * (port.level - 1))
    lean = max(-1.0, min(1.0, game.rep.get(port.faction, 0) / RELIEF_AT))
    return max(0.0, base * (1.0 - RELIEF * lean))


def due_on(game, system, value: float) -> int:
    """The due on a transaction worth `value`, in whole credits."""
    return max(0, round(rate(game, system) * max(0.0, value)))


def collect(game, system, value: float) -> int:
    """Take the due out of the captain's account and into the holder's purse.

    Both sides in one function on purpose: a fee that is deducted in one place
    and credited in another is a fee that can be deducted and credited for
    different amounts. Returns what was taken.
    """
    who = holder(game, system)
    if who is None:
        return 0
    amount = due_on(game, system, value)
    if amount <= 0:
        return 0
    game.credits -= amount
    p = exchequer_sim.purse(game, who)
    p.credits += amount
    p.dues += amount
    return amount


def unit_cost(game, system, price: float) -> float:
    """What a tonne actually costs at this counter — price plus its due.

    `trade.buy` sizes the purchase with this rather than with the posted price,
    because a hold filled to the last credit of the posted price could not pay
    the due at the end of it.
    """
    return price * (1.0 + rate(game, system))


def quote(game, system) -> dict:
    """What the market board needs to say about the charge, in one call."""
    who = holder(game, system)
    share = rate(game, system)
    port = getattr(system, "port", None)
    return {
        "holder": who,
        "name": FACTIONS_BY_ID[who].short if who else "",
        "rate": share,
        "pct": share * 100.0,
        "free": who is None,
        "why": ("your own Free Port" if port is not None and port.player_built
                else "an independent freehold" if port is not None
                and port.independent else ""),
        "standing": standing(game.rep.get(port.faction, 0))[0] if port else "",
    }


def line(game, system) -> str:
    """The market board's sentence about the due. Empty where there is none."""
    told = quote(game, system)
    if told["free"]:
        if told["why"]:
            return f"No wharfage here — {told['why']}."
        return ""
    return (f"{told['name']} takes {told['pct']:.1f}% of everything over this "
            f"counter, in and out, at your standing of {told['standing']}.")
