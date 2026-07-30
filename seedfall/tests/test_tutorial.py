"""Tutorial checks — it must not take your word for it.

A step that says "survey a body" and advances because Next was pressed has
taught nobody anything, and it will happily march a confused player through
eight screens of congratulation. So every lesson names a watcher, and every
watcher is a function of game state compared against a mark taken when the
lesson opened.

The sharpest check here drives the whole tutorial by *doing* each thing, and
separately proves that not doing it leaves the tutorial exactly where it was.
"""

from __future__ import annotations

import os
import tempfile

from ..core.rng import RNG
from ..core.state import new_game
from ..data.lessons import LESSONS, LESSONS_BY_ID
from ..sim import contracts as contract_sim
from ..sim import market as market_sim
from ..sim import trade as trade_sim
from ..sim import tutorial as tutorial_sim
from ..sim.actions import survey
from .harness import Suite


def _do(game, watch: str) -> None:
    """Actually perform the thing lesson `watch` is waiting for."""
    if watch == "surveyed_one":
        # The starting system can be as small as two bodies, so find one
        # that is still unsurveyed rather than assuming there is one here.
        index = next((i for i, b in enumerate(game.system.bodies)
                      if not b.surveyed), None)
        if index is None:
            elsewhere = next(s for s in game.galaxy.systems
                             if any(not b.surveyed for b in s.bodies))
            game.location_id = elsewhere.id
            index = next(i for i, b in enumerate(elsewhere.bodies)
                         if not b.surveyed)
        survey(game, index)
    elif watch == "saw_market":
        market_sim.note_prices(game, game.system, 0, 0)
    elif watch == "sold_something":
        # Sell what is already aboard. Adding cargo and then selling it puts
        # the hold back where the mark was, so the watcher — which wants
        # credits up *and* the hold lighter — correctly saw nothing.
        held = next((c for c, t in game.ship.cargo.items()
                     if c != "volatiles" and t > 0), None)
        assert held, "nothing aboard to sell"
        trade_sim.sell(game, held, game.ship.cargo[held])
    elif watch == "bought_fuel":
        trade_sim.buy(game, "volatiles", 10)
    elif watch == "moved":
        game.orbit_body = "1"
    elif watch == "took_contract":
        offered = contract_sim.generate(RNG("tut"), game, game.system)
        contract_sim.accept(game, offered[0])
    elif watch == "saw_plans":
        tutorial_sim.saw(game, "ship:plans")
    elif watch == "saw_diplomacy":
        tutorial_sim.saw(game, "diplomacy")
    else:
        raise AssertionError(f"the check does not know how to do {watch!r}")


