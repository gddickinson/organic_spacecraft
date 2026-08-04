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

    @check("a captain who fights it meets the Bloom the game describes")
    def _():
        # The whole reason for `STAGE_BY_ANSWERS`: burden only climbs when
        # nobody fights, so stage 3 — adaptation, resistance, the hunt — was
        # reachable only by 3½–5½ years of total neglect, and every game a
        # player actually played killed the antagonist at stage 0. Played as
        # a campaign: burn it back on a clock, watch it answer.
        game = new_game("engaged-captain")
        rng = RNG("engaged")
        st = bloom_sim.ensure(game)
        game.credits = 10 ** 6
        burns = 0
        heart = bloom_sim.heart_system(game)
        # A sector with something to fight — this seed happens to generate
        # no infested neighbours, and the claim is about the arc, not the
        # generator.
        for sysm in game.galaxy.systems[:4]:
            if sysm is not heart:
                sysm.bloom = max(sysm.bloom, 0.6)
        for _round in range(80):
            infested = [s for s in game.galaxy.systems
                        if s.bloom > 0.02 and s is not heart]
            if infested:
                worst = max(infested, key=lambda s: s.bloom)
                game.location_id = worst.id
                response_sim.provoke(game, "burn")
                for w in game.ship_stats.weapons:
                    bloom_sim.record_damage(game, w.family, w.wpn.dmg)
                worst.bloom = max(0.0, worst.bloom - 0.4)
                burns += 1
            for _k, _t in response_sim.check(game, rng):
                pass
            game.bloom_total = sum(s.bloom for s in game.galaxy.systems
                                   if s.bloom > 0.02)
            bloom_sim.review_stage(game, game.bloom_total)
            if st.stage >= 3:
                break
        assert st.stage >= 3, (
            f"{burns} burns and the Bloom never adapted — stage {st.stage}, "
            f"provocation {response_sim.level(game):.0f}")
        assert st.resist, "Adaptive, and resisting nothing"
        assert bloom_sim.resistance(game, next(iter(st.resist))) > 0, (
            "resistance recorded but not felt")
        return (f"stage {st.stage} after {burns} burns; hardened against "
                f"{sorted(st.resist)} — the antagonist shows up for the fight")

    @check("a mass never hunts the system it is standing in")
    def _():
        # `_retarget` could pick the instar's own system — the nearest of the
        # pool — and the mass then "arrived" every twenty days for ever,
        # re-seeding the growth and re-rolling the colony attack each time.
        # Swept over every system as a starting point.
        game, _sys = _infested("retarget-self")
        st = bloom_sim.ensure(game)
        for sysm in game.galaxy.systems:
            inst = bloom_sim.Instar(id=9000 + sysm.id, system_id=sysm.id,
                                    mass=1.0)
            bloom_sim._retarget(game, inst)
            assert inst.target_id != sysm.id, (
                f"an instar at {sysm.name} was sent to {sysm.name}")
        # And a cleaned sector still fields one while the heart lives.
        for s in game.galaxy.systems:
            s.bloom = 0.0
        assert st.heart_hp > 0
        spawned = bloom_sim._spawn_instar(game, RNG("clean-spawn"))
        assert spawned is not None, (
            "a clean sector spawned nothing — the seeding-wave response is "
            "a no-op exactly when a fighting captain earns it")
        assert spawned.system_id == st.heart_system, (
            "the last redoubt is the heart, and it detached from somewhere else")
        return (f"{len(game.galaxy.systems)} starting points, none self-"
                f"targeted; a clean sector still detaches from the heart")

    @check("a refused strike is not an answered one")
    def _():
        # `strike_heart` paid its provocation — 260, the table's largest —
        # before the guards that can refuse it, so shooting from the wrong
        # system enraged the thing you never touched.
        game, _sys = _infested("refused-strike")
        before = response_sim.level(game)
        somewhere_else = next(s for s in game.galaxy.systems
                              if s.id != bloom_sim.ensure(game).heart_system)
        game.location_id = somewhere_else.id
        res = bloom_sim.strike_heart(game, 120, RNG("refused"))
        assert not res["ok"], "the strike was supposed to be refused"
        assert response_sim.level(game) == before, (
            f"a refused strike provoked it: {before} → "
            f"{response_sim.level(game)}")
        return f"refused ('{res['why']}'), and the provocation held at {before:g}"

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
