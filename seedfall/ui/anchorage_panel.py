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


def _gate_lines(g, place) -> list[str]:
    """What this anchor is, and what it would take to ride it. In order.

    Written here rather than left to the sector chart because the chart is
    not where the captain is standing: they flew to the thing itself, and
    the thing itself said only that it was dark.
    """
    from ..sim import gates as gates_sim
    from ..sim import weave as weave_sim

    gate = weave_sim.gate_at(g, g.location_id)
    out = ["A Weave anchor. Transit through a lit ring is instant and costs "
           "a toll rather than days — the one thing in the Verge that does "
           "not take time."]
    if gate is None:
        return out
    if not gate.lit:
        ok, why = gates_sim.can_wake(g)
        out.append("This one is dark, so nothing runs from it yet.")
        out.append(why or "Everything needed to wake it is aboard — the "
                          "order is on the sector chart.")
        return out
    runs = weave_sim.reachable(g, g.location_id)
    if runs:
        names = ", ".join(g.galaxy.systems[d].name for d in runs[:4])
        out.append(f"Lit, and joined to {names}. Ride it from the Weave "
                   "panel on the sector chart.")
    else:
        out.append("Lit, but nothing it is joined to is burning — a ring "
                   "needs an anchor alight at both ends.")
    return out


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
        if place.here and place.kind == "gate":
            # **A player flew to one of these and could not work out what to
            # do with it.** They were right: an anchor is a place in the
            # system with no services, and the panel that operates it is on
            # another screen entirely — so standing at one offered "Open
            # holdings", which is the fall-through for anything that is not
            # a quay. What the anchor is for, and where the controls are,
            # said at the place the captain actually flew to.
            for line in _gate_lines(g, place):
                card.add(label(line, "", "dim", wrap=True))
            card.add(button("Open the Weave on the sector chart",
                            lambda: view.win.go("map"), kind="primary",
                            tip="A ring is ridden from the chart: the Weave "
                                "panel lists where this anchor can take you, "
                                "and what the toll is."))
        elif place.here:
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
                lambda pl=place: view.fly_to_place(pl),
                kind="primary" if afford else "", enabled=afford,
                tip=f"Fly to {place.name}, in orbit of "
                    f"{g.system.bodies[place.body_index].name}."))
            if not afford:
                card.add(label(
                    f"Not enough reaction mass: {q['fuel']} t needed, "
                    f"{int(g.ship.cargo.get('volatiles', 0))} t aboard.", "",
                    "warn", wrap=True))
        # The channel opens on anything, and lists what can be done with it
        # — see `ui/comms_window.py`. Offered on every place, including the
        # ones whose controls live on another screen.
        contact = _contact_for(g, place)
        if contact is not None:
            card.add(button(f"Open a channel to {place.name}",
                            lambda c=contact: _hail(view, c), kind="flat",
                            tip="Who they are, what they say, and everything "
                                "you can do about them."))
        panel.add(card)
    return panel


def _contact_for(g, place):
    from ..sim import track as track_sim
    return next((c for c in track_sim.contacts(g)
                 if c.kind == "anchorage" and c.name == place.name), None)


def _hail(view, contact) -> None:
    from .comms_window import open_comms
    open_comms(view.win, contact)
