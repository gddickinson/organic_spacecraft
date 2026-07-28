"""Manual and options checks.

Two rules, both of them the project's usual one pointed at screens that
normally escape it.

**A manual must not be able to go stale.** A help page that says "thirty-five
hulls" is wrong the day somebody adds one and nothing would notice, so every
countable claim is generated from the table it describes. These checks fail if
a topic names a fact nothing can resolve, or if a resolver breaks.

**An option that changes nothing is a lie.** Every setting the screen offers is
read somewhere in the package; a setting that stops being read fails here
rather than sitting on the screen doing nothing.
"""

from __future__ import annotations

import pathlib

from ..core.state import new_game
from ..data.help import TOPICS, TOPICS_BY_ID
from ..data.screens import KEY_FOR, NAV, NAV_KEYS, SCREENS
from ..sim import manual as manual_sim
from ..sim import options as options_sim
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("every topic opens, and every fact it names resolves")
    def _():
        for seed in ("manual-fresh", "manual-other"):
            game = new_game(seed)
            for topic in TOPICS:
                page = manual_sim.page(game, topic.id)
                assert page, f"{topic.id} has no page"
                assert page["body"], f"{topic.id} says nothing"
                for line in page["facts"]:
                    assert not line.startswith("(no such fact"), (
                        f"{topic.id}: {line}")
                    assert not line.startswith("(could not read"), (
                        f"{topic.id}: {line}")
                for other in topic.see:
                    assert other in TOPICS_BY_ID, (
                        f"{topic.id} points at {other}, which is not a topic")
        counted = sum(len(t.facts) for t in TOPICS)
        return f"{len(TOPICS)} topics, {counted} generated facts, all resolving"

    @check("the manual counts rather than restates")
    def _():
        # The point of the whole arrangement: add an ending and the manual
        # says so without anybody editing prose.
        from ..data.lore import VICTORIES
        game = new_game("manual-count")
        endings = "\n".join(manual_sim.resolve(game, "endings"))
        assert str(len(VICTORIES)) in endings, endings[:120]
        for _vid, name, *_rest in VICTORIES:
            assert name in endings, f"{name} is missing from the manual"

        hulls = "\n".join(manual_sim.resolve(game, "hulls"))
        from ..data.chassis import CHASSIS
        assert str(len(CHASSIS)) in hulls, hulls[:120]

        tree = "\n".join(manual_sim.resolve(game, "tech_tree"))
        from ..data.tech import TECH
        assert str(len(TECH)) in tree, tree[:120]
        return (f"{len(VICTORIES)} endings, {len(CHASSIS)} hulls and "
                f"{len(TECH)} technologies, all counted at read time")

    @check("the manual is about this chronicle, not about the game in general")
    def _():
        rich = new_game("manual-rich")
        rich.credits = 999_999
        poor = new_game("manual-poor")
        assert (manual_sim.resolve(rich, "starting_kit")
                != manual_sim.resolve(poor, "starting_kit"))
        assert "999,999" in "".join(manual_sim.resolve(rich, "starting_kit"))
        # And the reach line is this sector's, not a generic sentence.
        from ..sim import reach as reach_sim
        assert manual_sim.resolve(rich, "reach") == [reach_sim.note(rich)]
        return "the kit, the reach and the powers all read off this game"

    @check("search finds things, and finding nothing is not a crash")
    def _():
        assert len(manual_sim.search("")) == len(TOPICS)
        for word, expect in (("heat", "moving"), ("contraband", "trade"),
                             ("berth", "crew"), ("epoch", "endings")):
            found = {t.id for t in manual_sim.search(word)}
            assert expect in found, (
                f"searching {word!r} did not find {expect}: {sorted(found)}")
        assert manual_sim.search("zzzzznotathing") == []
        return "four searches hit their topic; a miss returns nothing quietly"

    @check("every screen has a key, and no two share one")
    def _():
        # A real defect this replaced: the window derived keys as "1-9 then 0
        # for the rest", so the tenth and eleventh screens both bound 0 and
        # the Aftermath had no key of its own at all.
        keys = [key for _sid, _label, key in SCREENS]
        duplicates = {k for k in keys if keys.count(k) > 1}
        assert not duplicates, f"screens sharing a key: {duplicates}"
        assert all(keys), "a screen with no key"
        assert len(NAV) == len(SCREENS) == len(NAV_KEYS)
        assert set(KEY_FOR) == {sid for sid, _l, _k in SCREENS}
        return f"{len(SCREENS)} screens, {len(set(keys))} distinct keys"

    @check("the rail and the manual are built from the same table")
    def _():
        from ..ui.window import NAV as WINDOW_NAV
        assert list(WINDOW_NAV) == list(NAV), (
            "the window's rail has drifted from data/screens.py")
        game = new_game("manual-keys")
        printed = "\n".join(manual_sim.resolve(game, "keys"))
        for _sid, label, key in SCREENS:
            name = label.split("  ", 1)[-1]
            assert name in printed, f"{name} is not on the Keys page"
            assert key in printed, f"key {key!r} is not on the Keys page"
        return f"{len(SCREENS)} screens on the rail and on the Keys page"

    @check("every option the screen offers actually does something")
    def _():
        # A setting nothing reads is a lie told by a screen. Two ways to be
        # consumed, and each is checked for what it is: most settings are read
        # by name somewhere else in the package, and the speech ones are
        # *forwarded* by `options.apply` into `core/llm.py`, which a textual
        # scan cannot see. The first version of this check only scanned, and
        # reported two perfectly live settings as dead.
        from ..core import llm
        root = pathlib.Path(__file__).resolve().parent.parent
        sources = [p for p in root.rglob("*.py")
                   if p.name != "options.py" and "tests" not in p.parts]
        haystack = "\n".join(p.read_text() for p in sources)

        game = new_game("manual-opt")
        llm.forget()
        unread, by_name, by_effect = [], 0, 0
        for entry in options_sim.summary(game):
            name = entry["name"]
            if f'"{name}"' in haystack:
                by_name += 1
                continue
            # Not named elsewhere: prove it by moving it and watching.
            before = llm.settings()
            changed = {"bool": not entry["value"]}.get(
                entry["kind"], f"probe-{name}")
            options_sim.set_to(game, name, changed)
            if llm.settings() != before:
                by_effect += 1
            else:
                unread.append(name)
            options_sim.set_to(game, name, entry["value"])
        llm.forget()
        assert not unread, (
            f"settings nothing reads — either wire them or take them off the "
            f"screen: {unread}")
        return (f"{len(options_sim.FIELDS)} settings: {by_name} read by name, "
                f"{by_effect} proven by changing them")

    @check("settings hold their bounds, and survive a save")
    def _():
        import os
        import tempfile
        game = new_game("manual-bounds")
        assert options_sim.set_to(game, "autosave_days", 999)["value"] == 30
        assert options_sim.set_to(game, "autosave_days", -5)["value"] == 0
        assert options_sim.set_to(game, "instrument_ms", 1)["value"] == 200
        assert not options_sim.set_to(game, "nonesuch", 1)["ok"]
        assert not options_sim.set_to(game, "instrument_ms", "fast")["ok"]
        assert options_sim.set_to(game, "confirm", False)["value"] is False

        os.environ["HOME"] = tempfile.mkdtemp()
        from ..core import save as save_mod
        from ..core.state import load_game
        options_sim.set_to(game, "instrument_ms", 2000)
        save_mod.write({"game": game})
        back = load_game()
        assert options_sim.get(back, "instrument_ms") == 2000
        assert options_sim.get(back, "confirm") is False
        return "bounds clamped, rubbish refused, and the settings reloaded"

    @check("the menu bar reaches every screen, instrument and setting")
    def _():
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..ui import theme
        from ..ui.monitors import SHAPES
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        win = MainWindow(new_game("menu-bar"))
        win.resize(1200, 800)
        win.show()

        menus = {}
        for entry in win.menuBar().actions():
            sub = entry.menu()
            if sub is not None:
                menus[entry.text().replace("&", "")] = [
                    a.text() for a in sub.actions() if a.text()]
        for wanted in ("Chronicle", "Screens", "Instruments", "Help"):
            assert wanted in menus, sorted(menus)

        # Built from the same tables as the rail and the monitors, so nothing
        # can exist without appearing here.
        for _sid, text, _key in SCREENS:
            name = text.split("  ", 1)[-1]
            assert name in menus["Screens"], f"{name} is not on the menu"
        for _name, (title, _cls, _size) in SHAPES.items():
            assert title in menus["Instruments"], f"{title} is not on the menu"
        assert "Options…" in menus["Chronicle"]
        win.close()
        return (f"{len(menus)} menus · {len(menus['Screens'])} screens · "
                f"{len(SHAPES)} instruments, all reachable")

    @check("every menu action fires without raising")
    def _():
        # Qt swallows what a slot raises, so an action wired to a method that
        # does not exist looks exactly like an action that works. That is not
        # hypothetical — see the next check.
        import sys
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..ui import theme
        from ..ui.monitors import close_all
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        win = MainWindow(new_game("menu-fire"))
        win.resize(1200, 800)
        win.show()
        win.dialog = lambda *a, **k: None
        win.confirm = lambda *a, **k: False       # never actually restart
        win.toast = lambda *a, **k: None

        caught = []
        previous = sys.excepthook
        sys.excepthook = lambda k, v, _t: caught.append(f"{k.__name__}: {v}")
        fired = 0
        try:
            for entry in win.menuBar().actions():
                sub = entry.menu()
                if sub is None:
                    continue
                for action in sub.actions():
                    text = action.text()
                    if not text or text in ("Quit", "Options…"):
                        continue      # one closes the window, one is modal
                    try:
                        action.trigger()
                        app.processEvents()
                    except Exception as err:      # noqa: BLE001 - reported
                        caught.append(f"{text}: {type(err).__name__}: {err}")
                    fired += 1
        finally:
            sys.excepthook = previous
            close_all(win)
            win.close()
        assert not caught, "menu actions that raised:\n      " + \
            "\n      ".join(caught[:6])
        return f"{fired} menu actions fired, none raised"

    @check("saving from the window works, and the aftermath uses it")
    def _():
        # The bug: `win.save()` did not exist, and three call sites used it —
        # carrying on past an ending, answering an aftermath situation, and
        # changing a setting. Every one raised inside a Qt slot, where it is
        # swallowed. The aftermath checks drove `sim/legacy.py` directly and
        # never pressed the button.
        import os
        import sys
        import tempfile
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:              # pragma: no cover
            return f"skipped: {err}"
        from ..core.rng import RNG
        from ..sim import legacy as legacy_sim
        from ..ui import theme
        from ..ui.window import MainWindow

        os.environ["HOME"] = tempfile.mkdtemp()
        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        game = new_game("aftermath-ui")
        win = MainWindow(game)
        win.resize(1200, 800)
        win.show()
        assert hasattr(win, "save"), "the window cannot save"
        win.save()

        legacy_sim.begin(game, "containment")
        for _ in range(24):
            game.advance_days(60)
            if legacy_sim.offer(game):
                break
        assert legacy_sim.offer(game), "no situation arrived to answer"

        caught = []
        previous = sys.excepthook
        sys.excepthook = lambda k, v, _t: caught.append(f"{k.__name__}: {v}")
        try:
            win.go("legacy")
            app.processEvents()
            win.views["legacy"]._answer(0)       # the button's own slot
            app.processEvents()
        finally:
            sys.excepthook = previous
            win.close()
        assert not caught, f"answering raised: {caught[:3]}"
        assert legacy_sim.offer(game) == {}, "the situation stayed open"
        return "the window saves; an aftermath answer goes through it cleanly"

    @check("the speech settings drive the model module, and start off")
    def _():
        from ..core import llm
        llm.forget()
        game = new_game("speech-set")
        assert llm.settings() == {"enabled": None, "provider": "", "model": ""}
        assert not llm.enabled(), "a model was live before anything asked"

        options_sim.set_to(game, "voices", True)
        options_sim.set_to(game, "llm_provider", "ollama")
        options_sim.set_to(game, "llm_model", "qwen2.5")
        asked = llm.settings()
        assert asked["enabled"] is True and asked["provider"] == "ollama"
        assert asked["model"] == "qwen2.5", asked

        # Nothing is running, so the game still writes every line itself.
        assert not options_sim.voices_live(game)
        from ..sim import voice as voice_sim
        said = voice_sim.speak(game, "ship:self", persona="ship",
                               name="Test", kind="ship")
        assert said["source"] == "written", said
        assert said["line"]

        options_sim.set_to(game, "voices", False)
        assert llm.settings()["enabled"] is False
        llm.forget()
        return ("settings reach core/llm.py, and with nothing answering the "
                "game still writes every line")

    @check("asking for a model is not the same as one answering")
    def _():
        # The player's switch turns the *attempt* on. Whether anything is
        # there is a separate fact, and the screen distinguishes them — a
        # toggle that reads "on" beside speech the game is still writing
        # itself would be the worst of both.
        from ..core import llm
        llm.forget()
        game = new_game("manual-voice")
        assert not llm.switched_on(), "on before anybody asked"
        assert "Off." in llm.describe()

        options_sim.set_to(game, "voices", True)
        assert llm.switched_on(), "the switch did not reach core/llm"
        # Nothing is running in a check, so it must report that plainly.
        assert "nothing answered" in llm.describe(), llm.describe()
        assert not options_sim.voices_live(game), (
            "reported a live model with nothing answering")

        from ..sim import voice as voice_sim
        said = voice_sim.speak(game, "port:q", persona="harbourmaster",
                               name="Vell", kind="port")
        assert said["source"] == "written" and said["line"]

        options_sim.set_to(game, "voices", False)
        assert not llm.switched_on()
        llm.forget()
        return ("asked-for and answering are separate, and the screen says "
                "which is missing")
