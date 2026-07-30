"""Selling a process: who would pay for it, and what it does to their quays.

The whole panel is `sim/industry.ledger` and `forecast`. In particular the price
comes from `industry.worth` and the button is guarded by `industry.can_licence` —
the same function `industry.licence` calls before it takes the money — because a
board that works out its own version of a price eventually offers one the till
will not honour.

The forecast is quoted in *both* directions, which is the design statement: a
berth that starts making a thing stops paying well for it, so the row that says
what they will pay you also says what you will stop earning there.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..sim import industry as industry_sim
from .widgets import Panel, button, label, note, spacer


def build(view, game) -> Panel | None:
    """None when the captain has nothing anybody could use."""
    rows = industry_sim.ledger(game)
    if not rows:
        return None
    told = industry_sim.summary(game)
    p = Panel("What your work is worth to somebody else")
    p.add(note("A process is a technology that makes a thing. License one to a "
               "power and it becomes an industry at every berth they hold: the "
               "good gets made there, so it gets cheaper there. They pay out of "
               "their own treasury, and they pay for the berths they have — a "
               "power with two quays will not find what one with nine will."))
    p.add_row("Processes you could sell",
              f"{told['sellable']} of {told['processes']}")
    if told["licensed"]:
        p.add_row("Licences granted",
                  f"{told['licensed']} · {cr(told['earned'])} earned",
                  "chloro")

    for row in rows:
        process, tech, best = row["process"], row["tech"], row["best"]
        p.add(spacer(4))
        head = process.name + ("  ✦ illicit" if process.illicit else "")
        p.add(label(head, "h3", "warn" if process.illicit else ""))
        p.add(note(process.blurb))
        p.add_row("From", f"{tech.name} · {tech.cost:,} points")
        if row["held_by"]:
            p.add_row("Already running at", ", ".join(row["held_by"]), "dim")

        if best is None:
            p.add(note("Nobody will take it just now — see the offers below."))
        else:
            fc = row["forecast"]
            p.add_row("Best offer",
                      f"{best['name']} · {cr(best['price'])} for "
                      f"{best['berths']} berth(s)", "chloro")
            if fc["opened"]:
                p.add_row("Opens", f"a trade in {fc['good']} at "
                                   f"{fc['opened']} berth(s) that has none now",
                          "warn")
            first = fc["rows"][0] if fc["rows"] else None
            if first is None:
                p.add_row("What it does to their prices",
                          "nothing they hold stocks it")
            elif first["buy_now"] is None:
                p.add_row("What it does to their prices",
                          f"{fc['good']} would go for about "
                          f"{cr(first['buy_then'])}; there is no trade in it "
                          "at their berths at all today")
            else:
                p.add_row("What it does to their prices",
                          f"{fc['good']} settles about "
                          f"{cr(first['buy_then'])} where it holds at "
                          f"{cr(first['buy_now'])} now")
            if fc["your_loss"] > 0:
                p.add_row("What it costs you",
                          f"{cr(fc['your_loss'])} a tonne less when you sell "
                          f"{fc['good']} at their quays", "warn")
            p.add(button(f"LICENCE TO {best['name'].upper()} — "
                         f"{cr(best['price'])}",
                         lambda _=None, pr=process, po=best["power"]:
                         view.sell_process(pr, po)))

        for offer in industry_sim.offers(game, process):
            if offer["holds"]:
                continue
            p.add_row(offer["name"],
                      f"{cr(offer['price'])} · {offer['berths']} berths"
                      if offer["ok"] else offer["why"],
                      "" if offer["ok"] else "dim")
    return p
