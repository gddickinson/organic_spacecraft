"""The register: what you wrote down at other ports, and how old it is."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import duration
from ..data.commodities import BY_ID
from ..sim import market as market_sim
from .widgets import Panel, Pill, label, mono_label, note, spacer


def _age_tint(confidence: float) -> str:
    if confidence > 0.7:
        return "chloro"
    if confidence > 0.35:
        return "lumen"
    return "warn"


def local_news(game, system) -> Panel | None:
    """What is happening to this market right now."""
    live = market_sim.at(game, system.id)
    if not live:
        return None
    p = Panel("On the quay")
    for shock in live:
        kind = shock.definition
        p.add(spacer(3))
        p.add(label(kind.name, "h3", kind.tint))
        p.add(note(shock.text(system.name)))
        p.add_row("Expected to last",
                  duration(max(0, shock.until - game.day)) + " more",
                  "warn" if kind.supply < 1 else "chloro")
    return p


def register(game, system) -> Panel:
    """Where your own notes say to take what you are carrying."""
    p = Panel("The register")
    known = market_sim.summary(game)
    p.add_row("Ports noted", f"{known['ports']} · {known['fresh']} still fresh",
              "chloro" if known["fresh"] else "dim")
    p.add(note("Prices you wrote down at ports you have stood in. Nobody "
               "updates them for you, and a note two years old is a rumour."))

    carrying = [(cid, n) for cid, n in game.ship.cargo.items() if n >= 1]
    if not carrying:
        p.add(spacer(3))
        p.add(note("The hold is empty. Fill it and this will tell you where "
                   "your notes say to take it."))
        return p

    for cid, held in sorted(carrying, key=lambda kv: -kv[1]):
        good = BY_ID.get(cid)
        if good is None:
            continue
        rows = [r for r in market_sim.best_markets(game, cid, selling=True)
                if r["system"].id != system.id]
        p.add(spacer(4))
        p.add(label(f"{good.name} — {round(held)} t aboard", "h3"))
        if not rows:
            p.add(note("Nowhere in the register buys this. You have not been "
                       "anywhere that trades it."))
            continue
        for row in rows:
            target = row["system"]
            marks = []
            if row["shocked"]:
                marks.append("something is happening there")
            if not row["open"]:
                marks.append("the berth there has closed — nothing left to "
                             "sell to")
            # Hops and days rather than a straight line. A light-year count is
            # not a journey: a third of what this list used to recommend was
            # unreachable at any distance, and the sort put an eight-hop port
            # above a one-hop one for three credits more.
            if not row["open"]:
                where = f"{target.name} · closed"
                worth = f"{cr(row['price'])} · when there was a berth"
            elif not row["reachable"]:
                where = f"{target.name} · beyond your jump"
                worth = f"{cr(row['price'])} · nothing you can reach"
            else:
                hops = row["hops"]
                where = (f"{target.name} · {hops} hop"
                         f"{'' if hops == 1 else 's'}, {row['days']} days")
                worth = (f"{cr(row['price'])} · {row['per_day']:,.0f} a day "
                         f"· noted {duration(row['age'])} ago")
            p.add_row(where, worth,
                      _age_tint(row["confidence"])
                      if row["reachable"] and row["open"] else "dim")
            if marks:
                p.add(note(" · ".join(marks)))
    return p
