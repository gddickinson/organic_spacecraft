"""Time: who ages, who eats, and the two clocks that stopped agreeing.

Everyone aboard used to be the same thing — immortal, breathing, and eating
nothing. The opening screen sold a Dry Choir lineage on "no air to run out of"
and the daily tick asphyxiated it on schedule.

These checks hold three claims:

- **Lineages differ where the screen says they differ.** Not merely that the
  numbers differ, but that the promised consequence lands: a recording aboard
  a hull with no air survives it.
- **Time is relative and the split is honest.** Sector time drives deadlines
  and markets; ship time drives ageing, upkeep, repair and research. A hard
  burn has to buy less ageing *and* cost real progress, or it is a free win.
- **A crossing states what it will do before it does it.**
"""

from __future__ import annotations

import copy

from ..core.state import new_game
from ..data.crossings import CROSSINGS, CROSSINGS_BY_ID
from ..data.lineages import LINEAGES, LINEAGES_BY_ID
from ..sim import lifespan, upkeep
from ..sim.actions import jump_quote
from ..sim.beginning import Choices
from .harness import Suite


def _of(stock: str, seed: str = "time"):
    return new_game(seed, 42, Choices(stock=stock, origin="surveyor",
                                      hull="navis", posting="charter",
                                      crew=(), name="Test"))


