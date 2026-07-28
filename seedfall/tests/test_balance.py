"""Balance checks — difficulty that means something, measured by playing.

Encounter difficulty used to be very nearly decorative. A scale-one opponent
carried no armament whatever, because every low-tier weapon in the game is
grown-family and a fabricated warship can mount none of them; the chassis was
drawn uniformly from the faction's whole list regardless of threat; and nerve
drained on a timer, so a hull with no guns at all drove off a battleship three
times in four simply by waiting.

Every check here plays the fights out. A balance assertion that does not is
worth nothing.

A note on method, learned the hard way while writing these: build a *fresh*
hull for every fight. Reusing one ship across a run silently starts every fight
after the first with a wreck, which reads as "encounters are brutally hard" and
sent an entire afternoon's tuning in the wrong direction.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, encounters
from ..sim.ship import build_layers, make_ship, stats
from . import captain_ai
from .harness import Suite

BUILDS = {
    "unarmed": ("navis", ["reaction_organ", "opsin_eyes", "chemo_gut",
                          "intima_bloom", "bioelectric_net"]),
    "armed": ("navis", ["slug_battery", "mag_lance", "reaction_organ",
                        "opsin_eyes", "chemo_gut"]),
    "warfit": ("navis", ["slug_battery", "mag_lance", "carapace",
                         "ossified_bracing", "reaction_organ", "opsin_eyes",
                         "chemo_gut", "radiator_bloom"]),
}


def _fresh(game, build: str):
    chassis, fitted = BUILDS[build]
    ship = make_ship(chassis, fitted)
    build_layers(ship, game.bonuses)
    ship.cargo = {"ore": 400, "alloy": 400}
    return ship


def _win_rate(game, build: str, scale: float, trials: int = 24,
              faction: str = "concordat") -> float:
    wins = 0
    for index in range(trials):
        ship = _fresh(game, build)          # fresh every fight — see the note
        rng = RNG(f"{build}-{scale}-{index}")
        battle = combat.start(ship, stats(ship),
                              encounters.make_enemy(rng, faction, scale),
                              rng=rng, game=game)
        for _ in range(60):
            if battle.over:
                break
            combat.take_turn(battle, captain_ai.orders(battle), rng)
        wins += battle.result in ("destroyed", "driven-off")
    return wins / trials


def run(suite: Suite) -> None:
    check = suite.check

    @check("no faction ever sends out an unarmed warship")
    def _():
        # Every weapon below tier two is grown-family, so a fabricated hull at
        # low difficulty could mount nothing at all and arrived unable to fire.
        naked = []
        for faction in ("charter", "concordat", "freeholds", "sanhedrin"):
            for scale in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
                for index in range(12):
                    rng = RNG(f"armed-{faction}-{scale}-{index}")
                    enemy = encounters.make_enemy(rng, faction, scale)
                    throw = sum(w.wpn.dmg for w in enemy["stats"].weapons if w.wpn)
                    if throw <= 0:
                        naked.append(f"{faction}@{scale}")
        assert not naked, (
            f"{len(naked)} unarmed warships, e.g. {sorted(set(naked))[:4]}")
        return "288 hulls across four factions and six difficulties, all armed"

    @check("a heavier threat arrives in a heavier hull")
    def _():
        # Drawing the chassis uniformly meant a scale-four patrol could turn up
        # in a scout and a scale-half one in a battleship.
        import statistics
        weights = {}
        for scale in (0.5, 2.0, 4.0):
            hulls = []
            for index in range(30):
                rng = RNG(f"hull-{scale}-{index}")
                enemy = encounters.make_enemy(rng, "concordat", scale)
                hulls.append(sum(l.max for l in enemy["ship"].layers))
            weights[scale] = statistics.median(hulls)
        assert weights[4.0] > weights[2.0] > weights[0.5], (
            f"hull does not rise with difficulty: {weights}")
        assert weights[4.0] > weights[0.5] * 2, (
            f"a scale-four hull is barely bigger than a scale-half one: {weights}")
        return " · ".join(f"s{k:g} {v:.0f}" for k, v in weights.items())

    @check("difficulty actually costs the player something")
    def _():
        game = new_game("balance-curve")
        # Measured over 80 fights per point: 99% / 66% / 29%. The thresholds
        # leave room for the run-to-run spread a 32-fight sample carries.
        easy = _win_rate(game, "armed", 0.5, trials=32)
        mid = _win_rate(game, "armed", 2.5, trials=32)
        hard = _win_rate(game, "armed", 4.0, trials=32)
        assert easy > mid > hard, (
            f"the curve is not a curve: 0.5 {easy:.0%}, 2.5 {mid:.0%}, "
            f"4 {hard:.0%}")
        assert easy > 0.8, f"a light patrol beats an armed hull {1-easy:.0%} of the time"
        assert hard < 0.5, f"a scale-four warship still loses {1-hard:.0%} of the time"
        return f"0.5 → {easy:.0%} · 2.5 → {mid:.0%} · 4 → {hard:.0%}"

    @check("a better ship does better, at every difficulty")
    def _():
        game = new_game("balance-builds")
        rows = {}
        for build in ("armed", "warfit"):
            rows[build] = [_win_rate(game, build, scale, trials=32)
                           for scale in (2.5, 3.5)]
        for index, scale in enumerate((2.5, 3.5)):
            assert rows["warfit"][index] >= rows["armed"][index], (
                f"at scale {scale} the warfit hull did no better: "
                f"{rows['warfit'][index]:.0%} against {rows['armed'][index]:.0%}")
        return " · ".join(f"{b} {r[0]:.0%}/{r[1]:.0%}" for b, r in rows.items())

    @check("waiting is not a way to beat a battleship")
    def _():
        # Nerve used to drain purely on the turn counter, and the enemy lost it
        # twice as fast as the player, so a hull with no armament drove off a
        # scale-four warship three times in four by doing nothing whatever.
        game = new_game("balance-wait")
        rate = _win_rate(game, "unarmed", 4.0, trials=32)
        assert rate < 0.3, (
            f"an unarmed hull beats a scale-four warship {rate:.0%} of the time")
        mid = _win_rate(game, "unarmed", 3.0, trials=32)
        assert mid < 0.4, (
            f"an unarmed hull beats a scale-three warship {mid:.0%} of the time")
        return f"unarmed against scale three {mid:.0%}, scale four {rate:.0%}"

    @check("breaking off and hailing both actually run")
    def _():
        # Splitting these out of combat.py left them calling names that no
        # longer existed, and nothing in the suite drove either path — every
        # attempt to flee would have raised NameError in a live game.
        game = new_game("balance-parley")
        outcomes = {}
        for action in ("flee", "hail"):
            for index in range(16):
                ship = _fresh(game, "armed")
                rng = RNG(f"{action}-{index}")
                battle = combat.start(ship, stats(ship),
                                      encounters.make_enemy(rng, "freeholds", 1.0),
                                      rng=rng, game=game)
                combat.take_turn(battle, {"type": action}, rng)
                key = f"{action}:{battle.result or 'continues'}"
                outcomes[key] = outcomes.get(key, 0) + 1
        assert any(k.startswith("flee:escaped") for k in outcomes), (
            f"fleeing never worked: {outcomes}")
        assert any(k.startswith("hail:parley") for k in outcomes), (
            f"hailing never worked: {outcomes}")
        return " ".join(f"{k}={v}" for k, v in sorted(outcomes.items()))

    @check("a hull built to be hit can still win by outlasting")
    def _():
        # The counterweight to the check above: endurance is a real strategy
        # and the game has always said so. A hull that is not being hurt should
        # be able to convince the other side there is no point continuing.
        game = new_game("balance-endure")
        ship = make_ship("testudo", ["carapace", "regrowth_surge",
                                     "sphincter_seal", "melanin_ward",
                                     "intima_bloom", "chemo_gut",
                                     "reaction_organ", "radiator_bloom"])
        build_layers(ship, game.bonuses)
        st = stats(ship)
        assert not st.weapons, "the TESTUDO loadout is unexpectedly armed"
        outcomes = {}
        for index in range(24):
            fresh = make_ship("testudo", ship.fitted)
            build_layers(fresh, game.bonuses)
            rng = RNG(f"endure-{index}")
            battle = combat.start(fresh, stats(fresh),
                                  encounters.make_enemy(rng, "freeholds", 1.0),
                                  rng=rng, game=game)
            for _ in range(80):
                if battle.over:
                    break
                combat.take_turn(battle, {"type": "brace"}, rng)
            outcomes[battle.result] = outcomes.get(battle.result, 0) + 1
        assert outcomes.get("driven-off"), (
            f"endurance never won a single fight: {outcomes}")
        return " ".join(f"{k}:{v}" for k, v in outcomes.items())
