"""Bloom checks — the middle of the arc.

The Bloom had two ends and very little between them: growth is detected, it
spreads on a timer, and eventually you burn into the heart. Nothing you did to
it changed what it did to you, and the setting's central tension — that the
thing worth understanding is the thing worth destroying — was described in the
codex and modelled nowhere.

These hold provocation to being felt, and the study option to actually costing
something.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.responses import PROVOCATION, RESPONSES, STUDY_FLOOR
from ..sim import bloom as bloom_sim
from ..sim import inquiry
from ..sim import responses as response_sim
from .harness import Suite


def _infested(seed: str, mass: float = 0.6):
    game = new_game(seed)
    game.credits = 300000
    system = game.system
    system.bloom = mass
    return game, system


def run(suite: Suite) -> None:
    check = suite.check

    @check("every response is reachable and fires in order")
    def _():
        thresholds = [r.at for r in RESPONSES]
        assert thresholds == sorted(thresholds), (
            f"responses are not in ascending order: {thresholds}")
        assert all(r.text and r.name for r in RESPONSES), "a response says nothing"
        assert all(r.growth >= 1.0 for r in RESPONSES), (
            "a response makes the Bloom grow more slowly")

        game, _sys = _infested("responses")
        rng = RNG("responses")
        seen = []
        for step in range(1, 40):
            response_sim.provoke(game, "heart")     # the heaviest provocation
            for _kind, text in response_sim.check(game, rng):
                seen.append(text.split(".")[0])
            if len(response_sim.fired(game)) == len(RESPONSES):
                break
        assert len(response_sim.fired(game)) == len(RESPONSES), (
            f"only {len(response_sim.fired(game))} of {len(RESPONSES)} ever fired")
        assert response_sim.fired(game) == [r.id for r in RESPONSES], (
            f"fired out of order: {response_sim.fired(game)}")
        # And never twice.
        again = response_sim.check(game, rng)
        assert not again, f"a response fired a second time: {again}"
        return " → ".join(response_sim.fired(game))

    @check("what you do to it is what provokes it")
    def _():
        game, _sys = _infested("provoke")
        assert response_sim.level(game) == 0.0, "it starts out annoyed"
        for kind in ("burn", "cleared", "instar", "heart"):
            before = response_sim.level(game)
            response_sim.provoke(game, kind)
            gained = response_sim.level(game) - before
            assert abs(gained - PROVOCATION[kind]) < 0.001, (
                f"{kind} moved provocation by {gained}, not {PROVOCATION[kind]}")
        peak = response_sim.level(game)

        # And it bleeds away when left alone.
        response_sim.decay(game, 365)
        assert response_sim.level(game) < peak, "provocation never fades"
        response_sim.decay(game, 10_000)
        assert response_sim.level(game) == 0.0, "provocation went negative"
        return f"peaked at {peak:.0f}, faded to nothing"

    @check("being provoked genuinely makes it grow faster")
    def _():
        # The multiplier was computed and read by nothing at all for a while —
        # the venture-counter bug in another costume.
        def spread(forced, seed):
            game = new_game(seed)
            state = response_sim.state(game)
            state.responses = list(forced)
            state.stage = 2
            for system in game.galaxy.systems[:8]:
                system.bloom = 0.3
            start = sum(s.bloom for s in game.galaxy.systems)
            for _ in range(6):
                game.advance_days(180)
            return sum(s.bloom for s in game.galaxy.systems) - start

        # **Twenty sectors, and it took three widenings to get here.** The
        # first draft measured a single seed and was passing on luck; eight
        # sectors with a "beaten in at most two" tally went red for the
        # addition of a star class, and again for the powers being given
        # money — neither of which touches the Bloom, both of which re-roll
        # what the sectors look like.
        #
        # The effect is real and noisy. Three years of growth in a forty-two
        # system sector runs close to saturation, which compresses the gap, so
        # per-sector the provoked side loses about a quarter of the time.
        # Measured over twenty: **+8.5% aggregate, ahead in 15**. The
        # aggregate is the measurement; the tally is a share rather than a
        # count now, so widening the sample makes it *more* stable instead of
        # inviting another round of the same edit.
        angry_id = [r.id for r in RESPONSES]
        seeds = ["growth"] + [f"growth-{n}" for n in range(1, 20)]
        calm = angry = 0.0
        agreed = 0
        for seed in seeds:
            one, two = spread([], seed), spread(angry_id, seed)
            calm += one
            angry += two
            agreed += two > one
        assert response_sim.growth_multiplier(new_game("x")) == 1.0, (
            "an unprovoked Bloom already grows faster")
        assert angry > calm * 1.04, (
            f"a fully provoked Bloom spread {angry:.1f} across eight sectors "
            f"against {calm:.1f} calm — the multiplier is not reaching the "
            "growth")
        assert agreed >= 0.65 * len(seeds), (
            f"provoked growth won in only {agreed} of {len(seeds)} sectors "
            f"({agreed / len(seeds):.0%}); it is ahead in about three quarters "
            "of them when the multiplier is reaching the growth")
        return (f"spread {calm:.1f} calm → {angry:.1f} provoked over "
                f"{len(seeds)} sectors, ahead in {agreed} of them")

    @check("provoked far enough, it comes after you")
    def _():
        game, _sys = _infested("hunt")
        for system in game.galaxy.systems[:6]:
            system.bloom = 0.7          # somewhere for masses to detach from
        state = response_sim.state(game)
        state.stage = 3
        rng = RNG("hunt")
        for _ in range(30):
            response_sim.provoke(game, "heart")
            response_sim.check(game, rng)
            if response_sim.hunting(game):
                break
        assert response_sim.hunting(game), "it never started hunting"
        aimed = [i for i in state.instars if i.target_id == game.location_id]
        assert aimed, "hunting, but nothing is aimed at the player"
        return f"{len(aimed)} mass(es) aimed at the hull"

    @check("studying a mass pays, and feeds it")
    def _():
        game, system = _infested("study", mass=0.55)
        before_mass = system.bloom
        before_readings = inquiry.held(game.research, "reading")
        before_xeno = game.ship.cargo.get("xenolith", 0)

        ok, why = response_sim.can_study(game, system)
        assert ok, f"cannot study a 55% mass: {why}"
        result = response_sim.study(game, system)
        assert result["ok"], result.get("why")
        assert game.ship.cargo.get("xenolith", 0) > before_xeno, "no xenolith"
        assert inquiry.held(game.research, "reading") > before_readings, (
            "studying the Bloom taught nothing")
        assert system.bloom > before_mass, (
            "the mass did not grow while it was being studied")
        return (f"{result['xenolith']:.1f} t and {result['readings']:.0f} readings; "
                f"mass {before_mass:.2f} → {system.bloom:.2f}")

    @check("a burnt-out system has nothing left to learn from")
    def _():
        # The tension only exists if the two are exclusive on the same mass.
        game, system = _infested("exclusive", mass=0.5)
        assert response_sim.can_study(game, system)[0]
        system.bloom = STUDY_FLOOR - 0.01
        ok, why = response_sim.can_study(game, system)
        assert not ok and why, "a burnt-out system is still worth studying"
        refused = response_sim.study(game, system)
        assert not refused["ok"], "studied a system with nothing in it"
        return "below the floor, there is nothing to read"

    @check("the arc survives a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game, _sys = _infested("persist-bloom")
        rng = RNG("persist")
        for _ in range(6):
            response_sim.provoke(game, "heart")
            response_sim.check(game, rng)
        before = (round(response_sim.level(game), 3),
                  list(response_sim.fired(game)))
        assert before[1], "nothing had fired to persist"

        back = decode(json.loads(json.dumps(encode(game))))
        after = (round(response_sim.level(back), 3),
                 list(response_sim.fired(back)))
        assert after == before, f"{after} != {before}"
        assert response_sim.growth_multiplier(back) > 1.0, (
            "the growth multiplier was lost over a save")
        return f"provocation {after[0]:.0f} and {len(after[1])} response(s) kept"
