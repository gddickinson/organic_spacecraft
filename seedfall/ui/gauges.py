"""Instruments, drawn: dials, segmented meters, traces and a scope.

These are painted rather than assembled out of labels, because a number you
have to read is a number you check and a needle you can see is a number you
notice. Everything is QPainter, so it renders identically offscreen and the
suite can look at it.

Each widget takes a reading dict from `sim/telemetry.py` and nothing else. It
does not know what a ship is, and it never decides whether a number is bad —
the reading carries its own `band`, which is the sim's threshold rather than
the panel's opinion.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (QColor, QFont, QPainter, QPainterPath, QPen,
                         QRadialGradient)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from . import theme

BAND = {"good": "#54cf7c", "watch": "#e6ac6d", "bad": "#e0685f"}
FACE = "#08120f"
ETCH = QColor(124, 150, 137, 70)


def _colour(reading: dict) -> QColor:
    return QColor(BAND.get(reading.get("band", "good"), BAND["good"]))


class Instrument(QWidget):
    """Shared frame: a dark face, a title, and a reading that can be replaced."""

    def __init__(self, reading: dict, height: int = 160):
        super().__init__()
        self.reading = reading
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    def set_reading(self, reading: dict) -> None:
        self.reading = reading
        self.update()

    def _face(self, p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(FACE))
        p.setFont(QFont(theme.mono_family(), 8))
        p.setPen(QColor(124, 150, 137, 190))
        p.drawText(10, 16, self.reading.get("title", "").upper())


class Dial(Instrument):
    """A 240° arc with a needle. Power, heat, anything with a ceiling."""

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        self._face(p)
        reading = self.reading
        tint = _colour(reading)
        width, height = self.width(), self.height()
        radius = min(width, height * 1.5) * 0.36
        centre = QPointF(width / 2, height * 0.72)
        box = QRectF(centre.x() - radius, centre.y() - radius,
                     radius * 2, radius * 2)

        start, span = 210, -240                     # degrees, clockwise
        p.setPen(QPen(ETCH, 7))
        p.drawArc(box, start * 16, span * 16)

        fraction = max(0.0, min(1.0, reading.get("fraction", 0.0)))
        p.setPen(QPen(tint, 7, cap=Qt.PenCapStyle.FlatCap))
        p.drawArc(box, start * 16, int(span * fraction) * 16)

        # Ticks, so the arc has a scale rather than just a length.
        p.setPen(QPen(ETCH, 1))
        for step in range(11):
            angle = math.radians(start + span * step / 10)
            inner = 0.86 if step % 5 else 0.78
            p.drawLine(
                QPointF(centre.x() + math.cos(angle) * radius * inner,
                        centre.y() - math.sin(angle) * radius * inner),
                QPointF(centre.x() + math.cos(angle) * radius * 0.98,
                        centre.y() - math.sin(angle) * radius * 0.98))

        angle = math.radians(start + span * fraction)
        p.setPen(QPen(tint, 2))
        p.drawLine(centre,
                   QPointF(centre.x() + math.cos(angle) * radius * 0.72,
                           centre.y() - math.sin(angle) * radius * 0.72))
        p.setBrush(tint)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(centre, 3, 3)

        value, cap = reading.get("now", 0.0), reading.get("cap", 0.0)
        p.setFont(QFont(theme.mono_family(), 13))
        p.setPen(tint)
        p.drawText(QRectF(0, centre.y() - radius * 0.42, width, 22),
                   Qt.AlignmentFlag.AlignHCenter,
                   f"{value:.0f}/{cap:.0f} {reading.get('unit', '')}".strip())
        p.setFont(QFont(theme.mono_family(), 7))
        p.setPen(QColor(124, 150, 137, 170))
        p.drawText(QRectF(6, height - 18, width - 12, 16),
                   Qt.AlignmentFlag.AlignHCenter, reading.get("note", ""))
        p.end()


class Stack(Instrument):
    """One segmented bar per layer — the hull, outermost first."""

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        self._face(p)
        rows = self.reading.get("layers") or self.reading.get("rows") or []
        if not rows:
            p.end()
            return
        top, width = 26, self.width()
        room = max(10.0, (self.height() - top - 22) / len(rows))
        p.setFont(QFont(theme.mono_family(), 7))
        for index, row in enumerate(rows):
            y = top + index * room
            fraction = max(0.0, min(1.0, row.get("fraction", 0.0)))
            tint = QColor(BAND.get(row.get("band", "good"), BAND["good"]))
            p.setPen(QColor(124, 150, 137, 190))
            p.drawText(QRectF(10, y, width * 0.46, room - 3),
                       Qt.AlignmentFlag.AlignVCenter,
                       row.get("name", "")[:22])
            track = QRectF(width * 0.48, y + room * 0.30,
                           width * 0.40, max(4.0, room * 0.34))
            p.fillRect(track, QColor(124, 150, 137, 34))
            filled = QRectF(track)
            filled.setWidth(track.width() * fraction)
            p.fillRect(filled, tint)
            if row.get("critical"):
                p.setPen(QPen(QColor(230, 172, 109, 190), 1))
                p.drawRect(track)
            p.setPen(tint)
            p.drawText(QRectF(width * 0.90, y, width * 0.09, room - 3),
                       Qt.AlignmentFlag.AlignVCenter
                       | Qt.AlignmentFlag.AlignRight,
                       f"{fraction * 100:.0f}%")
        p.setPen(QColor(124, 150, 137, 170))
        p.drawText(QRectF(6, self.height() - 18, width - 12, 16),
                   Qt.AlignmentFlag.AlignHCenter,
                   self.reading.get("note", ""))
        p.end()


class Scope(Instrument):
    """A plan view: bodies on their orbits, stars in sensor range, the front."""

    def __init__(self, reading: dict, height: int = 240):
        super().__init__(reading, height)
        self.sweep = 0.0

    def advance(self, by: float = 0.09) -> None:
        self.sweep = (self.sweep + by) % (2 * math.pi)
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        self._face(p)
        reading = self.reading
        width, height = self.width(), self.height()
        centre = QPointF(width / 2, height / 2 + 6)
        radius = min(width, height) * 0.42

        glow = QRadialGradient(centre, radius)
        glow.setColorAt(0.0, QColor(84, 207, 124, 26))
        glow.setColorAt(1.0, QColor(84, 207, 124, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(centre, radius, radius)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ETCH, 1))
        for ring in (0.33, 0.66, 1.0):
            p.drawEllipse(centre, radius * ring, radius * ring)
        for step in range(8):
            angle = math.pi * step / 4
            p.drawLine(centre,
                       QPointF(centre.x() + math.cos(angle) * radius,
                               centre.y() + math.sin(angle) * radius))

        # The sweep, which is what makes it read as an instrument.
        path = QPainterPath(centre)
        path.arcTo(QRectF(centre.x() - radius, centre.y() - radius,
                          radius * 2, radius * 2),
                   -math.degrees(self.sweep), 26)
        path.closeSubpath()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(84, 207, 124, 34))
        p.drawPath(path)

        reach = max(0.001, reading.get("reach", 1.0))
        p.setFont(QFont(theme.mono_family(), 7))
        for star in reading.get("neighbours", []):
            span = min(1.0, star["range"] / reach)
            at = QPointF(centre.x() + math.cos(star["bearing"]) * radius * span,
                         centre.y() + math.sin(star["bearing"]) * radius * span)
            tint = QColor(BAND["bad"]) if star["bloom"] > 0.4 else \
                QColor(BAND["good"] if star["port"] else "#7c9689")
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(tint)
            p.drawEllipse(at, 3.2 if star["port"] else 2.2,
                          3.2 if star["port"] else 2.2)
            p.setPen(QColor(tint.red(), tint.green(), tint.blue(), 150))
            p.drawText(QPointF(at.x() + 5, at.y() + 3), star["name"][:14])

        # Bodies here, on the inner third, so both scales are on one face.
        bodies = reading.get("contacts", [])
        furthest = max([b["range"] for b in bodies], default=1.0) or 1.0
        for body in bodies:
            span = 0.30 * (body["range"] / furthest)
            at = QPointF(centre.x() + math.cos(body["bearing"]) * radius * span,
                         centre.y() + math.sin(body["bearing"]) * radius * span)
            tint = QColor("#b98fe0") if body["relic"] else \
                QColor("#4fd6d0" if body["surveyed"] else "#7c9689")
            p.setPen(QPen(tint, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(at, 2.6, 2.6)

        p.setPen(QColor(theme.tint("chloro")))
        p.setBrush(QColor(theme.tint("chloro")))
        p.drawEllipse(centre, 2.4, 2.4)
        p.setPen(QColor(124, 150, 137, 170))
        p.drawText(QRectF(6, height - 16, width - 12, 14),
                   Qt.AlignmentFlag.AlignHCenter, reading.get("note", ""))
        p.end()
