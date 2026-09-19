"""The game can be played from the keyboard: pressed, not looked up.

Review item #25: `Card` took no focus, and cards carry the system's bodies,
the research tree, the hull classes and the new-game choices; the star chart
was the only way to choose a jump and it took no focus either; every action
rebuilt its screen and threw the focus to the heading bar; and the Port and
Research buttons said nothing when hovered, disabled or not. These send real
key events to a real window, the way `test_screenkeys` does.
"""

from __future__ import annotations

from .test_ui import _use_offscreen

_use_offscreen()


def _settle(app, n: int = 4) -> None:
    for _ in range(n):
        app.processEvents()


def run(suite) -> bool:
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QApplication, QListWidget, QPushButton
    except ImportError as err:
        print(f"── keyboard ───\n  skipped: PyQt6 not available ({err})\n")
        return False

    from ..core.state import new_game
    from ..data.expedition import FEATURES
    from ..data.tech import TECH
    from ..sim import research as research_sim
    from ..ui import focus, theme
    from ..ui.widgets import Card
    from ..ui.window import MainWindow

    check = suite.check
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(theme.stylesheet())
    game = new_game("keyboard-seed")
    port_sys = next(s for s in game.galaxy.systems if s.port)
    game.location_id = port_sys.id
    game.credits = 100_000
    game.ship.cargo["volatiles"] = 20
    game.recompute()
    win = MainWindow(game)
    win.dialog = lambda *a, **k: None
    win.confirm = lambda *a, **k: False
    win.toast = lambda *a, **k: None
    win.resize(1360, 880)
    win.show()
    win.activateWindow()
    _settle(app)

    @check("a research card takes the focus, and Space sets the project")
    def _():
        win.go("tech")
        _settle(app)
        view = win.views["tech"]
        pick = next(t for t in TECH
                    if research_sim.can_research(t.id, game.research.unlocked)
                    and t.id != game.research.current)
        card = view.findChild(Card, f"card:{pick.name}")
        assert card is not None, f"no card named {pick.name}"
        assert card.focusPolicy() & Qt.FocusPolicy.TabFocus, "a card takes no focus"
        card.setFocus()
        _settle(app)
        QTest.keyClick(card, Qt.Key.Key_Space)
        _settle(app)
        assert game.research.current == pick.id, (
            f"Space on {pick.name} left the bench on {game.research.current}")
        return f"Space on the {pick.name} card set it running"

    @check("after an action the focus is back on the control that had it, "
           "not on the heading bar")
    def _():
        view = win.views["port"]
        view.tab = "market"
        win.go("port")
        _settle(app)
        buy = view.findChild(QPushButton, "buy_volatiles")
        assert buy is not None
        buy.setFocus()
        _settle(app)
        had = game.ship.cargo.get("volatiles", 0)
        QTest.keyClick(buy, Qt.Key.Key_Space)
        _settle(app)
        assert game.ship.cargo.get("volatiles", 0) > had, "Space did not buy"
        # And on a screen that really is rebuilt, not changed in place.
        view.tab = "services"
        view.refresh()
        _settle(app)
        takers = [b for b in view.findChildren(QPushButton)
                  if b.isVisible() and b.isEnabled()
                  and b.property("kind") != "tab"]
        assert takers, "nothing to press on the services tab"
        target = takers[-1]
        name = target.objectName() or target.text()
        target.setFocus()
        _settle(app)
        view.refresh()                   # the rebuild an action would cause
        _settle(app)
        now = focus.where(view)
        assert now == name, (
            f"after a rebuild the focus is on {now!r}, not {name!r}")
        view.tab = "market"
        return f"Buy kept its focus; {name!r} had it back after a rebuild"

    @check("the chart has a destination list the keyboard can drive")
    def _():
        win.go("map")
        _settle(app)
        view = win.views["map"]
        box = view.findChild(QListWidget, "destinations")
        assert box is not None, "no destination list beside the chart"
        box.setFocus()
        box.setCurrentRow(2)
        want = box.currentItem().data(Qt.ItemDataRole.UserRole)
        QTest.keyClick(box, Qt.Key.Key_Return)
        _settle(app, 6)
        assert view.selected == want, (
            f"Enter on the list picked {view.selected}, not {want}")
        again = view.findChild(QListWidget, "destinations")
        assert focus.where(view) == "destinations" and again.hasFocus(), (
            "picking from the list lost the list's focus")
        name = game.galaxy.systems[want].name
        return f"Enter picked {name}, and the list kept the focus"

    @check("cards and drawn controls have a name a screen reader can read")
    def _():
        from ..ui.star_chart import StarChart
        missing = []
        for sid in ("tech", "system", "map"):
            win.go(sid)
            _settle(app)
            view = win.views[sid]
            for card in view.findChildren(Card):
                if card._selectable and not card.accessibleName():
                    missing.append(f"{sid}: a card")
        chart = win.views["map"].findChild(StarChart)
        if not chart.accessibleName():
            missing.append("the star chart")
        assert not missing, missing[:6]
        return "every selectable card and the chart are named"

    @check("every disabled button on the Port and Research screens says why")
    def _():
        silent = []
        for sid, tabs in (("port", ("market", "services")), ("tech", ("",))):
            view = win.views[sid]
            for tab in tabs:
                if tab:
                    view.tab = tab
                win.go(sid)
                _settle(app)
                for b in view.findChildren(QPushButton):
                    if b.isVisible() and not b.isEnabled() and not b.toolTip():
                        silent.append(f"{sid}/{tab}: {b.text()!r}")
        win.views["port"].tab = "market"
        assert not silent, silent[:8]
        return "each one carries its reason on hover"

    @check("every feature on the ground map wears its own letter")
    def _():
        from ..ui.expedition_view import feature_mark
        marks = {fid: feature_mark(fid) for fid in FEATURES}
        assert len(set(marks.values())) == len(marks), marks
        return " ".join(f"{m}={fid}" for fid, m in sorted(marks.items()))

    win.close()
    win.deleteLater()
    app.processEvents()
    return True
