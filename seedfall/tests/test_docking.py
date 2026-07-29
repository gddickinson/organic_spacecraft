"""The approach, and whether the instruments can be believed.

`minigames.forecast` was one of three forecast functions in the sim that no
check named. Asked the way the others have been, it turned up three faults in
one panel:

* **The readout re-rolled on every look.** `reading()` blurred the true error
  with a fresh die each call, and the screen called it from
  `game.rng("readout")` — which advances the save's seed. An axis nobody had
  touched read −44, −49, −42, −47, −49 in five consecutive paints. An
  instrument that changes when you look at it is not an instrument.
* **The panel took its colour from the truth while printing the blur.** So a
  reading of +9 could sit in a green panel, and a pilot had no way to know
  which of the two to believe. Measured at noise 5: 3% of readouts.
* **Every button's forecast quoted `d.error` — the truth.** Whatever the
  instruments said, the tooltip knew exactly where the axis would end up. That
  is the whole of what `noise`, and the sensor rating behind it, was for.

`Docking.shown` is the instrument now: read once when a pass begins, held
until the next correction, and used by the panel, the colours and the
forecast alike.

That left the rating still inert, because `noise` topped out at 5 against a
`TOLERANCE` of 6 — null the reading and you were inside whatever your sensors.
Flying on the instrument alone, 400 approaches at each level, every noise from
0 to 5 docked 100% of the time in 3.2–3.5 passes. `NOISE_CEILING` is 9 now: a
bare hull reads ±7 and pays about a pass; a well-found one reads ±3 and does
not.

The claims:

- **The instrument does not change when you look at it.** The general one.
- **The forecast is what the correction does**, in the terms the pilot has.
- **Panel, buttons and instrument are the same number.**
- **Better sensors are worth something**, measured by playing.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import minigames as mg
from .harness import Suite


class _Hull:
    """A hull of a chosen sensor rating, so noise can be driven directly."""

    def __init__(self, sensor: float, accuracy: float = 0.2) -> None:
        self.sensor, self.accuracy = sensor, accuracy


def _approach(seed: str, sensor: float = 2.0):
    game = new_game("dock")
    rng = RNG(seed)
    return mg.start_docking(rng, "Somewhere", _Hull(sensor), game.officers), rng


def _fly(sensor: float, trials: int = 300) -> tuple[float, float]:
    """A pilot who can only see the instrument. Returns (win rate, passes)."""
    game = new_game("dock")
    won = spent = 0
    for trial in range(trials):
        rng = RNG(f"fly{trial}")
        d = mg.start_docking(rng, "X", _Hull(sensor), game.officers)
        start = d.passes
        while not d.over:
            axis = max((a for a, _l in mg.AXES),
                       key=lambda a: abs(d.reading(a)))
            cap = d.precision * 4
            mg.correct(d, axis, max(-cap, min(cap, d.reading(axis))), rng)
        won += d.won
        spent += start - d.passes
    return won / trials, spent / trials


def run(suite: Suite) -> None:
    check = suite.check

    @check("the instrument does not change when you look at it")
    def _():
        # The general one. Reading an axis is not an act; doing it twenty
        # times must say the same thing twenty times.
        d, _rng = _approach("stable", sensor=0.0)
        assert d.noise > 0, "no blur at all, so this measures nothing"
        for axis, _label in mg.AXES:
            seen = {d.reading(axis) for _ in range(20)}
            assert len(seen) == 1, (
                f"{axis} read {sorted(seen)} across twenty looks with nothing "
                "touched in between")
        # And it *does* move when something happens.
        before = d.reading("range")
        mg.correct(d, "range", d.precision, RNG("move"))
        assert d.reading("range") != before or d.noise == 0, (
            "the instrument did not move after a correction")
        return f"three axes, twenty looks each, one number apiece (noise {d.noise})"

    @check("the forecast is what the correction does")
    def _():
        # Task #72's actual question. With clear instruments the forecast is
        # the next reading exactly; with blurred ones it cannot be, because
        # the next reading carries its own error — so what has to hold there
        # is the *movement*: what the burn promised to change is what it
        # changed.
        exact, deltas = 0, 0
        for sensor, blurred in ((9.0, False), (0.0, True)):
            for trial in range(60):
                d, rng = _approach(f"fc{trial}", sensor=sensor)
                assert (d.noise > 0) == blurred, (d.noise, blurred)
                for axis, _label in mg.AXES:
                    if d.over:
                        break
                    amount = max(-d.precision,
                                 min(d.precision, d.reading(axis)))
                    said = mg.forecast(d, axis, amount)
                    # In the pilot's terms, always: the forecast starts from
                    # what the instrument says, not from the truth behind it.
                    assert said["after"][axis] == d.reading(axis) - amount, (
                        f"forecast {said['after'][axis]:+d} against an "
                        f"instrument reading {d.reading(axis):+d} less a burn "
                        f"of {amount:+d} — it is quoting the truth")
                    was_true = dict(d.error)
                    mg.correct(d, axis, amount, rng)
                    if not blurred:
                        assert d.reading(axis) == said["after"][axis], (
                            f"promised {said['after'][axis]:+d} and the "
                            f"instrument reads {d.reading(axis):+d}")
                        exact += 1
                    moved = d.error[axis] - was_true[axis]
                    assert moved == -amount, (
                        f"promised a move of {-amount:+d} and the axis moved "
                        f"{moved:+d}")
                    deltas += 1
        assert exact > 40 and deltas > 100, (exact, deltas)
        return (f"{exact} clear-instrument forecasts exact to the digit, "
                f"{deltas} corrections moving what they promised")

    @check("panel, buttons and instrument are the same number")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("panel")
        game.docking = mg.start_docking(RNG("panel"), "Somewhere",
                                        _Hull(0.0), game.officers)
        d = game.docking
        assert d.noise > 0, "no blur, so the leak could not show"
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("docking")
        for _ in range(3):
            app.processEvents()
        rows = " ".join(lab.text() for lab in
                        win.views["docking"].findChildren(QLabel) if lab.text())
        win.close()

        for axis, _label in mg.AXES:
            assert f"{d.reading(axis):+d}" in rows, (
                f"the panel does not print the instrument's {axis} reading "
                f"of {d.reading(axis):+d}")
        hidden = [a for a, _l in mg.AXES if d.error[a] != d.reading(a)]
        assert hidden, "every axis happens to read true; nothing to check"
        win.close()

        # And the colour follows the same number. Straddle the tolerance —
        # true inside it, instrument outside — and the row has to read the
        # way the instrument does, or a pilot cannot tell which to believe.
        from ..ui import theme

        game = new_game("colour")
        game.docking = mg.start_docking(RNG("colour"), "X", _Hull(0.0),
                                        game.officers)
        straddle = game.docking
        straddle.error["roll"] = 2
        straddle.shown["roll"] = mg.TOLERANCE + 4
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("docking")
        for _ in range(3):
            app.processEvents()
        reading = f"{straddle.shown['roll']:+d}"
        rows_out = [lab for lab in win.views["docking"].findChildren(QLabel)
                    if lab.text().startswith(reading)]
        assert rows_out, f"the panel never printed {reading}"
        warn = theme.tint("warn")
        assert any(warn in lab.styleSheet() for lab in rows_out), (
            f"roll reads {reading}, outside a tolerance of {mg.TOLERANCE}, "
            f"and the panel is not marking it — it is colouring itself from "
            f"the {straddle.error['roll']:+d} behind the blur")
        win.close()
        return (f"{len(mg.AXES)} axes printed from the instrument, "
                f"{len(hidden)} differing from the truth, and the colour "
                "following the instrument too")

    @check("better instruments are worth something")
    def _():
        # `noise` capped at 5 against a tolerance of 6, so nulling the reading
        # was inside tolerance whatever the hull carried. Measured by flying.
        blind, blind_passes = _fly(sensor=2.0)
        keen, keen_passes = _fly(sensor=7.0)
        assert keen >= blind, (
            f"a well-found hull docks {keen:.0%} against a bare one's "
            f"{blind:.0%}")
        assert blind_passes > keen_passes + 0.4, (
            f"a bare hull spends {blind_passes:.1f} passes and a well-found "
            f"one {keen_passes:.1f} — the sensor rating buys nothing")
        assert blind > 0.6, (
            f"a bare hull docks only {blind:.0%} of the time, which is not a "
            "mini-game any more")
        assert mg.NOISE_CEILING > mg.TOLERANCE, (
            f"the worst readout blurs by {mg.NOISE_CEILING} against a "
            f"tolerance of {mg.TOLERANCE}: null the reading and you are "
            "inside it whatever your instruments")
        return (f"bare hull {blind:.0%} in {blind_passes:.1f} passes · "
                f"well-found {keen:.0%} in {keen_passes:.1f}")

    @check("a clear instrument is the truth, and a blurred one is bounded")
    def _():
        # The blur has to be the rating and nothing else: no drift into it,
        # and no hull ever reading further out than its own noise.
        clear, _rng = _approach("clear", sensor=99.0)
        assert clear.noise == 0, clear.noise
        for axis, _label in mg.AXES:
            assert clear.reading(axis) == clear.error[axis], (
                "a hull with every instrument aboard still reads blurred")
        worst = 0
        for trial in range(120):
            d, rng = _approach(f"bound{trial}", sensor=0.0)
            for _ in range(4):
                if d.over:
                    break
                for axis, _label in mg.AXES:
                    worst = max(worst, abs(d.reading(axis) - d.error[axis]))
                mg.correct(d, "range", d.precision, rng)
        assert worst <= mg.NOISE_CEILING, (
            f"an instrument read {worst} out against a blur of "
            f"{mg.NOISE_CEILING}")
        assert worst >= mg.NOISE_CEILING - 1, (
            f"the worst blur seen was {worst} against a declared "
            f"{mg.NOISE_CEILING} — the noise is not what it says it is")
        return (f"clear reads true; blurred never further out than "
                f"{mg.NOISE_CEILING}, worst seen {worst}")
