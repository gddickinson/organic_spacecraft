"""Somebody on the ground, and the local price of what they dig.

Measured at turn zero before this: **161 bodies across 42 systems and 0
settlements.** The player could plant a colony and no power ever had, so every
trade in the sector happened at an orbital berth and a world rich in phosphate was
a number on a survey screen.

The powers settle now, out of the treasuries `sim/exchequer.py` gave them, on
bodies in systems they hold whose grades are worth working. A settlement grows for
a couple of years, pays its founder, and **the market in that system knows** — the
good it works gets commoner and everything else its people eat gets scarcer.

The claims, measured by running a sector rather than by reading the table:

- **The sector settles over a chronicle** and keeps settling, rather than doing it
  once and stopping.
- **The ground decides what a settlement is for**: it works the best grade on the
  body it stands on.
- **The market shows it** — the worked good is cheaper where it is worked than
  where it is not, and the settlement's system is hungrier for everything else.
- **`Stock.works` has one writer**, so a licensed industry and a settlement in the
  same system compose rather than overwrite each other.
- **A body is keyed by system and body together**, because `Body.id` is an index
  within its system and 155 bodies share six distinct ids.
"""

from __future__ import annotations

from statistics import mean

from ..core.state import new_game
from ..data.settlements import (DEMAND, FOUND_COST, MATURE_DAYS, NEWBORN,
                                SUPPLY, UPKEEP, WORKABLE, WORTH_SETTLING,
                                YIELD)
from ..sim import exchequer as ex
from ..sim import industry as industry_sim
from ..sim import settlement as settle
from ..world.economy import buy_price
from .harness import Suite


