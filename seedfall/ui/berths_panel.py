"""The berths tab: who is on your bridge, how they feel, and who is hiring.

Kept apart from the rest of the port because a crew is not a commodity — this
is where loyalty, convictions and the two things that mend them live.
"""

from __future__ import annotations

from ..sim import crew as crew_sim
from ..sim import lifespan as lifespan_sim

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..core.util import credits as cr
from ..sim import loyalty as loyalty_sim
from ..sim.crew import daily_wages, recruit_pool
from .widgets import (Card, Panel, Pill, button, label, mono_label, note,
                      spacer)


class BerthsMixin:
    """Provides the berths tab. Mixed into :class:`PortView`."""

    def _berths(self, sys) -> None:
        g = self.game
        if self._pool is None or self._pool_system != sys.id:
            self._pool = recruit_pool(g.rng("recruit"), sys.port.level)
            self._pool_system = sys.id

        self.col.addWidget(note(
            f"Bridge wages run {cr(round(daily_wages(g.officers)))} a day. Six roles; "
            "you may keep as many as you can pay."))

        self.col.addWidget(self._mess_deck(g))

        bridge = Panel("Your bridge")
        if g.officers:
            for o in list(g.officers):
                w = QWidget()
                from PyQt6.QtWidgets import QHBoxLayout
                h = QHBoxLayout(w)
                h.setContentsMargins(0, 2, 0, 2)
                text = f"{o.name} — {o.role_name}"
                if o.trait_name:
                    text += f" · {o.trait_name}"
                h.addWidget(label(text))
                h.addStretch(1)
                mood, tint = loyalty_sim.band(o)
                h.addWidget(Pill(mood, tint))
                h.addWidget(Pill(f"level {o.level}", "lumen"))
                h.addWidget(button("Pay off", lambda _=False, off=o: self._dismiss(off)))
                bridge.add(w)
                conviction = loyalty_sim.conviction_of(o)
                if conviction is not None:
                    bridge.add(note(f"{conviction.name}. {conviction.blurb}"))
            bridge.add(spacer(4), mono_label("Keeping them"))
            bonus = self._bonus_cost()
            bridge.add(note("A bonus buys goodwill outright. Shore leave costs "
                            "you a week and buys more of it — and the ship goes "
                            "nowhere while they take it."))
            bridge.add_buttons(
                button(f"Pay a bonus — {cr(bonus)}",
                       lambda: self._bonus(), kind="primary",
                       enabled=g.credits >= bonus),
                button("Grant shore leave — 7 days", lambda: self._shore_leave()))
        else:
            bridge.add(note("Nobody on the bridge but you."))
        self.col.addWidget(bridge)

        cards = []
        for o in self._pool:
            card = Card(selectable=False)
            card.add(label(o.name, "h3"))
            card.add(label(o.role_name, "sub"))
            text = o.note + (f" · {o.trait_name}: {o.trait_note}" if o.trait_name else "")
            card.add(label(text, "", wrap=True))
            conviction = loyalty_sim.conviction_of(o)
            if conviction is not None:
                card.add(label(conviction.name, "", "lumen"))
                card.add(note(conviction.blurb))
            card.add(note(f"level {o.level} · {cr(o.wage)}/month"))
            card.add(button("Sign on", lambda _=False, who=o: self._hire(who),
                            kind="primary"))
            cards.append(card)
        if cards:
            self.col.addWidget(label("Looking for a berth", "h3"))
            self.grid(cards, cols=3)

    def _hire(self, officer) -> None:
        res = crew_sim.hire(self.game, officer)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self._pool = [o for o in self._pool if o is not officer]
        self.win.refresh()

    def _bonus_cost(self) -> int:
        return crew_sim.bonus_cost(self.game.officers)

    def _bonus(self) -> None:
        res = crew_sim.pay_bonus(self.game)
        if not res["ok"]:
            self.win.toast(res["why"], "warn")
            return
        self.win.refresh()

    def _shore_leave(self) -> None:
        g = self.game
        loyalty_sim.record(g, "shore_leave")
        g.advance_days(7)
        g.add_log("Seven days alongside. The bridge came back better company.",
                  "good")
        if self.win.check_ending():
            return
        self.win.refresh()

    def _dismiss(self, officer) -> None:
        self.game.officers = [o for o in self.game.officers if o is not officer]
        self.win.refresh()

    # ── the hands ──────────────────────────────────────────────────────────

    def _mess_deck(self, g):
        """The headcount, its age, and taking more on.

        The hands could only ever be lost — to fighting, to hunger, to a sleep
        somebody did not come up from — and there was no way to sign anybody
        on at all. They also never got older, so a twenty-year chronicle
        retired the bridge and left the lower decks untouched.
        """
        read = lifespan_sim.crew_profile(g)
        room = lifespan_sim.berths_free(g)
        panel = Panel("The mess deck")
        panel.add(label(lifespan_sim.crew_note(g), "",
                        "warn" if read["over"] > 0.1 else "", wrap=True))
        panel.add_row("Berths free", str(room))
        panel.add_row("Signing fee", cr(lifespan_sim.SIGNING_FEE) + " a head")

        for count in (5, 20):
            take = min(count, room)
            ok, why = lifespan_sim.can_sign_on(g, take) if take else \
                (False, "Every berth aboard is filled.")
            panel.add_buttons(button(
                f"Sign on {take} — {cr(lifespan_sim.SIGNING_FEE * take)}"
                if take else "No berths free",
                lambda n=take: self._sign_on(n),
                kind="primary" if ok and count == 5 else "",
                enabled=ok, tip=why))
            if not ok and why:
                panel.add(note(why))
                break
        return panel

    def _sign_on(self, count: int) -> None:
        res = lifespan_sim.sign_on(self.game, count)
        if not res.get("ok"):
            self.win.toast(res.get("why", "No."), "warn")
            return
        self.win.toast(f"{res['count']} signed on. The mess deck is younger "
                       f"by {res['mean']:.0f} on average.", "")
        self.win.save()
        self.refresh()
