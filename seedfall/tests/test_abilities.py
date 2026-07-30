"""The bridge abilities: bounded, and honest about what they will do.

Seven fitted parts grant six abilities, and a played decade of seventy
engagements fired **not one of them** — so nothing had ever driven the module end
to end. Reading it for that reason turned up two faults, both of the kind this
project keeps asking about.

**Is it bounded?** `seal` did `side.st.armour += 4` with a four-turn cooldown and
no other rule, so a captain pressing it whenever it came up went from **2 armour
to 34 over eight firings** and 43 over a long engagement, with no limit at all.
Its own sentence — "irises its bulkheads shut and gives up the breached
compartment" — presupposes a breach and is finite: six layers, and only the ones
a hull can afford to lose. The opening NAVIS carries the part, so a captain could
do this in their first fight.

**Does the screen say what it does?** The button offered the part's flavour text
and a cooldown. Every helm order on that same panel prints its consequence.

The claims:

- **Every ability a part grants fires and does something measurable** — the
  #38 question, answered by firing each one and watching the state.
- **The forecast is the act**: what `preview` says will change is what changes.
- **The seal is bounded** by the compartments there are to give up, and refuses
  on an undamaged hull with a reason.
- **A refused ability does not spend its cooldown.**
- **The screen prints the numbers**, not the flavour text alone.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.parts import PARTS
from ..sim import abilities as ab_sim
from ..sim import combat as combat_sim
from ..sim import encounters as enc_sim
from ..sim.ship import build_layers, make_ship, stats as ship_stats
from .harness import Suite

#: Every part that grants an ability, and the id it grants.
GRANTED = [(p.id, p.ability.id) for p in PARTS if getattr(p, "ability", None)]


def _engaged(seed: str, fitted: list, difficulty: float = 1.0):
    """A battle with a named part aboard, so its ability can be pressed."""
    game = new_game(seed)
    ship = make_ship("navis", list(fitted), "Test of Nerve")
    build_layers(ship, game.bonuses)
    st = ship_stats(ship, game.bonuses)
    rng = RNG(seed)
    enemy = enc_sim.make_enemy(rng, "charter", difficulty=difficulty)
    battle = combat_sim.start(ship, st, enemy, bonuses=game.bonuses,
                              officers=game.officers, game=game, rng=rng)
    return game, battle, rng


def _hole(battle, count: int = 1) -> list:
    """Hole the outermost non-critical layers, as a fight would."""
    done = []
    for layer in battle.player.ship.layers:
        if layer.critical or len(done) >= count:
            continue
        layer.hp = 0.0
        done.append(layer.name)
    return done


def run(suite: Suite) -> None:
    check = suite.check

    @check("every ability a part grants fires and changes something")
    def _():
        # The `annex` question — a work nobody can build — asked of the bridge.
        # Each is fired from a state where it should work, and the state before
        # and after are compared, so an ability that returns a cheerful line and
        # does nothing is caught.
        assert GRANTED, "no part in the game grants an ability"
        fired = {}
        for part_id, ability_id in GRANTED:
            game, battle, rng = _engaged(f"fire-{part_id}", [part_id])
            side = battle.player
            # Put the hull into the state each one exists for.
            if ability_id in ("regrow", "seal", "shed"):
                _hole(battle, 2)
            if ability_id == "vent":
                side.ship.heat = 80.0
            before = {
                "armour": side.st.armour,
                "hull": sum(max(0.0, l.hp) for l in side.ship.layers),
                "heat": side.ship.heat,
                "interpose": side.interpose,
                "jammed": battle.enemy.jammed,
                "braced": side.braced,
            }
            told = ab_sim.preview(battle, side, ability_id)
            assert told["can"], f"{part_id}: {told['why']}"
            assert told["lines"], f"{part_id}: fires and forecasts nothing"
            ok, msg, kind = ab_sim.use_ability(battle, side, ability_id, rng)
            assert ok and msg and kind, (part_id, ok, msg, kind)
            after = {
                "armour": side.st.armour,
                "hull": sum(max(0.0, l.hp) for l in side.ship.layers),
                "heat": side.ship.heat,
                "interpose": side.interpose,
                "jammed": battle.enemy.jammed,
                "braced": side.braced,
            }
            moved = [k for k in before if before[k] != after[k]]
            assert moved, (
                f"{part_id} ({ability_id}) fired, said "
                f"{msg!r}, and changed nothing at all")
            fired[ability_id] = moved
            assert side.cd[ability_id] > 0, f"{part_id}: no cooldown spent"
        assert len(fired) == len({a for _p, a in GRANTED}), fired
        return (f"{len(GRANTED)} parts, {len(fired)} abilities, each moving "
                + " · ".join(f"{a}:{','.join(w)}" for a, w in sorted(fired.items())))

    @check("what the button says is what firing it does")
    def _():
        # Forecast against act, for the two that name a figure the state carries.
        game, battle, rng = _engaged("said", ["sphincter_seal", "heat_sink_bank",
                                             "regrowth_surge"])
        side = battle.player
        _hole(battle, 2)
        side.ship.heat = 70.0

        seal = ab_sim.preview(battle, side, "seal")
        want = side.st.armour + ab_sim.SEAL_ARMOUR
        assert f"armour {side.st.armour:.0f} → {want:.0f}" in seal["lines"], seal
        ab_sim.use_ability(battle, side, "seal", rng)
        assert side.st.armour == want, (side.st.armour, want)

        vent = ab_sim.preview(battle, side, "vent")
        after = max(0.0, side.ship.heat - ab_sim.VENT_HEAT)
        assert f"heat {side.ship.heat:.0f} → {after:.0f}" in vent["lines"], vent
        ab_sim.use_ability(battle, side, "vent", rng)
        assert side.ship.heat == after, (side.ship.heat, after)

        hurt = next(l for l in reversed(side.ship.layers) if l.hp < l.max)
        grow = ab_sim.preview(battle, side, "regrow")
        gain = min(hurt.max - hurt.hp, hurt.max * ab_sim.REGROW_SHARE)
        assert f"{hurt.name} +{round(gain)}" in grow["lines"], (grow, hurt.name)
        was = hurt.hp
        ab_sim.use_ability(battle, side, "regrow", rng)
        assert abs(hurt.hp - (was + gain)) < 1e-6, (hurt.hp, was + gain)
        return ("the seal, the vent and the blastema each did exactly what the "
                "panel said, to the figure")

    @check("the seal is bounded by the compartments there are to give up")
    def _():
        # **The defect.** Measured before the fix: 2 armour to 34 over eight
        # firings, and no limit anywhere. It gives up a compartment now, and a
        # hull has only so many it can lose.
        game, battle, rng = _engaged("bound", ["sphincter_seal"])
        side = battle.player
        losable = [l for l in side.ship.layers if not l.critical]
        # **Every** layer holed, the pressure vessel included. Holing only the
        # losable ones let a mutation that dropped the `critical` guard pass,
        # because an intact vessel is skipped by the hp test anyway — the guard
        # only bites on a hull that is open all the way through, which is exactly
        # when giving up the compartment the crew breathes would kill them.
        for layer in side.ship.layers:
            layer.hp = 0.0

        start = side.st.armour
        fired = 0
        for _ in range(len(losable) + 4):
            side.cd["seal"] = 0
            ok, _msg, _k = ab_sim.use_ability(battle, side, "seal", rng)
            if not ok:
                break
            fired += 1
        assert fired == len(losable), (
            f"{fired} compartments given up out of {len(losable)} that could be")
        assert side.st.armour == start + ab_sim.SEAL_ARMOUR * len(losable), (
            side.st.armour, start)
        assert sorted(side.sealed) == sorted(l.name for l in losable), side.sealed

        # And it stops. However many times it is pressed after that.
        stuck = side.st.armour
        for _ in range(8):
            side.cd["seal"] = 0
            assert not ab_sim.use_ability(battle, side, "seal", rng)[0]
        assert side.st.armour == stuck, (
            f"armour went on to {side.st.armour} with every compartment "
            "already given up")
        assert not ab_sim.preview(battle, side, "seal")["can"]

        # The pressure vessel is never one of them.
        vessel = next(l for l in side.ship.layers if l.critical)
        assert vessel.name not in side.sealed, (
            "the compartment the crew is breathing was irised off")
        return (f"{fired} compartments of {len(side.ship.layers)} given up for "
                f"+{side.st.armour - start:.0f} armour, and the next eight "
                "presses bought nothing")

    @check("an undamaged hull cannot seal a hole it has not got")
    def _():
        game, battle, rng = _engaged("whole", ["sphincter_seal"])
        side = battle.player
        told = ab_sim.preview(battle, side, "seal")
        assert not told["can"], told
        assert "no compartment is open" in told["why"].lower(), told["why"]
        assert not ab_sim.use_ability(battle, side, "seal", rng)[0]
        assert side.st.armour == battle.player.st.armour
        assert not side.sealed
        return f"refused on a whole hull: {told['why']!r}"

    @check("an ability that cannot fire does not spend its cooldown")
    def _():
        # It did. The cooldown was set before anything was decided, so pressing
        # a seal on an undamaged hull put it out of action for four turns and
        # returned quietly — the gate and the act disagreeing about whether
        # something happened.
        game, battle, rng = _engaged("cool", ["sphincter_seal", "regrowth_surge"])
        side = battle.player
        assert not ab_sim.use_ability(battle, side, "seal", rng)[0]
        assert side.cd.get("seal", 0) == 0, (
            f"refused, and still recycling for {side.cd.get('seal')} turns")
        assert not ab_sim.use_ability(battle, side, "regrow", rng)[0]
        assert side.cd.get("regrow", 0) == 0, side.cd

        # And a real firing does spend it, and is refused while it runs. Two
        # compartments, not one: with only one hole to seal the refusal that
        # follows is "no compartment left" rather than the cooldown, and the
        # check would be reading the wrong reason.
        _hole(battle, 2)
        assert ab_sim.use_ability(battle, side, "seal", rng)[0]
        spent = side.cd["seal"]
        assert spent > 0
        told = ab_sim.preview(battle, side, "seal")
        assert not told["can"] and "recycling" in told["why"], told
        return (f"two refusals cost no cooldown; a firing cost {spent} turns and "
                "says so while it runs")

    @check("the battle screen prints what each system will do")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, battle, rng = _engaged("screen", ["sphincter_seal",
                                                "heat_sink_bank"])
        _hole(battle, 1)
        battle.player.ship.heat = 60.0
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.battle = battle
        win.go("battle")
        view = win.views["battle"]
        view.refresh()
        for _ in range(3):
            app.processEvents()
        said = " ".join(lab.text() for lab in view.findChildren(QLabel)
                        if lab.text())
        buttons = {b.text().split(" (")[0]: b
                   for b in view.findChildren(QPushButton)}
        win.close()

        for ability_id in ("seal", "vent"):
            told = ab_sim.preview(battle, battle.player, ability_id)
            assert told["can"], told
            for line in told["lines"]:
                assert line in said, (
                    f"{ability_id} forecasts {line!r} and the panel does not "
                    f"say it: {said[-500:]}")
            assert told["name"] in buttons, (told["name"], sorted(buttons))
            assert buttons[told["name"]].isEnabled()
        return ("the systems row prints every line the sim forecasts, for the "
                "seal and the vent")
