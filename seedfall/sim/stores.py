"""What the captain has to hand, and the one order it is spent in.

Two places hold matter: the depot (`game.stores`), which is location-free and
belongs to the holdings, and the hold (`game.ship.cargo`), which is aboard.
"Have I got it" is the sum of the two, and that sum was written out six times
over — in colony, shipyard, works, gates, diplomacy, dormancy, mining, robots,
survey and reach — with four separate copies of the spending that goes with it.

**And the copies spent in opposite orders.** `colony._spend` and
`shipyard.pay` drew on the depot first and left the hold alone; `works`,
`gates`, `diplomacy`, `dormancy`, `mining`, `robots` and `survey` emptied the
hold first and only then touched the depot. Biomass is crew food and
volatiles are reaction mass, so the same work planted from the same stocks
either left the crew fed and the tank full or ate both, depending on which
screen it was ordered from. A work that asks 30 t of biomass, started with 30
t in the depot and the opening larder of 20.5 t aboard, took **all 20.5 t of
the larder** and 9.5 t of the depot; planting a colony with the same bill
took the depot's 30 and left the larder alone. `test_exploits` pins the one
order.

One rule now: **materials come out of the depot first**, and the hold pays
only what the depot cannot. The hold is what keeps the ship alive; the depot
is what the holdings are for.

Two draws are deliberately *not* this rule, and say so where they live: the
crew eat what is aboard (`upkeep`), and a delivery is cargo *carried*
(`contracts`). Both go through `take(..., hold_first=True)` so the order is
still decided here and nowhere else.
"""

from __future__ import annotations

from .ship import add_cargo


def held(game, key: str) -> float:
    """How much of `key` the captain can reach: credits, or depot plus hold."""
    if key == "credits":
        return float(game.credits)
    return float(game.stores.get(key, 0) + game.ship.cargo.get(key, 0))


def lacking(game, cost: dict) -> list[tuple[str, float, float]]:
    """Everything in `cost` there is not enough of, as (key, need, have)."""
    return [(key, need, held(game, key)) for key, need in cost.items()
            if held(game, key) < need]


def take(game, key: str, amount: float, hold_first: bool = False) -> float:
    """Draw `amount` of one material. Returns what could not be found.

    Depot first unless `hold_first` — see the module docstring for the two
    draws that want the other order, and why.
    """
    left = max(0.0, float(amount))
    order = ("hold", "depot") if hold_first else ("depot", "hold")
    for where in order:
        if left <= 1e-9:
            break
        if where == "depot":
            have = game.stores.get(key, 0.0)
            spent = min(have, left)
            if spent > 0:
                game.stores[key] = max(0.0, have - spent)
        else:
            have = game.ship.cargo.get(key, 0.0)
            spent = min(have, left)
            if spent > 0:
                add_cargo(game.ship, key, -spent)
        left -= max(0.0, spent)
    return max(0.0, left)


def spend(game, cost: dict) -> float:
    """Pay a bill of credits and materials. Returns the total not found.

    Callers check `lacking` first; the return is there so a caller that
    cannot (a running upkeep, say) can tell what went short.
    """
    short = 0.0
    for key, need in cost.items():
        if key == "credits":
            game.credits -= need
            continue
        short += take(game, key, need)
    return short
