"""A port: the market, the services counter, and whoever is looking for a berth."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QSpinBox, QWidget

from ..core.util import credits as cr
from ..core.util import pct
from ..data.commodities import BY_ID, COMMODITIES
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import chains as chain_sim
from ..sim import services as services_sim
from ..sim import officials as officials_sim
from ..sim import trade as trade_sim
from ..sim import customs as customs_sim
from . import blackmarket_panel
from . import board_panel
from . import freight_panel
from . import register_panel
from ..sim import intel as intel_sim
from ..sim import market as market_sim
from ..sim import wharfage as wharfage_sim
from .berths_panel import BerthsMixin
from ..sim.fieldwork import buy_field_notes, xeno_notes_price
from ..sim import xeno as xeno_sim
from ..sim import contracts as contract_sim
from ..sim.ship import cargo_used, hull_pct
from ..world.economy import demands, price_note
from .widgets import (Panel, Pill, TabBar, View, button, label,
                      mono_label, note)


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

        # **Before you sell, not after.** A creditor who holds this counter
        # takes its share at the till (`sim/wharfage.collect`), which is the
        # whole reason a judgment cannot be ignored — so the board has to say
        # so first. A cut taken out of a sale the captain was not warned about
        # is the screen lying by omission.
        from ..sim import debts as debts_sim
        distraint = debts_sim.distraint_note(g, sys)
        if distraint:
            self.col.addWidget(label(distraint, "", "warn", wrap=True))

        # Why the numbers are not the posted ones. The office rate used to be
        # applied at the till, so the board showed one price and the counter
        # charged another; now it is in the quote, and the board says so.
        if officials_sim.pending_once(g, sys, "quiet_price"):
            self.col.addWidget(label(
                "Every price here is the office rate, not the posted one — "
                "somebody at this desk owes you a quiet price. It goes on your "
                "next deal over this counter and no further.", "", "chloro",
                wrap=True))
        elif officials_sim.favour_running(g, sys, "quiet_price"):
            self.col.addWidget(label(
                "These are office rates rather than posted prices.", "",
                "chloro", wrap=True))

        # What the quay takes for being the quay. Named, never silent: the whole
        # point of `sim/wharfage.py` is that the figure the board gives here is
        # the figure the counter charges.
        toll = wharfage_sim.line(g, sys)
        if toll:
            self.col.addWidget(label(
                toll, "", "dim" if wharfage_sim.holder(g, sys) is None
                else "lumen", wrap=True))

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
            # `quote_buy`, not `buy_price`. These two columns were the third
            # door onto a price: the till asks the quote helper, which carries
            # the grudge bias and the office rate, and this grid asked the raw
            # market. Measured with a quiet price in hand — the board said 36
            # and 29, the counter charged 32 and paid 33, and the comment forty
            # lines up claimed the board said so.
            bp = market_sim.quote_buy(g, sys, c.id)
            sp = None if banned else market_sim.quote_sell(g, sys, c.id)
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
        # Trading moves no calendar, so the autosave never fires for it —
        # these three save the way `learn_about` and `ask_favour` already do.
        self.win.save()
        self.win.refresh()

    def _buy(self, cid: str, units: int) -> None:
        res = trade_sim.buy(self.game, cid, units)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if res["due"]:
            self.win.toast(f"{cr(res['paid'])} for the cargo and "
                           f"{cr(res['due'])} to the quay.", "osteo")
        self.win.save()
        self.win.refresh()

    def _sell(self, cid: str, units: int) -> None:
        res = trade_sim.sell(self.game, cid, units)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if res["logged"]:
            self.win.toast("They took it. They also logged who sold it.",
                           "osteo")
        elif res["due"]:
            self.win.toast(f"{cr(res['took'])} over the counter, less "
                           f"{cr(res['due'])} wharfage — {cr(res['net'])} "
                           "clear.", "osteo")
        self.win.save()
        self.win.refresh()

    # ── contracts ──────────────────────────────────────────────────────────

    def _contracts(self, sysm) -> None:
        board_panel.build(self, sysm)

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

        # The counter's own quote — the market grid twenty lines up was
        # switched to `quote_buy` and pinned; this button was missed.
        vp = market_sim.quote_buy(self.game, sys, "volatiles") or 40
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

