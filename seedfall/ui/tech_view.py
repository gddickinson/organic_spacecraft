"""The research tree — ten branches, five tiers, and one project at a time."""

from __future__ import annotations

import math

from ..core.util import duration, num
from ..data.tech import BRANCHES, TECH, TECH_BY_ID
from ..sim import research as research_sim
from .widgets import (Card, Panel, Pill, TabBar, View, button, label,
                      mono_label, note)
from .xeno_view import build_xeno


class TechView(View):
    def __init__(self, win):
        super().__init__(win)
        self.branch = "all"

    def build(self) -> None:
        g = self.game
        rate = g.ship_stats.research + 0.25 + g.colony_fx.get("research", 0)
        known = sum(1 for t in TECH if t.id in g.research.unlocked)
        self.head("Research",
                  f"{known} of {len(TECH)} technologies · {rate:.2f} points a day "
                  f"· {round(g.research.banked)} banked")

        if self.branch != "xeno":
            self.col.addWidget(self._current(rate))

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

    def _switch(self, tid: str) -> None:
        self.branch = tid
        self.refresh()

    def _current(self, rate: float) -> Panel:
        res = self.game.research
        if not res.current:
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
