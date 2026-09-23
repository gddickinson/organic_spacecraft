"""The Shops tab: the purse, the counters, the shelf, and the paperwork.

What a captain can buy here with money that is not a cargo and is not a
person. The chandler is the bulk of it; everything else is a door with a
name, a note and what it sells, because an insurer and a notary are worth
*knowing about* long before they are worth a button.

Every price on this tab is `sim/shore.py`'s, read against the place being
walked rather than against a starport — so the same screen prices a Charter
emporium and a fence on a frontier rock, and the difference is four numbers
in `sim/places.py`.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QWidget

from ..data import kit as kit_table
from ..data import venues as venue_table
from ..sim import person as person_sim
from ..sim import shore
from . import concourse_hire
from .widgets import Panel, button, label, note

#: How many things to list in one category before saying there are more. A
#: chandler with ninety items is a catalogue, not a shop window.
SHOWN = 8

#: The kinds of door this tab is about. The rest of the concourse is beds,
#: bodies and evenings, and each of those has its own tab.
SHOP_KINDS = ("chandler", "market", "tech", "bank", "office", "law",
              "transport")


def build(view, place) -> None:
    """The whole tab."""
    game = view.game
    view.col.addWidget(_purse(view, game, place))
    _shelves(view, game, place)
    concourse_hire.build(view, place)
    _doors(view, game, place)


def _purse(view, game, place) -> Panel:
    """What you have, what is on account, and what you are carrying."""
    p = Panel("The purse")
    p.add_row("In hand", f"{int(game.credits):,} credits")
    p.add_row("On account", shore.account_line(game))
    owned = shore.owned(game)
    p.add_row("Carried", f"{len(owned)} possession(s)"
              if owned else "nothing of your own")
    risky = [i for i in owned if not kit_table.legal_at(i, place.law)]
    if risky:
        p.add(label("The desk here would take: "
                    + ", ".join(i.name for i in risky), "note", "warn",
                    wrap=True))
    crew = person_sim.risk_ashore(game, place.law)
    if crew["people"]:
        p.add(label(f"{crew['people']} of the watch are carrying something "
                    f"this world forbids.", "note", "warn", wrap=True))
    can, why = view.can_trade(place)
    if shore.bank_here(game, place):
        p.add(view.row(
            button("Deposit 5,000",
                   lambda: _bank(view, place, 5_000, True), kind="flat",
                   enabled=can, tip=why),
            button("Deposit all",
                   lambda: _bank(view, place, game.credits, True),
                   kind="flat", enabled=can, tip=why),
            button("Draw 5,000",
                   lambda: _bank(view, place, 5_000, False), kind="flat",
                   enabled=can, tip=why),
            button("Draw all",
                   lambda: _bank(view, place,
                                 getattr(game, "deposited", 0.0), False),
                   kind="flat", enabled=can, tip=why)))
    else:
        p.add(note("No counting house here; the money stays aboard."))
    return p


def _bank(view, place, amount, put: bool) -> None:
    got = (shore.deposit(view.game, place, amount) if put
           else shore.withdraw(view.game, place, amount))
    view.win.toast(got.get("why") or
                   (f"{got['cr']:,} credits "
                    + ("deposited." if put else "drawn.")),
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _shelves(view, game, place) -> None:
    """The chandler, a panel per category."""
    rows = shore.shelves(game, place)
    if not rows:
        view.col.addWidget(note("Nothing here sells anything a person can "
                                "carry."))
        return
    shops = shore.selling(game, place, "shelf")
    view.col.addWidget(label("The chandler", "h2"))
    view.col.addWidget(note("  ·  ".join(
        f"{v.name} — {v.note}" for v in shops)))
    held = list(getattr(game, "kit", []) or [])
    can, why = view.can_trade(place)
    cards = []
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
            # **And the price**, which this counter alone was not asking
            # about: the same shelf reached from a deck (`afoot_talk_panel`)
            # greys what you cannot afford, and here it stayed lit and
            # answered "1,200 credits, and you have -214".
            afford = game.credits >= row["cr"]
            box.addWidget(button(
                "Buy", lambda _=False, i=item.id: _buy(view, place, i),
                kind="flat", enabled=can and afford, tip=why,
                why=why if not can else
                    f"{row['cr']:,} credits, and you have "
                    f"{int(game.credits):,}."))
            if item.id in held:
                box.addWidget(button(
                    "Sell", lambda _=False, i=item.id: _sell(view, place, i),
                    kind="flat", enabled=can, tip=why))
            p.add(line)
            p.add(label(item.note, "note"))
        if len(here) > SHOWN:
            p.add(note(f"…and {len(here) - SHOWN} more."))
        cards.append(p)
    view.grid(cards, cols=3)


def _buy(view, place, item_id: str) -> None:
    got = shore.buy(view.game, place, item_id)
    view.win.toast(got.get("why") or f"{got['item'].name} bought.",
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _sell(view, place, item_id: str) -> None:
    got = shore.sell(view.game, place, item_id)
    view.win.toast(got.get("why") or
                   f"{got['item'].name} sold for {got['cr']:,}.",
                   "warn" if not got["ok"] else "good")
    view.refresh()


def _doors(view, game, place) -> None:
    """Everything else on this side of the concourse, by kind.

    A notary, an insurer and a hiring hall are not buttons — they are things
    that are *here*, and knowing a place has one is most of what a captain
    wants off a concourse board.
    """
    view.col.addWidget(label("On the concourse", "h2"))
    cards = []
    shown = 0
    for kind in SHOP_KINDS:
        rows = shore.open_here(game, place, kind)
        if not rows:
            continue
        shown += len(rows)
        p = Panel(venue_table.KIND_NAME[kind])
        p.add(note(venue_table.KIND_NOTE[kind]))
        for venue in rows:
            tint = "warn" if venue.kind == "law" else ""
            p.add(label(venue.name, "sub", tint))
            p.add(note(venue.note))
            if venue.offers:
                p.add(label("  " + ", ".join(
                    venue_table.OFFER_NAME[o] for o in venue.offers
                    if o in venue_table.OFFER_NAME), "note", "dim",
                    wrap=True))
        cards.append(p)
    if not shown:
        view.col.addWidget(note("Nothing here but the berth."))
        return
    view.grid(cards, cols=3)
