"""The gunner's station, in its own window.

The captain's screen has a fire row and a salvo button. What it has never had is
the seat where a gunner sits: every mount's arc, what each one would cost the
hull, and the choice of *which* of them speak this turn.

That choice did not exist. `combat` offered one named mount or `_salvo` —
"everything that can bear" — and on a HAMMERFALL with five mounts that is 69
points of heat against a fault line of 40. See `sim/gunnery.py` for the measured
consequence; the short version is that the hull cooked itself in a fight it was
winning, and buying more armament made the salvo button worse.

So the window is built around the middle option. Four parts:

- **The sights.** One boresight per mount, arc drawn, target marked at its true
  relative bearing. `ui/mount_sight.py`. A mount that will not train reads as a
  mark outside a wedge rather than as a sentence in a log.
- **The plot.** `ui/tactical_plot.py`, the same geometry the captain decides
  `come about` on.
- **The board.** One row per mount: whether it bears, what stops it, its
  penalty, its heat, and a toggle to include it in the volley.
- **The trigger**, with the heat it will cost quoted before it is pulled.

The window owns no rules. Every number comes from `sim/gunnery.py` and
`sim/firing.py`, and the trigger sends the same list the board is showing.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QVBoxLayout,
                             QWidget)

from ..sim import firing
from ..sim import gunnery
from . import theme
from .mount_sight import MountSight
from .widgets import button, label, mono_label, note


class GunnerWindow(QDialog):
    """Hand gunnery: pick the mounts, see the cost, pull the trigger."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Gunnery — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(1040, 720)
        #: Mount slots the gunner has taken out of the volley. Kept by position,
        #: because `Shot.mount_id` is a part id and a hull carrying three Fusion
        #: Lances reports all three under the same name.
        self.held: set[int] = set()
        self._build()
        self.refresh()

    # ── the battle it is looking at ────────────────────────────────────────

    @property
    def battle(self):
        """Asked of the game every time rather than kept.

        The conn was fixed twice for holding a copy of the world; a gunnery
        board that went on describing a finished engagement would be the same
        fault in a new place.
        """
        return getattr(self.win, "battle", None) or getattr(
            self.win.game, "battle", None)

    # ── layout ─────────────────────────────────────────────────────────────

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(12, 10, 12, 10)
        column.setSpacing(8)

        head = QHBoxLayout()
        self.title = label("Gunnery", "h2")
        head.addWidget(self.title)
        head.addStretch(1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        # The sights, one per mount, across the top.
        self.sight_row = QHBoxLayout()
        self.sight_row.setSpacing(6)
        holder = QWidget()
        holder.setLayout(self.sight_row)
        holder.setMinimumHeight(150)
        column.addWidget(holder)

        middle = QHBoxLayout()
        middle.setSpacing(10)
        self.plot_holder = QVBoxLayout()
        plot_box = QWidget()
        plot_box.setLayout(self.plot_holder)
        middle.addWidget(plot_box, 3)

        board_box = QWidget()
        self.board = QVBoxLayout(board_box)
        self.board.setContentsMargins(0, 0, 0, 0)
        self.board.setSpacing(3)
        middle.addWidget(board_box, 4)
        column.addLayout(middle, 1)

        self.heat_line = note("")
        column.addWidget(self.heat_line)
        self.status = note("")
        column.addWidget(self.status)

        trigger = QHBoxLayout()
        trigger.setSpacing(6)
        self.fire_btn = button("Fire the volley", self._fire, kind="primary")
        trigger.addWidget(self.fire_btn)
        trigger.addWidget(button("Take the advice", self._advise, kind="flat"))
        trigger.addWidget(button("All of them", self._all, kind="flat"))
        trigger.addWidget(button("Hold everything", self._none, kind="flat"))
        trigger.addStretch(1)
        column.addLayout(trigger)

    # ── acts ───────────────────────────────────────────────────────────────

    def _shots(self) -> list:
        b = self.battle
        return gunnery.mounts(b) if b is not None else []

    def chosen(self) -> list:
        """The mount ids the board is currently offering to fire."""
        return [s.mount_id for i, s in enumerate(self._shots())
                if s.can_fire and i not in self.held]

    def _toggle(self, slot: int) -> None:
        self.held.discard(slot) if slot in self.held else self.held.add(slot)
        self.refresh()

    def _advise(self) -> None:
        """Hold everything the advice would not fire.

        Expressed as holds rather than as a fresh selection, because the board
        is a set of exclusions and two ways of saying what fires would drift.
        """
        b = self.battle
        if b is None:
            return
        want = list(gunnery.advise(b))
        self.held = set()
        for slot, shot in enumerate(self._shots()):
            if not shot.can_fire:
                continue
            if shot.mount_id in want:
                want.remove(shot.mount_id)
            else:
                self.held.add(slot)
        self.refresh()

    def _all(self) -> None:
        self.held = set()
        self.refresh()

    def _none(self) -> None:
        self.held = {i for i, _s in enumerate(self._shots())}
        self.refresh()

    def _fire(self) -> None:
        b = self.battle
        if b is None or b.over:
            return
        picked = self.chosen()
        if not picked:
            self.win.toast("Nothing is chosen to fire.")
            return
        self.win.battle_act({"type": "volley", "mounts": picked})
        self.held = set()
        self.refresh()

    # ── what it says ───────────────────────────────────────────────────────

    def refresh(self) -> None:
        b = self.battle
        while self.board.count():
            item = self.board.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        while self.sight_row.count():
            item = self.sight_row.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        while self.plot_holder.count():
            item = self.plot_holder.takeAt(0)
            if item.widget():
                item.widget().setParent(None)

        if b is None:
            self.title.setText("Gunnery — nothing engaged")
            self.heat_line.setText("")
            self.fire_btn.setEnabled(False)
            return

        self.title.setText(f"Gunnery — {b.enemy.ship.name}")
        shots = self._shots()
        bearing = firing.bearing_degrees(b.player, b.enemy)

        from .tactical_plot import TacticalPlot
        self.plot_holder.addWidget(TacticalPlot(b))

        for shot in shots:
            sight = MountSight(shot, bearing)
            self.sight_row.addWidget(sight)
        self.sight_row.addStretch(1)

        self._rows(b, shots)
        self._last_exchange(b)
        # After both, since the exchange list is empty before the first volley
        # and a stretch inside that early return would never be added.
        self.board.addStretch(1)
        self._heat(b)

        live = not b.over and bool(self.chosen())
        self.fire_btn.setEnabled(live)
        self.status.setText(
            firing.summary(b.player, b.enemy, b.band) if not b.over
            else f"{(b.result or 'over').upper()}")

    def _rows(self, b, shots) -> None:
        self.board.addWidget(mono_label("Mounts"))
        for slot, shot in enumerate(shots):
            row = QWidget()
            line = QHBoxLayout(row)
            line.setContentsMargins(0, 0, 0, 0)
            line.setSpacing(6)
            held = slot in self.held
            firing_now = shot.can_fire and not held
            weapon = next((w for w in b.player.st.weapons
                           if w.id == shot.mount_id), None)
            heat = weapon.wpn.heat if weapon and weapon.wpn else 0.0

            mark = "◼" if firing_now else "◻"
            tick = button(f"{mark} {shot.name}",
                          lambda _=False, s=slot: self._toggle(s),
                          kind="flat", enabled=shot.can_fire)
            tick.setToolTip(shot.why or "Ready.")
            line.addWidget(tick, 1)

            # `Shot.band_shift` said "bands to close (negative) or open
            # (positive) to reach its envelope" and nothing read it — on the one
            # board whose whole job is to say what would fix a mount. "range" is
            # a complaint; "close 2" is an order for the helm.
            said = shot.blocked_by
            if not shot.can_fire and shot.blocked_by == "range" and shot.band_shift:
                said = (f"close {abs(shot.band_shift)}" if shot.band_shift < 0
                        else f"open {shot.band_shift}")
            state = QLabel(said if not shot.can_fire
                           else ("held" if held else "firing"))
            state.setStyleSheet(
                f"color: {theme.tint('lumen') if firing_now else theme.INK3};"
                f"font-family: '{theme.mono_family()}'; font-size: 11px;")
            line.addWidget(state)

            cost = QLabel(f"{heat:.0f} heat")
            cost.setStyleSheet(f"color: {theme.INK3}; font-size: 11px;")
            line.addWidget(cost)
            self.board.addWidget(row)

    def _last_exchange(self, b) -> None:
        """What the last volley actually did, gun by gun.

        `sim/gunfire.Shot` has recorded `frm`, `to` and `weapon` — "who fired,
        by name", "who at", "what with" — since it was written, and **nothing
        read any of them.** `ui/battle3d.py` draws the geometry from the same
        records and labels the two hulls, so which gun did what existed only as
        prose in the log. On the gunner's own board it is the answer to the
        question the trigger asks: did my volley land?

        Both sides, because what came back matters as much as what went out.
        """
        shots = list(getattr(b, "shots", None) or [])
        if not shots:
            return
        self.board.addWidget(mono_label("Last exchange"))
        for shot in shots[-8:]:
            landed = (f"hit for {shot.damage:,.0f}" if shot.landed
                      else shot.outcome)
            tint = (theme.tint("lumen") if shot.landed and shot.mine
                    else theme.tint("rust") if shot.landed
                    else theme.INK3)
            line = QLabel(f"{shot.weapon} · {shot.frm} → {shot.to} · {landed}")
            line.setStyleSheet(f"color: {tint}; font-size: 11px;"
                               f"font-family: '{theme.mono_family()}';")
            self.board.addWidget(line)

    def _heat(self, b) -> None:
        """What the chosen volley will do to the hull, before the trigger."""
        said = gunnery.quote(b, self.chosen())
        cap = said["fault_line"]
        tint = theme.tint("rust") if said["faults"] else theme.INK
        over = (f" — faulting by {said['over_by']:.0f}" if said["faults"]
                else " — under the line")
        self.heat_line.setText(
            f"{len(said['mounts'])} mount(s) · +{said['heat_added']:.0f} heat · "
            f"{said['heat_now']:.0f} → {said['heat_after']:.0f} of {cap:.0f}"
            f"{over}")
        self.heat_line.setStyleSheet(
            f"color: {tint}; font-family: '{theme.mono_family()}'; "
            "font-size: 11.5px;")

    def closeEvent(self, event) -> None:      # noqa: N802
        if getattr(self.win, "gunner_window", None) is self:
            self.win.gunner_window = None
        super().closeEvent(event)


def open_gunnery(win) -> GunnerWindow:
    """Open the gunner's station, or raise the one already open."""
    existing = getattr(win, "gunner_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = GunnerWindow(win)
    win.gunner_window = window
    window.show()
    return window
