"""What the board says against what the counter charges.

`market.quote_buy`'s own docstring says why it exists: "One helper rather than
a bias applied at the till, because a screen that quotes one number and charges
another is the defect this project keeps finding." The office-rate favour was
added afterwards and applied *at the till* — so with it running the board
showed 36/t and the counter charged 31.68, and the board said the port paid
29/t while it paid 32.95.

Except it never ran at all. `Favour.lasts` is a window in days and a quiet
price is granted "this once", so it carries `lasts=0` — and `ask()` recorded
favours with `if favour.lasts:`. A zero-day favour fell straight through.
Measured: asking cost 12.7 regard, stored nothing, and the purchase that
followed was charged the full posted price. One of the five favours the game
advertises as "read somewhere real" bought precisely nothing.

Both halves are fixed here. A one-shot is held in its own list until it is
used, and the office rate lives in `quote_buy`/`quote_sell` so the board and
the counter cannot disagree.

The claims:

- **What the board says is what the counter does.** The general one, swept
  over every commodity, buying and selling, with the favour and without.
- **A one-shot favour is recorded, and it moves the price.**
- **It is spent by being used** — once, not for ever.
- **The desk and the board both say it is in hand.**
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.officials import QUIET_SHARE
from ..sim import market, officials, trade
from .harness import Suite


def _at_a_quay(seed: str, regard: float = 60.0):
    """A game standing at a port whose official will do you a favour."""
    game = new_game(seed)
    system = game.system
    who = officials.mind(game, system)
    assert who is not None, "no official at the opening quay"
    officials._store(who)["regard"] = regard
    return game, system


def _sellable(game, system) -> str:
    return next(c for c in system.market.stock
                if market.quote_sell(game, system, c))


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the board says is what the counter charges")
    def _():
        # The general question. It is asked with the favour in hand and
        # without, because the whole defect was a discount that existed on one
        # side of the glass only.
        #
        # The quay's own cut is netted out rather than ignored: `sim/wharfage.py`
        # takes a share of every deal on top of the goods, and the claim here is
        # about the *price* — that what the board quotes for a tonne is what a
        # tonne costs. That the due is the one the board names, and that it lands
        # in the holder's purse, is `test_wharfage`'s question.
        checked = 0
        for favoured in (False, True):
            game, system = _at_a_quay("agree")
            if favoured:
                officials.ask(game, system, "quiet_price", False)
            for cid in list(system.market.stock)[:6]:
                quoted = market.quote_buy(game, system, cid)
                if quoted is None:
                    continue
                game.credits = 400_000
                before = game.credits
                res = trade.buy(game, cid, 3)
                if not res.get("ok"):
                    continue
                paid = (before - game.credits - res["due"]) / res["units"]
                assert abs(paid - quoted) < 0.01, (
                    f"{cid}: the board says {quoted} and the counter charged "
                    f"{paid:.2f} for the goods"
                    + (" with the office rate in hand" if favoured else ""))
                checked += 1
                if favoured:
                    break        # the one-shot is gone after the first deal

        for favoured in (False, True):
            game, system = _at_a_quay("agree-sell")
            if favoured:
                officials.ask(game, system, "quiet_price", False)
            cid = _sellable(game, system)
            game.ship.cargo[cid] = 90
            quoted = market.quote_sell(game, system, cid)
            before = game.credits
            res = trade.sell(game, cid, 15)
            assert res.get("ok"), res
            got = (game.credits - before + res["due"]) / res["units"]
            assert abs(got - quoted) < 0.01, (
                f"{cid}: the board says the port pays {quoted} and it paid "
                f"{got:.2f} over the counter"
                + (" with the office rate in hand" if favoured else ""))
            checked += 1
        assert checked >= 6, checked
        return (f"{checked} deals, board and counter agreeing on the price of every one")

    @check("a favour granted for one deal is actually recorded")
    def _():
        # `if favour.lasts:` dropped it, so this is where the whole thing died.
        game, system = _at_a_quay("recorded")
        who = officials.mind(game, system)
        before = officials._store(who)["regard"]
        res = officials.ask(game, system, "quiet_price", False)
        assert res.get("ok"), res
        assert officials._store(who)["regard"] < before - 1, (
            "asking cost no regard worth the name")
        assert officials.pending_once(game, system, "quiet_price"), (
            "the favour was granted, paid for in regard, and stored nowhere")
        assert officials.anywhere(game, "quiet_price"), (
            "the favour is held and `anywhere` cannot see it — which is what "
            "the price code asks")
        return (f"regard {before:.0f} → "
                f"{officials._store(who)['regard']:.0f}, and it is on the books")

    @check("the office rate is worth what it says, up to the counter's own ask")
    def _():
        # Measured against the share written in `data/officials.py` rather than
        # re-deriving it. The favour cuts both ways — but the sale is capped
        # under what the counter now asks, because a favour applied as a raise
        # on one side and a discount on the other used to invert the spread:
        # buy at the office rate, sell at the office rate, richer for it, on
        # the same tonne at the same counter. The promise on the screen is "the
        # office rate rather than the posted one", and that is what happens;
        # what no favour may promise is a counter that pays more than it asks.
        game, system = _at_a_quay("worth")
        goods = [c for c in system.market.stock
                 if market.quote_sell(game, system, c)]
        posted = {c: (market.quote_buy(game, system, c),
                      market.quote_sell(game, system, c)) for c in goods}
        officials.ask(game, system, "quiet_price", False)
        raised = []
        for cid in goods:
            office_buy = market.quote_buy(game, system, cid)
            office_sell = market.quote_sell(game, system, cid)
            posted_buy, posted_sell = posted[cid]
            if posted_buy is None:
                # Sold to, never sold by — no counter, so no ask to stay
                # under. The favour must still not make the sale worse.
                assert office_sell >= posted_sell, (
                    f"{cid}: the favour cut a sale with no counter")
                continue
            assert office_buy < posted_buy, (
                f"{cid}: the office rate charges {office_buy} against a "
                f"posted {posted_buy}")
            assert abs(office_buy - round(posted_buy * QUIET_SHARE)) <= 1, (
                f"{cid}: {office_buy} against {posted_buy} — not the share")
            assert office_sell >= posted_sell, (
                f"{cid}: the office rate pays {office_sell} against a "
                f"posted {posted_sell} — a favour made the sale worse")
            assert office_sell < office_buy, (
                f"{cid}: pays {office_sell}, asks {office_buy} — the favour "
                f"turned the counter into a pump")
            if office_sell > posted_sell:
                raised.append(cid)
        assert raised, "the office rate raised no sale price at all"
        return (f"{len(goods)} goods at the office rate: all cheaper to buy, "
                f"{len(raised)} dearer to sell, none above the ask")

    @check("the same counter never pays more than it asks, whoever asks")
    def _():
        # `sell_price` crossed `buy_price` at trade 0.222 (a finished tree is
        # 0.48), and a warm memory inverted the pair by its square — measured,
        # 18,000 credits became 2,645,369 in two hundred same-counter round
        # trips on day zero. Swept at the extremes of both modifiers, over
        # every stocked good at every port in the sector.
        from ..data.tech import TECH
        from ..sim import grudge as grudge_sim
        crossings = []
        ports = goods = 0
        for warmth in ("cold", "warm"):
            game = new_game("counter-sweep")
            game.research.unlocked = [t.id for t in TECH]
            game.recompute()
            for sysm in game.galaxy.systems:
                if not sysm.port or not sysm.market:
                    continue
                ports += 1
                if warmth == "warm":
                    for _ in range(3):
                        grudge_sim.note(game, sysm.port.faction, "rescue",
                                        "you came for us", 1.5)
                for cid in sysm.market.stock:
                    qb = market.quote_buy(game, sysm, cid)
                    qs = market.quote_sell(game, sysm, cid)
                    goods += 1
                    if qb is not None and qs is not None and qs >= qb:
                        crossings.append((warmth, sysm.name, cid, qb, qs))
        assert not crossings, f"sell ≥ buy at {crossings[:4]}"
        return (f"{goods} quotes across {ports} port visits, cold and warm: "
                f"sell under buy at every one")

    @check("working the same counter is a way to lose money")
    def _():
        # The compounding half of the same exploit: each cycle made the port
        # scarcer, so the next cycle paid better. Played rather than quoted.
        from ..data.tech import TECH
        game = new_game("counter-grind")
        game.research.unlocked = [t.id for t in TECH]
        game.recompute()
        start = game.credits
        cycles = 0
        for _ in range(40):
            if not trade.buy(game, "ore", 10)["ok"]:
                break
            if not trade.sell(game, "ore", 10)["ok"]:
                break
            cycles += 1
        assert cycles >= 20, f"the counter ran dry after {cycles} cycles"
        assert game.credits < start, (
            f"{cycles} same-counter round trips turned {start} into "
            f"{game.credits}")
        return (f"{cycles} round trips, {start} → {game.credits} credits — "
                f"the counter takes its cut every time")

    @check("a favour good once is good once")
    def _():
        game, system = _at_a_quay("spent")
        cid = _sellable(game, system)
        posted = market.quote_buy(game, system, cid)
        officials.ask(game, system, "quiet_price", False)
        assert market.quote_buy(game, system, cid) < posted
        game.credits = 400_000
        res = trade.buy(game, cid, 2)
        assert res.get("ok"), res
        assert not officials.pending_once(game, system, "quiet_price"), (
            "the office rate survived the deal it was granted for")

        # Against a control that made the same purchase and never asked for
        # anything, not against the price posted *before* the deal — because
        # buying moves the board. Measured, two tonnes of ore takes it from 36
        # to 37, so the old comparison was reading a market that had correctly
        # drifted as a favour that had not been spent. It passed only while the
        # drift on whatever commodity the seed picked stayed under a rounding
        # boundary, and went red when a change to *star generation* re-rolled
        # which quay and which commodity the chronicle lands on.
        control, csys = _at_a_quay("spent")
        control.credits = 400_000
        again = trade.buy(control, cid, 2)
        assert again.get("ok"), again
        unfavoured = market.quote_buy(control, csys, cid)
        assert market.quote_buy(game, system, cid) == unfavoured, (
            f"after the deal the favoured board quotes "
            f"{market.quote_buy(game, system, cid)} against {unfavoured} for a "
            "captain who never asked — the office rate outlived its one deal")
        return (f"one deal, and the counter goes back to what anyone else "
                f"pays ({unfavoured}); the office rate cut it to "
                f"{posted - 4} for exactly one purchase")

    @check("the price columns on the screen are the ones the counter reads")
    def _():
        # **The third door, and this suite missed it for as long as it has
        # existed.** Everything above compares `quote_buy`/`quote_sell` against
        # the till. The market grid on the port screen was not asking either of
        # them: it called `world.economy.buy_price` directly, so it carried
        # neither the grudge bias nor the office rate — and the comment forty
        # lines above it said "now it is in the quote, and the board says so".
        #
        # Measured with a quiet price in hand: the grid printed 36 and 29 while
        # the counter charged 32 and paid 33. A check that reads the helper can
        # never see this; it has to read the rendered screen.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..data.commodities import COMMODITIES
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, system = _at_a_quay("columns")
        officials.ask(game, system, "quiet_price", False)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("port")
        view = win.views["port"]
        view.tab = "market"
        view.refresh()
        for _ in range(3):
            app.processEvents()

        # The grid is laid out by name in column 0, buy in 1, sell in 2 — so
        # the row is found by the commodity's name rather than by counting.
        printed = {}
        for good in COMMODITIES:
            row = [lab for lab in view.findChildren(QLabel)
                   if lab.text() == good.name]
            if not row:
                continue
            grid = row[0].parentWidget().layout()
            at = grid.indexOf(row[0])
            r, c, _, _ = grid.getItemPosition(at)
            printed[good.id] = tuple(
                grid.itemAtPosition(r, col).widget().text() for col in (1, 2))
        win.close()
        assert printed, "the market grid printed no rows at all"

        from ..core.util import credits as cr
        checked = 0
        for cid, (shown_buy, shown_sell) in printed.items():
            for shown, quoted in ((shown_buy, market.quote_buy(game, system, cid)),
                                  (shown_sell, market.quote_sell(game, system, cid))):
                if shown == "—":
                    continue
                assert shown == cr(quoted), (
                    f"{cid}: the screen prints {shown} and the counter reads "
                    f"{cr(quoted)} — with the office rate in hand")
                checked += 1
        assert checked >= 10, checked
        return (f"{checked} price columns across {len(printed)} goods, every one "
                "the figure the till reads, office rate included")

    @check("the desk and the board both say it is in hand")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, system = _at_a_quay("screen")
        officials.ask(game, system, "quiet_price", False)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("port")
        view = win.views["port"]
        seen = {}
        for tab in ("desk", "market"):
            view.tab = tab
            view.refresh()
            for _ in range(3):
                app.processEvents()
            seen[tab] = " ".join(lab.text() for lab in view.findChildren(QLabel)
                                 if lab.text())
        win.close()
        # Two separate places say it and they are checked separately: the
        # standing "Running:" list, built from `active_favours`, and the
        # favour's own card, built from `pending_once`. Asserting only "good
        # once" appears somewhere let one of them be deleted in silence.
        assert "next time you deal here" in seen["desk"], (
            "the desk's list of what is running does not include the favour")
        assert "Already owed" in seen["desk"], (
            "the favour's own card does not say it is already in hand")
        assert "office rate" in seen["market"], (
            "the market board quotes office rates and never says so")
        return "the desk names it and the board explains its own numbers"
