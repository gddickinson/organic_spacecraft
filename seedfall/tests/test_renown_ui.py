"""Renown on the screens: the Voyage tab, the counsel card and its "take me
there", the chip, the memoir on the Aftermath and the Hall on the title.

Qt checks, offscreen, through `qtkit.main_window` (dialogs stubbed, the save
redirected before the window exists).
"""

from __future__ import annotations

import copy

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import counsel, renown
from . import careful_captain as cc
from . import qtkit
from . import renown_kit as kit
from .harness import Suite

_GAME: dict = {}


def _played():
    """A careful career two years in, played once per process."""
    if "g" not in _GAME:
        g = new_game("renown-ui")
        rng = RNG("renown-ui")
        plan: dict = {}
        renown.follow(g, "genesis")
        while g.day < 700 and not g.dead:
            day = g.day
            cc.turn(g, rng, plan)
            if g.day == day:
                g.advance_days(1)
        _GAME["g"] = g
    return copy.deepcopy(_GAME["g"])


def _texts(widget) -> str:
    from PyQt6.QtWidgets import QLabel, QPushButton
    return " ".join([w.text() for w in widget.findChildren(QLabel)]
                    + [w.text() for w in widget.findChildren(QPushButton)])


def _settle(app) -> None:
    for _ in range(4):
        app.processEvents()


def run(suite: Suite) -> bool:
    """An optional (Qt) suite: True says it ran (`tests/runner._run_here`)."""
    check = suite.check

    @check("the Voyage draws the rank, ten ladders and what is next")
    def _():
        app = qtkit.app()
        g = _played()
        win = qtkit.main_window(g, (1040, 680))
        win.show()
        view = win.views["empire"]
        view.tab = "voyage"
        win.go("empire")
        _settle(app)
        text = _texts(view)
        held = renown.rank(g)
        assert held["name"] in text and "The ten endings" in text
        for name in ("Containment", "Genesis", "Lineage", "The Cartel"):
            assert name in text, f"no {name} ladder"
        assert text.count("Next:") >= 8, "the ladders do not say what is next"
        assert view.horizontalScrollBar().maximum() == 0, (
            "the Voyage is wider than a 1,040 px window")
        from PyQt6.QtWidgets import QPushButton
        follow = next(b for b in view.findChildren(QPushButton)
                      if b.objectName() == "follow:lineage")
        follow.click()
        _settle(app)
        assert renown.focus(g) == "lineage", "Follow did not set the road"
        win.close()
        return (f"{held['name']} at {held['score']}; "
                f"{text.count('Next:')} ladders say what is next at 1040 px")

    @check("take me there opens the move's screen, tab and star")
    def _():
        from ..ui import counsel_card
        app = qtkit.app()
        games = kit.states(20)
        assert games
        opened = 0
        for game in games:
            moves = counsel.advise(game)
            if not moves:
                continue
            win = qtkit.main_window(game, (1360, 880))
            for move in moves:
                screen = counsel_card.take(win, move)
                _settle(app)
                if win.current != move["screen"]:
                    # Only a question on the bridge may divert it, and the
                    # window says so (`window.go`).
                    assert win.current in ("envoy", "demand", "legacy",
                                           "dig", "ground"), (
                        f"{move['id']} opened {win.current}, not {screen}")
                    continue
                if move["tab"]:
                    view = win.views[move["screen"]]
                    tab = (getattr(view, "hunts_tab", "")
                           if move["screen"] == "law" else view.tab)
                    assert tab == move["tab"], (move["id"], tab)
                if move["system"] is not None and move["screen"] == "map":
                    assert win.views["map"].selected == move["system"]
                opened += 1
            win.close()
        assert opened >= 30, f"only {opened} moves taken"
        return f"{opened} moves taken to their screen, tab and star"

    @check("the card dismisses for a month, and the menu brings it back")
    def _():
        from ..ui import counsel_card
        app = qtkit.app()
        g = _played()
        win = qtkit.main_window(g, (1360, 880))
        win.go("map")
        _settle(app)
        from PyQt6.QtWidgets import QPushButton
        buttons = [b for b in win.views["map"].findChildren(QPushButton)
                   if b.objectName().startswith("counsel:")]
        assert buttons, "no counsel on the chart"
        renown.dismiss_counsel(g)
        win.refresh()
        _settle(app)
        assert not [b for b in win.views["map"].findChildren(QPushButton)
                    if b.objectName().startswith("counsel:")]
        assert renown.counsel_quiet(g)
        counsel_card.recall(win)
        _settle(app)
        assert not renown.counsel_quiet(g) and win.current == "map"
        assert [b for b in win.views["map"].findChildren(QPushButton)
                if b.objectName().startswith("counsel:")]
        win.close()
        return f"{len(buttons)} rows; quiet, then back from the menu"

    @check("a fresh milestone lights the chip; the Voyage puts it out")
    def _():
        app = qtkit.app()
        g = new_game("renown-chip")
        win = qtkit.main_window(g, (1040, 680))
        win.show()
        chip = win.renown_chip
        assert not chip.isVisible()
        from . import renown_kit
        with renown_kit.facts({"surveyed": 1, "visited": 2}):
            renown.check(g)
        win.refresh()
        _settle(app)
        assert chip.isVisible() and "+20" in chip.text(), chip.text()
        # Visible is not readable: shown late, it was once squeezed into the
        # speaker's 42 px — an empty box, the speaker pushed off the edge.
        assert chip.width() >= chip.sizeHint().width(), (
            f"chip {chip.width()} px wide, wants {chip.sizeHint().width()}")
        speaker = win.sound_btn
        right = speaker.mapTo(win, speaker.rect().topRight()).x()
        assert right < win.width(), f"speaker ends at {right} of {win.width()}"
        chip.click()
        _settle(app)
        assert win.current == "empire" and win.views["empire"].tab == "voyage"
        assert not chip.isVisible() and not renown.state(g).fresh
        win.close()
        return "lit at +20, out once the Voyage was opened"

    @check("the memoir is on the Aftermath; the Hall is on the title")
    def _():
        from ..ui.title import TitleDialog
        app = qtkit.app()
        with kit.hall_folder():
            g = _played()
            g.die("Lost under the ice.")
            win = qtkit.main_window(g, (1040, 680))
            win.go("legacy")
            _settle(app)
            text = _texts(win.views["legacy"])
            assert "The memoir" in text and "Lost under the ice" in text
            assert renown.rank(g)["name"] in text
            win.close()
            dlg = TitleDialog(None)
            dlg.show()
            _settle(app)
            title = _texts(dlg)
            assert "Hall of Captains · 1 career" in title, title[:300]
            assert g.ship.name in title
            shown = {}
            dlg.dialog = lambda heading, widgets, *a, **k: shown.update(
                heading=heading, text=" ".join(_texts(w) for w in widgets))
            from PyQt6.QtWidgets import QPushButton
            opener = next(b for b in dlg.findChildren(QPushButton)
                          if b.objectName() == "hall_open")
            opener.click()
            _settle(app)
            assert shown.get("heading") == "Hall of Captains"
            assert "Lost under the ice" in shown["text"]
            assert dlg.height() <= 720, dlg.height()
            dlg.close()
        return f"memoir drawn; the title lists the Hall at {dlg.height()} px"

    return True
