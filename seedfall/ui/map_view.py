"""The sector chart screen: the chart, what you know about the star you have
picked, and the ways to fly there.

The chart itself is `ui/star_chart.py`. **Its panel used to sit under it.**
The chart takes the full width and 420 px of height, and under it came the
orders, the legend, the reach note, the wall, the mesh and the Weave — so the
Fly buttons were about 1,100 px below the chart that chose where they went.
The picked star's panel stands beside the chart now, with a list of every
destination above it: the list is also the keyboard's way to a star, since
the chart is a picture and takes no focus.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QListWidget, QListWidgetItem, QVBoxLayout,
                             QWidget)

from ..core.util import credits as cr
from ..core.util import duration, num, reaction_mass
from ..data.factions import FACTIONS, FACTIONS_BY_ID
from ..sim import intel as intel_sim
from . import counsel_card, mesh_panel, orders_panel, weave_panel
from ..sim import rumours as rumour_sim
from ..sim import reach as reach_sim
from ..sim import anchorage as anchorage_sim
from ..sim.actions import distress_call, is_stranded, jump_quote, jump_to
from ..world.galaxy import distance
from . import theme
from . import soundmap
from .flow import Flow
from .star_chart import FACTION_COLOUR, StarChart, marker_radius  # noqa: F401
from .view_base import WrapRow
from .widgets import (Panel, TabBar, View, button, label, mono_label, note,
                      spacer)
from . import reaches_chart, reaches_panel


class PickList(QListWidget):
    """A list where Enter picks, on every platform.

    Qt's item views emit `itemActivated` on Enter everywhere except macOS,
    where Enter starts an edit and activation is Cmd+O — so on the platform
    this game is played on most, the list could be walked and never chosen
    from. Enter and Return are answered here, the same everywhere.
    """

    def keyPressEvent(self, ev):  # noqa: N802
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) \
                and self.currentItem() is not None:
            ev.accept()
            self.itemActivated.emit(self.currentItem())
            return
        super().keyPressEvent(ev)


class MapView(View):
    def __init__(self, win):
        super().__init__(win)
        self.chart = StarChart(win)
        self.chart.picked.connect(self._on_pick)
        self.selected: int | None = None
        #: Which region's tab is up, and the region the ship was in when it
        #: was chosen: when the ship crosses the rim the tab follows it.
        self.region: str | None = None
        self._aboard: str | None = None

    def _on_pick(self, sid: int) -> None:
        self.selected = sid
        self.refresh()

    def _show(self, region: str) -> None:
        """Switch tabs: the ship's star if it is there, else the far end."""
        from ..sim import regions as regions_sim
        self.region = region
        here = self.game.system
        mine = regions_sim.region_of(here)
        opened = {r.id: r for r in self.game.galaxy.regions}
        if mine == region:
            self.selected = here.id
        elif region == "verge":
            self.selected = opened[mine].anchor_id       # the way home
        else:
            self.selected = (opened[region].entry_id if region in opened
                             else None)
        from .widgets import defer
        defer(self.refresh)

    def _tabs(self, g) -> TabBar:
        """The Verge and the three regions past its rim, dark or open."""
        from ..data.regions import REGIONS
        from ..sim import regions as regions_sim
        names = regions_sim.names(g)
        tabs = [("verge", names["verge"])] + [
            (spec.id, spec.name + ("" if reaches_chart.is_open(g, spec.id)
                                   else " · dark")) for spec in REGIONS]
        bar = TabBar(tabs, self.region)
        bar.changed.connect(self._show)
        return bar

    def build(self) -> None:
        g = self.game
        from ..sim import regions as regions_sim
        aboard = regions_sim.region_of(g.system)
        if self.region is None or aboard != self._aboard:
            self.region, self._aboard = aboard, aboard
            self.selected = None
        self.chart.region = self.region
        known = intel_sim.summary(g, reaches_chart.systems(g, self.region))
        leads = rumour_sim.summary(g)
        sealed = not reaches_chart.is_open(g, self.region)
        self.head("Sector Chart",
                  f"{regions_sim.names(g)[self.region]} · "
                  + ("dark — nothing past its deep anchor has been seen"
                     if sealed else
                     f"{known['total']} stars · "
                     f"{known['counts'][0]} names only · "
                     f"{known['counts'][1]} scanned · "
                     f"{known['counts'][2]} visited · "
                     f"{known['charted']} charted")
                  + (f" · {leads['held']} lead(s) to follow" if leads["held"] else ""))

        self.col.addWidget(counsel_card.build(self, g))   # "what now"
        self.col.addWidget(self._tabs(g))
        if self.selected is None and not sealed:
            self.selected = g.location_id
        self.chart.selected = self.selected
        self.chart.setParent(None)
        # Beside the chart: where to go, and what flying there costs.
        side = QWidget()
        down = QVBoxLayout(side)
        down.setContentsMargins(0, 0, 0, 0)
        down.setSpacing(10)
        if sealed:
            down.addWidget(reaches_panel.sealed(self, g, self.region))
        else:
            down.addWidget(self._destinations())
            down.addWidget(self._info())
        down.addStretch(1)
        across = WrapRow(14)
        across.add(self.chart, 3, Qt.AlignmentFlag.AlignTop)
        across.add(side, 2)
        self.col.addWidget(across)
        self.chart.show()
        self.chart.update()

        self.col.addWidget(legend())
        # What the ring never said: how much of the sector this drive can
        # actually get to, and what the next one would open.
        self.col.addWidget(note(reach_sim.note(self.game)))
        self.col.addWidget(orders_panel.build(self, g))
        wall = self._way_out()
        if wall is not None:
            self.col.addWidget(wall)
        heard = mesh_panel.build(g)
        if heard is not None:
            self.col.addWidget(heard)
        self.col.addWidget(weave_panel.build(self, g))

    def _destinations(self) -> QListWidget:
        """Every star by distance: the chart's choices, for the keyboard.

        Arrows move through it and Enter (or a click) picks, which does what
        clicking the star does. Picking rebuilds this screen and with it the
        list, so the pick is deferred past the signal (`widgets.defer`).
        """
        g = self.game
        here = g.system
        reach = g.ship_stats.jump
        within = reach_sim.component(g)
        box = PickList()
        box.setObjectName("destinations")
        box.setAccessibleName("Destinations, nearest first")
        box.setMaximumHeight(170)
        stars = sorted(reaches_chart.systems(g, self.region),
                       key=lambda s: (distance(s, here), s.id))
        for sys in stars:
            ly = distance(sys, here)
            tags = ["here" if sys.id == here.id else f"{ly:.1f} ly"
                    if ly < float("inf") else "beyond the rim"]
            if sys.id != here.id and reach < ly < float("inf"):
                tags.append("beyond one jump" if sys.id in within
                            else "beyond reach")
            if sys.port and intel_sim.level(g, sys) >= 1:
                tags.append("port")
            item = QListWidgetItem(f"{sys.name} — " + " · ".join(tags))
            item.setData(Qt.ItemDataRole.UserRole, sys.id)
            box.addItem(item)
            if sys.id == self.selected:
                box.setCurrentItem(item)

        def pick(item):
            sid = item.data(Qt.ItemDataRole.UserRole)
            if sid == self.selected:
                return          # a click can also activate: pick once
            self.selected = sid
            from .widgets import defer
            defer(lambda: self._on_pick(sid))
        box.itemActivated.connect(pick)
        box.itemClicked.connect(pick)
        return box

    def _step(self, dest: int) -> None:
        from ..sim import gates as gates_sim
        out = gates_sim.use(self.game, dest)
        if not out.get("ok"):
            self.win.toast(out["why"], "warn")
            return
        self.selected = dest
        from ..sim import regions as regions_sim
        self.region = regions_sim.region_of(self.game.galaxy.systems[dest])
        self.win.toast(f"{out['ly_saved']:.0f} light years, no time at all. "
                       f"₡{out['credits']:,.0f} in tolls.", "good")
        self.win.refresh()

    def _wake(self) -> None:
        from ..sim import gates as gates_sim
        out = gates_sim.wake(self.game)
        if not out.get("ok"):
            self.win.toast(out["why"], "warn")
            return
        self.win.toast(f"It is burning. {out.get('links', 0)} ring(s) answer.",
                       "good")
        self.win.refresh()

    def _build(self) -> None:
        from ..sim import gates as gates_sim
        out = gates_sim.build(self.game)
        if not out.get("ok"):
            self.win.toast(out["why"], "warn")
            return
        self.win.toast("The anchor is lit, and it is yours.", "good")
        self.win.refresh()

    def _way_out(self):
        """What getting past the wall would actually take, item by item.

        Naming a drive and stopping there is the same defect as a contract fee
        with no cargo cost beside it. Measured, the way out of a small pocket
        is twelve technologies, five thousand research points, seventy-eight
        thousand credits and twenty tonnes of magnetite — a project, not a
        purchase — and whether the ports you *can* reach sell those materials
        is the thing that decides whether it is a project at all.
        """
        from ..core.util import credits as cr
        from ..data.tech import TECH_BY_ID
        plan = reach_sim.plan(self.game)
        if not plan or plan["step"]["gain"] <= 0:
            return None
        step = plan["step"]
        p = Panel(f"Getting past the wall — {step['part'].name}")
        p.add(self.hint(
            "It opens the rest of the sector. This is what it takes, and "
            "whether the ports you can already reach can supply it."))
        p.add_row("Opens", f"{step['gain']} more systems "
                           f"({plan['within']} → {step['within']})")
        if plan["tech"]:
            done = len(plan["tech"])
            p.add_row("Still to research",
                      f"{done} technolog{'y' if done == 1 else 'ies'} · "
                      f"{plan['points']:,} points",
                      "osteo")
            p.add(note(", ".join(
                TECH_BY_ID[t].name for t in plan["tech"][:6]
                if t in TECH_BY_ID) + (" …" if done > 6 else "")))
        short = plan["have_credits"] - plan["credits"]
        p.add_row("Credits", f"{cr(plan['credits'])} "
                             f"({'have it' if short >= 0 else f'{cr(-short)} short'})",
                  "chloro" if short >= 0 else "osteo")
        for material in plan["materials"]:
            where = ", ".join(material["sold_at"][:2]) or "nowhere you can reach"
            p.add_row(f"{material['need']:g} t {material['id']}",
                      f"have {material['have']:g} · sold at {where}",
                      "warn" if material["short"] else "")
        p.add_row("Yard", ", ".join(plan["yards"][:2]) or "none in reach",
                  "warn" if not plan["yards"] else "")
        if plan["reachable"]:
            p.add(label("Everything it needs can be had from where you are. "
                        "It is a long project and it is not a trap.", "",
                        "chloro", wrap=True))
        else:
            p.add(label("Something it needs is not for sale anywhere you can "
                        "reach. Mine it, or take it off somebody.", "",
                        "warn", wrap=True))
        return p

    def _info(self) -> Panel:
        g = self.game
        sys = g.galaxy.systems[self.selected]
        q = jump_quote(g, sys)
        here = sys.id == g.location_id
        fac = FACTIONS_BY_ID.get(sys.faction) if sys.faction else None

        panel = Panel(sys.name + ("   ·   you are here" if here else ""))
        rank = intel_sim.level(g, sys)
        # **The body count is fogged too**: printing `len(sys.bodies)` at
        # every rank left the bottom two rungs differing by a dot's shade.
        count = intel_sim.body_count(g, sys)
        panel.add(note(f"{sys.star_name} · "
                       + (f"{count} catalogued bodies" if count is not None
                          else "how many bodies, nobody has said")))
        if fac and rank >= 1:
            panel.add(label(f"{fac.name}. {fac.creed}", "", wrap=True))
        elif rank >= 1:
            panel.add(label("Unclaimed space.", "dim"))
        else:
            panel.add(label("Whose space this is, nobody here has said.", "dim"))
        if sys.note:
            panel.add(label(sys.note, "", "warn", wrap=True))
        # What has grown there, and only where somebody of yours can see it.
        if intel_sim.sees_bloom(g, sys):
            if sys.bloom > 0.02:
                panel.add(label(f"Bloom mass: {round(sys.bloom * 100)}% of this "
                                "system converted.", "", "warn", wrap=True))
        else:
            panel.add(label("Nothing of yours is watching it, so what has "
                            "grown there since anybody looked is not known.",
                            "", "dim", wrap=True))
        name, tint = intel_sim.label(g, sys)
        panel.add_row("Knowledge", name, tint)
        panel.add(note(intel_sim.blurb(g, sys)))
        if rank >= 1 and rank < 3:
            done = intel_sim.survey_fraction(sys)
            panel.add_row("Bodies surveyed",
                          f"{round(done * len(sys.bodies))}/{len(sys.bodies)}")
            panel.add_bar(done, "lumen")
        if rank == 0:
            # Priced on the flying somebody did to make it, and saying what it
            # buys — both of which are `sim/intel.chart_offer`, because the price
            # used to be `900 + 260 a body` and therefore *was* the answer.
            offer = intel_sim.chart_offer(g, sys)
            panel.add(note("A chart of this system buys you "
                           + ", ".join(offer["buys"]) + "."))
            panel.add_buttons(button(f"Buy the chart — {cr(offer['price'])}",
                                     lambda _=False, sid=sys.id: self._buy_chart(sid),
                                     enabled=offer["can"]))
        for rumour in rumour_sim.about(g, sys.id):
            kind = rumour.definition
            panel.add(label(kind.name, "", kind.tint))
            panel.add(note(kind.claim.format(system=sys.name)))

        if q.get("beyond"):
            # Past the rim from here: the way is a deep gate, not a drive.
            panel.add(reaches_panel.beyond(self, g, sys))
            return panel
        panel.add(mono_label("Passage"))
        panel.add_row("Distance", f"{q['ly']:.1f} ly")
        panel.add_row("Jump range", f"{g.ship_stats.jump:.1f} ly")
        panel.add_row("Transit", "—" if here else duration(q["days"]))
        panel.add_row("Reaction mass", "—" if here else reaction_mass(q["fuel"]),
                      "warn" if (not here and
                                 g.ship.cargo.get("volatiles", 0) < q["fuel"]) else "")
        panel.add_row("Port", (sys.port.name + (" (capital)" if sys.port.capital else ""))
                      if sys.port else "none")
        # What the berth actually offers. "How would I navigate back to a
        # shipyard" is unanswerable if the chart will not say which systems
        # have one.
        if sys.port:
            panel.add_row("Offers", ", ".join(
                anchorage_sim.SERVICE_NAMES.get(x, x)
                for x in sys.port.services))
        panel.add_row("Your holdings",
                      num(len([c for c in g.colonies if c.system_id == sys.id])))

        if here:
            panel.add_buttons(
                button("Enter system", lambda: self.win.go("system"), kind="primary"),
                button("Dock", lambda: self.win.go("port")) if sys.port else None)
        else:
            # The four ways to fly it, each stating what it costs on both
            # clocks. A bare "Set course" could not say that a hard burn buys
            # the crew four years of their lives back.
            from .crossing_panel import how_to_fly
            panel.add(how_to_fly(self, g, sys))

        if is_stranded(g):
            panel.add(spacer(4))
            panel.add(label(
                "You cannot reach anywhere, cannot buy reaction mass and cannot "
                "make any here. Somebody will come if you ask — and they will "
                "remember that you asked.", "", "warn", wrap=True))
            panel.add_buttons(button("Broadcast distress", self._distress,
                                     kind="danger"))
        return panel

    def _distress(self) -> None:
        res = distress_call(self.game)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.dialog(
            "Answered",
            [f"A {res['faction']} tender reached you after {res['days']} days and "
             f"towed you to {res['port'].name}. They took two thousand credits, "
             "left twenty tonnes of reaction mass, and logged the whole thing."],
            [("Log it", None)])
        self.selected = self.game.location_id
        self.win.refresh()

    def _buy_chart(self, system_id: int) -> None:
        res = intel_sim.buy_chart(self.game, self.game.galaxy.systems[system_id])
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _jump(self, crossing: str = "steady") -> None:
        self.crossing = crossing
        res = jump_to(self.game, self.selected, crossing)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        soundmap.act(self.win, "jump")
        if self.win.check_ending():
            return
        if res.get("event"):
            ev = res["event"]
            texts = [ev["text"]]
            if ev["effect"].get("note"):
                texts.append(note(ev["effect"]["note"]))
            self.win.dialog("In transit", texts, [("Carry on", None)])
        if res.get("encounter"):
            self.win.begin_combat(res["encounter"], "system")
            return
        self.selected = self.game.location_id
        self.win.go("system")


def legend() -> QWidget:
    """What the chart's marks mean, with the colours shown, not named.

    It was a line of words — "Charter · Concordat · Freeholds …" — naming the
    six powers' colours without showing one of them, so the only way to read
    whose a port was, was to already know.
    """
    marks = [f"<span style='color:{FACTION_COLOUR.get(f.id, theme.INK3)}'>◎"
             f"</span> {f.short}" for f in FACTIONS if not f.hidden]
    marks += ["○ catalogued", "◍ scanned", "● visited", "◌ charted",
              "∧ something said about it", "dashed ring = jump range",
              "╲ beyond reach", "<span style='color:#e2ba60'>◉</span> Weave "
              "anchor (gold = lit)", "<span style='color:#b084ee'>◇</span> "
              "deep anchor (violet = relit)",
              "<span style='color:#e0685f'>⌜⌟</span> "
              "hulls nobody claims, heard by the mesh"]
    made = []
    for mark in marks:
        lb = label(mark, "note")
        lb.setTextFormat(Qt.TextFormat.RichText)
        made.append(lb)
    return Flow(made, spacing=14, line=2)
