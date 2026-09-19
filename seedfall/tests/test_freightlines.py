"""Freight lines: a trading house earns only what the counters pay it.

Innovation 5. A house charters at a Station or Fleet Hub, puts haulers on
lines with a master each, and every trip trades through the real counters on
the sector's clock. Each check performs the act and measures it:

- the forecast is held to the mean of fifty seeded trips;
- a route saturates as lines stack on it;
- a lawless route loses more trips than a policed one, counted;
- the house's books reconcile with the purse, and a credit reaches it only
  from a sale `apply_sale` saw — equal prices earn nothing, and insurance
  never pays out more than it took;
- standing from line trade runs through the counter's rule and a cap;
- an unpaid master walks; a hauler on a line is away;
- a house mid-trip survives a restart, and draws no luck from the chronicle;
- every preview the panel shows is what the act does.
"""

from __future__ import annotations

import copy
import json
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from ..core.rng import RNG
from ..data.freightlines import INSURANCE_LOADING, LINE_REGARD_CAP
from ..sim import consorts
from ..sim import freightlines as lines_sim
from ..sim import lineforecast, lineledger, lineroute, linetrips
from ..sim import masters as masters_sim
from ..sim import shipyard
from ..world import economy
from . import lines_kit as kit
from .efficacy import Lever, verdict
from .harness import Suite

ROOT = Path(__file__).resolve().parents[2]


def _fifty(game, line, walk: bool):
    """Fifty seeded trips from one state: (cash, cycle days, outcome) each."""
    out = []
    for k in range(50):
        twin, sailed = kit.one_trip(game, line, k, walk=k if walk else 0)
        out.append((kit.trip_cash(twin, sailed),
                    sailed.last_day - sailed.started, sailed.last))
    return out


