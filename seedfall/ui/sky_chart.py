"""The sky on the Sector Chart: a ring and a glyph per phenomenon.

Drawn by one line in `ui/star_chart.paintEvent`, after the rivals' marks.
A live phenomenon is a solid ring in its kind's colour (`data/phenomena
.Kind.colour`) with its glyph; a forecast one is the same ring dashed and a
touch wider, because it is not there yet. The nova, once it is brightening,
also rings its dose radius — the eight light years that are taking it.

What is marked is `phenomena.visible` — live within forecast range or where
the hull has been, and what the observatory has forecast — so the chart
shows only what the captain could know. Painting reads; it never writes.
"""

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from ..data import phenomena as data
from ..sim import phenomena as sky_sim
from . import theme


def draw(p, chart, game) -> None:
    """Every visible phenomenon on this tab of the chart."""
    shown = {s.id for s in _tab(chart, game)}
    font = QFont(theme.mono_family(), 11)
    font.setBold(True)
    scale = chart._projection()[0]
    rings: dict = {}
    for event, how in sky_sim.visible(game):
        if event.system_id not in shown:
            continue
        pt = chart._to_screen(game.galaxy.systems[event.system_id])
        stack = rings.get(event.system_id, 0)
        rings[event.system_id] = stack + 1
        radius = 12.0 + 4.0 * stack + (2.5 if how == "forecast" else 0.0)
        colour = QColor(event.spec.colour)
        colour.setAlpha(235 if how == "live" else 160)
        pen = QPen(colour, 2.2 if how == "live" else 1.4)
        if how == "forecast":
            pen.setStyle(Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(pt, radius, radius)
        if event.kind == "nova" and how == "live":
            reach = data.NOVA_RADIUS_LY * scale
            wide = QPen(QColor(colour.red(), colour.green(), colour.blue(), 90),
                        1.0, Qt.PenStyle.DotLine)
            p.setPen(wide)
            p.drawEllipse(pt, reach, reach)
            p.setPen(pen)
        p.setFont(font)
        p.drawText(QRectF(pt.x() - radius - 16, pt.y() - radius - 14, 18, 18),
                   Qt.AlignmentFlag.AlignCenter, event.spec.glyph)


def _tab(chart, game) -> list:
    from . import reaches_chart
    return reaches_chart.systems(game, chart.region)
