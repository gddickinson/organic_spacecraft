"""The person behind the counter, and what can be asked of them.

A quay was a bag of services. This is the first screen in the game where
somebody is standing there — with a name that does not change, a temperament
that decides what a favour costs them, a memory of what you have done at their
quay, and possibly something you know that they would rather you did not.

Both ways of asking are costed before either is taken, because the whole point
is that they are different transactions and not two buttons for the same
thing. Asking as a friend spends regard you built and needs enough of it.
Leaning spends the lever, works regardless of what they think of you, costs
*more* regard, and lowers the ceiling honest dealing can ever reach again.
"""

from __future__ import annotations

from ..data.officials import FAVOURS
from ..sim import officials as officials_sim
from .widgets import Card, Panel, button, label, note


def whos_here(view, g, system):
    """Who runs this quay, what they think of you, and what they will do."""
    who = officials_sim.describe(g, system)
    panel = Panel("The desk")
    if not who:
        panel.add(note("No quay here, and nobody to deal with."))
        return panel

    panel.add(label(f"{who['title']} {who['name']}", "h3"))
    panel.add(label(f"{who['temper'].name} — {who['temper'].blurb}", "",
                    "dim", wrap=True))
    panel.add(label(f"Regard: {who['regard']:.0f} — {who['band']}", "",
                    who["tint"]))
    if who["dealings"]:
        panel.add(note(f"{who['dealings']} dealings at this quay."))
    if who["capped"]:
        panel.add(note("Trading here has taken you as far with them as "
                       "trading can. The rest is not for sale."))
    if who["leant"]:
        panel.add(label(
            f"You have leant on them {who['leant']} time"
            f"{'' if who['leant'] == 1 else 's'}. They deal with you; they do "
            "not like you.", "", "warn", wrap=True))

    for lever in who["levers"]:
        panel.add(label(f"You know: {lever.name}", "", "chloro", wrap=True))
        panel.add(note(lever.holds.format(who=who["name"])))
    if not who["levers"]:
        ok, why = officials_sim.can_learn(g, system)
        if ok:
            panel.add(button("Ask around about them",
                             lambda: view.learn_about(system)))
        elif why and "nothing to know" not in why:
            panel.add(note(why))

    if who["favours"]:
        panel.add(label("Running:", "", "dim"))
        for favour, days in who["favours"]:
            held = ("good once, next time you deal here" if days == 0
                    else f"{days} days left")
            panel.add(label(f"{favour.name} — {held}", "",
                            "chloro", wrap=True))
    return panel


def what_to_ask(view, g, system):
    """Every favour, costed both ways, before either is taken."""
    panel = Panel("What you can ask for")
    who = officials_sim.describe(g, system)
    if not who:
        return panel
    panel.add(view.hint(
        "Asking as a friend spends what they think of you. Leaning on what "
        "you know works whatever they think — and costs more of it, for good."))

    for favour in FAVOURS:
        running = officials_sim.favour_running(g, system, favour.id)
        held = officials_sim.pending_once(g, system, favour.id)
        card = Card(selectable=False)
        card.add(label(favour.name, "h3",
                       "chloro" if (running or held) else ""))
        card.add(note(favour.blurb))
        if held:
            card.add(label("Already owed — good once, on your next deal "
                           "over this counter.", "", "chloro"))
        elif running:
            card.add(label(f"Already running — {running} days left.", "",
                           "chloro"))
            panel.add(card)
            continue
        # One cost line per route rather than the whole preview twice: the
        # lever's wording already sits in the left panel, and repeating it
        # under all five favours turned the screen into a wall.
        for lean, title in ((False, "Ask"), (True, "Lean on them")):
            plan = officials_sim.preview(g, system, favour.id, lean)
            if not plan:
                continue
            cost = abs(plan["cost"])
            terms = (f"{cost:.0f} of their regard"
                     + (", and the lever" if plan["spends_lever"] else ""))
            card.add(label(f"{title} — {terms}.", "note",
                           "warn" if plan["spends_lever"] else "", wrap=True))
            card.add(button(
                title, lambda f=favour.id, l=lean: view.ask_favour(system, f, l),
                kind="primary" if not lean else "",
                enabled=plan["ok"], tip=plan.get("why", "")))
            if not plan["ok"] and plan.get("why"):
                card.add(label(plan["why"], "", "warn", wrap=True))
        if favour.lasts:
            card.add(note(f"Holds {favour.lasts} days at this quay."))
        panel.add(card)
    return panel
