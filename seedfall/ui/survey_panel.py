"""The four ways of looking at a body, each saying what it cannot see.

Lifted out of `system_view.py` when that file crossed five hundred lines.

There used to be one Survey button: three days, no cost, the same answer for a
comet as for an ocean world. A method that cannot find a buried site has to say
so *before* you spend nine days not finding one, which is the whole reason this
panel exists rather than a single control.
"""

from __future__ import annotations

from ..data.xenotech import CULTURES_BY_ID, XENOTECH_BY_ID
from ..sim import survey as survey_sim
from .widgets import Card, Panel, button, label, note


def how_to_look(view, g, b):
    """The four ways of looking, each saying what it cannot see.

    There used to be one button. A method that cannot find a buried site
    has to say so before you spend nine days not finding one.
    """
    panel = Panel("How to look at it")
    panel.add(view.hint(survey_sim.note(g, b)))
    for method, ok, why in survey_sim.available(g, b):
        forecast = survey_sim.preview(g, b, method.id)
        card = Card(selectable=False)
        card.add(label(method.name, "h3", "chloro" if ok else "dim"))
        card.add(note(method.blurb))
        # `forecast["cost"]`, not `method.cost`: the method's own bill omits
        # the reaction mass for flying there, which is most of it for a
        # close pass.
        bill = ", ".join(f"{v:g} t {k}" for k, v in forecast["cost"].items())
        card.add(label(
            f"{forecast['days']} day{'' if forecast['days'] == 1 else 's'}"
            + (" (including the flight there)" if forecast["flies"] else "")
            + (f" · {bill}" if bill else " · nothing but time"),
            "", "dim"))
        card.add(label("Finds: " + ", ".join(forecast["finds"]), "",
                       "chloro", wrap=True))
        if forecast["blind"]:
            card.add(label("Cannot see: " + ", ".join(forecast["blind"]),
                           "", "warn", wrap=True))
        card.add(button(
            f"{method.name}", lambda m=method.id: view._survey(m),
            kind="primary" if ok else "", enabled=ok, tip=why))
        if not ok:
            card.add(label(why, "", "warn", wrap=True))
        panel.add(card)
    return panel


def report(res) -> list:
    """What a finished survey found, as lines for the dialog.

    Lives here rather than in `system_view` so the screen holds the screen and
    the survey holds the survey — and so `system_view` stays under the line
    limit, which it had just crossed.
    """
    lines = [f"{res['days']} days on station. {len(res['lifeforms'])} "
             f"organism(s) catalogued, {res['research']} points of research "
             "banked."]
    for lf in res["lifeforms"]:
        lines.append(f"{lf.name} — {lf.metabolism_name}; {lf.behaviour}.")
    if res["anomaly"]:
        lines.append(f"{res['anomaly'].name}: {res['anomaly'].text}")
    if res.get("relic"):
        tech = XENOTECH_BY_ID[res["relic"]]
        culture = CULTURES_BY_ID[tech.culture]
        lines.append(f"A {culture.name} site, buried and largely intact. "
                     f"The work appears to be {tech.name}. It can be "
                     "excavated.")
    elif res.get("method") is not None and "relic" not in res["method"].finds:
        # Say why nothing turned up, rather than letting a silent report read
        # as "there is nothing here" when the method simply could not look.
        lines.append(note("Nothing under the surface — though this method was "
                          "never going to see it."))
    if res["data"]:
        lines.append(note(f"{res['data']} data set(s) stowed — the factions "
                          "buy these."))
    return lines
