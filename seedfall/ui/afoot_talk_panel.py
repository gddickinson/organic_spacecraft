"""Talking to somebody on a deck, and the counters they stand behind.

The conversation is the sim's (`afoot_talk.topics`): every topic a button,
with its odds and its price, greyed with the reason when it cannot be
raised. What a topic *hands over to* is somebody else's counter, and it is
drawn here with that counter's own doors:

- **business** at a shelf — `shore.shelves`, `shore.buy`, `shore.sell`;
- **business** anywhere with a bed, a meal or an evening — `shore.ashore`;
- **business** at a clinic, a bank or an office — the Concourse screen's own
  tab for this place, because a surgery is not a thing to buy across a
  counter in a corridor;
- **the board** at a hiring hall — `crew.pool_here` and `crew.hire`;
- **a favour** from a harbourmaster, and **a gift** to the Kith — the Port
  screen's own desk and gathering, which a walk on that quay may open.
"""

from __future__ import annotations

from ..core.util import credits as cr
from ..data import venues as venue_table
from ..sim import afoot_talk, crew, places, shore
from .widgets import Panel, button, label, note

#: What each kind of counter's shelf carries, by kit category.
SHELF = {"chandler": ("weapon", "armour", "suit", "tool", "medical"),
         "market": ("luxury", "travel", "keepsake"),
         "tech": ("comp", "survey"),
         "vice": ("illicit", "weapon", "paper")}
#: The Concourse tab each kind of door's full counter lives on.
TAB_FOR = {"clinic": "clinic", "lodging": "board", "eatery": "board",
           "bank": "shops", "office": "shops", "law": "shops",
           "transport": "shops"}
SHELF_MOST = 10
PER_KIND = 2
SELL_MOST = 6


def conversation(view, walk, who, other) -> Panel:
    """The person, what they last said, and everything that can be raised."""
    p = Panel(f"Talking to {other.name}")
    if other.note and other.incident == "tie":
        p.add(note(other.note))
    for line in view.said[-4:]:
        p.add(label(line, "", wrap=True))
    for topic in afoot_talk.topics(view.game, walk, who, other):
        text = topic.label
        if topic.odds is not None and topic.ok:
            text += f" — {topic.odds:.0%}"
        b = button(text, lambda _=False, t=topic.id: view.say(t),
                   enabled=topic.ok, why=topic.why)
        b.setObjectName(f"afoot_topic_{topic.id}")
        p.add(b)
    leave = button("Walk away", view.stop_talking, kind="flat")
    leave.setObjectName("afoot_walk_away")
    p.add(leave)
    return p


def counter(view, walk, other, what: str):
    """The counter a topic handed over to, drawn with its own doors."""
    game = view.game
    place = places.by_id(game, walk.place_id) if walk.place_id else None
    room = next((r for r in walk.rooms if r.id == other.room), None)
    venue = venue_table.VENUE_BY_ID.get(room.venue) if room else None
    if what == "hire":
        return _board(view, game, place)
    if what in ("favour", "kith"):
        box = Panel("The harbourmaster" if what == "favour" else "The Kith")
        box.add(note("Their desk is the Port screen's: every favour costed "
                     "both ways." if what == "favour" else
                     "The gathering is the Port screen's: the lexicon, the "
                     "gift, and what may be asked."))
        b = button("Go to them", lambda _=False: view.to_port(
            "desk" if what == "favour" else "market"))
        b.setObjectName("afoot_to_port")
        box.add(b)
        return box
    if venue is None or place is None:
        return Panel("Business").add(note("There is nothing here to buy."))
    if venue.kind in SHELF:
        return _shelf(view, game, place, venue)
    return _door(view, game, place, venue)


def _shelf(view, game, place, venue) -> Panel:
    p = Panel(venue.name)
    rows = []
    for category in SHELF[venue.kind]:     # the cheapest of each kind
        rows += [r for r in shore.shelves(game, place, category)][:PER_KIND]
    rows = rows[:SHELF_MOST]
    if not rows:
        p.add(note("The shelves are bare."))
    for row in rows:
        item = row["item"]
        flag = "" if row["legal"] else " (not legal here)"
        b = button(f"{item.name} — {cr(row['cr'])}{flag}",
                   lambda _=False, i=item.id: view.counter_act(
                       shore.buy, place, i),
                   enabled=game.credits >= row["cr"],
                   why="You cannot afford it.")
        b.setObjectName(f"afoot_buy_{item.id}")
        p.add(b)
    mine = shore.owned(game)[:SELL_MOST]
    if mine:
        p.add(label("Sell", "h3"))
        for item in mine:
            b = button(f"Sell {item.name.lower()}",
                       lambda _=False, i=item.id: view.counter_act(
                           shore.sell, place, i))
            b.setObjectName(f"afoot_sell_{item.id}")
            p.add(b)
    return p


def _door(view, game, place, venue) -> Panel:
    p = Panel(venue.name)
    p.add(note(venue.note or venue_table.KIND_NOTE.get(venue.kind, "")))
    if venue.cr > 0:
        cost = shore.ashore_cost(game, venue)
        b = button(f"A night here — {cr(cost)}",
                   lambda _=False, v=venue.id: view.counter_act(
                       shore.ashore, place, v),
                   enabled=game.credits >= cost, why="You cannot afford it.")
        b.setObjectName(f"afoot_night_{venue.id}")
        p.add(b)
        p.add(note(shore.ashore_note(game, place, venue)))
    tab = TAB_FOR.get(venue.kind)
    if tab:
        b = button("The full counter", lambda _=False, t=tab:
                   view.to_concourse(t))
        b.setObjectName("afoot_counter")
        p.add(b)
    return p


def _board(view, game, place) -> Panel:
    p = Panel("The board")
    rows = crew.pool_here(game, place) if place is not None else []
    if not rows:
        p.add(note("Nobody on the board this month."))
    for officer in rows[:5]:
        ok, why = crew.can_hire(game, officer)
        b = button(f"{officer.name}, {officer.role_name} {officer.level} — "
                   f"{cr(officer.wage)}",
                   lambda _=False, o=officer: view.hire(o),
                   enabled=ok, why=why)
        b.setObjectName(f"afoot_hire_{officer.id}")
        p.add(b)
    return p
