"""The ship: the layer stack, what is fitted, who is aboard, and the hold."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import mass, num, pct
from ..data.chassis import CHASSIS_BY_ID, FAMILY_LABEL
from ..data.commodities import BY_ID
from ..data.part_types import SLOT_LABEL, SLOT_ORDER
from ..data.parts import part
from ..sim import loyalty as loyalty_sim
from ..sim.actions import transfer
from ..sim import trade as trade_sim
from ..sim.ship import cargo_used, hull_pct, is_breached
from .widgets import (Bar, Panel, Pill, View, button, label, mono_label, note,
                      spacer)


class ShipView(View):
    def build(self) -> None:
        g = self.game
        ship = g.ship
        ch = CHASSIS_BY_ID[ship.chassis]
        st = g.ship_stats

        sub = f"{FAMILY_LABEL[ch.family]} · {ch.role}"
        if ch.binomial:
            sub += f" · {ch.binomial}"
        self.head(f"{ch.name} «{ship.name}»", sub)

        self.row(self._layers(ship), self._performance(st, ch))
        self.row(self._fitted(ship), self._crew())
        self.col.addWidget(self._hold(ship, st))
        self.buttons(button("Refit or build", lambda: self.win.go("yard"),
                            kind="primary"))

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
            p.add_row("Bridge loyalty", f"{mood['mean']:.0f}"
                      + (f" · {mood['restless']} restless" if mood["restless"] else ""),
                      "warn" if mood["restless"] else "")
            p.add(spacer(3))
            for o in g.officers:
                row = QWidget()
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 0, 0, 0)
                h.addWidget(label(f"{o.name} · {o.role_name}"))
                h.addStretch(1)
                band, tint = loyalty_sim.band(o)
                h.addWidget(Pill(band, tint))
                h.addWidget(Pill(f"lvl {o.level}", "lumen"))
                p.add(row)
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
