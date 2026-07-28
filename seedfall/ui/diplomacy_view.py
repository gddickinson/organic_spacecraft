"""The diplomacy desk — standing, the relations matrix, and overtures."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.diplomacy import AGENDAS, CONCORD_RELATION, CONCORD_STANDING
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import diplomacy as dip
from ..sim import ventures as venture_sim
from . import ventures_panel
from .widgets import (Panel, Pill, TabBar, View, button, label, mono_label,
                      note, spacer)


class DiplomacyView(View):
    def __init__(self, win):
        super().__init__(win)
        self.focus = "charter"
        self.partner = "concordat"

    def build(self) -> None:
        g = self.game
        prog = dip.concord_progress(g)
        self.head("Diplomacy",
                  f"{len(prog['kin'])}/{prog['kin_need']} powers at Kin · "
                  f"{len(prog['peace'])}/{prog['peace_need']} pairs at peace")

        self.col.addWidget(ventures_panel.build(self, g))
        self.col.addWidget(self._matrix(g, prog))

        tabs = TabBar([(p, FACTIONS_BY_ID[p].short) for p in dip.POWERS], self.focus)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)
        self.col.addWidget(self._desk(g, self.focus))

    def take_side(self, venture, stance: str) -> None:
        res = venture_sim.intervene(self.game, venture, stance)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _switch(self, fid: str) -> None:
        self.focus = fid
        if self.partner == fid:
            self.partner = next(p for p in dip.POWERS if p != fid)
        self.refresh()

    # ── the matrix ─────────────────────────────────────────────────────────

    def _matrix(self, g, prog) -> Panel:
        p = Panel("How they regard each other")
        p.add(note("Concord is not four separate meters. It needs every power at "
                   f"Kin ({CONCORD_STANDING}) with you *and* every pair of them "
                   f"at {CONCORD_RELATION} or better with each other. Brokering "
                   "is the only thing that moves the second number much."))
        for i, a in enumerate(dip.POWERS):
            for b in dip.POWERS[i + 1:]:
                value = dip.relation(g, a, b)
                band, tint = dip.relation_band(value)
                ok = value >= CONCORD_RELATION
                p.add_row(f"{FACTIONS_BY_ID[a].short} · {FACTIONS_BY_ID[b].short}",
                          f"{band} ({value:+.0f})", "chloro" if ok else tint)
        p.add(spacer(4), mono_label("Your standing"))
        for power in dip.POWERS:
            rep = g.rep.get(power, 0)
            band, tint = standing(rep)
            marks = []
            if dip.has_treaty(g, power):
                marks.append("treaty")
            if rep >= CONCORD_STANDING:
                marks.append("kin")
            p.add_row(FACTIONS_BY_ID[power].name,
                      f"{band} ({rep:+.0f})" + (f" · {', '.join(marks)}" if marks else ""),
                      "chloro" if rep >= CONCORD_STANDING else tint)
        return p

    # ── one power's desk ───────────────────────────────────────────────────

    def _desk(self, g, fid: str) -> Panel:
        fac = FACTIONS_BY_ID[fid]
        rep = g.rep.get(fid, 0)
        band, tint = standing(rep)
        p = Panel(fac.name, fac.tint)
        p.add(label(f"“{fac.creed}”", "sub"))
        p.add(label(fac.doctrine, "", wrap=True))
        p.add_row("Standing", f"{band} ({rep:+.0f})", tint)

        agenda = AGENDAS.get(fid)
        if agenda:
            p.add(spacer(3), mono_label("What they want"))
            p.add(label(agenda.name, "h3", fac.tint))
            p.add(note(agenda.blurb))
            p.add_row("Chronically short of", agenda.wants, "osteo")

        rivals = dip.rivals_of(g, fid)
        if rivals:
            p.add(note("On bad terms with: "
                       + ", ".join(FACTIONS_BY_ID[r].short for r in rivals)))

        p.add(spacer(4), mono_label("Overtures"))
        needs_partner = {"denounce", "broker"}
        partner_row = QWidget()
        h = QHBoxLayout(partner_row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addWidget(label("Third party", "dim"))
        combo = QComboBox()
        others = [o for o in dip.POWERS if o != fid]
        for o in others:
            combo.addItem(FACTIONS_BY_ID[o].name, o)
        if self.partner in others:
            combo.setCurrentIndex(others.index(self.partner))
        combo.activated.connect(lambda _i, cb=combo: self._set_partner(cb.currentData()))
        h.addWidget(combo, 1)
        p.add(partner_row)

        for action, ok, why in dip.available(g, fid):
            p.add(spacer(3))
            p.add(label(action.name, "h3", "chloro" if ok else "dim"))
            p.add(note(action.blurb))
            cost = []
            if action.cost_credits:
                cost.append(cr(action.cost_credits))
            if action.cost_goods:
                cost.append(f"{action.cost_goods[1]} {action.cost_goods[0]}")
            if cost:
                p.add_row("Cost", " · ".join(cost))
            if not ok:
                p.add(label(why, "", "warn"))
            label_text = action.name
            if action.id in needs_partner:
                label_text += f" — {FACTIONS_BY_ID[self.partner].short}"
            p.add_buttons(button(label_text,
                                 lambda _=False, a=action.id: self._do(a, fid),
                                 kind="primary" if ok else "", enabled=ok))
        return p

    def _set_partner(self, fid: str) -> None:
        self.partner = fid
        self.refresh()

    def _do(self, action_id: str, faction: str) -> None:
        other = self.partner if action_id in ("denounce", "broker") else None
        res = dip.perform(self.game, action_id, faction, other)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.dialog(res["action"].name,
                        [note(line) for line in res["lines"]] or ["Done."],
                        [("Log it", None)])
        self.win.refresh()
