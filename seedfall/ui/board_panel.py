"""The contract board, drawn: what is posted, and what it takes to do it.

Lifted out of `ui/port_view.py`, which had grown past five hundred lines. The
rumour board, the commissions and the postings each already had their own
panel or their own block; this is the postings.

The card states the destination and the flight to it because the board used to
name a reward and a deadline and nothing else, while two postings in three
pointed at a system outside the reachable component — see
`tests/test_postings.py`.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..sim import allegiance
from ..sim import contracts as contract_sim
from . import commissions_panel, rumours_panel
from .widgets import Card, Panel, Pill, button, label, note, spacer


def build(view, sysm) -> None:
    """Fill `view.col` with the board as it stands at this port."""
    g = view.game
    # The board belongs to the sim, which turns it over on the harbour's
    # clock — generated here, it could never refresh, and it never did.
    board = contract_sim.board_for(g, sysm)

    rumours = rumours_panel.board(view, g, sysm)
    if rumours is not None:
        view.col.addWidget(rumours)
    office = rumours_panel.surveys(view, g, sysm)
    if office is not None:
        view.col.addWidget(office)

    commissions = commissions_panel.held_panel(view, g)
    if commissions is not None:
        view.col.addWidget(commissions)
    offers = commissions_panel.offers_panel(view, g, sysm)
    if offers is not None:
        view.col.addWidget(offers)

    mine = contract_sim.active(g)
    view.col.addWidget(note(
        f"{len(mine)} of {contract_sim.MAX_ACTIVE} contracts in hand. Nothing "
        "here is required — the endings are open whether you take work or "
        "not — but standing is worth more than the fee."))

    if mine:
        held = Panel("In hand")
        for c in mine:
            d = c.definition
            left = c.days_left(g.day)
            held.add(spacer(3))
            held.add(label(c.title, "h3", d.tint))
            bits = [f"{d.name} · {FACTIONS_BY_ID[c.issuer].short}",
                    f"{cr(c.reward)}", f"{left} day(s) left"]
            if c.amount > 1 and c.kind in ("survey", "bounty"):
                bits.append(f"{int(c.progress)}/{int(c.amount)} done")
            held.add(note(" · ".join(bits)))
            if left < 30:
                held.add(label("Running out of time.", "", "warn"))
            held.add_buttons(button("Abandon it",
                                    lambda _=False, x=c: view._abandon(x),
                                    kind="danger"))
        view.col.addWidget(held)

    if not board:
        view.col.addWidget(Panel("The board is empty").add(
            note("Nothing posted here at the moment. Boards refresh as the "
                 "postings expire.")))
        return

    cards = []
    for c in board:
        d = c.definition
        card = Card(selectable=False)
        card.add(label(c.title, "h3", d.tint))
        card.add(Pill(d.name, d.tint))
        card.add(label(c.posting, "", wrap=True))
        card.add(note(f"{cr(c.reward)} · {c.days_left(g.day)} days · "
                      f"standing +{c.rep}"))
        # What the cargo costs, and what is left. A fee on its own hid a
        # board that was half traps.
        money = contract_sim.quote(g, c)
        if money is not None:
            card.add(label(
                f"Cargo costs about {cr(money['cost'])} here"
                + (f" ({money['held']:g} t already aboard)"
                   if money["held"] else "")
                + f" — clears {cr(money['net'])}",
                "", "chloro" if money["net"] > 0 else "warn", wrap=True))
        # Where the work actually is. The board named a reward and a
        # deadline and never the destination, while two postings in three
        # pointed outside the reachable component altogether.
        leg = contract_sim.trip(g, c)
        if leg is not None:
            if leg["hops"] is None:
                card.add(label(f"{leg['name']} — you cannot get there "
                               "from here at this drive.", "", "warn",
                               wrap=True))
            elif leg["hops"] == 0:
                card.add(label(f"{leg['name']} — you are already here.",
                               "", "chloro", wrap=True))
            else:
                card.add(label(
                    f"{leg['name']} — {leg['hops']} jump(s), about "
                    f"{leg['days']} days each way"
                    + ("" if leg["in_time"] else
                       ", which the deadline will not cover"),
                    "", "chloro" if leg["in_time"] else "warn", wrap=True))
        # Whose enemies mind, before you commit rather than after.
        said, tint = allegiance.note(g, c.issuer, c.rep)
        card.add(label(said, "", tint))
        card.add(button("Take it", lambda _=False, x=c: view._accept(x),
                        kind="primary"))
        cards.append(card)
    view.col.addWidget(label("Posted", "h3"))
    view.grid(cards, cols=2)