def _years(game, years: float, step: int = 5) -> None:
    for _ in range(int(years * 365 / step)):
        game.advance_days(step)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the sector gets settled, and keeps getting settled")
    def _():
        game = new_game("ground-grow")
        assert not settle.held(game), "somebody was living here on day one"
        marks = []
        for _year in range(5):
            _years(game, 1)
            marks.append(settle.summary(game)["count"])
        told = settle.summary(game)
        assert told["count"] > 12, (
            f"{told['count']} settlements in five years across four powers")
        assert marks[-1] > marks[0], (
            f"settlement stopped after the first year: {marks}")
        assert marks[2] > marks[1], (
            f"no settlement in the third year: {marks} — the powers did it once "
            "and stopped, which is what a lexicographic preference does")
        assert told["systems"] > 4, told
        assert len(told["powers"]) >= 3, told["powers"]
        assert set(told["goods"]) <= set(WORKABLE), told["goods"]
        return (f"{marks} over five years — {told['count']} settlements in "
                f"{told['systems']} systems, {len(told['powers'])} powers, "
                f"working {', '.join(told['goods'])}")

    @check("the ground decides what a settlement is for")
    def _():
        game = new_game("ground-picks")
        power = max(("charter", "concordat", "freeholds", "sanhedrin"),
                    key=lambda p: len(settle.sites_for(game, p)))
        sites = settle.sites_for(game, power)
        assert len(sites) > 5, len(sites)
        for system, body, good in sites[:12]:
            assert settle.grade_of(body, good) >= WORTH_SETTLING, (
                f"{body.name} offered for {good} at "
                f"{settle.grade_of(body, good):.2f}")
            # And it is the *dearest* grade the body clears the bar on, in the
            # order `WORKABLE` puts them.
            wanted = next(g for g in WORKABLE
                          if settle.grade_of(body, g) >= WORTH_SETTLING)
            assert good == wanted, (
                f"{body.name} settled for {good} when it also gives {wanted}")

        system, body, good = sites[0]
        made = settle.found(game, system, body, power)
        assert made is not None and made.good == good
        assert settle.on_body(game, system.id, body.id) is made
        assert settle.found(game, system, body, power) is None, (
            "two settlements were planted on one body")
        return (f"{len(sites)} sites for {power}; the best is {body.name} at "
                f"{settle.grade_of(body, good):.2f} of {good}")

    @check("a body is keyed by its system as well as itself")
    def _():
        # **`Body.id` is the body's index within its system.** 155 bodies in a
        # sector share six distinct ids, so a lookup on the id alone matches a
        # body in every system at once. The first draft did that: six
        # settlements masked the whole sector, `sites_for` went from twenty-odd
        # candidates per power to zero inside a year, and nothing was ever
        # settled again.
        game = new_game("ground-keys")
        ids = [b.id for s in game.galaxy.systems for b in s.bodies]
        assert len(set(ids)) < len(ids) / 10, (
            f"{len(set(ids))} distinct ids for {len(ids)} bodies — if these were "
            "unique this check would be measuring nothing")

        power = "concordat"
        sites = settle.sites_for(game, power)
        assert len(sites) > 4
        before = len(sites)
        system, body, _good = sites[0]
        settle.found(game, system, body, power)
        after = settle.sites_for(game, power)
        assert len(after) == before - 1, (
            f"one settlement took {before - len(after)} sites off the list")
        # Explicitly: the same body index elsewhere is still free.
        twins = [(s, b) for s, b, _g in after if b.id == body.id]
        assert twins, (
            f"no other system has a body with id {body.id!r}, so the collision "
            "cannot be demonstrated")
        assert settle.on_body(game, twins[0][0].id, body.id) is None
        return (f"{len(ids)} bodies share {len(set(ids))} ids; one settlement "
                f"took exactly one of {before} sites")

    @check("what they work gets commoner where they work it")
    def _():
        game = new_game("ground-market")
        _years(game, 6)
        by_good = {}
        for good in WORKABLE:
            settled, bare = [], []
            for system in game.galaxy.systems:
                if system.market is None:
                    continue
                here = settle.in_system(game, system.id)
                price = buy_price(system.market, good, 0)
                if not price:
                    continue
                # The control is a market where *this good* is not worked,
                # not one with no settlements at all. That stricter version
                # stopped being measurable when `core/clock` began stepping a
                # day at a time (#116): the powers get some seventy times more
                # decisions over six years, found 77 settlements and leave 1
                # of 27 markets untouched. It is also the wrong control for
                # the claim, which is about one good and not about being
                # settled at all.
                if any(s.good == good for s in here):
                    settled.append(price)
                else:
                    bare.append(price)
            if len(settled) >= 2 and len(bare) >= 3:
                by_good[good] = (mean(settled), mean(bare))
        assert len(by_good) >= 2, (
            f"only {len(by_good)} goods have both a settled and an unsettled "
            "market to compare")
        for good, (settled, bare) in by_good.items():
            assert settled < bare, (
                f"{good} costs {settled:,.1f} where it is worked and "
                f"{bare:,.1f} where it is not")
        worst = min(bare / settled for settled, bare in by_good.values())
        assert worst > 1.03, f"the best case is only {worst:.3f}x"
        return " · ".join(f"{g} {s:,.0f} settled against {b:,.0f} not"
                          for g, (s, b) in by_good.items())

    @check("a settlement grows into its output, and pays for itself")
    def _():
        game = new_game("ground-grows")
        power = "charter"
        sites = settle.sites_for(game, power)
        assert sites
        system, body, good = sites[0]
        made = settle.found(game, system, body, power)
        young = settle.maturity(game, made)
        assert abs(young - NEWBORN) < 1e-9, young
        assert settle.yield_of(game, made) < YIELD - UPKEEP

        game.day += int(MATURE_DAYS)
        grown = settle.maturity(game, made)
        assert abs(grown - 1.0) < 1e-9, grown
        mature_pay = settle.yield_of(game, made)
        assert abs(mature_pay - (YIELD - UPKEEP)) < 1e-9, mature_pay
        assert mature_pay > 0, (
            "a mature settlement does not cover its own upkeep, so nobody "
            "would ever plant one")
        # The honest figure, which counts the loss-making ramp — see the check
        # below and `settlement.payback_days`. Dividing the cost by the mature
        # rate is the number this line used to print, and it is 485 days out.
        payback = settle.payback_days()
        assert 300 < payback < 2500, (
            f"a settlement pays for itself in {payback:,.0f} days")
        assert payback > FOUND_COST / mature_pay

        # And its market effect grows with it.
        assert settle.supply_at(game, system)[good] > \
            1.0 + (SUPPLY - 1.0) * NEWBORN
        assert abs(settle.supply_at(game, system)[good] - SUPPLY) < 1e-9
        return (f"{NEWBORN:.0%} of output on day one, all of it after "
                f"{MATURE_DAYS:,.0f} days; pays back in {payback:,.0f}, not the "
                f"{FOUND_COST / mature_pay:,.0f} the mature rate alone suggests")

    @check("people eat: a settled system is hungrier for what it does not make")
    def _():
        game = new_game("ground-eats")
        power = "sanhedrin"
        sites = settle.sites_for(game, power)
        assert sites
        system, body, good = sites[0]
        settle.found(game, system, body, power)
        supply = settle.supply_at(game, system)
        assert supply[good] > 1.0, supply
        others = [g for g in WORKABLE if g != good]
        for other in others:
            assert supply[other] < 1.0, (
                f"{other} is not scarcer in a system that eats it: {supply}")
            assert abs(supply[other] - DEMAND) < 1e-9, supply[other]
        return (f"{good} ×{supply[good]:.2f} and the other "
                f"{len(others)} at ×{DEMAND:.2f}")

    @check("one writer of what is made here: industry and settlement compose")
    def _():
        # `Stock.works` began as "what the holder of this berth was licensed to
        # make". A settlement makes things too, and two functions writing one
        # field is how they come to disagree — so `industrialise` computes it
        # from both and remains the only writer.
        game = new_game("ground-compose")
        power = "concordat"
        sites = [row for row in settle.sites_for(game, power)
                 if row[0].market is not None]
        assert sites, "no settleable system with a market"
        system, body, good = sites[0]
        settle.found(game, system, body, power)
        with_ground = system.market.stock[good].works
        assert with_ground > 1.0, with_ground

        process = next((p for p in industry_sim.PROCESSES if p.good == good), None)
        if process is not None:
            game.research.unlocked = list(set(game.research.unlocked)
                                         | {process.tech})
            ex.purse(game, power).credits = 500000
            game.rep[power] = 40
            res = industry_sim.licence(game, process, power)
            assert res["ok"], res
            both = system.market.stock[good].works
            assert both > with_ground, (
                f"a licence on top of a settlement left works at {both} "
                f"against {with_ground} — one of them overwrote the other")
            assert abs(both - with_ground * process.supply) < 1e-6, (
                f"{both} is not {with_ground} × {process.supply}")
        # Recomputing is idempotent, whichever sources are in play.
        once = dict((cid, st.works) for cid, st in system.market.stock.items())
        industry_sim.industrialise(game, system)
        industry_sim.industrialise(game, system)
        twice = dict((cid, st.works) for cid, st in system.market.stock.items())
        assert once == twice, "bringing it up three times changed the answer"
        return (f"{good} at ×{system.market.stock[good].works:.2f} from ground "
                "and licence together, and stable under recomputation")

    @check("a settlement costs before it pays, and the board prices it honestly")
    def _():
        # **A fresh settlement runs at a loss.** 25% of 46 a day against 14 of
        # upkeep is −2.5, so two of them moved a power's income *down* — from 724
        # a day to 720 — which is what the first draft of this check asserted the
        # opposite of. It is a real investment: it costs, then it pays.
        game = new_game("ground-income")
        power = "freeholds"
        before = ex.income(game, power)
        sites = settle.sites_for(game, power)
        assert len(sites) >= 2
        for system, body, _good in sites[:2]:
            settle.found(game, system, body, power)
        fresh = ex.income(game, power)
        assert fresh < before, (
            f"two newly planted settlements raised income from {before:,.0f} to "
            f"{fresh:,.0f}; a settlement that pays from day one is not an "
            "investment")

        game.day += int(MATURE_DAYS)
        grown = ex.income(game, power)
        assert grown > before, (
            f"income is {grown:,.0f} against {before:,.0f} with two mature "
            "settlements — they never come good")
        assert abs((grown - before) - settle.income(game, power)) < 1e-6, (
            "the exchequer's idea of settlement income is not the settlement "
            "module's")
        row = next(r for r in ex.ledger(game) if r["power"] == power)
        assert row["settlements"] == 2, row
        assert abs(row["ground"] - settle.income(game, power)) < 1e-6

        # And the works board prices it on the true figure, ramp included, so a
        # power choosing between settling and founding a berth chooses on facts.
        works = ex.works_open(game, power)
        settling = [w for w in works if w[2].startswith("settle:")]
        assert settling, "the exchequer never offers to settle anything"
        assert all(w[0] == FOUND_COST for w in settling), settling
        quoted = ex.payback(game, power, FOUND_COST, settling[0][2])
        naive = FOUND_COST / (YIELD - UPKEEP)
        assert abs(quoted - settle.payback_days()) < 1e-6
        assert quoted > naive * 1.2, (
            f"the board quotes {quoted:,.0f} days where the mature rate alone "
            f"says {naive:,.0f} — the loss-making years are not being counted")
        return (f"income {before:,.0f} → {fresh:,.0f} when planted → "
                f"{grown:,.0f} grown; the board says {quoted:,.0f} days, not "
                f"{naive:,.0f}")
