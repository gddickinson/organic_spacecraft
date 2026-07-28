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
        # The rule: a setting nothing reads is a lie told by a screen. Read
        # the package and require each one to appear somewhere outside the
        # module that defines it.
        root = pathlib.Path(__file__).resolve().parent.parent
        sources = [p for p in root.rglob("*.py")
                   if p.name not in ("options.py",)
                   and "tests" not in p.parts]
        haystack = "\n".join(p.read_text() for p in sources)
        unread = []
        for entry in options_sim.summary(new_game("manual-opt")):
            if f'"{entry["name"]}"' not in haystack:
                unread.append(entry["name"])
        assert not unread, (
            f"settings nothing reads — either wire them or take them off the "
            f"screen: {unread}")
        return (f"{len(options_sim.FIELDS)} settings, every one read outside "
                f"options.py")

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

    @check("model speech needs both switches, and says so when it has one")
    def _():
        from ..core import llm
        game = new_game("manual-voice")
        options_sim.set_to(game, "voices", True)
        llm.reset()
        assert not options_sim.voices_live(game), (
            "the player's switch alone turned a model on")
        assert "Off." in llm.describe()
        options_sim.set_to(game, "voices", False)
        assert not options_sim.voices_live(game)
        return ("the player's switch and the machine's are both required, and "
                "the screen reports which is missing")
