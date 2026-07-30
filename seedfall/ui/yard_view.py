"""The shipyard: design a hull, refit the one you have, and manage the fleet."""

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QInputDialog, QWidget

from ..core.util import credits as cr
from ..core.util import duration, num, pct
from ..data.chassis import (CHASSIS, CHASSIS_BY_ID, FAMILY_LABEL,
                            FAMILY_NOTE, FAMILY_ORDER, FAMILY_TINT)
from ..data.part_types import SLOT_LABEL, SLOT_ORDER
from ..data.parts import part, parts_available
from ..sim import colony as colony_sim
from ..sim import loading
from ..sim import plans as plans_sim
from ..sim import consorts as consort_sim
from ..sim import shipyard
from ..sim.ship import Ship, hull_pct, stats
from .plans_panel import ShipPlan
from .widgets import (defer, Card, Panel, Pill, TabBar, View, button, label,
                      mono_label, note, spacer)


class YardView(View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "refit"
        self.design_chassis = None
        self.design_fitted: list[str] = []
        self.hull_family = "all"

    # ── frame ──────────────────────────────────────────────────────────────

    def build(self) -> None:
        g = self.game
        sysm = g.system
        self.head("Shipyard",
                  f"{sysm.name} · {sysm.port.name}" if sysm.port
                  else f"{sysm.name} · no yard here — design only")

        tabs = TabBar([("refit", "Refit"), ("build", "Lay down a hull"),
                       ("fleet", "Fleet")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.tab == "fleet":
            self._fleet(sysm)
            return
        self._ensure_design()
        if self.tab == "build":
            self._hull_picker()
        self.col.addWidget(self._plan())
        self.row(self._slot_editor(), self._preview(sysm))

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.design_chassis = None
        self.refresh()

    def _families_present(self) -> list[str]:
        buildable = self._buildable()
        return [f for f in FAMILY_ORDER if any(c.family == f for c in buildable)]

    def _ensure_design(self) -> None:
        if self.design_chassis is not None:
            return
        if self.tab == "refit":
            self.design_chassis = self.game.ship.chassis
            self.design_fitted = list(self.game.ship.fitted)
        else:
            buildable = self._buildable()
            self.design_chassis = buildable[0].id if buildable else "spore"
            self.design_fitted = []

    def _buildable(self) -> list:
        known = self.game.research.unlocked
        return [c for c in CHASSIS if not c.tech or c.tech in known]

    # ── hull picker ────────────────────────────────────────────────────────

    def _hull_picker(self) -> None:
        buildable = self._buildable()
        families = [f for f in FAMILY_ORDER if any(c.family == f for c in buildable)]
        if self.hull_family not in families:
            self.hull_family = families[0] if families else "grown"

        tabs = TabBar([("all", f"All ({len(buildable)})")]
                      + [(f, f"{FAMILY_LABEL[f]} "
                             f"({sum(1 for c in buildable if c.family == f)})")
                         for f in families],
                      self.hull_family)
        tabs.changed.connect(self._pick_family)
        self.col.addWidget(tabs)

        if self.hull_family != "all":
            self.col.addWidget(note(FAMILY_NOTE[self.hull_family]))
        else:
            self.col.addWidget(note(
                "A grown hull needs a nursery and months of gestation, and costs "
                "almost nothing in credits. A fabricated hull is welded in weeks "
                "for a great deal of money."))

        shown = [c for c in buildable
                 if self.hull_family == "all" or c.family == self.hull_family]
        cards = []
        for c in shown:
            card = Card()
            card.add(label(c.name, "h3", FAMILY_TINT[c.family]))
            card.add(Pill(FAMILY_LABEL[c.family], FAMILY_TINT[c.family]))
            card.add(label(c.binomial or c.role, "sub"))
            card.add(label(c.blurb, "", wrap=True))
            card.set_selected(c.id == self.design_chassis)
            card.clicked.connect(lambda _=False, cid=c.id: self._pick_hull(cid))
            cards.append(card)
        self.grid(cards, cols=3)

    def _pick_family(self, fid: str) -> None:
        self.hull_family = fid
        # Follow the filter through to the design, or you end up reading
        # synthetic hull cards while editing the SPORE you had selected before.
        shown = [c for c in self._buildable() if fid == "all" or c.family == fid]
        if shown and not any(c.id == self.design_chassis for c in shown):
            self.design_chassis = shown[0].id
            self.design_fitted = []
        self.refresh()

    def _pick_hull(self, cid: str) -> None:
        self.design_chassis = cid
        self.design_fitted = []
        self.refresh()

    # ── slot editor ────────────────────────────────────────────────────────

    def _plan(self) -> ShipPlan:
        """The ship as it would be, not as it is.

        `design_fitted` is already the prospective parts list and the model is
        a function of exactly that, so the shape on screen is what you would
        be flying if you paid. On the build tab the hull is somebody else's
        entirely, so it gets a mock with an empty hold.
        """
        g = self.game
        if self.tab == "build":
            subject = Ship(uid=0, name="", chassis=self.design_chassis,
                           fitted=list(self.design_fitted))
        else:
            subject = g.ship
        plan = ShipPlan(plans_sim.build(g, subject,
                                        fitted=list(self.design_fitted)),
                        height=300)
        return plan

    def _slot_editor(self) -> Panel:
        ch = CHASSIS_BY_ID[self.design_chassis]
        p = Panel(f"{ch.name} — fittings")
        for slot in SLOT_ORDER:
            cap = ch.slots.get(slot, 0)
            if not cap:
                continue
            here = [pid for pid in self.design_fitted
                    if part(pid) and part(pid).slot == slot]
            p.add(spacer(3), mono_label(f"{SLOT_LABEL[slot]} — {len(here)}/{cap}"))
            for pid in here:
                m = part(pid)
                row = QWidget()
                h = QHBoxLayout(row)
                h.setContentsMargins(0, 0, 0, 0)
                text = label(m.name)
                text.setToolTip(m.blurb)
                h.addWidget(text)
                h.addStretch(1)
                h.addWidget(label(self._fx_line(m), "dim"))
                h.addWidget(button("Remove", lambda _=False, x=pid: self._remove(x)))
                p.add(row)
            if len(here) < cap:
                options = parts_available(slot, ch, self.game.research.unlocked)
                if not options:
                    p.add(label("nothing researched for this slot", "dim"))
                    continue
                combo = QComboBox()
                combo.addItem(f"— add {SLOT_LABEL[slot].lower()} —", None)
                for o in options:
                    combo.addItem(f"{o.name} · {cr(o.cost.get('credits', 0))}", o.id)
                # Deferred for the same reason as every other combo: `_add`
                # rebuilds the panel and frees this box while its popup is
                # still handling the click that chose the item.
                combo.activated.connect(
                    lambda _idx, cb=combo: defer(
                        lambda: self._add(cb.currentData())))
                p.add(combo)
        return p

    def _fx_line(self, m) -> str:
        if m.wpn:
            traits = f" · {', '.join(m.wpn.traits)}" if m.wpn.traits else ""
            return (f"{m.wpn.dmg:g} dmg · bands "
                    f"{m.wpn.bands[0]}–{m.wpn.bands[1]}{traits}")
        return " · ".join(f"{k} {'+' if v > 0 else ''}{v:g}"
                          for k, v in m.fx.items()) or m.slot

    def _add(self, pid: str | None) -> None:
        if pid:
            self.design_fitted.append(pid)
            self.refresh()

    def _remove(self, pid: str) -> None:
        if pid in self.design_fitted:
            self.design_fitted.remove(pid)
            self.refresh()

    # ── preview ────────────────────────────────────────────────────────────

    def _preview(self, sysm) -> Panel:
        g = self.game
        ch = CHASSIS_BY_ID[self.design_chassis]
        mock = Ship(uid=0, name="", chassis=ch.id, fitted=list(self.design_fitted))
        st = stats(mock, g.bonuses, g.officers)
        ok, errs, brownout = shipyard.validate(ch, self.design_fitted)
        is_build = self.tab == "build"

        # The same question the build asks. Quoting the list price while the
        # yard charges less is the shape of bug this project keeps finding.
        made_here = colony_sim.fabricating(g, g.location_id)
        if is_build:
            cost = shipyard.cost_of(ch, self.design_fitted, made_here)
        else:
            cost, _added, _removed, refund = shipyard.refit_cost(
                ch, g.ship.fitted, self.design_fitted, made_here)
        can_afford, missing = shipyard.affordable(g, cost)
        missing_keys = {m[0] for m in missing}

        p = Panel("Projected" if is_build else "After refit")
        p.add_row("Jump", f"{st.jump:.1f} ly")
        p.add_row("Sublight", f"{st.speed:.2f}×")
        p.add_row("Sensors", f"{st.sensor:.1f} ly")
        p.add_row("Accuracy / evasion", f"{pct(st.accuracy)} / {pct(st.evade)}")
        p.add_row("Armour", num(st.armour))
        p.add_row("Regrowth", f"{st.regen:.2f}×" if st.regen > 0 else "—")
        p.add_row("Hold", f"{round(st.cargo)} t")
        p.add_row("Berths", num(st.berths))
        p.add_row("Power", f"{num(st.power)} / {num(st.draw)}")

        # Fitted mass against what the hull is rated to shift. Everything above
        # the marks is paid for in speed and evasion.
        mock.crew = ch.crew
        load = loading.summary(mock, 0.0)
        reads, tint = loading.note(mock, 0.0)
        p.add_row("Fitted mass", f"{round(load['parts'])} t")
        p.add_row("Loading",
                  f"{round(load['laden'])} / {round(load['capacity'])} t · {reads}",
                  tint)
        p.add_bar(min(1.0, load["loading"]),
                  "chloro" if load["loading"] <= 0.9 else "warn")
        if abs(load["factor"] - 1.0) > 0.01:
            better = load["factor"] > 1.0
            p.add_row("Speed and evasion",
                      f"{'+' if better else ''}{(load['factor'] - 1) * 100:.0f}% "
                      f"for the loading",
                      "chloro" if better else "warn")
        p.add_row("Armament",
                  f"{len(st.weapons)} mount(s), "
                  f"{sum(w.wpn.dmg for w in st.weapons):g} damage"
                  if st.weapons else "none")

        if brownout:
            p.add(label("Power deficit — everything will run degraded.", "", "warn",
                        wrap=True))
        for e in errs:
            p.add(label(e, "", "warn", wrap=True))

        p.add(spacer(5), mono_label("Bill"))
        for key, n in cost.items():
            p.add_row("Credits" if key == "credits" else key,
                      cr(n) if key == "credits" else f"{n:g} t",
                      "warn" if key in missing_keys else "")
        if made_here:
            # Otherwise the number is simply smaller than the yard list and
            # nothing on the screen accounts for it.
            listed = (shipyard.cost_of(ch, self.design_fitted, False) if is_build
                      else shipyard.refit_cost(ch, g.ship.fitted,
                                               self.design_fitted, False)[0])
            saved = listed.get("credits", 0) - cost.get("credits", 0)
            if saved > 0:
                p.add(note(f"A yard of yours in this system makes the "
                           f"fabricated fittings rather than buying them: "
                           f"{cr(saved)} off. The metal is charged either "
                           "way."))

        if is_build:
            here, why = shipyard.can_build_here(g, sysm, ch)
            p.add_row("Time in cradle", duration(shipyard.build_days(ch, g, sysm.id)))
            if not here:
                p.add(label(why, "", "warn", wrap=True))
            p.add_buttons(button("Lay down", self._lay_down, kind="primary",
                                 enabled=ok and can_afford and here))
        else:
            if refund:
                p.add(note(f"Removed parts sell back for {cr(refund)}."))
            # The rule is the sim's, not the button's — the button used to
            # hold a different, laxer one of its own.
            where, why = shipyard.can_refit_here(g)
            p.add_buttons(button("Apply refit" if where else "Not here",
                                 self._apply_refit, kind="primary",
                                 enabled=ok and can_afford and where,
                                 tip=why))
            if not where:
                p.add(label(why, "", "warn", wrap=True))
        return p

    def _lay_down(self) -> None:
        ch = CHASSIS_BY_ID[self.design_chassis]
        name, accepted = QInputDialog.getText(
            self.win, "Name the hull",
            "Charter hulls take a two-word name. Nobody enforces it.",
            text=ch.name)
        if not accepted:
            return
        job, why = shipyard.start_build(self.game, ch.id, self.design_fitted,
                                        self.game.system, name.strip() or ch.name)
        if not job:
            self.win.toast(why, "warn")
            return
        self.game.add_log(f"{job.name} laid down at {job.system_name}. "
                          f"Ready in {job.need} days.", "good")
        self.win.toast(f"{job.name} laid down.", "chloro")
        self.win.refresh()

    def _apply_refit(self) -> None:
        ok, why = shipyard.apply_refit(self.game, self.game.ship, self.design_fitted)
        if not ok:
            self.win.toast(why, "warn")
            return
        self.game.add_log("Refit complete.", "good")
        self.win.toast("Refit complete.", "chloro")
        self.design_chassis = None
        self.win.refresh()

    # ── fleet ──────────────────────────────────────────────────────────────

    def _fleet(self, sysm) -> None:
        g = self.game
        if g.building:
            slips = Panel("On the slips")
            for job in g.building:
                slips.add_row(f"{job.name} — {job.system_name}",
                              f"{max(0, job.need - round(job.days))} d")
                slips.add_bar(job.days / job.need if job.need else 0, "lumen")
            self.col.addWidget(slips)

        p = Panel("Hulls")
        # What the company costs is on the panel, not left to be discovered.
        # A consort is your own people in your own second hull and it eats out of
        # your hold — see `sim/upkeep.complement`, which did not count them until
        # this was written and so made a fleet free to keep.
        told = consort_sim.keep(g)
        p.add(note("You command one hull at a time. The rest wait where they were "
                   "built — unless you order them to sail in company, in which "
                   "case they follow your flag and fight beside it. They eat out "
                   "of your hold while they do."))
        if told["hulls"]:
            p.add_row(f"In company · {told['hulls']} hull(s)",
                      f"{told['crew']} more mouths · "
                      + (", ".join(f"{amount:.2f} t {cid} a day"
                                   for cid, amount in told["extra"].items())
                         or "nothing extra"),
                      "lumen")
        for s in list(g.fleet):
            ch = CHASSIS_BY_ID[s.chassis]
            active = s.uid == g.ship.uid
            here = active or s.docked_at == sysm.id
            row = QWidget()
            h = QHBoxLayout(row)
            h.setContentsMargins(0, 2, 0, 2)
            h.addWidget(label(f"{ch.name} «{s.name}»"))
            h.addWidget(label(f"{pct(hull_pct(s))} integrity · {s.crew} crew", "dim"))
            h.addStretch(1)
            if active:
                h.addWidget(Pill("flagship", "chloro"))
            elif getattr(s, "escort", False):
                h.addWidget(Pill("in company", "lumen"))
                h.addWidget(button("Send to berth",
                                   lambda _=False, sh=s: self._set_escort(sh, False)))
            elif here:
                h.addWidget(button("Sail with me",
                                   lambda _=False, sh=s: self._set_escort(sh, True),
                                   kind="primary"))
                h.addWidget(button("Take command",
                                   lambda _=False, sh=s: self._switch_ship(sh)))
                h.addWidget(button(f"Scrap · {cr(shipyard.scrap_value(s))}",
                                   lambda _=False, sh=s: self._scrap(sh), kind="danger"))
            else:
                h.addWidget(label("berthed elsewhere", "dim"))
            p.add(row)
        self.col.addWidget(p)

    def _set_escort(self, ship: Ship, sailing: bool) -> None:
        """Order a hull out, or send it back. The sim owns both.

        This used to write `ship.escort` and `ship.docked_at` here, so the rule
        about which hulls may be ordered out lived in whether the button was
        drawn — and a headless caller's first act was to order out a hull that
        was not even in the fleet. `consorts.sail`/`berth` are the door now.
        """
        res = (consort_sim.sail(self.game, ship) if sailing
               else consort_sim.berth(self.game, ship))
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        told = res["keep"]
        if sailing and told["a_day"] > 0:
            self.win.toast(
                f"{told['hulls']} in company · {told['crew']} more mouths, "
                f"{told['a_day']:.2f} t a day out of your hold.", "osteo")
        self.win.refresh()

    def _switch_ship(self, ship: Ship) -> None:
        g = self.game
        old = g.ship
        old.docked_at = g.system.id
        g.ship = ship
        for cid, n in old.cargo.items():
            ship.cargo[cid] = ship.cargo.get(cid, 0) + n
        old.cargo = {}
        g.add_log(f"Transferred your flag to {ship.name}.", "good")
        self.design_chassis = None
        self.win.refresh()

    def _scrap(self, ship: Ship) -> None:
        value = shipyard.scrap_value(ship)
        if not self.win.confirm("Scrap the hull",
                                f"{ship.name} will be broken up for {cr(value)}. "
                                "This cannot be undone."):
            return
        res = shipyard.scrap(self.game, ship)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()
