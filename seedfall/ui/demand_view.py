"""Somebody has put your holding inside their border and wants an answer."""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..data.territory import ANSWERS, DEMAND, LEVY_SHARE, OUTCOMES
from ..sim import territory as territory_sim
from .widgets import (Panel, View, button, label, mono_label, note, spacer)


class DemandView(View):
    def build(self) -> None:
        demand = self.win.demand
        if demand is None or demand.over:
            self.head("Nothing outstanding", "Nobody is waiting on you.")
            self.buttons(button("Back", lambda: self.win.go("empire")))
            return

        g = self.game
        system = g.galaxy.systems[demand.system_id]
        power = FACTIONS_BY_ID[demand.power]
        self.head(f"{system.name} — a question of register",
                  f"{power.name} · standing {round(g.rep.get(power.id, 0)):+}")
        self.row(self._holding(demand, system, power), self._answers(demand))

    def _holding(self, demand, system, power) -> Panel:
        g = self.game
        p = Panel("What is at stake", "warn")
        p.add(label(DEMAND.format(power=power.name, system=system.name),
                    "", wrap=True))
        p.add(spacer(4), mono_label("The holding"))
        for col in territory_sim.holdings_in(g, system.id):
            p.add_row(col.name, "online" if col.online else "still growing",
                      "chloro" if col.online else "dim")
        p.add_row("Worth a year", cr(round(demand.worth)))
        p.add_row("A levy would cost", cr(round(demand.worth * LEVY_SHARE)) + " a year",
                  "warn")
        p.add(spacer(4))
        p.add(note("Nothing here is reversible. A power that has been refused "
                   "does not ask twice; it files."))
        return p

    def _answers(self, demand) -> Panel:
        p = Panel("What you tell them")
        for ans in ANSWERS:
            p.add(spacer(3))
            p.add(label(ans.name, "h3", "chloro"))
            p.add(note(ans.blurb))
            p.add_buttons(button(ans.name,
                                 lambda _=False, a=ans.id: self._answer(a)))
        return p

    def _answer(self, choice: str) -> None:
        g = self.game
        demand = self.win.demand
        system = g.galaxy.systems[demand.system_id]
        power = FACTIONS_BY_ID[demand.power]
        res = territory_sim.answer(g, system, demand.power, choice)
        if not res.get("ok"):
            self.win.toast(res.get("why", "No."), "warn")
            self.win.go("empire")
            return
        g.add_log(f"{system.name}: you {choice} to {power.short}.",
                  "good" if choice != "defy" else "warn")
        self.win.dialog(
            power.short,
            [label(OUTCOMES[choice].format(system=system.name), "", wrap=True)],
            [("Understood", None)])
        self.win.go("empire")
