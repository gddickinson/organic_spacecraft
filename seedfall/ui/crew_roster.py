"""The Roster tab: the complement, the watch bill, and a card for every hand.

The three things a captain opens a crew list to find out, in the order they
are asked: *how many of us are there and what does that cost*, *which watch
has nobody standing it*, and *who are these people*.

The cards are the third question answered shallowly on purpose — a station, a
mood, a life in one clause and the three things they are best at. Anything
deeper is the Sheet tab, one click away, because a roster that printed a whole
service record per person was a wall nobody could read (which is exactly what
the Ship screen's Crew tab had become).
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..core.util import credits as cr
from ..sim import arcs as arcs_sim
from ..sim import roster as roster_sim
from . import portrait_paint
from .widgets import Card, Panel, Pill, button, label, note


def build(view, said: dict) -> None:
    """The whole tab."""
    g = view.game
    view.row(_complement(g, said), _mood(said), _bill(g, said))
    view.col.addWidget(_watch_bill(view, g))
    _order_bar(view)
    cards = [_card(view, g, o) for o in roster_sim.roll(g, view.order)]
    view.grid(cards, cols=3)


# ── the three panels across the top ────────────────────────────────────────

def _complement(g, said: dict) -> Panel:
    p = Panel("The complement")
    p.add_row("Officers", f"{said['officers']} of 6 stations")
    p.add_row("Hands", f"{said['hands']} · {said['hands_band']}")
    if said["asleep"]:
        p.add_row("Under", f"{said['asleep']} asleep", "lumen")
    p.add_row("Berths free", str(said["berths_free"]),
              "warn" if said["berths_free"] <= 0 else "")
    p.add(note(said["hands_note"]))
    return p


def _mood(said: dict) -> Panel:
    p = Panel("How they are")
    tint = ("warn" if said["loyalty"] < 45 else
            "chloro" if said["loyalty"] >= 65 else "")
    p.add_row("Loyalty", f"{said['loyalty']:.0f} on average", tint)
    p.add_bar(max(0.0, min(1.0, said["loyalty"] / 100.0)),
              tint or "lumen")
    p.add_row("Morale", f"{said['morale']:.0%}",
              "warn" if said["morale"] < 0.35 else "")
    p.add_bar(max(0.0, min(1.0, said["morale"])), "chloro")
    if said["restless"]:
        p.add(label(f"{said['restless']} of them are restless. A restless "
                    "officer works worse and eventually walks.", "note",
                    "warn", wrap=True))
    else:
        p.add(note("Nobody aboard is thinking about leaving."))
    return p


def _bill(g, said: dict) -> Panel:
    p = Panel("What they cost")
    p.add_row("Wages", f"{cr(round(said['wages']))} a day")
    p.add_row("Stores", f"{said['stores']:.2f} t a day")
    p.add_row("Power", f"{said['power']:.1f} kW")
    bill = roster_sim.wage_bill(g)
    p.add_row("Thirty days", cr(round(bill["wages"])))
    days = bill["afford"]
    p.add(label(
        "The treasury covers the wage bill for "
        + ("as long as you like." if days == float("inf")
           else f"{days:,.0f} more days."), "note",
        "warn" if days != float("inf") and days < 60 else "", wrap=True))
    return p


# ── the watch bill ─────────────────────────────────────────────────────────

def _watch_bill(view, g) -> Panel:
    """Six stations, and the holes showing."""
    from .crew_view import empty_note
    rows = roster_sim.stations(g)
    p = Panel("The watch bill")
    for row in rows:
        officer = row["officer"]
        if officer is None:
            p.add_row(row["name"], "nobody — " + row["about"].lower(), "warn")
            continue
        p.add_row(row["name"],
                  f"{officer.name} · level {officer.level} · {row['band']}",
                  row["tint"])
    p.add(empty_note(rows))
    gap = roster_sim.missing(g)
    if gap:
        p.add(label("Nobody aboard is trained in: "
                    + ", ".join(roster_sim.pretty(s).lower() for s in gap)
                    + ".", "note", "osteo", wrap=True))
    p.add_buttons(button("Sign somebody on", view.to_berths, kind="primary"))
    return p


def _order_bar(view) -> None:
    """Which question the list is being read to answer."""
    from .widgets import TabBar
    bar = TabBar([(oid, name) for oid, name in roster_sim.ORDERS], view.order)
    bar.changed.connect(view.set_order)
    view.col.addWidget(label("Everybody aboard", "h3"))
    view.col.addWidget(bar)


# ── one card ───────────────────────────────────────────────────────────────

def _card(view, g, officer) -> Card:
    """A person, shallowly: enough to pick them out, not enough to read."""
    got = roster_sim.card(g, officer)
    card = Card()
    # The face first. Everything in it is a fact printed in words further
    # down the same card — the lineage is the colour, the years are in the
    # hair, the service is the collar, the mood is the mouth — and what a
    # clinic has fitted is visible, which is the part no number carries.
    head = QWidget()
    box = QHBoxLayout(head)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(10)
    box.addWidget(portrait_paint.chip(g, officer, 62))
    names = QWidget()
    stack = QVBoxLayout(names)
    stack.setContentsMargins(0, 2, 0, 0)
    stack.setSpacing(2)
    stack.addWidget(label(officer.name, "h3"))
    stack.addWidget(label(f"{officer.role_name} · level {officer.level}",
                          "sub"))
    stack.addStretch(1)
    box.addWidget(names, 1)
    card.add(head)
    row = view.row(Pill(got["band"], got["tint"] or "lumen"),
                   Pill(f"{got['career']} · {got['rank']}", "dim"))
    card.add(row)
    card.add(note(f"{got['terms']} term(s) served · {got['age']:.0f} years "
                  f"old · {got['stage']}"))
    if got["home"]:
        card.add(note(f"From {got['home'].lower()}."))
    if got["wants"]:
        card.add(label(f"Wants: {got['wants'].lower()}.", "note", "lumen"))
    if got["best"]:
        card.add(note("Best at: " + ", ".join(
            f"{name} {level}" for name, level in got["best"])))
    if officer.trait_name:
        card.add(note(f"{officer.trait_name}: {officer.trait_note}"))
    face = portrait_paint.portrait.of(g, officer)
    showing = portrait_paint.portrait.worst_mark(face)
    if showing:
        card.add(label(
            "You can see it: " + portrait_paint.portrait.named(showing)
            + ".", "note", "lumen", wrap=True))
    told = arcs_sim.status(g, officer)
    if told["arc"] is not None:
        card.add(label(f"{told['arc'].title}  {told['marks']}", "note",
                       "chloro" if told["signature"] else ""))
    card.add(note(_people_line(got)))
    card.add(button("Read their sheet",
                    lambda _=False, o=officer: view.open_sheet(o)))
    card.clicked.connect(lambda o=officer: view.open_sheet(o))
    return card


def _people_line(got: dict) -> str:
    """Who is attached to them, counted rather than named."""
    bits = []
    if got["friends"]:
        bits.append(f"{got['friends']} who would help")
    if got["trouble"]:
        bits.append(f"{got['trouble']} who would not")
    if got["kit"]:
        bits.append(f"{got['kit']} possession(s)")
    return "  ·  ".join(bits) if bits else "Nobody out there, and nothing."
