"""Tactical-combat checks.

Combat is positional now: ships have a heading and a speed on a real plane, the
range band is derived from an actual separation, and a mount only fires if the
target is inside its arc. These check that the geometry is load-bearing rather
than decorative.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..sim.ship import make_ship
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("combat is positional: arcs, headings and station orders")
    def _():
        from ..sim import combat, encounters, stations as st_mod, tactical as tac
        from ..sim.ship import stats as ship_stats

        r = RNG("tac-test")
        player = make_ship("navis", ["slug_battery", "lixiviant", "railgun",
                                     "reaction_organ", "opsin_eyes", "chemo_gut"])
        player.cargo = {"ore": 300, "alloy": 300}
        enemy = encounters.make_enemy(r, "freeholds", 1.5)
        b = combat.start(player, ship_stats(player), enemy, rng=r)

        # the band is derived from a real separation, not stored
        assert b.range_units > 0, "the ships started on top of each other"
        assert b.band == tac.band_for(b.range_units), "band is not derived"

        # arcs actually differ between mounts
        arcs = {tac.arc_of(w) for w in b.player.st.weapons}
        assert len(arcs) > 1, f"every mount has the same arc: {arcs}"

        # closing shortens the range
        before = b.range_units
        combat.take_turn(b, {"type": "station", "order": "close"}, r)
        assert b.player.body.speed > 0, "the helm order did not move the ship"
        moved = abs(b.range_units - before)
        assert moved > 0, "a full turn of manoeuvring changed nothing"

        # every station order runs without exploding, and the battle terminates
        orders = [o.id for o in st_mod.ORDERS]
        guard = 0
        while not b.over and guard < 120:
            combat.take_turn(b, {"type": "station",
                                 "order": orders[guard % len(orders)]}, r)
            guard += 1
        assert b.over, "combat with station orders never terminated"
        return (f"{len(orders)} orders across {len(st_mod.STATIONS)} stations, "
                f"arcs {sorted(arcs)}, ended {b.result}")

    @check("a mount that does not bear cannot fire")
    def _():
        from ..sim import combat, encounters, stations as st_mod, tactical as tac
        from ..sim.ship import stats as ship_stats
        r = RNG("arc-test")
        player = make_ship("navis", ["railgun", "reaction_organ", "opsin_eyes"])
        player.cargo = {"alloy": 200}
        enemy = encounters.make_enemy(r, "freeholds", 1)
        b = combat.start(player, ship_stats(player), enemy, rng=r)

        gun = b.player.st.weapons[0]
        assert tac.arc_of(gun) == "fore", "a railgun should be a fixed forward mount"
        # point the ship directly away from the target
        b.player.body.heading = (tac.bearing_to(b.player.body, b.enemy.body) + 180) % 360
        bears, gap = st_mod.bears_on(b.player, b.enemy, gun)
        assert not bears and gap > 0, "a mount pointing astern still bore on the target"
        before = sum(l.hp for l in b.enemy.ship.layers)
        combat.take_turn(b, {"type": "fire", "weapon_id": gun.id}, r)
        after_lines = " ".join(t for _, t, _ in b.log)
        assert "will not train" in after_lines, (
            "firing outside the arc was not refused")
        return f"a fixed mount {round(gap)}° off the target refuses to fire"

    @check("consorts fight, and screening pulls fire off the flag")
    def _():
        from ..core.state import new_game
        from ..sim import combat, consorts as cs, encounters
        from ..sim.ship import build_layers, make_ship, stats as ship_stats
        from . import captain_ai

        def run(count, order):
            flag_taken = consort_dealt = 0.0
            for seed in range(24):
                g = new_game(f"consort-{seed}")
                r = RNG(f"consort-{seed}")
                p = make_ship("navis", ["slug_battery", "mag_lance",
                                        "reaction_organ", "opsin_eyes",
                                        "chemo_gut"])
                build_layers(p, g.bonuses)
                p.cargo = {"ore": 600, "alloy": 600}
                fleet = []
                for i in range(count):
                    e = make_ship("vesper", ["mag_lance", "reaction_organ",
                                             "opsin_eyes"], f"Escort {i + 1}")
                    build_layers(e, g.bonuses)
                    e.cargo = {"ore": 200, "alloy": 200}
                    e.escort = True
                    fleet.append(e)
                b = combat.start(p, ship_stats(p),
                                 encounters.make_enemy(r, "freeholds", 1.2),
                                 rng=r, game=g, fleet=fleet)
                for c in b.consorts:
                    c.order = order
                for _ in range(60):
                    if b.over:
                        break
                    combat.take_turn(b, captain_ai.orders(b), r)
                flag_taken += b.player.taken
                consort_dealt += sum(c.dealt for c in b.consorts)
            return flag_taken / 24, consort_dealt / 24

        alone, _ = run(0, "screen")
        screened, screen_guns = run(2, "screen")
        flanked, flank_guns = run(2, "flank")

        assert screened < alone * 0.6, (
            f"two screening consorts barely helped: {alone:.0f} → {screened:.0f}")
        assert flank_guns > screen_guns * 2, (
            f"flanking consorts should shoot more than screening ones "
            f"({flank_guns:.0f} vs {screen_guns:.0f})")
        assert flanked > screened, (
            "flankers should not screen as well as screens do")
        return (f"flag took {alone:.0f} alone → {screened:.0f} screened; "
                f"flank guns {flank_guns:.0f} vs screen {screen_guns:.0f}")

    @check("a consort lost in action is gone from the fleet for good")
    def _():
        from ..core.state import new_game
        from ..sim import combat, consorts as cs
        from ..sim.ship import build_layers, make_ship

        g = new_game("loss")
        doomed = make_ship("vesper", ["mag_lance", "reaction_organ",
                                      "opsin_eyes"], "Doomed")
        build_layers(doomed, g.bonuses)
        doomed.escort = True
        g.fleet.append(doomed)
        assert cs.escorts_of(g) == [doomed], "escort not recognised"

        for layer in doomed.layers:      # kill it outright
            layer.hp = 0
        assert cs.escorts_of(g) == [], "a wreck is still sailing in company"

        gone = {doomed.uid}
        g.fleet = [s for s in g.fleet if s.uid not in gone]
        assert doomed not in g.fleet, "the wreck stayed in the fleet"
        return "escort recognised, then removed once destroyed"

    @check("an adaptive Bloom's resisted hit does not crash the fight")
    def _():
        # The resisted-hit branch called an undefined `say`, so a late-game
        # Bloom engagement raised NameError the moment a bearing mount landed
        # a hit on tissue that had learned that weapon family.
        from ..core.state import new_game
        from ..sim import bloom as bloom_sim, combat, encounters, tactical as tac
        from ..sim.ship import make_ship, stats as ship_stats

        class Always(RNG):
            def chance(self, p):
                return True

            def float(self, lo=0.0, hi=1.0):
                return hi

        g = new_game("resisted")
        bloom_sim.ensure(g).stage = 4
        p = make_ship("navis", ["slug_battery", "reaction_organ", "opsin_eyes",
                                "chemo_gut"])
        p.cargo = {"ore": 900, "alloy": 900}
        w = ship_stats(p).weapons[0]
        for _ in range(80):
            bloom_sim.record_damage(g, w.family, 500)
        assert bloom_sim.resistance(g, w.family) > 0, "no resistance to test with"

        b = combat.start(p, ship_stats(p),
                         encounters.make_enemy(RNG("e"), "bloom", 1.6),
                         rng=RNG("s"), game=g)
        b.enemy_faction = "bloom"
        # A broadside mount, on the beam, inside its band envelope.
        b.player.body = tac.Body2D(0, 0, 0, 0)
        b.enemy.body = tac.Body2D(tac.BAND_UNITS * 2.5, 0, 270, 0)
        combat._fire(b, b.player, b.enemy, w.id, Always("d"))
        assert any("shrugs off" in text for _t, text, _k in b.log), (
            "the resisted-hit branch never ran, so it was not exercised")
        return f"resisted hit logged at {bloom_sim.resistance(g, w.family):.0%}"
