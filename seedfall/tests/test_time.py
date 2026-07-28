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
        aged = {}
        for stock in ("wet", "dry", "grafted"):
            game = _of(stock, f"age-{stock}")
            who = game.officers[0]
            was = lifespan.age_of(who, game)
            game.advance_days(3650)             # ten years of sector time
            aged[stock] = lifespan.age_of(who, game) - was
        assert aged["wet"] > 9.5, (
            f"ten years passed and a wet officer aged {aged['wet']:.2f}")
        assert aged["dry"] < aged["grafted"] < aged["wet"], (
            f"lineages age in the wrong order: {aged}")
        return " · ".join(f"{k} aged {v:.1f}y in 10 sector years"
                          for k, v in aged.items())

    @check("a long enough chronicle ends a career, and opens the berth")
    def _():
        game = _of("wet", "span")
        who = game.officers[0]
        who.age = LINEAGES_BY_ID["wet"].span - 2
        start_level = who.level
        for _ in range(40):
            game.advance_days(365)
            if getattr(who, "retired", False):
                break
        assert getattr(who, "retired", False), (
            f"{who.name} reached {lifespan.age_of(who, game):.0f} and is still "
            "standing a watch")
        assert who not in lifespan.active(game.officers)
        return (f"{who.name} retired at {lifespan.age_of(who, game):.0f}, "
                f"level {start_level}→{who.level}")

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
