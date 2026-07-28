"""The ship, drawn. Drag to turn it, click a piece to find out what it is.

A software renderer painted with QPainter: `sim/plans.py` hands over solids,
`core/solid.py` projects and shades them, this fills the polygons back to front.
Around eight hundred faces survive the cull on a fitted NAVIS, which QPainter
draws without complaint and — the point — draws identically offscreen, so the
suite can look at the ship rather than take its word for it.

Selection is by tag: every face carries the id of the part, the cargo or the
berth it belongs to, so a click is a lookup rather than a hit-test against
geometry.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..core import solid as solid_mod
from ..data.hullforms import LIVING, ROCK, STRUCT, SYSTEM, VOID, WARM
from . import theme

#: The material vocabulary of `models3d/`: green living, cyan engineered,
#: amber structure, warm radiator, grey rock.
MATERIAL = {
    LIVING: "#54cf7c",
    SYSTEM: "#4fd6d0",
    STRUCT: "#e6ac6d",
    WARM: "#d68c60",
    ROCK: "#8a8072",
    VOID: "#2b3a36",
}


def _shaded(key: str, shade: float, dim: bool = False) -> QColor:
    colour = QColor(MATERIAL.get(key, "#7c9689"))
    factor = shade * (0.42 if dim else 1.0)
    return QColor(int(colour.red() * factor), int(colour.green() * factor),
                  int(colour.blue() * factor))


class ShipPlan(QWidget):
    """A turnable 3D view of one ship."""

    picked = pyqtSignal(str)

    def __init__(self, model: dict, height: int = 420):
        super().__init__()
        self.model = model
        self.view = solid_mod.View()
        self.selected: str | None = None
        self.spin = True
        self._drag = None
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._frame()

    # ── model ──────────────────────────────────────────────────────────────

    def set_model(self, model: dict) -> None:
        self.model = model
        self._frame()
        self.update()

    #: How much of the half-frame the ship should fill.
    FILL = 0.88

    def _frame(self) -> None:
        """Sit the camera so the ship fills the frame, whatever is fitted.

        Framed from the model's own extent rather than a fixed distance: a
        sensor mast or a mining root adds a third of the length again, and a
        constant camera drew a NAVIS at a third of the panel with the rest
        empty.
        """
        faces = [f for s in self.model["solids"] for f in s.faces]
        low, high = solid_mod.bounds(faces)
        span = max(high[i] - low[i] for i in range(3)) or 1.0
        radius = max((solid_mod.length(p)
                      for f in faces for p in f.points), default=1.0)
        self.view.distance = span * 1.6
        # project() scales by 1.6 / (depth + distance); solve for the zoom that
        # puts the outermost point at FILL of the half-frame.
        self.view.zoom = self.FILL * self.view.distance / max(1e-6, radius * 1.6)
        self._faces = faces
        self._names = {s.tag: (s.name, s.detail) for s in self.model["solids"]}

    def describe(self, tag: str | None) -> tuple:
        return self._names.get(tag or "", ("", ""))

    # ── interaction ────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        self._drag = event.position()
        self.spin = False
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event) -> None:
        if self._drag is None:
            return
        delta = event.position() - self._drag
        self._drag = event.position()
        self.view.yaw += delta.x() * 0.012
        self.view.pitch = max(-1.45, min(1.45,
                                         self.view.pitch + delta.y() * 0.012))
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        moved = self._drag is not None
        self._drag = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if moved:
            self.pick_at(event.position())

    def wheelEvent(self, event) -> None:
        step = event.angleDelta().y() / 900.0
        self.view.zoom = max(0.45, min(3.4, self.view.zoom + step))
        self.update()

    def pick_at(self, position) -> None:
        """Topmost face under the cursor wins — nearest, not furthest."""
        painted = solid_mod.project(self._faces, self.view)
        width, height = self.width(), self.height()
        scale = min(width, height) * 0.46
        cx, cy = width / 2, height / 2
        for face in reversed(painted):          # nearest first
            poly = QPolygonF([QPointF(cx + x * scale, cy + y * scale)
                              for x, y in face.points])
            if poly.containsPoint(position, Qt.FillRule.OddEvenFill):
                self.selected = None if face.tag == self.selected else face.tag
                self.picked.emit(self.selected or "")
                self.update()
                return
        self.selected = None
        self.picked.emit("")
        self.update()

    def turn(self, by: float) -> None:
        self.view.yaw += by
        self.update()

    # ── painting ───────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#08120f"))

        width, height = self.width(), self.height()
        scale = min(width, height) * 0.46
        cx, cy = width / 2, height / 2

        painted = solid_mod.project(self._faces, self.view)
        anything_selected = self.selected is not None
        for face in painted:
            chosen = face.tag == self.selected
            colour = _shaded(face.tint, face.shade,
                             dim=anything_selected and not chosen)
            if face.tint == VOID:
                colour.setAlpha(70 if not chosen else 150)
            poly = QPolygonF([QPointF(cx + x * scale, cy + y * scale)
                              for x, y in face.points])
            p.setBrush(colour)
            if chosen:
                p.setPen(QPen(QColor(theme.tint("lumen")), 1.4))
            else:
                edge = QColor(colour)
                edge.setAlpha(90)
                p.setPen(QPen(edge, 0.6))
            p.drawPolygon(poly)

        # Fore/aft, because a spheroid gives no other clue which way is up.
        p.setFont(QFont(theme.mono_family(), 8))
        p.setPen(QColor(124, 150, 137, 170))
        p.drawText(int(cx - scale), int(cy - scale * 0.86), "fore ↑ · aft ↓")
        if self.selected:
            name, detail = self.describe(self.selected)
            p.setPen(QColor(theme.tint("lumen")))
            p.drawText(int(cx - scale), int(cy + scale * 0.92),
                       f"{name}{'  ·  ' + detail if detail else ''}")
        p.end()
