"""Coming home from the ground: what the lander lifts, and what it leaves.

`haul_kept` applied the carrying limit on the way home and **skipped it
entirely when the party stranded**. Stranding returned 40% of everything ever
picked up, uncapped, while walking back to the pad was capped at what four
people can lift. Five hundred tonnes came home as 200 t stranded against 60 t
returned.

So the penalty was a reward. Measured with `ground_ai`: a leader who never
turned back kept **933 t**; one who always walked home kept **41 t**. The way
to play the ground was to strand the party deliberately — which is also the
opposite of what the ending says, since everything not on their backs is
supposed to stay where it fell.

The order is the fix: what they can carry, and *then* what stranding costs.

The claims:

- **Walking home pays better than stranding.**
- **The carrying limit binds whatever the outcome.**
- **The turn-back margin is a real decision** — a peak in the middle, not at
  either end.
- **The screen states what comes up, and the forecast is what lands.**
"""

from __future__ import annotations

import collections

from ..core.rng import RNG
from ..core.state import new_game
from ..data.expedition import PARTY_CAPACITY
from ..sim import expedition as ex
from . import ground_ai
from .harness import Suite


class _Party:
    """A bare party with a known haul, for arithmetic that needs no terrain."""

    def __init__(self, tonnes: float, outcome: str = "returned"):
        self.haul = {"ore": tonnes}
        self.outcome = outcome

    @property
    def carried(self) -> float:
        return sum(self.haul.values())


def _run(seed: str, margin):
    game = new_game(seed)
    party = ex.generate(RNG(f"g-{seed}"), game.system, game.system.bodies[0],
                        [o.id for o in game.officers])
    ground_ai.play(game, party, RNG(f"r-{seed}"), margin=margin)
    return party


def _sweep(margin, trials: int = 60) -> tuple[float, collections.Counter]:
    kept, outs = [], collections.Counter()
    for trial in range(trials):
        party = _run(f"s{trial}", margin)
        kept.append(sum(ex.haul_kept(party).values()))
        outs[party.outcome or "unfinished"] += 1
    return sum(kept) / len(kept), outs


def run(suite: Suite) -> None:
    check = suite.check

    @check("the carrying limit binds whatever the outcome")
    def _():
        # The arithmetic on its own, with no terrain in the way. Stranding may
        # never beat walking home for the same pile — it used to, three times
        # over, because the cap was on one branch only.
        rows = []
        for tonnes in (10, 60, 140, 500):
            home = sum(ex.haul_kept(_Party(tonnes, "returned")).values())
            lost = sum(ex.haul_kept(_Party(tonnes, "stranded")).values())
            assert home <= PARTY_CAPACITY + 1e-9, (
                f"{tonnes} t walked home as {home} t, over a limit of "
                f"{PARTY_CAPACITY}")
            assert lost <= PARTY_CAPACITY + 1e-9, (
                f"{tonnes} t stranded came home as {lost} t, over a limit of "
                f"{PARTY_CAPACITY} — the cap is not applied on this branch")
            assert lost < home, (
                f"{tonnes} t: stranding brings back {lost} against {home} for "
                "walking home, so stranding is the better play")
            rows.append(f"{tonnes}t → {home:.0f}/{lost:.0f}")
        return "carried → home/stranded: " + " · ".join(rows)

    @check("a leader who walks home beats one who never turns back")
    def _():
        # End to end, through the same driver, on the same seeds.
        stayed, stayed_outs = _sweep(None)
        walked, walked_outs = _sweep(4)
        assert stayed_outs["stranded"] > 20, dict(stayed_outs)
        assert walked_outs["returned"] > 20, dict(walked_outs)
        assert walked > stayed * 1.2, (
            f"never turning back keeps {stayed:.1f} t against {walked:.1f} t "
            "for walking home — the supplies are not a deadline, they are a "
            "collection target")
        return (f"never turning back {stayed:.1f} t · walking home "
                f"{walked:.1f} t")

    @check("how much supply to keep back is a real decision")
    def _():
        # A peak in the middle. Too little strands the party; too much spends
        # the expedition walking. If the best margin were an endpoint there
        # would be no decision, only a rule.
        # 120 seeds a margin: at 40 the peak is in the same place but the
        # gap to margin 0 wobbles between 1.12x and 1.21x, which is too thin
        # to write a threshold against. Six hundred expeditions cost about
        # three seconds, so they are simply run.
        scores = {margin: _sweep(margin, trials=120)[0]
                  for margin in (0, 2, 4, 8, 14)}
        best = max(scores, key=scores.get)
        shape = {k: round(v, 1) for k, v in scores.items()}
        # The claim that matters, and the one that held at every sample size:
        # the best answer is inside the range rather than at an end of it.
        assert best not in (0, 14), (
            f"the best margin is {best}, at the end of the range — that is a "
            f"rule, not a decision: {shape}")
        # Measured 1.21x and 1.55x at this sample size; asserted lower so a
        # small drift is not a failure and a collapse is.
        assert scores[best] > scores[0] * 1.12, (
            f"margin {best} keeps {scores[best]:.1f} t against "
            f"{scores[0]:.1f} t for never holding anything back: {shape}")
        assert scores[best] > scores[14] * 1.30, (
            f"margin {best} keeps {scores[best]:.1f} t against "
            f"{scores[14]:.1f} t for turning back almost at once: {shape}")
        return (f"best margin {best}: "
                + " · ".join(f"{k}→{v:.0f}t" for k, v in sorted(scores.items())))

    @check("supplies never run past empty")
    def _():
        # `-1 days of supply left` was reachable, because a crossing that cost
        # two could be paid out of one.
        lowest = 0
        for margin in (None, 1, 4):
            for trial in range(20):
                party = _run(f"neg{trial}", margin)
                lowest = min(lowest, party.supply)
        assert lowest >= 0, (
            f"a party got down to {lowest} days of supply, which is a number "
            "the screen should never have to print")
        return "sixty parties, none of them past empty"

    @check("the forecast is what the lander actually lifts")
    def _():
        # Screen and outcome off one helper, the rule this project keeps
        # relearning.
        checked = 0
        for margin in (None, 4):
            for trial in range(12):
                party = _run(f"fc{trial}", margin)
                if not party.over:
                    continue
                said = ex.landing_forecast(party)
                landed = sum(ex.haul_kept(party).values())
                want = (said["stranded"] if party.outcome == "stranded"
                        else said["kept"])
                assert abs(landed - want) < 0.01, (
                    f"{party.outcome}: the forecast said {want:.1f} t and "
                    f"{landed:.1f} t came up")
                checked += 1
        assert checked > 10, checked
        return f"{checked} landings, every one as forecast"

    @check("the ground screen says what comes up and what stranding costs")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("screen")
        party = ex.generate(RNG("screen"), game.system, game.system.bodies[0],
                            [o.id for o in game.officers])
        party.haul = {"ore": PARTY_CAPACITY * 2.5}
        game.expedition = party
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("ground")
        for _ in range(3):
            app.processEvents()
        rows = [lab.text() for lab in win.views["ground"].findChildren(QLabel)
                if lab.text()]
        win.close()
        said = ex.landing_forecast(party)
        assert "Comes up" in rows, (
            "the screen shows what they are carrying and never what lifts")
        assert "If they strand" in rows, (
            "the screen never states what stranding would cost")
        assert any(f"{round(said['kept'])} t" in r for r in rows), rows[:8]
        assert any(f"{round(said['stranded'])} t" in r for r in rows), rows[:8]
        return (f"carrying {said['carried']:.0f} t: "
                f"{said['kept']:.0f} up, {said['stranded']:.0f} if stranded")
