"""A power's envoy, waiting on an answer.

Diplomacy ran one way — you spent, standing moved — so this screen is the
first time the Verge asks *you* for something. That makes stating the
consequences non-negotiable: every one of the three answers is previewed in
full before it is taken, including the one that costs you nothing to click.

Letting the window lapse is refusing quietly and costs exactly the same, so
the deadline is on the screen in days rather than implied.
"""

from __future__ import annotations

from ..data.factions import FACTIONS_BY_ID
from ..sim import approach as approach_sim
from .widgets import Card, Panel, View, button, label, note


def _short(fid: str | None) -> str:
    got = FACTIONS_BY_ID.get(fid or "")
    return got.short if got else (fid or "them").title()


class EnvoyView(View):
    """Take it, push back, or refuse — with all three costed first."""

    def build(self) -> None:
        g = self.game
        envoy = getattr(g, "envoy", None)
        if envoy is None or envoy.over:
            self.head("Nobody waiting", "The anteroom is empty.")
            self.buttons(button("Back", lambda: self.win.go("diplomacy")))
            return

        action = envoy.action
        power = _short(envoy.faction)
        left = max(0, envoy.expires - g.day)
        self.head(f"{power} — {action.name}",
                  f"They want an answer inside {left} day"
                  f"{'' if left == 1 else 's'}.")

        said = Panel("What they say")
        said.add(label(approach_sim.opening(g, envoy), "", wrap=True))
        said.add(label(approach_sim.asking(g, envoy), "", "chloro", wrap=True))
        said.add(note(action.gives))
        if envoy.log:
            for line in envoy.log:
                said.add(note(line))

        answers = Panel("Your answer")
        for choice, title in (("accept", "Take it"),
                              ("push", "Push for better"),
                              ("refuse", "Refuse")):
            plan = approach_sim.preview(g, envoy, choice)
            if not plan:
                continue
            card = Card(selectable=False)
            card.add(label(title, "h3",
                           "chloro" if choice == "accept" else
                           "warn" if choice == "refuse" else ""))
            for line in plan["lines"]:
                card.add(label(line, "", "", wrap=True))
            # `Card` holds widgets, not rows — it has no `add_row`.
            for fid, delta in plan["rep"].items():
                card.add(label(
                    f"Standing with {_short(fid)}: {delta:+.0f}", "",
                    "chloro" if delta > 0 else "warn"))
            if plan["credits"]:
                card.add(label(f"Treasury: {plan['credits']:+,}", "",
                               "chloro" if plan["credits"] > 0 else "warn"))
            # Haggling moves the offer, not the treasury. Printing it as
            # `Treasury: +794` told a captain they had been paid for asking.
            if plan.get("offer"):
                card.add(label(
                    f"What is on the table: {plan['offer']:+,} credits", "",
                    "chloro" if plan["offer"] > 0 else "warn"))
            usable = self._usable(g, envoy, choice)
            card.add(button(title, lambda c=choice: self._answer(c),
                            kind="primary" if choice == "accept" else "",
                            enabled=usable[0], tip=usable[1]))
            if not usable[0]:
                card.add(label(usable[1], "", "warn", wrap=True))
            answers.add(card)

        self.row(said, answers)
        self.buttons(button("Leave it for now",
                            lambda: self.win.go("diplomacy")))

    @staticmethod
    def _usable(g, envoy, choice: str) -> tuple[bool, str]:
        """Whether an answer can be given, and why not when it cannot."""
        if choice == "push":
            if envoy.pushed:
                return False, "You have already pushed once."
            if not envoy.action.haggle:
                return False, "There is nothing to haggle over."
        if choice == "accept":
            if envoy.kind == "levy" and g.credits < envoy.credits:
                return False, (f"You cannot cover {envoy.credits:,} credits.")
            if envoy.kind == "requisition":
                held = g.ship.cargo.get(envoy.goods, 0)
                if held < envoy.amount:
                    return False, (f"You are carrying {held:g} t of "
                                   f"{envoy.goods}; they asked for "
                                   f"{envoy.amount:g}.")
        return True, ""

    def _answer(self, choice: str) -> None:
        g = self.game
        envoy = getattr(g, "envoy", None)
        if envoy is None:
            return
        res = approach_sim.answer(g, envoy, choice)
        if not res.get("ok"):
            self.win.toast(res.get("why", "No."), "warn")
            return
        if res.get("pushed"):
            self.win.toast("They moved.", "")
            self.refresh()
            return
        self.win.save()
        self.win.go("diplomacy")
