"""Standing orders: what the ship could usefully be doing next.

Deliberately compact and placed above the chart. Put below the fold it solves
nothing — a first-time captain never scrolls to find the thing that was meant
to tell them what to do.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data.orders import SHOWN
from ..sim import orders as orders_sim
from .widgets import Panel, button, label, note, spacer


def build(view, game) -> Panel:
    live = orders_sim.standing(game, SHOWN)
    p = Panel("Standing orders")
    if not live:
        p.add(note("Nothing pressing aboard. The Verge is not going to improve "
                   "on its own, but nothing needs you this minute."))
        return p

    p.add(note("What the ship could usefully be doing. None of it is required "
               "— there is no track here, only things worth doing."))
    for order in live:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(8)
        h.addWidget(label(order.title, "", order.tint or "chloro"))
        h.addStretch(1)
        h.addWidget(button("Go there",
                           lambda _=False, dest=order.goes_to: view.win.go(dest)))
        p.add(row)
        p.add(note(order.text))
    return p
