"""One long chronicle, driven through every screen it accumulates.

The other suites build fresh, narrow games. `test_verbs` clicks every control,
but on a chronicle that has never finished a survey; `test_ui` paints every
screen, but on a game with no history. Nothing put a decade of accumulated
state — charts, colonies, treaties, scrutiny, field notes, works, a hold full
of contraband — in front of the screens that read it.

That gap shipped a crash. Chart completion dates were kept in `game.register`,
which is the *price* register, and `market.best_markets` reads `.sell` off
everything in it — so a charted sector plus a port screen raised
`AttributeError` inside a Qt slot, where Qt swallows the traceback and the panel
silently fails to draw. Rendering the README screenshots found it in minutes,
because that was one long save touching every screen in sequence.
"""

from __future__ import annotations

import os
import sys
import tempfile

from ..core.state import new_game
from . import chronicle
from .harness import Suite


class _Trap:
    """Collects what Qt would otherwise print to stderr and carry on past."""

    def __init__(self):
        self.caught: list[str] = []
        self._previous = None

    def __enter__(self):
        self._previous = sys.excepthook
        sys.excepthook = self._hook
        return self

    def __exit__(self, *_exc):
        sys.excepthook = self._previous
        return False

    def _hook(self, kind, value, _tb):
        self.caught.append(f"{kind.__name__}: {str(value)[:140]}")


def run(suite: Suite) -> bool:
    try:
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
    except ImportError as err:      # pragma: no cover - no Qt, no screens
        print(f"── chronicle ───\n  skipped: {err}\n")
        return False

    from ..ui import theme
    from ..ui.window import MainWindow, NAV

    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    check = suite.check

    def window(game):
        win = MainWindow(game)
        win.resize(1400, 900)
        win.dialog = lambda *a, **k: None
        win.confirm = lambda *a, **k: True
        win.toast = lambda *a, **k: None
        win.show()
        return win

    def _tabs(view) -> list[str]:
        """Which tabs this screen is actually offering, right now.

        Read off the live TabBar rather than from a hardcoded list: a screen
        that grows a tab should be covered by this the day it grows it, and a
        guessed name is a KeyError in the driver dressed up as a game bug.
        """
        from ..ui.widgets import TabBar
        return [tid for bar in view.findChildren(TabBar)
                for tid in bar.buttons]

    def paint(win, screen, trap) -> None:
        try:
            win.go(screen)
            for _ in range(2):
                app.processEvents()
            win.views[win.current].grab()
        except Exception as err:                    # noqa: BLE001 - reported
            trap.caught.append(f"{screen}: {type(err).__name__} {err}")

    def paint_all(win, trap) -> int:
        """Every standing screen, and every tab behind them."""
        painted = 0
        for screen, *_rest in NAV:
            paint(win, screen, trap)
            painted += 1
            view = win.views[screen]
            for tab in _tabs(view):
                # Click the button rather than setting the attribute: the
                # refresh runs in a Qt slot, which is exactly where an
                # exception gets swallowed instead of failing anything.
                try:
                    from ..ui.widgets import TabBar
                    for bar in view.findChildren(TabBar):
                        if tab in bar.buttons:
                            bar.buttons[tab].click()
                            break
                    for _ in range(2):
                        app.processEvents()
                    win.views[win.current].grab()
                    painted += 1
                except Exception as err:            # noqa: BLE001 - reported
                    trap.caught.append(
                        f"{screen}/{tab}: {type(err).__name__} {err}")
        return painted

    @check("a decade of one chronicle paints every screen without a word")
    def _():
        # The check the project did not have. Everything else starts fresh.
        game = new_game("chronicle-long")
        win = window(game)
        painted = [0]
        with _Trap() as trap:
            def look(g, n):
                # Every twentieth round, not every sixth. Painting 43 screens
                # is by far the expensive half of this suite and the state
                # does not change shape that fast; at every sixth the suite
                # cost 3m45 of every cycle for the same three verdicts.
                if n % 20:
                    return
                win.game = g
                painted[0] += paint_all(win, trap)

            try:
                summary = chronicle.play(game, years=10, on_beat=look)
                win.game = game
                painted[0] += paint_all(win, trap)
            except Exception as err:                # noqa: BLE001 - reported
                trap.caught.append(f"the chronicle itself: "
                                   f"{type(err).__name__} {err}")
                summary = {}
        win.close()
        assert not trap.caught, (
            f"{len(trap.caught)} screen(s) raised across the chronicle:\n      "
            + "\n      ".join(trap.caught[:6]))
        assert summary.get("rounds", 0) > 20, (
            f"the chronicle only got {summary.get('rounds')} rounds in")
        return (f"{summary['rounds']} rounds over {summary['days']} days, "
                f"{painted[0]} screen paints, "
                f"{summary['charted']} charted · {summary['colonies']} colonies "
                f"· {summary['contracts']} contracts · {summary['notes']} notes")

    @check("a decade of accumulated state survives a save and reload")
    def _():
        game = new_game("chronicle-save")
        summary = chronicle.play(game, years=8)
        assert summary["rounds"] > 10

        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game
        save_mod.write({"game": game})
        back = load_game()

        for field in ("day", "credits", "location_id"):
            assert getattr(back, field) == getattr(game, field), field
        assert len(back.colonies) == len(game.colonies)
        assert len(back.contracts) == len(game.contracts)
        assert back.register.keys() == game.register.keys()
        assert (getattr(back, "charts_made", {}).keys()
                == getattr(game, "charts_made", {}).keys())
        assert back.rep == game.rep

        win = window(back)
        with _Trap() as trap:
            painted = paint_all(win, trap)
        win.close()
        assert not trap.caught, (
            "screens raised on a reloaded chronicle:\n      "
            + "\n      ".join(trap.caught[:5]))
        return (f"{summary['days']} days reloaded and repainted across "
                f"{painted} screens")

    @check("the chronicle actually does everything it claims to")
    def _():
        # A driver that quietly stops surveying, or never plants anything, is
        # a check that stops covering what it says it covers — and every one
        # of these counters has read zero at some point while the suite went
        # on calling itself a decade of doing everything. The seed is fixed
        # because whether a *particular* pocket of the sector has a plantable
        # body outside the Bloom is luck; that the driver can still do each
        # thing is not.
        #
        # How lucky, measured: 6 of 48 seeds plant anything over a decade, the
        # blocker being that the Bloom holds most systems and you cannot plant
        # in one it holds. It was 1 of 24 until the driver was taught to put
        # in at a yard before refitting — it had been calling `apply_refit`
        # from wherever it happened to be ever since `can_refit_here`
        # tightened, getting "you are not alongside a yard" back and dropping
        # it, so the seed bay was almost never fitted. If this check fails
        # after an unrelated change, suspect the driver's reach before the
        # seed: a capability that only one seed in twenty-four exercises is
        # not being covered, it is being got away with.
        game = new_game("chronicle-cover")
        summary = chronicle.play(game, years=10)
        did = {"fought something": bool(summary.get("fights")),
               "charted a system": summary["charted"] > 0,
               "planted a colony": summary["colonies"] > 0,
               "finished a contract": summary["contracts"] > 0,
               "filed a field note": summary["notes"] > 0,
               "signed a treaty": summary["treaties"] > 0,
               "flew for years": summary["days"] > 365 * 5}
        missing = [what for what, done in did.items() if not done]
        assert not missing, f"the chronicle never: {missing}"
        return (" · ".join(f"{k} {summary[k]}" for k in
                           ("charted", "colonies", "contracts", "notes",
                            "treaties"))
                + f" · {len(summary['fights'])} engagements")

    return True