def run(suite: Suite) -> None:
    check = suite.check

    @check("a lineage is a substrate, and no two of them cost the same")
    def _():
        assert len(LINEAGES) >= 3, "one kind of person is not a choice"
        seen = set()
        for lineage in LINEAGES:
            assert lineage.span > lineage.prime > 0, lineage.id
            assert lineage.ageing > 0, f"{lineage.id} is outside time entirely"
            assert lineage.upkeep, f"{lineage.id} consumes nothing at all"
            key = (tuple(sorted(lineage.upkeep)), lineage.breathes)
            seen.add(key)
        assert len(seen) > 1, "every lineage eats the same things"
        # The headline claim: exactly one of them does not breathe, and it is
        # the one the opening screen sells on not breathing.
        assert not LINEAGES_BY_ID["dry"].breathes
        assert LINEAGES_BY_ID["wet"].breathes
        return (f"{len(LINEAGES)} lineages, {len(seen)} distinct upkeep "
                "profiles, spans from "
                f"{min(l.span for l in LINEAGES):.0f} to "
                f"{max(l.span for l in LINEAGES):.0f} years")

    @check("the Choir does not suffocate, which is what the screen promised")
    def _():
        # The opening offers Dry as "no air to run out of". The daily tick ran
        # one air block for everybody and killed recordings by asphyxiation on
        # exactly the same schedule as a wet crew.
        out = {}
        for stock in ("wet", "dry"):
            game = _of(stock, f"air-{stock}")
            before = game.ship.crew
            # Hold the breach open. Advancing 120 days in one call does not
            # work: `repair_tick` heals the life layer back over twenty
            # percent, air_ok goes true again and the air comes back — which
            # is the game behaving correctly and the check measuring nothing.
            for _ in range(120):
                for layer in game.ship.layers:
                    if layer.life:
                        layer.hp = 0.0
                game.ship.o2 = 0.0
                game.advance_days(1)
                if game.dead:
                    break
            out[stock] = (before, game.ship.crew, game.dead)
        wet_before, wet_after, _wd = out["wet"]
        dry_before, dry_after, dry_dead = out["dry"]
        assert wet_after < wet_before, (
            "a wet crew survived four months with no air, so this proves "
            "nothing about the Choir")
        assert dry_after == dry_before and not dry_dead, (
            f"a Dry Choir crew went from {dry_before} to {dry_after} with the "
            "air gone — the screen says they have none to run out of")
        return (f"no air for 120 days: wet {wet_before}→{wet_after}, "
                f"Choir {dry_before}→{dry_after}")

    @check("everyone aboard is provisioned with what they actually eat")
    def _():
        # A Choir hull stocked with biomass and no silicon is a captain
        # punished on day one for a choice made on the character screen.
        lines = []
        for stock in ("wet", "dry", "grafted"):
            game = _of(stock, f"prov-{stock}")
            plan = upkeep.forecast(game, 200)
            assert plan["need"], f"{stock} consumes nothing"
            assert plan["ok"], (
                f"a {stock} hull launches short of "
                f"{', '.join(plan['short'])} for a 200-day crossing")
            lines.append(f"{stock}: " + ", ".join(sorted(plan["need"])))
        return " · ".join(lines)

    @check("time passes for the people, and differently for each lineage")
    def _():
        # Asked as a *rate*, because a chronicle nobody flies does not last
        # ten years. Measured under the honest clock: an idle wet captain
        # reaches ruin on day 2100 and a grafted one on day 2760, so "aged in
        # ten years" was reading two lineages over spans that differed by 660
        # days and calling the difference lineage. Per elapsed year the three
        # come out at exactly their table rate, which is the stronger claim
        # anyway: it has no tolerance for a tick that decides per call.
        rate, span = {}, {}
        for stock in ("wet", "dry", "grafted"):
            game = _of(stock, f"age-{stock}")
            # Wages paid. On the opening purse of 1 credit the officers quit
            # around day 1160 and an officer off the roster stops ageing while
            # `age_of` still reads their last age — the old check measured
            # someone who had walked off three years earlier.
            game.credits = 200_000
            who = game.officers[0]
            was = lifespan.age_of(who, game)
            game.advance_days(3650)             # ten years of sector time
            assert who in game.officers, (
                f"the {stock} officer left on day {game.day}, so nothing "
                "below is a measurement of ageing")
            span[stock] = game.ship_day / lifespan.YEAR
            assert span[stock] > 5.0, (
                f"the {stock} chronicle only ran {span[stock]:.1f} years")
            rate[stock] = (lifespan.age_of(who, game) - was) / span[stock]
            want = lifespan.lineage_of(who, game).ageing
            assert abs(rate[stock] - want) < 0.01, (
                f"a {stock} officer aged {rate[stock]:.3f} years per elapsed "
                f"year, and their lineage ages at {want}")
        assert rate["dry"] < rate["grafted"] < rate["wet"], (
            f"lineages age in the wrong order: {rate}")
        return " · ".join(f"{k} {rate[k]:.2f}y/y over {span[k]:.1f}y"
                          for k in rate)

    @check("a long enough chronicle ends a career, and opens the berth")
    def _():
        from ..sim import legacy as legacy_sim
        span = LINEAGES_BY_ID["wet"].span
        game = _of("wet", "span")
        # Wages paid, because an officer who is not paid *leaves*, and an
        # officer off the roster is never handed to `lifespan.tick` again —
        # they stop ageing where they stood while `age_of` goes on reporting
        # that last age. Measured on the opening purse: this one walked off at
        # 98, the roster was empty by day 12515, and the loop below spent the
        # remaining thirty-four years waiting for a retirement that could no
        # longer happen. Funded, they retire at 101.8 in the eighth year.
        game.credits = 200_000
        who = game.officers[0]
        who.age = span - 2
        start_level = who.level
        epochs = 0
        for _ in range(40):
            game.advance_days(365)
            if getattr(who, "retired", False):
                break
            assert who in game.officers, (
                f"{who.name} left the roster on day {game.day} without "
                "retiring, and nothing after this would be a measurement")
            # **The sector's story can end before a career does**, and the
            # clock stops dead when it does: `advance_days` returns on
            # `game.victory`. This check used to run its forty years on the
            # assumption that it would not happen, and got away with it only
            # because the officer usually retired first — the odds of standing
            # a watch eight years past ninety-six are about one in four. So it
            # goes on through the ending the way a player does, which is what
            # `legacy.begin` is for.
            if game.victory and not legacy_sim.in_epoch(game):
                legacy_sim.begin(game, game.victory)
                epochs += 1
        assert getattr(who, "retired", False), (
            f"{who.name} reached {lifespan.age_of(who, game):.0f} and is still "
            "standing a watch")
        assert who not in lifespan.active(game.officers)

        # And the *rate* is the thing worth pinning, not one officer's luck:
        # `END_SLOPE` is named in `sim/lifespan.py` and nowhere else, so if this
        # check only asked "does anybody ever retire" the slope could be any
        # number at all. Measured over a mess deck of sixty, through the same
        # `tick` the clock calls.
        cohort = _of("wet", "cohort")
        crew = []
        for i in range(60):
            hand = copy.deepcopy(cohort.officers[0])
            hand.name = f"Hand {i}"
            hand.age = span + 2
            hand.retired = False
            crew.append(hand)
        cohort.officers = crew
        standing = []
        for year in range(12):
            cohort.ship_day += 365
            lifespan.tick(cohort, 365, cohort.rng(f"cohort-{year}"))
            standing.append(sum(1 for o in crew
                                if not getattr(o, "retired", False)))
        half = next((y for y, n in enumerate(standing, 1) if n <= 30), None)
        assert half is not None, (
            f"sixty hands two years past their span and {standing[-1]} still "
            "aboard twelve years later — past the span is not a slope, it is "
            "a plateau")
        assert 2 <= half <= 8, (
            f"half the cohort was gone after {half} years past their span; "
            f"the slope is wrong. Yearly count: {standing}")
        return (f"{who.name} retired at {lifespan.age_of(who, game):.0f} "
                f"(level {start_level}→{who.level}, {epochs} epoch(s) run "
                f"through); half a cohort gone {half} years past span")

    @check("time is relative: the two clocks part company on a hard burn")
    def _():
        slow, fast = new_game("rel-slow"), new_game("rel-fast")
        slow.advance_days(200, 1.0)
        fast.advance_days(200, 5.0)
        assert slow.day == fast.day == 200, (slow.day, fast.day)
        assert slow.ship_day == 200, slow.ship_day
        assert fast.ship_day == 40, fast.ship_day
        return (f"200 sector days: {slow.ship_day} lived aboard at rest, "
                f"{fast.ship_day} at dilation 5")

    @check("dilation buys years and costs progress — it is not a free win")
    def _():
        slow, fast = new_game("cost-slow"), new_game("cost-fast")
        for game, gamma in ((slow, 1.0), (fast, 6.0)):
            game.advance_days(365, gamma)
        aged = (lifespan.age_of(slow.officers[0], slow)
                - lifespan.age_of(fast.officers[0], fast))
        assert aged > 0.5, (
            f"a year at dilation 6 aged the crew only {aged:.2f} years less "
            "than a year at rest")
        # And the bench: skip the ageing, skip the work.
        assert fast.research.points < slow.research.points * 0.4, (
            f"research at dilation 6 was {fast.research.points:.0f} against "
            f"{slow.research.points:.0f} at rest — the burn was nearly free")
        ate = (slow.ship.cargo.get("biomass", 0)
               < fast.ship.cargo.get("biomass", 0))
        assert ate, "a dilated crew ate as much as one living every day"
        return (f"a year at dilation 6: {aged:.2f} years of ageing saved, "
                f"{slow.research.points - fast.research.points:.0f} research "
                "points forgone")

    @check("a crossing says what it will cost on both clocks before you fly it")
    def _():
        game = new_game("quote")
        target = next(s for s in game.galaxy.systems
                      if s.id != game.location_id)
        quotes = {}
        for how in CROSSINGS:
            q = jump_quote(game, target, how.id)
            assert q["ship_days"] <= q["days"], (
                f"{how.id} claims the crew lives longer than the Verge")
            assert q["dilation"] >= 1.0
            quotes[how.id] = q
        assert quotes["hard"]["fuel"] > quotes["steady"]["fuel"], \
            "a hard burn is free"
        assert quotes["hard"]["ship_days"] < quotes["steady"]["ship_days"], \
            "a hard burn costs more and buys nothing"
        assert quotes["coast"]["fuel"] < quotes["steady"]["fuel"] \
            and quotes["coast"]["days"] > quotes["steady"]["days"], \
            "a coast is not actually cheaper and slower"
        return " · ".join(
            f"{CROSSINGS_BY_ID[k].name}: {v['days']}d out, {v['ship_days']}d "
            f"aboard, {v['fuel']}t" for k, v in quotes.items())

    @check("the quoted crossing is the crossing that gets flown")
    def _():
        # The signature defect of this project is a screen that offers a
        # commitment without stating its consequence. A jump that says six
        # days aboard and lives twenty is exactly that.
        checked = 0
        for how in CROSSINGS:
            game = new_game(f"fly-{how.id}")
            target = next((s for s in game.galaxy.systems
                           if s.id != game.location_id
                           and jump_quote(game, s, how.id)["in_range"]), None)
            if target is None:
                continue
            said = jump_quote(game, target, how.id)
            game.ship.cargo["volatiles"] = said["fuel"] + 5
            day0, ship0 = game.day, game.ship_day
            from ..sim.actions import jump_to
            res = jump_to(game, target.id, how.id)
            assert res.get("ok"), res.get("why")
            assert game.day - day0 == said["days"], (
                f"{how.id}: said {said['days']} sector days, took "
                f"{game.day - day0}")
            assert abs((game.ship_day - ship0) - said["ship_days"]) <= 1, (
                f"{how.id}: said {said['ship_days']} days aboard, lived "
                f"{game.ship_day - ship0}")
            checked += 1
        assert checked >= 2, f"only {checked} crossings were reachable to test"
        return f"{checked} crossings flown, both clocks as quoted"

    @check("going hungry costs, but not before it should")
    def _():
        game = _of("wet", "hunger")
        game.ship.cargo.pop("biomass", None)
        game.stores["biomass"] = 0
        before = game.ship.crew
        game.advance_days(int(upkeep.GRACE) - 1)
        assert game.ship.crew == before, (
            f"lost {before - game.ship.crew} of the crew inside the grace "
            "period — one short leg should not kill anybody")
        game.advance_days(90)
        assert game.ship.crew < before, (
            "three months with an empty hold and nobody went hungry")
        return (f"{before}→{game.ship.crew} after 90 days with no food, "
                f"nothing lost in the first {upkeep.GRACE:.0f}")

    @check("a wait stands down on bad news rather than running through it")
    def _():
        # Played before this existed: a year alongside a Fleet Hub starved
        # three crew one at a time, with credits in the purse and biomass
        # on sale a berth away, while the log said "it is starting to tell"
        # five times and the clock never paused.
        game = _of("wet", "stand-down")
        game.ship.cargo.pop("biomass", None)
        game.stores["biomass"] = 0
        crew = game.ship.crew
        # Waiting again after each stand-down, the way a player who reads
        # the digest and presses on would — clearing whatever question
        # stopped it. The crew must still be alive when the shortage is
        # first reported, because that is the point: there is time to act.
        stops, reported = [], []
        for _ in range(12):
            told = game.wait_days(365)
            stops.append(told["days"])
            reported.extend(told["bad"])
            if told["stopped"] == "bad news" or game.ship.crew < crew:
                break
            game.envoy = game.demand = game.situation = None
        assert sum(stops) < 365, (
            f"a year of starving ran through without standing down: {stops}")
        assert reported, "it stood down and reported nothing at all"
        assert game.ship.crew == crew, (
            f"lost {crew - game.ship.crew} of the crew before the wait "
            "stood down — the whole point is acting before that")
        told = {"days": sum(stops), "stopped": told["stopped"]}

        # And the physical clock is untouched: work that bills its own days
        # bills all of them, hungry or not.
        billed = _of("wet", "billed")
        billed.ship.cargo.pop("biomass", None)
        billed.stores["biomass"] = 0
        was = billed.day
        billed.advance_days(120)
        assert billed.day - was == 120, (
            f"advance_days stood down too — {billed.day - was} of 120")
        return (f"waited {told['days']} of 365 ({told['stopped']}), crew "
                f"intact at {game.ship.crew}; a billed 120 days still 120")

    @check("a wait always stops for a question waiting on an answer")
    def _():
        # An envoy, a demand or an aftermath situation locks the window, so
        # a wait that ran past one buried the very thing it was waiting on.
        # Stands down whatever the option says, which is why it is asked
        # for with the option deliberately off.
        from ..sim import options as options_sim
        from ..sim.approach import Envoy
        game = _of("wet", "answerable")
        options_sim.set_to(game, "wait_stands_down", False)
        game.envoy = Envoy(kind="tribute", faction="charter",
                           expires=game.day + 300)
        told = game.wait_days(90)
        assert told["days"] <= 1, (
            f"waited {told['days']} days with an envoy on the bridge")
        assert "answer" in told["stopped"], told["stopped"]
        return f"stopped in {told['days']} day(s): {told['stopped']}"

    @check("what the crew needs is stated before the crossing, not after")
    def _():
        game = _of("wet", "say")
        line = upkeep.note(game, 400)
        assert "biomass" in line and "400" in line, line
        game.ship.cargo.pop("biomass", None)
        game.stores["biomass"] = 0
        short = upkeep.note(game, 400)
        assert "short" in short.lower(), short
        crossing = lifespan.crossing_note(game, 400)
        assert "ageing" in crossing, crossing
        return f"“{short}” · “{crossing}”"
