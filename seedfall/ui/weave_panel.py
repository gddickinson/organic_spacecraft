"""The Weave, as the sector chart shows it.

Where a lit ring can take you from where you stand, what the toll is, and —
if you are standing on a dark anchor — what it would take to wake it.

The panel deliberately puts the price of the network next to its use. A gate
is instant, which is unlike everything else in the game, and growth crosses a
lit ring exactly as easily as a hull does, which is also unlike everything
else. Both facts belong on the same card.
"""

from __future__ import annotations

from ..data.gates import BUILD_DAYS, WAKE_DAYS
from .widgets import Panel, button, label, mono_label, note, spacer


def build(view, g) -> Panel:
    """The Weave: where it can take you, and what it would take to grow it."""
    from ..sim import gates as gates_sim
    from ..sim import weave as weave_sim

    state = weave_sim.summary(g)
    p = Panel("The Weave")
    p.add(note(
        f"{state['lit']} anchor(s) burning of {state['gates']}, "
        f"{state['links']} ring(s) live. Transit is instant; the tolls "
        "are not. Growth crosses a lit ring as easily as you do."))

    here = weave_sim.gate_at(g, g.location_id)
    if here is not None:
        p.add(spacer(4))
        p.add(label(f"{here.name} — {gates_sim.kind_name(here)}", "h3",
                    "warn" if here.lit else "dim"))
        p.add(note(gates_sim.kind_blurb(here)))
        if not here.lit and here.kind == "ancient":
            ok, why = gates_sim.can_wake(g)
            p.add(note(why or "Everything needed is aboard."))
            p.add_buttons(button(f"Wake it — {WAKE_DAYS} d",
                                 view._wake, kind="primary" if ok else "",
                                 enabled=ok))
    elif gates_sim.can_build(g)[0] or gates_sim.anchor_options(g):
        ok, why = gates_sim.can_build(g)
        p.add(spacer(4))
        p.add(label("No anchor here", "h3", "dim"))
        p.add(note(why or "There is a lit ring near enough to hang one off."))
        p.add_buttons(button(f"Lay an anchor — {BUILD_DAYS} d",
                             view._build, kind="primary" if ok else "",
                             enabled=ok))

    runs = weave_sim.reachable(g, g.location_id)
    if not runs:
        p.add(spacer(4))
        p.add(note("No lit ring runs from where you are standing."))
        return p
    p.add(spacer(4), mono_label("Through the ring, from here"))
    for dest in runs[:8]:
        said = gates_sim.quote(g, dest)
        target = g.galaxy.systems[dest]
        p.add_row(f"{target.name} · {said['ly_saved']:.0f} ly",
                  f"₡{said['credits']:,.0f} · {len(said['hops'])} ring(s)",
                  "" if said["ok"] else "warn")
        p.add_buttons(button(f"Step to {target.name}",
                             lambda d=dest: view._step(d),
                             kind="primary" if said["ok"] else "",
                             enabled=said["ok"],
                             tip=said["why"] or
                             f"Instant. {said['ly_saved']:.0f} light years."))
    return p
