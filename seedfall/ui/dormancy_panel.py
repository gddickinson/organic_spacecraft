"""Putting the crew under: what it saves, what it costs, who might not wake.

The time system priced a crossing in people and gave one answer — fly harder,
and pay in reaction mass. This is the other answer, and it is the one that can
fail to give somebody back, so every figure is on the screen before the
decision: the ageing saved, the rations saved, the medium consumed, the odds
against each sleeper, and what the hull drops to while the watch is short.

The odds are quoted two ways on purpose. A percentage is comparable between
methods; a headcount is what it actually means. "2.4% a head" and "0.7 of 30
people, on average" are the same number, and only one of them is a decision.
"""

from __future__ import annotations

from ..sim import dormancy as dormancy_sim
from .widgets import Card, Panel, button, label, note


def who_sleeps(view, g, days: int = 400):
    """Every way of putting the crew under, costed for a crossing of `days`."""
    panel = Panel("The long sleep")
    panel.add(view.hint(dormancy_sim.note(g)))

    under = dormancy_sim.current(g)
    if under is not None:
        method = under.how
        slept = max(0, g.ship_day - under.since)
        card = Card(selectable=False)
        card.add(label(method.name if method else "Asleep", "h3", "chloro"))
        card.add(note(f"{under.hands} hands and {len(under.officers)} "
                      f"officer(s) have been under {slept} days."))
        if method and method.risk:
            odds = 1.0 - (1.0 - method.risk / 100.0) ** (slept / 100.0)
            card.add(label(
                f"Waking them now: about {odds * 100:.1f}% of them do not "
                "come up.", "", "warn", wrap=True))
        card.add(button("Wake them", view.wake_crew, kind="primary"))
        panel.add(card)
        return panel

    room = dormancy_sim.most_that_can_sleep(g)
    if room <= 0:
        panel.add(note("There are too few aboard to spare anybody. The hull "
                       "still needs a watch."))
        return panel
    panel.add(note(f"At most {room} of {dormancy_sim.complement(g)} may go "
                   "under. Somebody has to stand the watch, and the watch "
                   "ages."))

    for method, ok, why in dormancy_sim.available(g):
        if method.id == "watch":
            continue
        card = Card(selectable=False)
        card.add(label(method.name, "h3", "chloro" if ok else "dim"))
        card.add(note(method.blurb))
        # Only cost a method you could actually use. The figures are computed
        # from *this* crew's lineage, so quoting them under a method only a
        # Dry Choir can use was arithmetic about somebody who is not aboard.
        if ok:
            plan = dormancy_sim.preview(g, method.id, room, days)
            for line in plan.get("lines", []):
                card.add(label(
                    line, "", "warn" if "not come back" in line else "",
                    wrap=True))
        else:
            card.add(note(f"{method.gives} {method.costs}"))
        card.add(button(f"Put {room} under", lambda m=method.id:
                        view.sleep_crew(m, room),
                        kind="primary" if ok else "", enabled=ok, tip=why))
        if not ok:
            card.add(label(why, "", "warn", wrap=True))
        panel.add(card)
    return panel
