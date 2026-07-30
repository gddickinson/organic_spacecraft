"""The diplomacy desk — standing, the relations matrix, and overtures."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..core.util import num, pct
from ..data.diplomacy import AGENDAS, CONCORD_RELATION, CONCORD_STANDING
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import diplomacy as dip
from ..sim import ventures as venture_sim
from . import exchequer_panel
from . import ventures_panel
from .widgets import (defer, Panel, Pill, TabBar, View, button, label, mono_label,
                      note, spacer)


def standing_figure(delta: float) -> str:
    """A movement in standing, never rendered as "-0".

    Courtship made the small end of this range real: a penalty of a tenth of
    a point formatted as "-0 standing", which reads as nothing and looks like
    a bug. Testing `abs(delta) < 0.5` was not enough — Python rounds a half to
    even, so exactly -0.5 formats as "-0" too. Ask what it rounds to.
    """
    return f"{delta:+.1f}" if round(delta) == 0 else f"{delta:+.0f}"


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
        self.col.addWidget(exchequer_panel.build(g))
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
        self._memory(p, g, fid)

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
        # Deferred: `_set_partner` rebuilds this screen, which frees the combo
        # while its own popup container is still delivering the mouse release
        # that dismissed it. Qt then filters an event on freed memory and the
        # process segfaults in `QComboBoxPrivateContainer::eventFilter`.
        combo.activated.connect(
            lambda _i, cb=combo: defer(
                lambda: self._set_partner(cb.currentData())))
        h.addWidget(combo, 1)
        p.add(partner_row)

        # Why the numbers below are smaller than they were. An overture used
        # to be worth the same at every standing, so a power that already
        # regarded you as Kin valued forty tonnes of biomass exactly as much
        # as one that distrusted you — and Concord was a shopping list.
        warmth = dip.courtship(g.rep.get(fid, 0.0))
        if warmth < 0.95:
            p.add(note(f"{FACTIONS_BY_ID[fid].short} already think well of "
                       f"you. An overture moves them about "
                       f"{warmth:.0%} of what it would move a stranger — "
                       "goodwill is cheapest from people who barely know you."))

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
            # What it buys, and what it costs you elsewhere. The screen used to
            # show a price and no benefit, so tribute at twelve thousand for
            # nine points read the same as relief at forty tonnes for eleven.
            partner = self.partner if action.id in needs_partner else None
            moved = dip.preview(g, action.id, fid, partner)
            for power, delta in moved.get("standing", []):
                p.add_row(FACTIONS_BY_ID[power].short,
                          f"{standing_figure(delta)} standing",
                          "chloro" if delta > 0 else "warn")
            # What a treaty is, beyond the standing. The blurb has promised
            # berthing and charts since treaties were written and the screen
            # quoted neither, so the instrument read as tribute at three times
            # the price.
            told = moved.get("accord")
            if told:
                p.add_row("Berthing",
                          (f"{told['relief']:.0%} off wharfage at their "
                           f"{told['quays']} quays" if told["quays"]
                           else "they hold no quay that charges"),
                          "chloro" if ok and told["quays"] else "dim")
                p.add_row("Their charts",
                          (f"{told['charts']} system(s) of theirs you cannot "
                           f"see — about {cr(told['worth'])} of broker's paper"
                           if told["charts"] else "nothing you do not have"),
                          "chloro" if ok and told["charts"] else "dim")
            rel = moved.get("relations")
            if rel:
                a, b, delta = rel
                p.add_row(f"{FACTIONS_BY_ID[a].short} ↔ "
                          f"{FACTIONS_BY_ID[b].short}",
                          f"{delta:+.0f} between them",
                          "chloro" if delta > 0 else "warn")
            if action.cooldown:
                p.add_row("Then not again for", f"{action.cooldown} days", "dim")
            if not ok:
                p.add(label(why, "", "warn"))
            label_text = action.name
            if action.id in needs_partner:
                label_text += f" — {FACTIONS_BY_ID[self.partner].short}"
            p.add_buttons(button(label_text,
                                 lambda _=False, a=action.id: self._do(a, fid),
                                 kind="primary" if ok else "", enabled=ok))
        return p

    def _memory(self, p: Panel, g, fid: str) -> None:
        """What they hold against you, and what it costs — by name and by day.

        Standing is a number that decays. This is the specific list, so a power
        that will not put work your way can be asked why and answer.
        """
        from ..core.util import stardate
        from ..sim import grudge as grudge_sim
        held = grudge_sim.feeling(g, fid)
        if abs(held) < 6 and not grudge_sim.because(g, fid):
            return
        p.add(spacer(3), mono_label("What they remember"))
        p.add_row("Their feeling", f"{held:+.0f}",
                  "warn" if held < -20 else ("chloro" if held > 20 else ""))
        bias = grudge_sim.price_bias(g, fid)
        if abs(bias - 1.0) > 0.005:
            p.add_row("Their prices to you",
                      f"{(bias - 1) * 100:+.0f}% on what you buy",
                      "warn" if bias > 1 else "chloro")
        deals, why = grudge_sim.will_deal(g, fid)
        if not deals:
            p.add(label(why, "", "warn", wrap=True))
        for entry in grudge_sim.because(g, fid):
            tint = "warn" if entry["weight"] < 0 else "chloro"
            when = ("" if entry["kind"] == "inherited"
                    else f"{stardate(entry['day'])} · ")
            p.add(label(f"{when}{entry['text']} ({entry['weight']:+.0f})",
                        "", tint, wrap=True))

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
