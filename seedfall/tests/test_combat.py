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
