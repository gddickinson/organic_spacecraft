"""Word going round, and the survey business.

Two halves of the same trade: what people will tell you about where to go, and
what your own charts are worth once you have been.
"""

from __future__ import annotations

from ..core.util import credits as cr
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
               "wrong. What it buys is a reason to go somewhere specific, and "
               "something to look for when you arrive."))

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
        p.add_row(target.name, f"{cr(kind.price)} to be told properly")
        p.add_buttons(
            button(f"Pay for it — {cr(kind.price)}",
                   lambda _=False, r=rumour: view.take_rumour(r, True),
                   kind="primary", enabled=game.credits >= kind.price),
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

    p.add(note("Complete surveys, sold once each."))
    for target in have[:8]:
        value = intel_sim.survey_value(game, target)
        p.add(spacer(3))
        p.add(label(target.name, "h3", "chloro"))
        p.add(note(f"{len(target.bodies)} bodies, all surveyed."))
        p.add_buttons(button(f"Sell the survey — {cr(value)}",
                             lambda _=False, sid=target.id: view.sell_survey(sid),
                             kind="primary"))
    return p
