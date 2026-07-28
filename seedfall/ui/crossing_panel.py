"""Choosing how hard to fly a crossing, and what each way costs on both clocks.

A jump was a distance and a button. Time is not uniform: the hull's clock and
the Verge's clock only agree if you let them, and `data/crossings.py` is where
the trade lives. This is where a captain sees it.

Each card states four things, because leaving any of them out makes the choice
a guess: sector days, days actually lived aboard, reaction mass, and what the
crew will eat and age in the time they live through. The last one is the whole
argument for burning hard, and it is the one a bare day count never told you.
"""

from __future__ import annotations

from ..data.crossings import CROSSINGS
from ..sim import lifespan, upkeep
from ..sim.actions import jump_quote
from .widgets import Card, Panel, button, label, note


def how_to_fly(view, g, target):
    """The four ways to fly there, each stating what it costs whom."""
    panel = Panel("How to fly it")
    panel.add(view.hint(
        "The Verge keeps its own clock. Fly hard and your crew lives through "
        "less of the crossing — they age less and eat less — but so does the "
        "bench, the workshop and the smelter."))

    chosen = getattr(view, "crossing", None)
    for how in CROSSINGS:
        q = jump_quote(g, target, how.id)
        fuel_ok = g.ship.cargo.get("volatiles", 0) >= q["fuel"]
        ok = q["in_range"] and fuel_ok

        card = Card(selectable=False)
        card.add(label(how.name, "h3", "chloro" if ok else "dim"))
        card.add(note(how.blurb))

        aboard = q["ship_days"]
        line = f"{q['days']} days out here"
        if aboard != q["days"]:
            line += f" · {aboard} lived aboard"
        line += f" · {q['fuel']} t of volatiles"
        card.add(label(line, "", "dim"))

        # What the people pay, on their own clock rather than the sector's.
        eats = upkeep.forecast(g, aboard)
        if eats["need"]:
            bill = ", ".join(f"{v:.1f} t {k}"
                             for k, v in sorted(eats["need"].items()))
            card.add(label(f"The crew will get through {bill}.", "",
                           "" if eats["ok"] else "warn", wrap=True))
        ages = lifespan.crossing_note(g, aboard)
        if ages:
            card.add(label(ages, "", "warn", wrap=True))

        card.add(button(f"Fly {how.name.lower()}",
                        lambda h=how.id: view._jump(h),
                        kind="primary" if ok and how.id == (chosen or "steady")
                        else "", enabled=ok,
                        tip=f"{how.gives} {how.costs}"))
        if not q["in_range"]:
            card.add(label(f"Out of reach — {q['ly']:.1f} ly against a "
                           f"{g.ship_stats.jump:.1f} ly range.", "", "warn",
                           wrap=True))
        elif not fuel_ok:
            card.add(label(
                f"Not enough reaction mass: {q['fuel']} t needed, "
                f"{int(g.ship.cargo.get('volatiles', 0))} t aboard.", "",
                "warn", wrap=True))
        panel.add(card)
    return panel
