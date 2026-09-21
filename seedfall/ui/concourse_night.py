"""Board and bed, and the evening: what a crew does when the watch turns.

Two tabs out of one module because they are one act — taking the watch
somewhere and paying for it — with the doors sorted by what time of day they
matter. `board` is eating and sleeping; `evening` is everything else,
including the half of a concourse that does not put a sign up.

Every night out is `sim/shore.ashore`, which is where the draw for a rumour
happens: a screen may not move the chronicle's luck, and a night ashore is
an act that can turn up a name.
"""

from __future__ import annotations

from ..data import venues as venue_table
from ..sim import lifepath as life_sim
from ..sim import shore
from .widgets import Panel, label, note, button

#: Which doors belong to which tab.
BOARD_KINDS = ("eatery", "lodging")
EVENING_KINDS = ("entertainment", "arts", "sport", "temple", "vice")


def board(view, place) -> None:
    """Eating and sleeping."""
    view.col.addWidget(note(
        "A crew that eats aboard and sleeps in its own berth for a year is "
        "a crew that stops talking to each other. Everything here costs "
        "money and buys something that is not money."))
    _kinds(view, place, BOARD_KINDS)


def evening(view, place) -> None:
    """Everything else, including what nobody advertises."""
    view.col.addWidget(note(
        "What the watch does with a night. The last panel is the other "
        "concourse: it is only ever open where the law does not reach, and "
        "what it sells is on the Clinic tab."))
    _kinds(view, place, EVENING_KINDS)


def _kinds(view, place, kinds) -> None:
    game = view.game
    shown = 0
    for kind in kinds:
        rows = shore.open_here(game, place, kind)
        if not rows:
            continue
        shown += len(rows)
        view.col.addWidget(label(venue_table.KIND_NAME[kind], "h2"))
        view.col.addWidget(note(venue_table.KIND_NOTE[kind]))
        # A grid, not a row. `WrapRow` is one row that goes across or down,
        # so eight doors side by side squeezed every one of them to nothing
        # and the whole panel rendered blank.
        view.grid([_venue(view, place, v) for v in rows], cols=3)
    if not shown:
        view.col.addWidget(note(
            "Nowhere here does any of this. A place this small is a berth, "
            "a counter and whoever happens to be on shift."))


def _venue(view, place, venue) -> Panel:
    """One door, what it would cost, and the button that opens it."""
    game = view.game
    p = Panel(venue.name, "warn" if venue.kind == "vice" else "")
    p.add(note(venue.note))
    if venue.favours:
        level, who = life_sim.skill_aboard(game, venue.favours)
        if who is not None:
            p.add(label(
                f"{who.name} has {venue.favours.replace('_', ' ').title()} "
                f"{level} — they will get more out of it.", "note",
                "chloro", wrap=True))
    if venue.offers:
        p.add(label("Sells: " + ", ".join(
            venue_table.OFFER_NAME[o] for o in venue.offers
            if o in venue_table.OFFER_NAME), "note", "dim", wrap=True))
    if venue.cr <= 0:
        p.add(note("Nothing to pay at the door. Whatever it costs is on "
                   "another tab."))
        return p
    p.add(label(shore.ashore_note(game, place, venue), "note",
                wrap=True))
    if venue.loyalty < 0:
        p.add(label("They will come back worse. Everybody knows it and they "
                    "go anyway.", "note", "warn", wrap=True))
    can, why = view.can_trade(place)
    p.add(button("Take the watch",
                 lambda _=False, v=venue.id: _ashore(view, place, v),
                 kind="primary", enabled=can, tip=why))
    return p


def _ashore(view, place, venue_id: str) -> None:
    got = shore.ashore(view.game, place, venue_id)
    if not got["ok"]:
        view.win.toast(got["why"], "warn")
        return
    said = f"{got['cr']:,} credits ashore."
    if got.get("heard"):
        said += f"  {got['heard']}"
    view.win.toast(said, "good")
    view.win.save()
    view.refresh()
