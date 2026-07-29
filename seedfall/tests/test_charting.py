"""Finishing a chart, dating it, and watching it go off.

`charts.freshness` says "a chart made long ago is worth less. The sector
moves." It was never once true. Dating a finished chart lived in
`actions.survey` — the single-method call the four survey methods replaced —
and the screen calls `survey.perform`, which did not. So no chart a player
ever made was stamped, `freshness` returned 1.0 for ever, and `FRESH_DAYS`
and `STALE_FLOOR` decided nothing: a survey made in year one sold in year ten
for exactly the same money.

The survey office had been written for this all along. It carries an "Age of
the survey" row behind `if fresh < 0.95`, which could not fire.

**The shape of it matters more than the bug.** Surveying a body has two doors
— `actions.survey`, which the remote bridge and every test driver use, and
`survey.perform`, which the screen uses — and they did different things. The
drivers went through the door that worked, which is exactly why nothing
caught it for as long as it lasted.

The claims:

- **Both doors leave the same state.** The general one.
- **A finished chart is dated, an unfinished one is not.**
- **A chart loses value with age, down to a floor.**
- **The office says how old it is.**
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.charts import FRESH_DAYS, STALE_FLOOR
from ..sim import charts, intel, survey
from ..sim.actions import survey as survey_action
from .harness import Suite


def _chart(seed: str, via: str = "screen", bodies: int | None = None):
    """Survey a system through one of the two doors."""
    game = new_game(seed)
    count = len(game.system.bodies) if bodies is None else bodies
    for index in range(count):
        game.ship.cargo["volatiles"] = 900
        if via == "screen":
            survey.perform(game, index, "pass")
        else:
            survey_action(game, index)
    return game


def _state(game) -> dict:
    system = game.system
    return {"scanned": bool(system.scanned),
            "stamped": str(system.id) in charts._made(game),
            "charted": intel.level(game, system) >= 3}


def run(suite: Suite) -> None:
    check = suite.check

    @check("both ways of surveying leave the same state behind")
    def _():
        # The general question, and the one that would have found this the day
        # it was introduced. Every driver in the suite uses the bridge door and
        # every player uses the screen door; only one of them dated the chart,
        # so the drivers all saw a system that worked.
        seeds = ("doors", "doors2", "doors3")
        for seed in seeds:
            screen = _state(_chart(seed, "screen"))
            bridge = _state(_chart(seed, "bridge"))
            assert screen == bridge, (
                f"{seed}: surveying through the screen leaves {screen} and "
                f"through the bridge leaves {bridge} — the same act, two "
                "different outcomes")
            assert screen["stamped"], (
                f"{seed}: neither door dates the chart, so nothing can ever "
                "go stale")
        return f"{len(seeds)} systems, both doors agreeing on every one"

    @check("a finished chart is dated and an unfinished one is not")
    def _():
        game = _chart("part", "screen", bodies=1)
        if all(b.surveyed for b in game.system.bodies):
            return "this system has a single body, so there is no partial case"
        assert not _state(game)["stamped"], (
            "a chart was dated with bodies still unsurveyed — the date is "
            "supposed to mean the day it was finished")
        assert intel.level(game, game.system) < 3

        done = _chart("part", "screen")
        assert _state(done)["stamped"], "a finished chart went undated"
        return "dated when the last body is done, and not before"

    @check("a chart loses value as it ages, and stops at a floor")
    def _():
        # Ages in plain days, not multiples of `FRESH_DAYS`. Measuring at
        # `FRESH_DAYS // 2` and `FRESH_DAYS` moves the ruler with the thing it
        # measures: widening the window to ten thousand years then passed
        # cleanly, because the check simply waited ten thousand years.
        game = _chart("age", "screen")
        made = int(charts._made(game)[str(game.system.id)])
        seen = {}
        for age in (0, 360, 730, 2200):
            game.day = made + age
            seen[age] = (charts.freshness(game, game.system),
                         charts.best_buyer(game, game.system)[1])
        assert abs(seen[0][0] - 1.0) < 1e-6, f"a chart is born stale: {seen}"
        assert seen[360][0] < 0.85, (
            f"a year old and still {seen[360][0]:.2f} of fresh — the sector "
            "is not moving very fast")
        assert seen[730][0] <= 0.55, (
            f"two years old and still worth {seen[730][0]:.2f} of fresh")
        assert abs(seen[2200][0] - seen[730][0]) < 1e-6, (
            "past the window it keeps falling — the floor is not a floor")
        assert seen[730][0] >= STALE_FLOOR - 1e-6, (
            f"it fell through the floor to {seen[730][0]}")
        # And it reaches the money, not just the multiplier.
        assert seen[0][1] > seen[730][1] * 1.4, (
            f"fresh {seen[0][1]:,} against two years old {seen[730][1]:,} — "
            "there is no reason to sell a chart while it is current")
        return " · ".join(f"{k}d {v[0]:.2f} {v[1]:,}"
                          for k, v in sorted(seen.items()))

    @check("selling it late is worth measurably less")
    def _():
        # End to end through `intel.sell_survey`, which is what the button
        # calls, rather than off the multiplier.
        early = _chart("sell", "screen")
        made = int(charts._made(early)[str(early.system.id)])
        early.day = made
        got_early = intel.sell_survey(early, early.system, "concordat")

        late = _chart("sell", "screen")
        late.day = made + 730          # two years, written here on purpose
        got_late = intel.sell_survey(late, late.system, "concordat")

        assert got_early.get("ok") and got_late.get("ok"), (got_early, got_late)
        assert got_early["value"] > got_late["value"] * 1.4, (
            f"sold fresh for {got_early['value']:,} and stale for "
            f"{got_late['value']:,}")
        return (f"fresh {got_early['value']:,} · "
                f"stale {got_late['value']:,}")

    @check("the survey office says how old the chart is")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _chart("office", "screen")
        game.day += int(FRESH_DAYS * 0.7)
        fresh = charts.freshness(game, game.system)
        assert fresh < 0.95, fresh

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("port")
        view = win.views["port"]
        view.tab = "contracts"
        view.refresh()
        for _ in range(3):
            app.processEvents()
        rows = [lab.text() for lab in view.findChildren(QLabel) if lab.text()]
        win.close()
        assert "Age of the survey" in rows, (
            "the office never says the chart is going off — the row exists "
            "and could not fire, because nothing was ever dated")
        assert any(f"{round(fresh * 100)}% of fresh" in r for r in rows), (
            f"the office does not state the {fresh:.2f} it is pricing on")
        return f"the office reads {round(fresh * 100)}% of fresh"
