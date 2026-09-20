"""The title screen: the premise, a seed box, and the way back in."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLineEdit, QVBoxLayout,
                             QWidget)

from ..core import slots
from ..core import state as state_mod
from ..data.chassis import CHASSIS_BY_ID
from ..data.lore import INTRO, SUBTITLE, TAGLINE, TITLE, VICTORIES
from . import chronicle_picker, memoir_panel, theme, window_dialogs
from .widgets import button, defer, label, note, spacer


class TitleDialog(QDialog):
    """Returns a :class:`Game` in :attr:`game`, or ``None`` if dismissed.

    `current` is the live chronicle when the title is opened from inside one
    ("Begin again", an ending), so the picker can keep *that* as a slot rather
    than the save on disk, which may be days behind it.
    """

    #: The window's question, bound the same way `MainWindow` binds it, so the
    #: picker's confirmations are the game's own dialog and a check can stub
    #: them on the instance exactly as it stubs `win.dialog`.
    dialog = window_dialogs.dialog

    def __init__(self, parent=None, current=None):
        super().__init__(parent)
        self.game = None
        self.current = current
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

        # **A returning captain gets the hook, not the whole premise.** With
        # four chronicles listed the dialog measured 932 px tall at its 720 px
        # width — over the 680 px the main window is allowed to shrink to —
        # and the list is what somebody coming back is here for. The rest is
        # one press away; a first launch lists nothing and reads it all.
        returning = bool(slots.listing()) or current is not None
        self.premise = [label(para, "", wrap=True) for para in INTRO]
        for para in self.premise:
            v.addWidget(para)
        if returning and len(self.premise) > 1:
            for para in self.premise[1:]:
                para.hide()
            more = button("The whole premise", kind="flat")
            more.clicked.connect(lambda: self._unfold(more))
            v.addWidget(more, 0, Qt.AlignmentFlag.AlignLeft)
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
        ah.addStretch(1)
        v.addWidget(actions)

        self.problem = note("")
        self.problem.setWordWrap(True)
        self.problem.hide()
        v.addWidget(self.problem)

        # Resume lives on the picker's first row now, beside what it resumes:
        # a button that said only "Resume" never said *which* chronicle.
        slot_host = QWidget()
        self.picker_slot = QVBoxLayout(slot_host)
        self.picker_slot.setContentsMargins(0, 0, 0, 0)
        self.picker = chronicle_picker.build(self)
        self.picker_slot.addWidget(self.picker)
        v.addWidget(slot_host)
        v.addWidget(memoir_panel.hall(self))     # the Hall of Captains

        foot = note("A concept, not a build spec. Every organ, material and number "
                    "in this game is drawn from the GESTALT design documents in "
                    "this repository.")
        foot.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        v.addWidget(spacer(10))
        v.addWidget(foot)

    def _unfold(self, more) -> None:
        """Show the premise in full. Hides the button rather than freeing it:
        it is the widget whose click this is."""
        for para in self.premise:
            para.show()
        more.hide()
        self.adjustSize()

    def _new(self) -> None:
        seed = self.seed_box.text().strip() or None
        self.game = state_mod.begin_new(seed)
        self.accept()

    def _compose(self) -> None:
        """The long way in: pick stock, origin, hull, crew and posting."""
        from .beginning_view import BeginningDialog
        seed = self.seed_box.text().strip()
        dlg = BeginningDialog(seed, self)
        dlg.exec()
        if dlg.choices is None:
            return
        self.game = state_mod.begin_new(seed or None, choices=dlg.choices)
        self.accept()

    def _resume(self) -> None:
        game = state_mod.load_game()
        if game is None:
            # Say why, and that nothing was destroyed: an unreadable save is
            # moved aside as `.bad` by `core/save.read`, so starting a new
            # chronicle from here can no longer clear the only copy of it.
            why = state_mod.load_problem() or "no reason given"
            self.seed_box.setPlaceholderText("that save could not be read")
            self.problem.setText(
                f"That save could not be read — {why}. It has been kept "
                f"beside the save as a .bad file, so a new chronicle will "
                f"not overwrite it.")
            self.problem.show()
            # The file has moved, so its row has to go — after the click that
            # pressed it, which came from a button in that row.
            defer(lambda: chronicle_picker.rebuild(self))
            return
        self.game = game
        self.accept()


def ask_for_game(parent=None, current=None):
    """Show the title screen. Returns a Game, or None if the player closed it."""
    dlg = TitleDialog(parent, current)
    dlg.exec()
    return dlg.game


def start_new_chronicle(win) -> None:
    """Get a fresh game and reset the window in place.

    Called after an ending and from "Begin again". Cancelling the title
    screen must cost nothing: with a live chronicle still underway the window
    goes back to it — closing here used to be the only exit, which made
    Escape abandon a game the player had just declined to abandon. Only when
    there is nothing to go back to does the window close.
    """
    game = ask_for_game(win, win.game)
    if game is None:
        g = win.game
        if g is not None and not g.dead and not g.victory:
            win.refresh()
            return
        win.close()
        return
    win.game = game
    win.battle = None
    # Saved the moment it opens, which is what the picker's warning promises.
    # It also resets the autosave's mark: `refresh` saves when the calendar
    # passes the day last saved, and that day was the *old* chronicle's — a
    # new one at day 0 behind a day-400 mark went unsaved for 400 days.
    win.save()
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
    from ..data.lessons import LESSONS
    take = win.confirm(
        "A short walk through",
        # Counted, not stated — "Eight things to try" survived two curriculum
        # rewrites, the same way "Five of them" once survived ten endings.
        f"{len(LESSONS)} things to try, one at a time, along the top of the "
        "screen. It watches what you actually do rather than what you click, "
        "it never blocks anything, and you can stop it whenever you like.",
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
         f"something neither faction has. {len(VICTORIES)} different endings "
         "are open to you and none of them are locked behind the others.",
         note("Keys 1–0 and the letters on the rail switch screens. The game "
              "saves itself whenever time passes.")],
        [("Take the bridge", None)])
