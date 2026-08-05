"""What the exchequer's screens read: one row per power, and a sector total.

Split from `sim/exchequer.py` when it went past five hundred lines, along
the seam that file's own banner already marked ("what the screens read").
The seam is real: everything here is a *query* — it decides nothing, spends
nothing and moves no port — while `sim/exchequer` holds the purse, the
ladder and the acts that change the map.

`ui/exchequer_panel.py` is the one caller, and it reads these functions from
here rather than through a re-export, so there is one door and not two.
"""

from __future__ import annotations

from ..data.exchequer import RESERVE
from ..data.factions import FACTIONS_BY_ID
from . import diplomacy as dip
from .exchequer import (Purse, holdings, income, margin, outlay, purse,
                        scarce, works_open)


def settlement_of(game, power: str) -> list:
    from . import settlement as settlement_sim
    return settlement_sim.of_power(game, power)


def settlement_income(game, power: str) -> float:
    from . import settlement as settlement_sim
    return settlement_sim.income(game, power)


def ledger(game) -> list[dict]:
    """One row per power, from the same functions `settle` spends from."""
    out = []
    for power in dip.POWERS:
        p = purse(game, power)
        held = holdings(game, power)
        out.append({
            # Off the purse itself rather than the loop variable: a row that
            # says whose money it is should be asking the money.
            "power": p.power,
            "name": FACTIONS_BY_ID[p.power].short,
            "tint": FACTIONS_BY_ID[p.power].tint,
            "credits": p.credits,
            "took": income(game, power),
            "paid": outlay(game, power),
            "margin": margin(game, power),
            "ports": len(held),
            "levels": sum(s.port.level for s in held),
            "pinched": sum(1 for s in held if scarce(game, s)),
            "settlements": len(settlement_of(game, p.power)),
            "ground": settlement_income(game, p.power),
            "last": p.last,
            "works": p.works,
            "losses": p.losses,
            "ventures": p.ventures,
            "dues": p.dues,
            "levies": p.levies,
            "next": _next_work(game, power, p),
        })
    out.sort(key=lambda row: -row["credits"])
    return out


def _next_work(game, power: str, p: Purse) -> str:
    """What this power is saving up for, in words."""
    if p.credits < 0:
        return "in deficit — something will have to go"
    open_now = works_open(game, power)
    if not open_now:
        return "nothing left to build"
    cost, system, what = open_now[0]
    short = ("found a berth at" if what == "found"
             else "settle" if what.startswith("settle:") else "build up")
    want = cost + RESERVE - p.credits
    if want <= 0:
        return f"about to {short} {system.name}"
    rate = margin(game, power)
    when = f", {round(want / rate)} days at this rate" if rate > 0 else ""
    return f"{short} {system.name} — {round(want):,} short{when}"


def summary(game) -> dict:
    """The sector's infrastructure, in one line, for a check or a screen."""
    ports = [s for s in game.galaxy.systems if s.port]
    return {
        "ports": len(ports),
        "levels": sum(s.port.level for s in ports),
        "built": sum(purse(game, p).works for p in dip.POWERS),
        "lost": sum(purse(game, p).losses for p in dip.POWERS),
        "purse": sum(purse(game, p).credits for p in dip.POWERS),
    }
