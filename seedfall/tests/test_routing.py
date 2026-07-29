"""Power routed to the drive, and the turn on which it arrives.

`_run_seats` ran the helm first and the engineering section second. Engineering
is what sets `side.route`, and the two consumers sit on opposite sides of that
order: the guns read it when they fire, which is *after* both seats, so
`route_guns` landed on the turn it was given; the helm reads it while
steering, which is *before* engineering set it, so `route_engines` landed a
turn late.

Measured by playing, ordering "power to the drive" on turn three:

    turn 3   route_engines    route=engines    speed  0.00
    turn 4   hold             route=None       speed 74.90

The captain who ordered it saw nothing happen, and the ship leapt forward on
the turn they ordered *hold station*. Engineering runs first now — it is what
decides where the power goes, and the other two seats spend it.

The panel was the other half. It said "takes effect next turn" for both route
orders, which was wrong about the mounts even before the fix and is wrong
about both after it. `ROUTE_ACCURACY`, `ROUTE_SPEED` and `ROUTE_ACCEL` are
named now, read by the act and by the forecast, and the panel quotes them.

The claims:

- **Routing takes effect on the turn it is ordered**, both destinations,
  measured by playing rather than read off the flag.
- **The forecast is what routing does**, in the numbers the act uses.
- **Every seat has run before a shot is fired.** The general one — it is the
  ordering that made this a bug, not the constants.
- **The screen prints what routing buys.**
"""

from __future__ import annotations

import copy

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, encounters
from ..sim import stations as st_mod
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite

MIXED = ["slug_battery", "mag_lance", "reaction_organ", "opsin_eyes",
         "chemo_gut"]


