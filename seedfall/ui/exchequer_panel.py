"""The public purse, from the outside: what each power earns and is building.

Everything on this panel comes from `sim/exchequer.ledger`, which is computed by
the same `income` and `outlay` the sim spends from. There is deliberately no
arithmetic here — a screen that works out its own version of a number the sim
already knows is how a forecast comes to disagree with the act it forecasts.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..sim import exchequer as exchequer_sim
from .widgets import Panel, label, note, spacer


def build(game) -> Panel:
    rows = exchequer_sim.ledger(game)
    total = exchequer_sim.summary(game)
    p = Panel("The public purse")
    p.add(note("Ports are not scenery. Each one pays its holder in proportion "
               "to its size and costs the square of it, so an outpost and a "
               "station both clear about the same and a Fleet Hub very nearly "
               "pays for itself and no more. A surplus gets built with. A "
               "deficit has to give something up."))
    p.add_row("Berths in the sector",
              f"{total['ports']} · {total['levels']} levels between them")
    p.add_row("Built since you started",
              f"{total['built']} works · {total['lost']} given up",
              "chloro" if total["built"] else "dim")

    for row in rows:
        p.add(spacer(4))
        p.add(label(row["name"], "h3", row["tint"]))
        p.add_row("In hand", cr(row["credits"]),
                  "warn" if row["credits"] < 0 else "")
        p.add_row("A day of it",
                  f"{cr(row['took'])} in · {cr(row['paid'])} out · "
                  f"{cr(row['margin'])} clear",
                  "chloro" if row["margin"] > 0 else "warn")
        p.add_row("Holds", f"{row['ports']} berths · {row['levels']} levels"
                           + (f" · {row['pinched']} pinched by a shortage"
                              if row["pinched"] else ""),
                  "warn" if row["pinched"] else "")
        p.add_row("Has paid for",
                  f"{row['works']} works · {row['ventures']} ventures"
                  + (f" · {row['losses']} steps lost" if row["losses"] else ""))
        p.add_row("Next", row["next"],
                  "warn" if row["credits"] < 0 else "")
        if row["last"]:
            p.add(note(f"Last: {row['last']}."))
    return p
