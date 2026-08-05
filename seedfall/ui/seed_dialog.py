"""Choosing what to plant on a body, and what it will be worth.

Split out of `ui/system_view.py` when that file went past five hundred lines.
The seam is real: the system screen's job is showing what is in a system, and
this is a self-contained flow — offer the classes that will take root here,
price each one honestly, take a choice, plant it.

Bound as a method on the view (`SystemView._colonise`), the same way
`ui/flight_clock.py` and `ui/window_dialogs.py` are bound on the window, so
the button that calls it is untouched.

**The card states the consequence.** It used to give a price and a gestation
time and nothing else, so a Free Port at 74,000 credits read much like a
RADIX Mine at 12,000 — one makes 260 credits a day and the other 2.6 tonnes
of ore. It now quotes the yield, the effects, the upkeep, the administration
the *whole empire* will pay for one more holding, and a rough payback.
"""

from __future__ import annotations

from ..core.util import cost_line, credits as cr, duration
from ..data.colonies import effect_text
from ..data.factions import FACTIONS_BY_ID
from ..data.territory import TRESPASS_NOTE
from ..sim import colony as colony_sim
from ..sim import territory as territory_sim
from .widgets import Card, label, note


def colonise(self) -> None:
    """The seed dialog for the selected body."""
    g = self.game
    sys = g.system
    body = sys.bodies[self.selected]
    options = colony_sim.colonies_for(body.kind, g.research.unlocked)
    if not options:
        self.win.toast("Nothing you know how to grow will take root there.",
                       "warn")
        return

    chosen = {"id": None}
    cards = []
    widgets = [note("A grown colony gestates for months and costs almost "
                    "nothing in credits. A fabricator yard is the opposite "
                    "bargain.")]
    # Planting on somebody's register is allowed and it is not free. Say so
    # here rather than in the log afterwards.
    claimant = territory_sim.claimant(g, sys)
    if claimant:
        widgets.append(label(
            TRESPASS_NOTE.format(power=FACTIONS_BY_ID[claimant].name,
                                 cost=territory_sim.trespass_cost(g, sys)),
            "", "warn", wrap=True))
    for c in options:
        ok, why = colony_sim.can_found(g, sys, body, c.id)
        card = Card(selectable=ok)
        card.add(label(c.name, "h3"))
        if c.binomial:
            card.add(label(c.binomial, "sub"))
        card.add(label(c.blurb, "", wrap=True))
        card.add(note(cost_line(c.cost) + f" · {duration(c.days)} gestation"))
        plan = colony_sim.forecast(g, sys, body, c.id)
        yields = ", ".join(
            (f"{cr(round(v))}/day" if k == "credits" else f"{v:g} {k}/day")
            for k, v in plan.get("yields", {}).items())
        card.add(label(yields or "Produces nothing directly.", "",
                       "chloro" if yields else "dim", wrap=True))
        if plan.get("effects"):
            # What each grant *does*, not the internal name of it.
            for key in sorted(plan["effects"]):
                card.add(note("· " + effect_text(key)))
        if plan.get("upkeep"):
            card.add(note("Upkeep: " + ", ".join(
                f"{v:g} {k}/day" for k, v in plan["upkeep"].items())))
        if plan.get("admin"):
            # An empire is not free to administer, and the card used to
            # quote every holding as though it were your only one.
            card.add(note(f"Administration: another "
                          f"{cr(round(plan['admin']))}/day across everything "
                          f"you hold."))
        if plan.get("payback"):
            years = plan["payback"] / 365
            card.add(note(f"Pays for itself in about {years:.1f} year(s) "
                          f"once it is up."))
        if not ok:
            card.add(label(why, "", "warn", wrap=True))
        else:
            def pick(cid=c.id, this=card):
                chosen["id"] = cid
                for other in cards:
                    other.set_selected(other is this)
            card.clicked.connect(pick)
        cards.append(card)
        widgets.append(card)

    if self.win.dialog(f"Plant a seed on {body.name}", widgets,
                       [("Plant it", "go"), ("Not yet", None)]) != "go":
        return
    if not chosen["id"]:
        self.win.toast("No class selected.", "warn")
        return
    col, why = colony_sim.found(g, sys, body, chosen["id"])
    if not col:
        self.win.toast(why, "warn")
        return
    g.add_log(f"Seed planted at {body.name}. Gestation {col.need} days.",
              "good")
    self.win.toast("Seed planted.", "chloro")
    self.win.refresh()
