"""Inside a system: the bodies, what a survey found on them, and the four things
you can do about it — look, dig, dive, or plant a seed."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..core.util import cost_line, credits as cr, duration, num, pct
from ..data.factions import FACTIONS_BY_ID
from ..data.territory import TRESPASS_NOTE
from ..sim import colony as colony_sim
from ..sim import territory as territory_sim
from ..sim import dig as dig_sim
from ..sim import mining
from ..sim import responses as response_sim
from ..sim.actions import burn_bloom, dive, extract, strike_heart, survey
from . import mining_panel
from ..sim import bloom as bloom_sim
from ..sim.fieldwork import excavate, launch_expedition
from ..sim import xeno as xeno_sim
from ..data.xenotech import CULTURES_BY_ID, XENOTECH_BY_ID
from ..world.planets import BODY_KINDS
from ..data.lifeforms import biome_name
from .widgets import (Bar, Card, Panel, Pill, View, button, label, mono_label,
                      note, spacer)


class SystemView(View):
    def __init__(self, win):
        super().__init__(win)
        self.selected = 0

    def build(self) -> None:
        g = self.game
        sys = g.system
        if self.selected >= len(sys.bodies):
            self.selected = 0
        fac = FACTIONS_BY_ID.get(sys.faction) if sys.faction else None

        self.head(sys.name,
                  f"{sys.star_name} · {len(sys.bodies)} bodies · "
                  f"{fac.name if fac else 'unclaimed'}")

        if sys.bloom > 0.02:
            p = Panel("Unlicensed growth in this system", "warn")
            p.add(label(f"Roughly {round(sys.bloom * 100)}% of the accessible mass "
                        "here has been converted. It is not attacking anything. It "
                        "is eating, and there is more of it than there was last "
                        "month.", "", wrap=True))
            # The choice the setting has always described: the mass worth
            # understanding is the mass worth destroying, and not both.
            can_study, why = response_sim.can_study(self.game, sys)
            if can_study:
                worth = response_sim.study_value(self.game, sys)
                p.add(spacer(3))
                p.add_row("Nine days alongside would yield",
                          f"{round(worth['xenolith'])} t xenolith · "
                          f"{round(worth['readings'])} readings", "xeno")
                p.add(note("It grows while you watch. Burning it afterwards "
                           "costs you nothing you have already taken."))
            p.add_buttons(
                button("Burn it back", self._cleanse, kind="danger"),
                button("Study the mass", self._study_bloom,
                       enabled=can_study, tip=why or None))

            reaction = response_sim.summary(self.game)
            if reaction["fired"]:
                p.add(spacer(3), mono_label("It has been paying attention"))
                p.add_row("Growing", f"×{reaction['growth']:.2f} faster", "warn")
                if reaction["hunting"]:
                    p.add(label("It is sending masses after your hull "
                                "specifically.", "", "bad", wrap=True))
            self.col.addWidget(p)

        roaming = bloom_sim.instar_at(self.game, sys.id)
        if roaming is not None:
            p = Panel("There is a mass in this system", "bad")
            p.add(label("A detached instar is here — the same thing that eats "
                        "colonies, moving under its own decision. It will move "
                        "on when it is finished.", "", wrap=True))
            p.add_row("Mass", f"{roaming.mass:.1f}", "warn")
            p.add(note("Nothing aboard it will answer a hail."))
            p.add_buttons(button("Intercept it", self._intercept, kind="danger"))
            self.col.addWidget(p)

        heart = bloom_sim.heart_system(self.game)
        if heart is not None and heart.id == sys.id:
            st = bloom_sim.summary(self.game)
            hp = Panel("Kessel's Reach — the origin", "warn")
            if not st["heart_found"]:
                hp.add(label("Something is under the overgrowth here. Survey the "
                             "bodies and find out what.", "", wrap=True))
            elif st["heart_hp"] > 0:
                from ..data.bloom import HEART_BLURB, HEART_NAME
                hp.add(label(HEART_NAME, "h3", "warn"))
                hp.add(label(HEART_BLURB, "", wrap=True))
                hp.add_bar(1 - st["heart_hp"] / 2600, "chloro")
                hp.add_row("Mass remaining", f"{round(st['heart_hp'])}")
                hp.add_buttons(button("Burn into the heart", self._heart,
                                      kind="danger"))
            else:
                hp.add(label("The husk is ash. Whatever is still growing out "
                             "here is growing on its own now.", "", wrap=True))
            self.col.addWidget(hp)

        self.row(self._body_list(), self._detail(), spacing=14)

        body = (sys.bodies[self.selected]
                if self.selected is not None and self.selected < len(sys.bodies)
                else None)
        if body is not None and (g.ship_stats.mine > 0 or g.ship_stats.drink > 0):
            self.col.addWidget(mining_panel.build(
                self, g, body,
                getattr(self, "mining_method", mining.DEFAULT_METHOD)))

        if sys.port:
            self.buttons(
                button(f"Fly the approach to {sys.port.name}", self._dock,
                       kind="primary",
                       tip="Line the hull up yourself. A clean approach earns "
                           "standing; a botched one costs a tug fee."),
                button("Let the harbourmaster bring you in",
                       lambda: self.win.go("port"),
                       tip="Skip the approach and dock directly."),
                button("Helm", lambda: self.win.go("helm")))

    # ── the list ───────────────────────────────────────────────────────────

    def _body_list(self) -> Panel:
        g = self.game
        panel = Panel("Bodies")
        for i, b in enumerate(g.system.bodies):
            kind_name, kind_tint, _ = BODY_KINDS[b.kind]
            card = Card()
            head = QWidget()
            hv = QVBoxLayout(head)
            hv.setContentsMargins(0, 0, 0, 0)
            hv.setSpacing(2)
            hv.addWidget(label(b.name, "h3"))
            hv.addWidget(Pill(kind_name, kind_tint))
            card.add(head)
            if b.surveyed:
                res = b.best_resource()
                card.add(note(f"{biome_name(b.biome)} · {b.temp_k} K"
                              + (f" · {res}-bearing" if res else "")))
            else:
                card.add(note("Unsurveyed."))
            if b.colony is not None:
                col = next((c for c in g.colonies if c.id == b.colony), None)
                if col:
                    card.add(label(col.name if col.online
                                   else f"{col.name} — gestating", "", "chloro"))
            card.set_selected(i == self.selected)
            card.clicked.connect(lambda _=False, idx=i: self._select(idx))
            panel.add(card)
        return panel

    def _select(self, idx: int) -> None:
        self.selected = idx
        self.refresh()

    # ── the detail ─────────────────────────────────────────────────────────

    def _detail(self) -> Panel:
        g = self.game
        sys = g.system
        if not sys.bodies:
            return Panel("Nothing here")
        b = sys.bodies[self.selected]
        st = g.ship_stats

        panel = Panel(b.name)
        panel.add(note(b.summary))
        panel.add_row("Radius", f"{num(b.radius_km)} km")
        panel.add_row("Gravity", f"{b.gravity:.2f} g")
        panel.add_row("Temperature", f"{b.temp_k} K")
        panel.add_row("Biome", biome_name(b.biome))

        if b.surveyed:
            panel.add_row("Depletion", pct(b.depleted))
            panel.add(spacer(4), mono_label("Resource grades"))
            for key, v in b.resources.items():
                if v <= 0.02:
                    continue
                panel.add(mono_label(f"{key}  {pct(v)}"))
                panel.add(Bar(v, "chloro" if v > 0.6 else "osteo"))

            seen = [l for l in b.lifeforms if l.catalogued]
            panel.add(spacer(4))
            if b.lifeforms:
                panel.add(mono_label(
                    f"Biota — {len(seen)}/{len(b.lifeforms)} catalogued"))
                for lf in seen:
                    traits = ("; " + ", ".join(t[1] for t in lf.traits)
                              if lf.traits else "")
                    panel.add(label(f"{lf.name}, {lf.metabolism_name} — "
                                    f"{lf.metabolism_note}{traits}. {lf.behaviour}.",
                                    "", wrap=True))
                if len(seen) < len(b.lifeforms):
                    panel.add(note(f"{len(b.lifeforms) - len(seen)} organism(s) noted "
                                   "but not catalogued."))
            else:
                panel.add(note("No biology detected."))

            if b.anomaly and b.anomaly.found:
                panel.add(spacer(4))
                panel.add(label(b.anomaly.name, "h3", b.anomaly.tint))
                panel.add(label(b.anomaly.text, "", wrap=True))

            if b.relic and b.relic_found:
                tech = XENOTECH_BY_ID[b.relic]
                culture = CULTURES_BY_ID[tech.culture]
                panel.add(spacer(4))
                panel.add(label(f"{culture.name} site", "h3", culture.tint))
                panel.add(label(tech.blurb, "", wrap=True))
                pr = xeno_sim.progress(g, tech.id)
                if xeno_sim.is_incorporated(g, tech.id):
                    panel.add(Pill("incorporated", "chloro"))
                else:
                    panel.add(note(f"{tech.name} — {pct(pr)} understood"))
                    panel.add_bar(pr, culture.tint)
                if b.digs:
                    panel.add(note(f"Worked {b.digs} time(s); the easy material "
                                   "is gone."))
        else:
            panel.add(note("Nothing is known about this body beyond its orbit and "
                           "mass. A survey would take a few days."))

        panel.add_buttons(
            button("Re-survey" if b.surveyed else "Survey", self._survey,
                   kind="primary"),
            button("Dive the ocean", self._dive)
            if (b.biome == "subsurface" and st.can_dive) else None,
            button("Excavate the site", self._excavate)
            if (b.relic and b.relic_found
                and not xeno_sim.is_incorporated(g, b.relic)) else None,
            button("Plant a seed", self._colonise),
            button("Land a party", self._land)
            if (b.surveyed and BODY_KINDS[b.kind][2]) else None,
        )
        return panel

    # ── actions ────────────────────────────────────────────────────────────

    def _survey(self) -> None:
        res = survey(self.game, self.selected)
        if self.win.check_ending():
            return
        lines = [f"{res['days']} days on station. {len(res['lifeforms'])} organism(s) "
                 f"catalogued, {res['research']} points of research banked."]
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
        if res["data"]:
            lines.append(note(f"{res['data']} data set(s) stowed — the factions buy "
                              "these."))
        self.win.dialog("Survey complete", lines, [("Log it", None)])
        self.win.refresh()

    def set_mining_method(self, method_id: str) -> None:
        self.mining_method = method_id
        self.refresh()

    def run_extract(self, days: int) -> None:
        res = extract(self.game, self.selected, days,
                      getattr(self, "mining_method", mining.DEFAULT_METHOD))
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        got = res["got"]
        lines = [note("Aboard: " + ", ".join(f"{round(v)} t {k}"
                                             for k, v in got.items())
                      if got else "The grade was too poor, or the hold too "
                                  "full. Nothing to show for it.")]
        event = res.get("event")
        if event and event["kind"] == "mishap":
            lines.append(label(event["mishap"].name, "h3", "warn"))
            lines.append(note(event["mishap"].text))
        elif event and event["kind"] == "strike":
            lines.append(label("A rich strike", "h3", "chloro"))
            lines.append(note("The face opened onto something markedly better "
                              "than the survey promised."))
        if res.get("wear", 0) > 0:
            lines.append(note(f"The rig cost the hull {round(res['wear'])} "
                              "points of its outer layer."))
        self.win.dialog(f"{days} days — {res['method'].name.lower()}", lines,
                        [("Understood", None)])
        self.win.refresh()

    def _dive(self) -> None:
        res = dive(self.game, self.selected)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        if res["contact"]:
            text = ("Twenty kilometres down, in water at a hundred and fifty "
                    "megapascals and four degrees above freezing, the hull's "
                    "mechanoreceptors picked up a pressure pattern that repeated, "
                    "varied, and repeated again — and changed when you answered it.")
        else:
            text = ("Black water, vent fields, and things crowded around them that "
                    "never needed light. Nothing answered the pressure signal. "
                    "This time.")
        self.win.dialog("Contact" if res["contact"] else "The ocean",
                        [text, note(f"{len(res['found']['lifeforms'])} organism(s) "
                                    "catalogued.")], [("Surface", None)])
        self.win.refresh()

    def _dock(self) -> None:
        sysm = self.game.system
        self.win.views["docking"].begin(sysm.port.name)
        self.win.go("docking")

    def _land(self) -> None:
        from ..data.expedition import SUPPLY_LOADS
        g = self.game
        if not g.officers:
            self.win.toast("Nobody aboard to send down.", "warn")
            return
        body = g.system.bodies[self.selected]
        held = int(g.ship.cargo.get("biomass", 0))
        choices = []
        for i, (label, tonnes, days) in enumerate(SUPPLY_LOADS):
            mark = "" if held >= tonnes else "  — not enough biomass"
            choices.append((f"{label}: {tonnes} t → {days} days{mark}", i))
        choices.append(("Stay in orbit", None))
        load = self.win.dialog(
            f"Land on {body.name}",
            ["Biomass goes down as supplies. The party is on its own until it "
             "walks back to the lander, and nothing is banked until it does.",
             note(f"{held} t of biomass in the hold. Three days to descend.")],
            choices)
        if load is None:
            return
        res = launch_expedition(g, self.selected, [o.id for o in g.officers], load)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.go("ground")

    def _excavate(self) -> None:
        res = dig_sim.begin(self.game, self.selected)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.dig = res["dig"]
        self.win.go("dig")

    def _heart(self) -> None:
        if not self.win.confirm(
                "Burn into the heart",
                "You will hold station inside the origin mass and burn until "
                "something gives. It burns back."):
            return
        res = strike_heart(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        lines = [f"{round(res['cut'])} burned out of it; it took "
                 f"{round(res['backlash'])} off your hull in return."]
        if res["destroyed"]:
            lines.append("The First Instar is dead.")
        else:
            lines.append(note(f"Roughly {round(res['left'])} of it left."))
        self.win.dialog("The heart", lines, [("Log it", None)])
        self.win.refresh()

    def _intercept(self) -> None:
        g = self.game
        roaming = bloom_sim.instar_at(g, g.system.id)
        if roaming is None:
            self.win.toast("It has already moved on.", "warn")
            return
        self.win.views["battle"].begin(bloom_sim.engage_instar(g, roaming))
        self.win.go("battle")

    def _study_bloom(self) -> None:
        g = self.game
        res = response_sim.study(g, g.system)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        if not res.get("dead"):
            self.win.dialog(
                "Nine days alongside",
                [note(f"{round(res['xenolith'])} t of xenolith aboard and "
                      f"{round(res['readings'])} of readings on the bench."),
                 note("The mass is larger than it was. Everything you learned "
                      "came from letting it be.")],
                [("Understood", None)])
        self.win.refresh()

    def _cleanse(self) -> None:
        if not self.win.confirm(
                "Burn back the growth",
                "You will close to contact range with a mass that does not "
                "negotiate, spend six days burning it out, and take real damage "
                "doing it. The Charter will approve."):
            return
        res = burn_bloom(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.toast("System clear." if res["cleared"]
                       else f"Bloom mass reduced by {round(res['cut'] * 100)}%.",
                       "chloro" if res["cleared"] else "osteo")
        self.win.refresh()

    def _colonise(self) -> None:
        g = self.game
        sys = g.system
        body = sys.bodies[self.selected]
        options = colony_sim.colonies_for(body.kind, g.research.unlocked)
        if not options:
            self.win.toast("Nothing you know how to grow will take root there.", "warn")
            return

        chosen = {"id": None}
        cards = []
        widgets = [note("A grown colony gestates for months and costs almost nothing "
                        "in credits. A fabricator yard is the opposite bargain.")]
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
            # What it will actually produce. The dialog used to give a price
            # and a gestation time and nothing else, so a Free Port at 74,000
            # read much like a RADIX Mine at 12,000.
            plan = colony_sim.forecast(g, sys, body, c.id)
            yields = ", ".join(
                (f"{cr(round(v))}/day" if k == "credits" else f"{v:g} {k}/day")
                for k, v in plan.get("yields", {}).items())
            card.add(label(yields or "Produces nothing directly.", "",
                           "chloro" if yields else "dim", wrap=True))
            if plan.get("effects"):
                card.add(note("Grants: " + ", ".join(sorted(plan["effects"]))))
            if plan.get("upkeep"):
                card.add(note("Upkeep: " + ", ".join(
                    f"{v:g} {k}/day" for k, v in plan["upkeep"].items())))
            if plan.get("payback"):
                years = plan["payback"] / 365
                card.add(note(f"Pays for itself in about "
                              f"{years:.1f} year(s) once it is up."))
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
        g.add_log(f"Seed planted at {body.name}. Gestation {col.need} days.", "good")
        self.win.toast("Seed planted.", "chloro")
        self.win.refresh()
