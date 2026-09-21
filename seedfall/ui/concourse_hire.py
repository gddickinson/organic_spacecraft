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
from ..data import lineages as lineage_table
from ..sim import kindred as kindred_sim
from ..sim import lifespan as lifespan_sim
from ..sim import loyalty as loyalty_sim
from ..sim import shore
from . import portrait_paint
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
    view.col.addWidget(_admitted(game, place))
    can, why = view.can_trade(place)
    cards = []
    for officer in rows:
        card = Card(selectable=False)
        card.add(portrait_paint.chip(game, officer, 58))
        card.add(label(officer.name, "h3"))
        lineage = lifespan_sim.lineage_of(officer, game)
        card.add(label(f"{officer.role_name} · {lineage.name}", "sub"))
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


def _admitted(game, place) -> Panel:
    """Which substrates this gate will and will not put on its board.

    A board only ever holds people the port would admit, so a captain who
    wants a frame has to know which ports have one — and that is a fact
    about the *power*, not about luck.
    """
    p = Panel("Who they will have here")
    for lineage in lineage_table.LINEAGES:
        got = kindred_sim.standing(game, place, lineage.id)
        tint = {"welcome": "chloro", "licensed": "", "watched": "osteo",
                "refused": "warn"}.get(got["band"], "")
        p.add_row(lineage.name, got["band"], tint)
    p.add(note("What a hull draws is another matter: a fabricated hull "
               "brings frames to its board and a grown one does not."))
    return p


def _hire(view, officer) -> None:
    got = crew_sim.hire(view.game, officer)
    if not got["ok"]:
        view.win.toast(got["why"], "warn")
        return
    view.win.toast(f"{officer.name} signed on as {officer.role_name}.",
                   "good")
    view.win.save()
    view.win.refresh()
