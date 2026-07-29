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
                paid = (before - game.credits) / res["units"]
                assert abs(paid - quoted) < 0.01, (
                    f"{cid}: the board says {quoted} and the counter charged "
                    f"{paid:.2f}"
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
            got = (game.credits - before) / res["units"]
            assert abs(got - quoted) < 0.01, (
                f"{cid}: the board says the port pays {quoted} and it paid "
                f"{got:.2f}"
                + (" with the office rate in hand" if favoured else ""))
            checked += 1
        assert checked >= 6, checked
        return f"{checked} deals, board and counter agreeing on every one"

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

    @check("the office rate is worth what it says, both ways")
    def _():
        # Measured against the share written in `data/officials.py` rather than
        # re-deriving it, and confirmed to move in opposite directions.
        game, system = _at_a_quay("worth")
        cid = _sellable(game, system)
        posted_buy = market.quote_buy(game, system, cid)
        posted_sell = market.quote_sell(game, system, cid)
        officials.ask(game, system, "quiet_price", False)
        office_buy = market.quote_buy(game, system, cid)
        office_sell = market.quote_sell(game, system, cid)
        assert office_buy < posted_buy, (
            f"the office rate charges {office_buy} against a posted "
            f"{posted_buy}")
        assert office_sell > posted_sell, (
            f"the office rate pays {office_sell} against a posted "
            f"{posted_sell} — it is supposed to cut both ways")
        assert abs(office_buy - round(posted_buy * QUIET_SHARE)) <= 1, (
            f"{office_buy} against {posted_buy} — not the office share")
        return (f"buying {posted_buy} → {office_buy}, "
                f"selling {posted_sell} → {office_sell}")

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
