"""The Port screen's Concourse tab: what is here, and the way into it.

The concourse outgrew a tab. It was four kinds of door gated on a starport;
it is fifteen kinds gated on a *place* (`sim/places.py`), which means it
works at a habitat drum, a holding of yours and a settlement on the ground as
well as at a quay — and it carries a clinic, a hiring hall, cold berths and
the other concourse besides a chandler and a bar.

So this is the board at the head of the gangway: what is standing here, what
it will cost the watch, and the door through to the whole of it. The Port
screen keeps it because a captain who has just docked looks at the Port
screen, and being told there is a rejuvenation clinic on this station is the
thing that makes them go and find it.
"""

from __future__ import annotations

from ..data import venues as venue_table
from ..sim import clinic as clinic_sim
from ..sim import places as places_sim
from ..sim import shore
from .widgets import Panel, button, label, note

#: How many doors of one kind to name on the board before counting the rest.
NAMED = 4


def build(view) -> None:
    """The whole tab."""
    game = view.game
    place = next((p for p in places_sim.in_system(game, game.system)
                  if p.kind == "port"), None)
    if place is None:
        view.col.addWidget(note("There is no concourse here."))
        return
    for line in places_sim.says(place):
        view.col.addWidget(note(line))
    view.col.addWidget(_summary(view, game, place))
    _board(view, game, place)
    view.buttons(button("Walk the concourse",
                        lambda: view.win.go("concourse"), kind="primary"))


def _summary(view, game, place) -> Panel:
    """The purse and the two things worth knowing before walking down."""
    p = Panel("At the head of the gangway")
    p.add_row("In hand", f"{int(game.credits):,} credits")
    p.add_row("On account", shore.account_line(game))
    owned = shore.owned(game)
    p.add_row("Carried", f"{len(owned)} possession(s)"
              if owned else "nothing of your own")
    shelf = shore.shelves(game, place)
    p.add_row("On the chandler's shelf", f"{len(shelf)} lines"
              if shelf else "nothing")
    care = clinic_sim.offered(game, place)
    p.add_row("The clinic will do", f"{len(care)} sorts of work"
              if care else "nothing at all")
    others = [q for q in places_sim.in_system(game) if q.id != place.id]
    if others:
        p.add(label("Also in this system: " + ", ".join(
            f"{q.name} ({q.kind_name.lower()}, {q.heads:,})"
            for q in others[:4]), "note", "chloro", wrap=True))
    return p


def _board(view, game, place) -> None:
    """Every kind of door here, named."""
    cards = []
    shown = 0
    for kind, name, _about in venue_table.KINDS:
        rows = shore.open_here(game, place, kind)
        if not rows:
            continue
        shown += 1
        p = Panel(name, "warn" if kind == "vice" else "")
        p.add(note("  ·  ".join(v.name for v in rows[:NAMED])
                   + (f"  ·  and {len(rows) - NAMED} more"
                      if len(rows) > NAMED else "")))
        cards.append(p)
    if not shown:
        view.col.addWidget(note("Nothing here but the berth."))
        return
    view.col.addWidget(label("What is open", "h2"))
    view.grid(cards, cols=3)