def _at_a_port(seed: str):
    game = new_game(seed)
    if not game.system.port:
        port = next(s for s in game.galaxy.systems if s.port and s.market)
        game.location_id = port.id
    game.credits = 60_000
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every lesson has a watcher, and every watcher has a lesson")
    def _():
        wanted = {lesson.watch for lesson in LESSONS}
        assert wanted <= set(tutorial_sim.WATCHERS), (
            f"lessons waiting on nothing: {sorted(wanted - set(tutorial_sim.WATCHERS))}")
        orphans = set(tutorial_sim.WATCHERS) - wanted
        assert not orphans, f"watchers no lesson uses: {sorted(orphans)}"
        for lesson in LESSONS:
            assert lesson.ask and lesson.then and lesson.title
            assert lesson.screen, f"{lesson.id} points at no screen"
        assert len(LESSONS_BY_ID) == len(LESSONS), "two lessons share an id"
        return f"{len(LESSONS)} lessons, {len(tutorial_sim.WATCHERS)} watchers, paired"

    @check("the whole tutorial can be walked by doing the things")
    def _():
        game = _at_a_port("tut-walk")
        tutorial_sim.begin(game)
        walked = []
        for _ in range(len(LESSONS) + 2):
            lesson = tutorial_sim.current(game)
            if lesson is None:
                break
            assert not tutorial_sim.check(game), (
                f"{lesson.id} was satisfied before anything was done")
            _do(game, lesson.watch)
            assert tutorial_sim.check(game), (
                f"{lesson.id}: did the thing and it was not noticed")
            standing = tutorial_sim.state(game)
            assert standing["explaining"], lesson.id
            assert standing["text"] == lesson.then
            assert tutorial_sim.acknowledge(game)
            walked.append(lesson.id)
        assert walked == [l.id for l in LESSONS], walked
        assert not tutorial_sim.running(game), "it did not finish"
        assert tutorial_sim.state(game)["finished"]
        return f"{len(walked)} lessons walked in order by doing each one"

    @check("not doing the thing leaves it exactly where it was")
    def _():
        # The defect this whole design exists to avoid.
        game = _at_a_port("tut-idle")
        tutorial_sim.begin(game)
        first = tutorial_sim.current(game)
        for _ in range(30):
            game.advance_days(10)
            assert not tutorial_sim.check(game), (
                "the tutorial advanced on its own")
        assert tutorial_sim.current(game) is first
        assert tutorial_sim.state(game)["step"] == 1
        # Acknowledging when nothing has happened must do nothing either.
        assert not tutorial_sim.acknowledge(game)
        assert tutorial_sim.current(game) is first
        return "300 days of doing nothing, still on lesson one"

    @check("a captain who did it already is not advanced for free")
    def _():
        # The mark is taken when the lesson opens, so "survey a body" means
        # one more than you had. Without it, anybody who surveyed something
        # before the tutorial started would be waved through.
        game = _at_a_port("tut-mark")
        survey(game, 0)
        survey(game, 1)
        tutorial_sim.begin(game)
        assert not tutorial_sim.check(game), (
            "an earlier survey satisfied the lesson")
        _do(game, "surveyed_one")
        assert tutorial_sim.check(game)
        return "two bodies surveyed beforehand, and the lesson still had to be done"

    @check("a veteran restarting it is not made to do it all again")
    def _():
        # **The other half of the check above, and the reason `skip_if` existed.**
        # The tutorial can be started from the Help screen at any time, so a
        # captain two years in was being told to "survey one of the bodies here"
        # with thirty surveys behind them, and had to go and do another. Every
        # step demanded a fresh action for something long since learned.
        #
        # `Lesson.skip_if` was declared for exactly this from the day lessons were
        # written, set on **no lesson at all**, and read by nothing.
        from ..sim import market as market_sim

        game = _at_a_port("tut-veteran")
        survey(game, 0)
        market_sim.note_prices(game, game.system)
        game.discovered["systems"].append(
            next(s.id for s in game.galaxy.systems if s.id != game.location_id))
        game.day = 700

        tutorial_sim.begin(game)
        told = tutorial_sim.state(game)
        assert told["running"], told
        assert told["known"] == 2, (
            f"{told['known']} steps stepped over; surveying and a noted market "
            "are both demonstrably done")
        assert told["lesson"].id == "sell", told["lesson"].id
        assert told["step"] == 3, told["step"]

        # And the rest is still taught, including the ones the chronicle cannot
        # vouch for. `helm` goes when its turn comes, because `_past_known` runs
        # after every step and not only at the start.
        taught = []
        for _ in range(len(LESSONS) + 2):
            state = tutorial_sim.state(game)
            if not state.get("running"):
                break
            taught.append(state["lesson"].id)
            _do(game, state["lesson"].watch)
            assert tutorial_sim.check(game), state["lesson"].id
            tutorial_sim.acknowledge(game)
        assert "helm" not in taught, (
            f"the helm lesson was taught to a captain who has been to another "
            f"system: {taught}")
        assert {"sell", "fuel", "ship", "powers"} <= set(taught), taught
        assert tutorial_sim.held(game).known == 3, tutorial_sim.held(game).known
        return (f"opened at step 3 of {len(LESSONS)} with 2 already done, "
                f"taught {', '.join(taught)}, stepped over 3 in all")

    @check("the settling-in month is a month, not a moratorium")
    def _():
        # The check above stands at day 700 and the one above that inside the
        # first weeks, so between them they say the gate exists — but not
        # *where*. Set `SETTLED_IN_DAYS` to two months and both still pass, and
        # a captain a season in would be sent to survey a body again.
        #
        # So this one brackets it from both sides with the same captain: a week
        # in, everything is taught; six weeks in, what the chronicle can show is
        # stepped over. Whatever the number is, it lies between them.
        made = []
        for day in (7, 45):
            game = _at_a_port(f"tut-month-{day}")
            survey(game, 0)
            game.day = day
            tutorial_sim.begin(game)
            made.append(tutorial_sim.state(game)["known"])
        early, settled = made
        assert early == 0, (
            f"a captain {7} days in was stepped over {early} lessons — inside "
            "the settling-in month nothing is assumed")
        assert settled == 1, (
            f"a captain 45 days in was stepped over {settled} lessons; the "
            "survey behind them should have counted by then")
        return "a week in nothing is assumed, six weeks in the survey counts"

    @check("only the lessons the chronicle can vouch for carry a skip")
    def _():
        # Four of eight, and the four that do not are not an oversight: the
        # chronicle keeps *state*, and "was cargo ever sold", "were volatiles
        # bought rather than mined" and "was this screen ever opened" are
        # *history* it does not keep. Inventing a counter to feed a tutorial
        # would be the tail wagging the dog.
        named = {lesson.id: lesson.skip_if for lesson in LESSONS
                 if lesson.skip_if}
        assert len(named) == 4, named
        for lesson in LESSONS:
            if lesson.skip_if:
                assert lesson.skip_if in tutorial_sim.SKIPS, (
                    f"{lesson.id} names a skip watcher that does not exist: "
                    f"{lesson.skip_if}")
        stray = set(tutorial_sim.SKIPS) - set(named.values())
        assert not stray, f"skip watchers no lesson names: {stray}"

        # Each one is false on a fresh chronicle and true once the thing is done,
        # which is the whole of what it claims.
        game = _at_a_port("tut-skips")
        game.day = 700
        for name, fn in tutorial_sim.SKIPS.items():
            assert not fn(game), (
                f"{name} is already true of a chronicle where nothing has "
                "happened")
        from ..sim import market as market_sim
        survey(game, 0)
        market_sim.note_prices(game, game.system)
        game.discovered["systems"].append(
            next(s.id for s in game.galaxy.systems if s.id != game.location_id))
        fired = [name for name, fn in tutorial_sim.SKIPS.items() if fn(game)]
        assert set(fired) == {"have_surveyed", "have_prices", "have_travelled"}, \
            fired
        return (f"{len(named)} of {len(LESSONS)} lessons carry a skip; "
                f"{len(fired)} fired once the things were done")

    @check("a chronicle can be opened with a lesson already running")
    def _():
        # **Which is the reload case, and it crashed.** `MainWindow.__init__`
        # builds the tutorial bar, the bar refreshes on construction, and it asks
        # `win.current` to decide whether to offer "Take me there" — while
        # `self.current` was assigned forty lines further down. So opening a
        # chronicle that already had a tutorial running died with
        # `'MainWindow' object has no attribute 'current'`.
        #
        # Every check here built the window first and started the tutorial after,
        # so not one of them ever went through this door.
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..ui import theme
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        game = _at_a_port("tut-reload")
        tutorial_sim.begin(game)                # running *before* the window
        assert tutorial_sim.running(game)
        win = MainWindow(game)                  # this used to raise
        win.resize(1100, 700)
        win.dialog = lambda *a, **k: None
        win.go("port")
        win.refresh()
        win.grab()
        # `isHidden`, not `isVisible`: the window is never shown here, and a
        # widget in an unshown window is not "visible" however it was set. The
        # bar's own `setVisible(False)` is what this is asking about.
        assert not win.tutorial_bar.isHidden(), "the bar did not come up"
        from PyQt6.QtWidgets import QLabel
        said = " ".join(lb.text() for lb in
                        win.tutorial_bar.findChildren(QLabel))
        assert "of" in said and said.strip(), said
        return "a window built around a running tutorial opens and draws"

    @check("it never blocks a screen")
    def _():
        # A tutorial that stops you doing the thing it describes is worse than
        # none. Checked by walking every screen with a lesson open rather than
        # by reading `go()` for the word "tutorial" — the first version did
        # that and tripped over the import line.
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..data.screens import SCREENS
        from ..ui import theme
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        game = _at_a_port("tut-free")
        win = MainWindow(game)
        win.resize(1200, 800)
        win.show()
        tutorial_sim.begin(game)
        blocked = []
        for sid, _label, _key in SCREENS:
            win.go(sid)
            app.processEvents()
            if win.current != sid:
                blocked.append(f"{sid} → {win.current}")
        win.close()
        assert not blocked, f"the tutorial diverted: {blocked}"
        return f"all {len(SCREENS)} screens reachable with a lesson open"

    @check("it survives a save, mid-lesson and mid-explanation")
    def _():
        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game

        game = _at_a_port("tut-save")
        tutorial_sim.begin(game)
        _do(game, "surveyed_one")
        tutorial_sim.check(game)
        tutorial_sim.acknowledge(game)
        _do(game, "saw_market")
        tutorial_sim.check(game)              # part-way: explaining lesson two
        assert tutorial_sim.state(game)["explaining"]

        save_mod.write({"game": game})
        back = load_game()
        assert back is not None
        assert tutorial_sim.running(back), "the tutorial was lost"
        assert back.tutorial.step == 1
        assert tutorial_sim.state(back)["explaining"], (
            "it forgot it was mid-explanation")
        assert tutorial_sim.acknowledge(back)
        assert tutorial_sim.current(back).id == LESSONS[2].id
        return "reloaded mid-explanation on lesson two and carried on"

    @check("skipping is final until it is started again")
    def _():
        game = _at_a_port("tut-skip")
        tutorial_sim.begin(game)
        tutorial_sim.skip(game)
        assert not tutorial_sim.running(game)
        assert tutorial_sim.current(game) is None
        assert not tutorial_sim.state(game)["running"]
        assert not tutorial_sim.state(game)["finished"], (
            "a skipped tutorial reports as finished")
        for _ in range(5):
            game.advance_days(30)
            assert not tutorial_sim.check(game), "a skipped tutorial came back"
        tutorial_sim.begin(game)
        assert tutorial_sim.running(game), "it could not be started again"
        assert tutorial_sim.current(game).id == LESSONS[0].id
        return "skipped, stayed skipped for 150 days, and restarted from the top"

    @check("the bar draws every lesson and both of its faces")
    def _():
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..ui import theme
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        game = _at_a_port("tut-draw")
        win = MainWindow(game)
        win.resize(1300, 850)
        win.show()
        tutorial_sim.begin(game)

        painted = 0
        for lesson in LESSONS:
            win.tutorial_bar.refresh()
            app.processEvents()
            assert win.tutorial_bar.isVisible(), f"{lesson.id} drew nothing"
            assert not win.tutorial_bar.grab().isNull()
            painted += 1
            _do(game, lesson.watch)
            tutorial_sim.check(game)
            win.tutorial_bar.refresh()          # the explanation face
            app.processEvents()
            assert not win.tutorial_bar.grab().isNull()
            painted += 1
            tutorial_sim.acknowledge(game)
        win.tutorial_bar.refresh()
        app.processEvents()
        assert not win.tutorial_bar.isVisible(), (
            "the bar is still there with nothing left to say")
        win.close()
        return f"{painted} faces drawn across {len(LESSONS)} lessons, then gone"
