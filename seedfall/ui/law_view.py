"""The docket: who has what on you, what it will cost, and the way out.

The screen the governance layer needed and the game had nowhere to put. There
was no court, no warrant, no arrest and no bounty anywhere in it, so there was
also nothing to look at — a captain's entire legal position was a reputation
number that also meant nine other things.

Every figure here comes out of `sim/tribunal.case`, which is the same function
`plead` spends against, so a button cannot promise a price the hearing will
not honour. That rule has caught two real defects in this project already and
it is not going to be relaxed for this screen.

The layout follows what a captain actually needs to decide, in order: **what
is about to happen** (a summons with a day on it), **what is in force right
now** (the instruments — the reason a quay just refused you), **what you owe**,
and only then the history. A file of closed matters is interesting; a hearing
in nine days is urgent, and urgent goes at the top.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..data.factions import FACTIONS_BY_ID
from ..data.forums import forum_of
from ..data.offences import LAWFUL, OFFENCES_BY_ID
from ..sim import clemency as clemency_sim
from ..sim import debts as debts_sim
from ..sim import governance as gov_sim
from ..sim import law as law_sim
from ..sim import tribunal as tribunal_sim
from ..sim import warrants as warrants_sim
from .widgets import Panel, View, button, label, note, spacer


def _short(power: str) -> str:
    who = FACTIONS_BY_ID.get(power)
    return who.short if who else power


class LawView(View):
    """Everything the powers have on you, and everything you can do about it."""

    def build(self) -> None:
        g = self.game
        trouble = gov_sim.trouble(g)
        self.head("The law",
                  "There is no law of the Verge. There are four powers, each "
                  "with its own, and each only as long as its own reach.")

        if not gov_sim.any_business(g):
            self.col.addWidget(Panel("Nothing outstanding").add(
                "No power has anything on your file. That is not the same as "
                "being innocent — most of what a captain does is simply never "
                "witnessed by anybody who would call it a crime.",
                note("An act is only charged where a power has a quay, a "
                     "register or hulls to see it with — or a friend who "
                     "does.")))
            self.buttons(button("Back to the chart",
                                lambda: self.win.go("map")))
            return

        self.col.addWidget(label(
            f"Exposure across the sector: {trouble:.2f}", "sub"))

        waiting = tribunal_sim.summons(g)
        if waiting:
            for charge in waiting[:3]:
                self.col.addWidget(self._summons(charge))

        live = warrants_sim.summary(g)
        if live:
            self.col.addWidget(self._instruments(live))

        owing = debts_sim.live(g)
        if owing:
            self.col.addWidget(self._debts(owing))

        self.row(*[self._power(p) for p in LAWFUL
                   if gov_sim.standing_with(g, p)["open"]
                   or warrants_sim.in_force(g, p)][:2] or [spacer()])
        self.col.addWidget(self._history())
        self.buttons(button("Back to the chart", lambda: self.win.go("map")))

    # ── what is about to happen ────────────────────────────────────────────

    def _summons(self, charge) -> Panel:
        g = self.game
        quote = tribunal_sim.case(g, charge)
        if not quote["ok"]:
            return Panel("A matter").add(quote.get("why", ""))
        days = max(0, int(charge.due - g.day))
        panel = Panel(f"{quote['who']} — {quote['offence']}", "warn")
        panel.add(label(f"{quote['forum']}", "sub"))
        panel.add(f"Charged with {quote['writ']}. {quote['detail'] or ''}")
        panel.add_row("Where", charge.where or "—")
        if charge.filed_on >= 0:
            panel.add_row("Filed", f"day {charge.filed_on:.0f}, "
                                   f"{max(0, int(g.day - charge.filed_on))} "
                                   "day(s) ago")
        panel.add_row("Decided in", f"{days} day(s)")
        panel.add_row("At stake", cr(quote["stake"]))
        panel.add_row("If you never answer", cr(quote["default_cost"]), "warn")
        for name, worth in quote["defence"]["rows"]:
            panel.add_row(name, f"+{worth:.2f}")
        if not quote["pleas"]:
            panel.add(note(quote["absent"] + " There is nothing to answer and "
                                            "nowhere to answer it."))
            return panel
        if charge.state == "answered":
            panel.add(note(f"Your plea is in: {charge.plea}. The "
                           f"{quote['occasion']} decides on the day."))
            return panel
        for plea in quote["pleas"]:
            text = plea["name"]
            if plea["cost"]:
                text += f" — {cr(plea['cost'])}"
            if plea["odds"]:
                text += f" ({plea['odds']:.0%} dismissed)"
            panel.add(button(text, self._plead(charge, plea["id"]),
                             kind="primary" if plea["id"] == "settle" else "",
                             tip=plea["blurb"]))
        return panel

    def _plead(self, charge, plea: str):
        def go():
            out = tribunal_sim.plead(self.game, charge, plea)
            if not out.get("ok"):
                self.win.toast(out.get("why", "Refused."), "warn")
                return
            for kind, text in out.get("lines") or []:
                self.game.add_log(text, kind)
            self.win.toast(out.get("said", ""))
            self.win.refresh()
        return go

    # ── what is in force ───────────────────────────────────────────────────

    def _instruments(self, live: list) -> Panel:
        panel = Panel("In force", "warn")
        for row in live:
            where = {"system": "in one system",
                     "holdings": "anywhere they hold",
                     "everywhere": "everywhere"}.get(row["reach"], row["reach"])
            panel.add_row(f"{row['who']} · {row['name']}",
                          ("HERE — " if row["here"] else "") + where,
                          "bad" if row["here"] else "")
            panel.add(note(f"{row['blurb']} Because {row['why']}."))
            if row["price"]:
                panel.add(button(
                    f"Buy the paper back from {row['who']}",
                    self._buyback(row["power"]),
                    tip="Whoever holds it will sell it back, for rather more "
                        "than they paid for it."))
        return panel

    def _buyback(self, power: str):
        def go():
            out = clemency_sim.settle_bounty(self.game, power)
            if not out.get("ok"):
                self.win.toast(out.get("why", "Refused."), "warn")
                return
            for kind, text in out.get("lines") or []:
                self.game.add_log(text, kind)
            self.win.toast(out["said"])
            self.win.refresh()
        return go

    # ── what you owe ───────────────────────────────────────────────────────

    def _debts(self, owing: list) -> Panel:
        g = self.game
        panel = Panel(f"Owed — {cr(debts_sim.total_owed(g))}")
        for debt in owing:
            late = g.day > debt.due
            panel.add_row(
                f"{_short(debt.holder.split(':')[-1])} · {debt.note or debt.kind}",
                cr(debts_sim.balance(g, debt))
                + (" — past due" if late else ""),
                "bad" if late else "")
            if debt.distrain:
                panel.add(note("They take a share of anything you sell at "
                               "their counters, and they do not ask first."))
            if debt.kind == "bond":
                panel.add(note("This is security against the hull itself. "
                               "Default and the ship is theirs."))
            panel.add(button(f"Pay {cr(debts_sim.balance(g, debt))}",
                             self._pay(debt)))
        return panel

    def _pay(self, debt):
        def go():
            out = debts_sim.pay(self.game, debt)
            self.win.toast(out.get("said") or out.get("why", ""),
                           "" if out.get("ok") else "warn")
            if out.get("ok"):
                for kind, text in clemency_sim.settled_up(self.game):
                    self.game.add_log(text, kind)
            self.win.refresh()
        return go

    # ── who they are ───────────────────────────────────────────────────────

    def _power(self, power: str) -> Panel:
        g = self.game
        state = gov_sim.standing_with(g, power)
        forum = forum_of(power)
        panel = Panel(f"{_short(power)} — {state['forum']}")
        if forum is not None:
            panel.add(note(forum.blurb))
        panel.add_row("On the file", state["note"])
        panel.add_row("Exposure", f"{state['exposure']:.2f}")
        if state["owed"]:
            panel.add_row("Owed", cr(state["owed"]))
        ok, why = clemency_sim.can_pardon(g, getattr(g, "system", None), power)
        price = clemency_sim.pardon_price(g, power)
        if price["exposure"] > 0:
            panel.add(button(
                f"Ask them to lose the file — {cr(price['credits'])}",
                self._pardon(power), enabled=ok,
                tip=why if not ok else
                    f"{why} Nothing is explained and nothing is written down."))
        return panel

    def _pardon(self, power: str):
        def go():
            out = clemency_sim.pardon(self.game, self.game.system, power)
            if not out.get("ok"):
                self.win.toast(out.get("why", "Refused."), "warn")
                return
            for kind, text in out.get("lines") or []:
                self.game.add_log(text, kind)
            self.win.toast(out["said"])
            self.win.refresh()
        return go

    # ── what has already happened ──────────────────────────────────────────

    def _history(self) -> Panel:
        g = self.game
        closed = [c for c in law_sim.charges(g) if c.state == "closed"][:8]
        panel = Panel("The record")
        if not closed:
            panel.add("Nothing has been decided yet.")
            return panel
        for charge in closed:
            offence = OFFENCES_BY_ID.get(charge.offence)
            tint = {"convicted": "bad", "acquitted": "chloro",
                    "settled": "lumen", "pardoned": "lumen",
                    "spent": "dim"}.get(charge.outcome, "")
            panel.add_row(
                f"{_short(charge.power)} · {offence.name if offence else charge.offence}",
                charge.outcome.title(), tint)
            if charge.verdict:
                panel.add(note(charge.verdict))
        return panel
