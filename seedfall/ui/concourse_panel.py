"""The Port screen's concourse: the chandler, the counter, and a night ashore.

What a captain can do at a port with money that is not a cargo. Three panels,
and every one of them is gated on the world profile — so the tab on a class-A
capital is four floors of chandlery, a chartered bank and a members' club,
and on a class-D rock it is a shed and somewhere selling noodles.

The screen decides nothing: `sim/shore.py` says what is open, what is on the
shelf, what a night would cost and what it would buy, and every button calls
back into it. The prices quoted here are the prices charged, which is this
project's oldest rule.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data import kit as kit_table
from ..data import venues as venue_table
from ..sim import person as person_sim
from ..sim import profile as profile_sim
from ..sim import shore
from .view_base import WrapRow
from .widgets import Panel, button, label, note

#: How many things to list in one category before saying there are more. A
#: chandler with ninety items is a catalogue, not a shop window.
SHOWN = 8


def build(view) -> None:
    """The whole tab."""
    game, system = view.game, view.game.system
    world = profile_sim.port_world(system)
    if world is None or not system.port:
        view.col.addWidget(note("There is no concourse here."))
        return
    got = profile_sim.profile(game, system, world)
    from ..data import uwp
    star = uwp.STARPORTS.get(got.starport, uwp.STARPORTS[0])[0]
    view.col.addWidget(note(
        f"{system.port.name} — starport {star}, tech level {got.tech}, law "
        f"level {got.law}. What is on the shelves is the tech level; what "
        "the desk will let you carry off is the law."))
    view.col.addWidget(_purse(view, game, system, got))
    _shelves(view, game, system, got)
    _nights(view, game, system)


def _purse(view, game, system, got) -> Panel:
    """What you have, what is on account, and what you are carrying."""
    p = Panel("The purse")
    p.add_row("In hand", f"{int(game.credits):,} credits")
    p.add_row("On account", shore.account_line(game))
    owned = shore.owned(game)
    p.add_row("Carried", f"{len(owned)} possession(s)"
              if owned else "nothing of your own")
    risky = [i for i in owned if not kit_table.legal_at(i, got.law)]
    if risky:
        p.add(label("The desk here would take: "
                    + ", ".join(i.name for i in risky), "note", "warn"))
    crew = person_sim.risk_ashore(game, got.law)
    if crew["people"]:
        p.add(label(f"{crew['people']} of the watch are carrying something "
                    f"this world forbids.", "note", "warn"))
    if shore.bank_here(game, system):
        p.add(view.row(
            button("Deposit 5,000",
                   lambda: _bank(view, system, 5_000, True), kind="flat"),
            button("Deposit all",
                   lambda: _bank(view, system, game.credits, True),
                   kind="flat"),
            button("Draw 5,000",
                   lambda: _bank(view, system, 5_000, False), kind="flat"),
            button("Draw all",
                   lambda: _bank(view, system,
                                 getattr(game, "deposited", 0.0), False),
                   kind="flat")))
    else:
        p.add(note("No counting house here; the money stays aboard."))
    return p


def _bank(view, system, amount, put: bool) -> None:
    got = (shore.deposit(view.game, system, amount) if put
           else shore.withdraw(view.game, system, amount))
    view.win.toast(got.get("why") or
                   (f"{got['cr']:,} credits "
                    + ("deposited." if put else "drawn.")),
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _shelves(view, game, system, got) -> None:
    """The chandler, a panel per category."""
    rows = shore.shelves(game, system)
    if not rows:
        view.col.addWidget(note("Nothing here sells anything a person can "
                                "carry."))
        return
    shops = shore.open_here(game, system, "chandler")
    view.col.addWidget(label("The chandler", "h2"))
    view.col.addWidget(note("  ·  ".join(
        f"{v.name} — {v.note}" for v in shops)))
    held = list(getattr(game, "kit", []) or [])
    wrap = WrapRow(10)
    for cid, name, _note in kit_table.CATEGORIES:
        here = [r for r in rows if r["item"].category == cid]
        if not here:
            continue
        p = Panel(name)
        for row in here[:SHOWN]:
            item = row["item"]
            line = QWidget()
            box = QHBoxLayout(line)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(6)
            tint = "" if row["legal"] else "warn"
            box.addWidget(label(f"{item.name} — {row['cr']:,}", "note", tint),
                          1)
            box.addWidget(button(
                "Buy", lambda _=False, i=item.id: _buy(view, system, i),
                kind="flat"))
            if item.id in held:
                box.addWidget(button(
                    "Sell", lambda _=False, i=item.id: _sell(view, system, i),
                    kind="flat"))
            p.add(line)
            p.add(label(item.note, "note"))
        if len(here) > SHOWN:
            p.add(note(f"…and {len(here) - SHOWN} more."))
        wrap.add(p, 1)
    view.col.addWidget(wrap)


def _buy(view, system, item_id: str) -> None:
    got = shore.buy(view.game, system, item_id)
    view.win.toast(got.get("why") or f"{got['item'].name} bought.",
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _sell(view, system, item_id: str) -> None:
    got = shore.sell(view.game, system, item_id)
    view.win.toast(got.get("why") or
                   f"{got['item'].name} sold for {got['cr']:,}.",
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _nights(view, game, system) -> None:
    """Somewhere to eat, and somewhere to go afterwards."""
    for kind in ("eatery", "entertainment"):
        rows = shore.open_here(game, system, kind)
        if not rows:
            continue
        view.col.addWidget(label(venue_table.KIND_NAME[kind], "h2"))
        wrap = WrapRow(10)
        for venue in rows:
            p = Panel(venue.name)
            p.add(note(venue.note))
            if venue.favours:
                level, who = _best(game, venue.favours)
                if who is not None:
                    p.add(label(
                        f"{who.name} has {venue.favours.title()} {level} — "
                        "they will get more out of it.", "note", "chloro"))
            p.add(label(shore.ashore_note(game, system, venue), "note"))
            p.add(button("Take the watch",
                         lambda _=False, v=venue.id: _ashore(view, system, v),
                         kind="primary"))
            wrap.add(p, 1)
        view.col.addWidget(wrap)


def _best(game, skill: str):
    from ..sim import lifepath as life_sim
    level, who = life_sim.skill_aboard(game, skill)
    return level, who


def _ashore(view, system, venue_id: str) -> None:
    got = shore.ashore(view.game, system, venue_id)
    if not got["ok"]:
        view.win.toast(got["why"], "warn")
        return
    said = f"{got['cr']:,} credits ashore."
    if got.get("heard"):
        said += f"  {got['heard']}"
    view.win.toast(said, "good")
    view.refresh()
