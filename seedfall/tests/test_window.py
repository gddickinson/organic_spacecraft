"""The window as an application: navigation, saving, and the ending dialog.

Split from `tests/test_ui.py` when it went past five hundred lines, along a
seam that is real rather than convenient. `test_ui` asks whether the
*screens* draw — every view built, laid out, painted and pressed. These ask
whether the **window** behaves: that it refuses a screen it does not have
before touching anything, that quitting writes the chronicle, that a
dismissed dialog is a refusal and not a choice, and that the briefing the
player meets first is built for real rather than stubbed.

Every windowed check in `test_ui` stubs `win.dialog`, which is exactly why
the briefing check belongs here and unstubbed: the split that created
`ui/window_dialogs.py` swapped in a same-named helper that maps None to a
spacer instead of text to a label, and the first fresh launch of the game
died on it with no suite the wiser.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()


def run(suite) -> bool:
    try:
        from PyQt6.QtWidgets import QApplication
    except ImportError as err:
        print(f"── window ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.state import new_game
    from ..ui import theme
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())

    game = new_game("window-test-seed")
    port_sys = next(s for s in game.galaxy.systems if s.port)
    game.location_id = port_sys.id
    game.recompute()

    win = MainWindow(game)
    win.resize(1360, 880)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False

    @check("every topic's screen is a view this window holds")
    def _():
        # Two topics once named views that do not exist ("xeno", "conn"),
        # and the manual's "go to" button pressed them straight into `go()`.
        # A topic may be about an event view — "battle" is one, and
        # `manual.for_screen` reads it for contextual help — so the rule is
        # asked of the built window, the only place the full set exists.
        from ..data.help import TOPICS
        for topic in TOPICS:
            assert topic.screen == "" or topic.screen in win.views, (
                f"{topic.id} says it is about {topic.screen!r}, "
                f"which is not a view")
        named = sum(1 for t in TOPICS if t.screen)
        return f"{named} topics name a view, all of them held"

    @check("an unknown screen is refused before anything is touched")
    def _():
        # `go()` used to hide the outgoing view and reassign `current`
        # *before* the lookup, so one bad id (a manual topic naming a screen
        # that is not a view) bricked the window for the session — blank
        # content area, every later navigation re-raising the same KeyError.
        win.go("map")
        win.go("xeno")                       # the id that used to do it
        assert win.current == "map", f"went to {win.current!r}"
        win.go("system")                     # and navigation still works
        assert win.current == "system"
        return "refused, said so, and the window still navigates"

    @check("the opening briefing really opens, unstubbed")
    def _():
        # Every windowed check stubs `win.dialog`, so no suite had ever
        # built the real one — and the split to `ui/window_dialogs` picked
        # up `widgets.body_or` (None → spacer) in place of the string
        # wrapper, which crashed the first fresh launch of the game before
        # the title. This builds the genuine dialog, paragraphs and all.
        #
        # `exec` is stubbed rather than a timer sent to press the button:
        # a timer that hunts for a visible dialog among *all* top-level
        # widgets finds whatever an earlier suite left standing, and its
        # rescheduling chain outlives the check that started it — which is
        # why this passed alone and failed in a full run, on a dialog whose
        # C++ side had already gone. Everything above `exec` is the part
        # that broke, and it all runs.
        from PyQt6.QtWidgets import QDialog
        from ..ui.title import opening_briefing
        built = []
        real_exec = QDialog.exec

        def spy(self):
            built.append(self.windowTitle() or "untitled")
            return int(QDialog.DialogCode.Rejected)

        fresh = MainWindow(new_game("briefing-check"))
        QDialog.exec = spy
        try:
            opening_briefing(fresh)
        finally:
            QDialog.exec = real_exec
        assert built, "no briefing dialog was ever built"
        fresh.close()
        fresh.deleteLater()
        app.processEvents()
        return f"briefing built and shown ({built[0]})"

    @check("quitting is a save")
    def _():
        # Trading advances no calendar and the autosave fires on calendar
        # movement, so a shopping run used to be lost on quit.
        from ..core import state as state_mod
        leaving = MainWindow(new_game("quit-save"))
        leaving.dialog = lambda *a, **k: None
        leaving.game.credits = 4242
        leaving.close()
        app.processEvents()
        back = state_mod.load_game()
        assert back is not None and back.credits == 4242, (
            "the quit did not write the chronicle")
        leaving.deleteLater()
        app.processEvents()
        return "credits changed, window closed, chronicle holds the change"

    @check("dismissing an ending does not destroy the chronicle")
    def _():
        # Escape at the ending dialog fell past the "carry" branch into
        # `clear_save()` — the one dialog in the game where "no" erased
        # everything. None is a refusal, never a button.
        from ..core import state as state_mod
        from ..data.lore import VICTORIES
        from ..ui import title as title_mod
        ended = new_game("escape-check")
        ended.save()
        ended.victory = VICTORIES[0][0]
        win.game = ended
        called = []
        kept, title_mod.start_new_chronicle = (
            title_mod.start_new_chronicle, lambda w: called.append(w))
        try:
            assert win.check_ending(), "the ending did not present"
        finally:
            title_mod.start_new_chronicle = kept
        assert not called, "a dismissed ending began a new chronicle"
        assert state_mod.has_save(), "a dismissed ending cleared the save"
        return "Escape at the ending: save intact, nothing begun"

    win.close()
    return True
