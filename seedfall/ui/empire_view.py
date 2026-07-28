"""Holdings — colonies, the depot, and how close each of the five endings is."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import duration, num, pct
from ..data.commodities import BY_ID
from ..data.lore import VICTORIES
from ..sim.threat import victory_progress
from .widgets import Panel, Pill, View, button, label, mono_label, note, spacer


class EmpireView(View):
    def build(self) -> None:
        g = self.game
        online = [c for c in g.colonies if c.online]
        pop = sum(c.pop for c in online)

        self.head("Holdings",
                  f"{len(online)} colonies online · {len(g.colonies) - len(online)} "
                  f"gestating · {num(pop)} citizens")

        self.buttons(
            button("Wait 30 days", lambda: self._wait(30)),
            button("Wait 90 days", lambda: self._wait(90)),
            button("Wait a year", lambda: self._wait(365)),
            label("Colonies yield while you wait. So does the Bloom.", "note"))

        self.row(self._colonies(), self._victories())
        self.col.addWidget(self._depot())

    def _wait(self, days: int) -> None:
        before = self.game.credits
        self.game.advance_days(days)
        if self.win.check_ending():
            return
        gain = round(self.game.credits - before)
        self.win.toast(f"{duration(days)} passed. Treasury {cr(gain)}.",
                       "chloro" if gain >= 0 else "osteo")
        self.win.refresh()

    def _colonies(self) -> Panel:
        g = self.game
        p = Panel("Colonies")
        if not g.colonies:
            p.add(note("Nothing planted yet. Fit a seed bay, find a body worth "
                       "having, and leave something growing on it."))
            p.add_buttons(button("Find a site", lambda: self.win.go("system")))
            return p

        for c in g.colonies:
            definition = c.definition
            sys = g.galaxy.systems[c.system_id]
            p.add_row(f"{definition.name} · {sys.name}",
                      "online" if c.online
                      else f"{max(0, c.need - round(c.days))} d",
                      "chloro" if c.online else "osteo")
            if c.online:
                yields = definition.yields
                if yields:
                    line = " · ".join(f"{cr(v)}/day" if k == "credits"
                                      else f"{v:g} {k}/day" for k, v in yields.items())
                else:
                    line = "Infrastructure — no direct yield."
                if c.pop:
                    line += f" · {num(round(c.pop))} people"
                p.add(note(line))
            else:
                p.add_bar(c.days / c.need if c.need else 0, "osteo")
            if c.starving > 0:
                p.add(label("Upkeep unmet — production has stopped.", "", "warn"))
            p.add(spacer(3))

        if g.building:
            p.add(spacer(4), mono_label("On the slips"))
            for job in g.building:
                p.add_row(f"{job.name} · {job.system_name}",
                          f"{max(0, job.need - round(job.days))} d", "lumen")
        return p

    def _depot(self) -> Panel:
        p = Panel("Empire depot")
        p.add(note("Colony output accumulates here. Draw on it from the ship's hold "
                   "panel, or spend it directly on hulls and seeds."))
        items = [(k, v) for k, v in self.game.stores.items() if v > 0.01]
        if not items:
            p.add(note("Empty."))
        for cid, n in items:
            p.add_row(BY_ID[cid].name if cid in BY_ID else cid, f"{round(n)} t")
        return p

    def _victories(self) -> Panel:
        g = self.game
        progress = victory_progress(g)
        p = Panel("Ways this ends")
        p.add(note("Five of them. You do not have to pick one now, and nothing stops "
                   "you from working two at once."))

        for vid, name, tint, goal, blurb in VICTORIES:
            have, need, done = progress[vid]
            p.add(spacer(5))
            row_label = label(name, "h3", tint)
            p.add(row_label)
            if done:
                p.add(Pill("achieved", "chloro"))
            p.add(note(goal))
            p.add_bar(have / need if need else 0, tint)
            p.add_row(blurb[:70] + "…", f"{num(have)}/{num(need)}")

        infested = [s for s in g.galaxy.systems if s.bloom > 0.02]
        total = max(1, len(g.galaxy.systems))
        p.add(spacer(6))
        p.add(label("Bloom burden", "h3", "warn"))
        p.add(note(f"{len(infested)} systems carrying unlicensed growth, "
                   f"{pct(g.bloom_total / total)} of the sector by mass."))
        p.add_bar(g.bloom_total / total, "warn")
        return p
