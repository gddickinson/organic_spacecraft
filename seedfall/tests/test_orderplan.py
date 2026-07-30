"""What an order will do, said before it is given.

`seat_value` says what taking a station personally is worth. The orders inside
those stations were bare buttons with a sentence of prose — "More damage, far
more heat" — and no number anywhere.

Since the thermal work that matters most at gunnery. A Bastion sitting at 30
of a 50 cap that presses *fire everything that bears* makes seventy-four more
and ends the turn pinned at the ceiling, where every penalty for running hot
is charged against it. Nothing on the screen said so until the turn had
resolved.

`stations.order_preview` says it: how many mounts bear, what the shot is worth,
what the heat becomes, and whether that is over the cap. Helm orders are left
alone deliberately — the firing picture already says what coming about would
bring on, and repeating it under the buttons would be noise.

The claims:

- **The forecast is what the order does**, in heat, measured against the act.
- **A salvo that will breach the cap says so.**
- **Every order that can be given is accounted for**, or deliberately silent.
- **The screen prints it.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.parts import PARTS
from ..sim import combat, encounters
from ..sim import stations as st_mod
from ..sim import turnplan
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite

HEAVY = [w.id for w in sorted([p for p in PARTS if p.slot == "weapon"],
                              key=lambda w: -w.wpn.heat)[:5]]

#: Nothing is silent any more. Helm orders used to say nothing here on the
#: grounds that the firing picture already reports what coming about would
#: bring on, in degrees — which was about *what bears*, and left the captain
#: with no idea what the turn would do to the hull. It does plenty: the gunner
#: keeps firing while you fly, so a helm order has a heat figure like any other.
SILENT: set = set()


def _engaged(seed: str, heat: float = 30.0, hurt: bool = False):
    game = new_game(seed)
    ship = make_ship("bastion", HEAVY + ["reaction_organ"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 300, "alloy": 300, "volatiles": 300, "silicon": 300}
    game.recompute()
    rng = RNG(f"o-{seed}")
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "concordat", 2.0),
                          rng=rng, game=game, officers=game.officers)
    battle.player.ship.heat = heat
    if hurt:
        battle.player.ship.layers[0].hp = battle.player.ship.layers[0].max * 0.5
    return game, battle, rng


def _plan(battle, order_id: str):
    return turnplan.order_preview(battle.player, battle.enemy, order_id,
                                battle.officers, battle.band)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the heat a salvo promises is the heat a salvo makes")
    def _():
        # Measured against `_salvo` itself rather than a whole turn, because a
        # turn also vents and runs the seats — this is the number on the
        # button, so it is the number the button's act must produce.
        # From three starting heats, including one where the ceiling clamps.
        # The forecast does its own clamping — quoting the raw sum when the
        # hull will stop at the ceiling is the same defect this function
        # exists to fix, one layer up, and my first draft did it.
        rows = []
        for start in (0.0, 30.0, 95.0):
            game, battle, rng = _engaged(f"salvo{start:.0f}", heat=start)
            said = _plan(battle, "salvo")
            before = battle.player.ship.heat
            combat._salvo(battle, battle.player, battle.enemy, rng)
            moved = battle.player.ship.heat - before
            assert abs(moved - said["heat"]) < 0.01, (
                f"from {start:.0f}: promised {said['heat']:+.1f} heat and "
                f"made {moved:+.1f}")
            rows.append(f"{start:.0f}→{moved:+.0f}")
        return " · ".join(rows) + ", every one as forecast"

    @check("an aimed shot names the mount it will use, and its heat")
    def _():
        game, battle, rng = _engaged("aimed")
        said = _plan(battle, "aimed")
        bearing = [w for w in battle.player.st.weapons
                   if st_mod.bears_on(battle.player, battle.enemy, w)[0]]
        assert bearing, "nothing bears in this seed"
        best = max(bearing, key=lambda w: w.wpn.dmg)
        assert any(best.name in line for line in said["lines"]), (
            f"the forecast names no mount: {said['lines']}")
        before = battle.player.ship.heat
        combat._fire(battle, battle.player, battle.enemy, best.id, rng)
        moved = battle.player.ship.heat - before
        assert abs(moved - said["heat"]) < 0.01, (
            f"promised {said['heat']:+.0f} and made {moved:+.0f}")
        return f"{best.name}: {said['heat']:.0f} heat, as promised"

    @check("venting promises what the section actually sheds")
    def _():
        game, battle, rng = _engaged("vent", heat=40.0)
        said = _plan(battle, "vent")
        assert said["heat"] < 0, said
        before = battle.player.ship.heat
        st_mod.run_engineering(battle.player, "vent", True, battle.officers,
                               battle.enemy)
        moved = battle.player.ship.heat - before
        assert abs(moved - said["heat"]) < 0.01, (
            f"promised {said['heat']:+.0f} and shed {moved:+.0f}")
        return f"sheds {-moved:.0f}, as promised"

    @check("a salvo that would breach the cap says so before it is given")
    def _():
        # The case the whole thing exists for.
        # Two warnings, and they are not the same warning: from cold, a salvo
        # goes over the cap; from 30 it goes over *and* stops at the ceiling,
        # which is a worse place to be and says so.
        cold, over = _engaged("over-cold", heat=0.0)[1:2][0], None
        said_cold = _plan(cold, "salvo")
        cap = cold.player.st.heat_cap
        assert said_cold["over"], said_cold
        assert any("over the cap" in line for line in said_cold["lines"]), (
            f"a salvo from cold takes this hull past its cap and the forecast "
            f"does not say so: {said_cold['lines']}")

        # And the two warnings are not the same warning. From 30 this hull ends
        # the turn at 94 of a 50 cap — over, and not pinned: the engineering
        # section sheds four and a half before the guns speak, so it peaks at
        # 99.6 of a 100 ceiling. That distinction only exists now the forecast
        # covers the whole turn; quoting the salvo alone made it 104, clamped
        # it, and called every hot salvo pinned.
        _g, hot, _r = _engaged("over-hot", heat=30.0)
        said_hot = _plan(hot, "salvo")
        assert said_hot["over"] and not said_hot["pinned"], said_hot
        assert any("over the cap" in line for line in said_hot["lines"]), said_hot

        # Pinned is what happens when it really does touch the ceiling.
        _g3, pinned, _r3 = _engaged("pinned", heat=60.0)
        said_pinned = _plan(pinned, "salvo")
        assert said_pinned["pinned"], said_pinned
        assert any("pinned at the ceiling" in line
                   for line in said_pinned["lines"]), (
            f"a salvo from 60 takes this hull to its ceiling and the forecast "
            f"calls it merely over: {said_pinned['lines']}")

        # And a hull with room to spare is not warned for nothing.
        _g2, cool, _r2 = _engaged("under", heat=0.0)
        quiet = _plan(cool, "aimed")
        assert not quiet["over"], (
            f"a cold hull is warned about an aimed shot: {quiet['lines']}")
        return (f"over the cap from cold, pinned from 30, quiet for an aimed "
                f"shot on a {cap:.0f} cap")

    @check("every order is accounted for, or silent on purpose")
    def _():
        game, battle, _rng = _engaged("all", hurt=True)
        spoke, silent = [], []
        for order in st_mod.ORDERS:
            plan = _plan(battle, order.id)
            (spoke if plan["lines"] else silent).append(order.id)
        stray = sorted(o for o in silent if o not in SILENT)
        assert not stray, (
            f"orders offered as bare buttons with nothing said about them: "
            f"{stray}")
        # Every one of them, helm included: an order that moves the ship still
        # leaves the gunner firing, and the captain is entitled to know what
        # the hull will be sitting at when the turn ends.
        assert len(spoke) == len(st_mod.ORDERS), sorted(silent)
        for order in st_mod.ORDERS:
            plan = _plan(battle, order.id)
            assert any("by the end of the turn" in line
                       for line in plan["lines"]), (order.id, plan["lines"])
        return f"all {len(spoke)} orders costed, none left as a bare button"

    @check("the orders panel prints what each one will do")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, battle, _rng = _engaged("screen", hurt=True)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = battle
        win.go("battle")
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in
                        win.views["battle"].findChildren(QLabel) if lab.text())
        win.close()

        for order_id in ("salvo", "aimed", "vent"):
            plan = _plan(battle, order_id)
            for line in plan["lines"]:
                assert line in rows, (
                    f"{order_id}: the screen does not say {line!r}")
        assert "pinned at the ceiling" in rows or "over the cap" in rows, (
            "the hull would breach its cap firing everything and the panel "
            "does not say so")
        return "gunnery and engineering orders costed on the panel"
