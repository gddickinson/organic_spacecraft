"""The conn: a pop-out window for flying the ship by hand.

A row of six camera feeds across the top, whichever one you pick blown up as
the main screen, an instrument panel down the side, and the controls: six
translation axes on thrusters or the main drive, three autopilot modes, and a
clock you can let run.

The window owns no rules. Every number on it comes from `sim/conn.py` and
every button calls into it — including the tooltips, which quote
`conn.forecast` so what the panel promises is what the burn does.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QGridLayout, QHBoxLayout, QLabel,
                             QVBoxLayout, QWidget)

from ..sim import autopilot as pilot_sim
from ..sim import conn as conn_sim
from ..sim import track as track_sim
from . import theme
from .viewport import Viewport
from .widgets import button, label, note

#: How often the window re-reads the approach while the clock is running.
TICK_MS = 700


class ConnWindow(QDialog):
    """Hand-flying, in its own window so the game stays behind it."""

    def __init__(self, win, contact=None):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.setWindowTitle("Conn — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1080, 760)

        self.contacts = [c for c in track_sim.contacts(self.game)
                         if c.kind != "star"]
        self.contact = contact or (self.contacts[0] if self.contacts else None)
        self.conn = (conn_sim.start(self.game, self.contact)
                     if self.contact is not None else None)
        self.main_view = "fore"
        self.running = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self._build()
        self.refresh()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(9)

        head = QHBoxLayout()
        self.title = label("", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        # The camera row. Clicking one puts it on the main screen.
        strip = QHBoxLayout()
        strip.setSpacing(6)
        self.feeds = {}
        for view_id, view_label, _vec in conn_sim.VIEWS:
            cell = QWidget()
            box = QVBoxLayout(cell)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(2)
            feed = Viewport(self.conn, view_id, compact=True)
            feed.mousePressEvent = (
                lambda _e, v=view_id: self._show_view(v))
            box.addWidget(feed)
            box.addWidget(button(view_label,
                                 lambda v=view_id: self._show_view(v),
                                 kind="flat"))
            self.feeds[view_id] = feed
            strip.addWidget(cell, 1)
        column.addLayout(strip)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        self.screen = Viewport(self.conn, self.main_view)
        middle.addWidget(self.screen, 3)

        side = QWidget()
        self.side = QVBoxLayout(side)
        self.side.setContentsMargins(0, 0, 0, 0)
        self.side.setSpacing(4)
        side.setMinimumWidth(260)
        middle.addWidget(side, 1)
        column.addLayout(middle, 1)

        self.status = note("")
        self.status.setWordWrap(True)
        column.addWidget(self.status)

        column.addWidget(self._controls())

    def _controls(self) -> QWidget:
        """Translation, drive selection, autopilot, and the clock."""
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 4, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(4)

        # Two rows of three: the six axes, laid out the way a pilot's hand
        # sits on them rather than alphabetically.
        order = [("left", 0, 0), ("forward", 0, 1), ("right", 0, 2),
                 ("down", 1, 0), ("back", 1, 1), ("up", 1, 2)]
        self.axis_buttons = {}
        for axis_id, row, col in order:
            _aid, axis_label, _vec = conn_sim.AXES_BY_ID[axis_id]
            btn = button(axis_label, lambda a=axis_id: self._burn(a))
            grid.addWidget(btn, row, col)
            self.axis_buttons[axis_id] = btn

        self.main_btn = button("Main drive: off", self._toggle_drive,
                               kind="flat")
        grid.addWidget(self.main_btn, 0, 3)
        self.use_main = False
        grid.addWidget(button("Hold (coast a minute)",
                              lambda: self._burn(None)), 1, 3)

        for index, (mode, text) in enumerate(
                (("null", "Kill relative motion"),
                 ("close", "Close and berth"),
                 ("orbit", "Make orbit"))):
            grid.addWidget(button(text, lambda m=mode: self._auto(m),
                                  kind="flat"), index // 2, 4 + index % 2)

        self.run_btn = button("Run clock", self._toggle_clock, kind="primary")
        grid.addWidget(self.run_btn, 1, 5)
        grid.addWidget(button("New approach…", self._pick_target, kind="flat"),
                       0, 6)
        grid.addWidget(button("Break off", self._break_off, kind="flat"), 1, 6)
        return panel

    # ── acts ───────────────────────────────────────────────────────────────

    def _show_view(self, view_id: str) -> None:
        self.main_view = view_id
        self.screen.view_id = view_id
        self.refresh()

    def _toggle_drive(self) -> None:
        self.use_main = not self.use_main
        self.refresh()

    def _burn(self, axis_id) -> None:
        if self.conn is None or self.conn.over:
            return
        self.conn.apply_result = conn_sim.apply(self.conn, axis_id,
                                                main=self.use_main)
        self.refresh()

    def _auto(self, mode: str) -> None:
        """Let the flight computer fly it until it resolves or stops helping."""
        if self.conn is None or self.conn.over:
            return
        before = (self.conn.range_km, self.conn.speed)
        for _ in range(400):
            if self.conn.over:
                break
            axis, main = pilot_sim.autopilot(self.conn, mode)
            if axis is None and mode == "null":
                break              # nothing left to null
            conn_sim.apply(self.conn, axis, main=main)
        if not self.conn.over and (self.conn.range_km, self.conn.speed) == before:
            self.win.toast("The computer has nothing to add.", "warn")
        self.refresh()

    def _toggle_clock(self) -> None:
        self.running = not self.running
        if self.running:
            self.timer.start(TICK_MS)
        else:
            self.timer.stop()
        self.refresh()

    def _tick(self) -> None:
        if self.conn is None or self.conn.over:
            self.running = False
            self.timer.stop()
        else:
            conn_sim.apply(self.conn, None)
        self.refresh()

    def _pick_target(self) -> None:
        rows = [f"{index + 1}. {c.name} — {c.detail}"
                for index, c in enumerate(self.contacts[:12])]
        picked = self.win.dialog(
            "Approach which?",
            ["Pick a contact and the conn opens on it twelve kilometres out."]
            + rows,
            [(c.name, index) for index, c in enumerate(self.contacts[:6])]
            + [("Cancel", None)])
        if picked is None:
            return
        self.contact = self.contacts[picked]
        self.conn = conn_sim.start(self.game, self.contact)
        for feed in self.feeds.values():
            feed.conn = self.conn
        self.screen.conn = self.conn
        self.refresh()

    def _break_off(self) -> None:
        if self.conn is not None and not self.conn.over:
            self.conn.outcome = "broken off"
            self.conn.log.append("Approach broken off.")
        self.running = False
        self.timer.stop()
        self.refresh()

    # ── painting ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        conn = self.conn
        if conn is None:
            self.title.setText("Nothing in range to approach")
            return
        self.title.setText(f"Conn — {conn.target.name}")
        self.main_btn.setText(f"Main drive: {'ON' if self.use_main else 'off'}")
        self.run_btn.setText("Stop clock" if self.running else "Run clock")

        live = not conn.over
        ok, why = conn_sim.can_burn(conn, self.use_main)
        for axis_id, btn in self.axis_buttons.items():
            btn.setEnabled(live and ok)
            if live:
                said = conn_sim.forecast(conn, axis_id, main=self.use_main)
                btn.setToolTip(
                    f"{conn_sim.AXES_BY_ID[axis_id][1]}: range "
                    f"{said['range_km'] * 1000:,.0f} m, closing "
                    f"{said['closing']:+,.1f} m/s, "
                    f"{said['rcs']:,.2f} mass left")
            else:
                btn.setToolTip(why)

        while self.side.count():
            item = self.side.takeAt(0)
            if item.widget():
                # Now, not when the event loop next idles: a deferred delete
                # leaves the old readout painted under the new one.
                item.widget().setParent(None)
        for name, value, kind in conn_sim.readout(conn):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            left = QLabel(name)
            left.setStyleSheet(f"color: {theme.INK3}; font-size: 12px;")
            right = QLabel(value)
            right.setStyleSheet(
                f"color: {theme.tint(kind) if kind in theme.TINTS else theme.INK};"
                f"font-family: '{theme.mono_family()}'; font-size: 12.5px;")
            line.addWidget(left)
            line.addStretch(1)
            line.addWidget(right)
            self.side.addWidget(row)
        hint = conn_sim.orbit_note(conn)
        if hint:
            self.side.addWidget(note(hint))
        self.side.addStretch(1)

        if conn.over:
            self.status.setText(f"{conn.outcome.upper()} — "
                                + (conn.log[-1] if conn.log else ""))
        else:
            self.status.setText(conn.log[-1] if conn.log else "")

        for feed in self.feeds.values():
            feed.update()
        self.screen.update()

    def closeEvent(self, event) -> None:
        self.timer.stop()
        if getattr(self.win, "conn_window", None) is self:
            self.win.conn_window = None
        super().closeEvent(event)


def open_conn(win, contact=None) -> ConnWindow:
    """Open the conn, or raise the one already open."""
    existing = getattr(win, "conn_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = ConnWindow(win, contact)
    win.conn_window = window
    window.show()
    return window
