"""Pop-out instrument windows you can leave open beside the game.

Six of them — power, heat, integrity, hold, crew and the scope — each a small
frameless-ish window that stays on top, reads the live game every second, and
can be closed and reopened without losing anything. They are deliberately
*windows* rather than another tab: the point is watching a number while doing
something else, and a tab cannot do that.

Nothing here computes. `sim/telemetry.py` produces the readings and
`ui/gauges.py` paints them; this owns the windows, the timer and the registry
of what is open.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QDialog, QVBoxLayout

from ..sim import telemetry
from . import theme
from .gauges import Dial, Scope, Stack
from .widgets import button, label, note

#: instrument id -> (window title, gauge class, opening size)
SHAPES = {
    "power": ("Power", Dial, (320, 230)),
    "heat": ("Heat", Dial, (320, 230)),
    "integrity": ("Integrity", Stack, (380, 250)),
    "hold": ("Hold", Stack, (380, 250)),
    "crew": ("Crew", Dial, (320, 230)),
    "scope": ("Scope", Scope, (420, 420)),
}

#: How often an open instrument re-reads the game.
REFRESH_MS = 900


class Monitor(QDialog):
    """One instrument, in its own window, watching the live game."""

    def __init__(self, win, instrument: str):
        super().__init__(win)
        title, gauge_class, size = SHAPES[instrument]
        self.win = win
        self.instrument = instrument
        self.setWindowTitle(f"{title} — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Tool)
        self.setStyleSheet(theme.stylesheet())
        self.resize(*size)

        column = QVBoxLayout(self)
        column.setContentsMargins(10, 10, 10, 10)
        column.setSpacing(6)
        self.gauge = gauge_class(telemetry.read(win.game, instrument))
        column.addWidget(self.gauge, 1)
        column.addWidget(button("Close", self.close))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.pull)
        self.timer.start(REFRESH_MS)
        self.pull()

    def pull(self) -> None:
        """Re-read the game. Live, not a snapshot taken when this opened."""
        reading = telemetry.read(self.win.game, self.instrument)
        self.gauge.set_reading(reading)
        if isinstance(self.gauge, Scope):
            self.gauge.advance()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        self.win.monitors.pop(self.instrument, None)
        super().closeEvent(event)


def toggle(win, instrument: str) -> None:
    """Open the instrument, or close it if it is already up."""
    open_now = getattr(win, "monitors", None)
    if open_now is None:
        open_now = win.monitors = {}
    existing = open_now.get(instrument)
    if existing is not None:
        existing.close()
        return
    monitor = Monitor(win, instrument)
    open_now[instrument] = monitor
    monitor.show()


def open_all(win) -> None:
    for instrument in SHAPES:
        if instrument not in getattr(win, "monitors", {}):
            toggle(win, instrument)


def close_all(win) -> None:
    for monitor in list(getattr(win, "monitors", {}).values()):
        monitor.close()


def chooser(win) -> QDialog:
    """A small panel listing the instruments, with what each one is for."""
    dlg = QDialog(win)
    dlg.setWindowTitle("Instruments")
    dlg.setStyleSheet(theme.stylesheet())
    dlg.setMinimumWidth(420)
    column = QVBoxLayout(dlg)
    column.setContentsMargins(18, 16, 18, 16)
    column.setSpacing(6)
    column.addWidget(label("Instruments", "h2"))
    column.addWidget(note(
        "Each opens in its own window and stays on top, reading the live "
        "game. Leave the ones you care about open while you fly."))
    for instrument, (title, _cls, _size) in SHAPES.items():
        reading = telemetry.read(win.game, instrument)
        column.addWidget(button(
            f"{title} — {reading.get('note', '')}"[:64],
            lambda _=False, i=instrument: toggle(win, i)))
    column.addWidget(button("Open them all", lambda: open_all(win),
                            kind="primary"))
    column.addWidget(button("Close them all", lambda: close_all(win)))
    column.addWidget(button("Done", dlg.accept))
    return dlg
