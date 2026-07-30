"""What a signed treaty is worth — the clauses the blurb has always promised.

`data/diplomacy.ACTIONS` sells a treaty as "a signed instrument: mutual berthing,
shared charts, and a clause about the Bloom that nobody expects to be honoured".
The third is a joke. The other two were as well: signing appended a faction id to
`DiplomaticState.treaties`, which was read by `treaty_bonus` (+3% on the trade
stat, printed on no screen) and by the matrix's "treaty" pill, and by nothing
else. Measured at Vesper Bight before the fix: wharfage 1.714% before signing and
1.552% after — and the whole of that fall was the *standing* the treaty granted,
which tribute at a third of the price buys as well. Charts known: 0 before, 0
after.

The claims:

- **Both clauses in the blurb are clauses in the act.** Named in the text,
  measured in the game, at a standing held still so the treaty is the only thing
  that moved.
- **The quote is a dry run of the act.** What the desk promises before signing is
  what signing hands over, system for system and credit for credit.
- **Only the signatory's quays**, and not a free port, which was already free.
- **The relief reaches every door the charge does** — the market board, the
  freight forecast, the counter and the holder's purse — because `wharfage.rate`
  is the one place the charge is worked out.
- **The gift shrinks as you explore it yourself**, so it cannot be double-counted.
- **Both screens say it**: the desk quotes the instrument before you sign, and
  the market board says why the number fell.
- **And what the instrument is actually worth** against its 30,000 credits, for
  each of the four powers, since the answer turns out to be geography.
"""

from __future__ import annotations

import re

from ..core.state import new_game
from ..data.diplomacy import ACTIONS_BY_ID
from ..sim import accord as accord_sim
from ..sim import diplomacy as dip
from ..sim import freight as freight_sim
from ..sim import intel as intel_sim
from ..sim import market as market_sim
from ..sim import trade as trade_sim
from ..sim import wharfage as wharfage_sim
from .harness import Suite


def _ready(seed: str = "accord", power: str = "charter"):
    """A captain who can afford the instrument, at a standing that will not move."""
    game = new_game(seed)
    game.credits = 400_000
    game.rep[power] = 50.0
    return game


def _sign(game, power: str) -> dict:
    """Sign, holding standing still, so the treaty is the only thing that moved.

    `perform` grants standing as well, and `wharfage.rate` reads standing — so a
    check that let the gain land would be measuring courtship and calling it
    berthing. That is exactly the reading that hid this defect for a cycle.
    """
    was = dict(game.rep)
    res = dip.perform(game, "treaty", power)
    game.rep.update(was)
    return res


def _quays_of(game, power: str) -> list:
    return [s for s in game.galaxy.systems
            if wharfage_sim.holder(game, s) == power and s.market]


def _stand_at(game, system) -> None:
    game.location_id = system.id
    market_sim.note_prices(game, system,
                           game.rep.get(system.port.faction, 0),
                           game.ship_stats.trade)


def _tradeable(game, system) -> str:
    return next(c for c in system.market.stock
                if market_sim.quote_buy(game, system, c)
                and market_sim.quote_sell(game, system, c))


