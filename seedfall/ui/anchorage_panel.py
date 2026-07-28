"""Where you can put in, and how to get back to it.

A player at the helm: *"the map only shows the sun and planets. What about
stations, the fleet hub and other shipyards? How would I navigate back to a
shipyard if it is not on the map?"* This is the answer to the second half —
`sim/anchorage.py` gives each one a place to be, and this lists them as things
you can actually set a course for.

The panel leads with where the hull is *standing*, because that was the other
half of the complaint: you could not tell you had launched from a shipyard
except by opening the shipyard window.
"""

from __future__ import annotations

from ..sim import anchorage as anchorage_sim
from .widgets import Card, Panel, button, label, note


def where_to_put_in(view, g):
    """Everything in this system you can put in at, nearest first."""
    places = sorted(anchorage_sim.in_system(g),
                    key=lambda a: (not a.here, anchorage_sim.reach_to(g, a)))
    panel = Panel("Where you can put in")
    panel.add(view.hint(anchorage_sim.where_am_i(g)))

    if not places:
        panel.add(note("Nothing in this system but rock. No quay, no holding, "
                       "nowhere to take on stores or lay down a hull."))
        return panel

    for place in places:
        card = Card(selectable=False)
        card.add(label(f"{place.glyph}  {place.name}", "h3",
                       "chloro" if place.here else ""))
        card.add(note(place.what))
        card.add(label(anchorage_sim.note(g, place), "",
                       "chloro" if place.here else "dim", wrap=True))
        if place.here:
            card.add(button("Dock here", lambda: view.win.go("port"),
                            kind="primary")
                     if place.kind in ("quay", "hub")
                     else button("Open holdings",
                                 lambda: view.win.go("empire")))
        else:
            q = anchorage_sim.quote(g, place)
            afford = g.ship.cargo.get("volatiles", 0) >= q["fuel"]
            card.add(button(
                f"Set course — {q['days']} d, {q['fuel']} t",
                lambda i=place.body_index: view.course_to(i),
                kind="primary" if afford else "", enabled=afford,
                tip=f"Fly to {place.name}, in orbit of "
                    f"{g.system.bodies[place.body_index].name}."))
            if not afford:
                card.add(label(
                    f"Not enough reaction mass: {q['fuel']} t needed, "
                    f"{int(g.ship.cargo.get('volatiles', 0))} t aboard.", "",
                    "warn", wrap=True))
        panel.add(card)
    return panel
