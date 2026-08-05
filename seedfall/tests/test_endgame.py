"""The Bloom endgame: does it escalate, does it learn, and can it be ended?

Split from `tests/test_play.py` when that file went past five hundred lines,
along the seam its own docstring names — it asks two questions, "can a
chronicle be finished" and "can it jam", and these are the first.

The climax has a shape worth stating: burning the heart provokes it, the
responses that answer detach masses from the origin itself, and those seed
what they reach. So Containment is *clean and dead, in that order* — the
sector the captain cleared before the climax is not the sector they are
standing in after it, and the field has to be finished.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import threat
from ..sim.ship import build_layers, make_ship
from .harness import Suite


def _stocked(seed="endgame"):
    from ..data.tech import TECH
    g = new_game(seed)
    g.research.unlocked = [t.id for t in TECH]
    g.credits = 10_000_000
    for k in ("ore", "volatiles", "phosphate", "biomass", "silicon", "alloy",
              "magnetite", "spidroin", "trehalose", "xenolith"):
        g.stores[k] = 99999
    g.recompute()
    return g


def run(suite: Suite) -> None:
    check = suite.check

    @check("the Bloom escalates and stops being a pushover")
    def _():
        from ..sim import bloom as bloom_sim
        g = new_game("arc-test")
        assert bloom_sim.ensure(g).definition.id == 0, "it should start latent"
        r = RNG("arc")
        seen = []
        for _ in range(12):
            threat.tick(g, 365, r)
            stage = bloom_sim.ensure(g).definition
            if stage.id not in [x.id for x in seen]:
                seen.append(stage)
        assert len(seen) >= 4, (
            f"the Bloom never escalated past {[s.name for s in seen]}")
        assert bloom_sim.ensure(g).instars, "it never put an instar in the field"
        return " → ".join(s.name for s in seen)

    @check("the Bloom learns what you keep shooting it with")
    def _():
        from ..sim import bloom as bloom_sim
        g = new_game("adapt")
        state = bloom_sim.ensure(g)
        state.stage = 3                       # adaptive
        assert bloom_sim.resistance(g, "fabricated") == 0, "starts resistant"
        for _ in range(200):
            bloom_sim.record_damage(g, "fabricated", 30)
        grown = bloom_sim.resistance(g, "grown")
        fab = bloom_sim.resistance(g, "fabricated")
        assert fab > 0.2, f"200 hits taught it nothing: {fab:.2f}"
        assert grown == 0, "it resisted a weapon it never met"
        # and it forgets what you stop using
        bloom_sim.decay_resistance(g, 2000)
        assert bloom_sim.resistance(g, "fabricated") < fab, "it never forgets"
        return f"fabricated resistance {fab:.0%}, grown {grown:.0%}, decays"

    @check("Containment requires reaching and killing the heart")
    def _():
        from ..sim import bloom as bloom_sim
        from ..sim import actions
        g = _stocked("heart")
        for s in g.galaxy.systems:
            s.bloom = 0.0
        g.day = 60
        assert threat.check_victory(g) is None, "cleared the map and won early"

        state = bloom_sim.ensure(g)
        g.location_id = state.heart_system
        state.heart_found = True
        ship = make_ship("bastion", ["fusion_lance", "fusion_lance", "railgun",
                                     "fusion_plant", "fusion_plant", "plasma_drive"])
        build_layers(ship, g.bonuses)
        g.ship = ship
        g.fleet.append(ship)
        g.recompute()
        strikes = 0
        while not bloom_sim.heart_dead(g) and strikes < 40:
            strikes += 1
            for layer in g.ship.layers:
                layer.hp = layer.max
            res = actions.strike_heart(g)
            assert res.get("ok"), res.get("why")
        assert bloom_sim.heart_dead(g), "the heart could not be killed at all"
        # **Bracketed, because `strikes > 1` did not hold `HEART_HP` at all.**
        # Measured with a battleship: 9 passes at 1,300, 19 at 2,600, 37 at
        # 5,200 — so halving and doubling the Heart both sailed through the
        # old bound, and doubling cleared the loop's own cap of 40 by three.
        # `data/bloom.HEART_HP` decides how long the game's climax lasts and
        # was pinned by nothing; the numbers here are absolute on purpose.
        assert 14 <= strikes <= 26, (
            f"the heart took {strikes} passes from a battleship, against 19 "
            "when this was measured — the climax has changed length")

        # **It fights back while you kill it.** Nineteen passes is enough
        # provocation to fire every response in the table, and the waves
        # they detach come off the origin itself and seed what they reach —
        # so the sector the captain cleaned before the climax is not the
        # sector they are standing in after it. Containment is *clean* and
        # dead, in that order, and the field has to be finished.
        from ..core.rng import RNG
        state = bloom_sim.ensure(g)
        assert state.instars or any(s.bloom > 0.02 for s in g.galaxy.systems), (
            "burning the heart cost nothing at all — the responses that "
            "detach masses are printing their text and doing nothing again")
        assert threat.check_victory(g) is None, (
            "won with masses still in the field")

        rng = RNG("mop-up")
        for inst in list(state.instars):
            bloom_sim.kill_instar(g, inst)
        burns = 0
        while any(s.bloom > 0.02 for s in g.galaxy.systems) and burns < 40:
            worst = max(g.galaxy.systems, key=lambda s: s.bloom)
            g.location_id = worst.id
            res, why = threat.cleanse(g, worst, rng)
            assert res is not None, f"could not finish {worst.name}: {why}"
            burns += 1
        assert threat.check_victory(g) == "containment", (
            "the field is clear, the husk is ash, and it did not win")
        return (f"heart took {strikes} passes; it seeded {burns} system(s) "
                f"on the way down, and finishing them won")

