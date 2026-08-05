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
from ..data.tech import TECH
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

    @check("no faction sends out a warship that cannot hurt you")
    def _():
        # Every weapon below tier two is grown-family, so a fabricated hull at
        # low difficulty could mount nothing at all and arrived unable to fire.
        #
        # This asked only whether the throw was above zero, and a hull with a
        # single point-defence cannon clears that at 8 damage. `_weapon_pool`
        # raised the tier until *some* weapon existed, and for a fabricated
        # hull the first one to appear is the flak gun — so 40% of NPCs came
        # out carrying nothing but point-defence and this check called them
        # armed. Being armed is not the claim worth making; being able to
        # hurt somebody is.
        from ..data.parts import PARTS
        from ..sim.encounters import MAIN_GUN_DAMAGE

        naked, toothless = [], []
        for faction in ("charter", "concordat", "freeholds", "sanhedrin"):
            for scale in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
                for index in range(12):
                    rng = RNG(f"armed-{faction}-{scale}-{index}")
                    enemy = encounters.make_enemy(rng, faction, scale)
                    mounts = [w for w in enemy["stats"].weapons if w.wpn]
                    if not sum(w.wpn.dmg for w in mounts):
                        naked.append(f"{faction}@{scale}")
                    elif not any(w.wpn.dmg >= MAIN_GUN_DAMAGE for w in mounts):
                        toothless.append(
                            f"{faction}@{scale} "
                            f"[{', '.join(w.name for w in mounts)}]")
        assert not naked, (
            f"{len(naked)} unarmed warships, e.g. {sorted(set(naked))[:4]}")
        assert not toothless, (
            f"{len(toothless)} warships carrying only specialist mounts, "
            f"e.g. {sorted(set(toothless))[:3]}")

        # And the bar itself is a real one, stated against the parts table so
        # that dropping MAIN_GUN_DAMAGE to nothing cannot satisfy the above.
        guns = sorted(p.wpn.dmg for p in PARTS
                      if p.slot == "weapon" and p.wpn)
        median = guns[len(guns) // 2]
        assert 9 < MAIN_GUN_DAMAGE < median, (
            f"MAIN_GUN_DAMAGE is {MAIN_GUN_DAMAGE}: it has to sit above the "
            f"specialist mounts (the boarding pod is 9) and below the median "
            f"gun ({median}) to mean anything")
        return (f"288 hulls, every one with a mount of {MAIN_GUN_DAMAGE}+ "
                f"damage against a median of {median}")

    @check("warships carry no civilian kit, and the player still can")
    def _():
        # Adding two smuggling parts put them straight into the NPC outfit
        # pool, changed what every enemy in the game was carrying, and broke
        # the assessment check — a feature about trade silently re-tuning
        # combat. The flag exists so the next civilian part cannot do it
        # again; the second half is here so flagging one cannot quietly
        # delete it from the shipyard instead.
        from ..data.chassis import CHASSIS_BY_ID
        from ..data.parts import PARTS, parts_available

        civilian = {p.id for p in PARTS if p.civilian}
        assert civilian, "nothing is marked civilian; the flag reads as dead"

        seen = set()
        for faction in ("charter", "concordat", "freeholds", "sanhedrin"):
            for scale in (0.5, 2.0, 4.0):
                for index in range(8):
                    enemy = encounters.make_enemy(
                        RNG(f"civ-{faction}-{scale}-{index}"), faction, scale)
                    seen.update(enemy["ship"].fitted)
        strayed = sorted(seen & civilian)
        assert not strayed, f"warships turned up carrying {strayed}"

        # And every one of them is still buildable by somebody.
        every_tech = [t.id for t in TECH]
        buyable = set()
        for chassis in CHASSIS_BY_ID.values():
            for slot in chassis.slots:
                buyable.update(p.id for p in
                               parts_available(slot, chassis, every_tech))
        orphaned = sorted(civilian - buyable)
        assert not orphaned, (
            f"civilian parts no hull in the game can fit: {orphaned}")
        return (f"{len(civilian)} civilian part(s), on no warship in 96 "
                f"encounters and fittable by the player")

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
        # **Judged on the record across both scales, not one scale at a
        # time.** Thirty-two fights carries about ±8 points of spread, and
        # the gap being measured is around 11 — so a per-scale `>=` failed
        # on noise while the effect was plain: at 150 fights a scale,
        # warfit takes 56% against armed's 35% at 2.5, and 32% against 21%
        # at 3.5. The combined record doubles the sample for nothing, and
        # each scale is still held to within the spread so a real collapse
        # at one end cannot hide inside a good result at the other.
        game = new_game("balance-builds")
        scales = (2.5, 3.5)
        rows = {build: [_win_rate(game, build, scale, trials=32)
                        for scale in scales]
                for build in ("armed", "warfit")}
        for index, scale in enumerate(scales):
            assert rows["warfit"][index] >= rows["armed"][index] - 0.10, (
                f"at scale {scale} the warfit hull did worse than the spread "
                f"allows: {rows['warfit'][index]:.0%} against "
                f"{rows['armed'][index]:.0%}")
        better = sum(rows["warfit"]) - sum(rows["armed"])
        assert better > 0, (
            f"across {len(scales)} scales the warfit hull won no more often "
            f"than the armed one: {rows}")
        return (" · ".join(f"{b} {r[0]:.0%}/{r[1]:.0%}" for b, r in rows.items())
                + f" — warfit ahead by {better:.0%} across the pair")

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
