"""The plotting board: a pop-out system plot you can navigate from.

`ui/plot_canvas.py` draws it. This is the window round it — the controls for
zoom, pan and tilt, the list of what is in the system, and the panel that
turns a selection into a course.

What a navigator can do here that the flat helm chart never allowed:

* **Select anything**, including a bare position in empty space.
* **Track** a contact, so its past and predicted tracks stay drawn while you
  look at something else.
* **Plot an intercept for a chosen date**, against where the target will be
  on that date — and see immediately whether the burn can make it, because
  the days come from the same `flight._leg` that charges for the flying.
* **Sweep the horizon** for the cheapest date to meet it, which is a real
  question with a moving target and has no answer on a static chart.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QLabel,
                             QListWidget, QListWidgetItem, QSlider,
                             QVBoxLayout, QWidget)

from ..sim import flight
from ..sim import track as track_sim
from . import theme
from .plot_canvas import MAX_SCALE, MIN_SCALE, PlotCanvas
from .widgets import button, label, note


class PlotWindow(QDialog):
    """The system, with time in it."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.game = win.game
        self.setWindowTitle("Plotting board — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1180, 800)
        self.burn_id = "standard"
        self._build()
        self.canvas.frame_all()
        self._sync_zoom()
        self.refresh()

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(8)

        head = QHBoxLayout()
        head.addWidget(label(f"Plotting board — {self.game.system.name}", "h2"), 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        middle = QHBoxLayout()
        middle.setSpacing(10)

        self.canvas = PlotCanvas(self.game)
        self.canvas.picked.connect(self._picked)
        middle.addWidget(self.canvas, 3)

        side = QWidget()
        side.setMinimumWidth(320)
        self.side = QVBoxLayout(side)
        self.side.setContentsMargins(0, 0, 0, 0)
        self.side.setSpacing(6)

        self.contact_list = QListWidget()
        self.contact_list.setMaximumHeight(190)
        self.contact_list.itemSelectionChanged.connect(self._from_list)
        self.side.addWidget(self.contact_list)

        self.detail = QVBoxLayout()
        self.side.addLayout(self.detail)
        self.side.addStretch(1)
        middle.addWidget(side, 1)
        column.addLayout(middle, 1)

        column.addWidget(self._viewbar())
        column.addWidget(self._plotbar())

    def _viewbar(self) -> QWidget:
        """Zoom, tilt, spin — the controls the captain asked for."""
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        row.addWidget(QLabel("Zoom"))
        self.zoom = QSlider(Qt.Orientation.Horizontal)
        self.zoom.setRange(0, 1000)
        self.zoom.valueChanged.connect(
            lambda v: self.canvas.set_scale(
                MIN_SCALE * (MAX_SCALE / MIN_SCALE) ** (v / 1000)))
        row.addWidget(self.zoom, 2)

        row.addWidget(QLabel("Tilt"))
        self.tilt = QSlider(Qt.Orientation.Horizontal)
        self.tilt.setRange(0, 82)
        self.tilt.setValue(34)
        self.tilt.valueChanged.connect(
            lambda v: self.canvas.set_tilt(math.radians(v)))
        row.addWidget(self.tilt, 1)

        row.addWidget(QLabel("Spin"))
        self.spin = QSlider(Qt.Orientation.Horizontal)
        self.spin.setRange(0, 359)
        self.spin.valueChanged.connect(
            lambda v: self.canvas.set_spin(math.radians(v)))
        row.addWidget(self.spin, 1)

        row.addWidget(button("Fit", self._fit, kind="flat"))
        row.addWidget(button("Orbits", self._toggle_orbits, kind="flat"))
        return bar

    def _plotbar(self) -> QWidget:
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        row.addWidget(QLabel("Burn"))
        self.burns = QComboBox()
        for burn in flight.BURNS:
            self.burns.addItem(burn.name, burn.id)
        self.burns.setCurrentIndex(
            [b.id for b in flight.BURNS].index(self.burn_id))
        self.burns.currentIndexChanged.connect(self._burn_changed)
        row.addWidget(self.burns)

        row.addWidget(QLabel("Arrive"))
        self.when = QSlider(Qt.Orientation.Horizontal)
        self.when.setRange(0, 100)
        self.when.valueChanged.connect(self._when_changed)
        row.addWidget(self.when, 2)
        self.when_label = QLabel("soonest")
        row.addWidget(self.when_label)

        row.addWidget(button("Soonest", self._soonest, kind="flat"))
        row.addWidget(button("Cheapest date", self._cheapest, kind="flat"))
        row.addWidget(button("Track", self._toggle_track, kind="flat"))
        row.addWidget(button("Fly it", self._engage, kind="primary"))
        row.addWidget(button("Conn…", self._conn, kind="flat"))
        return bar

    # ── acts ───────────────────────────────────────────────────────────────

    def _fit(self) -> None:
        self.canvas.frame_all()
        self._sync_zoom()

    def _sync_zoom(self) -> None:
        span = math.log(self.canvas.scale / MIN_SCALE) / math.log(
            MAX_SCALE / MIN_SCALE)
        self.zoom.blockSignals(True)
        self.zoom.setValue(int(max(0, min(1000, span * 1000))))
        self.zoom.blockSignals(False)

    def _toggle_orbits(self) -> None:
        self.canvas.show_orbits = not self.canvas.show_orbits
        self.canvas.update()

    def _picked(self, _cid: str) -> None:
        self.canvas.arrive_day = None
        self.when.blockSignals(True)
        self.when.setValue(0)
        self.when.blockSignals(False)
        self.refresh()

    def _from_list(self) -> None:
        items = self.contact_list.selectedItems()
        if items:
            self.canvas.selected = items[0].data(Qt.ItemDataRole.UserRole)
            self._picked(self.canvas.selected)

    def _burn_changed(self, index: int) -> None:
        self.burn_id = self.burns.itemData(index)
        self.refresh()

    def _when_changed(self, value: int) -> None:
        contact = self.canvas.contact_for(self.canvas.selected)
        if contact is None:
            return
        if value == 0:
            self.canvas.arrive_day = None
            self.when_label.setText("soonest")
        else:
            soonest = track_sim.solve(self.game, contact, self.burn_id)
            first = self.game.day + max(1.0, soonest.get("days", 1.0))
            self.canvas.arrive_day = first + (
                self.game.day + track_sim.HORIZON - first) * (value / 100)
            self.when_label.setText(f"day {self.canvas.arrive_day:,.0f}")
        self.refresh()

    def _soonest(self) -> None:
        self.when.setValue(0)

    def _cheapest(self) -> None:
        """Sweep the horizon for the least reaction mass. A real question."""
        contact = self.canvas.contact_for(self.canvas.selected)
        if contact is None:
            self.win.toast("Nothing selected to plot against.", "warn")
            return
        best = track_sim.cheapest(self.game, contact, self.burn_id)
        if best is None:
            self.win.toast("No date inside the horizon this burn can make.",
                           "bad")
            return
        self.canvas.arrive_day = best["arrive_day"]
        self.when_label.setText(f"day {best['arrive_day']:,.0f}")
        self.refresh()

    def _toggle_track(self) -> None:
        cid = self.canvas.selected
        if not cid:
            return
        if cid in self.canvas.tracked:
            self.canvas.tracked.discard(cid)
        else:
            self.canvas.tracked.add(cid)
        self.refresh()

    def _engage(self) -> None:
        """Hand the plot to the helm, which is the only thing that may fly."""
        contact = self.canvas.contact_for(self.canvas.selected)
        if contact is None:
            self.win.toast("Nothing selected.", "warn")
            return
        if contact.body_index is None:
            self.win.toast(
                f"{contact.name} is not somewhere the ship can be laid up. "
                "Plot it, then take the conn.", "warn")
            return
        result = flight.travel_to(self.game, contact.body_index, self.burn_id)
        self.win.toast(result.get("text") or f"Under way for {contact.name}.",
                       "good" if result.get("ok", True) else "bad")
        self.win.refresh()
        self.refresh()

    def _conn(self) -> None:
        from .conn_window import open_conn
        contact = self.canvas.contact_for(self.canvas.selected)
        open_conn(self.win, contact if contact and contact.kind != "point"
                  else None)

    # ── painting ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._fill_list()
        while self.detail.count():
            item = self.detail.takeAt(0)
            if item.widget():
                # `deleteLater` is deferred, so the old rows were still on
                # screen under the new ones — the panel read as two overlaid
                # descriptions. Unparenting takes them out now.
                item.widget().setParent(None)

        contact = self.canvas.contact_for(self.canvas.selected)
        if contact is None:
            self.detail.addWidget(note(
                "Click anything in the plot — a body, a quay, a hull, or a "
                "patch of empty space — to plot against it."))
            self.canvas.plotted = None
            self.canvas.update()
            return

        self.detail.addWidget(label(contact.name, "h3"))
        self.detail.addWidget(note(contact.detail))

        solved = track_sim.solve(self.game, contact, self.burn_id,
                                 self.canvas.arrive_day)
        self.canvas.plotted = solved
        rows = [
            ("Distance", f"{solved['au']:.2f} AU"),
            ("Flight time", f"{solved['days']:,.0f} days"),
            ("Reaction mass", f"{solved['fuel']:,.0f}"),
            ("Arrives", f"day {solved['arrive_day']:,.0f}"),
            ("Lead", f"{solved.get('lead', 0):.2f} AU"),
        ]
        if solved.get("wait"):
            rows.append(("Waiting", f"{solved['wait']:,.0f} days"))
        for name, value in rows:
            self.detail.addWidget(self._row(name, value))

        if not solved.get("feasible", True):
            self.detail.addWidget(note(
                f"This burn cannot be there by then — it is "
                f"{solved['short_by']:,.0f} days short. Choose a later date "
                "or a harder burn."))
        confidence = solved.get("confidence", 1.0)
        if confidence < 1.0:
            self.detail.addWidget(note(
                f"{contact.name} may not keep this errand: the growth in this "
                f"system crosses the threshold that redraws the traffic "
                f"before you arrive. Treat the plot as {confidence:.0%} good."))
        elif not contact.predictable:
            self.detail.addWidget(note(
                "Holding its present errand, this track is exact."))
        if self.canvas.selected in self.canvas.tracked:
            self.detail.addWidget(note("Tracked: its history and forecast "
                                       "stay on the plot."))
        self.canvas.update()

    def _row(self, name: str, value: str) -> QWidget:
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        left = QLabel(name)
        left.setStyleSheet(f"color: {theme.INK3}; font-size: 12px;")
        right = QLabel(value)
        right.setStyleSheet(f"color: {theme.INK}; "
                            f"font-family: '{theme.mono_family()}'; "
                            "font-size: 12.5px;")
        line.addWidget(left)
        line.addStretch(1)
        line.addWidget(right)
        return row

    def _fill_list(self) -> None:
        self.contact_list.blockSignals(True)
        self.contact_list.clear()
        for contact in track_sim.contacts(self.game):
            mark = "◎ " if contact.id in self.canvas.tracked else "  "
            item = QListWidgetItem(f"{mark}{contact.name} — {contact.detail}")
            item.setData(Qt.ItemDataRole.UserRole, contact.id)
            self.contact_list.addItem(item)
            if contact.id == self.canvas.selected:
                item.setSelected(True)
        self.contact_list.blockSignals(False)

    def closeEvent(self, event) -> None:
        if getattr(self.win, "plot_window", None) is self:
            self.win.plot_window = None
        super().closeEvent(event)


def open_plot(win) -> PlotWindow:
    """Open the plotting board, or raise the one already open."""
    existing = getattr(win, "plot_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = PlotWindow(win)
    win.plot_window = window
    window.show()
    return window
