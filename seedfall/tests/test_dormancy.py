"""Sleeping through a crossing: what it saves, and what it costs to wake.

The time system priced a crossing in people and offered exactly one answer —
fly harder, and pay in reaction mass. That is an engineering answer to a
biological problem. This is the other one, and the claims worth pinning are:

- **The saving is real and it is on the sleepers.** Ageing and rations both.
- **Somebody stays awake**, always, and the watch pays full price.
- **It is not a free stack with dilation.** Both cost the ship's own work, so
  doing both costs it twice.
- **Waking can fail**, at the odds the screen quoted, against the days
  actually spent under.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data.dormancy import METHODS, METHODS_BY_ID, MIN_WATCH
from ..sim import dormancy, lifespan, upkeep
from .harness import Suite


def _ready(seed: str):
    game = new_game(seed)
    game.research.unlocked.append("trehalose")
    game.stores.update({"biomass": 600, "trehalose": 600, "magnetite": 200})
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every way of sleeping states what it saves, risks and costs")
    def _():
        for method in METHODS:
            assert method.blurb and method.gives and method.costs, method.id
            assert 0.0 <= method.ageing <= 1.0, method.id
            assert 0.0 <= method.upkeep <= 1.0, method.id
            if method.id == "watch":
                assert method.risk == 0.0 and not method.cost
                continue
            assert method.ageing < 1.0, (
                f"{method.id} saves no ageing, so there is no reason to do it")
            assert method.risk > 0.0, (
                f"{method.id} is free of risk, which makes it strictly better "
                "than standing the watch")
        return (f"{len(METHODS)} methods, every one of them a trade")

    @check("a sleeper ages less, and eats less, by exactly what was promised")
    def _():
        game = _ready("saves")
        room = dormancy.most_that_can_sleep(game)
        plan = dormancy.preview(game, "vitrify", room, 400)
        assert dormancy.put_under(game, "vitrify", room)["ok"]

        sleeper = next(o for o in game.officers if dormancy.is_asleep(game, o))
        waker = next((o for o in lifespan.active(game.officers)
                      if not dormancy.is_asleep(game, o)), None)
        assert waker is not None, "nobody was left on watch"

        slept_from = lifespan.age_of(sleeper, game)
        woke_from = lifespan.age_of(waker, game)
        method = METHODS_BY_ID["vitrify"]

        game.advance_days(365)
        slept = lifespan.age_of(sleeper, game) - slept_from
        awake = lifespan.age_of(waker, game) - woke_from
        assert awake > 0.9, f"the watch aged {awake:.2f} in a year"
        assert abs(slept - awake * method.ageing) < 0.02, (
            f"a sleeper aged {slept:.3f} against {awake * method.ageing:.3f} "
            "promised")
        assert plan["cost"], "vitrification consumed nothing"
        return (f"a year under: the watch aged {awake:.2f}, the sleeper "
                f"{slept:.3f} — {method.ageing:.0%} as promised")

    @check("the rations fall with the number under")
    def _():
        game = _ready("rations")
        full = upkeep.demand(game).get("biomass", 0)
        dormancy.put_under(game, "cold", dormancy.most_that_can_sleep(game))
        under = upkeep.demand(game).get("biomass", 0)
        assert under < full * 0.6, (
            f"a sleeping crew still wants {under:.3f} against {full:.3f}")
        return (f"{full:.3f} t a day awake, {under:.3f} t with the crew under")

    @check("somebody always stands the watch")
    def _():
        # The floor is why this is a way of paying less for a crossing and
        # never a way of paying nothing.
        game = _ready("watch")
        total = dormancy.complement(game)
        room = dormancy.most_that_can_sleep(game)
        assert room < total, "the whole complement could go under"

        # Asking for more than the room still leaves a watch.
        dormancy.put_under(game, "cold", total + 50)
        assert dormancy.asleep(game) <= room, dormancy.asleep(game)

        # An absolute floor, not one recomputed from `MIN_WATCH`. Asserting
        # `total - room >= round(total * MIN_WATCH)` reads the very constant
        # whose effect it claims to test and passes with it set to zero — the
        # `max(1, ...)` leaves one person awake and the arithmetic agrees.
        # One person is not a watch on a thirty-seven-hand hull.
        share = dormancy.awake_share(game)
        assert share >= 0.10, (
            f"only {share*100:.0f}% of the complement is awake — that is not "
            "a watch, it is a survivor")
        awake_heads = total - dormancy.asleep(game)
        assert awake_heads >= 4, f"{awake_heads} awake on a hull of {total}"
        assert lifespan.active(game.officers), "every officer went under"
        assert any(not dormancy.is_asleep(game, o)
                   for o in lifespan.active(game.officers)), \
            "every officer went under; nobody is on the bridge"
        return (f"{total} aboard, at most {room} under, "
                f"{total - room} always on watch")

    @check("a short watch does less of the ship's own work")
    def _():
        # The brake that stops dormancy and a hard burn stacking into a free
        # lunch: both cost the ship's work, so doing both costs it twice.
        def banked(sleep: bool, dilation: float) -> float:
            game = _ready(f"work-{sleep}-{dilation}")
            if sleep:
                dormancy.put_under(game, "cold",
                                   dormancy.most_that_can_sleep(game))
            before = game.research.points
            game.advance_days(365, dilation)
            return game.research.points - before

        plain = banked(False, 1.0)
        slept = banked(True, 1.0)
        burnt = banked(False, 4.0)
        both = banked(True, 4.0)
        assert slept < plain * 0.6, (slept, plain)
        assert burnt < plain * 0.6, (burnt, plain)
        assert both < slept and both < burnt, (
            f"doing both banked {both:.0f}, against {slept:.0f} sleeping and "
            f"{burnt:.0f} burning — the costs do not compound")
        return (f"research over a year: {plain:.0f} awake at rest, "
                f"{slept:.0f} asleep, {burnt:.0f} at dilation 4, "
                f"{both:.0f} doing both")

    @check("waking kills at the odds the screen quoted")
    def _():
        method = METHODS_BY_ID["vitrify"]
        days, trials = 400, 40
        said = 1.0 - (1.0 - method.risk / 100.0) ** (days / 100.0)
        lost = total = 0
        for trial in range(trials):
            game = _ready(f"risk{trial}")
            room = dormancy.most_that_can_sleep(game)
            dormancy.put_under(game, "vitrify", room)
            before = dormancy.asleep(game)
            game.advance_days(days)
            res, _lines = dormancy.wake(game, RNG(f"w{trial}"))
            assert res["ok"], res
            lost += res["lost"]
            total += before
        seen = lost / max(1, total)
        assert abs(seen - said) < said * 0.35, (
            f"the screen said {said*100:.1f}% and {seen*100:.1f}% did not "
            "come up")
        return (f"{total} sleepers over {trials} crossings: quoted "
                f"{said*100:.1f}%, lost {seen*100:.1f}%")

    @check("running out of the medium brings them up rather than killing them")
    def _():
        game = _ready("dry")
        game.stores["trehalose"] = 4
        game.ship.cargo.pop("trehalose", None)
        room = dormancy.most_that_can_sleep(game)
        dormancy.put_under(game, "vitrify", room)
        before = game.ship.crew
        game.advance_days(500)
        assert dormancy.current(game) is None, (
            "they are still under with no trehalose left to hold them")
        assert game.ship.crew > before * 0.5, (
            f"{before} became {game.ship.crew} when the sugar ran out")
        return (f"the medium ran out and {game.ship.crew} of {before} came up")

    @check("a lineage can only sleep the way its body allows")
    def _():
        from ..sim.beginning import Choices
        out = {}
        for stock in ("wet", "dry"):
            game = new_game(f"lin-{stock}", 42, Choices(
                stock=stock, origin="surveyor", hull="navis",
                posting="charter", crew=(), name="T"))
            game.research.unlocked.append("trehalose")
            offered = {m.id: ok for m, ok, _w in dormancy.available(game)}
            out[stock] = sorted(k for k, v in offered.items() if v)
        assert "idle" in out["dry"] and "idle" not in out["wet"], out
        assert "cold" in out["wet"] and "cold" not in out["dry"], out
        return " · ".join(f"{k}: {', '.join(v)}" for k, v in out.items())

    @check("the ship screen states the whole bargain before you take it")
    def _():
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _ready("screen")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("ship")
        for _ in range(3):
            app.processEvents()
        view = win.views["ship"]
        texts = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
        buttons = [b.text() for b in view.findChildren(QPushButton) if b.text()]
        for phrase in ("come back up", "of their span", "The hull runs at"):
            assert phrase in texts, f"the screen never says {phrase!r}"
        assert any("under" in b.lower() for b in buttons), buttons
        win.close()
        return "ageing, rations, odds and the hull's rate all stated first"
