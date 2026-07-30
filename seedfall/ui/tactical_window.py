"""The tactical station, open whether or not anybody is shooting.

The conn is for the last few kilometres and the plotting board is for the
next few AU. Between them there was nothing for the question a captain asks
before either: *what happens if this goes wrong?* Combat existed only once it
had already started — the battle screen outside an engagement was two labels
and a Back button, and the gunner's window was one label — so the decision the
whole tactical model exists to serve, whether to be here at all, was made
blind and reviewed in the after-action log.

Two states, one window:

- **Standing by.** `sim/readiness.py` rehearses the fight that is not
  happening and this shows what it found: what is out there and how far off,
  which of your mounts would bear on it, what a full volley would do to the
  hull, who is in which seat, and who breaks whom first. Pick any hull on the
  list to have the rehearsal run against that one.
- **Engaged.** The same window, showing the live plot, the real bearings and
  the way through to the gunner's station — so a captain who was watching the
  board when the shooting started keeps the board they were watching.

The window owns no rules. Every figure is `sim/readiness.py`'s, which is
itself a dry run through `combat.start` — so the board cannot say one thing
and the engagement another.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QListWidget,
                             QListWidgetItem, QVBoxLayout, QWidget)

from ..sim import readiness as ready_sim
from . import theme
from .mount_sight import MountSight
from .tactical_board import TacticalBoard
from .tactical_plot import TacticalPlot
from .widgets import button, label, note

#: How many boresights fit across the head of the window. Five is the most
#: weapon slots any chassis in the game has, measured off `data/chassis.py`,
#: so no hull overflows this today.
SIGHTS_ACROSS = 5

#: Height for the boresight row. `MountSight` has a 132 px minimum and writes
#: the mount's name across the top and its state across the bottom; at the
#: minimum both captions sat on the arc. Measured at 132, 150 and 168: the
#: name clears the wedge at 168 and the state line stops being clipped.
SIGHT_HEIGHT = 168


class TacticalWindow(QDialog):
    """The tactical station: readiness when quiet, the plot when not."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Tactical — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1120, 780)
        #: Which hull the rehearsal is run against. None means whoever the
        #: sector would most likely send, which is the honest default for a
        #: captain who has not picked a quarrel with anyone in particular.
        self.against = None
        self._build()
        self.refresh()

    @property
    def game(self):
        return self.win.game

    @property
    def battle(self):
        b = getattr(self.win, "battle", None)
        return b if b is not None and not b.over else None

    # ── building ───────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(8)

        head = QHBoxLayout()
        self.title = label("Tactical", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        self.standing = note("")
        column.addWidget(self.standing)

        self.sights = QWidget()
        self.sights.setFixedHeight(SIGHT_HEIGHT)
        self.sight_row = QHBoxLayout(self.sights)
        self.sight_row.setContentsMargins(0, 0, 0, 0)
        self.sight_row.setSpacing(8)
        column.addWidget(self.sights)

        body = QHBoxLayout()
        body.setSpacing(10)

        left = QVBoxLayout()
        left.addWidget(label("In this system", "h3"))
        self.contacts = QListWidget()
        self.contacts.setMinimumWidth(300)
        self.contacts.currentRowChanged.connect(self._pick)
        left.addWidget(self.contacts, 1)
        left.addWidget(button("Against whoever comes", self._clear, kind="flat"))
        body.addLayout(left, 0)

        self.board = TacticalBoard()
        body.addWidget(self.board, 1)

        #: The live plot lives in a holder rather than being kept between
        #: refreshes: `TacticalPlot` takes its battle at construction and
        #: there is no battle at all most of the time.
        self.plot_holder = QWidget()
        self.plot_box = QVBoxLayout(self.plot_holder)
        self.plot_box.setContentsMargins(0, 0, 0, 0)
        self.plot_box.setSpacing(4)
        body.addWidget(self.plot_holder, 0)
        column.addLayout(body, 1)

        row = QHBoxLayout()
        self.to_gunnery = button("Gunnery…", self._gunnery, kind="flat")
        row.addWidget(self.to_gunnery)
        row.addWidget(button("Conn…", self._conn, kind="flat"))
        row.addWidget(button("Plotting board…", self._plotting, kind="flat"))
        row.addStretch(1)
        column.addLayout(row)

    # ── what it is looking at ──────────────────────────────────────────────

    def _rows(self) -> list:
        return ready_sim.threats(self.game)

    def _pick(self, index: int) -> None:
        rows = self._rows()
        self.against = rows[index]["hull"] if 0 <= index < len(rows) else None
        self.refresh(keep_list=True)

    def _clear(self) -> None:
        self.against = None
        self.contacts.setCurrentRow(-1)
        self.refresh()

    def _gunnery(self) -> None:
        from .gunner_window import open_gunnery
        open_gunnery(self.win)

    def _conn(self) -> None:
        from .conn_window import open_conn
        open_conn(self.win)

    def _plotting(self) -> None:
        from .plot3d_window import open_plot
        open_plot(self.win)

    # ── drawing ────────────────────────────────────────────────────────────

    def refresh(self, keep_list: bool = False) -> None:
        b = self.battle
        engaged = b is not None
        self.to_gunnery.setEnabled(engaged)
        while self.plot_box.count():
            old = self.plot_box.takeAt(0).widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        # Off the live battle when there is one. Asking for a rehearsal here
        # put a forecast against a hypothetical opponent under a title naming
        # the ship actually firing.
        report = (ready_sim.of(b, self.game) if engaged
                  else ready_sim.report(self.game, self.against))
        if engaged:
            self.plot_box.addWidget(label("The engagement", "h3"))
            self.plot_box.addWidget(TacticalPlot(b))
            self.title.setText(f"Tactical — {b.enemy_name}, turn {b.turn}")
        else:
            # The rehearsal's own geometry, drawn by the plot the fight uses.
            # It is the opening aspect a fight would actually start from, so
            # the range rings and the bearing are the ones that would apply —
            # and the caption says it is a rehearsal, because a plot that
            # looks live and is not would be the worst thing on the window.
            self.plot_box.addWidget(label("If it started now", "h3"))
            self.plot_box.addWidget(TacticalPlot(report["battle"]))
            self.plot_box.addWidget(note(
                "Rehearsal — nobody is shooting. The opening range and "
                "aspect a fight here would begin at."))
            self.title.setText(f"Tactical — {self.game.system.name}")
        self.plot_box.addStretch(1)
        self.standing.setText(ready_sim.standing(self.game))
        self.board.show_report(report, engaged=engaged)
        self._draw_sights(report)
        if not keep_list:
            self._fill_list()

    def _fill_list(self) -> None:
        self.contacts.blockSignals(True)
        self.contacts.clear()
        for row in self._rows():
            flag = "⚠ " if row["hostile"] else ""
            item = QListWidgetItem(
                f"{flag}{row['name']} — {row['kind']}\n"
                f"      {ready_sim.span(row['range_au'])} · {row['doing']}")
            self.contacts.addItem(item)
        self.contacts.blockSignals(False)

    def _draw_sights(self, report) -> None:
        while self.sight_row.count():
            old = self.sight_row.takeAt(0).widget()
            if old is not None:
                old.setParent(None)
                old.deleteLater()
        shots = report["shots"][:SIGHTS_ACROSS]
        if not shots:
            self.sight_row.addWidget(note("No mount aboard that will fire."))
            return
        # The *target's* bearing off the bow, not the turn needed to fix it.
        # Passing `turn_to_bear` put the mark where the enemy would be after
        # coming about, so every sight showed its mount already bearing.
        for shot in shots:
            self.sight_row.addWidget(MountSight(shot, report["bearing"]))
        self.sight_row.addStretch(1)

    def closeEvent(self, event) -> None:      # noqa: N802
        if getattr(self.win, "tactical_window", None) is self:
            self.win.tactical_window = None
        super().closeEvent(event)


def open_tactical(win) -> TacticalWindow:
    """Open the tactical station, or raise the one already open."""
    existing = getattr(win, "tactical_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = TacticalWindow(win)
    win.tactical_window = window
    window.show()
    return window
