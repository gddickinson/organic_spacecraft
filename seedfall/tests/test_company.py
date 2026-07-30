"""Sailing in company: who may be ordered out, and what keeping them costs.

Found by counting which mechanics a played decade ever reaches. Over ten years
the chronicle fought **seventy engagements and deployed a consort in none of
them** — `consorts.deploy` fires only when `escorts_of` returns something, and a
chronicle never lays down a second hull. So the whole consort subsystem, orders
and screening and interception and all, had never been driven end to end by a
game.

Two things were wrong underneath that, and both are the kind this project keeps
finding:

- **The act was a screen.** `ui/yard_view._set_escort` wrote `ship.escort` and
  `ship.docked_at` itself, so the rule about which hulls may be ordered out lived
  in whether the button had been drawn. The first thing a headless caller did was
  order out a hull that was not in the fleet at all.
- **A fleet was free to keep.** Measured: ordering a thirty-crew escort out
  changed the day's demand not at all, the power draw not at all and the wage
  bill not at all. `upkeep.complement` counted the flagship's crew and the
  officers, and nothing else in the game charged for a consort either.

The claims:

- **The door refuses what the button used to hide** — somebody else's hull, your
  own flag, a wreck, an empty hull, one berthed elsewhere, one already out.
- **A company eats**, and it eats what `consorts.keep` said it would, taken out
  of the hold by `upkeep.tick` rather than promised and forgotten.
- **Air and power are per hull**: a consort does not breathe your tank.
- **The yard says what it will cost** before the captain commits.
- **And it works when it is reached** — a chronicle sailing in company deploys
  its consort, the consort fights, and what happens to it lands on the chronicle.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import consorts as consort_sim
from ..sim import upkeep as upkeep_sim
from ..sim.ship import build_layers, is_destroyed, make_ship
from .harness import Suite


def _with_a_second_hull(seed: str = "company", crew: int = 30,
                        chassis: str = "navis"):
    """A captain who owns two hulls, the second berthed where they are."""
    game = new_game(seed)
    second = make_ship(chassis, [], "Wake of Ash")
    build_layers(second, game.bonuses)
    second.crew = crew
    second.docked_at = game.system.id
    game.fleet.append(second)
    return game, second


def run(suite: Suite) -> None:
    check = suite.check

    @check("only a hull that could actually sail is ordered out")
    def _():
        # Every one of these was enforced by the screen not drawing a button.
        game, second = _with_a_second_hull("gates")
        refused = {}

        stranger = make_ship("navis", [], "Not Yours")
        build_layers(stranger, game.bonuses)
        stranger.crew = 10
        stranger.docked_at = game.system.id
        refused["not yours"] = consort_sim.sail(game, stranger)

        refused["your own flag"] = consort_sim.sail(game, game.ship)

        second.docked_at = (second.docked_at + 1) % len(game.galaxy.systems)
        refused["berthed elsewhere"] = consort_sim.sail(game, second)
        second.docked_at = game.system.id

        empty = make_ship("navis", [], "Nobody Aboard")
        build_layers(empty, game.bonuses)
        empty.crew = 0
        empty.docked_at = game.system.id
        game.fleet.append(empty)
        refused["nobody aboard"] = consort_sim.sail(game, empty)

        wreck = make_ship("navis", [], "Burnt Out")
        build_layers(wreck, game.bonuses)
        wreck.crew = 8
        wreck.docked_at = game.system.id
        for layer in wreck.layers:
            layer.hp = 0.0
        game.fleet.append(wreck)
        refused["a wreck"] = consort_sim.sail(game, wreck)

        for why, res in refused.items():
            assert not res["ok"], f"{why}: ordered out anyway"
            assert res["why"], f"{why}: refused and said nothing"
        assert not consort_sim.escorts_of(game), "something got out regardless"

        # And the one that should go, does — then cannot be ordered twice.
        out = consort_sim.sail(game, second)
        assert out["ok"], out
        assert second.escort and second.docked_at is None
        again = consort_sim.sail(game, second)
        assert not again["ok"] and "already" in again["why"], again
        assert [s.name for s in consort_sim.escorts_of(game)] == [second.name]
        return (f"{len(refused)} kinds of hull refused with a reason — "
                + " · ".join(refused) + " — and the sound one sailed")

    @check("a hull in company eats out of your hold")
    def _():
        game, second = _with_a_second_hull("fed", crew=30)
        alone = dict(upkeep_sim.demand(game))
        told = consort_sim.sail(game, second)["keep"]
        with_them = dict(upkeep_sim.demand(game))
        assert with_them != alone, (
            "thirty more mouths and the day's demand did not move")
        for cid, rate in with_them.items():
            grew = rate - alone.get(cid, 0.0)
            assert abs(grew - told["extra"].get(cid, 0.0)) < 1e-6, (
                f"{cid}: the yard said {told['extra'].get(cid, 0.0)} a day and "
                f"the demand moved by {grew}")
        assert told["crew"] == 30 and told["hulls"] == 1, told

        # And it is really taken, not merely asked for. Stock the hold, run a
        # fortnight, and compare what went against what was quoted.
        for cid in with_them:
            game.ship.cargo[cid] = 500.0
        before = {cid: game.ship.cargo.get(cid, 0.0) for cid in with_them}
        upkeep_sim.tick(game, 14.0, RNG("fed"))
        gone = {cid: before[cid] - game.ship.cargo.get(cid, 0.0)
                for cid in with_them}
        for cid, amount in gone.items():
            want = with_them[cid] * 14.0
            assert abs(amount - want) < 0.01, (
                f"{cid}: a fortnight wanted {want:.3f} t and took {amount:.3f}")
        share = sum(told["extra"].values()) / sum(with_them.values())
        return (f"{told['crew']} more mouths cost {told['a_day']:.3f} t a day "
                f"({share:.0%} of the fleet's stores), and a fortnight took "
                f"exactly that")

    @check("a consort breathes its own air and makes its own power")
    def _():
        # The other half of the rule, and it is not symmetry for its own sake:
        # `game.ship.o2` is *this hull's* tank and every hull has a reactor. Only
        # the stores are shared, because those come out of the hold.
        game, second = _with_a_second_hull("air", crew=40)
        air = upkeep_sim.breathers(game)
        watts = upkeep_sim.draw(game)
        consort_sim.sail(game, second)
        assert upkeep_sim.breathers(game) == air, (
            f"{air} → {upkeep_sim.breathers(game)} breathing your tank")
        assert abs(upkeep_sim.draw(game) - watts) < 1e-9, (
            f"{watts} → {upkeep_sim.draw(game)} kW off your reactor")
        assert upkeep_sim.demand(game) != upkeep_sim.demand(game, company=False)
        return (f"{air} breathers and {watts:.1f} kW unchanged with 40 more "
                "crew in company; only the stores moved")

    @check("the yard says what the company costs before you commit")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, second = _with_a_second_hull("screen", crew=25)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("yard")
        view = win.views["yard"]
        view.tab = "fleet"
        view.refresh()
        for _ in range(3):
            app.processEvents()
        # The offer, before: a berthed hull of your own can be ordered out.
        from PyQt6.QtWidgets import QPushButton
        sail = [b for b in view.findChildren(QPushButton)
                if "Sail with me" in b.text()]
        assert sail, "a berthed hull of your own and nothing offering to sail it"

        told = consort_sim.sail(game, second)["keep"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        win.close()
        assert "In company" in said, f"the panel never says who is out: {said[:300]}"
        assert "more mouths" in said, "the panel never says what they cost"
        assert f"{told['crew']} more mouths" in said, (
            f"{told['crew']} in company and the panel says otherwise")
        for cid, amount in told["extra"].items():
            assert f"{amount:.2f} t {cid}" in said, (
                f"{cid} at {amount:.2f} a day is not on the panel: {said[:300]}")
        return ("the hulls panel offers the berth a sail, then reads "
                f"\"{told['crew']} more mouths\" and prices the stores")

    @check("the standing order matches the act it is nagging about")
    def _():
        # `data/orders.py` promises "You own more than one and only one of them
        # is doing anything. Order it to sail in company." Its gate was "you own
        # a hull that is not already out", which is true of a hull berthed six
        # systems away — a card telling the captain to do something they cannot
        # do from here. It asks `consorts.can_sail` now, so the gate and the act
        # are the same function.
        from ..sim import orders as orders_sim

        game, second = _with_a_second_hull("nagging", crew=12)
        assert "escort" in orders_sim.summary(game)["ids"], (
            "a sound hull berthed right here and the card is silent")

        elsewhere = (game.system.id + 1) % len(game.galaxy.systems)
        second.docked_at = elsewhere
        assert "escort" not in orders_sim.summary(game)["ids"], (
            "the card nags about a hull berthed in another system, which "
            "cannot be ordered out from here")

        second.docked_at = game.system.id
        consort_sim.sail(game, second)
        assert "escort" not in orders_sim.summary(game)["ids"], (
            "the hull is already sailing and the card still asks for it")
        return ("the card fires for a hull berthed here, and is silent for one "
                "berthed elsewhere or already out")

    @check("a chronicle that sails in company actually fights with it")
    def _():
        # The point of the whole cycle. Nothing had ever driven this: seventy
        # engagements in a played decade and not one consort deployed, because
        # a chronicle never builds a second hull.
        from ..sim import combat as combat_sim
        from ..sim import encounters as enc_sim
        from .captain_ai import orders

        deployed = fought = interposed = 0
        losses = 0
        for seed in ("fight-a", "fight-b", "fight-c", "fight-d"):
            game, second = _with_a_second_hull(seed, crew=24, chassis="testudo")
            assert consort_sim.sail(game, second)["ok"]
            rng = RNG(seed)
            enemy = enc_sim.make_enemy(rng, "charter", difficulty=1.4)
            battle = combat_sim.start(
                game.ship, game.ship_stats, enemy, bonuses=game.bonuses,
                officers=game.officers, game=game, rng=rng,
                fleet=consort_sim.escorts_of(game))
            assert battle.consorts, "sailed in company and deployed nobody"
            deployed += len(battle.consorts)
            start_hull = consort_sim.hull_fraction(battle.consorts[0].ship)
            guard = 0
            while not battle.over and guard < 80:
                guard += 1
                combat_sim.take_turn(battle, orders(battle), rng)
                if any(consort_sim._is_between(battle, c)
                       for c in consort_sim.active(battle)):
                    interposed += 1
            if consort_sim.hull_fraction(battle.consorts[0].ship) < start_hull:
                fought += 1
            losses += len(consort_sim.losses(battle))
        assert deployed >= 4, deployed
        assert fought >= 1, (
            f"{deployed} consorts deployed across four engagements and not one "
            "of them was ever touched — they are scenery")
        assert interposed >= 1, (
            "no consort ever got between the flag and the enemy, so screening "
            "is a standing order nothing acts on")
        return (f"{deployed} consorts deployed over 4 engagements, {fought} took "
                f"hull damage, {interposed} turns with one interposed, "
                f"{losses} lost")
