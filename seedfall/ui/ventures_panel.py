"""What the powers are doing, and whether you mean to help."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import duration, pct
from ..data.factions import FACTIONS_BY_ID
from ..sim import ventures as venture_sim
from .widgets import Panel, Pill, button, label, mono_label, note, spacer


def build(view, game) -> Panel:
    running = venture_sim.live(game)
    p = Panel("What they are doing")
    p.add(note("The powers act on their own account whether or not you are "
               "watching. You can put money and standing behind one, work "
               "against it, or let it happen — which is also a choice."))

    if not running:
        p.add(spacer(3))
        p.add(note("Nothing is moving in the open just now. It rarely lasts."))
        return p

    for venture in running:
        kind = venture.definition
        power = FACTIONS_BY_ID[venture.power]
        p.add(spacer(4))
        p.add(label(f"{kind.name} — {power.short}", "h3", kind.tint))
        p.add(note(venture_sim.describe(game, venture, kind.premise)))

        p.add_row("Resolves in", duration(max(0, venture.until - game.day)))
        chance = venture_sim.odds(game, venture)
        p.add_row("Odds as things stand", pct(chance),
                  "chloro" if chance > 0.65 else ("warn" if chance < 0.4 else ""))
        if venture.other:
            p.add_row("Against", FACTIONS_BY_ID[venture.other].name)
        if venture.place is not None:
            p.add_row("Over", game.galaxy.systems[venture.place].name)

        if venture.stance != "none":
            p.add(Pill("you have backed this" if venture.stance == "backed"
                       else "you are working against this",
                       "chloro" if venture.stance == "backed" else "warn"))
            continue

        can_back, why_back = venture_sim.can_intervene(game, venture, "back")
        p.add_row("Backing it costs", cr(kind.back_cost),
                  "" if can_back else "warn")
        p.add(note(f"Backing buys {kind.back_rep:+.0f} standing with "
                   f"{power.short}"
                   + (f" and costs you with "
                      f"{FACTIONS_BY_ID[venture.other].short}."
                      if venture.other else ".")))
        if not can_back:
            p.add(label(why_back, "", "warn"))
        p.add_buttons(
            button(f"Back it — {cr(kind.back_cost)}",
                   lambda _=False, v=venture: view.take_side(v, "back"),
                   kind="primary", enabled=can_back),
            button("Work against it",
                   lambda _=False, v=venture: view.take_side(v, "oppose")))
    return p
