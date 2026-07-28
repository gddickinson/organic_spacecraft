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
