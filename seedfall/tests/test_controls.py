"""Controls that are not buttons — cards, combos, spinners, fields, the plan.

`test_verbs` drives every `QPushButton` on every screen, and for a long time
that read as complete coverage. It was not. Qt emits a button's `clicked`
safely after the press finishes; a hand-written `mousePressEvent` does not, and
almost every handler in this game rebuilds the screen it lives on.

Two crashes came out of that gap, both from a player rather than from the
suite. Clicking a card aborted the process. Typing one character into the
manual's search field **segfaulted** it — signal 11, not an exception, because
`textChanged` fires mid-keystroke and the rebuild freed the field being typed
into.

So this drives every other kind of control there is: cards, combo boxes, spin
boxes, text entry a character at a time, and the ship plan's drag and wheel.
"""

from __future__ import annotations

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QComboBox, QLineEdit, QSpinBox

from .harness import Suite


def run(suite: Suite, app, window, _stocked, NAV, _Trap) -> None:
    """Driven from `test_verbs`, which owns the offscreen app and fixtures."""
    check = suite.check

    @check("clicking a card does not destroy the game")
    def _():
        """A crash a player hit within a minute of starting.

        Cards are how you select a body, a technology or a hull, and almost
        every handler on one rebuilds the screen it lives on — which unparents
        the old widgets and frees them there and then. `Card.mousePressEvent`
        emitted inline, so the very next statement touched a deleted C++ object
        and aborted the process.

        Nothing in the suite had ever clicked a card. `test_verbs` clicks
        *buttons*, whose signal Qt emits safely after the press completes, so
        every control was covered except the one kind that crashed.
        """
        from ..ui.widgets import Card

        def press(card):
            card.mousePressEvent(QMouseEvent(
                QEvent.Type.MouseButtonPress, QPointF(4, 4),
                Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier))
            for _ in range(3):
                app.processEvents()

        _game, win = window("cards", "map")
        clicked, screens = 0, []
        with _Trap() as trap:
            for screen, *_rest in NAV:
                win.go(screen)
                app.processEvents()
                found = [c for c in win.views[screen].findChildren(Card)
                         if c._selectable]
                if not found:
                    continue
                screens.append(f"{screen}:{len(found)}")
                for index in range(min(5, len(found))):
                    # Re-read after every click: the screen rebuilds itself and
                    # the old cards are gone, which is the whole point.
                    live = [c for c in win.views[screen].findChildren(Card)
                            if c._selectable]
                    if index >= len(live):
                        break
                    press(live[index])
                    clicked += 1
        win.close()
        assert not trap.caught, (
            "clicking a card raised:\n      "
            + "\n      ".join(trap.caught[:5]))
        assert clicked >= 8, f"only {clicked} cards were clickable anywhere"
        return f"{clicked} cards clicked across {', '.join(screens)}"

    @check("every other kind of control works too, not only buttons")
    def _():
        """Buttons were covered; nothing else was.

        The card crash a player hit lived behind full button coverage because
        `QPushButton` emits safely after the press completes and a hand-rolled
        `mousePressEvent` does not. Auditing the rest turned up 14 line edits,
        13 spin boxes and 5 combo boxes that nothing had ever touched — and
        the first one driven, the manual's search field, **segfaulted the
        process** on the first keystroke.
        """

        game = _stocked("controls")
        game.credits = 500_000
        for key in ("alloy", "silicon", "biomass", "phosphate", "ore"):
            game.stores[key] = 400
        _g, win = window("controls", "map", state=lambda _s: game)

        counts = {"combo": 0, "spin": 0, "typed": 0}
        with _Trap() as trap:
            for screen, *_rest in NAV:
                win.go(screen)
                app.processEvents()
                view = win.views[screen]

                for box in list(view.findChildren(QComboBox)):
                    for index in range(min(3, box.count())):
                        box.setCurrentIndex(index)
                        for _ in range(3):
                            app.processEvents()
                        counts["combo"] += 1

                for spin in list(view.findChildren(QSpinBox)):
                    for value in (spin.maximum(), spin.minimum()):
                        spin.setValue(value)
                        for _ in range(2):
                            app.processEvents()
                        counts["spin"] += 1

                # Typed a character at a time into whatever holds focus, which
                # is the only way to notice that a rebuild threw the field away
                # mid-word.
                edits = view.findChildren(QLineEdit)
                if edits:
                    edits[0].setFocus()
                    app.processEvents()
                    for letter in "berth":
                        target = win.focusWidget() or edits[0]
                        QApplication.sendEvent(target, QKeyEvent(
                            QEvent.Type.KeyPress, Qt.Key.Key_A,
                            Qt.KeyboardModifier.NoModifier, letter))
                        for _ in range(3):
                            app.processEvents()
                        counts["typed"] += 1
            # And the one widget with hand-written drag, wheel and hit-test.
            from ..ui.plans_panel import ShipPlan

            win.views["ship"].tab = "plans"
            win.go("ship")
            for _ in range(3):
                app.processEvents()
            for plan in win.views["ship"].findChildren(ShipPlan):
                def at(kind, x, y):
                    return QMouseEvent(kind, QPointF(x, y),
                                       Qt.MouseButton.LeftButton,
                                       Qt.MouseButton.LeftButton,
                                       Qt.KeyboardModifier.NoModifier)
                plan.mousePressEvent(at(QEvent.Type.MouseButtonPress, 200, 200))
                for step in range(0, 60, 12):
                    plan.mouseMoveEvent(
                        at(QEvent.Type.MouseMove, 200 + step, 200 + step // 2))
                plan.mouseReleaseEvent(
                    at(QEvent.Type.MouseButtonRelease, 260, 230))
                plan.wheelEvent(QWheelEvent(
                    QPointF(200, 200), QPointF(200, 200), QPoint(0, 0),
                    QPoint(0, 120), Qt.MouseButton.NoButton,
                    Qt.KeyboardModifier.NoModifier,
                    Qt.ScrollPhase.NoScrollPhase, False))
                for _ in range(2):
                    app.processEvents()
                assert not plan.grab().isNull()
                counts["plan"] = counts.get("plan", 0) + 1
        win.close()
        assert not trap.caught, (
            "a control raised:\n      " + "\n      ".join(trap.caught[:5]))
        assert counts["combo"] and counts["spin"] and counts["typed"], counts
        assert counts.get("plan"), "the ship plan was never driven"
        return (f"{counts['combo']} combo selections · {counts['spin']} spin "
                f"values · {counts['typed']} keystrokes · "
                f"{counts['plan']} plan drag/wheel, all clean")

    @check("typing a whole word into the manual actually searches")
    def _():
        # Not only "does not crash": the field has to survive its own rebuild
        # well enough to accept a second character.
        from ..sim import manual as manual_sim

        _game, win = window("search", "help")
        view = win.views["help"]
        view.tab = "manual"
        win.go("help")
        app.processEvents()
        view.findChildren(QLineEdit)[0].setFocus()
        app.processEvents()

        with _Trap() as trap:
            for letter in "berth":
                target = win.focusWidget()
                assert target is not None, "focus was lost mid-word"
                QApplication.sendEvent(target, QKeyEvent(
                    QEvent.Type.KeyPress, Qt.Key.Key_A,
                    Qt.KeyboardModifier.NoModifier, letter))
                for _ in range(4):
                    app.processEvents()
        box = view.findChildren(QLineEdit)[0]
        win.close()
        assert not trap.caught, trap.caught[:3]
        assert view.query == "berth", f"the field kept {view.query!r}"
        assert box.text() == "berth", f"the box shows {box.text()!r}"
        found = {t.id for t in manual_sim.search("berth")}
        assert "crew" in found, found
        return f"typed 'berth' one key at a time; it found {sorted(found)}"

