"""Working a body out: whether it ever ends, and whether the method matters.

A body capped at 95% depleted and then paid a token tonne a session **for
ever** — measured still yielding at trip 199, exactly as at trip 20. So there
was never a moment at which a seam was finished, never a reason to prospect
for another, and no point at all to a method that works a body gently: the
cap arrived whatever you did.

With an ending, the four methods finally pull in different directions. From
one body: `bore` lifts 2.12 t a day and takes 179 t in total; `leach` lifts
0.94 a day and takes 389. Rate against lifetime, and neither figure is
visible from the other — which is why the panel states both.

The claims:

- **A body ends**, and says so rather than paying out forever.
- **Gentle methods get more out of it**, and fast ones get it sooner.
- **The forecast is what the body actually gives up** — calibrated against
  the measurement, and re-measured here so it cannot quietly drift.
"""

from __future__ import annotations

import statistics

from ..core.state import new_game
from ..data.mining import METHODS
from ..sim import mining
from ..sim.actions import extract
from .harness import Suite


def _work_out(method_id: str, seed: str, days_each: int = 10,
              cap: int = 400) -> tuple[float, int, str]:
    """Work one body until it refuses. Returns (lifted, days, why it stopped)."""
    game = new_game(seed)
    game.research.unlocked.append("drink")
    lifted, start, why = 0.0, game.day, ""
    for _ in range(cap):
        game.ship.cargo = {"volatiles": 60}
        game.stores["biomass"] = 900
        res = extract(game, 0, days_each, method_id)
        if not res.get("ok"):
            why = res.get("why", "")
            break
        lifted += sum(res.get("got", {}).values())
        if game.dead or game.victory:
            why = "the chronicle ended"
            break
    return lifted, game.day - start, why


def run(suite: Suite) -> None:
    check = suite.check

    @check("a body is finished eventually, and says so")
    def _():
        # It used to sit at the cap paying 1.1 t a session without limit.
        lifted, days, why = _work_out("bore", "endings")
        assert "worked out" in why.lower(), (
            f"four hundred sessions on one body and it stopped because "
            f"{why!r} — a seam that never ends is a seam nobody leaves")
        game = new_game("endings")
        body = game.system.bodies[0]
        body.depleted = 1.0
        assert mining.worked_out(body)
        res = extract(game, 0, 10, "cut")
        assert not res["ok"] and "worked out" in res["why"].lower(), res
        return (f"a body gave up {lifted:.0f} t over {days} days and then "
                "refused the rig")

    @check("a gentle method takes more out of a body than a fast one")
    def _():
        # The whole reason to have four methods. While the cap paid out for
        # ever this was untrue and unmeasurable: everything converged.
        totals, rates = {}, {}
        for method in METHODS:
            lifted = [_work_out(method.id, f"t{method.id}{trial}")
                      for trial in range(6)]
            totals[method.id] = statistics.mean(x[0] for x in lifted)
            rates[method.id] = statistics.mean(
                x[0] / max(1, x[1]) for x in lifted)

        fastest = max(rates, key=rates.get)
        richest = max(totals, key=totals.get)
        assert fastest != richest, (
            f"{fastest} is both the fastest and the most productive way to "
            "work a body, so there is no decision here")
        assert totals[richest] > totals[fastest] * 1.4, (
            f"{richest} takes {totals[richest]:.0f} t against {fastest}'s "
            f"{totals[fastest]:.0f} — not enough to be worth the extra time")
        assert rates[fastest] > rates[richest] * 1.4, (
            f"{fastest} lifts {rates[fastest]:.2f} t/day against "
            f"{richest}'s {rates[richest]:.2f} — not enough to be worth the "
            "waste")
        return (f"{fastest} {rates[fastest]:.2f} t/day for "
                f"{totals[fastest]:.0f} t total · {richest} "
                f"{rates[richest]:.2f} t/day for {totals[richest]:.0f} t")

    @check("the forecast is what the body actually gives up")
    def _():
        # `WORKING_LOSS` is calibrated against this measurement rather than
        # derived, so this is the thing that keeps it honest: if the
        # extraction arithmetic moves and the estimate stops matching, it
        # fails here rather than misleading a captain.
        rows = []
        for method in METHODS:
            said, got = [], []
            for trial in range(6):
                game = new_game(f"fc{method.id}{trial}")
                game.research.unlocked.append("drink")
                said.append(mining.prospect(game.system.bodies[0], method.id,
                                            game.ship_stats)["total"])
                got.append(_work_out(method.id, f"fc{method.id}{trial}")[0])
            claimed, actual = statistics.mean(said), statistics.mean(got)
            assert claimed > 0, method.id
            ratio = actual / claimed
            assert 0.75 <= ratio <= 1.3, (
                f"{method.id}: the panel promises {claimed:.0f} t and the "
                f"body gives up {actual:.0f} ({ratio:.0%})")
            rows.append(f"{method.id} {ratio:.0%}")
        return " · ".join(rows)

    @check("the forecast says how long the body has left, and is right")
    def _():
        checked = 0
        for method in METHODS:
            game = new_game(f"days-{method.id}")
            game.research.unlocked.append("drink")
            said = mining.prospect(game.system.bodies[0], method.id,
                                   game.ship_stats)["days"]
            if said <= 0:
                continue
            _lifted, spent, _why = _work_out(method.id, f"days-{method.id}")
            # Mishaps collapse a working and end a body early, so the forecast
            # is an upper bound rather than a promise — which is what "at this
            # rate" means, and why the risk is stated beside it.
            assert spent <= said * 1.25 + 20, (
                f"{method.id}: said {said:.0f} days and took {spent}")
            assert spent > said * 0.35, (
                f"{method.id}: said {said:.0f} days and it was over in "
                f"{spent} — the estimate is not worth reading")
            checked += 1
        assert checked >= 3, checked
        return f"{checked} methods, every estimate inside the working range"

    @check("the mining screen states the lifetime as well as the rate")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("panel")
        # The mining panel wants a body you have actually looked at — an
        # unsurveyed rock shows a name and an orbit and nothing else.
        game.system.bodies[0].surveyed = True
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("system")
        # The mining panel only appears with a body selected — the screen
        # opens on the system itself.
        win.views["system"].selected = 0
        win.views["system"].refresh()
        for _ in range(3):
            app.processEvents()
        texts = " ".join(w.text() for w in
                         win.views["system"].findChildren(QLabel) if w.text())
        assert "Body lasts" in texts, (
            "the screen never says how long the body has left")
        assert "Total still in it" in texts, (
            "the screen states a daily rate and never a lifetime, which is "
            "the half that decides which method to use")
        win.close()
        return "rate and lifetime both on the screen before the rig goes on"
