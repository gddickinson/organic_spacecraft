"""The berths tab: who is on your bridge, how they feel, and who is hiring.

Kept apart from the rest of the port because a crew is not a commodity — this
is where loyalty, convictions and the two things that mend them live.
"""

from __future__ import annotations

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
        g = self.game
        if any(x.stat == officer.stat for x in g.officers):
            self.win.toast("That station is already crewed. Pay off the incumbent "
                           "first.", "warn")
            return
        if g.credits < officer.wage:
            self.win.toast("Not enough credits for the signing fee.", "warn")
            return
        g.credits -= officer.wage
        g.officers.append(officer)
        self._pool = [o for o in self._pool if o is not officer]
        g.add_log(f"{officer.name} signed on as {officer.role_name}.", "good")
        self.win.refresh()

    def _bonus_cost(self) -> int:
        return int(sum(o.wage for o in self.game.officers) * 0.6)

    def _bonus(self) -> None:
        g = self.game
        cost = self._bonus_cost()
        if g.credits < cost:
            self.win.toast("Not enough in the treasury for that.", "warn")
            return
        g.credits -= cost
        loyalty_sim.record(g, "bonus_paid")
        g.add_log("A bonus went round the bridge.", "good")
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