def _engaged(seed: str, strength: float = 1.5):
    game = new_game(seed)
    ship = make_ship("navis", MIXED)
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 400, "alloy": 300, "volatiles": 300, "silicon": 300}
    game.recompute()
    rng = RNG(f"rt-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "concordat", strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def _turn(battle, rng, order: str):
    combat.take_turn(battle, {"type": "station", "order": order}, rng)


def run(suite: Suite) -> None:
    check = suite.check

    @check("power to the drive moves the ship on the turn it is ordered")
    def _():
        # The case the whole thing exists for, A/B from an identical state so
        # the comparison is against not routing rather than against a memory.
        gains = []
        for seed in range(6):
            _g, battle, rng = _engaged(f"drive{seed}")
            for _ in range(3):
                _turn(battle, rng, "hold")
            if battle.over:
                continue
            routed = copy.deepcopy(battle)
            plain = copy.deepcopy(battle)
            _turn(routed, RNG("same"), "route_engines")
            _turn(plain, RNG("same"), "vent")
            gains.append(routed.player.body.speed - plain.player.body.speed)
        assert len(gains) >= 4, gains
        assert all(g > 0.01 for g in gains), (
            f"ordering power to the drive left the ship no faster on the turn "
            f"it was ordered: speed gains {['%.2f' % g for g in gains]}")
        return (f"{len(gains)} engagements, every one faster the same turn "
                f"(median {sorted(gains)[len(gains) // 2]:.0f})")

    @check("power to the mounts is in the guns' hands before they fire")
    def _():
        _g, battle, rng = _engaged("mounts")
        side = battle.player
        side.route = None
        plain = st_mod.accuracy_modifier(side, True, battle.officers)
        side.route = "guns"
        routed = st_mod.accuracy_modifier(side, True, battle.officers)
        assert abs((routed - plain) - st_mod.ROUTE_ACCURACY) < 1e-9, (
            f"routing to the mounts moves accuracy {routed - plain:+.3f} "
            f"against a declared {st_mod.ROUTE_ACCURACY:+.3f}")
        # And it is genuinely set by the time the guns go: the seats all run
        # before any shot on the station path.
        _g2, live, rng2 = _engaged("mounts2")
        _turn(live, rng2, "route_guns")
        assert live.player.route == "guns", (
            "the engineering section was asked for power to the mounts and "
            f"the routing came out {live.player.route!r}")
        return f"{st_mod.ROUTE_ACCURACY:+.0%} to hit, set before the shot"

    @check("every seat has run before a shot is fired")
    def _():
        # The general one. It was the *ordering* that made this a bug rather
        # than any constant, so the invariant worth holding is about order:
        # by the time anything is fired, the ship has been flown and the
        # engineering section has been worked this turn.
        _g, battle, rng = _engaged("order")
        before = battle.player.helm_order
        assert before is None, before
        marked = len(battle.log)
        _turn(battle, rng, "salvo")
        assert battle.player.helm_order is not None, (
            "a salvo was fired and nobody flew the ship that turn")
        # Engineering having run is visible in `route`: it is reset to None at
        # the top of the section every turn, and a stale value would mean the
        # section never ran at all.
        assert battle.player.route is None, (
            f"the engineering section did not run before the salvo: route is "
            f"{battle.player.route!r}, left over from an earlier turn")
        assert len(battle.log) > marked, "the turn produced no log at all"
        return "helm and engineering both worked before the guns"

    @check("the forecast is what routing actually does")
    def _():
        # Both numbers, against the act rather than against themselves.
        _g, battle, rng = _engaged("forecast")
        for _ in range(3):
            _turn(battle, rng, "hold")
        plan = st_mod.order_preview(battle.player, battle.enemy,
                                    "route_engines", battle.officers,
                                    battle.band)
        assert plan["lines"], "routing to the drive is offered with nothing said"
        said = " ".join(plan["lines"])
        assert f"{st_mod.ROUTE_SPEED - 1:+.0%}" in said, (
            f"the forecast does not quote the speed it buys: {said}")
        assert f"{st_mod.ROUTE_ACCEL - 1:+.0%}" in said, (
            f"the forecast does not quote the acceleration it buys: {said}")

        # And the act honours it — measured, not read off the constant.
        # Both hulls run "close" at the helm, which throttles to full; the
        # routed one repeats that order while engineering feeds the drive, so
        # the ratio of the two terminal speeds *is* ROUTE_SPEED. Comparing
        # the routed speed against `top * ROUTE_SPEED` would have been the
        # tautology this suite has already fallen into once: both sides of
        # that comparison come from the same number.
        routed, plain = copy.deepcopy(battle), copy.deepcopy(battle)
        _turn(routed, RNG("f"), "close")
        for _ in range(8):                      # let both reach their ceiling
            _turn(routed, RNG("f"), "route_engines")
            _turn(plain, RNG("f"), "close")
            if routed.over or plain.over:
                break
        ratio = routed.player.body.speed / max(1e-9, plain.player.body.speed)
        assert abs(ratio - st_mod.ROUTE_SPEED) < 0.02, (
            f"routing to the drive multiplies the ship's speed by "
            f"{ratio:.2f} against a declared {st_mod.ROUTE_SPEED:.2f}")

        # Routing is a lever on the ship you have, not a different ship. A
        # boost much past half again makes the helm orders beside the point,
        # because outrunning the problem beats solving it every time.
        assert 1.10 <= st_mod.ROUTE_SPEED <= 1.50, (
            f"ROUTE_SPEED is {st_mod.ROUTE_SPEED}: outside the band where "
            "routing is a choice rather than the answer to everything")
        assert 1.2 <= st_mod.ROUTE_ACCEL <= 2.0, st_mod.ROUTE_ACCEL
        assert 0.05 <= st_mod.ROUTE_ACCURACY <= 0.25, st_mod.ROUTE_ACCURACY
        mounts = st_mod.order_preview(battle.player, battle.enemy,
                                      "route_guns", battle.officers,
                                      battle.band)
        assert f"{st_mod.ROUTE_ACCURACY:+.0%}" in " ".join(mounts["lines"]), (
            f"the forecast for the mounts quotes no figure: {mounts['lines']}")
        # Neither may claim the delay that used to be real.
        for plan_lines in (plan["lines"], mounts["lines"]):
            assert not any("next turn" in line for line in plan_lines), (
                f"the panel still says routing takes effect next turn: "
                f"{plan_lines}")
        return (f"drive {st_mod.ROUTE_SPEED - 1:+.0%} speed / "
                f"{st_mod.ROUTE_ACCEL - 1:+.0%} accel, mounts "
                f"{st_mod.ROUTE_ACCURACY:+.0%} to hit, all quoted and honoured")

    @check("the orders panel prints what routing buys")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, battle, _rng = _engaged("screen")
        battle.player.ship.layers[0].hp = battle.player.ship.layers[0].max * 0.5
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = battle
        win.go("battle")
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in
                        win.views["battle"].findChildren(QLabel) if lab.text())
        win.close()
        for order_id in ("route_guns", "route_engines"):
            plan = st_mod.order_preview(battle.player, battle.enemy, order_id,
                                        battle.officers, battle.band)
            for line in plan["lines"]:
                assert line in rows, (
                    f"{order_id}: the screen does not say {line!r}")
        assert "takes effect next turn" not in rows
        return "both routing orders costed on the panel, in figures"
