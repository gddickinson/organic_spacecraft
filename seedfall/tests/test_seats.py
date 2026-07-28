"""Seat checks — the bridge has to say what taking a station is worth.

The orders panel printed each station's name, its officer's level and a blurb,
and never what sitting there yourself bought. Measured from the sim: gunnery
directed is +0.10 accuracy against automatic's −0.12 + 0.02 a level, so the
seat is worth +0.22 with a green officer and +0.10 with a veteran. An
unattended helm repeats its last order at seven-tenths of the turn rate plus
0.06 a level. An unattended engineering section sheds a fraction of its vent
and can do nothing else — no venting hard, no routing power, no damage control.

Three turn-by-turn decisions, none of them stated.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import combat, encounters
from ..sim import stations as st_mod
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite


def _engaged(seed: str, levels: dict | None = None):
    game = new_game(seed)
    ship = make_ship("navis", ["slug_battery", "mag_lance", "reaction_organ",
                               "opsin_eyes", "chemo_gut"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    if levels:
        # The opening crew is a scientist, a navigator and an engineer — there
        # is no tactical officer at all, so promoting "the tactical officer"
        # silently changed nothing and the check compared a green bridge with
        # itself. Make the seat exist before setting its level.
        from ..sim.crew import make_officer
        for stat, level in levels.items():
            holder = next((o for o in game.officers if o.stat == stat), None)
            if holder is None:
                holder = make_officer(RNG(f"{seed}-{stat}"))
                holder.stat = stat
                game.officers.append(holder)
            holder.level = level
    game.recompute()
    rng = RNG(f"seat-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "concordat", 1.2),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def run(suite: Suite) -> None:
    check = suite.check

    @check("every seat says what it is worth, and it is not nothing")
    def _():
        _game, battle, _rng = _engaged("says")
        seats = st_mod.seat_value(battle.player, battle.officers)
        assert set(seats) == set(st_mod.STATION_IDS), (
            f"seats described: {sorted(seats)}")
        for sid, seat in seats.items():
            assert seat["gain"] > 0, f"{sid} is worth {seat['gain']} to take"
            assert seat["level"] >= 0
        assert seats["gunnery"]["gain"] <= 1.0, "gunnery gain is not a fraction"
        return " · ".join(f"{k} {v['gain']:.2f}" for k, v in sorted(seats.items()))

    @check("the gunnery figure is the accuracy the sim actually applies")
    def _():
        for tactical in (0, 2, 5):
            _game, battle, _rng = _engaged(f"gun-{tactical}",
                                           {"tactical": tactical})
            said = st_mod.seat_value(battle.player,
                                     battle.officers)["gunnery"]["gain"]
            directed = st_mod.accuracy_modifier(battle.player, True,
                                                battle.officers)
            automatic = st_mod.accuracy_modifier(battle.player, False,
                                                 battle.officers)
            assert abs(said - (directed - automatic)) < 1e-9, (
                f"tactical {tactical}: said {said:.3f}, sim applies "
                f"{directed - automatic:.3f}")
        return "matches at tactical 0, 2 and 5"

    @check("an unattended helm really does turn at the stated rate")
    def _():
        # Driven through `run_helm` rather than re-deriving the formula, so a
        # change to one and not the other is caught.
        from ..sim import tactical as tac
        for nav in (0, 3, 6):
            _game, battle, _rng = _engaged(f"helm-{nav}", {"nav": nav})
            side, other = battle.player, battle.enemy
            said = st_mod.seat_value(side, battle.officers)["helm"]
            share = 1.0 - said["gain"]

            def swing(directed: bool) -> float:
                # Point the bow directly away, so the turn the order asks for
                # is larger than either limit and both actually clamp. Facing
                # nearly the right way already, both reach the target heading
                # and the ratio reads 100% however slow the officer is.
                side.body.heading = (tac.bearing_to(side.body, other.body)
                                     + 180.0) % 360
                start = side.body.heading
                side.helm_order = "comeabout"
                st_mod.run_helm(side, other, "comeabout", directed,
                                battle.officers)
                return abs((side.body.heading - start + 540) % 360 - 180)

            free, held = swing(True), swing(False)
            if free <= 0.01:
                continue
            assert abs(held / free - share) < 0.06, (
                f"nav {nav}: said an officer turns at {share:.0%} and it "
                f"turned at {held / free:.0%}")
        return "the turn rate an officer keeps is the rate quoted, at nav 0, 3 and 6"

    @check("an unattended section sheds the heat it says it will")
    def _():
        for level in (0, 3, 6):
            _game, battle, _rng = _engaged(f"eng-{level}",
                                           {"engineering": level})
            side = battle.player
            said = st_mod.seat_value(side, battle.officers)["engineering"]

            side.ship.heat = 400.0
            st_mod.run_engineering(side, None, False, battle.officers)
            idle = 400.0 - side.ship.heat

            side.ship.heat = 400.0
            st_mod.run_engineering(side, "vent", True, battle.officers)
            hard = 400.0 - side.ship.heat

            assert abs((hard - idle) - said["gain"]) < 0.01, (
                f"engineering {level}: said taking it sheds "
                f"{said['gain']:.1f} more and it shed {hard - idle:.1f}")
        return "matches at engineering 0, 3 and 6"

    @check("a green officer makes a seat worth more than a veteran does")
    def _():
        # The decision the panel exists to support: who you have decides where
        # you should be sitting.
        green = _engaged("green", {"tactical": 0, "nav": 0, "engineering": 0})[1]
        crack = _engaged("crack", {"tactical": 6, "nav": 6, "engineering": 6})[1]
        lean = st_mod.seat_value(green.player, green.officers)
        good = st_mod.seat_value(crack.player, crack.officers)
        for sid in ("gunnery", "helm"):
            assert lean[sid]["gain"] > good[sid]["gain"], (
                f"{sid} is worth {lean[sid]['gain']:.2f} with a green officer "
                f"and {good[sid]['gain']:.2f} with a veteran")
        return (f"gunnery {lean['gunnery']['gain']:.2f} green against "
                f"{good['gunnery']['gain']:.2f} crack · "
                f"helm {lean['helm']['gain']:.2f} against "
                f"{good['helm']['gain']:.2f}")

    @check("asking what a seat is worth does not take it")
    def _():
        _game, battle, _rng = _engaged("pure")
        side = battle.player
        before = (side.station, side.helm_order, side.route,
                  round(side.ship.heat, 3), round(side.body.heading, 3))
        for _ in range(5):
            st_mod.seat_value(side, battle.officers)
        after = (side.station, side.helm_order, side.route,
                 round(side.ship.heat, 3), round(side.body.heading, 3))
        assert after == before, f"{after} != {before}"
        return "five enquiries, nothing on the bridge moved"
