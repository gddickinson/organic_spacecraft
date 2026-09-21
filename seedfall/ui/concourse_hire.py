"""The hiring board, wherever somebody is standing under one.

Four kinds of door carry the `hire` tag — a hiring hall, a crewing agency, a
factor's rooms and, where the law does not reach, a stone people stand on —
and until now every one of them was a name on a list. A berth board was a
fact about a *quay*, so a habitat of a million people could not offer you a
navigator.

The same act the Port screen's berths tab uses (`sim/crew.hire`), against a
pool drawn for this place rather than for the system's port.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..sim import crew as crew_sim
from ..sim import loyalty as loyalty_sim
from ..sim import shore
from .widgets import Card, Panel, button, label, note


def build(view, place) -> None:
    """Who is looking for a berth here."""
    game = view.game
    doors = shore.selling(game, place, "hire")
    if not doors:
        return
    rows = crew_sim.pool_here(game, place)
    view.col.addWidget(label("Looking for a berth", "h2"))
    view.col.addWidget(note("  ·  ".join(
        f"{v.name} — {v.note}" for v in doors)))
    if not rows:
        view.col.addWidget(Panel("Nobody").add(
            note("The board is up and there is nobody under it this month. "
                 "Boards turn over on the thirtieth.")))
        return
    can, why = view.can_trade(place)
    cards = []
    for officer in rows:
        card = Card(selectable=False)
        card.add(label(officer.name, "h3"))
        card.add(label(officer.role_name, "sub"))
        text = officer.note + (f" · {officer.trait_name}: {officer.trait_note}"
                               if officer.trait_name else "")
        card.add(label(text, "", wrap=True))
        conviction = loyalty_sim.conviction_of(officer)
        if conviction is not None:
            card.add(label(conviction.name, "", "lumen"))
            card.add(note(conviction.blurb))
        card.add(note(f"level {officer.level} · {cr(officer.wage)}/month"))
        # Asked of the same function `hire` asks, so a live button is a
        # button that works — half a board is stations you already hold.
        ok, refusal = crew_sim.can_hire(game, officer)
        if not ok:
            card.add(label(refusal, "", "warn", wrap=True))
        card.add(button("Sign on",
                        lambda _=False, who=officer: _hire(view, who),
                        kind="primary" if ok and can else "",
                        enabled=ok and can, tip=why or refusal))
        cards.append(card)
    view.grid(cards, cols=3)


def _hire(view, officer) -> None:
    got = crew_sim.hire(view.game, officer)
    if not got["ok"]:
        view.win.toast(got["why"], "warn")
        return
    view.win.toast(f"{officer.name} signed on as {officer.role_name}.",
                   "good")
    view.win.save()
    view.win.refresh()
