"""Plotting the jump: the first thing in this game to ask for Astrogation.

The 2d6 grammar landed and the life path teaches thirty-one skills. Audited
across the package, **three of them are never asked for by anything** —
`tactics`, `gunnery` and `astrogation` — and those three are exactly the
skills that describe running a starship. Every skill the game rolls is
person-scale, out of the Afoot layer.

This is the first of the three brought across, on the reading Traveller is
clearest about: astrogation is jump accuracy. You do not roll to arrive, you
roll for *where* — and a jump in SEEDFALL had always arrived at exactly the
same point, `(0, -ARRIVAL_RADIUS, 0)`, in every system, for every captain.

The claims:

- **Nought is the mark the game has always used**, to the metre, so a plot
  is a change no existing chronicle has to notice.
- **Whoever plots best plots** — the skill *and* the characteristic behind
  it, not the biggest number in one column.
- **A hull plots its own jumps.** A crew with no astrogator is no better
  than the board, not worse than nothing.
- **A longer jump is a harder plot**, on rungs chosen against the sector's
  own measured legs rather than out of the air.
- **Preview equals act**: the Helm quotes the throw the jump makes.
- **And it costs the chronicle nothing it did not already spend** — the
  plot's dice are its own, not the shared counter every other roll comes
  off.
"""

from __future__ import annotations

import collections
import math
import statistics

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import astrogation as astro
from ..sim import checks
from ..sim.flight import ARRIVAL_RADIUS
from ..world.galaxy import distance
from .harness import Suite

#: The mark every jump in this game arrived at before plots existed.
MARK = (0.0, -ARRIVAL_RADIUS, 0.0)


