"""Licensing a process, measured at the counter it changes.

The tech tree had sixty-two nodes and one economic effect — `trade`, a haggling
bonus on the price the captain is quoted. Nothing anybody could learn changed
what a market held or what a port could make.

Every claim here is measured by licensing a process and then going and looking at
the prices, rather than by asserting the multiplier in the table that set it:

- **the buyer's treasury pays, and the captain gets exactly that**;
- **the gate agrees with the act** for every process against every power;
- **the industry comes up and the price comes down**, and stays down;
- **the forecast is where the market actually settles** — it is a dry run
  through the same pricing the till uses, not a second formula;
- **it costs the captain at that counter**, which is the whole trade;
- **a berth built afterwards comes up with the industry already running**;
- and **a good a port does not trade stays untraded**, which is the regression
  check for a compatibility shim that was putting contraband on sale at every
  port in the sector one day into every chronicle.
"""

from __future__ import annotations

from statistics import mean

from ..core.state import new_game
from ..data.industry import (ILLICIT_COST, LICENSEE_GAIN, MIN_STANDING,
                             OPENED_SUPPLY, PROCESSES, RIVAL_COST, SECOND_HAND,
                             WORTH_PER_POINT)
from ..data.tech import TECH_BY_ID
from ..sim import diplomacy as dip
from ..sim import exchequer as ex
from ..sim import industry as ind
from ..sim import market as market_sim
from ..world.economy import buy_price, sell_price
from .harness import Suite

#: A captain who has done the work: every process in hand, and money enough that
#: the powers are the only constraint.
ALL = [p.tech for p in PROCESSES]


def _ready(seed: str, years: float = 2.0, step: int = 5):
    """A chronicle far enough along that the treasuries can afford things."""
    game = new_game(seed)
    game.research.unlocked = list(set(game.research.unlocked) | set(ALL))
    game.recompute()
    for _ in range(int(years * 365 / step)):
        game.advance_days(step)
    return game


