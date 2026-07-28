"""What the battle computer intends at the seats you are not sitting in.

You take one station a turn and the other two run themselves. Before battle
computers they ran themselves badly and silently: the helm repeated its last
order forever and the gunner salvoed every turn whatever the heat and whatever
bore. Now they choose — and a system that acts on your behalf without saying
what it is about to do is the defect this project keeps finding, wearing a
uniform. So it says, before the turn resolves, and it says *why*.

The panel also states the case when there is no computer, because "the helm
will repeat *close* until you come back to it" is exactly the thing a captain
needs to know before walking away from the helm.
"""

from __future__ import annotations

from ..sim import doctrine
from ..sim.stations import ORDERS_BY_ID
from .widgets import Card, Panel, label, note


def intentions(view, b):
    """A card per seat nobody is in, naming the order and the reasoning."""
    side = b.player
    panel = Panel("Battle computer")
    panel.add(note(doctrine.note(side)))

    if not doctrine.fitted(side.st):
        held = ORDERS_BY_ID.get(getattr(side, "helm_order", "") or "")
        if held is not None:
            panel.add(label(
                f"The helm will go on {held.name.lower()} until you take the "
                "seat back.", "", "warn", wrap=True))
        panel.add(label("Gunnery will fire everything it has every turn, "
                        "whatever the heat and whatever bears.", "", "warn",
                        wrap=True))
        return panel

    plan = doctrine.plan(b)
    if not plan:
        panel.add(note("You are holding every seat there is."))
        return panel

    for station, (order_id, why) in sorted(plan.items()):
        order = ORDERS_BY_ID.get(order_id)
        card = Card(selectable=False)
        card.add(label(station.capitalize(), "h3", "dim"))
        card.add(label(order.name if order else order_id, "", "chloro"))
        card.add(label(why, "", "", wrap=True))
        panel.add(card)

    panel.add(note("Take a seat yourself to override it — and to work that "
                   "station at your own rate rather than the machine's."))
    return panel
