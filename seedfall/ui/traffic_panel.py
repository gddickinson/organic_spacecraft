"""Who else is out here, and what they are doing.

The helm plotted the star, the planets and the quays, and not one other ship —
because no other ship had anywhere to be. `sim/traffic.py` gives them
positions; this says who they are in words, because a glyph on a chart tells
you something is there and nothing about whether it matters.

The unmarked hulls are called out separately and last, which is where the eye
lands. A hull running dark at the outer bodies is the thing most likely to
turn onto you when you arrive, and now that `roll_encounter` weighs what is
actually in the system, seeing it here is a warning rather than scenery.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..sim import traffic as traffic_sim
from .widgets import Card, Panel, label, note


def who_else(view, g):
    """Every hull working this system, quiet ones first and dark ones last."""
    hulls = sorted(traffic_sim.in_system(g),
                   key=lambda h: (h.hostile, traffic_sim.reach_to(g, h)))
    panel = Panel("Who else is out here")
    panel.add(view.hint(traffic_sim.summary(g)))
    if not hulls:
        return panel

    for hull in hulls:
        card = Card(selectable=False)
        who = FACTIONS_BY_ID.get(hull.faction) if hull.faction else None
        card.add(label(f"{hull.glyph}  {hull.name}", "h3",
                       "warn" if hull.hostile else ""))
        card.add(label(f"{hull.kind_name} · {who.short if who else 'no colours'}",
                       "", "dim"))
        card.add(label(traffic_sim.note(g, hull), "",
                       "warn" if hull.hostile else "dim", wrap=True))
        if hull.hostile:
            card.add(note("Nothing on the transponder. If anything stops you "
                          "in this system, expect it to be this."))
        panel.add(card)
    return panel
