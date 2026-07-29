"""Four ways to run a programme, and whether any of them is a choice.

Measured, `push` was simply the best. Fastest mean time to unlock — 76 days
against `careful`'s 132 — with its 28%-a-season setback risk *already priced
into that figure*, because a setback only costs progress and progress is what
the measurement counts. Four approaches on the screen and one answer.

The blurb had always named the missing cost: "skip the confirmations, build on
results nobody has replicated." Nothing read it. So a pushed result is
provisional now — the technology unlocks and delivers a fraction of what it
promises until somebody goes back over the figures — which is a cost that
"days to unlock" cannot see, and exactly why the dominance was invisible.

The claims:

- **Pushing leaves debt**, and careful work does not.
- **A provisional technology is worth less**, in the bonuses that reach the
  ship.
- **The debt can be paid**, in bench time.
- **No approach dominates** once soundness is counted.
"""

from __future__ import annotations

import statistics

from ..data.inquiry import APPROACHES, EVIDENCE
from ..data.tech import PROVISIONAL_WORTH, TECH, TECH_BY_ID, bonuses
from ..core.state import new_game
from ..sim import inquiry
from .harness import Suite

#: Derived from the data, not written out. The hand-written tuple here named
#: `field`, `relic` and `trade` — none of which are evidence kinds — and
#: omitted `reading`, which is. `inquiry.add` returns 0.0 for a name it does
#: not know, silently, so three of the six did nothing and every programme in
#: a branch that wants `reading` (cognition asks for 35% of it) was measured
#: on a bench starved of it. `test_bench` has always derived this correctly.
KINDS = tuple(e.id for e in EVIDENCE)


def _programmes(approach: str, count: int, seed: str, trickle: float = 400,
                cap: int = 14000):
    """Run `count` programmes back to back. Returns the game and the days."""
    game = new_game(seed)
    inquiry.set_approach(game.research, approach)
    day = 0
    for _ in range(count):
        target = next((t for t in TECH if t.id not in game.research.unlocked),
                      None)
        if target is None:
            break
        game.research.current = target.id
        game.research.progress = 0.0
        while game.research.current == target.id and day < cap:
            for kind in KINDS:
                inquiry.add(game.research, kind, trickle)
            game.advance_days(30)
            day += 30
            if game.dead or game.victory:
                break
    return game, day


def _settle(game, day: int, cap: int = 20000) -> int:
    """Go back and confirm everything left unreplicated."""
    while game.research.provisional and day < cap:
        target = game.research.provisional[0]
        game.research.confirming = target
        game.research.confirm_days = inquiry.confirm_cost(game.research, target)
        while game.research.confirming and day < cap:
            game.advance_days(30)
            day += 30
    return day


