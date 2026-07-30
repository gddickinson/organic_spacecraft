"""What the quay takes, and whether anyone can tell.

The purse cycle connected the powers to the sector's own trade and left the
captain's out: a fortune could be made over the counter at a Fleet Hub the
Charter built and maintains without a credit reaching the Charter. `sim/wharfage.py`
is that connection — a share of the value crossing the quay, taken by whoever
holds it, on the way in and on the way out.

The claims:

- **Nothing is invented and nothing is lost.** What leaves the captain's account
  arrives in the holder's purse, to the credit, buying and selling.
- **The board names the rate the counter charges.** Read off the rendered screen
  and applied to a real deal, not read out of the module that charges it.
- **A free port is free.** No cut at an independent freehold, and none at a Free
  Port of the captain's own — which is the same rule `exchequer.holdings` already
  applies from the other side.
- **Standing is worth money**, and **the size of the berth is worth money**.
- **The freight desk counts both quays**, because a forecast that leaves out a
  cost the till takes is a forecast that cannot be met.
- **A purse spent to the last credit can still pay the due.**
- **Off the books pays nothing.** The smuggler's edge, in money, for the first
  time.
- **And what it costs to trade for a living** — measured over the runs the desk
  actually recommends, because "a small rate" is not the same as "a small
  change".
"""

from __future__ import annotations

import re

from ..core.state import new_game
from ..data import wharfage as tuning
from ..sim import customs as customs_sim
from ..sim import exchequer as exchequer_sim
from ..sim import freight as freight_sim
from ..sim import market as market_sim
from ..sim import trade as trade_sim
from ..sim import wharfage as wharfage_sim
from .harness import Suite


def _at_a_quay(seed: str = "wharf"):
    game = new_game(seed)
    game.credits = 400_000
    return game, game.system


def _tradeable(game, system) -> str:
    """A good this quay both sells and buys, so one hold can do both legs."""
    return next(c for c in system.market.stock
                if market_sim.quote_buy(game, system, c)
                and market_sim.quote_sell(game, system, c))


def _stand_at(game, system):
    """Put the captain's hull at `system` and write down its prices."""
    game.location_id = system.id
    market_sim.note_prices(game, system,
                           game.rep.get(system.port.faction, 0),
                           game.ship_stats.trade)