def _settle(game, days: int = 365, step: int = 5) -> None:
    for _ in range(days // step):
        game.advance_days(step)


def _steady(game, systems, cid: str) -> list:
    """The berths where this good is not under a live shock.

    An industry is a permanent change in what a place *makes*; a shock is a
    temporary change in what it *costs*, and the two are deliberately kept apart
    (`world/economy.Stock`). Measuring an industry across a port with a strike on
    means measuring both at once: the first draft of the check below did exactly
    that and read a 6% fall where four of the five berths had fallen 11% — the
    fifth had a strike, and its price had gone *up* by fifteen per cent.
    """
    return [s for s in systems if s.market is not None
            and not [k for k in market_sim.at(game, s.id) if k.commodity == cid]]


def _price(game, systems, cid: str) -> float:
    got = [buy_price(s.market, cid, 0) for s in systems if s.market]
    got = [p for p in got if p]
    return mean(got) if got else 0.0


def run(suite: Suite) -> None:
    check = suite.check

    @check("a licence is paid out of the buyer's treasury, to the credit")
    def _():
        game = _ready("lic-pay")
        process = ind.process_of("separation")
        buyer = ind.best_buyer(game, process)
        assert buyer is not None, "nobody can afford anything two years in"
        power = buyer["power"]
        purse_was = ex.purse(game, power).credits
        mine_was = game.credits
        quoted = ind.worth(game, process, power)

        res = ind.licence(game, process, power)
        assert res["ok"], res.get("why")
        assert res["price"] == quoted, (
            f"quoted {quoted:,} and charged {res['price']:,}")
        assert abs(game.credits - (mine_was + quoted)) < 1e-6
        assert abs(ex.purse(game, power).credits
                   - (purse_was - quoted)) < 1e-6, (
            "the money the captain was paid did not come out of anybody's purse")
        assert ind.has(game, process.tech, power)
        assert game.industries.sold[-1][1:] == [process.tech, power, quoted]
        return (f"{buyer['name']} paid {quoted:,} from a purse of "
                f"{purse_was:,.0f}, and it left the purse")

    @check("the gate agrees with the act, for every process and every power")
    def _():
        # The sweep that keeps finding things: a "may I?" that disagrees with
        # the act it guards. Every process against every power, both answers
        # taken from the same functions and then actually attempted.
        game = _ready("lic-gate")
        tried = agreed = 0
        for process in PROCESSES:
            for power in dip.POWERS:
                ok, why = ind.can_licence(game, process, power)
                res = ind.licence(game, process, power)
                tried += 1
                if ok:
                    assert res["ok"], (
                        f"{process.name}/{power}: allowed, then refused with "
                        f"{res.get('why')!r}")
                else:
                    assert not res["ok"], (
                        f"{process.name}/{power}: refused with {why!r}, and the "
                        "act went through anyway")
                    assert res["why"] == why, (
                        f"{process.name}/{power}: gate said {why!r}, act said "
                        f"{res['why']!r}")
                agreed += 1
        assert tried >= 40, tried
        # And a refusal never moves anything.
        purses = {p: ex.purse(game, p).credits for p in dip.POWERS}
        for power in dip.POWERS:
            ok, _why = ind.can_licence(game, PROCESSES[0], power)
            if not ok:
                ind.licence(game, PROCESSES[0], power)
                assert ex.purse(game, power).credits == purses[power], (
                    "a refused licence still took the money")
        return f"{agreed} of {tried} gate/act pairs agreed"

    @check("the industry comes up, and the price comes down and stays down")
    def _():
        game = _ready("lic-market")
        process = ind.process_of("separation")
        buyer = ind.best_buyer(game, process)
        assert buyer is not None
        power = buyer["power"]
        theirs = list(ex.holdings(game, power))
        others = [s for s in game.galaxy.systems
                  if s.market and s not in theirs][:8]
        was_theirs = _price(game, theirs, "alloy")
        was_others = _price(game, others, "alloy")

        assert ind.licence(game, process, power)["ok"]
        _settle(game, 365)

        # Over the berths where alloy is not under a shock at either end, so
        # what is measured is the industry and not somebody's strike.
        steady = _steady(game, theirs, "alloy")
        assert len(steady) >= 3, (
            f"only {len(steady)} of {len(theirs)} berths are shock-free; there "
            "is nothing clean left to measure")
        now_theirs = _price(game, steady, "alloy")
        now_others = _price(game, _steady(game, others, "alloy"), "alloy")
        assert now_theirs < was_theirs * 0.92, (
            f"a year of Separation Guts and alloy at their berths went "
            f"{was_theirs:,.0f} → {now_theirs:,.0f}")
        # And it is the industry, not the whole sector drifting: the
        # unlicensed ports are the control.
        assert now_others > now_theirs * 1.15, (
            f"alloy is {now_theirs:,.0f} where it is made and "
            f"{now_others:,.0f} where it is not — that is not an industry, "
            "that is a coincidence")
        assert abs(now_others - was_others) < was_others * 0.25, (
            f"the control moved too: {was_others:,.0f} → {now_others:,.0f}")
        return (f"alloy {was_theirs:,.0f} → {now_theirs:,.0f} across "
                f"{len(steady)} of the licensee's {len(theirs)} berths, against "
                f"{now_others:,.0f} elsewhere")

    @check("the forecast is where the market actually settles")
    def _():
        # A forecast that does its own arithmetic is how a quote comes to
        # disagree with a till. This one prices a copy of the stock through the
        # same `buy_price` the counter uses; the test of that is to license the
        # thing and go back and look.
        game = _ready("lic-forecast")
        worst = 0.0
        rows = skipped = 0
        for tech in ("separation", "magnetite", "organics"):
            process = ind.process_of(tech)
            buyer = ind.best_buyer(game, process)
            if buyer is None:
                continue
            power = buyer["power"]
            # The same standing and the same haggling the forecast used, or
            # the two are not quoting the same counter: a captain holding every
            # process in the tree has a trade bonus near 0.48 and is charged a
            # quarter less than the sticker price. The first draft compared the
            # forecast against `buy_price(..., 0)` and read every berth as 40%
            # out, in the same direction, which is the signature of a scale
            # factor rather than a bad forecast.
            rep, haggle = float(game.rep.get(power, 0)), game.ship_stats.trade
            said = {r["system"].id: r["buy_then"]
                    for r in ind.forecast(game, process, power)["rows"]}
            # **And who was living there when the forecast was made.** The powers
            # plant settlements over a chronicle now (`sim/settlement.py`), and a
            # settlement is a permanent new producer of the thing it works — so
            # one founded during the year the licence is settling moves the price
            # the forecast quoted, by something the forecast could not have
            # known. Same treatment as a live shock: not a bad forecast, a
            # changed world, and it is excluded rather than averaged in.
            from ..sim import settlement as settle_sim
            was_settled = {sid: len(settle_sim.in_system(game, sid))
                           for sid in said}
            # **A shock at *either* end disqualifies the pair.** `_steady` is
            # asked after the settling and so only sees the shocks alive then; a
            # glut that was running when the forecast was taken and had lifted by
            # the time the price was read moves the answer just as far. Measured:
            # one berth read 27% out because a `dumping` shock (×1.9 supply) was
            # live for the forecast and expired before the measurement, and the
            # comment written for this check last cycle said "at either end"
            # while the code only did one.
            shocked_then = {sid for sid in said
                            if [k for k in market_sim.at(game, sid)
                                if k.commodity == process.good]}
            assert ind.licence(game, process, power)["ok"]
            # 150 days rather than 400: the drift reaches the new baseline in
            # about ninety (3% a day toward it), and every extra day is another
            # chance for a power to plant a settlement in one of these systems
            # and move the price by something the forecast could not know.
            _settle(game, 150)
            # A forecast quotes the *baseline* the market settles onto. A live
            # shock is a deliberate temporary departure from it — the first
            # draft counted one and read 56% out.
            for system in _steady(game, ex.holdings(game, power), process.good):
                want = said.get(system.id)
                if want is None:
                    continue
                if (system.id in shocked_then
                        or len(settle_sim.in_system(game, system.id))
                        != was_settled.get(system.id)):
                    skipped += 1
                    continue
                got = buy_price(system.market, process.good, rep, haggle)
                if not got:
                    continue
                rows += 1
                worst = max(worst, abs(got - want) / want)
        assert rows >= 8, f"only {rows} berths measured"
        assert worst < 0.22, (
            f"the worst forecast was {100 * worst:.0f}% out from where the "
            "price settled a year later")
        return (f"{rows} berths, worst forecast {100 * worst:.0f}% from the "
                f"settled price; {skipped} skipped for gaining a settlement "
                "mid-flight")

    @check("it costs you at that counter, by about what it said it would")
    def _():
        game = _ready("lic-cost")
        process = ind.process_of("solforge")
        buyer = ind.best_buyer(game, process)
        if buyer is None:
            process = ind.process_of("separation")
            buyer = ind.best_buyer(game, process)
        assert buyer is not None
        power = buyer["power"]
        theirs = list(ex.holdings(game, power))
        rep, haggle = float(game.rep.get(power, 0)), game.ship_stats.trade
        quoted = ind.forecast(game, process, power)["your_loss"]
        was = mean([sell_price(s.market, process.good, rep, haggle)
                    for s in theirs if s.market])

        assert ind.licence(game, process, power)["ok"]
        _settle(game, 400)
        steady = _steady(game, ex.holdings(game, power), process.good)
        assert len(steady) >= 3, len(steady)
        now = mean([sell_price(s.market, process.good, rep, haggle)
                    for s in steady])
        lost = was - now
        assert lost > 0, (
            f"{process.good} still fetches {now:,.0f} where it fetched "
            f"{was:,.0f} — the industry cost the captain nothing, so the trade "
            "has no other side to it")
        assert abs(lost - quoted) < max(6.0, quoted * 0.4), (
            f"quoted {quoted:,} a tonne and it actually cost {lost:,.0f}")
        return (f"{process.good} fetched {was:,.0f} at their quays, now "
                f"{now:,.0f} — quoted {quoted:,} a tonne, cost {lost:,.0f}")

    @check("a berth built afterwards comes up with the industry running")
    def _():
        game = _ready("lic-found")
        process = ind.process_of("bioleach")
        buyer = ind.best_buyer(game, process)
        assert buyer is not None
        power = buyer["power"]
        assert ind.licence(game, process, power)["ok"]

        blank = next((s for s in game.galaxy.systems
                      if s.faction == power and s.port is None), None)
        if blank is None:
            blank = next(s for s in game.galaxy.systems if s.port is None)
            blank.faction = power
        assert ex.found(game, blank, power) is not None
        works = blank.market.stock[process.good].works
        assert works > 1.0, (
            f"a berth founded after the licence has works {works} on "
            f"{process.good} — it is the one port of theirs that never got it")
        assert abs(works - process.supply) < 1e-9
        return (f"{blank.name} opened with the {process.name} already running "
                f"at ×{works:.2f}")

    @check("nobody is licensed twice, and bringing it up twice changes nothing")
    def _():
        game = _ready("lic-twice")
        process = ind.process_of("magnetite")
        buyer = ind.best_buyer(game, process)
        assert buyer is not None
        power = buyer["power"]
        assert ind.licence(game, process, power)["ok"]
        one = [s.market.stock[process.good].works
               for s in ex.holdings(game, power)]

        again = ind.licence(game, process, power)
        assert not again["ok"] and "already" in again["why"], again
        for system in ex.holdings(game, power):
            ind.industrialise(game, system)
            ind.industrialise(game, system)
        two = [s.market.stock[process.good].works
               for s in ex.holdings(game, power)]
        assert one == two, (
            f"bringing the industry up three times gave {two} against {one} — "
            "it multiplies what is there instead of recomputing it")
        # A second buyer pays less: exclusivity was most of what it was worth.
        rival = next(p for p in dip.POWERS if p != power)
        game.rep[rival] = game.rep.get(power, 0)
        ex.purse(game, rival).credits = 400000
        second = ind.worth(game, process, rival)
        game.industries.held[process.tech] = []
        first = ind.worth(game, process, rival)
        assert second < first, (
            f"the second buyer is quoted {second:,} where the first was "
            f"{first:,}")
        return (f"works held at {one[0]:.2f} through three passes; a second "
                f"buyer pays {second:,} against {first:,}")

    @check("everybody notices, and an illicit process most of all")
    def _():
        game = _ready("lic-politics")
        process = ind.process_of("separation")
        buyer = ind.best_buyer(game, process)
        assert buyer is not None
        power = buyer["power"]
        rivals = [p for p in dip.POWERS if p != power]
        rep_was = {p: game.rep.get(p, 0) for p in dip.POWERS}
        rel_was = {p: dip.relation(game, power, p) for p in rivals}

        assert ind.licence(game, process, power)["ok"]
        assert game.rep[power] - rep_was[power] == LICENSEE_GAIN
        for other in rivals:
            assert game.rep[other] - rep_was[other] == RIVAL_COST, (
                f"{other} did not mind at all")
            assert dip.relation(game, power, other) < rel_was[other], (
                "it is a fact about the two of them as well, and their "
                "relation did not move")

        # And the seed process costs you with everybody, licensee included.
        seed = ind.process_of("multifront")
        got = ind.best_buyer(game, seed)
        if got is not None:
            before = {p: game.rep.get(p, 0) for p in dip.POWERS}
            assert ind.licence(game, seed, got["power"])["ok"]
            hit = [game.rep[p] - before[p] for p in dip.POWERS
                   if p != got["power"]]
            assert all(h <= RIVAL_COST + ILLICIT_COST + 1e-9 for h in hit), (
                f"teaching somebody to grow unlicensed seed cost {hit} with "
                "the rest of the sector")
        return (f"licensee {LICENSEE_GAIN:+.0f}, each rival {RIVAL_COST:+.0f}, "
                f"and an illicit licence {ILLICIT_COST:+.0f} on top")

    @check("a good a port does not trade stays untraded")
    def _():
        # **The regression check for a compatibility shim.** `tick_market`
        # adopted a baseline of 1.0 for any stock that had none, and the supply
        # floor lifted a zero supply to 0.02 so that the shim then adopted
        # *that*. Between them, unlicensed seed — stocked at nine ports in
        # twenty-one by `make_market` — was on sale at all twenty-one one day
        # into every chronicle. Most of the point of contraband, gone.
        game = new_game("untraded")
        ports = [s for s in game.galaxy.systems if s.market]
        opening = [s for s in ports if buy_price(s.market, "wildseed", 0)]
        assert 2 <= len(opening) < len(ports), (
            f"{len(opening)} of {len(ports)} ports open selling contraband; "
            "this check cannot say anything about a sector where everybody "
            "or nobody does")
        game.advance_days(1)
        after_one = [s for s in ports if s.market
                     and buy_price(s.market, "wildseed", 0)]
        assert len(after_one) == len(opening), (
            f"{len(opening)} ports sold unlicensed seed on day one and "
            f"{len(after_one)} sold it on day two")
        _settle(game, 730)
        later = [s for s in ports if s.market
                 and buy_price(s.market, "wildseed", 0)]
        assert len(later) <= len(opening) + 2, (
            f"{len(later)} ports selling contraband two years in, against "
            f"{len(opening)} at the start")

        # And a licence is what opens one, which is the other half of the claim.
        game2 = _ready("untraded-open")
        seed = ind.process_of("multifront")
        clean = [p for p in dip.POWERS
                 if all(s.market.stock["wildseed"].base <= 0
                        for s in ex.holdings(game2, p) if s.market)]
        assert clean, "every power already trades it; nothing to open"
        power = clean[0]
        ex.purse(game2, power).credits = 400000
        game2.rep[power] = 40
        assert ind.licence(game2, seed, power)["ok"]
        opened = [s for s in ex.holdings(game2, power)
                  if s.market and s.market.stock["wildseed"].base > 0]
        assert len(opened) == len(ex.holdings(game2, power)), (
            f"{len(opened)} of {len(ex.holdings(game2, power))} berths opened")
        assert abs(opened[0].market.stock["wildseed"].base
                   - OPENED_SUPPLY * seed.supply) < 1e-6 or \
            opened[0].market.stock["wildseed"].base >= OPENED_SUPPLY
        return (f"{len(opening)} of {len(ports)} ports sell it and stay that "
                f"way; a licence opened {len(opened)} more")

    @check("the numbers make a licence worth selling and worth buying")
    def _():
        # The tripwires, each pinned by a consequence rather than by repeating
        # the constant. What a licence is worth has to be large enough to be
        # worth a detour and small enough that a power can find it.
        game = _ready("lic-pace")
        dearest = max(PROCESSES, key=lambda p: TECH_BY_ID[p.tech].cost)
        cheapest = min(PROCESSES, key=lambda p: TECH_BY_ID[p.tech].cost)
        power = max(dip.POWERS, key=lambda p: len(ex.holdings(game, p)))
        game.rep[power] = 0.0
        big = ind.worth(game, dearest, power)
        small = ind.worth(game, cheapest, power)
        assert big > small * 4, (
            f"the dearest process in the tree fetches {big:,} and the cheapest "
            f"{small:,}; the tree's own costs are 900 points against 140")
        assert big > 15000, f"the best licence in the game is worth {big:,}"

        # A power's own income has to make the purchase make sense, or nobody
        # would ever sign. Measured as the payback time on the fee.
        before = ex.income(game, power)
        assert ind.licence(game, cheapest, power)["ok"]
        after = ex.income(game, power)
        gain = after - before
        assert gain > 0, "an industry adds nothing to what a power earns"
        # One industry is worth a few per cent of what a power earns. Pinned as
        # a band rather than against the constant, because a check that reads
        # the constant on both sides of the comparison agrees with any value
        # of it.
        lift = after / before - 1.0
        assert 0.035 < lift < 0.095, (
            f"one industry lifted this power's income by {lift:.1%}; a process "
            "is meant to be worth a few per cent, not nothing and not a third")
        payback = small / gain
        assert 20 < payback < 900, (
            f"a licence pays for itself in {payback:,.0f} days")

        # Standing is worth money, and open hostility is a closed door.
        game.rep[power] = 70.0
        liked = ind.worth(game, dearest, power)
        game.rep[power] = -60.0
        hated = ind.worth(game, dearest, power)
        assert liked > hated * 1.4, (
            f"Kin pays {liked:,} and Hostile {hated:,} for the same process")
        ok, why = ind.can_licence(game, dearest, power)
        assert not ok and "will not take" in why, (
            f"a power at -60 standing still deals: {ok}, {why!r}")
        assert MIN_STANDING < -8, (
            "a power that is merely Neutral about you refuses to trade")
        assert 0.3 < SECOND_HAND < 0.8, SECOND_HAND
        assert WORTH_PER_POINT > 1.0, WORTH_PER_POINT
        return (f"{dearest.name} {big:,} against {cheapest.name} {small:,}; "
                f"payback {payback:,.0f} days; Kin pays {liked / hated:.2f}× "
                "what Hostile does")
