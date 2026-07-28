"""A port: the market, the services counter, and whoever is looking for a berth."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QSpinBox, QWidget

from ..core.util import credits as cr
from ..core.util import pct
from ..data.commodities import BY_ID, COMMODITIES, bulk_of
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import allegiance
from ..sim import chains as chain_sim
from ..sim import services as services_sim
from ..sim import officials as officials_sim
from ..sim import trade as trade_sim
from ..sim import loyalty as loyalty_sim
from ..sim import customs as customs_sim
from . import blackmarket_panel
from . import commissions_panel
from . import freight_panel
from . import register_panel
from . import rumours_panel
from ..sim import intel as intel_sim
from ..sim import market as market_sim
from ..sim import rumours as rumour_sim
from .berths_panel import BerthsMixin
from ..sim.fieldwork import buy_field_notes, xeno_notes_price
from ..sim import xeno as xeno_sim
from ..sim import contracts as contract_sim
from ..sim import diplomacy as dip_sim
from ..sim.ship import add_cargo, cargo_free, cargo_used, hull_pct
from ..world.economy import (apply_sale, apply_trade, buy_price, demands,
                             price_note, sell_price)
from . import theme
from .widgets import (Card, Panel, Pill, TabBar, View, button, label,
                      mono_label, note, spacer)


class PortView(BerthsMixin, View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "market"
        self._pool = None
        self._pool_system = None

    def build(self) -> None:
        g = self.game
        sys = g.system
        if not sys.port:
            self.head("No port here", "Nothing in this system will sell you anything.")
            self.buttons(button("Back to system", lambda: self.win.go("system")))
            return

        fac = FACTIONS_BY_ID.get(sys.port.faction)
        rep = g.rep.get(fac.id, 0) if fac else 0
        band, tint = standing(rep)
        # Standing at a quay means writing down what it is paying today.
        market_sim.note_prices(g, sys, rep, g.ship_stats.trade)
        self.head(f"{sys.name} · {sys.port.name}",
                  f"{fac.name if fac else 'Independent'} — standing: {band} "
                  f"({'+' if rep > 0 else ''}{round(rep)})")

        tabs = TabBar([("market", "Market"), ("contracts", "Contracts"),
                       ("services", "Services"), ("crew", "Berths"),
                       ("desk", "The desk")], self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.tab == "contracts":
            self._contracts(sys)
        elif self.tab == "services":
            self._services(sys, fac, rep)
        elif self.tab == "crew":
            self._berths(sys)
        elif self.tab == "desk":
            self._desk(sys)
        else:
            self._market(sys, fac, rep)

    def _desk(self, sysm) -> None:
        """Whoever runs this quay, and what they will do for you."""
        from .official_panel import what_to_ask, whos_here
        self.row(whos_here(self, self.game, sysm),
                 what_to_ask(self, self.game, sysm))

    def learn_about(self, sysm) -> None:
        res = officials_sim.learn_lever(
            self.game, sysm, "a bosun who talks when the shift ends")
        if not res.get("ok"):
            self.win.toast(res.get("why", "Nothing to learn."), "warn")
            return
        self.win.dialog("You hear something",
                        [res["text"],
                         note("It is not much. It is enough.")],
                        [("Keep it to yourself", None)])
        self.win.save()
        self.refresh()

    def ask_favour(self, sysm, favour_id: str, lean: bool) -> None:
        res = officials_sim.ask(self.game, sysm, favour_id, lean)
        if not res.get("ok"):
            self.win.toast(res.get("why", "They will not."), "warn")
            return
        self.win.toast(
            ("They do it, and they remember how you asked."
             if res["leant"] else "They do it."),
            "warn" if res["leant"] else "")
        self.win.save()
        self.refresh()

    def _switch(self, tid: str) -> None:
        self.tab = tid
        self.refresh()

    # ── market ─────────────────────────────────────────────────────────────

    def _market(self, sys, fac, rep) -> None:
        g = self.game
        m = sys.market
        wants = ", ".join(BY_ID[c].name for c in demands(m))
        self.col.addWidget(note(
            f"This port is short of: {wants}.   Hold: {round(cargo_used(g.ship))}/"
            f"{round(g.ship_stats.cargo)} t."))

        news = register_panel.local_news(g, sys)
        if news is not None:
            self.col.addWidget(news)

        panel = Panel()
        grid = QWidget()
        gl = QGridLayout(grid)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setHorizontalSpacing(12)
        gl.setVerticalSpacing(6)
        for i, head in enumerate(("Commodity", "Buy", "Sell", "Local", "Aboard", "")):
            gl.addWidget(mono_label(head), 0, i)

        row = 1
        for c in COMMODITIES:
            # A good this power seizes has no counter here. Leaving the posted
            # sell price up let you hand unlicensed seed over the desk at a
            # Yards station for a receipt, which is the exact thing the
            # boarding party is there to stop.
            banned = customs_sim.outlaws(sys.port.faction, c.id)
            bp = buy_price(m, c.id, rep, g.ship_stats.trade)
            sp = (None if banned
                  else sell_price(m, c.id, rep, g.ship_stats.trade))
            held = g.ship.cargo.get(c.id, 0)
            if bp is None and held <= 0:
                continue
            note_text, note_tint = (("seized on sight", "warn") if banned
                                    else price_note(m, c.id))

            name = label(c.name)
            name.setToolTip(c.blurb)
            gl.addWidget(name, row, 0)
            gl.addWidget(label(cr(bp) if bp else "—"), row, 1)
            gl.addWidget(label(cr(sp) if sp else "—"), row, 2)
            gl.addWidget(Pill(note_text, note_tint), row, 3)
            gl.addWidget(label(f"{held:g}" if held else "—"), row, 4)

            actions = QWidget()
            from PyQt6.QtWidgets import QHBoxLayout
            ah = QHBoxLayout(actions)
            ah.setContentsMargins(0, 0, 0, 0)
            ah.setSpacing(4)
            qty = QSpinBox()
            qty.setRange(1, 9999)
            qty.setValue(10)
            qty.setFixedWidth(66)
            ah.addWidget(qty)
            ah.addWidget(button("Buy", lambda cid=c.id, q=qty: self._buy(cid, q.value()),
                                enabled=bp is not None))
            ah.addWidget(button("Sell", lambda cid=c.id, q=qty: self._sell(cid, q.value()),
                                enabled=held > 0 and not banned))
            gl.addWidget(actions, row, 5)
            row += 1

        panel.add(grid)
        self.col.addWidget(panel)
        quiet = blackmarket_panel.offer(g, sys, self._sell_quietly, self._dump)
        if quiet is not None:
            self.col.addWidget(quiet)
        tip = blackmarket_panel.tipoff(g, sys)
        if tip is not None:
            self.col.addWidget(tip)
        stall = freight_panel.desk(g, sys)
        if stall is not None:
            self.col.addWidget(stall)
        self.col.addWidget(register_panel.register(g, sys))

    def _sell_quietly(self, cid: str) -> None:
        res = customs_sim.sell_quietly(self.game, cid)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.toast("Nobody signed anything." if res["all"] else
                       f"They took {res['tonnes']:g} t. That is what they can "
                       "move.", "osteo")
        self.win.refresh()

    def _dump(self, cid: str) -> None:
        if not self.win.confirm("Vent the hold",
                                "It goes to space and it is not coming back."):
            return
        customs_sim.jettison(self.game, cid)
        self.win.refresh()

    def _buy(self, cid: str, units: int) -> None:
        res = trade_sim.buy(self.game, cid, units)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _sell(self, cid: str, units: int) -> None:
        res = trade_sim.sell(self.game, cid, units)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if res["logged"]:
            self.win.toast("They took it. They also logged who sold it.",
                           "osteo")
        self.win.refresh()

    # ── contracts ──────────────────────────────────────────────────────────

    def _contracts(self, sysm) -> None:
        g = self.game
        # A board is generated once per port and keeps until it is worked out.
        key = str(sysm.id)
        if key not in g.boards:
            g.boards[key] = contract_sim.generate(g.rng("board"), g, sysm)
        board = [c for c in g.boards[key]
                 if not c.accepted and c.deadline > g.day]
        g.boards[key] = board

        rumours = rumours_panel.board(self, g, sysm)
        if rumours is not None:
            self.col.addWidget(rumours)
        office = rumours_panel.surveys(self, g, sysm)
        if office is not None:
            self.col.addWidget(office)

        commissions = commissions_panel.held_panel(self, g)
        if commissions is not None:
            self.col.addWidget(commissions)
        offers = commissions_panel.offers_panel(self, g, sysm)
        if offers is not None:
            self.col.addWidget(offers)

        mine = contract_sim.active(g)
        self.col.addWidget(note(
            f"{len(mine)} of {contract_sim.MAX_ACTIVE} contracts in hand. Nothing "
            "here is required — the endings are open whether you take work or "
            "not — but standing is worth more than the fee."))

        if mine:
            held = Panel("In hand")
            for c in mine:
                d = c.definition
                left = c.days_left(g.day)
                held.add(spacer(3))
                held.add(label(c.title, "h3", d.tint))
                bits = [f"{d.name} · {FACTIONS_BY_ID[c.issuer].short}",
                        f"{cr(c.reward)}", f"{left} day(s) left"]
                if c.amount > 1 and c.kind in ("survey", "bounty"):
                    bits.append(f"{int(c.progress)}/{int(c.amount)} done")
                held.add(note(" · ".join(bits)))
                if left < 30:
                    held.add(label("Running out of time.", "", "warn"))
                held.add_buttons(button("Abandon it",
                                        lambda _=False, x=c: self._abandon(x),
                                        kind="danger"))
            self.col.addWidget(held)

        if not board:
            self.col.addWidget(Panel("The board is empty").add(
                note("Nothing posted here at the moment. Boards refresh as the "
                     "postings expire.")))
            return

        cards = []
        for c in board:
            d = c.definition
            card = Card(selectable=False)
            card.add(label(c.title, "h3", d.tint))
            card.add(Pill(d.name, d.tint))
            card.add(label(c.posting, "", wrap=True))
            card.add(note(f"{cr(c.reward)} · {c.days_left(g.day)} days · "
                          f"standing +{c.rep}"))
            # What the cargo costs, and what is left. A fee on its own hid a
            # board that was half traps.
            money = contract_sim.quote(g, c)
            if money is not None:
                card.add(label(
                    f"Cargo costs about {cr(money['cost'])} here"
                    + (f" ({money['held']:g} t already aboard)"
                       if money["held"] else "")
                    + f" — clears {cr(money['net'])}",
                    "", "chloro" if money["net"] > 0 else "warn", wrap=True))
            # Whose enemies mind, before you commit rather than after.
            said, tint = allegiance.note(g, c.issuer, c.rep)
            card.add(label(said, "", tint))
            card.add(button("Take it", lambda _=False, x=c: self._accept(x),
                            kind="primary"))
            cards.append(card)
        self.col.addWidget(label("Posted", "h3"))
        self.grid(cards, cols=2)

    def _accept(self, contract) -> None:
        ok, why = contract_sim.accept(self.game, contract)
        if not ok:
            self.win.toast(why, "warn")
            return
        self.game.add_log(f"Contract taken: {contract.title}.", "good")
        self.win.refresh()

    def _abandon(self, contract) -> None:
        if not self.win.confirm("Abandon the contract",
                                f"{contract.title}. Walking away costs standing "
                                "with the issuer."):
            return
        contract_sim.abandon(self.game, contract)
        self.win.refresh()

    # ── services ───────────────────────────────────────────────────────────

    def take_rumour(self, rumour, paid: bool) -> None:
        g = self.game
        kind = rumour.definition
        res = services_sim.buy_rumour(g, rumour, paid,
                                      g.rng(f"listen-{rumour.id}"))
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def sell_survey(self, system_id: int) -> None:
        g = self.game
        res = intel_sim.sell_survey(g, g.galaxy.systems[system_id],
                                    g.system.port.faction if g.system.port else None)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _services(self, sys, fac, rep) -> None:
        g = self.game
        st = g.ship_stats
        damage = sum(l.max - l.hp for l in g.ship.layers)
        repair_cost = round(damage * (26 if st.family == "fabricated" else 15))

        dock = Panel("Drydock")
        dock.add(label(f"Hull integrity {pct(hull_pct(g.ship))}. " + (
            "A grown hull will close this on its own, given weeks and biomass. "
            "Paying for it is faster." if st.regen > 0 else
            "A fabricated hull will not close this on its own. Somebody has to be "
            "holding the torch."), "", wrap=True))
        dock.add_buttons(
            button("No damage" if damage < 1 else f"Full repair — {cr(repair_cost)}",
                   lambda: self._repair(repair_cost), kind="primary",
                   enabled=damage >= 1 and g.credits >= repair_cost),
            button(f"Clear {len(g.ship.disabled)} fault(s)", self._clear_faults)
            if g.ship.disabled else None)

        vp = buy_price(sys.market, "volatiles", rep, st.trade) or 40
        bunker = Panel("Bunkering")
        bunker.add(label("Reaction mass is volatiles. Every jump burns roughly a "
                         "tonne per light-year.", "", wrap=True))
        bunker.add(note(f"Aboard: {round(g.ship.cargo.get('volatiles', 0))} t."))
        bunker.add_buttons(button(f"Take on 40 t — ~{cr(vp * 40)}",
                                  lambda: self._buy("volatiles", 40)))

        data_held = g.ship.cargo.get("survey", 0)
        office = Panel("Survey Office")
        office.add(label(f"{fac.short if fac else 'The port'} buys charted orbits, ore "
                         "grades and spectra. Selling them here raises your standing "
                         "as well as your balance.", "", wrap=True))
        office.add(note(f"{round(data_held)} data set(s) aboard."))
        office.add_buttons(button("Sell all survey data", self._sell_data,
                                  kind="primary", enabled=data_held >= 1))

        rep_panel = Panel("Standing")
        rep_panel.add(label(fac.doctrine if fac else
                            "This port answers to nobody in particular.", "", wrap=True))
        for fid, value in g.rep.items():
            f = FACTIONS_BY_ID.get(fid)
            if not f or f.hidden:
                continue
            band, tint = standing(value)
            rep_panel.add_row(f.short, f"{band} · {round(value)}", tint)

        self.row(dock, bunker)
        self.row(office, rep_panel)

        target = xeno_sim.best_unfinished(g)
        if target is not None and xeno_sim.is_known(g, target.id):
            price = xeno_notes_price(g, target)
            notes = Panel("Xenology Desk")
            notes.add(label(
                f"Somebody has already dug at a {target.culture.replace('_', ' ')} "
                "site and written it up. Field notes are legal, expensive, and "
                "save you a season in a trench.", "", wrap=True))
            notes.add_row("On offer", target.name)
            notes.add_row("Understood so far", pct(xeno_sim.progress(g, target.id)))
            notes.add_buttons(button(f"Buy the notes — {cr(price)}",
                                     lambda t=target.id: self._buy_notes(t),
                                     kind="primary", enabled=g.credits >= price))
            self.col.addWidget(notes)

        if "research" in sys.port.services:
            lib = Panel("Fleet Library")
            lib.add(label("A hub keeps a copy of the canon. Two weeks reading it is "
                          "worth as much as a month of your own instruments.", "",
                          wrap=True))
            lib.add_buttons(button(f"Study for a fortnight — {cr(4000)}",
                                   self._study, enabled=g.credits >= 4000))
            self.col.addWidget(lib)

    def _buy_notes(self, tech_id: str) -> None:
        res = buy_field_notes(self.game, tech_id)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        tech = res["tech"]
        lines = [f"{round(res['points'])} points of understanding toward "
                 f"{tech.name}, for {cr(res['price'])}."]
        if res["incorporated"]:
            lines.append(f"{tech.name} is now yours. {tech.grants}")
        self.win.dialog("Field notes", lines, [("Log it", None)])
        self.win.refresh()

    def _repair(self, cost: int) -> None:
        res = services_sim.repair(self.game, cost)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _clear_faults(self) -> None:
        services_sim.clear_faults(self.game)
        self.win.toast("Systems restored.", "chloro")
        self.win.refresh()

    def _sell_data(self) -> None:
        res = trade_sim.sell_survey_data(self.game)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _study(self) -> None:
        res = services_sim.commission_study(self.game)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if self.win.check_ending():
            return
        self.win.toast(f"{res['points']} points banked.", "chloro")
        self.win.refresh()

    # ── berths ─────────────────────────────────────────────────────────────

    def take_commission(self, chain_id: str) -> None:
        res = chain_sim.begin(self.game, chain_id, self.game.system)
        if not res.get("ok"):
            self.win.toast(res["why"], "warn")
            return
        chain = res["chain"]
        self.win.dialog(chain.name,
                        [note(chain.premise),
                         note(f"First: {res['contract'].title}")],
                        [("Understood", None)])
        self.win.refresh()

