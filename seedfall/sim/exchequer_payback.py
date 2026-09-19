"""How long a work takes to pay for itself — the exchequer's investment rule.

Split out of `sim/exchequer.py` when it reached five hundred lines; still
asked for as `exchequer.payback`, which re-exports it. The exchequer module is
imported inside the function, so either module can be imported first.
"""

from __future__ import annotations

from ..world.galaxy import PORT_KINDS


def payback(game, power: str, cost: int, what: str, system=None) -> float:
    """Days for one work to pay for itself, or `inf` if it never does.

    **The exchequer chose by price, and price is not value.** `_invest` took the
    cheapest work it could afford, and the equilibrium the upkeep curve is built
    on means the cheap works are the ones that never pay: promoting an outpost to
    a station adds 90 a day of yield and 90 a day of upkeep — *net nothing* — and
    promoting a station to a hub is 60 a day worse than not bothering. Founding a
    berth clears 60 a day for 40,000, and settling ground clears 32 for 32,000.
    So the rule "take the cheapest" bought the two works with no return before
    either of the two with one, and a sector's powers planted **six settlements
    in year one and none in the seven years after**.

    Sorting by payback fixes it without inventing a preference: a power does the
    thing that pays for itself soonest, and the works that never pay are what it
    does with money it has nothing better to do with — which is exactly what a
    Fleet Hub is.
    """
    from .exchequer import upkeep_at, would_yield
    if what.startswith("settle:"):
        # Asked of the settlement module, which counts the years a new one
        # *loses* money — see `settlement.payback_days`. Dividing the cost by the
        # mature rate reads 1,000 days where the truth is 1,485.
        from . import settlement as settlement_sim
        return settlement_sim.payback_days()
    if what == "found":
        base = PORT_KINDS[0][2]
        gain = would_yield(game, power, system, base) - upkeep_at(base)
    else:
        # The *real* marginal gain, with this port's own multipliers — a
        # thriving capital is worth promoting and a bare outpost is not,
        # which is a texture the bare constants cannot express (they say
        # exactly zero for level 2, everywhere, for everyone).
        level = int(what.split(":", 1)[1]) if ":" in what else 0
        gain = ((would_yield(game, power, system, level) - upkeep_at(level))
                - (would_yield(game, power, system, level - 1)
                   - upkeep_at(level - 1)))
    if gain <= 0:
        return float("inf")
    return cost / gain
