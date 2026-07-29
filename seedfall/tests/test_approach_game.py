"""The docking approach: what a correction will do, and who is flying.

The mini-game modelled an error per axis, a drift per axis, a readout blurred
by the sensors and a precision set by the hull and the navigator — and every
bit of it reached the player as three integers and six buttons. The drift did
not reach them at all, so a pilot correcting the worst reading three times
running could watch the other two walk out of tolerance and never be told why.

Three claims:

- **The forecast is the burn.** What the screen says a correction leaves is
  what the correction leaves, drift included.
- **The computer flies, and pays for it.** It docks about as reliably as a
  careful hand and is graded as a bare clean dock — measured at 1.00 against
  2.45 by hand. Without that it matched a good pilot exactly and the approach
  became a chore to automate away.
- **No fitting, no autopilot.**
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import minigames as mg
from .harness import Suite


def _approach(seed: str, doctrine: float = 0.0):
    game = new_game(seed)
    if doctrine:
        game.stock_fx = dict(game.stock_fx or {})
        game.stock_fx["doctrine"] = doctrine
        game.recompute()
    docking = mg.start_docking(RNG(f"d-{seed}"), "Quay", game.ship_stats,
                               game.officers)
    return game, docking


def run(suite: Suite) -> None:
    check = suite.check

    @check("what the forecast promises is what the burn leaves")
    def _():
        # Stated against the instruments, which is where the pilot stands.
        # This used to compare `said["after"]` with `d.error` — the truth
        # behind the blur — and passed only because the forecast was reading
        # the truth as well. Both now start from `d.reading`, so on a hull
        # with clear instruments the two are identical and on a blurred one
        # the forecast is what the *readout* will say, less its own error.
        checked = 0
        for seed in range(12):
            game, d = _approach(f"fc{seed}")
            d.noise = 0                       # instruments you can trust
            mg.take_reading(d, RNG(f"clear{seed}"))
            for axis, _label in mg.AXES:
                if d.over:
                    break
                amount = d.precision * (1 if d.reading(axis) > 0 else -1)
                said = mg.forecast(d, axis, amount)
                mg.correct(d, axis, amount, RNG(f"r{seed}"))
                assert d.error == said["after"], (
                    f"forecast said {said['after']} and the burn left "
                    f"{d.error}")
                checked += 1
        assert checked > 10, checked
        return f"{checked} corrections, every one landing where it was said to"

    @check("the forecast counts the drift the other axes take")
    def _():
        # The part the numbers never showed: firing on one axis lets the other
        # two walk while you do.
        game, d = _approach("drift")
        moving = [a for a, _l in mg.AXES if d.drift[a] != 0]
        assert moving, "no axis drifts in this seed, so nothing is measured"
        axis = next(a for a, _l in mg.AXES if a not in moving) \
            if len(moving) < len(mg.AXES) else moving[0]
        said = mg.forecast(d, axis, d.precision)
        for other in moving:
            if other == axis:
                continue
            # From the readout, like everything else the pilot is shown.
            assert said["after"][other] == d.reading(other) + d.drift[other], (
                f"the forecast has {other} unmoved while the burn drifts it "
                f"{d.drift[other]:+d}")
        return (f"{len(moving)} axes drifting, every one counted in the "
                "forecast")

    @check("the computer picks something outside tolerance, and says why")
    def _():
        game, d = _approach("pick", doctrine=0.8)
        plan = mg.autopilot(d)
        assert plan, "the computer had nothing to say with three axes out"
        assert abs(d.error[plan["axis"]]) > mg.TOLERANCE, (
            f"it chose {plan['axis']}, which is already inside tolerance")
        assert abs(plan["amount"]) <= d.precision, (
            f"it fired {plan['amount']} on a hull that can manage "
            f"{d.precision}")
        assert len(plan["why"]) > 15, plan["why"]
        assert plan["forecast"]["after"] == mg.forecast(
            d, plan["axis"], plan["amount"])["after"]

        # And with everything inside, it has nothing to do.
        for axis, _l in mg.AXES:
            d.error[axis] = 0
        assert mg.autopilot(d) == {}, "it wants to fire at a lined-up hull"
        return f"it fires {plan['amount']:+d} on {plan['axis']}: {plan['why']}"

    @check("the computer docks you, and does not dock you well")
    def _():
        # It matched a careful hand exactly before the grade was capped, which
        # makes the approach a chore to automate rather than a skill.
        def play(auto: bool, trials: int = 120):
            won = grade = 0
            for trial in range(trials):
                game, d = _approach(f"g{trial}", doctrine=0.8 if auto else 0.0)
                rng = RNG(f"t{trial}")
                while not d.over:
                    if auto:
                        plan = mg.autopilot(d)
                        if not plan:
                            break
                        mg.correct(d, plan["axis"], plan["amount"], rng,
                                   by_computer=True)
                    else:
                        axis = max(d.error, key=lambda a: abs(d.error[a]))
                        step = max(-d.precision,
                                   min(d.precision, d.error[axis]))
                        mg.correct(d, axis, step, rng)
                if d.won:
                    won += 1
                    grade += mg.dock_result(d)["grade"]
            return won / trials, grade / max(1, won)

        auto_rate, auto_grade = play(True)
        hand_rate, hand_grade = play(False)
        assert auto_rate > 0.25, (
            f"the computer only docks {auto_rate*100:.0f}% of the time — it "
            "is not worth fitting")
        assert auto_grade < hand_grade - 0.4, (
            f"a computer-flown approach grades {auto_grade:.2f} against "
            f"{hand_grade:.2f} by hand — flying it yourself buys nothing")
        return (f"computer: {auto_rate*100:.0f}% at grade {auto_grade:.2f} · "
                f"by hand: {hand_rate*100:.0f}% at grade {hand_grade:.2f}")

    @check("a hull with no computer is flown by hand or not at all")
    def _():
        from ..sim import doctrine as doctrine_sim
        game, _d = _approach("bare")
        assert not doctrine_sim.fitted(game.ship_stats), (
            f"the stock hull rates {game.ship_stats.doctrine:.2f} and would "
            "fly its own approaches")
        rich, _d2 = _approach("rich", doctrine=0.8)
        assert doctrine_sim.fitted(rich.ship_stats)
        return (f"stock {game.ship_stats.doctrine:.2f} · "
                f"fitted {rich.ship_stats.doctrine:.2f}")

    @check("the approach screen draws the hull and offers the computer")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.approach_plot import ApproachPlot
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game, docking = _approach("screen", doctrine=0.8)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.docking = docking
        win.go("docking")
        for _ in range(3):
            app.processEvents()
        view = win.views["docking"]

        plots = view.findChildren(ApproachPlot)
        assert plots, "the approach is still three numbers and no picture"
        plots[0].preview = ("range", docking.precision)
        plots[0].grab()          # paints with the ghost, without falling over

        texts = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        assert "not bring you alongside well" in texts, (
            "the screen does not say what letting the computer fly costs")
        assert any("fly the pass" in b for b in buttons), buttons
        win.close()
        return "the plot draws, and the computer states its price"
