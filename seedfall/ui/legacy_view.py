"""The epoch you are living in, the pressure on it, and what wants an answer.

Reaching an ending no longer stops the chronicle. It opens an epoch: the world
is rewritten once, a new clock starts in place of the Bloom, and situations
arrive that have to be answered. This is where you read all of that.

Every answer prints what it will do before you take it, and `sim/legacy.apply`
reads the same dict the card was rendered from, so the two cannot drift.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..core.util import duration
from ..data.factions import FACTIONS_BY_ID
from ..sim import legacy as legacy_sim
from .widgets import Bar, Card, Panel, View, button, label, note, spacer


def _says(effect: dict) -> str:
    """The effect, in the game's own units, under the sentence."""
    parts = []
    if effect.get("pressure"):
        move = effect["pressure"]
        parts.append(f"{'−' if move < 0 else '+'}{abs(move) * 100:.0f} pressure")
    if effect.get("credits"):
        parts.append(cr(effect["credits"]))
    for fid, delta in effect.get("rep", {}).items():
        faction = FACTIONS_BY_ID.get(fid)
        parts.append(f"{faction.short if faction else fid} {delta:+.0f}")
    if effect.get("hull"):
        parts.append(f"hull {effect['hull'] * 100:+.0f}%")
    for key, amount in effect.get("stores", {}).items():
        parts.append(f"{key} {amount:+g} t")
    if effect.get("research"):
        parts.append(f"+{effect['research']:g} research")
    return " · ".join(parts)


class LegacyView(View):
    """What became of the Verge, and what it is asking now."""

    def build(self) -> None:
        g = self.game
        standing = legacy_sim.gauge(g)
        if not standing:
            self.head("No aftermath yet",
                      "The chronicle has not reached an ending.")
            self.buttons(button("Back to the chart",
                                lambda: self.win.go("map")))
            return

        epoch = standing["epoch"]
        self.head(epoch.name, epoch.pressure)

        waiting = legacy_sim.offer(g)
        if waiting:
            self.col.addWidget(self._situation(waiting))
        self.row(self._state(standing), self._history())
        if not waiting:
            self.buttons(button("Back to the chart",
                                lambda: self.win.go("map"), kind="primary"))

    # ── the situation ──────────────────────────────────────────────────────

    def _situation(self, waiting) -> Panel:
        p = Panel(waiting["title"])
        p.add(label(waiting["text"], "", wrap=True))
        p.add(spacer(6))
        for index, answer in enumerate(waiting["answers"]):
            card = Card()
            card.add(label(answer["label"], "h3"))
            card.add(note(answer["says"]))
            detail = _says(answer["effect"])
            if detail:
                card.add(label(detail, "", "dim", wrap=True))
            card.add(button("Answer", lambda i=index: self._answer(i),
                            kind="primary"))
            p.add(card)
        return p

    def _answer(self, index: int) -> None:
        result = legacy_sim.answer(self.game, index)
        if not result.get("ok"):
            self.win.toast(result.get("why", "No."), "warn")
            return
        self.win.save()
        self.refresh()

    # ── the readout ────────────────────────────────────────────────────────

    def _state(self, standing) -> Panel:
        epoch = standing["epoch"]
        p = Panel("Where it stands")
        p.add(note(epoch.opening))
        p.add(spacer(4))
        p.add_row(standing["gauge"], f"{standing['pressure'] * 100:.0f}%",
                  "warn" if standing["pressure"] > 0.65 else "")
        p.add(Bar(standing["pressure"],
                  "warn" if standing["pressure"] > 0.65 else "osteo"))
        p.add(note(f"At a hundred: {epoch.failure}"))
        p.add(spacer(4))
        p.add_row("Held for", duration(standing["days"]))
        p.add_row("Still to hold", duration(standing["left"]))
        p.add(note(f"Hold it that long: {epoch.triumph}"))
        if standing["over"]:
            p.add(spacer(4))
            p.add(label(
                epoch.triumph if standing["outcome"] == "triumph"
                else epoch.failure, "",
                "chloro" if standing["outcome"] == "triumph" else "warn",
                wrap=True))
        return p

    def _history(self) -> Panel:
        p = Panel("This chronicle")
        p.add(self.hint("An ending is a turn in the sector's history, not a "
                        "stop. Every one this chronicle has taken is here."))
        for epoch, outcome, day in legacy_sim.summary(self.game):
            p.add_row(epoch.name,
                      {"triumph": "held", "failure": "lost",
                       "under way": "under way"}.get(outcome, outcome),
                      tint={"triumph": "chloro", "failure": "warn"}.get(outcome))
        return p
