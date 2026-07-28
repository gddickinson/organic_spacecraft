"""The ship: the layer stack, what is fitted, who is aboard, and the hold."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import mass, num, pct
from ..data.chassis import CHASSIS_BY_ID, FAMILY_LABEL
from ..data.commodities import BY_ID
from ..data.part_types import SLOT_LABEL, SLOT_ORDER
from ..data.parts import part
from ..sim import dormancy as dormancy_sim
from ..sim import lifespan as lifespan_sim
from ..sim import loyalty as loyalty_sim
from ..sim import upkeep as upkeep_sim
from ..sim import plans as plans_sim
from ..sim.actions import transfer
from ..sim import trade as trade_sim
from ..sim.ship import cargo_used, hull_pct, is_breached
from .plans_panel import ShipPlan
from .widgets import (body_or, Bar, Panel, Pill, TabBar, View, button, label,
                      mono_label, note, spacer)


class ShipView(View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "readout"
        self.plan = None
        self._caption = None

    def build(self) -> None:
        g = self.game
        ship = g.ship
        ch = CHASSIS_BY_ID[ship.chassis]
        st = g.ship_stats

        sub = f"{FAMILY_LABEL[ch.family]} · {ch.role}"
        if ch.binomial:
            sub += f" · {ch.binomial}"
        self.head(f"{ch.name} «{ship.name}»", sub)

        tabs = TabBar([("readout", "Readout"), ("plans", "Plans")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.tab == "plans":
            self._plans(ship, ch, st)
            return

        self.row(self._layers(ship), self._performance(st, ch))
        self.row(self._fitted(ship), self._crew())
        self.col.addWidget(self._sleep())
        self.col.addWidget(self._hold(ship, st))
        self.buttons(button("Refit or build", lambda: self.win.go("yard"),
                            kind="primary"))

    def _sleep(self):
        from .dormancy_panel import who_sleeps
        return who_sleeps(self, self.game)

    def sleep_crew(self, method_id: str, count: int) -> None:
        res = dormancy_sim.put_under(self.game, method_id, count)
        if not res.get("ok"):
            self.win.toast(res.get("why", "No."), "warn")
            return
        self.win.save()
        self.refresh()

    def wake_crew(self) -> None:
        res, lines = dormancy_sim.wake(self.game, self.game.rng("wake"))
        if not res.get("ok"):
            self.win.toast(res.get("why", "Nobody is under."), "warn")
            return
        for kind, text in lines:
            self.game.add_log(text, kind)
        body = [text for _kind, text in lines] or \
            ["They are all up, and none the worse."]
        self.win.dialog(f"Up after {res['days']} days", body,
                        [("Back to work", None)])
        self.win.save()
        self.refresh()

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    # ── plans ──────────────────────────────────────────────────────────────

    def _plans(self, ship, ch, st) -> None:
        """The ship as a shape, with the numbers hung off the piece you click."""
        self.col.addWidget(body_or(self.hint(
            "Drag to turn her over, scroll to close in, click any piece to "
            "read it. Everything here is the ship as fitted — refit and the "
            "model changes, because the model is the fitted list.")))
        self.plan = ShipPlan(plans_sim.build(self.game, ship,
                                            cutaway=self._cut), height=460)
        self.plan.picked.connect(self._picked)
        self.col.addWidget(self.plan, 1)
        self._caption = note(self._legend(ship, ch, st))
        self.col.addWidget(self._caption)
        self.row(self._anatomy(ship, ch), self._stowage(ship, st))
        self.buttons(
            button("Turn", lambda: self.plan.turn(0.5)),
            button("Cutaway" if not self._cut else "Skin on", self._toggle_cut),
            button("Refit or build", lambda: self.win.go("yard"),
                   kind="primary"))

    _cut = False

    def _toggle_cut(self) -> None:
        ShipView._cut = not ShipView._cut
        self.refresh()

    def _picked(self, tag: str) -> None:
        if self._caption is not None:
            name, detail = self.plan.describe(tag)
            self._caption.setText(
                f"{name} — {detail}" if name else
                self._legend(self.game.ship, CHASSIS_BY_ID[self.game.ship.chassis],
                             self.game.ship_stats))

    def _legend(self, ship, ch, st) -> str:
        return (f"{len(ship.fitted)} fittings · hull {pct(hull_pct(ship))} · "
                f"hold {mass(cargo_used(ship))} of {mass(st.cargo)} · "
                f"{len(self.game.officers)} of {ch.crew} berths filled")

    def _anatomy(self, ship, ch) -> Panel:
        p = Panel("Anatomy")
        p.add(note("What is where, outermost layer first. A breach reads on "
                   "the model as well as in the list."))
        for name, fraction, _tint in plans_sim.layer_health(ship):
            p.add_row(name, pct(fraction),
                      tint="warn" if fraction < 0.35 else None)
        return p

    def _stowage(self, ship, st) -> Panel:
        p = Panel("Stowage")
        used = cargo_used(ship)
        fill = used / max(1.0, st.cargo)
        p.add_row("Hold", f"{mass(used)} of {mass(st.cargo)}")
        p.add(Bar(fill, "warn" if fill > 0.95 else "chloro"))
        if not ship.cargo:
            p.add(note("Empty. The hold draws as an outline until there is "
                       "something in it."))
        for cid, tonnes in sorted(ship.cargo.items(), key=lambda kv: -kv[1]):
            if tonnes > 0:
                c = BY_ID.get(cid)
                p.add_row(c.name if c else cid, mass(tonnes))
        return p

    def _layers(self, ship) -> Panel:
        p = Panel("Hull layers")
        p.add(note("Damage lands outermost first. The critical layer is the pressure "
                   "vessel; below it there is only crew."))
        for L in ship.layers:
            frac = L.hp / L.max if L.max else 0
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 1, 0, 1)
            name = label(L.name, "", "warn" if L.hp <= 0 else
                         ("osteo" if L.critical else ""))
            name.setToolTip(L.note)
            name.setMinimumWidth(180)
            h.addWidget(name)
            bar = Bar(frac, "warn" if frac < 0.3 else ("osteo" if L.critical else "chloro"))
            h.addWidget(bar, 1)
            v = label(pct(frac), "dim")
            v.setFixedWidth(42)
            h.addWidget(v)
            p.add(row)
        p.add(spacer(4))
        hp = hull_pct(ship)
        p.add_row("Overall integrity", pct(hp), "warn" if hp < 0.4 else "")
        if is_breached(ship):
            p.add(label("The pressure vessel is open. The crew is on bottled air "
                        "and dying slowly.", "", "warn", wrap=True))
        return p

    def _performance(self, st, ch) -> Panel:
        p = Panel("Performance")
        rows = [
            ("Jump range", f"{st.jump:.1f} ly"),
            ("Sublight", f"{st.speed:.2f}×"),
            ("Sensors", f"{st.sensor:.1f} ly"),
            ("Survey quality", pct(st.scan)),
            ("Accuracy", pct(st.accuracy)),
            ("Evasion", pct(st.evade)),
            ("Armour soak", num(st.armour)),
            ("Regrowth", f"{st.regen:.2f}×" if st.regen > 0 else "none — fabricated"),
            ("Power", f"{num(st.power)} generated · {num(st.draw)} drawn"),
            ("Heat", f"{round(self.game.ship.heat)} / {num(st.heat_cap)} · "
                     f"vents {num(st.vent)}/turn"),
            ("Extraction", f"{st.mine:.1f} t ore · {st.phos:.2f} t phosphate · "
                           f"{st.drink:.1f} t ice per day"),
            ("Research", f"{st.research:.2f}/day"),
            ("Air reserve", f"{round(st.o2_days)} days"),
            ("Hull mass", mass(ch.mass_t)),
        ]
        for k, v in rows:
            p.add_row(k, v)
        if st.brownout < 1:
            p.add(label(f"Power deficit — every system is running at "
                        f"{pct(st.brownout)}.", "", "warn", wrap=True))
        return p

    def _fitted(self, ship) -> Panel:
        ch = CHASSIS_BY_ID[ship.chassis]
        p = Panel("Fitted systems")
        for slot in SLOT_ORDER:
            cap = ch.slots.get(slot, 0)
            if not cap:
                continue
            ids = [pid for pid in ship.fitted if part(pid) and part(pid).slot == slot]
            p.add(spacer(3), mono_label(f"{SLOT_LABEL[slot]} — {len(ids)}/{cap}"))
            if not ids:
                p.add(label("empty", "dim"))
            for pid in ids:
                m = part(pid)
                off = pid in ship.disabled
                row = QWidget()
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 0, 0, 0)
                text = m.name
                if m.wpn:
                    text += (f"  —  {m.wpn.dmg:g} dmg, bands "
                             f"{m.wpn.bands[0]}–{m.wpn.bands[1]}")
                lb = label(text, "", "warn" if off else "")
                lb.setToolTip(m.blurb)
                h.addWidget(lb)
                h.addStretch(1)
                if off:
                    h.addWidget(Pill("offline", "warn"))
                h.addWidget(label(f"{m.mass:g} t", "dim"))
                p.add(row)
        return p

    def _crew(self) -> Panel:
        g = self.game
        p = Panel(f"Complement — {g.ship.crew}")
        p.add_row("Morale", pct(g.ship.morale))
        p.add_bar(g.ship.morale, "warn" if g.ship.morale < 0.4 else "lumen")
        p.add(spacer(4))
        if g.officers:
            mood = loyalty_sim.summary(g)
            p.add_row("Upkeep a day", ", ".join(
                f"{v:.2f} t {k}" for k, v in sorted(upkeep_sim.demand(g).items()))
                or "nothing")
            p.add_row("Bridge loyalty", f"{mood['mean']:.0f}"
                      + (f" · {mood['restless']} restless" if mood["restless"] else ""),
                      "warn" if mood["restless"] else "")
            p.add(spacer(3))
            for o in lifespan_sim.active(g.officers):
                row = QWidget()
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 0, 0, 0)
                h.addWidget(label(f"{o.name} · {o.role_name}"))
                h.addStretch(1)
                band, tint = loyalty_sim.band(o)
                h.addWidget(Pill(band, tint))
                h.addWidget(Pill(f"lvl {o.level}", "lumen"))
                p.add(row)
                # What they are made of and how far through their run. Nobody
                # aged at all until there were two clocks; now a long crossing
                # is something you can watch happen to people.
                where = lifespan_sim.stage(o, g)
                p.add(label(lifespan_sim.note(o, g), "note",
                            "warn" if where in ("declining", "past their span")
                            else ""))
                conviction = loyalty_sim.conviction_of(o)
                if conviction is not None:
                    p.add(label(conviction.name, "note"))
        else:
            p.add(note("No officers signed on."))
        return p

    def _hold(self, ship, st) -> Panel:
        used = cargo_used(ship)
        p = Panel("Hold")
        p.add_row("Capacity", f"{round(used)} / {round(st.cargo)} t")
        p.add_bar(used / st.cargo if st.cargo else 0, "osteo")

        items = [(k, v) for k, v in ship.cargo.items() if v > 0.01]
        if not items:
            p.add(note("Empty."))
        for cid, n in items:
            p.add(self._transfer_row(cid, n, to_ship=False))

        stores = [(k, v) for k, v in self.game.stores.items() if v > 0.01]
        if stores:
            p.add(spacer(6), mono_label("Empire depot"))
            for cid, n in stores:
                p.add(self._transfer_row(cid, n, to_ship=True))
        return p

    def _transfer_row(self, cid: str, n: float, to_ship: bool) -> QWidget:
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(label(BY_ID[cid].name if cid in BY_ID else cid))
        h.addStretch(1)
        h.addWidget(label(f"{round(n * 10) / 10:g}", "dim"))
        h.addWidget(button("→ hold" if to_ship else "→ depot",
                           lambda: self._move(cid, n, to_ship)))
        if not to_ship:
            # Somewhere to put cargo you cannot sell and cannot carry. Without
            # this a full hold and an empty tank is a hard stranding: no room
            # to mine ice for reaction mass, no mass to jump on.
            h.addWidget(button("vent", lambda: self._vent(cid),
                               kind="danger", tip="Put it over the side"))
        return row

    def _vent(self, cid: str) -> None:
        name = BY_ID[cid].name if cid in BY_ID else cid
        if not self.win.confirm("Vent the hold",
                                f"All the {name} goes over the side. It is not "
                                "coming back."):
            return
        trade_sim.jettison(self.game, cid)
        self.win.refresh()

    def _move(self, cid: str, n: float, to_ship: bool) -> None:
        moved = transfer(self.game, cid, n, to_ship)
        if moved <= 0:
            self.win.toast("No room." if to_ship else "Nothing to move.", "warn")
        self.win.refresh()