def run(suite: Suite) -> None:
    check = suite.check

    @check("every fast approach can hand you an unreplicated result")
    def _():
        for approach in APPROACHES:
            assert hasattr(approach, "provisional"), approach.id
            assert 0.0 <= approach.provisional <= 1.0, approach.id
            if approach.speed > 1.6:
                assert approach.provisional > 0, (
                    f"{approach.id} runs at x{approach.speed} and never hands "
                    "you an unchecked result — that is free speed")
        careful = next(a for a in APPROACHES if a.id == "careful")
        assert careful.provisional == 0.0 and careful.setback == 0.0, (
            "the careful approach is supposed to be the sound one")
        return " · ".join(f"{a.id} {a.provisional:.0%}" for a in APPROACHES)

    @check("pushing leaves debt and careful work does not")
    def _():
        pushed = sound = 0
        for trial in range(14):
            game, _day = _programmes("push", 3, f"push{trial}")
            pushed += len(game.research.provisional)
            game, _day = _programmes("careful", 3, f"care{trial}")
            sound += len(game.research.provisional)
        assert pushed > 0, (
            "fourteen chronicles of pushing left not one unreplicated result")
        assert sound == 0, (
            f"{sound} careful programmes came out unconfirmed")
        return (f"pushing left {pushed} unconfirmed over 14 runs; careful "
                "left none")

    @check("an unconfirmed technology is worth less to the ship")
    def _():
        # Not merely recorded — actually reaching the hull as smaller numbers.
        with_flaw = None
        for tech in TECH:
            if tech.bonus:
                with_flaw = tech
                break
        assert with_flaw is not None, "no technology grants a passive bonus"
        full = bonuses([with_flaw.id])
        shaky = bonuses([with_flaw.id], [with_flaw.id])
        moved = [k for k in full if abs(full[k] - shaky[k]) > 1e-9]
        assert moved, (
            f"{with_flaw.id} contributes the same confirmed or not")
        for key in moved:
            assert abs(shaky[key] - full[key] * PROVISIONAL_WORTH) < 1e-6, (
                f"{key}: {shaky[key]} against {full[key] * PROVISIONAL_WORTH}")

        # And it reaches the ship, not just the table. None of the *starting*
        # technologies grants a passive bonus, so one has to be unlocked here
        # rather than looked for among them.
        game = new_game("worth")
        target = with_flaw.id
        if target not in game.research.unlocked:
            game.research.unlocked.append(target)
        game.research.provisional = []
        game.recompute()
        before = dict(game.bonuses)
        game.research.provisional = [target]
        game.recompute()
        after = dict(game.bonuses)
        assert any(abs(before[k] - after.get(k, 0)) > 1e-9 for k in before), (
            "marking a technology unconfirmed changed nothing about the ship")
        return (f"a provisional result contributes {PROVISIONAL_WORTH:.0%}, "
                f"across {len(moved)} bonus(es)")

    @check("the debt can be paid, in bench time and nothing else")
    def _():
        game, day = _programmes("push", 3, "settle")
        if not game.research.provisional:
            return "nothing came out unconfirmed in this seed"
        target = game.research.provisional[0]
        cost = inquiry.confirm_cost(game.research, target)
        assert cost > 0, cost
        # Bench time and nothing else: no evidence is drawn for it. Credits
        # are *not* checked — days pass and wages are paid, which is the
        # clock's business rather than the bench's, and asserting otherwise
        # was my mistake rather than the game's.
        held = {k: inquiry.held(game.research, k) for k in KINDS}

        game.research.confirming = target
        game.research.confirm_days = cost
        spent = 0
        while game.research.confirming and spent < cost * 4:
            game.advance_days(15)
            spent += 15
        assert target not in game.research.provisional, (
            f"{target} was checked for {spent} days and is still unconfirmed")
        drawn = {k: was - inquiry.held(game.research, k)
                 for k, was in held.items()
                 if was - inquiry.held(game.research, k) > 0.01}
        assert not drawn or game.research.current, (
            f"confirming drew evidence with no programme running: {drawn}")
        return (f"{TECH_BY_ID[target].name} confirmed after {spent} days of "
                "bench time")

    @check("no approach is best at everything once soundness is counted")
    def _():
        # `push` was fastest to unlock *and* had no cost the measurement could
        # see. Now the fast approaches trade tempo for debt, and the frugal one
        # earns its place when the bench is thin.
        def to_sound(approach: str, trickle: float, trials: int = 12) -> float:
            spans = []
            for trial in range(trials):
                game, day = _programmes(approach, 2, f"nd{approach}{trial}",
                                        trickle=trickle)
                spans.append(_settle(game, day))
            return statistics.mean(spans)

        rich = {a.id: to_sound(a.id, 400) for a in APPROACHES}
        thin = {a.id: to_sound(a.id, 6) for a in APPROACHES}
        best_rich = min(rich, key=rich.get)
        best_thin = min(thin, key=thin.get)
        assert best_rich != "push" or best_thin != "push", (
            "push is still the fastest route to sound technology in both a "
            "full bench and a thin one — the choice is not a choice")
        assert rich["push"] < rich["careful"], (
            "pushing is not even faster to unlock, so it has no purpose")
        return (f"full bench: {best_rich} · thin bench: {best_thin} — "
                + " · ".join(f"{k} {v:.0f}d" for k, v in sorted(thin.items())))

    @check("the research screen states the unreplicated rate and the debt")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("screen")
        target = next(t for t in TECH if t.id not in game.research.unlocked)
        game.research.current = target.id
        inquiry.set_approach(game.research, "push")
        shaky = [t for t in game.research.unlocked if TECH_BY_ID.get(t)][:2]
        game.research.provisional = list(shaky)
        game.recompute()

        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("tech")
        for _ in range(3):
            app.processEvents()
        view = win.views["tech"]
        texts = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        assert "unreplicated" in texts, (
            "the approach panel never says what pushing costs")
        assert "Unconfirmed results" in texts, texts[:200]
        assert any("Confirm" in b for b in buttons), buttons
        win.close()
        return "the rate is on the approach panel and the debt has a button"
