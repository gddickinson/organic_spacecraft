"""The guard `sim/options.py` has been promising since it was written.

Its docstring opens with the rule — **an option that changes nothing is a lie** —
and then says: *"Every field below is read somewhere, and `test_options` fails if
one stops being."* There was no `test_options`. The module named a guard that did
not exist, which is the same class of untruth it was written to prevent, one level
up: a claim about the code rather than a claim about the game.

So this is that guard, and it asks the strong form of the question. "Is the name
mentioned somewhere" is cheap and nearly worthless — a setting can be read into a
variable that nothing consumes, which is the defect this project has found more
often than any other. Each option here is **turned on and off, and something the
player would notice has to differ**:

- `confirm` — the window stops asking;
- `hints` — a panel's explanation disappears;
- `instrument_ms` — an open instrument's timer follows it;
- `autosave_days` — the chronicle is written on the cadence asked for;
- `voices`, `llm_provider`, `llm_model` — reach `core/llm.py`, which is outside
  the `Game` and has to be pushed to;
- `tutorial` — the title screen offers it, or does not.

Plus the structural pair: every field is on the screen and every screen row is a
field, and the bounds are enforced in the sim where a second UI cannot disagree
with them.
"""

from __future__ import annotations

import dataclasses

from ..core.state import new_game
from ..sim import options as options_sim
from .harness import Suite


#: Held for the life of the suite. A `MainWindow` whose `QApplication` has been
#: collected takes its C++ object with it, and the next Qt call aborts the whole
#: process with "Must construct a QApplication before a QWidget" — which is what
#: the first draft of this file did.
_ALIVE: list = []