def _quays(game, level: int, independent: bool = False) -> list:
    return [s for s in game.galaxy.systems
            if s.port and s.market and s.port.level == level
            and bool(s.port.independent) == independent]


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the captain pays, the holder of the quay receives")
    def _():
        # The whole point, and the reason `collect` moves both sides in one
        # function: a fee deducted in one place and credited in another can be
        # deducted and credited for different amounts.
        game, _ = _at_a_quay("conserve")
        deals = paid = got = 0
        for system in _quays(game, 1)[:6] + _quays(game, 3)[:3]:
            _stand_at(game, system)
            who = wharfage_sim.holder(game, system)
            if who is None:
                continue
            p = exchequer_sim.purse(game, who)
            cid = _tradeable(game, system)
            for act in ("buy", "sell"):
                if act == "sell":
                    game.ship.cargo[cid] = 60
                credits_before, purse_before = game.credits, p.credits
                res = (trade_sim.buy(game, cid, 40) if act == "buy"
                       else trade_sim.sell(game, cid, 40))
                if not res.get("ok"):
                    continue
                moved = credits_before - game.credits if act == "buy" else \
                    game.credits - credits_before
                goods = res["paid"] if act == "buy" else res["took"]
                want = goods + res["due"] if act == "buy" else goods - res["due"]
                assert abs(moved - want) < 0.01, (
                    f"{system.name}: the captain's account moved {moved} on a "
                    f"{act} of {goods} with a due of {res['due']}")
                assert abs((p.credits - purse_before) - res["due"]) < 0.01, (
                    f"{system.name}: {res['due']} taken off the captain and "
                    f"{p.credits - purse_before} into {who}'s purse")
                paid += res["due"]
                got += p.credits - purse_before
                deals += 1
        assert deals >= 8, deals
        assert paid > 0, "not one deal paid a due"
        assert abs(paid - got) < 0.01, (paid, got)
        return (f"{deals} deals across {len(_quays(game, 1)[:6]) + 3} quays, "
                f"{paid:,} taken and {got:,} banked, to the credit")

    @check("the board names the rate, and the counter charges that rate")
    def _():
        # The percentage is read off the *rendered* screen and applied to a real
        # deal. Reading `wharfage.rate` here would only prove the module agrees
        # with itself, which is the mistake the tripwire exists to catch.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, system = _at_a_quay("named")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("port")
        view = win.views["port"]
        view.tab = "market"
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()

        found = re.search(r"takes (\d+\.\d)% of everything over this counter",
                          said)
        assert found, f"the market board never names the charge: {said[:400]}"
        shown = float(found.group(1)) / 100.0
        cid = _tradeable(game, system)
        res = trade_sim.buy(game, cid, 200)
        assert res.get("ok") and res["due"] > 0, res
        want = shown * res["paid"]
        # The sentence carries one decimal place, so half of a tenth of a per
        # cent of the deal is honest rounding rather than a disagreement.
        slack = 0.0005 * res["paid"] + 1
        assert abs(res["due"] - want) <= slack, (
            f"the board says {shown:.3%} of {res['paid']:,}, which is "
            f"{want:.1f}, and the counter took {res['due']}")
        return (f"the board says {found.group(1)}%; a {res['paid']:,} deal was "
                f"charged {res['due']}, within {slack:.1f} of it")

    @check("a free port is free, both kinds")
    def _():
        # `exchequer.holdings` will not pay a power for an independent freehold
        # or for a Free Port the captain built. This is the same rule from the
        # other side, so a captain is never charged rent on their own quay.
        from ..sim import colony as colony_sim

        game, _ = _at_a_quay("free")
        told = []
        free = _quays(game, 1, independent=True)
        assert free, "no independent freehold in the sector to stand on"
        mine = next(s for s in game.galaxy.systems if s.port is None)
        colony_sim.open_harbour(game, mine)
        assert mine.port.player_built

        before = sum(exchequer_sim.purse(game, p).credits
                     for p in ("charter", "concordat", "freeholds", "sanhedrin"))
        for system in (free[0], mine):
            _stand_at(game, system)
            assert wharfage_sim.holder(game, system) is None, system.port.name
            assert wharfage_sim.rate(game, system) == 0.0
            cid = _tradeable(game, system)
            game.ship.cargo[cid] = 40
            bought = trade_sim.buy(game, cid, 30)
            sold = trade_sim.sell(game, cid, 30)
            assert not bought.get("due"), bought
            assert not sold.get("due"), sold
            line = wharfage_sim.line(game, system)
            assert line.startswith("No wharfage here"), line
            told.append(line)
        after = sum(exchequer_sim.purse(game, p).credits
                    for p in ("charter", "concordat", "freeholds", "sanhedrin"))
        assert abs(after - before) < 0.01, (
            f"{after - before} reached a purse from a free port")
        return " · ".join(told)

    @check("standing is worth money at the counter, not just at the price")
    def _():
        # The widest lever on the page, and the reason the charge is a diplomacy
        # number rather than a tax: the same trade at the same quay, once as
        # somebody they would not miss and once as kin.
        game, system = _at_a_quay("standing")
        fac = system.port.faction
        cid = _tradeable(game, system)
        seen = {}
        for name, rep in (("Hunted", -100.0), ("Neutral", 0.0), ("Kin", 100.0)):
            game.rep[fac] = rep
            seen[name] = wharfage_sim.due_on(game, system, 10_000)
        assert seen["Hunted"] > seen["Neutral"] > seen["Kin"] > 0, seen
        spread = seen["Hunted"] / seen["Kin"]
        assert 3.5 <= spread <= 4.5, (
            f"the Kin-to-Hunted spread is {spread:.2f}, and the relief share "
            f"says it should be about 4: {seen}")

        # And it is the real till, not just the helper.
        game.rep[fac] = 100.0
        kin = trade_sim.buy(game, cid, 60)
        game.rep[fac] = -100.0
        hunted = trade_sim.buy(game, cid, 60)
        assert hunted["due"] > kin["due"], (kin, hunted)
        return (f"on 10,000: Hunted {seen['Hunted']}, Neutral {seen['Neutral']}, "
                f"Kin {seen['Kin']} — a factor of {spread:.1f}")

    @check("a bigger berth takes a bigger cut")
    def _():
        game, _ = _at_a_quay("levels")
        rates = {}
        for level in (1, 3):
            for system in _quays(game, level):
                if wharfage_sim.holder(game, system) is None:
                    continue
                game.rep[system.port.faction] = 0.0
                rates[level] = wharfage_sim.rate(game, system)
                break
        assert 1 in rates and 3 in rates, rates
        step = rates[3] / rates[1]
        assert step > 1.2, (
            f"an outpost charges {rates[1]:.3%} and a Fleet Hub {rates[3]:.3%} "
            "— the ladder is doing nothing")
        return (f"outpost {rates[1]:.2%} · Fleet Hub {rates[3]:.2%} at the same "
                f"standing, a factor of {step:.2f}")

    @check("the freight desk forecasts the dues at both quays")
    def _():
        # A desk that quoted the spread and the fuel and not the wharfage would
        # be naming a figure the counter cannot pay. The near quay's due can be
        # checked exactly, because it is taken before the hull leaves.
        game, _ = _at_a_quay("desk")
        for system in game.galaxy.systems:
            if system.port and system.market:
                market_sim.note_prices(game, system,
                                       game.rep.get(system.port.faction, 0),
                                       game.ship_stats.trade)
        flown = 0
        for start in game.galaxy.systems:
            if not (start.port and start.market):
                continue
            _stand_at(game, start)
            best = freight_sim.worth_flying(game, start, limit=1)
            if not best:
                continue
            run_, trip = best[0]
            if trip["tonnes"] < 5 or not trip["dues"]:
                continue
            target = game.galaxy.systems[run_.target_id]
            near = wharfage_sim.due_on(game, start, run_.buy_here * trip["tonnes"])
            far = wharfage_sim.due_on(game, target, run_.pays * trip["tonnes"])
            assert trip["dues"] == near + far, (
                f"the desk forecast {trip['dues']} and the two quays come to "
                f"{near} + {far}")
            res = trade_sim.buy(game, run_.commodity, int(trip["tonnes"]))
            assert res.get("ok"), res
            if near:
                # Per tonne, because the hold may take fewer than the forecast
                # asked for. The claim is that the desk forecast the same *rate*
                # at the same quay, not that it guessed the tonnage.
                want = near / trip["tonnes"]
                paid = res["due"] / res["units"]
                assert abs(paid - want) <= max(0.05, want * 0.05), (
                    f"the desk forecast {want:.2f} a tonne in dues at "
                    f"{start.port.name} and the counter took {paid:.2f}")
            flown += 1
            if flown >= 3:
                break
        assert flown >= 2, f"only {flown} runs to check"
        return (f"{flown} recommended runs, each forecasting both quays' dues "
                "and charged what it forecast at the near one")

    @check("a purse spent to the last credit can still pay the due")
    def _():
        # `buy` used to size the purchase against the posted price alone, so a
        # hold filled with every credit left nothing for the charge at the end
        # of it — an approach ordering burns it has no mass for, in a counting
        # house.
        game, system = _at_a_quay("skint")
        cid = _tradeable(game, system)
        price = market_sim.quote_buy(game, system, cid)
        game.credits = price * 20                     # exactly twenty tonnes
        res = trade_sim.buy(game, cid, 20)
        assert res.get("ok"), res
        assert game.credits >= 0, (
            f"{game.credits} left after a purchase sized to the last credit")
        assert res["units"] < 20, (
            f"bought all {res['units']} tonnes and paid a due of {res['due']} "
            "out of a purse that held exactly the goods")
        assert res["due"] > 0
        return (f"a purse holding exactly 20 t bought {res['units']} and paid "
                f"the {res['due']} due, with {game.credits:.0f} left")

    @check("off the books pays no dues")
    def _():
        game, _ = _at_a_quay("quiet")
        found = None
        for system in game.galaxy.systems:
            if not (system.port and system.market):
                continue
            _stand_at(game, system)
            reg = customs_sim.regime(system.port.faction)
            for cid in (reg.outlaws if reg else ()):
                if customs_sim.premium(game, system.port.faction, cid):
                    found = (system, cid)
                    break
            if found:
                break
        assert found, "nowhere in the sector deals off the books"
        system, cid = found
        game.ship.cargo[cid] = 40
        purses = {p: exchequer_sim.purse(game, p).credits
                  for p in ("charter", "concordat", "freeholds", "sanhedrin")}
        res = customs_sim.sell_quietly(game, cid)
        assert res.get("ok"), res
        for power, was in purses.items():
            now = exchequer_sim.purse(game, power).credits
            assert abs(now - was) < 0.01, (
                f"{res['took']} sold off the books and {now - was} of it "
                f"reached {power}'s purse")
        return (f"{res['took']:,} off the books at {system.port.name}, "
                "and not a credit of it declared")

    @check("what a trading career actually pays in dues")
    def _():
        # The measurement task #100 asked for: not "is the rate small" but "what
        # does it take out of the runs a captain is actually told to fly". Over
        # six sectors, ranked by the desk's own `worth_flying`.
        rows = []
        for seed in ("w1", "w2", "w3", "w4", "w5", "w6"):
            game = new_game(seed)
            game.credits = 120_000
            for system in game.galaxy.systems:
                if system.port and system.market:
                    market_sim.note_prices(game, system,
                                           game.rep.get(system.port.faction, 0),
                                           game.ship_stats.trade)
            for system in game.galaxy.systems[:14]:
                if not (system.port and system.market):
                    continue
                _stand_at(game, system)
                for _run, trip in freight_sim.worth_flying(game, system, limit=3):
                    clear = trip["net"] + trip["dues"]
                    if clear > 0:
                        rows.append((trip["dues"], clear, system.port.level))
        assert len(rows) >= 8, len(rows)
        share = sum(r[0] for r in rows) / sum(r[1] for r in rows)
        assert 0.08 <= share <= 0.25, (
            f"the quays take {share:.1%} of what a recommended run clears — "
            "task #66 records that surveying is already break-even, and this "
            "is the number that decides whether trading joins it")
        small = [r for r in rows if r[2] == 1]
        big = [r for r in rows if r[2] > 1]
        note = ""
        if small and big:
            lo = sum(r[0] for r in small) / sum(r[1] for r in small)
            hi = sum(r[0] for r in big) / sum(r[1] for r in big)
            assert lo < hi, (
                f"loading at an outpost costs {lo:.1%} and at a bigger berth "
                f"{hi:.1%} — there is no reason to prefer the small quay")
            note = f"; {lo:.0%} loading at an outpost against {hi:.0%} at a station"
        return (f"{len(rows)} recommended runs across 6 sectors: the two quays "
                f"take {share:.1%} of what one clears{note}")

    @check("the charge is pinned to the constants that set it")
    def _():
        # Against the figures written here, never against the constants under
        # test — the mistake `tests/tripwire.py` exists to stop.
        game, _ = _at_a_quay("pinned")
        system = next(s for s in _quays(game, 1)
                      if wharfage_sim.holder(game, s) is not None)
        game.rep[system.port.faction] = 0.0
        assert abs(wharfage_sim.rate(game, system) - 0.02) < 1e-9, (
            f"an outpost at neutral standing charges "
            f"{wharfage_sim.rate(game, system):.4f}, and the base is 2%")
        game.rep[system.port.faction] = 35.0          # half way to full relief
        assert abs(wharfage_sim.rate(game, system) - 0.014) < 1e-9, (
            f"half way to Kin should be 1.4% and is "
            f"{wharfage_sim.rate(game, system):.4f}")
        assert tuning.RELIEF_AT == 70.0, (
            "relief is supposed to arrive with the Kin band, which begins at 70")
        hub = next(s for s in _quays(game, 3)
                   if wharfage_sim.holder(game, s) is not None)
        game.rep[hub.port.faction] = 0.0
        assert abs(wharfage_sim.rate(game, hub) - 0.03) < 1e-9, (
            f"a Fleet Hub at neutral standing should be 3% and is "
            f"{wharfage_sim.rate(game, hub):.4f}")
        return ("outpost 2.0% · half way to Kin 1.4% · Fleet Hub 3.0%, all at "
                "the figures written in the check")
