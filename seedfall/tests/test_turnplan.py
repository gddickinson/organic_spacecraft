"""What the orders panel promises, measured against the turn that follows.

`test_orderplan.py` already checks that each order's forecast matches that
order's act — and it passed throughout, because it asked `run_engineering`
directly. The captain does not give an order directly. They give it inside a
turn, in which the two seats they have just walked away from run themselves.

Measured on a Bastion at 45 of a 50 cap, the captain sitting down at
engineering and ordering *vent*:

    the panel said    heat 45 → 20 of 50
    the turn ended at 74

— because the gunner left at the guns fires everything that bears, always,
whatever the heat. That behaviour is deliberate and is what a battle computer
is bought to fix. Quoting it at nobody was not: the one order in the game whose
entire purpose is cooling was advertised with the wrong sign, and *hold fire* —
which really does cool, by 10 — looked like the order that does nothing.

So the forecast is a dry run of the turn, stepped the way `combat.take_turn`
steps it: engineering, then the helm (on a copy of the hull, because our guns
fire from where our own helm has just put us and the enemy does not move until
afterwards), then the guns, then the radiators.

The claims:

- **The figure on the button is where the hull ends the turn** — played, order
  by order, on two hulls, hot and cold, over thousands of turns, to the
  hundredth of a point.
- **The one exception is the turn that ends the engagement**, when there is no
  end of turn to have — stated, and counted, rather than papered over.
- **No order promises cooling and delivers heating.** The defect itself.
- **The gunner you leave behind is named**, with the heat they will make.
- **One door for what bears**: the count under the button is the count in the
  log is the heat in the hull.
- **A dry mount is announced and not charged**, because `combat._fire` returns
  before `add_heat`.
- **A hull above a lowered ceiling is not cooled on paper**, which is what
  `ship.add_heat` does and does not do.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.parts import PARTS
from ..sim import combat, encounters
from ..sim import stations as st_mod
from ..sim import turnplan
from ..sim.ship import HEAT_CEILING, build_layers, make_ship, stats
from .harness import Suite

#: Five heavy mounts, so a salvo is a real thermal event rather than a rounding
#: error. Sorted by damage, which is how `_salvo` and the idle gunner both pick.
HEAVY = [w.id for w in sorted([p for p in PARTS if p.slot == "weapon"],
                              key=lambda w: -w.wpn.dmg)[:5]]

ORDER_IDS = [o.id for o in st_mod.ORDERS]


def _warship(seed: str, cargo: dict | None = None, strength: float = 1.4):
    game = new_game(seed)
    ship = make_ship("bastion", HEAVY + ["reaction_organ"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = dict(cargo if cargo is not None else {"ore": 300, "alloy": 300})
    game.recompute()
    rng = RNG(seed)
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "corsair", strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def _opening(seed: str, strength: float = 1.0):
    game = new_game(seed)
    rng = RNG(seed)
    battle = combat.start(game.ship, game.ship_stats,
                          encounters.make_enemy(rng, "corsair", strength),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def _plan(battle, order_id: str) -> dict:
    return turnplan.order_preview(battle.player, battle.enemy, order_id,
                                battle.officers, battle.band)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the figure on the button is where the hull ends the turn")
    def _():
        # The whole claim, played rather than reasoned. Both hulls, both
        # magazine states, every order, twelve turns deep.
        live = ended = off_live = off_ended = 0
        worst = 0.0
        for build in ("warship", "opening"):
            for cargo in ({"ore": 300, "alloy": 300}, {"ore": 300}):
                for order_id in ORDER_IDS:
                    for seed in ("t1", "t2", "t3", "t4"):
                        if build == "warship":
                            _g, b, rng = _warship(seed, cargo)
                        else:
                            _g, b, rng = _opening(seed)
                        for _turn in range(12):
                            if b.over:
                                break
                            told = _plan(b, order_id)
                            combat.take_turn(
                                b, {"type": "station", "order": order_id}, rng)
                            gap = abs(told["after"] - b.player.ship.heat)
                            if b.over:
                                ended += 1
                                off_ended += gap > 0.01
                            else:
                                live += 1
                                off_live += gap > 0.01
                                worst = max(worst, gap)
        assert live > 1500, live
        assert off_live == 0, (
            f"{off_live} of {live} turns ended somewhere other than where the "
            f"panel said, worst by {worst:.2f}")
        # And the exception is stated rather than hidden: on the turn the
        # engagement ends, `_finish` returns before `_end_of_turn`, so the
        # radiators never shed and the hull keeps the heat.
        assert ended > 40, ended
        return (f"{live} turns played across two hulls and {len(ORDER_IDS)} "
                f"orders, every one ending where the panel said, to the "
                f"hundredth; {off_ended} of {ended} fight-ending turns differ, "
                "which is the end-of-turn that never runs")

    @check("no order promises cooling and delivers heating")
    def _():
        # The defect itself, stated as the property that would have caught it.
        wrong, played = [], 0
        for order_id in ORDER_IDS:
            for seed in ("w1", "w2", "w3", "w4"):
                _g, b, rng = _warship(seed)
                for _turn in range(10):
                    if b.over:
                        break
                    was = b.player.ship.heat
                    told = _plan(b, order_id)
                    combat.take_turn(
                        b, {"type": "station", "order": order_id}, rng)
                    played += 1
                    if told["turn"] < -0.6 and b.player.ship.heat - was > 0.6:
                        wrong.append((order_id, round(told["turn"], 1),
                                      round(b.player.ship.heat - was, 1)))
        assert not wrong, (
            f"{len(wrong)} of {played} forecasts promised the hull would cool "
            f"and the turn heated it: {wrong[:4]}")
        return f"{played} turns, not one quoted with the wrong sign"

    @check("the measured case: venting a hot hull, and hold fire beside it")
    def _():
        # The exact reading that opened this cycle. A Bastion at 90% of its cap,
        # captain at engineering, ordering the one thing that cools: the panel
        # promised 45 → 20 and the turn ended at 74. And the order that really
        # does cool — *hold fire*, which is the captain sitting at the guns and
        # not pulling the trigger — read as the one that does nothing.
        _g, hot, rng = _warship("measured")
        cap = hot.player.st.heat_cap
        hot.player.ship.heat = cap * 0.9
        vent = _plan(hot, "vent")
        was = hot.player.ship.heat
        combat.take_turn(hot, {"type": "station", "order": "vent"}, rng)
        went = hot.player.ship.heat - was
        assert abs(vent["after"] - hot.player.ship.heat) < 0.01, (
            f"venting: panel {vent['after']:.1f}, hull {hot.player.ship.heat:.1f}")
        assert went > 0 and vent["turn"] > 0, (
            "on this hull venting is a net gain of heat, and the panel has to "
            f"say so: it says {vent['turn']:+.1f} and the turn did {went:+.1f}")

        _g2, quiet, rng2 = _warship("measured")
        quiet.player.ship.heat = cap * 0.9
        held = _plan(quiet, "hold_fire")
        was2 = quiet.player.ship.heat
        combat.take_turn(quiet, {"type": "station", "order": "hold_fire"}, rng2)
        assert abs(held["after"] - quiet.player.ship.heat) < 0.01, held
        assert held["turn"] < 0, (
            f"holding fire should cool this hull and is quoted {held['turn']:+.1f}")
        assert held["after"] < vent["after"], (
            f"the panel makes venting ({vent['after']:.0f}) look better than "
            f"holding fire ({held['after']:.0f}) on a hull this hot")
        return (f"from {was:.0f} of {cap:.0f}: venting ends at "
                f"{vent['after']:.0f} (quoted {vent['turn']:+.0f}), holding "
                f"fire at {held['after']:.0f} (quoted {held['turn']:+.0f})")

    @check("the gunner you leave behind is named, and their heat is real")
    def _():
        _g, b, rng = _warship("named")
        cap = b.player.st.heat_cap
        b.player.ship.heat = cap * 0.9
        told = _plan(b, "vent")
        named = [line for line in told["lines"] if "your gunner" in line]
        assert named, (
            f"the captain is about to leave the guns to fire everything and "
            f"the panel does not mention it: {told['lines']}")
        assert told["idle_guns"] > 0, told
        # And that figure is the heat those mounts really make.
        ghost = turnplan.flown(b.player, b.enemy, "vent", b.officers)
        want = turnplan.heat_of(turnplan.will_burn(ghost, b.enemy))
        was = b.player.ship.heat
        combat.take_turn(b, {"type": "station", "order": "vent"}, rng)
        assert abs(told["after"] - b.player.ship.heat) < 0.01, (
            told["after"], b.player.ship.heat)
        assert abs(told["idle_guns"] - want) < 0.01, (told["idle_guns"], want)
        return (f"{named[0]}; the hull went {was:.0f} → "
                f"{b.player.ship.heat:.0f} exactly as forecast")

    @check("the count under the button is the count in the log")
    def _():
        # One door for what bears. `combat._salvo` fires `bearing_set` and the
        # panel costs it, so the two cannot name different numbers.
        # Both magazine states, because with a full hold `bearing_set` and
        # `will_burn` are the same list and any confusion between them is
        # invisible. The interesting case is the mount that trains and cannot
        # fire: the log has to keep naming it, and the count has to keep
        # counting it, or the captain never learns the torpedoes are out.
        seen = dry_seen = 0
        for cargo in ({"ore": 300, "alloy": 300}, {"ore": 300}):
            for seed in ("c1", "c2", "c3"):
                _g, b, rng = _warship(seed, cargo)
                for _turn in range(8):
                    if b.over:
                        break
                    told = _plan(b, "salvo")
                    said = [line for line in told["lines"]
                            if "mounts bear" in line]
                    bearing = turnplan.bearing_set(b.player, b.enemy)
                    live = turnplan.will_burn(b.player, b.enemy)
                    if said:
                        assert said[0].startswith(f"{len(bearing)} of "), (
                            said[0], len(bearing))
                    start = len(b.log)
                    combat.take_turn(
                        b, {"type": "station", "order": "salvo"}, rng)
                    lines = [str(ln) for ln in b.log[start:]]
                    fired = [ln for ln in lines
                             if "fires everything that will bear" in ln]
                    if fired and bearing:
                        assert f"{len(bearing)} mount(s)" in fired[0], (
                            f"the panel counted {len(bearing)} and the log "
                            f"says {fired[0]}")
                        seen += 1
                    if len(bearing) > len(live) and fired:
                        empty = [w.name for w in bearing if w not in live]
                        assert any("is dry" in ln and empty[0] in ln
                                   for ln in lines), (
                            f"{empty[0]} trains and is dry, and the log never "
                            f"says so: {lines}")
                        dry_seen += 1
        assert seen >= 12, seen
        assert dry_seen >= 3, (
            f"only {dry_seen} salvos had a mount that trains and cannot fire — "
            "the case where the two lists differ was barely exercised")
        return (f"{seen} salvos counted alike by the button and the log, "
                f"{dry_seen} of them with a mount that trains and is dry")

    @check("a dry mount is announced and not charged for")
    def _():
        # `combat._fire` names the empty magazine and returns *before*
        # `add_heat`, so a forecast that charged for it would talk a gunner out
        # of a volley they could afford — which is the mistake
        # `gunnery.firing_set` was written to avoid, made one module over.
        found = None
        for seed in ("d1", "d2", "d3", "d4", "d5"):
            _g, b, _rng = _warship(seed, cargo={"ore": 300})
            wet = turnplan.will_burn(b.player, b.enemy)
            all_bearing = turnplan.bearing_set(b.player, b.enemy)
            if len(all_bearing) > len(wet):
                found = (b, all_bearing, wet)
                break
        assert found, "no hull in five had a dry mount that would otherwise bear"
        b, all_bearing, wet = found
        dry = [w.name for w in all_bearing if w not in wet]
        told = _plan(b, "salvo")
        assert abs(told["heat"] - turnplan.heat_of(wet)) < 0.01, (
            f"the panel charged {told['heat']} for a salvo whose live mounts "
            f"make {turnplan.heat_of(wet)}; {dry} are dry")
        assert len(all_bearing) > len(wet)
        return (f"{dry} bears and is dry: counted among the "
                f"{len(all_bearing)} that train, charged none of the heat")

    @check("a hull above a lowered ceiling is not cooled on paper")
    def _():
        # `ship.add_heat` clamps where heat goes *in* and nowhere else, so a
        # hull carrying more heat than its ceiling — which happens the moment a
        # hit takes out a radiator and `heat_cap` falls — sheds normally and is
        # not quietly pulled down to the ceiling. Forecasting that clamp on
        # every step, and on a step of zero, cooled such a hull by five points
        # a turn that it never lost.
        _g, b, rng = _warship("ceiling")
        cap = b.player.st.heat_cap
        b.player.ship.heat = cap * HEAT_CEILING + 11.0
        told = _plan(b, "hold")
        was = b.player.ship.heat
        combat.take_turn(b, {"type": "station", "order": "hold"}, rng)
        assert abs(told["after"] - b.player.ship.heat) < 0.01, (
            f"over the ceiling at {was:.0f}: the panel said "
            f"{told['after']:.1f} and the hull holds {b.player.ship.heat:.1f}")
        assert b.player.ship.heat > cap, (
            "the hull should still be over its cap after one turn of cooling")
        return (f"{was:.0f} on a ceiling of {cap * HEAT_CEILING:.0f}: forecast "
                f"{told['after']:.1f}, actual {b.player.ship.heat:.1f}")

    @check("the panel prints the turn's figure, not the order's")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, b, _rng = _warship("screen")
        b.player.ship.heat = b.player.st.heat_cap * 0.9
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = b
        win.go("battle")
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in
                        win.views["battle"].findChildren(QLabel) if lab.text())
        win.close()

        told = _plan(b, "vent")
        for line in told["lines"]:
            assert line in rows, f"the screen does not say {line!r}"
        assert "by the end of the turn" in rows, rows[:400]
        assert "your gunner" in rows, (
            "the screen never mentions the seat the captain is leaving")
        return "the battle screen carries the whole-turn figure and the gunner"