def _window(seed: str = "opt"):
    """A real MainWindow, offscreen, with dialogs stubbed."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication

    from ..ui import theme
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    assert app is not None
    app.setStyleSheet(theme.stylesheet())
    game = new_game(seed)
    win = MainWindow(game)
    win.resize(1200, 800)
    # `dialog` is stubbed because `QDialog.exec()` blocks. `confirm` is *not*:
    # it is the thing one of these checks is about, and the first draft stubbed
    # it here and then tested the stub.
    win.dialog = lambda *a, **k: None
    _ALIVE.append((app, game, win))
    return game, win


def _hints(game, win, view):
    options_sim.set_to(game, "hints", True)
    win.apply_options()
    assert view.hint("This is how the game explains itself.") is not None
    options_sim.set_to(game, "hints", False)
    win.apply_options()
    assert view.hint("This is how the game explains itself.") is None, (
        "a hint was drawn with hints turned off")

    # And it reaches a real screen rather than only the helper. Counted in
    # labels, because that is what a hint *is* once drawn.
    from PyQt6.QtWidgets import QLabel
    counts = {}
    for setting in (True, False):
        options_sim.set_to(game, "hints", setting)
        win.apply_options()          # what the options page calls
        win.go("port")
        win.views["port"].grab()
        # Not hidden, because a withheld note *is* a hidden label — see
        # `widgets.note`, which hides rather than returning None so that the
        # fifteen places adding one straight to a layout keep working.
        counts[setting] = len([lb for lb
                               in win.views["port"].findChildren(QLabel)
                               if not lb.isHidden()])
    assert counts[False] < counts[True], (
        f"the port screen drew {counts[True]} notes with hints on and "
        f"{counts[False]} with them off")
    return (f"the helper is silent with hints off, and the port screen "
            f"goes from {counts[True]} labels to {counts[False]}")


def run(suite: Suite) -> None:
    check = suite.check

    @check("every setting is on the screen, and every screen row is a setting")
    def _():
        fields = {f.name for f in dataclasses.fields(options_sim.Options)}
        rows = {row[0] for row in options_sim.FIELDS}
        assert fields == rows, (
            f"declared but not offered: {sorted(fields - rows)}; "
            f"offered but not declared: {sorted(rows - fields)}")
        # And `summary` — what the screen actually draws — carries every one,
        # with the sentence that says what it does.
        game = new_game("opt-rows")
        told = options_sim.summary(game)
        assert {row["name"] for row in told} == fields
        for row in told:
            assert row["label"] and row["doc"], row
            assert len(row["doc"]) > 40, (
                f"{row['name']} is described in {len(row['doc'])} characters; "
                "the options page is where the game explains itself")
            assert row["kind"] in ("bool", "days", "ms", "choice", "text"), row
        return f"{len(fields)} settings, every one offered and described"

    @check("the bounds live in the sim, and a bad value cannot get in")
    def _():
        game = new_game("opt-bounds")
        # Out of range clamps rather than refusing: a slider that snaps back is
        # kinder than one that errors.
        assert options_sim.set_to(game, "autosave_days", 999)["value"] == 30
        assert options_sim.set_to(game, "autosave_days", -5)["value"] == 0
        assert options_sim.set_to(game, "instrument_ms", 1)["value"] == 200
        assert options_sim.set_to(game, "instrument_ms", 99999)["value"] == 5000
        # Types are coerced, not trusted.
        assert options_sim.set_to(game, "confirm", "")["value"] is False
        assert options_sim.set_to(game, "llm_model", "  llama3.2 ")["value"] \
            == "llama3.2"
        # And the two ways in cannot disagree.
        options_sim.set_to(game, "autosave_days", 7)
        assert options_sim.get(game, "autosave_days") == 7
        assert options_sim.held(game).autosave_days == 7

        bad = options_sim.set_to(game, "instrument_ms", "soon")
        assert not bad["ok"] and "number" in bad["why"], bad
        gone = options_sim.set_to(game, "warp_factor", 9)
        assert not gone["ok"] and "No such setting" in gone["why"], gone
        return "clamped, coerced, and two unknown values refused"

    @check("turning confirmation off stops the window asking")
    def _():
        game, win = _window("opt-confirm")
        asked = []
        win.dialog = lambda *a, **k: (asked.append(a), True)[1]

        options_sim.set_to(game, "confirm", True)
        assert win.confirm("Jettison", "Ten tonnes of ore.") is True
        assert len(asked) == 1, "the dialog was skipped while confirm was on"

        options_sim.set_to(game, "confirm", False)
        assert win.confirm("Jettison", "Ten tonnes of ore.") is True
        assert len(asked) == 1, (
            "the window asked anyway with confirmation turned off — the "
            "setting is a lie")
        return "asked once with it on, not at all with it off"

    @check("turning hints off takes the explanations away")
    def _():
        # **Restored at the end, in a `finally`.** `widgets.HINTS` is module
        # state for the life of the process (see `widgets.note`), so a check that
        # left it off would silently strip the explanations from every suite that
        # runs after this one — and any check asserting a note's text would fail
        # somewhere else entirely.
        game, win = _window("opt-hints")
        view = next(iter(win.views.values()))
        try:
            return _hints(game, win, view)
        finally:
            options_sim.set_to(game, "hints", True)
            win.apply_options()

    @check("an instrument's refresh follows the setting")
    def _():
        game, win = _window("opt-pace")
        from ..ui import monitors as monitor_mod

        options_sim.set_to(game, "instrument_ms", 400)
        kinds = list(monitor_mod.SHAPES)
        assert kinds, "there are no instruments to open"
        monitor_mod.toggle(win, kinds[0])
        held = list(win.monitors.values())
        assert held, "no instrument window opened"
        assert held[0].timer.interval() == 400, (
            f"an instrument opened at {held[0].timer.interval()} ms with the "
            "setting at 400")

        # And changing it moves the ones already open, which is the part a
        # player notices: `apply_options` is what the options page calls.
        options_sim.set_to(game, "instrument_ms", 1500)
        win.apply_options()
        assert held[0].timer.interval() == 1500, held[0].timer.interval()
        return "an open instrument moved from 400 ms to 1,500 when told to"

    @check("the chronicle is written on the cadence asked for")
    def _():
        game, win = _window("opt-save")
        wrote = []
        game.save = lambda *a, **k: wrote.append(game.day)

        options_sim.set_to(game, "autosave_days", 0)
        win._saved_day = game.day
        game.advance_days(1)
        win.refresh()
        assert wrote, "at zero days the calendar moving did not write a save"

        wrote.clear()
        options_sim.set_to(game, "autosave_days", 20)
        win._saved_day = game.day
        for _ in range(3):
            game.advance_days(5)
            win.refresh()
        assert not wrote, (
            f"fifteen days written {len(wrote)} time(s) with a twenty-day "
            "cadence set")
        game.advance_days(6)
        win.refresh()
        assert wrote, "twenty-one days passed and nothing was written"
        return "wrote at once at zero, and not until day 21 at twenty"

    @check("the speech settings reach the module that holds them")
    def _():
        # `core/llm.py` keeps its own state so that it stays a `core` module and
        # knows nothing about a `Game`, so these three are the one group that has
        # to be *pushed* — `options.apply` does it. A setting that only ever sat
        # on the dataclass would look read and do nothing.
        #
        # **Not asserted through `llm.enabled()`**, which asks whether a provider
        # is actually answering: on a machine with no model running it is False
        # however the switch is set, and the first draft of this check read that
        # as "the switch was never passed on". What is being checked is the
        # *push*, so the push is what is watched.
        from ..core import llm

        game = new_game("opt-voice")
        seen = []
        real = llm.configure
        try:
            llm.configure = lambda **kw: (seen.append(kw), real(**kw))[1]
            options_sim.set_to(game, "llm_provider", "ollama")
            options_sim.set_to(game, "llm_model", "llama3.2")
            options_sim.set_to(game, "voices", True)
        finally:
            llm.configure = real
        assert len(seen) == 3, (
            f"three speech settings changed and `core/llm` was told {len(seen)} "
            "time(s)")
        assert seen[-1] == {"enabled": True, "provider_id": "ollama",
                            "model": "llama3.2"}, seen[-1]

        # And a setting that is *not* a speech setting must not push: `apply`
        # resets the provider probe, and doing that on every keystroke would be
        # waste with a side effect.
        seen.clear()
        try:
            llm.configure = lambda **kw: (seen.append(kw), real(**kw))[1]
            options_sim.set_to(game, "hints", False)
            options_sim.set_to(game, "autosave_days", 3)
        finally:
            llm.configure = real
        assert not seen, f"changing hints pushed the speech settings: {seen}"

        # Necessary and not sufficient, which is what the screen has to say: the
        # switch on and nothing answering is not live speech.
        options_sim.set_to(game, "voices", False)
        real(enabled=False, provider_id="", model="")
        assert not options_sim.voices_live(game)
        return "three pushes for three speech settings, none for the others"

    @check("the tutorial offer is the setting, and settings survive a reload")
    def _():
        from ..ui import title as title_mod

        game, win = _window("opt-tutorial")
        asked = []
        win.confirm = lambda *a, **k: (asked.append(a), False)[1]

        options_sim.set_to(game, "tutorial", False)
        title_mod.offer_tutorial(win)
        assert not asked, "the tutorial was offered with the setting off"
        options_sim.set_to(game, "tutorial", True)
        title_mod.offer_tutorial(win)
        assert asked, "the tutorial was not offered with the setting on"

        # And a chronicle carries its own preferences, which is the whole reason
        # they live on the Game rather than in a config file.
        options_sim.set_to(game, "autosave_days", 11)
        options_sim.set_to(game, "hints", False)
        options_sim.set_to(game, "llm_model", "some-model")
        from ..core import save as save_mod
        blob = save_mod.encode(game)
        back = save_mod.decode(blob)
        assert options_sim.get(back, "autosave_days") == 11
        assert options_sim.get(back, "hints") is False
        assert options_sim.get(back, "llm_model") == "some-model"
        assert options_sim.get(back, "tutorial") is True
        return "offered only with the switch on; a reload keeps all of it"
