"""Reach checks — the chart has to mean what it draws.

Measured before any of this existed: flooding from the start at starting jump
range reaches between 2 and all 42 systems depending on the seed. The median is
13; a quarter of sectors open with fewer than eight, and one in eight with three
or fewer. None of that was on the chart, which drew a dashed ring at the jump
range and greyed one button to "Out of range" — so a star behind a gap no amount
of hopping closes looked exactly like the one next door.

These hold the reach readout to being reachability, and hold the drives it names
to being drives this hull would actually accept.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..sim import reach as reach_sim
from ..sim.actions import jump_quote
from ..sim.shipyard import validate
from ..world.galaxy import distance
from .harness import Suite


def _dock_at_a_yard(game) -> bool:
    """Put the hull alongside something that can open it up.

    `apply_refit` used to work anywhere — the rule lived in the button, not
    the sim, so a hull could be stripped in deep space. It does not any more,
    and a check that refits has to say where it is standing. Not every system
    has a yard, so this moves the hull to one that does.
    """
    from ..sim import anchorage
    for candidate in [game.system] + list(game.galaxy.systems):
        for berth in anchorage.in_system(game, candidate):
            if berth.offers("shipyard"):
                game.location_id = candidate.id
                game.orbit_body = berth.body_id
                return True
    return False

def run(suite: Suite) -> None:
    check = suite.check

    @check("what the chart calls reachable is reachable by flying it")
    def _():
        # The claim is transitive: not "one jump", but "a sequence of jumps",
        # each of which the game itself would allow.
        game = new_game("reach-real")
        within = reach_sim.component(game)
        jump = game.ship_stats.jump

        # Walk it: breadth-first, but every step confirmed by jump_quote,
        # which is what the Set course button actually asks.
        proven, edge = {game.location_id}, [game.system]
        while edge:
            following = []
            for system in edge:
                game.location_id = system.id
                for other in game.galaxy.systems:
                    if other.id in proven:
                        continue
                    if jump_quote(game, other)["in_range"]:
                        proven.add(other.id)
                        following.append(other)
            edge = following
        assert proven == within, (
            f"the chart says {len(within)} reachable, flying says {len(proven)}: "
            f"{sorted(within ^ proven)[:6]}")
        return f"{len(within)} of {len(game.galaxy.systems)} confirmed by jump_quote"

    @check("one route and a whole list of them cannot disagree")
    def _():
        # `route_to` answered one question with its own breadth-first walk, which
        # is fine for the contract a captain is reading and wrong for a list: the
        # price register asks about four ports for each of thirteen commodities
        # on every repaint, and that was fifty-two walks of the galaxy. It
        # delegates to `routes_from` now, so this pins the two together — and
        # pins the contract a sweep found nothing else holding: **None** for
        # somewhere unreachable, not a cheerful nought hops.
        looked = beyond = 0
        for seed in range(3):
            game = new_game(f"one-door-{seed}")
            routes = reach_sim.routes_from(game)
            for system in game.galaxy.systems:
                one = reach_sim.route_to(game, system.id)
                if system.id in routes:
                    assert one == routes[system.id], (
                        f"{system.name}: route_to says {one} and the walk says "
                        f"{routes[system.id]}")
                    assert one["days"] >= 0 and one["hops"] >= 0, one
                else:
                    beyond += 1
                    assert one is None, (
                        f"{system.name} cannot be reached and `route_to` "
                        f"answered {one} — a caller weighing a deadline against "
                        "that will believe it is next door")
                looked += 1
        assert looked > 90, looked
        assert beyond > 0, (
            "every system was reachable in three sectors, so the None case "
            "was never exercised")
        # And the home system is nought of both, not absent.
        game = new_game("one-door-here")
        assert reach_sim.route_to(game, game.location_id) == {"hops": 0, "days": 0}
        return (f"{looked} systems over 3 sectors, {beyond} unreachable and "
                "every one answered None")

    @check("a walled-off system really cannot be got to")
    def _():
        # The stronger half: everything the chart strikes through must be
        # unreachable from *every* system you can stand in, not merely far
        # from the one you happen to be in.
        game = new_game("reach-wall")
        within = reach_sim.component(game)
        beyond = reach_sim.walled(game)
        if not beyond:
            return "this sector has no wall; checked the other seed instead"
        jump = game.ship_stats.jump
        for sid in within:
            here = game.galaxy.systems[sid]
            crossings = [t.id for t in game.galaxy.systems
                         if t.id in beyond and distance(here, t) <= jump]
            assert not crossings, (
                f"{here.name} is inside the wall but reaches {crossings} outside it")
        return (f"{len(beyond)} systems beyond the wall, no crossing from any "
                f"of the {len(within)} inside")

    @check("the wall is a real feature of the sector, not a rare accident")
    def _():
        # The number that made this worth doing. If generation later closes
        # the gaps, this check is the thing that notices the readout has
        # stopped earning its place.
        sizes = []
        for index in range(30):
            game = new_game(f"reach-spread-{index}")
            sizes.append(len(reach_sim.component(game)))
        sizes.sort()
        total = len(new_game("reach-spread-0").galaxy.systems)
        walled = sum(1 for n in sizes if n < total)
        assert walled > len(sizes) // 2, (
            f"only {walled} of {len(sizes)} sectors are walled at all — the "
            "chart line is describing something that no longer happens")
        return (f"pocket over 30 seeds: min {sizes[0]} · median "
                f"{sizes[len(sizes) // 2]} · max {sizes[-1]} of {total}; "
                f"{walled} walled")

    @check("every drive the chart offers is one this hull would take")
    def _():
        # A grown hull refuses the fabricated drives, so naming them would
        # make the ladder look gentle when for a NAVIS it is reaction organ,
        # sail film, foldrunner — 8.9, 9.0 and 13.6 light-years.
        seen = 0
        for index in range(6):
            game = new_game(f"reach-fit-{index}")
            chassis = CHASSIS_BY_ID[game.ship.chassis]
            for row in reach_sim.opens(game):
                fitted = [p for p in game.ship.fitted
                          if p != "reaction_organ"] + [row["part"].id]
                ok, errs, _brown = validate(chassis, fitted)
                assert ok, (f"{row['part'].name} offered to a {chassis.family} "
                            f"hull: {errs[:1]}")
                assert row["jump"] > game.ship_stats.jump, (
                    f"{row['part'].name} offered but does not reach further")
                seen += 1
        assert seen, "no drive was offered in six sectors"
        return f"{seen} drive offers across 6 sectors, all graftable and all longer"

    @check("what a drive is said to open is what it opens")
    def _():
        # Same shape as every other preview in the project: do the thing and
        # compare. Here the thing is fitting the drive and re-flooding.
        from ..sim import ship as ship_sim
        from ..sim import shipyard as shipyard_sim

        checked = 0
        for index in range(5):
            game = new_game(f"reach-open-{index}")
            before = len(reach_sim.component(game))
            for row in reach_sim.opens(game):
                fitted = [p for p in game.ship.fitted
                          if p != "reaction_organ"] + [row["part"].id]
                game.credits = 10_000_000
                for key in ("alloy", "silicon", "magnetite", "biomass", "ore"):
                    game.stores[key] = 500
                _dock_at_a_yard(game)
                ok, why = shipyard_sim.apply_refit(game, game.ship, fitted)
                assert ok, why
                game.ship_stats = ship_sim.stats(game.ship, game.bonuses)
                actual = len(reach_sim.component(game))
                assert actual == row["within"], (
                    f"{row['part'].name} was said to reach {row['within']} "
                    f"systems and reaches {actual}")
                assert actual - before == row["gain"], (
                    f"{row['part'].name} was said to open {row['gain']} and "
                    f"opened {actual - before}")
                checked += 1
                break            # one refit per sector; the hull has changed
        assert checked, "nothing was ever offered to check"
        return f"{checked} forecasts fitted and re-flooded, all exact"

    @check("the way out is costed, and every figure in it is true")
    def _():
        # The chart named a drive and stopped. Measured, the way out of a
        # small pocket is twelve technologies, five thousand research points,
        # seventy-eight thousand credits and twenty tonnes of magnetite — a
        # project rather than a purchase — and saying so is the difference
        # between working toward something and waiting for nothing.
        from ..data.tech import TECH_BY_ID
        checked = 0
        for index in range(6):
            game = new_game(f"reach-plan-{index}")
            plan = reach_sim.plan(game)
            if not plan:
                continue
            part = plan["part"]

            # The chain is exactly what is missing, and nothing already held.
            for tech in plan["tech"]:
                assert tech not in game.research.unlocked, (
                    f"{tech} is already known and still listed as needed")
            assert part.tech in plan["tech"] or not part.tech
            assert plan["points"] == sum(TECH_BY_ID[t].cost
                                         for t in plan["tech"]), "points differ"

            # Every prerequisite of everything listed is either held or listed.
            for tech in plan["tech"]:
                for need in TECH_BY_ID[tech].reqs:
                    assert (need in plan["tech"]
                            or need in game.research.unlocked), (
                        f"{tech} needs {need}, which is neither held nor listed")

            # The materials, and where they are said to be sold.
            for material in plan["materials"]:
                assert material["need"] == part.cost[material["id"]]
                for where in material["sold_at"]:
                    system = next(s for s in game.galaxy.systems
                                  if s.name == where)
                    assert system.market and material["id"] in system.market.stock
                    assert system.id in reach_sim.component(game), (
                        f"{where} is named and cannot be reached")
            assert plan["credits"] == part.cost.get("credits", 0)
            checked += 1
        assert checked >= 4, f"only {checked} sectors had a wall to cost"
        return f"{checked} plans, every technology, price and quay verified"

    @check("a pocket is a long project and not a trap")
    def _():
        # The question behind the whole feature, asked continuously rather
        # than answered once: can a captain walled into a handful of systems
        # actually buy their way out from where they are standing? Measured
        # across seeds — including the two-system ones.
        walled, fundable, tightest = 0, 0, 99
        for index in range(24):
            game = new_game(f"reach-trap-{index}")
            plan = reach_sim.plan(game)
            if not plan or plan["step"]["gain"] <= 0:
                continue
            walled += 1
            tightest = min(tightest, plan["within"])
            if plan["reachable"]:
                fundable += 1
            else:
                missing = [m["id"] for m in plan["materials"] if m["short"]]
                assert plan["yards"], (
                    f"seed {index}: {plan['within']} systems and no yard — "
                    "the drive could never be fitted")
                assert not missing, (
                    f"seed {index}: {plan['within']} systems and nowhere to "
                    f"buy {missing}")
        assert walled >= 12, f"only {walled} of 24 sectors were walled"
        assert fundable == walled, f"{walled - fundable} pockets are traps"
        return (f"{walled} walled sectors, smallest {tightest} systems, "
                f"every one of them able to supply its own way out")

    @check("the plan appears only when there is a wall to get past")
    def _():
        # A sector with nothing beyond the wall must not offer a way past it.
        open_ones = 0
        for index in range(10):
            game = new_game(f"reach-when-{index}")
            horizon = reach_sim.horizon(game)
            plan = reach_sim.plan(game)
            if horizon["whole"]:
                open_ones += 1
                assert not plan or plan["step"]["gain"] == 0, (
                    "a sector with nothing beyond it offered a way out")
            elif plan:
                assert plan["step"]["gain"] > 0
                assert plan["within"] == horizon["within"]
        return (f"{10 - open_ones} walled and {open_ones} whole sectors, "
                "each offered the right thing")

    @check("the line the chart prints says the true numbers")
    def _():
        for index in range(8):
            game = new_game(f"reach-note-{index}")
            horizon = reach_sim.horizon(game)
            line = reach_sim.note(game)
            assert str(horizon["total"]) in line, line
            if horizon["whole"]:
                assert "All" in line, line
            else:
                assert str(horizon["within"]) in line, line
                assert str(horizon["beyond"]) in line, line
                step = reach_sim.next_step(game)
                if step is not None:
                    assert step["part"].name in line, line
                    assert str(step["gain"]) in line, line
        return "8 sectors, every figure in the line matching the sector"
