"""The gunner's console: everything the hands can reach, and what it promises.

Two pieces, both of them dumb. `Console` is the row of controls along the
bottom — traverse, elevation, the trigger, the director — and `sidebar` is the
column of instruments beside the glass. Neither decides anything: every button
calls into `ui/turret_window`, which calls into the sim, and every number is
`sim/turret.readout`'s.

**The stick buttons are press-and-hold**, wired the way `ui/flight_clock`
wires a thruster, because a gun that traversed in fixed steps would be a
menu rather than a mounting. A pointing device and the keyboard both end up
in the same two calls.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QWidget

from ..sim import turret as turret_sim
from . import theme
from .widgets import button, label, mono_label, note


class Console(QWidget):
    """The row of controls under the glass."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        row.addWidget(self._stick())
        row.addWidget(self._trigger(), 1)
        row.addWidget(self._director())

    def _hold(self, text: str, axis: str, amount: float):
        """A button that works the mounting for as long as it is held."""
        btn = button(text, lambda: None, kind="flat")
        btn.pressed.connect(lambda a=axis, m=amount: self.window.push(a, m))
        btn.released.connect(lambda a=axis: self.window.release(a))
        btn.setAutoRepeat(False)
        return btn

    def _stick(self) -> QWidget:
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        grid.addWidget(self._hold("▲  up", "y", 1.0), 0, 1)
        grid.addWidget(self._hold("◀  left", "x", -1.0), 1, 0)
        grid.addWidget(self._hold("▶  right", "x", 1.0), 1, 2)
        grid.addWidget(self._hold("▼  down", "y", -1.0), 2, 1)
        return holder

    def _trigger(self) -> QWidget:
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        self.fire = button("FIRE   (space)", lambda: None, kind="danger")
        self.fire.pressed.connect(lambda: self.window.trigger(True))
        self.fire.released.connect(lambda: self.window.trigger(False))
        column.addWidget(self.fire)
        self.why = note("")
        self.why.setWordWrap(True)
        column.addWidget(self.why)
        return holder

    def _director(self) -> QWidget:
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(4)
        grid.addWidget(button("Next  (tab)", self.window.next_target,
                              kind="flat"), 0, 0)
        grid.addWidget(button("Back  (q)",
                              lambda: self.window.next_target(True),
                              kind="flat"), 0, 1)
        grid.addWidget(button("Worst threat  (t)", self.window.worst,
                              kind="primary"), 1, 0)
        self.feed = button("Feed  (r)", self.window.feed, kind="flat")
        grid.addWidget(self.feed, 1, 1)
        return holder

    def sync(self, action) -> None:
        """Say what the trigger would do, before it is pulled."""
        turret = action.turret
        ok, why = turret_sim.can_fire(turret)
        self.fire.setEnabled(not action.over)
        kind = turret.kind
        if action.over:
            self.why.setText("The action is over.")
        elif why:
            self.why.setText(why)
        elif ok:
            self.why.setText(
                f"{turret_sim.damage(turret):,.0f} a round  ·  "
                f"{kind.burst} out  ·  {kind.heat:,.0f}° of heat")
        else:
            self.why.setText(f"Loading — {turret.cooldown:.1f} s.")
        self.feed.setEnabled(bool(kind.rounds)
                             and turret.rounds < kind.rounds
                             and turret.reloading <= 0.0)


def sidebar(window) -> None:
    """Fill the window's side column with the seat's own instruments.

    Rebuilt rather than updated in place: it is a dozen labels refreshed
    twenty times a second and the whole column costs less to make than the
    bookkeeping to keep it. The Pilot screen's churn rule (#150) is about
    *controls* going out from under a finger, and there are none here.
    """
    column = window.side
    while column.count():
        item = column.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
    action = window.action
    if action is None:
        return
    turret = action.turret
    column.addWidget(label(turret.seat, "h3"))
    column.addWidget(note(turret.kind.note))
    for name, value, tint in turret_sim.readout(turret):
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(6)
        line.addWidget(note(name), 1)
        shade = mono_label(value)
        if tint:
            shade.setStyleSheet(f"color: {theme.tint(tint)};")
        line.addWidget(shade, 0, Qt.AlignmentFlag.AlignRight)
        column.addWidget(row)
    column.addSpacing(6)
    column.addWidget(label("Keys", "h3"))
    from .turret_window import KEYS
    for key, does in KEYS:
        row = QWidget()
        line = QHBoxLayout(row)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(6)
        line.addWidget(mono_label(key), 0)
        line.addWidget(note(does), 1)
        column.addWidget(row)
    column.addStretch(1)
