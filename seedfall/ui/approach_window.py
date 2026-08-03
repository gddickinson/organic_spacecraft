"""Ship and target together, from outside, with where they are going.

The conn looks *out of the windows* and the flight panel reads the
instruments. Neither shows the one thing a docking pilot most wants: the two
objects together, from a viewpoint of their own choosing, with the geometry of
the approach visible as a shape rather than as three numbers.

So: a third view. The target at the origin drawn as the structure it is, the
ship where it actually is, the berths marked, and **the predicted course**
drawn as a track with the time written on it. Zoom, pan and tilt are the
pilot's, because which way to look at a docking is a question only the pilot
can answer — an approach that is dead ahead in one view is edge-on in another.

The track comes from `sim/preview.track`, which flies a throwaway twin with
the real `conn.apply` under the real flight computer. It is a *dry run of the
act*, not a formula: a predicted course worked out any other way would be a
second answer to a question the game already answers by doing it.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QSizePolicy, QSlider,
                             QVBoxLayout, QWidget)

from ..data import models3d
from ..sim import moorings
from ..sim import preview as preview_sim
from . import render3d, theme
from .widgets import button, label, mono_label, note

#: How far ahead the track is flown, in ticks of the conn's own minute, and
#: how often a point is kept. Sixty minutes is about what a berthing takes
#: from twelve kilometres, and a mark every six is enough to read the pace
#: without turning the line into beads.
AHEAD_TICKS = 60
MARK_EVERY = 6

#: The zoom slider's ends, as a share of the opening range that fills the
#: frame. At the wide end the whole approach fits; at the tight end the
#: structure fills it, which is what the last hundred metres needs.
WIDE = 1.6
TIGHT = 0.02

VOID = "#04060a"


class ApproachView(QWidget):
    """The pair, drawn from wherever the pilot has put the camera."""

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.setMinimumSize(420, 340)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(VOID))
            conn = self.window.conn
            if conn is None:
                painter.setPen(QColor(theme.INK2))
                painter.drawText(14, 24, "Nothing in reach to plot.")
                return
            span = self.window.span_km()
            camera = self.window.camera(w, h, span)
            self._target(painter, camera, conn)
            self._berths(painter, camera, conn)
            self._track(painter, camera, conn)
            self._ship(painter, camera, conn)
            self._scale(painter, w, h, span)
        finally:
            # **Always.** A `paintEvent` that leaves without ending its
            # painter leaves the QPainter attached to the widget, and Qt then
            # takes the whole process down when the widget is destroyed:
            # "Cannot destroy paint device that is being painted", and a
            # segfault. Measured — the full suite died at exit code 139 after
            # this window's own checks, every check passing, nothing failing,
            # and no traceback to read.
            painter.end()

    # ── the pieces ─────────────────────────────────────────────────────────

    def _target(self, painter, camera, conn) -> None:
        shown = models3d.present("anchorage", getattr(conn.target, "berth", ""))
        render3d.draw(painter, camera, shown["mesh"], (0.0, 0.0, 0.0),
                      conn.target.radius_km, (-0.5, -0.4, 0.75),
                      spin=0.0, tilt=shown["tilt"])

    def _berths(self, painter, camera, conn) -> None:
        want = getattr(conn, "berth", "")
        for name, at in moorings.points(conn.target):
            spot = camera.project(at)
            if spot is None:
                continue
            point, _ahead = spot
            lit = name == want
            tint = QColor(theme.tint("lumen" if lit else "steel"))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(tint, 1.6 if lit else 1.0))
            painter.drawEllipse(point, 5.0 if lit else 3.0,
                                5.0 if lit else 3.0)
            if lit:
                painter.setFont(QFont(theme.mono_family(), 8))
                painter.drawText(point + QPointF(8, 3), name)

    def _ship(self, painter, camera, conn) -> None:
        spot = camera.project(tuple(conn.pos))
        if spot is None:
            return
        point, _ahead = spot
        tint = QColor(theme.tint("chloro"))
        painter.setBrush(tint)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(point, 4.0, 4.0)
        # The nose, so the picture says which way the hull is pointing.
        nose = tuple(p + n * conn.target.radius_km * 0.6
                     for p, n in zip(conn.pos, conn.nose))
        far = camera.project(nose)
        if far is not None:
            painter.setPen(QPen(tint, 1.4))
            painter.drawLine(point, far[0])

    def _track(self, painter, camera, conn) -> None:
        rows = self.window.track()
        if len(rows) < 2:
            return
        tint = QColor(theme.tint("amber"))
        painter.setFont(QFont(theme.mono_family(), 8))
        last = None
        for seconds, at, _range_km, _speed in rows:
            spot = camera.project(at)
            if spot is None:
                last = None
                continue
            point, _ahead = spot
            if last is not None:
                painter.setPen(QPen(tint, 1.0, Qt.PenStyle.DashLine))
                painter.drawLine(last, point)
            painter.setBrush(tint)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point, 1.8, 1.8)
            if seconds > 0:
                painter.setPen(QColor(theme.INK2))
                painter.drawText(point + QPointF(5, -4),
                                 f"{seconds / 60:.0f}m")
            last = point

    def _scale(self, painter, w: int, h: int, span: float) -> None:
        painter.setPen(QColor(theme.INK2))
        painter.setFont(QFont(theme.mono_family(), 8))
        bar = w * 0.22
        painter.drawLine(QPointF(14, h - 18), QPointF(14 + bar, h - 18))
        across = span * (bar / max(1, w))
        said = (f"{across * 1000:,.0f} m" if across < 2 else f"{across:,.1f} km")
        painter.drawText(QPointF(14, h - 24), said)


class ApproachWindow(QDialog):
    """The approach from outside: zoom, pan, tilt, and where it is going."""

    def __init__(self, win):
        super().__init__(win)
        self.win = win
        self.setWindowTitle("Approach — SEEDFALL")
        self.setWindowFlag(Qt.WindowType.Window)
        self.setStyleSheet(theme.stylesheet())
        self.resize(720, 640)
        #: The camera, as the pilot has set it: how much of the approach is in
        #: frame, and which way round it is being looked at.
        self.zoom = 0.5
        self.turn = 0.6
        self.tilt = 0.5
        self.predict = True
        self._build()
        self.refresh()

    @property
    def conn(self):
        """The chronicle's flight — `game.conn`, not any one window's copy."""
        return self.win.conn

    @property
    def mode(self):
        """The armed computer mode — the flight's own, `Conn.auto`."""
        return getattr(self.win.conn, "auto", "") or None

    def _build(self) -> None:
        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(8)

        head = QHBoxLayout()
        self.title = label("Approach", "h2")
        head.addWidget(self.title, 1)
        head.addWidget(button("Close", self.close, kind="flat"))
        column.addLayout(head)

        self.view = ApproachView(self)
        column.addWidget(self.view, 1)

        self.readout = mono_label("")
        column.addWidget(self.readout)
        self.said = note("")
        column.addWidget(self.said)

        self.sliders = {}
        for name, text in (("zoom", "Zoom"), ("turn", "Pan"),
                           ("tilt", "Tilt")):
            row = QHBoxLayout()
            row.addWidget(label(text, ""))
            bar = QSlider(Qt.Orientation.Horizontal)
            bar.setRange(0, 100)
            bar.setValue(int(getattr(self, name) * 100))
            bar.valueChanged.connect(
                lambda value, n=name: self._set(n, value / 100.0))
            row.addWidget(bar, 1)
            column.addLayout(row)
            self.sliders[name] = bar

        row = QHBoxLayout()
        self.predict_btn = button("Predicted course: on", self._toggle,
                                  kind="flat")
        row.addWidget(self.predict_btn)
        row.addWidget(button("Frame it", self._frame, kind="flat"))
        row.addWidget(button("Flight controls…", self._flying, kind="flat"))
        column.addLayout(row)

        # **The one autopilot bar.** This window could show the computer's
        # course and offered no way to give it the conn — the only flying
        # screen with no autopilot at all. Same modes, same Manual, same
        # door (`flight_clock.arm_mode`) as everywhere else; `refresh`
        # relights it from the flight.
        from . import autopilot_bar
        self._auto_btns = autopilot_bar.buttons(self.win)
        if self._auto_btns:
            bar_row = QHBoxLayout()
            for btn in self._auto_btns:
                bar_row.addWidget(btn)
            column.addLayout(bar_row)

    # ── the camera ─────────────────────────────────────────────────────────

    def span_km(self) -> float:
        """How much of the approach is across the frame, in km."""
        conn = self.conn
        opening = max(getattr(conn, "start_km", 12.0) or 12.0, 0.001) \
            if conn is not None else 12.0
        share = TIGHT + (WIDE - TIGHT) * (self.zoom ** 2)
        floor = (conn.target.radius_km * 2.4) if conn is not None else 0.1
        return max(floor, opening * share)

    def centre(self) -> tuple:
        """What the camera looks at: the middle of the pair, not the target.

        The target is at the origin of the approach's own frame, so orbiting
        *that* puts a ship twelve kilometres out in a corner and leaves most
        of the window empty — which is what the first version did, and it
        looked like a mistake because it was one. A view of two things has to
        be centred on both of them.
        """
        conn = self.conn
        if conn is None:
            return (0.0, 0.0, 0.0)
        return tuple(p * 0.5 for p in conn.pos)

    def camera(self, w: int, h: int, span: float):
        """A camera on the pair, from wherever the pilot has put it.

        `turn` swings it round them and `tilt` lifts it over, far enough back
        that `span` kilometres fill the frame.
        """
        half = math.radians(30)
        back = (span * 0.5) / math.tan(half)
        yaw = (self.turn - 0.5) * math.tau
        pitch = (self.tilt - 0.5) * math.pi * 0.95
        middle = self.centre()
        eye = (middle[0] + math.cos(pitch) * math.sin(yaw) * back,
               middle[1] + math.cos(pitch) * math.cos(yaw) * back,
               middle[2] + math.sin(pitch) * back)
        forward = render3d.unit([m - e for m, e in zip(middle, eye)])
        # Any up that is not along the line of sight; the pole unless we are
        # looking down it, which is exactly the case a fixed up-vector breaks.
        pole = (0.0, 0.0, 1.0)
        if abs(render3d.dot(forward, pole)) > 0.98:
            pole = (0.0, 1.0, 0.0)
        right = render3d.unit(render3d.cross(forward, pole))
        up = render3d.unit(render3d.cross(right, forward))
        return render3d.Camera(at=eye, forward=forward, up=up,
                               width=w, height=h, half_fov=half)

    def track(self) -> list:
        if not self.predict or self.conn is None or self.conn.over:
            return []
        return preview_sim.track(self.conn, self.mode, ticks=AHEAD_TICKS,
                                 every=MARK_EVERY)

    # ── controls ───────────────────────────────────────────────────────────

    def _set(self, name: str, value: float) -> None:
        setattr(self, name, value)
        self.refresh()

    def _toggle(self) -> None:
        self.predict = not self.predict
        self.refresh()

    def _frame(self) -> None:
        """Put the whole approach in frame, which is what a lost pilot wants."""
        conn = self.conn
        if conn is None:
            return
        opening = max(getattr(conn, "start_km", 12.0) or 12.0, 0.001)
        # The pair, with room round them: the ship is at `range_km` and the
        # camera is on the midpoint, so the separation itself plus a margin is
        # what has to fit.
        want = max(conn.range_km * 1.5, conn.target.radius_km * 6.0)
        share = min(WIDE, max(TIGHT, want / opening))
        self.zoom = math.sqrt(max(0.0, (share - TIGHT) / (WIDE - TIGHT)))
        self.sliders["zoom"].blockSignals(True)
        self.sliders["zoom"].setValue(int(self.zoom * 100))
        self.sliders["zoom"].blockSignals(False)
        self.refresh()

    def _flying(self) -> None:
        from .flight_window import open_flight
        open_flight(self.win)

    def refresh(self) -> None:
        conn = self.conn
        self.predict_btn.setText(
            f"Predicted course: {'on' if self.predict else 'off'}")
        from . import autopilot_bar
        autopilot_bar.sync(self.win, getattr(self, "_auto_btns", []))
        if conn is None:
            self.title.setText("Approach — nothing in reach")
            self.readout.setText("")
            self.said.setText("Take the conn on something first.")
            self.view.update()
            return
        self.title.setText(f"Approach — {conn.target.name}")
        span = self.span_km()
        self.readout.setText(
            f"{conn.range_km * 1000:,.0f} m · closing {conn.closing:+.2f} m/s"
            f" · frame {span:,.2f} km across")
        rows = self.track()
        if rows and len(rows) > 1:
            seconds, _at, range_km, speed = rows[-1]
            # "run" is the free-flight mode and needs the game to fly, which
            # a dry run has not got — so the plotted line is ballistic and
            # the caption must not claim the computer flew it. Before the
            # mode lived on the flight, a Pilot-screen "Run for X" showed
            # here as "coasting — the computer has not got it" while the
            # computer was in fact burning.
            if self.mode == "run":
                tail = (f", under the computer, running for "
                        f"{getattr(conn, 'mark', '') or 'the mark'} — the "
                        "plotted line is the coast alone.")
            elif self.mode:
                tail = f", under the computer on {self.mode}."
            else:
                tail = ", coasting — the computer has not got it."
            self.said.setText(
                f"On this course: {range_km * 1000:,.0f} m at "
                f"{speed:.2f} m/s in {seconds / 60:.0f} minutes" + tail)
        else:
            self.said.setText("No course predicted.")
        self.view.update()

    def closeEvent(self, event) -> None:      # noqa: N802
        if getattr(self.win, "approach_window", None) is self:
            self.win.approach_window = None
        super().closeEvent(event)


def open_approach(win) -> ApproachWindow:
    """Open the approach view, or raise the one already open."""
    existing = getattr(win, "approach_window", None)
    if existing is not None:
        existing.raise_()
        existing.activateWindow()
        return existing
    window = ApproachWindow(win)
    win.approach_window = window
    window.show()
    return window
