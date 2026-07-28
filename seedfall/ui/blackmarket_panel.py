"""The unposted market: what they will pay here for what they forbid here."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import pct
from ..data.commodities import BY_ID
from ..data.contraband import REGIMES
from ..data.factions import FACTIONS_BY_ID
from ..sim import customs as customs_sim
from .widgets import Panel, Pill, button, label, mono_label, note, spacer


def tipoff(game, system) -> Panel | None:
    """Shown where contraband is *sold*, naming where it is worth carrying.

    Without this the whole trade is a secret: the quiet word only appears once
    you are already standing on a hostile dock with a hold full of the stuff,
    which is not a thing anybody does by accident.
    """
    port = getattr(system, "port", None)
    stocked = [cid for cid, stock in system.market.stock.items()
               if stock.supply > 0 and not BY_ID[cid].legal] if system.market else []
    if not stocked or not port:
        return None
    # Only the ports that actually post a price talk like this.
    if customs_sim.regime(port.faction) and customs_sim.regime(port.faction).outlaws:
        return None

    p = Panel("What the board does not say", "osteo")
    said = False
    for cid in stocked:
        good = BY_ID.get(cid)
        buyers = [(reg, round(good.base * (1.15 + reg.zeal * 0.7)))
                  for reg in REGIMES if cid in reg.outlaws]
        if not good or not buyers:
            continue
        said = True
        p.add(label(f"{good.name} — posted here, forbidden elsewhere", "h3",
                    "warn"))
        for reg, worth in sorted(buyers, key=lambda t: -t[1]):
            fac = FACTIONS_BY_ID.get(reg.faction)
            p.add_row(f"{fac.short if fac else reg.faction} space",
                      f"about {cr(worth)} the tonne, unposted", "chloro")
        p.add(spacer(3))
    if not said:
        return None
    p.add(note("Their dock, their rules, their search. Nobody posts these "
               "prices and nobody has to."))
    return p


def offer(game, system, on_sell, on_dump) -> Panel | None:
    """Shown only when you are carrying something this port outlaws.

    Nothing here appears on the board upstairs — the good has no posted price
    precisely because the power whose dock you are standing on will seize it.
    """
    port = getattr(system, "port", None)
    faction = port.faction if port else None
    carrying = customs_sim.aboard(game, faction)
    reg = customs_sim.regime(faction)
    if not carrying or not reg:
        return None

    p = Panel("A quiet word on the quay", "warn")
    p.add(label(
        f"Nothing you are carrying under {reg.writ} has a posted price here. "
        "That is exactly why it has a good unposted one.", "", wrap=True))

    mood, tint = customs_sim.standing_note(game, faction)
    p.add(spacer(4), mono_label("How they are looking at you"))
    p.add_row("Their interest in you", mood, tint)
    p.add_row("If you dock here again", pct(customs_sim.chance(game, faction)),
              "warn")

    room = customs_sim.absorbs(game, faction)
    p.add(spacer(4), mono_label("On offer"))
    for cid, tonnes in carrying:
        price = customs_sim.premium(game, faction, cid)
        good = BY_ID.get(cid)
        take = min(tonnes, room)
        p.add(spacer(3))
        p.add(label(good.name if good else cid, "h3", "warn"))
        p.add_row(f"{tonnes:g} t aboard", f"{cr(price)} the tonne")
        p.add_row("They can move", f"{take:g} t this visit",
                  "warn" if take < tonnes else "")
        p.add_row("For that", cr(round(price * take)), "chloro")
        p.add_buttons(
            button(f"Sell {take:g} t quietly",
                   lambda _=False, c=cid: on_sell(c), kind="primary"),
            button("Vent it", lambda _=False, c=cid: on_dump(c), kind="danger"))
    p.add(spacer(4))
    p.add(note("Selling raises their interest in you, which both thins what "
               "they will pay and thickens the search. So does being cleared. "
               "Venting costs you the cargo and nothing else."))
    return p
