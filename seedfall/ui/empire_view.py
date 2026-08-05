"""Holdings — colonies, the depot, and how close each ending is."""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.works import WORKS_BY_ID
from ..sim import territory as territory_sim
from ..sim import works as works_sim
from . import works_panel
from ..core.util import duration, num, pct
from ..data.commodities import BY_ID
from ..data.lore import VICTORIES
from ..data.bloom import HEART_HP
from ..sim.threat import victory_progress
from ..sim import bloom as bloom_sim
from ..sim.actions import launch_exodus
from .widgets import Panel, Pill, View, button, label, mono_label, note, spacer


class EmpireView(View):
    focus: int | None = None

    def begin_work(self, col, work_id: str) -> None:
        res = works_sim.begin(self.game, col, work_id)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def abandon_work(self, col) -> None:
        if not self.win.confirm(
                "Abandon the work",
                f"Everything committed to it at {col.name} is spent. "
                "This cannot be undone."):
            return
        works_sim.cancel(self.game, col)
        self.win.refresh()

    def _focus(self, colony_id: int) -> None:
        self.focus = None if self.focus == colony_id else colony_id
        self.refresh()

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

        ark = self._exodus()
        if ark is not None:
            self.col.addWidget(ark)
        self.row(self._colonies(), self._victories())
        focused = next((c for c in g.colonies
                        if c.id == self.focus and c.online), None)
        if focused is not None:
            self.col.addWidget(works_panel.build(self, g, focused))
        self.col.addWidget(self._depot())

    def _wait(self, days: int, ignoring=()) -> None:
        """Sit still, and be told what happened while you did.

        A toast with a credits delta was the whole report on a year of
        the sector's life — and the clock ran through anything short of
        death, so a colony seized, a contract expired or a crew starving
        scrolled past unread. `wait_days` stands down on bad news; this
        says what stopped it and what was said.
        """
        told = self.game.wait_days(days, ignoring)
        if self.win.check_ending():
            return
        gain = told["credits"]
        body = [f"{duration(told['days'])} passed"
                + (f" of {duration(days)} asked — {told['stopped']}."
                   if told["stopped"] else ".")]
        body.append(label(f"Treasury {cr(gain)}.", "",
                          "chloro" if gain >= 0 else "osteo", wrap=True))
        for text in told["bad"][-6:]:
            body.append(label(text, "", "bad", wrap=True))
        for text in told["good"][-4:]:
            body.append(label(text, "", "good", wrap=True))
        if not told["bad"] and not told["good"]:
            body.append(label("Nothing worth reporting.", "note", wrap=True))
        choices = [("Carry on", None)]
        if told["stopped"] and told["days"] < days and not told["stopped"] == \
                "something is waiting on an answer":
            choices.insert(0, (f"Wait the remaining "
                               f"{duration(days - told['days'])}", "more"))
        again = self.win.dialog("While you waited", body, choices)
        self.win.refresh()
        if again == "more":
            # Carrying on means "I have read that": what stopped this spell
            # is handed back, so a warning that recurs every few days — a
            # hold short of biomass — does not stop the next one too.
            self._wait(days - told["days"],
                       tuple(ignoring) + tuple(told.get("told", ())))

    def _exodus(self) -> Panel | None:
        """Offered only once a LEVIATHAN exists — it ends the chronicle."""
        g = self.game
        has_ark = (g.ship.chassis == "leviathan"
                   or any(s.chassis == "leviathan" for s in g.fleet))
        if not has_ark or g.flags.get("exodus_launched"):
            return None
        pop = sum(c.pop for c in g.colonies if c.online)
        p = Panel("The ark is ready", "osteo")
        p.add(label(
            "Twelve drums, ten million berths and a course out. Launching ends "
            "the chronicle here: you concede the Verge and carry the biology "
            "somewhere it can start again with better rules.", "", wrap=True))
        p.add_row("Citizens who would sail", num(round(pop)))
        p.add_buttons(button("Launch the Exodus", self._launch, kind="danger"))
        return p

    def _launch(self) -> None:
        if not self.win.confirm(
                "Launch the Exodus",
                "The trunk meristem stands down and the ark leaves. This ends "
                "the chronicle — there is no coming back to the Verge.",
                "Go", "Stay"):
            return
        res = launch_exodus(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.check_ending()

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
                yields = works_sim.yields_of(c)
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
            # Whose register the ground is on, and what that costs you.
            said, tint = territory_sim.status(g, c)
            p.add_row("Ground", said, tint)
            if c.starving > 0:
                p.add(label("Upkeep unmet — production has stopped.", "", "warn"))
            if c.online:
                done = len(works_sim.done(c))
                job = getattr(c, "job", None)
                if job:
                    p.add_row("Under way",
                              f"{WORKS_BY_ID[job].name} · "
                              f"{pct(works_sim.progress(c))}", "lumen")
                elif done:
                    p.add_row("Works", ", ".join(w.name for w in works_sim.done(c)),
                              "chloro")
                p.add_buttons(button(
                    "Develop" if self.focus != c.id else "Hide works",
                    lambda _=False, cid=c.id: self._focus(cid),
                    kind="primary" if self.focus == c.id else ""))
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
        # Counted, not stated: it said "five" from the day there were five,
        # and there have been ten for some time.
        p.add(note(f"{len(VICTORIES)} of them. You do not have to pick one "
                   "now, and nothing stops you from working two at once."))

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
        st = bloom_sim.summary(g)
        stage = st["stage"]
        p.add(spacer(6))
        p.add(label(f"The Bloom — {stage.name}", "h3", stage.tint))
        p.add(note(stage.blurb))
        p.add(note(f"{len(infested)} systems carrying unlicensed growth, "
                   f"{pct(g.bloom_total / total)} of the sector by mass."))
        p.add_bar(g.bloom_total / total, "warn")
        if st["instars"]:
            p.add_row("Instars under way", num(st["instars"]), "warn")
        worst = bloom_sim.worst_resisted(g)
        if worst:
            family, value = worst
            p.add_row(f"Resistant to {family} weapons", pct(value), "warn")
            p.add(note("Vary what you shoot it with. What you stop using, it "
                       "stops needing to resist."))
        if st["heart_found"]:
            p.add_row("The First Instar",
                      "destroyed" if st["heart_hp"] <= 0
                      else f"{round(st['heart_hp'])} left",
                      "chloro" if st["heart_hp"] <= 0 else "warn")
            p.add_bar(1 - st["heart_hp"] / HEART_HP, "chloro")
        return p
