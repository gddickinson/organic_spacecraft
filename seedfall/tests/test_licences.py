"""Who notices a licence, what it is worth, and what it cannot put on sale.

Split out of `tests/test_industry.py` when it reached 520 lines. That file
measures a licensed process at the counter it changes; this one measures the
world around the counter: every power notices (an illicit process most of
all), a good a port does not trade stays untraded — the regression check for
a shim that put contraband on sale at every port one day into every
chronicle — and the numbers make a licence worth both selling and buying.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.industry import (LICENSEE_GAIN, MIN_STANDING, OPENED_SUPPLY,
                             PROCESSES, RIVAL_COST, SECOND_HAND,
                             WORTH_PER_POINT)
from ..data.tech import TECH_BY_ID
from ..sim import diplomacy as dip
from ..sim import exchequer as ex
from ..sim import industry as ind
from ..world.economy import buy_price
from .harness import Suite
from .test_industry import _ready, _settle


def run(suite: Suite) -> None:
    check = suite.check

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
            # Absolute, not `== RIVAL_COST`: read off the constant this
            # moved with it and could not fail. A licit licence costs a rival
            # 6, and the illicit one below costs 24 — the difference is the
            # 18 that `ILLICIT_COST` is.
            assert abs(game.rep[other] - rep_was[other] - (-6.0)) < 1e-9, (
                f"{other} lost {game.rep[other] - rep_was[other]:+.1f}, not 6")
            assert dip.relation(game, power, other) < rel_was[other], (
                "it is a fact about the two of them as well, and their "
                "relation did not move")

        # And the seed process costs you with everybody, licensee included.
        #
        # **This branch never ran, and the line below still reported it.** It
        # was wrapped in `if got is not None`, and `best_buyer` returns None
        # here because the seed licence is the dearest in the tree — measured,
        # all four powers answer "cannot raise 23,645–31,280, the treasury
        # will not stand it". So the check skipped the whole illicit case and
        # returned a summary quoting `ILLICIT_COST` as though it had tested
        # it. The purse is funded now and the buyer is asserted, so the case
        # is reached rather than hoped for.
        for who in dip.POWERS:
            ex.purse(game, who).credits = 500_000.0
        seed = ind.process_of("multifront")
        got = ind.best_buyer(game, seed)
        assert got is not None, (
            "nobody can afford the seed licence, so the illicit cost is "
            "untested — fund the purse rather than skipping the case")
        before = {p: game.rep.get(p, 0) for p in dip.POWERS}
        assert ind.licence(game, seed, got["power"])["ok"]
        hit = [game.rep[p] - before[p] for p in dip.POWERS
               if p != got["power"]]
        # **Absolute, deliberately not `RIVAL_COST + ILLICIT_COST`.** Read off
        # the constants, the assertion moved with them and could not fail.
        # Measured: a rival loses 6 for the licence and 18 more for it being
        # illicit, so 24 exactly.
        assert all(abs(h - (-24.0)) < 1e-9 for h in hit), (
            f"teaching somebody to grow unlicensed seed cost {hit} with the "
            "rest of the sector, against -24 each")
        return (f"licensee {LICENSEE_GAIN:+.0f}, each rival {RIVAL_COST:+.0f} "
                f"for a licence and -24 for an illicit one")

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