def run(suite: Suite) -> None:
    check = suite.check
    game, hull, master = kit.house()
    line, told = kit.route(game, hull, master)
    first = told["first"]

    @check("the forecast is what fifty seeded trips clear")
    def _():
        # With the market's own dice held at their mean the only chance left
        # is the trip's own, so a completed trip must clear what the forecast
        # says one clears. Measured on the fixture's trehalose route: all 50
        # completed, mean 13,066 against a forecast 13,060, and 34.4 days
        # against 34.2.
        from ..core import sectortime
        live = sectortime.tick_market
        sectortime.tick_market = (lambda m, n, _r, level=1: economy.tick_market(
            m, n, lineforecast.MEAN, level))
        try:
            held = _fifty(game, line, walk=False)
        finally:
            sectortime.tick_market = live
        done = [c for c, _d, fate in held if fate in ("done", "delayed")]
        mean = statistics.mean(done)
        assert abs(mean - first["clear"]) <= 0.01 * first["outlay"], (
            f"completed trips cleared {mean:,.0f}; the forecast said "
            f"{first['clear']:,.0f}")
        days = statistics.mean(d for _c, d, _f in held)
        assert abs(days - first["cycle"]) <= 1.0, (days, first["cycle"])
        # And with the dice live. The walk is noise about nought in supply,
        # but a price is convex in supply, so noise can lift the mean a
        # counter pays: measured -0.9% of the cargo's cost on this route, and
        # +1.9% on a 58-day survey-set run. Held to -1% .. +4% of the cargo:
        # the forecast may say a little less than the dice give, not more.
        loose = _fifty(game, line, walk=True)
        done_l = [c for c, _d, fate in loose if fate in ("done", "delayed")]
        drift = (statistics.mean(done_l) - first["clear"]) / first["outlay"]
        assert -0.01 <= drift <= 0.04, f"live dice {drift:+.2%} of outlay"
        lost = sum(1 for _c, _d, f in held + loose
                   if f not in ("done", "delayed"))
        return (f"completed trips {mean:,.0f} vs forecast "
                f"{first['clear']:,.0f} at mean dice; {drift:+.1%} of the "
                f"cargo's cost with live dice; {lost}/100 trips lost, "
                f"{told['p_cargo']:.1%} forecast; {days:.1f} d vs "
                f"{first['cycle']:.1f}")

    @check("a route saturates as lines stack on it")
    def _():
        # Five lines on one route push its prices until a trip clears less
        # than half what one line's did — the house's profit a trip, wages
        # and upkeep in, since a master will not sail a closed spread and the
        # lines that wait are paid to wait. Measured over 180 days: one line,
        # 5 trips at 8,201; five lines, 7 trips between them at 2,897, and
        # the route as a whole clearing 20,000 against one line's 41,000.
        per_trip, whole = {}, {}
        for count in (1, 5):
            g, h, m = kit.house(deposit=600_000)
            paper, _told = kit.route(g, h, m)
            hulls = [h] + [kit.hauler(g) for _ in range(count - 1)]
            crew = [m] + kit.hire(g, count - 1)
            opened = []
            for hl, ms in zip(hulls, crew):
                res = lines_sim.open_line(g, lines_sim.draft(
                    g, hl.uid, ms.id, paper.origin, paper.dest, paper.good,
                    9999))
                assert res["ok"], res
                opened.append(res["line"])
            kit.wait(g, 180)
            trips = sum(l.trips for l in opened)
            cleared = sum(kit.done_net(g, l) for l in opened)
            per_trip[count], whole[count] = cleared / trips, cleared
        assert per_trip[5] < 0.5 * per_trip[1], per_trip
        assert whole[5] < whole[1], whole
        return (f"a trip clears {per_trip[1]:,.0f} with one line and "
                f"{per_trip[5]:,.0f} with five; the route {whole[1]:,.0f} "
                f"against {whole[5]:,.0f} in 180 days")

    @check("a lawless route loses more trips than a policed one, counted")
    def _():
        g, h, m = kit.house()
        rough, rough_told = kit.route(g, h, m, lawless=True)
        calm, calm_told = kit.route(g, h, m)
        counted = {}
        for name, paper in (("lawless", rough), ("policed", calm)):
            plan = lineroute.route_for(g, paper)
            lost = sum(1 for k in range(1000) if lineroute.roll(
                RNG(f"{g.seed}:line:7:{k}"), plan["risk"])["fate"] != "done")
            counted[name] = lost / 1000
        # The targets: 5-15% of trips on a lawless route, under 2% policed.
        assert 0.05 <= counted["lawless"] <= 0.15, counted
        assert counted["policed"] < 0.02, counted
        # And the roll counted is the roll a sailing makes: same key, same
        # dice, same fate.
        twin, sailed = kit.one_trip(g, rough, 3)
        plan = lineroute.route_for(g, rough)
        rolled = lineroute.roll(RNG(f"{g.seed}:line:{sailed.id}:3"),
                                plan["risk"])["fate"]
        assert sailed.fate == rolled, (sailed.fate, rolled)
        return (f"lawless {counted['lawless']:.1%} "
                f"(forecast {rough_told['p_cargo']:.1%}), policed "
                f"{counted['policed']:.1%} (forecast "
                f"{calm_told['p_cargo']:.1%}) of 1,000 seeded trips each")

    @check("the house's books reconcile with the purse; nothing is conjured")
    def _():
        # Two chronicles, one with a house: every credit of difference in
        # the purse is a row on the house's books.
        sales = []
        real = economy.apply_sale

        def witnessed(market, cid, units):
            sales.append(units)
            real(market, cid, units)
        g, _h, _m = kit.house()
        bare = copy.deepcopy(g)
        bare.house = None
        start = (g.house.purse_in, g.house.purse_out)
        paper, _t = kit.route(g, _h, _m)
        lines_sim.open_line(g, paper)
        linetrips.apply_sale = witnessed
        try:
            for chronicle in (g, bare):
                kit.wait(chronicle, 240)
        finally:
            linetrips.apply_sale = real
        books = lineledger.reconcile(g, g.house)
        assert books["balanced"] and books["purse_ok"], books
        gap = g.credits - bare.credits
        moved = (books["purse_in"] - start[0]) - (books["purse_out"] - start[1])
        assert abs(gap - moved) < 0.01, (gap, moved, books)
        rows = lineledger.lifetime(g.house)
        assert set(rows) <= {"deposit", "sweep", "withdraw", "sale",
                             "purchase", "fuel", "wharfage", "distraint",
                             "premium", "claim", "repair", "upkeep", "wages",
                             "hire", "severance", "charter"}, rows
        assert sales and rows.get("sale", 0) > 0, "no sale was witnessed"
        # Equal prices, after wharfage, earn nothing: the counter's quote at
        # the far end made to equal what the home port charges. A master will
        # not sail it; made to, the till loses on every trip.
        from ..sim import market as market_sim
        quote, judged = market_sim.quote_sell, linetrips.judged
        flats = []
        for forced in (False, True):
            g2, h2, m2 = kit.house()
            paper2, _t2 = kit.route(g2, h2, m2)
            origin = g2.galaxy.systems[paper2.origin]
            market_sim.quote_sell = lambda gm, sy, cid: market_sim.quote_buy(
                gm, origin, cid)
            if forced:
                linetrips.judged = lambda *_a: 1.0
            try:
                opened2 = lines_sim.open_line(g2, paper2)["line"]
                kit.wait(g2, 200)
            finally:
                market_sim.quote_sell, linetrips.judged = quote, judged
            flats.append((opened2.trips, lineledger.net(
                lineledger.lifetime(g2.house, opened2.id), trading_only=True)))
        assert flats[0] == (0, 0.0), f"a master sailed equal prices: {flats[0]}"
        assert flats[1][0] > 0 and flats[1][1] < 0, flats[1]
        flat = flats[1][1]
        return (f"over 240 days the purse is {gap:,.0f} ahead, and the house "
                f"swept exactly that across; {len(sales)} sales witnessed by "
                f"apply_sale; at equal prices no master sails, and one made "
                f"to lost {-flat:,.0f} in {flats[1][0]} trips")

    @check("insurance never pays out more than it takes")
    def _():
        g, h, m = kit.house()
        rough, _t = kit.route(g, h, m, lawless=True)
        plan = lineroute.route_for(g, rough)
        cargo = 50_000.0
        premium = linetrips.insurance(g, rough, h, plan["risk"], cargo)
        worth = linetrips.hull_worth(h)
        claims = 0.0
        # Five thousand sailings, because a loss is rare: over a thousand the
        # count of one key range ran at twice its rate by chance alone.
        for k in range(5000):
            fate = lineroute.roll(RNG(f"{g.seed}:line:9:{k}"),
                                  plan["risk"])["fate"]
            if fate != "done":
                claims += cargo + (worth if fate == "lost" else 0.0)
        assert claims < 5000 * premium, (claims, premium)
        return (f"5,000 seeded sailings of a lawless route: premiums "
                f"{5000 * premium:,.0f}, claims {claims:,.0f} (loading "
                f"{INSURANCE_LOADING:g})")

    @check("standing from a line is the counter's rule, capped per period")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)
        power = g.galaxy.systems[paper.dest].port.faction
        before = g.rep.get(power, 0.0)
        lines_sim.open_line(g, paper)
        kit.wait(g, 85)
        gained = g.rep.get(power, 0.0) - before
        assert 0 < gained <= LINE_REGARD_CAP + 1e-9, gained
        # Selling a counter its own goods back is not trade, for a line as
        # for a captain: the far counter sold the house these tonnes itself.
        dest = g.galaxy.systems[paper.dest]
        from ..sim import trade as trade_sim
        trade_sim._bought(g, dest, paper.good, 9_999)
        house = g.house
        house.regard.clear()
        flat = g.rep.get(power, 0.0)
        linetrips.sell(g, house, g.house.lines[0], dest, paper.good, 50, 100)
        assert g.rep.get(power, 0.0) == flat, "churned tonnes moved standing"
        return f"+{gained:.2f} in 85 days (cap {LINE_REGARD_CAP:g}); churn 0"

    @check("an unpaid master walks, and the line stands down")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)
        lines_sim.open_line(g, paper)
        opened = g.house.lines[0]
        g.house.sweep = False
        for _month in range(3):
            # The account is emptied the day before every payroll, so the
            # line's own sales cannot meet it.
            kit.wait(g, g.house.next_settle - g.day - 1)
            lineledger.to_purse(g, g.house, g.house.account, "withdraw")
            kit.wait(g, 2)
            if m not in g.house.masters:
                break
        assert m not in g.house.masters and not opened.active, (
            m.loyalty, m.owed, opened.phase)
        assert h.line_id is None and m.line_id is None
        said = [t for _d, t, _k in g.log if "has quit the house" in t]
        assert said, "the chronicle did not hear it"
        return f"walked with {m.owed:,.0f} owed; the line stood down"

    @check("a hauler on a line is away: no escort, no flag, no breaker")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)
        lines_sim.open_line(g, paper)
        h.docked_at = g.location_id          # even alongside the captain
        ok, why = consorts.can_sail(g, h)
        assert not ok and "freight line" in why, why
        ok2, why2 = consorts.can_take_command(g, h)
        assert not ok2 and "freight line" in why2, why2
        scrapped = shipyard.scrap(g, h)
        assert not scrapped["ok"] and h in g.fleet, scrapped
        return why

    @check("a used hauler costs what the yard quoted, and scraps for less")
    def _():
        from ..sim import haulers as haulers_sim
        g, _h, _m = kit.house()
        terms = haulers_sim.used_terms(g, "tender")
        before, fleet = g.credits, len(g.fleet)
        bought = haulers_sim.buy_used(g, "tender")
        assert bought["ok"] and len(g.fleet) == fleet + 1, bought
        assert abs(before - g.credits - terms["price"]) < 0.01
        ship = bought["ship"]
        scrap = shipyard.scrap_value(ship)
        assert scrap < terms["price"], (scrap, terms["price"])
        ok, why = haulers_sim.can_haul(g, ship)
        assert ok, why
        return (f"a used TENDER at {terms['price']:,}, quoted and charged; "
                f"a breaker pays {scrap:,} for her")

    @check("a house with a line mid-trip survives a restart")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)
        lines_sim.open_line(g, paper)
        kit.wait(g, 9)
        opened = g.house.lines[0]
        assert opened.phase == "out", opened.phase
        here = copy.deepcopy(g)
        kit.wait(here, 60)
        save = Path(tempfile.mkdtemp(prefix="seedfall-lines-")) / "save.json"
        from ..core import save as save_mod
        assert save_mod.write(g.to_save(), save)
        code = (
            "import json\nfrom seedfall.core.state import load_game\n"
            "from seedfall.tests import lines_kit as kit\n"
            "g = load_game()\nl = g.house.lines[0]\n"
            "was = [l.phase, l.due, round(g.house.account, 2)]\n"
            "kit.wait(g, 60)\n"
            "print(json.dumps({'was': was, 'trips': l.trips, "
            "'acct': round(g.house.account, 2), 'credits': round(g.credits, 2)}))")
        env = dict(os.environ, SEEDFALL_SAVE=str(save),
                   QT_QPA_PLATFORM="offscreen")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True,
                              text=True, env=env, cwd=str(ROOT), timeout=300)
        rows = [r for r in proc.stdout.splitlines() if r.startswith("{")]
        assert rows, proc.stderr[-800:]
        got = json.loads(rows[-1])
        assert got["was"] == ["out", opened.due, round(g.house.account, 2)]
        assert got["trips"] == here.house.lines[0].trips
        assert got["acct"] == round(here.house.account, 2), (got, here.house.account)
        return (f"out, due day {opened.due}; 60 days on in a fresh process: "
                f"{got['trips']} trip(s), account {got['acct']:,.0f} — the "
                "same as never having stopped")

    @check("a house draws no luck from the chronicle")
    def _():
        g, h, m = kit.house()
        bare = copy.deepcopy(g)
        bare.house = None
        paper, _t = kit.route(g, h, m)
        lines_sim.open_line(g, paper)
        for chronicle in (g, bare):
            kit.wait(chronicle, 120)
        assert g.rng_seed == bare.rng_seed, "a trip drew from the day's stream"
        return f"{g.house.lines[0].trips} trips; the day's stream untouched"

    @check("the Cartel's register stays fresh at both ends of a line")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)
        lines_sim.open_line(g, paper)
        kit.wait(g, 200)
        from ..sim import market as market_sim
        ages = [market_sim.age_of(g, end) for end in (paper.origin, paper.dest)]
        assert all(a is not None and a < 60 for a in ages), ages
        return f"quotes {ages[0]} and {ages[1]} days old on day {g.day}"

    @check("what the panel previews is what the act does")
    def _():
        g, h, m = kit.house()
        terms = lines_sim.charter_terms(g)          # a house exists: refused
        assert not terms["ok"] and terms["why"]
        paper, told = kit.route(g, h, m)
        quoted = lines_sim.open_terms(g, paper)["forecast"]["first"]
        res = lines_sim.open_line(g, paper)
        rows = lineledger.lifetime(g.house, res["line"].id)
        assert abs(-rows["purchase"] - quoted["outlay"]) < 0.01, (rows, quoted)
        assert res["line"].paid > 0 and g.house.lines[0].phase == "out"
        spare = kit.hire(g, 1)[0]
        cost = masters_sim.dismiss_terms(g, spare)["cost"]
        was = g.house.account
        masters_sim.dismiss(g, spare)
        assert abs(was - g.house.account - cost) < 0.01
        return (f"{quoted['tonnes']} t at {quoted['price']:,}: "
                f"{quoted['outlay']:,.0f} quoted and paid; a pay-off of "
                f"{cost:,} charged {cost:,}")

    @check("it matters who is master")
    def _():
        g, h, m = kit.house()
        paper, _t = kit.route(g, h, m)

        def clears() -> float:
            return lineforecast.forecast(g, paper)["first"]["clear"]
        lever = Lever("master-margin", "a master's skill is in the margin",
                      patch=(masters_sim, "slip",
                             lambda _m: masters_sim.MAX_SLIP),
                      probe=clears, direction="lower")
        ok, said = verdict(lever)
        assert ok, said
        return said.split("; ")[0]

    @check("the Trading house tab draws, and its buttons are the sim's")
    def _():
        from . import qtkit
        g, h, m = kit.house()
        win = qtkit.main_window(g, (1040, 680), confirm=True)
        win.go("empire")
        view = win.views["empire"]
        view.tab = "house"
        view.refresh()
        from ..ui.house_dialog import NewLineDialog, describe
        dlg = NewLineDialog(view)
        terms = dlg.update_forecast()
        assert dlg.told.text() == describe(g, terms)
        assert terms["ok"], terms
        paper = dlg.draft()
        dlg.commit()
        assert dlg.opened is not None and dlg.opened.good == paper.good
        dlg.deleteLater()
        win.close()
        return f"opened {paper.good} from the dialog, as its forecast said"
