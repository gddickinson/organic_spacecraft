"""The trench: which stratum you are on, and how you mean to take it."""

from __future__ import annotations

from ..core.util import num, pct
from ..data.strata import METHODS, STRATA
from ..sim import dig as dig_sim
from ..sim import xeno as xeno_sim
from ..sim.ship import hull_pct
from .widgets import (Panel, Pill, View, button, label, mono_label, note,
                      spacer)


class DigView(View):
    def build(self) -> None:
        site = self.win.dig
        if site is None:
            self.head("No trench open", "Nothing is being dug.")
            self.buttons(button("Back to the system", lambda: self.win.go("system")))
            return

        tech = site.definition
        self.head(f"The trench — {site.body_name}",
                  f"stratum {site.depth} · {site.days} days in the ground")
        self.row(self._site(site, tech), self._face(site))
        self.col.addWidget(self._log(site))

    def _site(self, site, tech) -> Panel:
        g = self.game
        p = Panel(tech.name if tech else "An unreadable site", "xeno")
        if tech:
            p.add(label(tech.blurb, "", wrap=True))
            known = xeno_sim.study_of(g, tech.id)
            p.add_row("Understanding", f"{round(known)} / {tech.study}")
            p.add_bar(min(1.0, known / tech.study if tech.study else 0), "xeno")
        p.add(spacer(4), mono_label("The trench"))
        p.add_bar(site.layer / len(STRATA), "osteo")
        p.add_row("Banked from this site", f"{round(site.points)} points")
        p.add_row("Crated", f"{site.relics:.1f} t of xenolith")
        p.add_row("Hull", pct(hull_pct(g.ship)),
                  "warn" if hull_pct(g.ship) < 0.5 else "")
        if site.finds:
            p.add(spacer(3), mono_label("Out of the ground"))
            for name in site.finds:
                p.add_row(name, "crated", "chloro")
        return p

    def _face(self, site) -> Panel:
        if site.over:
            p = Panel("The trench is closed")
            p.add(note("Nothing further to take out of it."))
            p.add_buttons(button("Back to the system", self._leave, kind="primary"))
            return p

        stratum = site.stratum
        p = Panel(stratum.name, stratum.tint)
        p.add(label(stratum.text, "", wrap=True))
        p.add(spacer(4), mono_label("How to take it"))
        for method in METHODS:
            worth = dig_sim.layer_value(self.game, site, method.id)
            p.add(spacer(3))
            p.add(label(method.name, "h3", "chloro"))
            p.add(note(method.blurb))
            p.add_row(f"{method.days} days",
                      f"{round(worth['points'])} points · "
                      f"{worth['relics']:.1f} t xenolith")
            p.add_row("Chance of spoiling it", pct(worth["spoil"]),
                      "warn" if worth["spoil"] > 0.4 else "")
            if worth["collapse"]:
                p.add_row("Chance the face comes in", pct(worth["collapse"]),
                          "warn")
            p.add_buttons(button(method.name,
                                 lambda _=False, mid=method.id: self._work(mid)))
        p.add(spacer(4))
        p.add(note("What comes out of a layer is banked when the layer is "
                   "finished. Backfilling now keeps everything you have."))
        p.add_buttons(button("Backfill and leave", self._stop, kind="danger"))
        return p

    def _log(self, site) -> Panel:
        p = Panel("The trench log")
        for day, text, kind in site.log[-10:]:
            p.add_row(f"day {day}", text, kind)
        return p

    # ── the spade ──────────────────────────────────────────────────────────

    def _work(self, method_id: str) -> None:
        g = self.game
        res = dig_sim.work(g, self.win.dig, method_id, g.rng("trench"))
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        lines = []
        if res.get("collapsed"):
            lines.append(label("The face came in", "h3", "bad"))
        if res.get("spoiled"):
            lines.append(label(res["spoil_name"], "h3", "warn"))
            lines.append(note(res["spoil_text"]))
        elif res.get("find"):
            lines.append(label(res["find"][0], "h3", "chloro"))
            lines.append(note(res["find"][1]))
        lines.append(note(f"{round(res['points'])} points banked."))
        if res.get("bottomed"):
            lines.append(note("The trench is at the bottom."))
        self.win.dialog(res["stratum"].name, lines, [("Carry on", None)])
        self.refresh()

    def _stop(self) -> None:
        if not self.win.confirm("Backfill the trench",
                                "What is banked is yours. The rest of it stays "
                                "in the ground."):
            return
        dig_sim.stop(self.game, self.win.dig)
        self.refresh()

    def _leave(self) -> None:
        self.win.dig = None
        self.win.go("system")
