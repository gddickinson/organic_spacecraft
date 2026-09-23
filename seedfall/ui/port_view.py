"""A port: the market, the services counter, and whoever is looking for a berth."""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import pct
from ..data.commodities import BY_ID
from ..data.factions import FACTIONS_BY_ID, standing
from ..sim import chains as chain_sim
from ..sim import services as services_sim
from ..sim import officials as officials_sim
from ..sim import trade as trade_sim
from ..sim import customs as customs_sim
from . import blackmarket_panel
from . import board_panel
from . import freight_panel
from . import kith_panel
from . import register_panel
from ..sim import intel as intel_sim
from ..sim import market as market_sim
from ..sim import wharfage as wharfage_sim
from .berths_panel import BerthsMixin
from ..sim.fieldwork import buy_field_notes, xeno_notes_price
from ..sim import xeno as xeno_sim
from ..sim import commitments as commitments_sim
from ..sim.ship import cargo_used, hull_pct
from ..world.economy import demands
from .market_grid import MarketGrid
from .widgets import Panel, TabBar, View, button, label, note


class PortView(BerthsMixin, View):
    def __init__(self, win):
        super().__init__(win)
        self.tab = "market"
        self._pool = None
        self._board = None

    def keep(self) -> tuple:
        """The price board, changed in place (`ui/market_grid.py`), while the
        market tab is up at the port it was made for."""
        board = self._board
        if (board is not None and self.tab == "market"
                and board.system_id == self.game.location_id):
            return (board,)
        return ()

    def build(self) -> None:
        g = self.game
        sys = g.system
        if not sys.port:
            self.head("No port here", "Nothing in this system will sell you anything.")
            self.buttons(button("Back to system", lambda: self.win.go("system")))
            return
        if kith_panel.hosts(sys):          # a Kith gathering has no market
            kith_panel.build(self, sys)
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
                       ("concourse", "Concourse"), ("desk", "The desk")],
                      self.tab)
        tabs.changed.connect(self._switch)
        self.col.addWidget(tabs)

        if self.tab == "concourse":
            from . import concourse_panel
            concourse_panel.build(self)
            return
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

        # And where you are dealing *from* (`sim/quayside`): alongside the
        # cranes are theirs, and from out in the system the goods are
        # lightered at a rate that rises with the distance. Named on the
        # board for the same reason the due is — it is charged at the till.
        from ..sim import quayside as quayside_sim
        standing = quayside_sim.quote(g, sys)
        self.col.addWidget(label(
            standing["line"], "", "chloro" if standing["alongside"] else
            "warn", wrap=True))
        if not standing["alongside"]:
            # **And only when there is a harbourmaster within reach.** The
            # button was lit from anywhere in the system and answered "not
            # in this orbit: fly there first", which is a door with a wall
            # behind it. `sim/crossing.ways` already knows.
            way = self._alongside_way(g)
            self.col.addWidget(button(
                "Let the harbourmaster bring you in", self._come_alongside,
                kind="primary", enabled=way is None or way.ok,
                tip="An hour, and the counter's cranes are yours for "
                    "nothing.",
                why=(way.why if way is not None and not way.ok
                     else "Nobody there to bring you in.")))

        news = register_panel.local_news(g, sys)
        if news is not None:
            self.col.addWidget(news)

        board = self._board
        if board is None or board.system_id != sys.id:
            board = self._board = MarketGrid(self, sys.id)
        self.col.addWidget(board)
        board.show()
        board.sync(g, sys)
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

    def _alongside_way(self, game):
        """The harbourmaster's own way across, or None if there is no port."""
        from ..sim import crossing, places
        place = places.by_id(game, f"port-{game.location_id}")
        if place is None:
            return None
        return next((w for w in crossing.ways(game, place)
                     if w.id == "dock"), None)

    def _come_alongside(self) -> None:
        """The harbourmaster's own door (`sim/crossing`), from the board."""
        from ..sim import crossing, places
        g = self.game
        place = places.by_id(g, f"port-{g.location_id}")
        got = (crossing.cross(g, place, "dock") if place is not None
               else {"ok": False, "why": "Nobody there to bring you in."})
        self.win.toast(got.get("text") or got.get("why", ""),
                       "good" if got.get("ok") else "warn")
        self.win.refresh()
        self.refresh()

    def _sell(self, cid: str, units: int) -> None:
        res = trade_sim.sell(self.game, cid, units)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        if res["logged"]:
            self.win.toast("They took it. They also logged who sold it.",
                           "osteo")
        elif res["due"] or res.get("lighter"):
            lightered = (f" and {cr(res['lighter'])} lighterage"
                         if res.get("lighter") else "")
            self.win.toast(f"{cr(res['took'])} over the counter, less "
                           f"{cr(res['due'])} wharfage{lightered} — "
                           f"{cr(res['net'])} clear.", "osteo")
        self.win.save()
        self.win.refresh()

    # ── contracts ──────────────────────────────────────────────────────────

    def _contracts(self, sysm) -> None:
        board_panel.build(self, sysm)

    def _accept(self, contract) -> None:
        res = commitments_sim.take_contract(self.game, contract)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _abandon(self, contract) -> None:
        if not self.win.confirm("Abandon the contract",
                                f"{contract.title}. Walking away costs standing "
                                "with the issuer."):
            return
        res = commitments_sim.abandon_contract(self.game, contract)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    # ── services ───────────────────────────────────────────────────────────

    def take_rumour(self, rumour, paid: bool) -> None:
        res = services_sim.buy_rumour(self.game, rumour, paid)
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
        # The drydock's price, from the drydock — `services.repair_quote`.
        quote = services_sim.repair_quote(g)
        damage, repair_cost = quote["damage"], quote["cost"]

        dock = Panel("Drydock")
        dock.add(label(f"Hull integrity {pct(hull_pct(g.ship))}. " + (
            "A grown hull will close this on its own, given weeks and biomass. "
            "Paying for it is faster." if st.regen > 0 else
            "A fabricated hull will not close this on its own. Somebody has to be "
            "holding the torch."), "", wrap=True))
        dock.add_buttons(
            button("No damage" if damage < 1 else f"Full repair — {cr(repair_cost)}",
                   self._repair, kind="primary",
                   enabled=damage >= 1 and g.credits >= repair_cost,
                   tip="Close every wound in the hull now, at the drydock's price.",
                   why=("The hull is whole." if damage < 1 else
                        f"You have {cr(g.credits)} of the {cr(repair_cost)} it "
                        "costs.")),
            button(f"Clear {len(g.ship.disabled)} fault(s)", self._clear_faults,
                   tip="Put every disabled system back in service.")
            if g.ship.disabled else None)

        # The counter's own quote — the market grid twenty lines up was
        # switched to `quote_buy` and pinned; this button was missed.
        vp = market_sim.quote_buy(self.game, sys, "volatiles") or 40
        bunker = Panel("Bunkering")
        bunker.add(label("Reaction mass is volatiles. Every jump burns roughly a "
                         "tonne per light-year.", "", wrap=True))
        bunker.add(note(f"Aboard: {round(g.ship.cargo.get('volatiles', 0))} t."))
        # The till's own gate (`trade.can_buy`) — it was lit with an empty
        # purse and answered "not enough credits".
        from ..sim import trade as trade_sim
        fuel_ok, fuel_why = trade_sim.can_buy(g, "volatiles")
        bunker.add_buttons(button(f"Take on 40 t — ~{cr(vp * 40)}",
                                  lambda: self._buy("volatiles", 40),
                                  enabled=fuel_ok, why=fuel_why,
                                  tip="Buy forty tonnes of volatiles over the "
                                      "counter, at the market's price."))

        data_held = g.ship.cargo.get("survey", 0)
        office = Panel("Survey Office")
        office.add(label(f"{fac.short if fac else 'The port'} buys charted orbits, ore "
                         "grades and spectra. Selling them here raises your standing "
                         "as well as your balance.", "", wrap=True))
        office.add(note(f"{round(data_held)} data set(s) aboard."))
        # **And somewhere to sell it from** (`sim/quayside`): a counter is a
        # place, and this button was lit in deep space, where pressing it
        # answered "nobody is at the counter — come alongside".
        from ..sim import quayside as quayside_sim
        at_hand, off_why = quayside_sim.at_counter(g, sys)
        office.add_buttons(button("Sell all survey data", self._sell_data,
                                  kind="primary",
                                  enabled=data_held >= 1 and at_hand,
                                  tip="Every data set aboard, for credits and "
                                      "standing with this port's power.",
                                  why=(off_why if not at_hand else
                                       "No survey data aboard. Survey a "
                                       "system first.")))

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
                                     kind="primary", enabled=g.credits >= price,
                                     why=f"You have {cr(g.credits)} of the "
                                         f"{cr(price)} they want."))
            self.col.addWidget(notes)

        if "research" in sys.port.services:
            lib = Panel("Fleet Library")
            lib.add(label("A hub keeps a copy of the canon. Two weeks reading it is "
                          "worth as much as a month of your own instruments.", "",
                          wrap=True))
            lib.add_buttons(button(f"Study for a fortnight — {cr(4000)}",
                                   self._study, enabled=g.credits >= 4000,
                                   tip="Two weeks alongside, reading. The "
                                       "calendar moves.",
                                   why=f"You have {cr(g.credits)} of the "
                                       f"{cr(4000)} it costs."))
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

    def _repair(self) -> None:
        res = services_sim.repair(self.game)
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

