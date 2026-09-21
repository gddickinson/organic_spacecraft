"""The gun, in a window you can actually fight from: the beat, the keys, the hands.

The conn is flown from a pop-out because flying is real time and the rest of
the game is not; a gun is the same and for the same reason. The window owns
one beat — `BEAT_MS` of wall clock is `STEP` of action — and every control on
it, the keys included, goes through the sim and nowhere else.

**The stick is held, not tapped.** A key down puts the mounting on that axis
and a key up takes it off, so traversing is something you do *for as long as
you need to*, which is the whole feel of working a turret by hand. That is
`ui/flight_clock.start_burn`'s rule for a thruster, applied to a gun.

**Three ways to point it**, and a gunner uses all of them: the stick for
searching, `Tab` to put the director on something, and `T` for whatever is
most likely to kill you next. The trigger is always the gunner's.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QVBoxLayout, QWidget)

from ..core.rng import RNG
from ..sim import drills as drill_sim
from ..sim import skirmish, turret as turret_sim
from . import theme, turret_controls
from .turret_view import TurretGlass
from .widgets import button, label, note

#: Milliseconds of wall clock between beats. Twenty a second: fast enough
#: that a mounting reads as swinging rather than stepping, cheap enough that
#: a two-minute action is 2,400 frames and not 7,200.
BEAT_MS = 50

#: How much action one beat is worth. Real time — a second at the gun is a
#: second in the action — because a turret that ran at any other rate would
#: make every lead in `sim/gunsight` a lie.
BEAT = BEAT_MS / 1000.0

#: What each key does. One table, read by the window and printed on the
#: console, so the help and the behaviour cannot drift.
KEYS = (
    ("A / D", "traverse left and right"),
    ("W / S", "elevate and depress"),
    ("Space", "fire"),
    ("Tab", "next contact"),
    ("Q", "previous contact"),
    ("T", "the worst thing out there"),
    ("R", "feed the mounting"),
    ("Esc", "leave the seat"),
)

_STICK = {
    Qt.Key.Key_A: ("x", -1.0), Qt.Key.Key_Left: ("x", -1.0),
    Qt.Key.Key_D: ("x", 1.0), Qt.Key.Key_Right: ("x", 1.0),
    Qt.Key.Key_W: ("y", 1.0), Qt.Key.Key_Up: ("y", 1.0),
    Qt.Key.Key_S: ("y", -1.0), Qt.Key.Key_Down: ("y", -1.0),
}


class TurretWindow(QDialog):
    """One seat, one action, one beat."""

    def __init__(self, win, action, drill=None, on_done=None):
        super().__init__(win)
        self.win = win
        self.action = action
        self.drill = drill
        self.on_done = on_done
        self.rng = RNG(f"turret:{id(action)}")
        self.held: dict = {}
        self.setWindowTitle(
            f"{action.turret.seat} — {drill.name if drill else 'the gun'}")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1180, 800)
        self._build()
        self.beat = QTimer(self)
        self.beat.timeout.connect(self.step)
        self.beat.start(BEAT_MS)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.refresh()

    # ── layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(12, 10, 12, 10)
        column.setSpacing(8)

        head = QHBoxLayout()
        self.title = label("", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Leave the seat", self.close, kind="flat"))
        column.addLayout(head)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        self.glass = TurretGlass(self.action, self.drill)
        middle.addWidget(self.glass, 3)
        side = QWidget()
        self.side = QVBoxLayout(side)
        self.side.setContentsMargins(0, 0, 0, 0)
        self.side.setSpacing(4)
        side.setMinimumWidth(250)
        side.setMaximumWidth(290)
        middle.addWidget(side, 0)
        column.addLayout(middle, 1)

        self.status = note("")
        self.status.setWordWrap(True)
        column.addWidget(self.status)
        self.controls = turret_controls.Console(self)
        column.addWidget(self.controls)

    # ── the beat ───────────────────────────────────────────────────────────

    def step(self) -> None:
        """One slice of the action, then the picture."""
        action = self.action
        if action is None or action.over:
            self.beat.stop()
            self.refresh()
            self._finished()
            return
        if self.drill is not None:
            drill_sim.tick(action, self.drill, self.rng, BEAT)
        else:
            skirmish.tick(action, self.rng, BEAT)
        if action.turret.firing:
            skirmish.fire(action, self.rng)
        self.refresh()
        if action.over:
            self.beat.stop()
            self._finished()

    def _finished(self) -> None:
        """Hand the debrief back to whoever opened the seat, once."""
        if self.on_done is None:
            return
        done, self.on_done = self.on_done, None
        done(self.action, self.drill)

    # ── the hands ──────────────────────────────────────────────────────────

    def _sync_stick(self) -> None:
        turret_sim.stick(self.action.turret,
                         self.held.get("x", 0.0), self.held.get("y", 0.0))

    def push(self, axis: str, amount: float) -> None:
        """A control is held: put the mounting on that axis."""
        self.held[axis] = amount
        self._sync_stick()

    def release(self, axis: str) -> None:
        self.held.pop(axis, None)
        self._sync_stick()

    def trigger(self, on: bool) -> None:
        """The trigger, held. One pull happens at once so a tap does something."""
        if self.action is None or self.action.over:
            return
        self.action.turret.firing = bool(on)
        if on:
            shot = skirmish.fire(self.action, self.rng)
            if shot.why:
                self.status.setText(shot.why)
            elif shot.target:
                # **How far off it was.** The one thing a gunner learning to
                # lead cannot see for themselves: the pip says where to aim
                # and only the round knows where the gun actually was.
                self.status.setText(
                    f"Hit — {shot.damage:,.0f}, {shot.off:.1f}° off."
                    if shot.hit else f"Missed by {shot.off:.1f}°.")
        self.refresh()

    def next_target(self, back: bool = False) -> None:
        skirmish.cycle(self.action, back)
        self.refresh()

    def worst(self) -> None:
        """Put the director on whatever is most likely to kill you."""
        contact = skirmish.nearest_threat(self.action)
        turret_sim.lock(self.action.turret, contact.id if contact else "")
        self.refresh()

    def feed(self) -> None:
        ok, why = turret_sim.feed(self.action.turret)
        self.status.setText(why)
        self.refresh()

    # ── keys ───────────────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:            # noqa: N802
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in _STICK:
            axis, amount = _STICK[key]
            self.push(axis, amount)
            return
        if key == Qt.Key.Key_Space:
            self.trigger(True)
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_E):
            self.next_target()
            return
        if key == Qt.Key.Key_Q:
            self.next_target(back=True)
            return
        if key == Qt.Key.Key_T:
            self.worst()
            return
        if key == Qt.Key.Key_R:
            self.feed()
            return
        if key == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:          # noqa: N802
        if event.isAutoRepeat():
            return
        key = event.key()
        if key in _STICK:
            self.release(_STICK[key][0])
            return
        if key == Qt.Key.Key_Space:
            self.trigger(False)
            return
        super().keyReleaseEvent(event)

    # ── painting ───────────────────────────────────────────────────────────

    def refresh(self) -> None:
        action = self.action
        if action is None:
            return
        seat = action.turret.seat
        if self.drill is not None:
            self.title.setText(f"{self.drill.name} — {seat}")
        else:
            self.title.setText(f"{seat} — {action.hull}")
        self.controls.sync(action)
        turret_controls.sidebar(self)
        if not self.status.text() or action.log:
            self.status.setText(action.log[-1] if action.log else "")
        self.glass.action = action
        self.glass.drill = self.drill
        self.glass.update()

    def closeEvent(self, event) -> None:               # noqa: N802
        self.beat.stop()
        self.held.clear()
        if self.action is not None:
            self.action.turret.firing = False
            skirmish.finish(self.action, self.action.outcome or "left",
                            "You left the seat.")
        self._finished()
        if getattr(self.win, "turret_window", None) is self:
            self.win.turret_window = None
        super().closeEvent(event)


def open_turret(win, action, drill=None, on_done=None) -> TurretWindow:
    """Open the seat, or raise the one already open."""
    from . import popout
    return popout.open_one(
        win, "turret_window",
        lambda: TurretWindow(win, action, drill, on_done))
