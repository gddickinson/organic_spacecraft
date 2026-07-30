"""The ship itself, small, with its engines lit when they fire.

A docking panel that shows only numbers asks a pilot to hold the hull's
geometry in their head — which thruster is where, and which one the computer
just used. The hull has been a real 3D model since `data/hulls3d.py`, and
every engine has carried a position and a shove direction since propulsion
got places, and none of it had ever been drawn from the cockpit.

So: the ship, in its own frame, with a mark at every mount. Lit ones glow and
show a plume along the way they actually push — which is *opposite* to the way
the ship goes, so pressing **Ahead** lights the **aft** cluster. That is not a
flourish; it is the thing that makes the diagram worth looking at, because it
is the fact a pilot has to know and the console never said.

`sim/thrusters.firing` decides which are alight. This draws what it is told.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data import hulls3d
from ..data.chassis import CHASSIS_BY_ID
from ..sim import thrusters
from . import render3d, theme

#: How far back the camera sits, in hull half-lengths. The hull is authored at
#: half-length 1, so this frames it with room for the plumes at the ends.
SUBJECT_AT = 4.6
HALF_FOV = math.radians(30)

#: How the hull is held: broadside and tipped, the same reasoning as the
#: catalogue's portraits — a ship is a profile, and a plume pointing straight
#: at the viewer is a dot.
TILT = 1.16
SPIN = 0.72

#: Where the light comes from, over the viewer's left shoulder, so the hull
#: reads as a solid rather than a silhouette.
LIGHT = (-0.55, -0.40, 0.72)

#: A mount's mark, in pixels, and how far its plume reaches. The plume is
#: drawn in the hull's own frame and projected, so it foreshortens with
#: everything else.
MARK = 3.4
PLUME = 0.42

VOID = "#05070a"


class ShipDiagram(QWidget):
    """The hull with its engines, lit from a live approach."""

    def __init__(self, game, height: int = 190):
        super().__init__()
        self.game = game
        self.conn = None
        self._height = height
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding,
                           QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:
        return QSize(self._height * 2, self._height)

    def _mounts(self) -> list:
        conn = self.conn
        ship = getattr(self.game, "ship", None)
        if ship is None:
            return []
        axis = getattr(conn, "fired_axis", None) if conn is not None else None
        main = bool(getattr(conn, "fired_main", False)) if conn else False
        return thrusters.firing(ship, axis, main)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            w, h = self.width(), self.height()
            painter.fillRect(0, 0, w, h, QColor(VOID))
            ship = getattr(self.game, "ship", None)
            if ship is None:
                return
            camera = render3d.Camera(at=(0.0, 0.0, 0.0),
                                     forward=(0.0, 0.0, 1.0),
                                     up=(0.0, 1.0, 0.0), width=w, height=h,
                                     half_fov=HALF_FOV)
            chassis = CHASSIS_BY_ID.get(getattr(ship, "chassis", ""))
            if chassis is not None:
                render3d.draw(painter, camera,
                              hulls3d.mesh_for_chassis(chassis),
                              (0.0, 0.0, SUBJECT_AT), 1.0, LIGHT,
                              spin=SPIN, tilt=TILT)
            self._mounts_on(painter, camera)
        finally:
            # See `ui/approach_window.py`: a painter left open takes the
            # process down when the widget is destroyed.
            painter.end()

    def _mounts_on(self, painter: QPainter, camera) -> None:
        """Every mount as a mark, and the lit ones with a plume.

        The marks are rotated by the same `spin` and `tilt` the hull is drawn
        with — read off `render3d` rather than reimplemented, so a mount sits
        on the part of the hull it belongs to instead of near it.
        """
        lumen = QColor(theme.tint("lumen"))
        dim = QColor(theme.tint("steel"))
        for at, push, _label, _kn, lit in self._mounts():
            here = render3d.place(at, SPIN, TILT)
            here = (here[0], here[1], here[2] + SUBJECT_AT)
            spot = camera.project(here)
            if spot is None:
                continue
            point, _ahead = spot
            if lit:
                tail = render3d.place(
                    [a + p * PLUME for a, p in zip(at, push)], SPIN, TILT)
                tail = (tail[0], tail[1], tail[2] + SUBJECT_AT)
                far = camera.project(tail)
                if far is not None:
                    glow = QRadialGradient(point, max(
                        6.0, math.dist((point.x(), point.y()),
                                       (far[0].x(), far[0].y()))))
                    glow.setColorAt(0.0, QColor(lumen.red(), lumen.green(),
                                                lumen.blue(), 210))
                    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
                    painter.setBrush(glow)
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawEllipse(point, 9.0, 9.0)
                    painter.setPen(QPen(lumen, 2.0))
                    painter.drawLine(point, far[0])
                painter.setBrush(lumen)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawEllipse(point, MARK + 1.2, MARK + 1.2)
            else:
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.setPen(QPen(dim, 1.0))
                painter.drawEllipse(point, MARK, MARK)
