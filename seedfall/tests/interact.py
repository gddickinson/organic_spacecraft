"""Playing the game the way a player does: by pressing what is on the screen.

Everything else drives `sim/`. `chronicle.py` plays a decade by calling survey
and extract and jump directly, and then paints the screens to look at them —
which is a good check and misses a whole class of defect, because a player
never calls `sim.extract`. They press *Open cut*, and the handler behind that
button flies the ship there first.

That seam is where the last three bugs lived. The clearest: a short transit
advances the clock by a fraction of a day, `advance_days` took it, `game.day`
became a float and the heading bar died formatting it. A six-year chronicle
makes **zero** fractional advances, so nothing in the suite could reach it. A
player hit it in four minutes.

So this presses real, enabled controls on real screens, for a long session,
with the clock running — and reports what it touched. It is deliberately not
random: it only ever presses things a player could press, and it refuses the
handful that end the session rather than continue it.
"""

from __future__ import annotations

import collections

#: Labels never pressed: they abandon the chronicle or close the window, which
#: ends the session rather than testing it.
AVOID = ("quit", "begin again", "abandon", "close", "done", "skip the tutorial")

#: Screens worth spending presses on, in roughly the order a captain uses them.
ROUNDS = ("system", "port", "helm", "ship", "yard", "tech", "empire",
          "diplomacy", "map", "codex", "help")


def _pressable(view, avoid=AVOID) -> list:
    from PyQt6.QtWidgets import QPushButton
    out = []
    for widget in view.findChildren(QPushButton):
        if not widget.isEnabled():
            continue
        label = (widget.text() or "").strip().lower()
        if not label or any(bad in label for bad in avoid):
            continue
        out.append(widget)
    return out


def _cards(view) -> list:
    from ..ui.widgets import Card
    return [c for c in view.findChildren(Card) if c._selectable]


def play(win, app, rounds: int = 3, per_screen: int = 4, rng=None,
         seconds: float = 90.0) -> dict:
    """Press things. Returns what was touched and what the clock did.

    `rng` picks which control when there are several, so a session is varied
    but reproducible. `seconds` is a hard wall-clock budget: a press can put
    the game somewhere expensive — a colony sweep, ninety days of clock — and
    a session with no ceiling is a suite that hangs rather than fails.

    Anything modal is neutralised for the duration. A dialog runs its own
    event loop, so `click()` would not return until somebody answered it, and
    there is nobody there.
    """
    import time

    from PyQt6.QtCore import QEvent, QPointF, Qt
    from PyQt6.QtGui import QMouseEvent
    from PyQt6.QtWidgets import QDialog, QInputDialog

    deadline = time.monotonic() + seconds
    held_exec = QDialog.exec
    held_text = QInputDialog.getText
    # `QDialog.exec` covers the game's own dialogs. `QInputDialog.getText` is a
    # *static* blocking call and does not go through it — the shipyard uses it
    # to ask a new hull's name, and a session that pressed "Lay down" waited
    # there for an answer nobody was going to give. Ten minutes of a suite
    # hanging, from one control.
    QDialog.exec = lambda self, *a, **k: 0
    QInputDialog.getText = staticmethod(lambda *a, **k: ("Test Hull", True))

    pressed = collections.Counter()
    labels: collections.Counter = collections.Counter()
    started = win.game.day
    day_kinds = set()
    seen: set = set()          # (screen, label) already pressed

    def settle(times: int = 3) -> None:
        for _ in range(times):
            app.processEvents()

    def note_day() -> None:
        day_kinds.add(type(win.game.day).__name__)

    for _round in range(rounds):
        for screen in ROUNDS:
            win.go(screen)
            settle()
            note_day()
            view = win.views[win.current]

            for index in range(per_screen):
                buttons = _pressable(view)
                if not buttons:
                    break
                # Prefer something not pressed yet on this screen. Choosing at
                # random left whole panels untouched: the first version never
                # once put the rig on a body, which is exactly the handler the
                # seam bugs live behind — it flies the ship before it mines.
                fresh = [b for b in buttons
                         if (screen, (b.text() or "").strip()) not in seen]
                pool = fresh or buttons
                which = (rng.int(0, len(pool) - 1) if rng and len(pool) > 1
                         else 0)
                button = pool[which]
                seen.add((screen, (button.text() or "").strip()))
                labels[(button.text() or "?").strip()[:34]] += 1
                button.click()
                settle()
                note_day()
                pressed["button"] += 1
                # A press can divert the window — into a battle, a trench, an
                # aftermath question. Follow it rather than fighting it: that
                # is what a player would be looking at.
                if win.current != screen:
                    view = win.views[win.current]
                    screen = win.current
                if (win.game.dead or win.game.victory
                        or time.monotonic() > deadline):
                    break

            # Re-read the cards every time: pressing one rebuilds the screen
            # and frees the rest, so a list gathered once is a list of corpses
            # by the second press. (The driver made that mistake first.)
            for slot in range(2):
                here = _cards(win.views[win.current])
                if slot >= len(here):
                    break
                here[slot].mousePressEvent(QMouseEvent(
                    QEvent.Type.MouseButtonPress, QPointF(4, 4),
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier))
                settle()
                note_day()
                pressed["card"] += 1

            if win.game.dead or win.game.victory or time.monotonic() > deadline:
                break
        if win.game.dead or win.game.victory or time.monotonic() > deadline:
            break

    QDialog.exec = held_exec
    QInputDialog.getText = held_text
    return {"pressed": dict(pressed), "labels": labels,
            "ran_out": time.monotonic() > deadline,
            "days": win.game.day - started, "day_kinds": sorted(day_kinds),
            "dead": win.game.dead, "victory": win.game.victory,
            "ended_on": win.current}