def run(suite: Suite) -> None:
    check = suite.check

    @check("the blurb names berthing and charts, and the act delivers both")
    def _():
        # The regression for the defect itself, read off the text that sells it
        # rather than off a list written here: if the sales pitch changes, this
        # check goes looking for the new promise.
        blurb = ACTIONS_BY_ID["treaty"].blurb.lower()
        assert "berthing" in blurb and "chart" in blurb, blurb
        game = _ready("clauses")
        quays = _quays_of(game, "charter")
        assert quays, "the Charter holds no quay that charges a due"
        before_rate = {s.id: wharfage_sim.rate(game, s) for s in quays}
        before_charts = list(intel_sim.ensure(game))
        told = dip.preview(game, "treaty", "charter")["accord"]
        _sign(game, "charter")

        cheaper = [s for s in quays
                   if wharfage_sim.rate(game, s) < before_rate[s.id] - 1e-12]
        assert len(cheaper) == len(quays), (
            f"{len(quays) - len(cheaper)} of the Charter's {len(quays)} quays "
            "charge the same after signing a treaty that promises berthing")
        gained = [c for c in intel_sim.ensure(game) if c not in before_charts]
        assert gained, (
            "signed a treaty promising shared charts and not one chart changed "
            f"hands (they hold {told['space']} systems)")
        return (f"{len(cheaper)} quays cheaper and {len(gained)} charts handed "
                f"over, at a standing held still at {game.rep['charter']:+.0f}")

    @check("what the desk promises is what signing hands over")
    def _():
        # One door: `preview` and `perform` both ask `accord.worth`, so the
        # count and the price on the screen are a dry run of the act rather than
        # a formula that resembles it. Checked for all four, because the gift is
        # geography and the near power's is the small one.
        rows = []
        for power in dip.POWERS:
            game = _ready("dryrun", power)
            told = dip.preview(game, "treaty", power)["accord"]
            names = set(told["names"])
            before = set(intel_sim.ensure(game))
            res = _sign(game, power)
            gained = set(intel_sim.ensure(game)) - before
            got = {s.name for s in game.galaxy.systems if s.id in gained}
            assert got == names, (
                f"{power}: the desk promised {sorted(names)} and signing "
                f"handed over {sorted(got)}")
            assert len(gained) == told["charts"], (told["charts"], len(gained))
            if told["worth"]:
                said = f"{told['worth']:,}"
                assert any(said in line for line in res["lines"]), (
                    f"{power}: quoted {said} and the dialogue says "
                    f"{res['lines']}")
            rows.append(f"{power} {told['charts']}/{told['worth']:,}")
        return "quote matched the act for all four — " + " · ".join(rows)

    @check("the relief applies at their quays and nobody else's")
    def _():
        game = _ready("theirs")
        others = [p for p in dip.POWERS if p != "charter"]
        watch = {p: [s for s in game.galaxy.systems
                     if wharfage_sim.holder(game, s) == p]
                 for p in ["charter"] + others}
        before = {s.id: wharfage_sim.rate(game, s)
                  for group in watch.values() for s in group}
        _sign(game, "charter")
        for power in others:
            for system in watch[power]:
                assert abs(wharfage_sim.rate(game, system)
                           - before[system.id]) < 1e-12, (
                    f"a treaty with the Charter moved the due at "
                    f"{system.port.name}, which {power} holds")
        # And a free port stays free rather than going negative or gaining a
        # relief on a charge that was never made.
        free = [s for s in game.galaxy.systems
                if s.port and wharfage_sim.holder(game, s) is None]
        assert free, "no free port in the sector"
        for system in free[:4]:
            assert wharfage_sim.rate(game, system) == 0.0
            assert wharfage_sim.due_on(game, system, 50_000) == 0
        # And the count the desk puts on the offer is the count that moved: a
        # quote of "5 quays" against a relief that lands at three of them is the
        # gate not matching the act, which is how the berthing clause came to be
        # decoration in the first place.
        told = accord_sim.worth(game, "charter")
        all_theirs = watch["charter"]
        moved = sum(1 for s in all_theirs
                    if wharfage_sim.rate(game, s) != before[s.id])
        assert told["quays"] == len(all_theirs), (told["quays"], len(all_theirs))
        assert moved == told["quays"], (
            f"the desk counts {told['quays']} quays and the relief moved "
            f"{moved} of them")
        return (f"{moved} Charter quays moved, "
                f"{sum(len(watch[p]) for p in others)} others untouched, "
                f"{len(free[:4])} free ports still free")

    @check("the charge is pinned to the figures the relief is worth")
    def _():
        # Written figures, never the constant under test. An outpost at neutral
        # standing charges 2%; the same quay under an instrument charges 1%.
        game = new_game("pinned")
        system = next(s for s in game.galaxy.systems
                      if s.port and s.port.level == 1
                      and wharfage_sim.holder(game, s) is not None)
        power = system.port.faction
        game.rep[power] = 0.0
        assert abs(wharfage_sim.rate(game, system) - 0.02) < 1e-9, (
            f"neutral standing at an outpost is 2% and reads "
            f"{wharfage_sim.rate(game, system):.4f}")
        dip.ensure(game).treaties.append(power)
        assert abs(wharfage_sim.rate(game, system) - 0.01) < 1e-9, (
            f"under a treaty it should be 1% and reads "
            f"{wharfage_sim.rate(game, system):.4f}")
        # Kin *and* an instrument: the two levers multiply, and the floor holds.
        game.rep[power] = 70.0
        both = wharfage_sim.rate(game, system)
        assert abs(both - 0.004) < 1e-9, (
            f"Kin under a treaty should be 0.4% and reads {both:.4f}")
        assert both > 0.0, "the relief has taken the charge to nothing"
        return "outpost 2.0% · under a treaty 1.0% · Kin as well 0.4%"

    @check("the relief reaches the forecast, the counter and the purse")
    def _():
        # The reason the relief goes in `rate` and nowhere else. A discount the
        # market board knows about and the freight desk does not is the two-door
        # bug this project has found more often than any other.
        from ..sim import exchequer as exchequer_sim

        game = _ready("doors")
        for system in game.galaxy.systems:
            if system.port and system.market:
                market_sim.note_prices(game, system,
                                       game.rep.get(system.port.faction, 0),
                                       game.ship_stats.trade)
        quays = _quays_of(game, "charter")
        start = next(s for s in quays if s.market.stock)
        _stand_at(game, start)
        _sign(game, "charter")
        purse = exchequer_sim.purse(game, "charter")

        cid = _tradeable(game, start)
        forecast = wharfage_sim.due_on(game, start,
                                       market_sim.quote_buy(game, start, cid) * 30)
        was, banked = game.credits, purse.credits
        res = trade_sim.buy(game, cid, 30)
        assert res.get("ok") and res["due"] > 0, res
        assert abs(res["due"] - forecast) <= 1, (forecast, res["due"])
        assert abs((was - game.credits) - (res["paid"] + res["due"])) < 0.01
        assert abs((purse.credits - banked) - res["due"]) < 0.01, (
            "the relief came off the captain and not off the credit to the "
            "power granting it")
        # The freight desk's own forecast, at the same quay, under the same
        # instrument.
        runs = freight_sim.worth_flying(game, start, limit=3)
        checked = 0
        for run_, trip in runs:
            if not trip["dues"] or trip["tonnes"] < 5:
                continue
            target = game.galaxy.systems[run_.target_id]
            want = (wharfage_sim.due_on(game, start,
                                        run_.buy_here * trip["tonnes"])
                    + wharfage_sim.due_on(game, target,
                                          run_.pays * trip["tonnes"]))
            assert trip["dues"] == want, (trip["dues"], want)
            checked += 1
        return (f"a 30 t deal forecast {forecast} and was charged {res['due']}, "
                f"banked to the credit; {checked} freight runs agreed")

    @check("the gift is what they know and you do not")
    def _():
        # So it cannot be double-counted: a system of theirs you have already
        # charted is not part of the instrument, and signing a second time (if
        # anything ever let you) would hand over nothing.
        game = _ready("shrink", "freeholds")
        first = accord_sim.worth(game, "freeholds")
        assert first["charts"] >= 3, first
        theirs = next(s for s in game.galaxy.systems
                      if s.faction == "freeholds" and intel_sim.level(game, s) < 1)
        intel_sim.ensure(game).append(theirs.id)
        second = accord_sim.worth(game, "freeholds")
        assert second["charts"] == first["charts"] - 1, (
            f"charting one of their {first['charts']} systems yourself left the "
            f"gift at {second['charts']}")
        assert second["worth"] < first["worth"], (first, second)
        _sign(game, "freeholds")
        after = accord_sim.worth(game, "freeholds")
        assert after["charts"] == 0 and after["worth"] == 0, after
        assert after["signed"] is True
        assert not accord_sim.shared(game, "freeholds")
        line = accord_sim.charts_line(after)
        assert "add nothing" in line, line
        return (f"{first['charts']} systems worth {first['worth']:,}, "
                f"{second['charts']} after charting one myself, 0 after signing")

    @check("the paper is priced at what a broker would really take for it")
    def _():
        # The desk says "about N credits of broker's paper", and N had better be
        # what a broker takes. Comparing `accord._price` with `intel.chart_price`
        # would only prove the two agree; this buys one of the very systems in
        # the gift, out of the captain's own account, and takes the difference.
        game = _ready("brokered", "sanhedrin")
        told = accord_sim.worth(game, "sanhedrin")
        assert told["charts"] >= 2, told
        first = next(s for s in accord_sim.shared(game, "sanhedrin"))
        offer = intel_sim.chart_offer(game, first)
        was = game.credits
        res = intel_sim.buy_chart(game, first)
        assert res.get("ok"), res
        spent = was - game.credits
        assert spent == offer["price"] > 0, (spent, offer["price"])
        now = accord_sim.worth(game, "sanhedrin")
        assert now["charts"] == told["charts"] - 1, (told, now)
        assert told["worth"] - now["worth"] == spent, (
            f"the desk had that system in a gift worth {told['worth']:,}, "
            f"dropping to {now['worth']:,} once bought — a difference of "
            f"{told['worth'] - now['worth']:,} against {spent:,} actually paid")
        return (f"bought {first.name} from a broker for {spent:,}; the quoted "
                f"gift fell from {told['worth']:,} to {now['worth']:,}, exactly")

    @check("both screens say it: the desk before, the board after")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _ready("said", "freeholds")

        def _words(view) -> str:
            view.refresh()
            for _ in range(3):
                app.processEvents()
            return " ".join(lab.text() for lab in view.findChildren(QLabel)
                            if lab.text())

        told = accord_sim.worth(game, "freeholds")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("diplomacy")
        desk = win.views["diplomacy"]
        desk.focus = "freeholds"
        said = _words(desk)
        assert "Berthing" in said, f"the desk never names berthing: {said[:300]}"
        assert f"{told['charts']} system" in said, (
            f"the desk never says how many charts: {said[:300]}")
        assert f"{told['quays']} quays" in said, said[:300]

        # And the market board, once signed, says why its figure fell.
        quay = _quays_of(game, "freeholds")[0]
        _stand_at(game, quay)
        _sign(game, "freeholds")
        board = win.views["port"] if "port" in win.views else None
        win.go("port")
        board = win.views["port"]
        board.tab = "market"
        shown = _words(board)
        win.close()
        assert "berthing clause" in shown, (
            f"the board does not say why the charge fell: {shown[:400]}")
        found = re.search(r"takes (\d+\.\d)% of everything over this counter",
                          shown)
        assert found, shown[:400]
        charged = wharfage_sim.rate(game, quay)
        assert abs(float(found.group(1)) / 100.0 - charged) <= 0.0005, (
            f"the board says {found.group(1)}% and the counter charges "
            f"{charged:.3%}")
        return (f"the desk quotes {told['charts']} charts at {told['quays']} "
                f"quays; the board says {found.group(1)}% and names the clause")

    @check("the same instrument through either door")
    def _():
        # There are two ways to sign: propose one, or accept the one an envoy
        # brings. `data/diplomacy.py` records what happened the last time they
        # differed — proposing charged the signatory's enemies and accepting
        # charged nobody, so the way to sign for free was to wait to be asked.
        # The charts clause was one edit from being that bug in reverse.
        from ..core.rng import RNG
        from ..sim import approach as approach_sim

        seen = {}
        for door in ("proposed", "offered"):
            game = _ready("doors2", "concordat")
            quay = _quays_of(game, "concordat")[0]
            was_rate = wharfage_sim.rate(game, quay)
            told = accord_sim.worth(game, "concordat")
            # Standing held still on *both* paths: accepting an envoy's offer
            # grants `accept_rep` as well, and `wharfage.rate` reads standing,
            # so letting it land on one path only would measure courtship at one
            # door and berthing at the other.
            held = dict(game.rep)
            if door == "proposed":
                _sign(game, "concordat")
            else:
                envoy = approach_sim._build(game, "concordat", "treaty_offer",
                                            None, RNG("either"))
                game.envoy = envoy
                res = approach_sim.answer(game, envoy, "accept")
                assert res.get("ok"), res
                game.rep.update(held)
            assert dip.has_treaty(game, "concordat"), door
            seen[door] = (len(intel_sim.ensure(game)),
                          round(wharfage_sim.rate(game, quay) / was_rate, 6),
                          told["charts"])
        assert seen["proposed"][0] == seen["offered"][0] > 0, (
            f"proposing handed over {seen['proposed'][0]} charts and accepting "
            f"the identical instrument handed over {seen['offered'][0]}")
        assert seen["proposed"][1] == seen["offered"][1] < 1.0, seen
        return (f"both doors: {seen['proposed'][0]} charts and the same quay at "
                f"{seen['proposed'][1]:.2f} of its rate")

    @check("what an instrument is actually worth, power by power")
    def _():
        # Task #39's question asked of the treaty: at 30,000 credits and 180
        # days, is it a purchase or a courtesy? The answer is geography — the
        # power whose space you are sitting in has least to give.
        rows, dear = [], 0
        price = ACTIONS_BY_ID["treaty"].cost_credits
        for power in dip.POWERS:
            game = _ready("worth", power)
            told = accord_sim.worth(game, power)
            ported = [s for s in game.galaxy.systems if s.port]
            # What the berthing clause saves on one full hold at each of their
            # quays, as a floor on its worth — it is charged again on every
            # deal, for ever. And the count of quays where the charge actually
            # falls, against the count the offer puts on the screen: the
            # Freeholds' independent outposts fly their flag and take no due, so
            # a quay count read off the flag rather than off `wharfage.holder`
            # over-promises at one power in four and at no other.
            full = {s.id: wharfage_sim.due_on(game, s, 40_000) for s in ported}
            dip.ensure(game).treaties.append(power)
            under = {s.id: wharfage_sim.due_on(game, s, 40_000) for s in ported}
            dip.ensure(game).treaties.remove(power)
            fell = [s for s in ported if under[s.id] < full[s.id]]
            saved = sum(full[s.id] - under[s.id] for s in fell)
            assert saved > 0, f"{power}: berthing saves nothing anywhere"
            assert len(fell) == told["quays"], (
                f"{power}: the offer counts {told['quays']} quays and the "
                f"charge fell at {len(fell)}")
            if told["worth"] >= price:
                dear += 1
            rows.append(f"{power}: {told['charts']} charts worth "
                        f"{told['worth']:,} + {saved:,} a round of holds")
        assert dear >= 1, (
            f"no power's charts are worth the {price:,} the instrument costs — "
            "the clause is decoration")
        assert dear <= 3, (
            "every power's charts alone outvalue the price, which makes signing "
            "all four the obvious opening move rather than a decision")
        return " · ".join(rows)
