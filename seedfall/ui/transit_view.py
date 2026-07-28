"""The pilot's seat during a crossing: the watch, and what it wants."""

from __future__ import annotations

from ..core.util import duration, num, pct
from ..data.watches import WATCHES_BY_ID
from ..sim import transit as transit_sim
from ..sim.ship import hull_pct
from .widgets import (Panel, Pill, View, button, label, mono_label, note,
                      spacer)


class TransitView(View):
    def build(self) -> None:
        crossing = self.win.transit
        if crossing is None:
            self.head("Not under way", "Nothing is being flown.")
            self.buttons(button("Helm", lambda: self.win.go("helm")))
            return

        g = self.game
        self.head(f"Under way — {crossing.body_name}",
                  f"watch {min(crossing.stood + 1, crossing.watches)} of "
                  f"{crossing.watches} · {crossing.days_spent} days out")

        self.row(self._board(g, crossing), self._watch(crossing))
        self.col.addWidget(self._log(crossing))

    # ── the boards ─────────────────────────────────────────────────────────

    def _board(self, g, crossing) -> Panel:
        p = Panel("The crossing")
        p.add_bar(crossing.progress, "lumen")
        p.add_row("Watches stood", f"{crossing.stood} of {crossing.watches}")
        p.add_row("Days out", f"{crossing.days_spent}"
                              + (f" of {crossing.days_planned} planned"
                                 if crossing.days_planned else ""),
                  "warn" if crossing.days_spent > crossing.days_planned else "")
        p.add_row("Mass burned", f"{round(crossing.fuel_spent)} t of "
                                 f"{round(crossing.fuel_planned)} planned",
                  "warn" if crossing.fuel_spent > crossing.fuel_planned else "")
        p.add(spacer(3), mono_label("The hull"))
        p.add_row("Integrity", pct(hull_pct(g.ship)),
                  "warn" if hull_pct(g.ship) < 0.5 else "")
        p.add_row("Heat", f"{round(g.ship.heat)} / {round(g.ship_stats.heat_cap)}",
                  "warn" if g.ship.heat > g.ship_stats.heat_cap * 0.8 else "")
        p.add_row("Reaction mass aboard",
                  f"{round(g.ship.cargo.get('volatiles', 0))} t",
                  "warn" if g.ship.cargo.get("volatiles", 0) < 8 else "")
        return p

    def _watch(self, crossing) -> Panel:
        if crossing.over:
            p = Panel("The crossing is finished")
            p.add(note("Nothing further to fly."))
            p.add_buttons(button("Back to the system", self._leave,
                                 kind="primary"))
            return p

        watch = WATCHES_BY_ID.get(crossing.event or "")
        if watch is None:
            p = Panel("The watch")
            p.add(note("Quiet. The drive is doing what it was told and the "
                       "plot is where it should be."))
            p.add_buttons(
                button("Stand the next watch", self._stand, kind="primary"),
                button("Cut the burn and turn back", self._abort, kind="danger"))
            return p

        p = Panel(watch.name, watch.tint)
        p.add(label(watch.text, "", wrap=True))
        p.add(spacer(4), mono_label("The helm is waiting"))
        for option in watch.options:
            p.add(spacer(3))
            p.add(label(option.label, "h3", "chloro"))
            p.add(note(option.blurb))
            cost = []
            if option.days:
                cost.append(f"{option.days} day(s)")
            if option.fuel:
                cost.append(f"{option.fuel:g} t of mass")
            if option.damage:
                cost.append(f"{round(option.damage)} off the hull")
            if option.heat:
                cost.append(f"{round(option.heat)} heat")
            if cost:
                p.add_row("Costs", " · ".join(cost))
            if option.risk:
                p.add_row("Might go wrong", pct(option.risk), "warn")
            if option.salvage or option.research:
                worth = [f"{round(v)} t {k}" for k, v in option.salvage.items()]
                if option.research:
                    worth.append(f"{round(option.research)} research")
                p.add_row("Worth", " · ".join(worth), "chloro")
            p.add_buttons(button(option.label,
                                 lambda _=False, oid=option.id: self._choose(oid)))
        return p

    def _log(self, crossing) -> Panel:
        p = Panel("The watch log")
        for day, text, kind in crossing.log[-10:]:
            p.add_row(f"day {day}", text, kind)
        return p

    # ── the pilot's hands ──────────────────────────────────────────────────

    def _stand(self) -> None:
        g = self.game
        res = transit_sim.stand(g, self.win.transit, g.rng("watch"))
        if self.win.check_ending():
            return
        if res.get("arrived"):
            self._arrive()
            return
        self.refresh()

    def _choose(self, option_id: str) -> None:
        g = self.game
        res = transit_sim.choose(g, self.win.transit, option_id, g.rng("watch"))
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        if res.get("went_wrong"):
            self.win.dialog("That went badly",
                            [note(self.win.transit.log[-1][1])],
                            [("Carry on", None)])
        if res.get("arrived"):
            self._arrive()
            return
        self.refresh()

    def _abort(self) -> None:
        if not self.win.confirm("Cut the burn",
                                "You will be where you started and the mass "
                                "you have burned is gone."):
            return
        transit_sim.abort(self.game, self.win.transit)
        self.refresh()

    def _arrive(self) -> None:
        crossing = self.win.transit
        self.win.dialog(
            f"Alongside {crossing.body_name}",
            [note(f"{crossing.days_spent} days and "
                  f"{round(crossing.fuel_spent)} t of reaction mass.")],
            [("Log it", None)])
        self._leave()

    def _leave(self) -> None:
        self.win.transit = None
        self.win.go("system")
