"""The Port's price board, kept between refreshes and changed in place.

Split out of `ui/port_view.py`. **Every purchase rebuilt the board** — a
hundred-odd widgets for thirteen goods, made and styled again after each
press of Buy, and every quantity box put back to 10 whatever the captain had
typed into it. Measured: 131 ms from pressing Buy to the screen standing
again, 46 of it the ship's log (`ui/log_panel.py`) and most of the rest this
grid. Now the board is built once per port and a refresh rewrites the text
that changed; it is made again only when the set of goods on it changes.
"""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QSpinBox, QWidget

from ..core.util import credits as cr
from ..data.commodities import COMMODITIES
from ..sim import customs as customs_sim
from ..sim import market as market_sim
from ..world.economy import price_note
from .widgets import Panel, Pill, button, label, mono_label

HEADS = ("Commodity", "Buy", "Sell", "Local", "Aboard", "")


def rows(game, system) -> list:
    """What the board shows, good by good: the quotes the till will use."""
    out = []
    for c in COMMODITIES:
        # A good this power seizes has no counter here. Leaving the posted
        # sell price up let you hand unlicensed seed over the desk at a Yards
        # station for a receipt, which is the exact thing the boarding party
        # is there to stop.
        banned = customs_sim.outlaws(system.port.faction, c.id)
        # `quote_buy`, not `buy_price`: the till asks the quote helper, which
        # carries the grudge bias and the office rate. Measured with a quiet
        # price in hand, the raw market said 36 and 29 where the counter
        # charged 32 and paid 33.
        bp = market_sim.quote_buy(game, system, c.id)
        sp = None if banned else market_sim.quote_sell(game, system, c.id)
        held = game.ship.cargo.get(c.id, 0)
        if bp is None and held <= 0:
            continue
        note_text, note_tint = (("seized on sight", "warn") if banned
                                else price_note(system.market, c.id))
        out.append((c, bp, sp, held, banned, note_text, note_tint))
    return out


class MarketGrid(Panel):
    """One port's board. `sync` rewrites it; the quantities typed stay."""

    def __init__(self, view, system_id: int):
        super().__init__()
        self.view = view
        self.system_id = system_id
        self._ids: list[str] = []
        self._cells: dict[str, dict] = {}
        self._host = QWidget()
        self._grid = QGridLayout(self._host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(12)
        self._grid.setVerticalSpacing(6)
        for i, head in enumerate(HEADS):
            self._grid.addWidget(mono_label(head), 0, i)
        self.add(self._host)

    def sync(self, game, system) -> int:
        """Bring the board up to date. Returns how many rows were made."""
        now = rows(game, system)
        ids = [r[0].id for r in now]
        made = 0
        if ids != self._ids:
            for cells in self._cells.values():
                for w in cells["widgets"]:
                    self._grid.removeWidget(w)
                    self.view.park(w)
            self._cells = {}
            for i, r in enumerate(now, start=1):
                self._make(i, r)
            self._ids = ids
            made = len(now)
        for r in now:
            self._fill(r)
        return made

    def _make(self, i: int, r) -> None:
        c = r[0]
        name = label(c.name)
        name.setToolTip(c.blurb)
        buy, sell, local, aboard = label(""), label(""), Pill(""), label("")
        actions = QWidget()
        ah = QHBoxLayout(actions)
        ah.setContentsMargins(0, 0, 0, 0)
        ah.setSpacing(4)
        qty = QSpinBox()
        qty.setRange(1, 9999)
        qty.setValue(10)
        qty.setFixedWidth(66)
        qty.setAccessibleName(f"Tonnes of {c.name}")
        qty.setObjectName(f"qty_{c.id}")
        b_buy = button("Buy", lambda cid=c.id, q=qty: self.view._buy(cid, q.value()))
        b_sell = button("Sell", lambda cid=c.id, q=qty: self.view._sell(cid, q.value()))
        b_buy.setObjectName(f"buy_{c.id}")
        b_sell.setObjectName(f"sell_{c.id}")
        b_buy.setAccessibleName(f"Buy {c.name}")
        b_sell.setAccessibleName(f"Sell {c.name}")
        for w in (qty, b_buy, b_sell):
            ah.addWidget(w)
        for col, w in enumerate((name, buy, sell, local, aboard, actions)):
            self._grid.addWidget(w, i, col)
            if self.isVisible():
                w.show()
        self._cells[c.id] = {"buy": buy, "sell": sell, "local": local,
                             "aboard": aboard, "b_buy": b_buy, "b_sell": b_sell,
                             "widgets": (name, buy, sell, local, aboard,
                                         actions)}

    def _fill(self, r) -> None:
        c, bp, sp, held, banned, note_text, note_tint = r
        cells = self._cells[c.id]
        cells["buy"].setText(cr(bp) if bp else "—")
        cells["sell"].setText(cr(sp) if sp else "—")
        cells["local"].set_tint(note_text, note_tint)
        cells["aboard"].setText(f"{round(held, 1):g}" if held else "—")
        b_buy, b_sell = cells["b_buy"], cells["b_sell"]
        # **The till's own gate** (`trade.can_buy`), not merely a posted
        # price: lit on the price alone, Buy answered "no room in the hold"
        # and "not enough credits" in a play session.
        from ..sim import trade as trade_sim
        can_buy, buy_why = (trade_sim.can_buy(self.view.game, c.id)
                            if bp is not None
                            else (False,
                                  f"Nobody here is selling {c.name.lower()}."))
        b_buy.setEnabled(can_buy)
        b_buy.setToolTip(f"Buy the tonnage set beside it, at {cr(bp)} a tonne."
                         if can_buy else buy_why)
        can_sell = held > 0 and not banned
        b_sell.setEnabled(can_sell)
        b_sell.setToolTip(
            (f"Sell the tonnage set beside it, at {cr(sp)} a tonne."
             if sp else "Sell the tonnage set beside it.")
            if can_sell else
            f"{c.name} is seized on sight here — no counter will take it."
            if banned else f"You have no {c.name.lower()} aboard.")
