"""The Services tab of the Port screen: the drydock, the bunker, the office.

Split out of `ui/port_view.py` when that crossed five hundred lines, along
a seam that was already there — the tab is a different set of counters from
the market board beside it, and nothing on it reads anything the market
does. It owns no rules: every figure is a quote from `sim/services.py`,
`sim/trade.py`, `sim/quayside.py` or `sim/customs.py`, and every button is
a call back onto the view that owns the acts.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import pct
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import customs as customs_sim
from ..sim import market as market_sim
from ..sim import quayside as quayside_sim
from ..sim import services as services_sim
from ..sim import trade as trade_sim
from ..sim import xeno as xeno_sim
from ..sim.fieldwork import xeno_notes_price
from ..sim.ship import hull_pct
from .widgets import Panel, button, label, note


def build(view, sys, fac, rep) -> None:
    g = view.game
    st = g.ship_stats
    # The drydock's price, from the drydock — `services.repair_quote`.
    quote = services_sim.repair_quote(g)
    damage, repair_cost = quote["damage"], quote["cost"]

    dock = Panel("Drydock")
    dock.add(label(f"Hull integrity {pct(hull_pct(g.ship))}. " + (
        "A grown hull will close this on its own, given weeks and biomass. "
        "Paying for it is faster." if st.regen > 0 else
        "A fabricated hull will not close this on its own. Somebody has to be "
        "holding the torch."), "", wrap=True))
    dock.add_buttons(
        button("No damage" if damage < 1 else f"Full repair — {cr(repair_cost)}",
               view._repair, kind="primary",
               enabled=damage >= 1 and g.credits >= repair_cost,
               tip="Close every wound in the hull now, at the drydock's price.",
               why=("The hull is whole." if damage < 1 else
                    f"You have {cr(g.credits)} of the {cr(repair_cost)} it "
                    "costs.")),
        button(f"Clear {len(g.ship.disabled)} fault(s)", view._clear_faults,
               tip="Put every disabled system back in service.")
        if g.ship.disabled else None)

    # The counter's own quote — the market grid twenty lines up was
    # switched to `quote_buy` and pinned; this button was missed.
    vp = market_sim.quote_buy(view.game, sys, "volatiles") or 40
    bunker = Panel("Bunkering")
    bunker.add(label("Reaction mass is volatiles. Every jump burns roughly a "
                     "tonne per light-year.", "", wrap=True))
    bunker.add(note(f"Aboard: {round(g.ship.cargo.get('volatiles', 0))} t."))
    # The till's own gate (`trade.can_buy`) — it was lit with an empty
    # purse and answered "not enough credits".
    fuel_ok, fuel_why = trade_sim.can_buy(g, "volatiles")
    bunker.add_buttons(button(f"Take on 40 t — ~{cr(vp * 40)}",
                              lambda: view._buy("volatiles", 40),
                              enabled=fuel_ok, why=fuel_why,
                              tip="Buy forty tonnes of volatiles over the "
                                  "counter, at the market's price."))

    data_held = g.ship.cargo.get("survey", 0)
    office = Panel("Survey Office")
    office.add(label(f"{fac.short if fac else 'The port'} buys charted orbits, ore "
                     "grades and spectra. Selling them here raises your standing "
                     "as well as your balance.", "", wrap=True))
    office.add(note(f"{round(data_held)} data set(s) aboard."))
    # **And somewhere to sell it from** (`sim/quayside`): a counter is a
    # place, and this button was lit in deep space, where pressing it
    # answered "nobody is at the counter — come alongside".
    at_hand, off_why = quayside_sim.at_counter(g, sys)
    # And a world at law 10 licenses charts (`sim/lawlevel.py`), which
    # closes this window as surely as being a light-second out does.
    licensed = customs_sim.seizes(g, "survey", sys)
    office.add_buttons(button("Sell all survey data", view._sell_data,
                              kind="primary",
                              enabled=(data_held >= 1 and at_hand
                                       and not licensed),
                              tip="Every data set aboard, for credits and "
                                  "standing with this port's power.",
                              why=("Charts are licensed here. This "
                                   "office will take them and not pay "
                                   "for them." if licensed else
                                   off_why if not at_hand else
                                   "No survey data aboard. Survey a "
                                   "system first.")))

    rep_panel = Panel("Standing")
    rep_panel.add(label(fac.doctrine if fac else
                        "This port answers to nobody in particular.", "", wrap=True))
    for fid, value in g.rep.items():
        f = FACTIONS_BY_ID.get(fid)
        if not f or f.hidden:
            continue
        band, tint = standing(value)
        rep_panel.add_row(f.short, f"{band} · {round(value)}", tint)

    view.row(dock, bunker)
    view.row(office, rep_panel)

    target = xeno_sim.best_unfinished(g)
    if target is not None and xeno_sim.is_known(g, target.id):
        price = xeno_notes_price(g, target)
        notes = Panel("Xenology Desk")
        notes.add(label(
            f"Somebody has already dug at a {target.culture.replace('_', ' ')} "
            "site and written it up. Field notes are legal, expensive, and "
            "save you a season in a trench.", "", wrap=True))
        notes.add_row("On offer", target.name)
        notes.add_row("Understood so far", pct(xeno_sim.progress(g, target.id)))
        notes.add_buttons(button(f"Buy the notes — {cr(price)}",
                                 lambda t=target.id: view._buy_notes(t),
                                 kind="primary", enabled=g.credits >= price,
                                 why=f"You have {cr(g.credits)} of the "
                                     f"{cr(price)} they want."))
        view.col.addWidget(notes)

    if "research" in sys.port.services:
        lib = Panel("Fleet Library")
        lib.add(label("A hub keeps a copy of the canon. Two weeks reading it is "
                      "worth as much as a month of your own instruments.", "",
                      wrap=True))
        lib.add_buttons(button(f"Study for a fortnight — {cr(4000)}",
                               view._study, enabled=g.credits >= 4000,
                               tip="Two weeks alongside, reading. The "
                                   "calendar moves.",
                               why=f"You have {cr(g.credits)} of the "
                                   f"{cr(4000)} it costs."))
        view.col.addWidget(lib)