def _legs(seeds: int = 4) -> list:
    """The jumps a captain actually makes: near-neighbour legs."""
    out = []
    for n in range(seeds):
        game = new_game(f"legs-{n}")
        for system in game.galaxy.systems:
            near = sorted(distance(system, other)
                          for other in game.galaxy.systems
                          if other.id != system.id)
            out.extend(ly for ly in near[:3] if ly < 30)
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("an effect of nought is the arrival the game has always had")
    def _():
        game = new_game("mark")
        found = None
        for n in range(400):
            got = astro.plot(game, RNG(f"mark-{n}"), 7.0)
            if got.effect == 0:
                found = got
                break
        assert found is not None, "no plot in 400 came out exactly on the mark"
        where = astro.landfall(found, RNG("bearing"))
        assert math.dist(where, MARK) == 0.0, (where, MARK)
        assert astro.drift_au(found) == 0.0
        return (f"an Effect of 0 puts the hull at {MARK[1]:.2f} AU on the "
                "line, which is where every jump in this game has arrived")

    @check("whoever plots best plots, not whoever holds the most of it")
    def _():
        # The fault this is written against: picking the biggest skill and
        # then throwing *that* person's characteristic put an officer with
        # Astrogation 1 and Education 2 on the board ahead of a machine
        # that would have done it better.
        rows = []
        for n in range(12):
            game = new_game(f"best-{n}")
            skill, score, who = astro.plotter(game)
            worth = skill + checks.modifier(score)
            board = astro.HULL_PLOTS + checks.modifier(astro.BOARD_EDU)
            assert worth >= board, (who, skill, score, worth, board)
            # And nobody aboard beats the chosen plotter.
            from ..sim import lifepath
            for officer in game.officers:
                life = lifepath.of(game, officer)
                theirs = (life.skill(astro.SKILL)
                          + checks.modifier(life.score("edu")))
                assert theirs <= worth, (officer.name, theirs, worth)
            rows.append((who, worth))
        assert len(rows) >= 12, rows
        best = max(rows, key=lambda r: r[1])
        return (f"{len(rows)} chronicles, every board taken by the best plot "
                f"aboard; the best of them {best[0]} at {best[1]:+d}")

    @check("a hull plots its own jumps, so no astrogator is not a penalty")
    def _():
        game = new_game("board")
        # Strip every astrogator: the board should take it, at nought.
        from ..sim import lifepath
        for officer in list(game.officers):
            lifepath.of(game, officer).skills.pop(astro.SKILL, None)
        skill, score, who = astro.plotter(game)
        assert skill >= astro.HULL_PLOTS, (who, skill)
        assert skill > checks.UNTRAINED, (
            "a crew with no astrogator is plotting worse than a machine")
        # And the board is worth nothing either way as a characteristic.
        assert checks.modifier(astro.BOARD_EDU) == 0, astro.BOARD_EDU
        return (f"with nobody aboard who holds it the plot is made at "
                f"{astro.HULL_PLOTS}, not {checks.UNTRAINED}")

    @check("a longer jump is a harder plot, on the sector's own distances")
    def _():
        legs = _legs()
        assert len(legs) >= 200, len(legs)
        median = statistics.median(legs)
        rungs = collections.Counter(astro.how(ly) for ly in legs)
        # The ordinary leg is an ordinary plot. Measured at 2.0/3.5 — the
        # first draft's guess — the median leg came out *difficult* and
        # most arrivals in the game would have been wide ones.
        assert astro.how(median) == "average", (median, astro.how(median))
        assert rungs["average"] > rungs["difficult"], rungs
        # And it is monotone: further is never easier.
        game = new_game("harder")
        was = 1.1
        for ly in range(1, 30):
            odds = astro.forecast(game, float(ly))["chance"]
            assert odds <= was + 1e-9, (ly, odds, was)
            was = odds
        return (f"{len(legs)} legs, median {median:.1f} ly — "
                + " · ".join(f"{k} {v}" for k, v in rungs.most_common()))

    @check("the odds the Helm quotes are the odds the jump throws")
    def _():
        rows = 0
        for n in range(6):
            game = new_game(f"quoted-{n}")
            for ly in (3.0, 7.0, 11.0):
                said = astro.forecast(game, ly)
                got = astro.plot(game, RNG(f"{n}-{ly}"), ly)
                assert got.how == said["how"], (got.how, said["how"])
                want = checks.chance(said["skill"], said["score"], got.how)
                assert abs(want - said["chance"]) < 1e-9, (want, said)
                rows += 1
        assert rows >= 18, rows
        return (f"{rows} quotes, every one of them the throw the jump makes")

    @check("a good plot comes in and a bad one goes wide, and the quote is true")
    def _():
        game = new_game("wide")
        near = far = 0
        worst = 0.0
        for n in range(500):
            got = astro.plot(game, RNG(f"w{n}"), 7.0)
            where = astro.landfall(got, RNG(f"b{n}"))
            reach = math.dist((0.0, where[1], 0.0), (0.0, 0.0, 0.0))
            if got.effect > 0:
                near += 1
                assert reach < ARRIVAL_RADIUS, (got.effect, reach)
                assert where[0] == 0.0 and where[2] == 0.0, where
            elif got.effect < 0:
                far += 1
                assert reach > ARRIVAL_RADIUS, (got.effect, reach)
                assert where[0] or where[2], "a miss that is not sideways"
            # And what a screen would have said is what happened.
            worst = max(worst, abs(math.dist(where, MARK)
                                   - astro.drift_au(got)))
        assert near and far, (near, far)
        assert worst < 1e-9, worst
        return (f"{near} plots in and {far} out of 500; the quoted drift and "
                "the arrival never differed by so much as a metre")

    @check("the plot spends no dice the chronicle was counting on")
    def _():
        """`game.rng(tag)` advances a counter every other roll comes off.

        Plotting off it moved every draw after the jump: measured, the
        careful captain stopped reaching its ending on one seed of four
        **with the arrival pinned to the old mark**, which is how the
        landfall was ruled out as the cause. The same fault
        `sim/patrons.attach` records.
        """
        from ..sim import actions
        game = new_game("nodice")
        target = next(s for s in game.galaxy.systems
                      if s.id != game.location_id
                      and distance(s, game.system) <= game.ship_stats.jump)
        game.ship.cargo["volatiles"] = 900
        before = game.rng_seed
        got = actions.jump_to(game, target.id)
        assert got["ok"], got
        assert got.get("plot") is not None, got
        after = game.rng_seed
        # The jump spends the counter for its own events; what matters is
        # that plotting it did not add draws of its own.
        again = new_game("nodice")
        again.ship.cargo["volatiles"] = 900
        import seedfall.sim.astrogation as module
        held = module.plot
        module.plot = lambda g, rng, ly: held(g, RNG("fixed"), ly)
        actions.jump_to(again, target.id)
        module.plot = held
        assert again.rng_seed == after, (again.rng_seed, after)
        assert after != before, "the jump spent no luck at all; check the arms"
        return ("the jump's own events moved the counter and the plot did "
                "not: the same landing with the dice fixed leaves it on the "
                "same number")
