"""The freight desk: what is worth loading here, and where it goes."""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.commodities import BY_ID
from ..data.factions import FACTIONS_BY_ID
from ..sim import freight as freight_sim
from .widgets import Panel, Pill, label, mono_label, note, spacer

_SOURCE = {
    "register": ("your own notes", "chloro"),
    "desk": ("their word for it", "osteo"),
}


def desk(game, system) -> Panel | None:
    """Shown at any port with a market. The point of the whole thing.

    Within a starting jump only about one lane in twenty is profitable, and
    finding it meant visiting every neighbour first. The runs were there; you
    could not see them.
    """
    if not system.market or not system.port:
        return None
    summary = freight_sim.summary(game, system)
    flying = freight_sim.worth_flying(game, system, limit=5)
    faction = FACTIONS_BY_ID.get(system.port.faction)

    p = Panel("The freight desk", "lumen")
    if summary["reach"]:
        p.add(note(f"{faction.short if faction else 'The harbourmaster'} will "
                   f"name {summary['reach']} of its own ports and what they "
                   "are short of. It will not quote you their board."))
    else:
        p.add(label("They will not discuss their shipping with you.", "", "warn"))

    p.add_row("Runs your notes and their word support",
              f"{summary['reachable']} in range of {summary['runs']}",
              "chloro" if summary["reachable"] else "dim")

    if not flying:
        p.add(spacer(3))
        p.add(note("Nothing here clears its own reaction mass. Ports of one "
                   "power tend to want the same things; the work on the "
                   "contracts board is the other way to earn."))
        return p

    p.add(spacer(4), mono_label("Worth loading"))
    for run, trip in flying:
        good = BY_ID.get(run.commodity)
        said, tint = _SOURCE.get(run.source, ("", ""))
        p.add(spacer(3))
        p.add(label(f"{good.name if good else run.commodity} → "
                    f"{run.target_name}", "h3", "chloro"))
        p.add(Pill(said, tint))
        p.add_row(f"{run.ly:.1f} ly · {trip['days']} days",
                  f"buy {cr(run.buy_here)} · pays about {cr(run.pays)}")
        p.add_row(f"{trip['tonnes']:g} t and the burn",
                  f"{cr(trip['outlay'])} out, {cr(trip['fuel'])} of mass")
        p.add_row("Clears about", cr(trip["net"]), "chloro")
    p.add(spacer(4))
    p.add(note("What it clears is the voyage, not the spread: a four-credit "
               "margin nine light-years away costs more in reaction mass than "
               "it pays."))
    return p
