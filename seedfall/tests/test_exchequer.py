"""The public purse, measured by running a sector for years.

Before this the powers were penniless: a port's level was fixed when the galaxy
was made and nothing in the game could raise it, lower it, build a new one or
close an old one. The map you flew in year one was the map you flew in year
twelve.

Every claim here is measured by playing rather than read off the table that set
it up, and the ones that matter are the couplings — the places where money
touches something the captain can see:

- **A day changes the purse by exactly what the ledger says**, because the panel
  and the sim read the same two functions.
- **A surplus builds and a deficit gives something up**, so the sector's
  infrastructure moves over a chronicle.
- **A blockade costs its target income**, which is the first time in this game
  that a venture has cost anybody money.
- **A power that cannot pay the stake starts no ventures.**
- **A berth that closes is marked in the register**, because a note about a
  price is not a promise that there is still somewhere to sell.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.exchequer import (FOUND_COST, HARBOUR_DUE, OPENING_PURSE, RESERVE,
                              SETTLE_DAYS, STEP_COST, VENTURE_STAKE)
from ..data.factions import FACTIONS_BY_ID
from ..sim import diplomacy as dip
from ..sim import exchequer as ex
from ..sim import exchequer_ledger as ex_ledger
from ..sim import market as market_sim
from ..sim import ventures as venture_sim
from .harness import Suite


def _years(game, years: float, step: int = 5) -> None:
    for _ in range(int(years * 365 / step)):
        game.advance_days(step)


def _levels(game) -> tuple[int, int]:
    ports = [s for s in game.galaxy.systems if s.port]
    return len(ports), sum(s.port.level for s in ports)


def run(suite: Suite) -> None:
    check = suite.check

    @check("a day changes the purse by exactly what the ledger says")
    def _():
        # **The forecast and the act read the same function.** Every screen in
        # this game that worked out its own version of a number the sim already
        # knew has eventually disagreed with it — the docking forecast, the
        # mining prospect, the register's "best" market. So the panel is handed
        # `income` and `outlay`, and this is the check that they are what a day
        # actually does.
        game = new_game("purse-arith")
        worst = 0.0
        for power in dip.POWERS:
            p = ex.purse(game, power)
            # Away from a settlement, so nothing is spent or given up in the
            # same step and the arithmetic is only the accrual.
            p.settled = game.day
            before = p.credits
            want = ex.margin(game, power)
            game.advance_days(1)
            got = ex.purse(game, power).credits - before
            worst = max(worst, abs(got - want))
        assert worst < 1e-6, (
            f"the purse moved by {worst:,.2f} more than the ledger's margin — "
            "the screen is quoting a rate the sim does not charge")

        # And the margin is the two halves of it, not a third number.
        power = dip.POWERS[0]
        assert abs(ex.margin(game, power)
                   - (ex.income(game, power) - ex.outlay(game, power))) < 1e-9
        return (f"four purses tracked their own ledgers to "
                f"{worst:.2e} credits over a day")

    @check("a surplus builds, and the sector is not the same place years later")
    def _():
        # The whole point. Measured over a chronicle rather than by calling
        # `promote` and observing that it promotes.
        game = new_game("purse-grow")
        was_ports, was_levels = _levels(game)
        _years(game, 8)
        now_ports, now_levels = _levels(game)
        told = ex_ledger.summary(game)

        assert told["built"] >= 8, (
            f"only {told['built']} works paid for in eight years — the powers "
            "are not building anything")
        assert now_levels > was_levels + 6, (
            f"the sector went from {was_levels} levels of port to {now_levels}; "
            "that is not an infrastructure, it is scenery")
        assert now_ports > was_ports, (
            f"{was_ports} berths became {now_ports} — nobody founded anything")
        # Bounded, not runaway: the point of an upkeep that goes as the square
        # of the level is that a built-out sector runs at break-even.
        rich = max(ex.purse(game, p).credits for p in dip.POWERS)
        assert rich < 40 * OPENING_PURSE, (
            f"a power is sitting on {rich:,.0f} credits — the treasuries are "
            "growing without limit, which is the banked-research bug again")
        return (f"{was_ports} berths / {was_levels} levels → {now_ports} / "
                f"{now_levels} over eight years; {told['built']} works paid "
                f"for, {told['lost']} steps given up")

    @check("a deficit gives something up, and that recovers the upkeep")
    def _():
        game = new_game("purse-bust")
        power = "sanhedrin"
        held = ex.holdings(game, power)
        assert held, "nothing to take away"
        before = ex.outlay(game, power)
        levels_before = sum(s.port.level for s in held)

        p = ex.purse(game, power)
        # Far enough under that the day's own income cannot lift it out: the
        # accrual happens before the books are done, and a purse one credit
        # short is a purse in surplus by the time anybody looks at it.
        p.credits = -10000.0
        p.settled = game.day - SETTLE_DAYS
        events = ex.settle(game, 1)

        after = ex.outlay(game, power)
        levels_after = sum(s.port.level for s in ex.holdings(game, power))
        assert levels_after < levels_before, (
            f"a power in deficit kept all {levels_before} levels of port")
        assert after < before, (
            f"it gave a step up and its upkeep stayed at {after:,.0f} — "
            "retrenchment that recovers nothing is not retrenchment")
        assert p.losses == 1, f"{p.losses} steps recorded, expected 1"
        assert any("warn" == kind for kind, _ in events), (
            "giving up a berth passed without a word to the log")
        return (f"upkeep {before:,.0f} → {after:,.0f} a day; "
                f"{levels_before} levels → {levels_after}")

    @check("a power builds what pays for itself, and not what is cheapest")
    def _():
        # `exchequer.payback`'s docstring has described this since it was
        # written and nothing has ever checked it: the upkeep curve is
        # quadratic and the yield is linear, so **the cheap works are the ones
        # that never pay**. Measured on a level-1 berth:
        #
        #     level   1      2      3      4      5
        #     yield  90    180    270    360    450
        #     upkeep 30    120    270    480    750
        #     net   +60    +60      0   −120   −300
        #
        # Promoting an outpost to a station is worth exactly nothing a day,
        # and every step above it is a loss. That is deliberate — a Fleet Hub
        # is what a power builds with money it has nothing better to do with —
        # but it only works because `works_open` sorts by payback rather than
        # by price, and that sort was unguarded.
        game = new_game("payback")
        power = dip.POWERS[0]
        found = ex.payback(game, power, ex.FOUND_COST, "found")
        assert found < float("inf"), (
            f"founding a berth never pays for itself: {found}")
        for level in (2, 3, 4):
            step = ex.payback(game, power, 10_000, f"promote:{level}")
            assert step == float("inf"), (
                f"promoting to level {level} claims to pay back in {step:.0f} "
                "days, and it clears nothing a day")
        # And the ordering the sort exists for: nothing that never pays is
        # offered ahead of something that does.
        for held in ex.holdings(game, power):
            opts = ex.works_open(game, power)
            if len(opts) < 2:
                continue
            paying = [i for i, (cost, _s, what) in enumerate(opts)
                      if ex.payback(game, power, cost, what) < float("inf")]
            never = [i for i, (cost, _s, what) in enumerate(opts)
                     if ex.payback(game, power, cost, what) == float("inf")]
            if paying and never:
                assert max(paying) < min(never), (
                    "a work that never pays is offered before one that does")
            break
        return (f"founding pays back in {found:,.0f} days; promoting to "
                "levels 2, 3 and 4 never does, and is offered last")

    @check("a power that cannot pay the stake starts nothing")
    def _():
        # A venture used to cost its sponsor exactly nothing, so a power
        # stripped of every port ran as many initiatives as one holding half
        # the sector. This is the gate that makes a purse mean something.
        game = new_game("purse-broke")
        broke, flush = "charter", "sanhedrin"
        ex.purse(game, broke).credits = VENTURE_STAKE - 1
        ex.purse(game, flush).credits = 400000

        assert ex.appetite(game, broke) == 0.0, "a broke power is still restless"
        assert ex.appetite(game, flush) > 1.0, (
            "a power with a war chest is no keener than a poor one")

        rng = game.rng("onset")
        started = {broke: 0, flush: 0}
        for _ in range(400):
            for power in (broke, flush):
                before = len(venture_sim.by_power(game, power))
                venture_sim.start(game, rng, power)
                if len(venture_sim.by_power(game, power)) > before:
                    started[power] += 1
                # Clear the board so the per-power cap is not what is being
                # measured here.
                for v in venture_sim.by_power(game, power):
                    v.resolved = True
        assert started[broke] == 0, (
            f"a power holding {VENTURE_STAKE - 1} credits started "
            f"{started[broke]} ventures at {VENTURE_STAKE} a time")
        assert started[flush] > 20, (
            f"a power with 400,000 credits managed only {started[flush]} "
            "ventures in four hundred attempts")
        spent = 400000 - ex.purse(game, flush).credits
        assert abs(spent - started[flush] * VENTURE_STAKE) < 1e-6, (
            f"{started[flush]} ventures cost {spent:,.0f}, not "
            f"{started[flush] * VENTURE_STAKE:,}")
        return (f"{started[broke]} ventures on an empty purse, "
                f"{started[flush]} on a full one, at {VENTURE_STAKE:,} each")

    @check("a blockade costs its target income, and the shortage is why")
    def _():
        # The first venture in this game that has ever cost anybody money.
        game = new_game("purse-blockade")
        target = "sanhedrin"
        before = ex.income(game, target)
        pinched_before = sum(1 for s in ex.holdings(game, target)
                             if ex.scarce(game, s))

        venture = venture_sim.Venture(id=90001, kind="blockade", power="charter",
                                      other=target, until=game.day)
        venture_sim.ensure(game).append(venture)
        venture_sim._apply(game, venture, game.rng("land"))
        market_sim.apply_to_markets(game)

        after = ex.income(game, target)
        pinched = sum(1 for s in ex.holdings(game, target)
                      if ex.scarce(game, s))
        assert pinched > pinched_before, (
            "the blockade landed and not one of the target's berths is pinched")
        assert after < before * 0.95, (
            f"income {before:,.0f} → {after:,.0f}: a blockade that costs the "
            "blockaded nothing is a press release")
        # And it is the shortage doing it, through the same function the
        # ledger reads — not a second penalty applied somewhere else.
        by_hand = sum(ex.yield_of(game, s) for s in ex.holdings(game, target))
        assert abs(by_hand - after) < 1e-9
        return (f"income {before:,.0f} → {after:,.0f} a day "
                f"({100 * (after / before - 1):+.0f}%), {pinched} berths pinched")

    @check("a new berth comes with a market you can actually trade at")
    def _():
        game = new_game("purse-found")
        power = "concordat"
        empty = next((s for s in game.galaxy.systems
                      if s.faction == power and s.port is None), None)
        assert empty is not None, "nowhere for this power to build"
        assert empty.market is None

        told = ex.found(game, empty, power)
        assert told and empty.port is not None
        assert empty.market is not None, (
            "a berth with no market is not a port, it is a decoration")
        assert empty.port.faction == power
        # The player can stand there and see prices, which is the only test of
        # a market that matters.
        game.location_id = empty.id
        quoted = {cid: market_sim.quote_sell(game, empty, cid)
                  for cid in empty.market.stock}
        quoted = {c: v for c, v in quoted.items() if v}
        assert quoted, "the new market quotes nothing"
        assert ex.income(game, power) > 0

        # And it is on the exchequer's own books from then on.
        assert empty in ex.holdings(game, power)
        return (f"{empty.name}: a new {empty.port.name} quoting "
                f"{len(quoted)} goods, worth {ex.yield_of(game, empty):,.0f} "
                "a day to its holder")

    @check("a berth that closes says so in the register")
    def _():
        # **Found by playing.** With the powers able to close a port, the
        # register could hand the captain a two-year-old note about a good
        # price at a berth that is no longer there — and the panel drew it
        # exactly like a live one, hops, days and revenue a day included.
        game = new_game("purse-closed")
        here = next(s for s in game.galaxy.systems
                    if s.port and s.market and not s.port.capital)
        game.location_id = here.id
        market_sim.note_prices(game, here)
        good = next(c for c in here.market.stock
                    if market_sim.quote_sell(game, here, c))

        rows = market_sim.best_markets(game, good, selling=True)
        mine = [r for r in rows if r["system"].id == here.id]
        assert mine and mine[0]["open"], "a live berth is marked closed"

        # Now the power gives it up.
        game.location_id = next(s.id for s in game.galaxy.systems
                                if s.id != here.id)
        while here.port is not None:
            ex.demote(game, here)
        rows = market_sim.best_markets(game, good, selling=True)
        mine = [r for r in rows if r["system"].id == here.id]
        assert mine, "the note vanished with the berth; it is still a record"
        assert not mine[0]["open"], (
            "the berth is gone and the register still offers it as somewhere "
            "to take cargo")
        # Closed berths sort below open ones rather than being hidden.
        opens = [r["open"] for r in rows]
        assert opens == sorted(opens, reverse=True), (
            f"a closed berth outranks an open one: {opens}")
        return (f"{here.name} closed; its note is kept, marked, and ranked "
                f"below {sum(opens)} open berths")

    @check("nobody pulls a berth down with your hull alongside")
    def _():
        game = new_game("purse-moored")
        power = "freeholds"
        held = [s for s in ex.holdings(game, power) if not s.port.capital]
        assert held, "no berth to test with"
        # Take the smallest down to an outpost, then stand in it.
        target = min(held, key=lambda s: s.port.level)
        while target.port.level > 1:
            ex.demote(game, target)
        game.location_id = target.id
        assert ex.demote(game, target) is None, (
            "the berth was abandoned out from under the ship in it")
        assert target.port is not None
        # Somewhere else, the same call closes it.
        game.location_id = next(s.id for s in game.galaxy.systems
                                if s.id != target.id)
        assert ex.demote(game, target) is not None
        assert target.port is None and target.market is None
        return f"{target.name} survived while moored, closed once left"

    @check("a Free Port of your own pays you a harbour due")
    def _():
        # `player_built` was read by exactly one function before this: the one
        # that tears the harbour down again.
        game = new_game("purse-due")
        blank = next(s for s in game.galaxy.systems if s.port is None)
        from ..sim import colony as colony_sim
        assert colony_sim.open_harbour(game, blank) is not None
        level = blank.port.level

        game.credits = 5000.0
        want = HARBOUR_DUE * level * 3
        got_before = game.credits
        ex.settle(game, 3)
        paid = game.credits - got_before
        assert abs(paid - want) < 1e-6, (
            f"three days of a level-{level} Free Port paid {paid:,.1f}, "
            f"expected {want:,.1f}")
        # And it is the player's, not a power's: nobody else's purse sees it.
        assert blank not in ex.holdings(game, blank.port.faction), (
            "a power is drawing income from a berth the player built")
        return f"a level-{level} Free Port pays {HARBOUR_DUE * level:,.0f} a day"

    @check("the numbers make a sector that changes at a playable pace")
    def _():
        # The tripwires. Every constant in `data/exchequer.py` is pinned by a
        # consequence rather than by repeating its value: mutate one and a
        # claim here about how the sector behaves stops being true.
        game = new_game("purse-pace")

        # An outpost and a station clear about the same; a hub clears almost
        # nothing. That equilibrium *is* YIELD_PER_LEVEL against UPKEEP_COEFF,
        # and it is why a built-out sector settles instead of running away.
        one, two, three = (ex.YIELD_PER_LEVEL * n - ex.UPKEEP_COEFF * n * n
                           for n in (1, 2, 3))
        assert 0.75 < two / one < 1.35, (
            f"an outpost clears {one:,.0f} a day and a station {two:,.0f}; "
            "growth is meant to be steady, not explosive")
        assert three < one * 0.35, (
            f"a Fleet Hub clears {three:,.0f} against an outpost's {one:,.0f} "
            "— prestige is supposed to be expensive")

        # A capital is worth holding. Compared per level of port, because on
        # day one a capital is the *only* Fleet Hub anybody has and there is no
        # plain berth of the same size to hold it against.
        cap = next(s for s in game.galaxy.systems
                   if s.port and s.port.capital and not ex.scarce(game, s))
        plain = next(s for s in game.galaxy.systems
                     if s.port and not s.port.capital
                     and not ex.scarce(game, s))
        ratio = ((ex.yield_of(game, cap) / cap.port.level)
                 / (ex.yield_of(game, plain) / plain.port.level))
        assert 1.2 < ratio < 1.6, (
            f"a capital yields {ratio:.2f}× a plain berth, per level of port")

        # A shortage really pinches.
        bare = ex.yield_of(game, plain)
        market_sim.all_shocks(game).append(market_sim.Shock(
            id=77001, kind="rearm", system_id=plain.id, commodity="alloy",
            until=game.day + 90))
        pinched = ex.yield_of(game, plain)
        assert 0.2 < pinched / bare < 0.5, (
            f"a shortage leaves {pinched / bare:.0%} of the yield — that is "
            "either no pressure at all or a death sentence")

        # Building takes seasons, not days and not decades, at the margin a
        # power actually runs.
        rate = max(ex.margin(game, p) for p in dip.POWERS)
        seasons = (STEP_COST[2] + RESERVE) / rate
        assert 60 < seasons < 500, (
            f"the cheapest promotion is {seasons:,.0f} days of surplus away")
        assert FOUND_COST > STEP_COST[2], (
            "founding a berth from nothing is cheaper than promoting one")
        assert STEP_COST[3] > STEP_COST[2] * 2, (
            "a Fleet Hub costs about the same as a station")

        # A power can act at once, and its first work is weeks off rather than
        # years. What it *cannot* do is both on day one — 30,000 against a
        # 9,000 stake and a 24,000 promotion over a 12,000 reserve — which is
        # the choice the opening purse is sized to force.
        assert OPENING_PURSE >= VENTURE_STAKE, (
            "a power cannot even open its account with a venture")
        first = (STEP_COST[2] + RESERVE - OPENING_PURSE) / rate
        assert 0 < first < 120, (
            f"the first promotion of the chronicle is {first:,.0f} days off")

        # And nobody decides twice inside a month. Over four years that caps
        # what any one power can have done.
        _years(game, 4)
        for power in dip.POWERS:
            p = ex.purse(game, power)
            moves = p.works + p.losses
            assert moves <= 4 * 365 / SETTLE_DAYS + 1, (
                f"{FACTIONS_BY_ID[power].short} made {moves} decisions in four "
                f"years, more than one every {SETTLE_DAYS} days")
        return (f"outpost {one:,.0f}/station {two:,.0f}/hub {three:,.0f} a day; "
                f"a promotion is {seasons:,.0f} days of surplus and the first "
                f"is {first:,.0f} days in; a shortage leaves {pinched / bare:.0%}")
