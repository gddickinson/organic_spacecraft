"""The title screen: the premise, a seed box, and the way back in."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QVBoxLayout,
                             QWidget)

from ..core import state as state_mod
from ..data.chassis import CHASSIS_BY_ID
from ..data.lore import INTRO, SUBTITLE, TAGLINE, TITLE
from . import theme
from .widgets import button, label, note, spacer


class TitleDialog(QDialog):
    """Returns a :class:`Game` in :attr:`game`, or ``None`` if dismissed."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.game = None
        self.setWindowTitle(f"{TITLE} — {SUBTITLE}")
        self.setMinimumWidth(720)

        v = QVBoxLayout(self)
        v.setContentsMargins(46, 34, 46, 34)
        v.setSpacing(9)

        kicker = label("GESTALT Programme · Fleet Chronicle", "label")
        kicker.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(kicker)

        word = label(TITLE)
        word.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        word.setStyleSheet(
            f"font-size: 62px; font-weight: 600; letter-spacing: 12px;"
            f"color: {theme.tint('chloro')};")
        v.addWidget(word)

        tag = label(TAGLINE, "sub")
        tag.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(tag)
        v.addWidget(spacer(14))

        for para in INTRO:
            v.addWidget(label(para, "", wrap=True))
        v.addWidget(spacer(10))

        seed_row = QWidget()
        h = QHBoxLayout(seed_row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        h.addWidget(label("Sector seed", "label"))
        self.seed_box = QLineEdit()
        self.seed_box.setPlaceholderText("leave blank for a new sky")
        self.seed_box.setFixedWidth(260)
        h.addWidget(self.seed_box)
        h.addStretch(1)
        v.addWidget(seed_row)
        v.addWidget(spacer(6))

        actions = QWidget()
        ah = QHBoxLayout(actions)
        ah.setContentsMargins(0, 0, 0, 0)
        ah.addStretch(1)
        ah.addWidget(button("Germinate a new chronicle", self._new, kind="primary"))
        ah.addWidget(button("Choose your commission", self._compose, kind="flat"))
        if state_mod.has_save():
            ah.addWidget(button("Resume", self._resume, kind="flat"))
        ah.addStretch(1)
        v.addWidget(actions)

        foot = note("A concept, not a build spec. Every organ, material and number "
                    "in this game is drawn from the GESTALT design documents in "
                    "this repository.")
        foot.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(spacer(10))
        v.addWidget(foot)

    def _new(self) -> None:
        seed = self.seed_box.text().strip() or None
        state_mod.clear_save()
        self.game = state_mod.new_game(seed)
        self.accept()

    def _compose(self) -> None:
        """The long way in: pick stock, origin, hull, crew and posting."""
        from .beginning_view import BeginningDialog
        seed = self.seed_box.text().strip()
        dlg = BeginningDialog(seed, self)
        dlg.exec()
        if dlg.choices is None:
            return
        state_mod.clear_save()
        self.game = state_mod.new_game(seed or None, choices=dlg.choices)
        self.accept()

    def _resume(self) -> None:
        game = state_mod.load_game()
        if game is None:
            self.seed_box.setPlaceholderText("that save could not be read")
            return
        self.game = game
        self.accept()


def ask_for_game(parent=None):
    """Show the title screen. Returns a Game, or None if the player closed it."""
    dlg = TitleDialog(parent)
    dlg.exec()
    return dlg.game


def start_new_chronicle(win) -> None:
    """Called after an ending: get a fresh game and reset the window in place."""
    game = ask_for_game(win)
    if game is None:
        win.close()
        return
    win.game = game
    win.battle = None
    win.go("map")


def offer_tutorial(win) -> None:
    """Ask once, when a chronicle opens. Skippable, and restartable from Help."""
    from ..sim import options as options_sim
    from ..sim import tutorial as tutorial_sim
    game = win.game
    if tutorial_sim.held(game) is not None:
        return                      # already offered, or already running
    if not options_sim.get(game, "tutorial"):
        return
    take = win.confirm(
        "A short walk through",
        "Eight things to try, one at a time, along the top of the screen. It "
        "watches what you actually do rather than what you click, it never "
        "blocks anything, and you can stop it whenever you like.",
        yes="Walk me through it", no="I will find my own way")
    if take:
        tutorial_sim.begin(game)
    else:
        tutorial_sim.skip(game)
    win.save()
    win.refresh()


def opening_briefing(win) -> None:
    g = win.game
    win.dialog(
        "Standing orders",
        [f"You have the {g.ship.name}, a {CHASSIS_BY_ID[g.ship.chassis].name}-class "
         f"hull out of {g.system.name}, {len(g.officers)} officers, a signing key "
         f"and {round(g.credits):,} credits.",
         "Nobody has told you what to do about the Bloom, because nobody knows. "
         "Survey what is out there and sell the data. Dig phosphate and trade it. "
         "Grow colonies, or buy a Concordat battleship, or research your way to "
         "something neither faction has. Five different endings are open to you "
         "and none of them are locked behind the others.",
         note("Keys 1–8 switch screens. The game saves itself whenever time passes.")],
        [("Take the bridge", None)])
