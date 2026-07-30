"""Word going round, and the survey business.

Two halves of the same trade: what people will tell you about where to go, and
what your own charts are worth once you have been. Both are questions about a
*source* — whether theirs is any good (`rumours.provenance`) and whether yours
is one they know (`charts.acquaintance`) — so both are said out loud here rather
than folded silently into a number.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..sim import charts as chart_sim
from ..sim import intel as intel_sim
from ..sim import rumours as rumour_sim
from .widgets import Panel, Pill, button, label, mono_label, note, spacer


def board(view, game, system) -> Panel | None:
    """What is being said at this port. Regenerated, never stored."""
    if not system.port:
        return None
    # Seeded by port and season so the same stories are going round all month.
    rng = game.rng(f"rumour-{system.id}-{game.day // 30}")
    going = [r for r in rumour_sim.circulating(game, system, rng)
             if not rumour_sim.about(game, r.system_id)]

    p = Panel("Word going round")
    p.add(note("Nobody is paying you and nobody is checking. Some of this is "
               "wrong — and how wrong depends on where you are hearing it. "
               "Word travels by ship, so a story about the next star over, "
               "told at a hub a dozen hulls a week call at, is worth more than "
               "one about the far side of the sector told at an outpost. The "
               "price follows the source — within a kind. A salvage lead is "
               "dearer than a nobody-goes-there whatever the source, because "
               "it is worth more if it holds up."))

    holding = rumour_sim.held(game)
    if holding:
        p.add(spacer(3), mono_label("Following up"))
        for rumour in holding:
            kind = rumour.definition
            target = game.galaxy.systems[rumour.system_id]
            p.add_row(f"{kind.name} · {target.name}",
                      "paid for" if rumour.paid else "overheard", kind.tint)

    if not going:
        p.add(spacer(3))
        p.add(note("Nothing new is being said here this month."))
        return p

    p.add(spacer(4), mono_label("On offer"))
    for rumour in going:
        kind = rumour.definition
        target = game.galaxy.systems[rumour.system_id]
        p.add(spacer(3))
        p.add(label(kind.name, "h3", kind.tint))
        p.add(note(kind.claim.format(system=target.name)))
        # The price and the trust are both `rumours.provenance`, which is also
        # what decided whether the story is true. One figure, three readings.
        where = rumour_sim.provenance(game, rumour)
        price = rumour_sim.price_of(game, rumour)
        p.add_row(target.name, f"{where['light_years']:.0f} ly from this quay")
        p.add_row("How good the source is",
                  f"{round(where['trust'] * 100)}% of these turn out true",
                  "chloro" if where["trust"] > 0.7
                  else ("warn" if where["trust"] < 0.5 else ""))
        p.add(note(where["words"] + "."))
        p.add_buttons(
            button(f"Pay for it — {cr(price)}",
                   lambda _=False, r=rumour: view.take_rumour(r, True),
                   kind="primary", enabled=game.credits >= price),
            button("Just listen",
                   lambda _=False, r=rumour: view.take_rumour(r, False)))
    return p


def surveys(view, game, system) -> Panel | None:
    """Charted systems are worth money to whoever holds this port."""
    if not system.port:
        return None
    have = intel_sim.sellable(game)
    known = intel_sim.summary(game)
    p = Panel("Survey office")
    p.add_row("Sector charted",
              f"{known['charted']}/{known['total']} systems",
              "chloro" if known["charted"] else "dim")
    if not have:
        p.add(note("A survey is worth something only when it is complete — "
                   "every body in the system, not the interesting ones. "
                   "Nothing of yours qualifies yet."))
        return p

    here = system.port.faction
    p.add(note(f"Complete surveys, sold once each. This office buys for "
               f"{chart_sim.buyer_name(here)}."))
    p.add(note(chart_sim.buyer_line(here)))
    # A survey is a claim about places they cannot check without flying there.
    # How well they know the surveyor is part of the price.
    face = chart_sim.acquaintance(game, here)
    p.add_row("What you are to this office", face["words"],
              "chloro" if face["trust"] > 0.5 else "dim")
    for target in have[:8]:
        value = intel_sim.survey_value(game, target, here)
        best_f, best_v = chart_sim.best_buyer(game, target)
        fresh = chart_sim.freshness(game, target)
        p.add(spacer(3))
        p.add(label(target.name, "h3", "chloro"))
        p.add(note(chart_sim.note(game, target)))
        p.add_row("They will pay", cr(value))
        if best_v > value * 1.05:
            # A chart is worth different money to different people, and the
            # office you are standing in is not always the right one.
            p.add_row(f"{chart_sim.buyer_name(best_f)} would pay",
                      cr(best_v), "chloro")
        if fresh < 0.95:
            p.add_row("Age of the survey", f"{round(fresh * 100)}% of fresh",
                      "warn" if fresh < 0.7 else "osteo")
        p.add_buttons(button(f"Sell it here — {cr(value)}",
                             lambda _=False, sid=target.id: view.sell_survey(sid),
                             kind="primary"))
    return p
