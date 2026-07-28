"""Ground checks — weather that changes while the party is out in it.

Terrain is fixed the moment you land. Weather is not, and it is what turns "how
far dare we push" into a question whose answer changes while you are pushing.
These hold it to actually biting, and hold the pinned case to always having a
way out — a party that can neither move nor die is an expedition that stops.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data.expedition import TERRAIN
from ..data.weather import CLEAR, WEATHERS, WEATHERS_BY_ID
from ..sim import expedition as exp_sim
from ..sim import weather as weather_sim
from .harness import Suite


def _landable(game):
    return next(b for s in game.galaxy.systems for b in s.bodies
                if b.kind not in ("gas", "star"))


def _party(game, rng, supply: int = 40):
    return exp_sim.generate(rng, game.system, _landable(game), [], supply)


def run(suite: Suite) -> None:
    check = suite.check

    @check("every condition can actually occur")
    def _():
        # A biome gate naming something the generator never produces makes the
        # whole condition unreachable. The first draft of the weather table
        # lost its whiteout and its downpour exactly this way.
        game = new_game("biomes")
        real = {b.biome for s in game.galaxy.systems for b in s.bodies}
        dead = []
        for weather in WEATHERS:
            assert weather.sight >= 0, f"{weather.id} has negative sight"
            assert weather.danger > 0, f"{weather.id} cannot spring anything"
            if weather.biomes and not (set(weather.biomes) & real):
                dead.append(f"{weather.id}{weather.biomes}")
        assert not dead, f"conditions gated on biomes that do not exist: {dead}"
        return f"{len(WEATHERS)} conditions, all reachable across {len(real)} biomes"

    @check("the sky turns over while the party is out")
    def _():
        seen = Counter()
        for seed in range(30):
            game = new_game(f"sky-{seed}")
            rng = RNG(f"sky-{seed}")
            exp = _party(game, rng)
            for _ in range(30):
                if exp.over:
                    break
                weather_sim.tick(exp, 1, rng, exp.biome)
                seen[weather_sim.current(exp).id] += 1
        assert len(seen) >= 3, f"only {len(seen)} conditions in 30 expeditions"
        assert seen["clear"] > 0, "it is never clear"
        assert sum(v for k, v in seen.items() if k != "clear") > 0, (
            "the weather never turns")
        share = seen["clear"] / sum(seen.values())
        assert 0.3 < share < 0.85, f"clear weather is {share:.0%} of the time"
        return f"{len(seen)} conditions, clear {share:.0%} of the time"

    @check("bad weather costs more to cross and springs more hazards")
    def _():
        game = new_game("bite")
        rng = RNG("bite")
        exp = _party(game, rng)
        base = 2

        weather_sim.set_front(exp, "clear", 5)
        fair_cost = weather_sim.move_cost(exp, base)
        fair_danger = weather_sim.danger(exp, 0.2)

        weather_sim.set_front(exp, "gale", 5)
        foul_cost = weather_sim.move_cost(exp, base)
        foul_danger = weather_sim.danger(exp, 0.2)

        assert foul_cost > fair_cost, f"a gale costs no more: {fair_cost}"
        assert foul_danger > fair_danger * 1.5, (
            f"a gale is no more dangerous: {fair_danger} → {foul_danger}")
        assert weather_sim.sight(exp) < CLEAR.sight, "a gale hides nothing"
        return (f"crossing {fair_cost}d → {foul_cost}d, "
                f"hazards {fair_danger:.0%} → {foul_danger:.0%}")

    @check("a pinned party always has a way out")
    def _():
        # Being unable to move with nothing else to do is a stuck game: the
        # expedition can neither progress nor end.
        game = new_game("pinned")
        rng = RNG("pinned")
        exp = _party(game, rng, supply=12)
        weather_sim.set_front(exp, "gale", 99)
        assert weather_sim.pinned(exp), "the gale does not pin"

        blocked = exp_sim.move(exp, 0, -1, [], rng)
        assert not blocked["ok"], "walked out into a katabatic gale"
        assert blocked["why"], "refused without saying why"

        guard = 0
        while not exp.over and guard < 60:
            guard += 1
            res = exp_sim.shelter(exp, rng)
            assert res["ok"], "could not shelter"
        assert exp.over, "sheltering forever never ended the expedition"
        assert guard < 60, "sheltering did not consume supply"
        return f"pinned, sheltered {guard} days, expedition ended"

    @check("a whiteout shortens what the party can see")
    def _():
        game = new_game("sight")
        rng = RNG("sight")
        exp = _party(game, rng)
        for tile in exp.tiles:
            tile.seen = False

        weather_sim.set_front(exp, "clear", 9)
        exp_sim._reveal(exp)
        clear_seen = sum(1 for t in exp.tiles if t.seen)

        for tile in exp.tiles:
            tile.seen = False
        weather_sim.set_front(exp, "whiteout", 9)
        exp_sim._reveal(exp)
        blind_seen = sum(1 for t in exp.tiles if t.seen)

        assert clear_seen > blind_seen, (
            f"a whiteout sees as much as clear air: {clear_seen} vs {blind_seen}")
        assert blind_seen >= 1, "a whiteout cannot even see its own tile"
        return f"{clear_seen} tiles clear → {blind_seen} in a whiteout"

    @check("weather makes an expedition measurably harder")
    def _():
        def trial(force_clear: bool) -> float:
            covered = []
            for seed in range(24):
                game = new_game(f"hard-{seed}")
                rng = RNG(f"hard-{seed}")
                exp = _party(game, rng, supply=30)
                for _ in range(40):
                    if exp.over:
                        break
                    if force_clear:
                        weather_sim.set_front(exp, "clear", 99)
                    if weather_sim.pinned(exp):
                        exp_sim.shelter(exp, rng)
                        continue
                    exp_sim.move(exp, *rng.pick([(0, -1), (1, 0), (-1, 0), (0, 1)]),
                                 [], rng)
                covered.append(sum(1 for t in exp.tiles if t.visited))
            return sum(covered) / len(covered)

        fair, real = trial(True), trial(False)
        assert real < fair, (
            f"weather changed nothing: {fair:.1f} tiles against {real:.1f}")
        return f"{fair:.1f} tiles crossed in fair weather → {real:.1f} with weather"

    @check("the weather survives a save and reload")
    def _():
        import json

        from ..core.save import decode, encode

        game = new_game("persist-ground")
        rng = RNG("persist")
        game.expedition = _party(game, rng)
        weather_sim.set_front(game.expedition, "dust", 4)
        before = (weather_sim.current(game.expedition).id,
                  weather_sim.days_left(game.expedition),
                  game.expedition.biome)

        back = decode(json.loads(json.dumps(encode(game))))
        after = (weather_sim.current(back.expedition).id,
                 weather_sim.days_left(back.expedition),
                 back.expedition.biome)
        assert after == before, f"{after} != {before}"
        return f"{after[0]} with {after[1]} day(s) to run came back"
