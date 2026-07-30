"""The research tree — ten branches, five tiers, and one project at a time."""

from __future__ import annotations

import math

from ..core.util import duration, num
from ..data.tech import BRANCHES, TECH, TECH_BY_ID
from ..sim import industry as industry_sim
from ..sim import inquiry
from ..sim import research as research_sim
from . import industry_panel
from . import inquiry_panel, programmes_panel
from .widgets import (Card, Panel, Pill, TabBar, View, button, label,
                      mono_label, note)
from .xeno_view import build_xeno


class TechView(View):
    def __init__(self, win):
        super().__init__(win)
        self.branch = "all"

    def build(self) -> None:
        g = self.game
        rate = g.ship_stats.research + 0.25
        known = sum(1 for t in TECH if t.id in g.research.unlocked)
        self.head("Research",
                  f"{known} of {len(TECH)} technologies · {rate:.2f} points a day "
                  f"· {round(g.research.banked)} banked")

        if self.branch != "xeno":
            self.col.addWidget(self._current(rate))
            approaches = inquiry_panel.approaches(self, g)
            self.row(inquiry_panel.lockers(g), approaches) if approaches \
                else self.col.addWidget(inquiry_panel.lockers(g))
            shaky = inquiry_panel.unconfirmed(self, g)
            if shaky is not None:
                self.col.addWidget(shaky)
            # What the bench does once a branch is finished, and what becomes
            # of what it finds. Both are None until a branch is complete, so a
            # captain is not shown a board of things they cannot do yet.
            standing = programmes_panel.running(self, g)
            if standing is not None:
                self.col.addWidget(standing)
            in_hand = programmes_panel.findings(self, g)
            if in_hand is not None:
                self.col.addWidget(in_hand)
            # What the bench has made that somebody else would pay for. None
            # until the captain holds a process, so a new chronicle is not shown
            # a board of things it cannot sell.
            sellable = industry_panel.build(self, g)
            if sellable is not None:
                self.col.addWidget(sellable)

        tabs = TabBar([("all", "All")] + [(k, v[0]) for k, v in BRANCHES.items()]
                      + [("xeno", "Xenotech ✦")], self.branch)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.branch == "xeno":
            build_xeno(self)
            return

        techs = [t for t in TECH if self.branch in ("all", t.branch)]
        techs.sort(key=lambda t: (t.tier, t.name))
        self.grid([self._card(t) for t in techs], cols=3)

    def sell_process(self, process, power: str) -> None:
        res = industry_sim.licence(self.game, process, power)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.game.add_log(res["text"], "good")
        self.win.toast(f"Licensed for {round(res['price']):,}.", "good")
        self.win.refresh()

    def _switch(self, tid: str) -> None:
        self.branch = tid
        self.refresh()

    def _current(self, rate: float) -> Panel:
        res = self.game.research
        if not res.current:
            # Two different situations, and the panel said the same thing about
            # both. With the tree finished there is nothing "below" to pick and
            # the points are not accumulating unassigned — they are going to
            # the standing programmes. A screen that tells a captain to choose
            # from an empty list is worse than one that says nothing.
            if not research_sim.researchable(res.unlocked):
                p = Panel("The tree is finished")
                p.add(note("Every technology in the sector is known. The day's "
                           "points go to whichever standing programme the "
                           "bench is on — and if it is on none, they wait for "
                           "you to put it on one."))
                return p
            p = Panel("No project running")
            p.add(note("Points are accumulating unassigned. Pick something below and "
                       "they will be spent on it the moment you do."))
            return p
        t = TECH_BY_ID[res.current]
        left = research_sim.days_remaining(res, rate)
        p = Panel(f"Under way — {t.name}")
        p.add(label(t.blurb, "", wrap=True))
        p.add_bar(research_sim.progress_pct(res), "lumen")
        p.add_row(f"{round(res.progress)} / {num(t.cost)} points",
                  duration(left) + " remaining" if math.isfinite(left)
                  else "stalled — no research rate")
        p.add_buttons(button("Set aside", self._clear, kind="flat"))
        return p

    def confirm(self, tech_id: str) -> None:
        """Put the bench on checking a result nobody replicated."""
        from ..sim import inquiry as inquiry_sim
        res = self.game.research
        if getattr(res, "confirming", None):
            self.win.toast("Something is already being checked.", "warn")
            return
        res.confirming = tech_id
        res.confirm_days = inquiry_sim.confirm_cost(res, tech_id)
        self.win.save()
        self.refresh()

    def set_approach(self, approach_id: str) -> None:
        inquiry.set_approach(self.game.research, approach_id)
        self.win.refresh()

    def _clear(self) -> None:
        self.game.research.current = None
        self.win.refresh()

    def _card(self, t) -> Card:
        g = self.game
        done = t.id in g.research.unlocked
        open_now = research_sim.can_research(t.id, g.research.unlocked)
        branch_name, branch_tint, _ = BRANCHES[t.branch]

        card = Card(selectable=open_now)
        card.add(label(t.name, "h3", branch_tint if not done else "dim"))
        card.add(label(f"{branch_name} · tier {t.tier} · {num(t.cost)} pts", "label"))
        card.add(label(t.blurb, "", wrap=True))

        if done:
            card.add(Pill("known", "chloro"))
        elif open_now:
            card.add(Pill("available", "lumen"))
            card.clicked.connect(lambda _=False, tid=t.id: self._choose(tid))
        else:
            missing = [TECH_BY_ID[r].name for r in t.reqs
                       if r not in g.research.unlocked]
            card.add(Pill("needs " + ", ".join(missing), "dim"))
        if t.bonus:
            card.add(note(" · ".join(f"{k} +{round(v * 100)}%"
                                     for k, v in t.bonus.items())))
        if done:
            card.setStyleSheet("QFrame[role='card'] { border: 1px solid #25382f;"
                               "background: #0c1714; border-radius: 3px; }")
        return card

    def _choose(self, tech_id: str) -> None:
        if research_sim.set_project(self.game.research, tech_id):
            self.win.toast(f"Project set: {TECH_BY_ID[tech_id].name}.", "chloro")
            self.win.refresh()
