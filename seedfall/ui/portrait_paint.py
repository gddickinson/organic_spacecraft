"""Drawing a face: flat shapes, one hard light, and nothing airbrushed.

The same discipline every other picture in this game keeps — the hulls, the
holdings, the sky. Two tones of skin and a rim, because a portrait that
gradient-blended would sit oddly beside a structure drawn out of eight
polygons.

Read `ui/portrait.py` first: it works out *what* somebody looks like. This
only puts it on a widget, and every shape here is one fact off that record.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QSizePolicy, QWidget

from . import painting, portrait, theme

#: Where everything sits in the frame, as shares of it. Kept here rather than
#: scattered through the drawing so the whole layout can be read at once.
HEAD_Y = 0.39
HEAD_RX = 0.205
HEAD_RY = 0.250
CHIN = 0.32
NECK_W = 0.115
SHOULDER_Y = 0.80
SHOULDER_W = 0.72

#: How far the shadow side is pushed across the face.
SHADOW_AT = 0.34


def _head_path(cx: float, cy: float, rx: float, ry: float,
               jaw: float) -> QPainterPath:
    """A skull and a jaw that meets at a chin, as one closed shape."""
    path = QPainterPath()
    chin = cy + ry * (1.0 + CHIN * jaw)
    path.moveTo(cx - rx, cy)
    # The cranium: a half-ellipse over the top.
    path.cubicTo(cx - rx, cy - ry * 1.35, cx + rx, cy - ry * 1.35,
                 cx + rx, cy)
    # And down the cheek to the point of the chin.
    path.cubicTo(cx + rx * 0.98, cy + ry * 0.72,
                 cx + rx * 0.52, chin - ry * 0.10, cx, chin)
    path.cubicTo(cx - rx * 0.52, chin - ry * 0.10,
                 cx - rx * 0.98, cy + ry * 0.72, cx - rx, cy)
    path.closeSubpath()
    return path


def _hair_path(cx: float, cy: float, rx: float, ry: float,
               bald: float) -> QPainterPath:
    """A cap over the skull, receding with the years."""
    drop = ry * (0.12 + 0.34 * (1.0 - bald))
    path = QPainterPath()
    path.moveTo(cx - rx * 1.02, cy - ry * 0.10)
    path.cubicTo(cx - rx * 1.06, cy - ry * 1.45,
                 cx + rx * 1.06, cy - ry * 1.45,
                 cx + rx * 1.02, cy - ry * 0.10)
    path.cubicTo(cx + rx * 0.86, cy - ry * 0.52 - drop * 0.2,
                 cx - rx * 0.86, cy - ry * 0.52 - drop * 0.2,
                 cx - rx * 1.02, cy - ry * 0.10)
    path.closeSubpath()
    return path


def paint(p: QPainter, rect: QRectF, face: portrait.Face) -> None:
    """One portrait, inside `rect`."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setClipRect(rect)
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    unit = min(w, h)
    cx = x + w * 0.5 + unit * face.tilt
    cy = y + h * HEAD_Y
    rx = unit * HEAD_RX * face.width
    ry = unit * HEAD_RY

    _ground(p, rect, face)
    _shoulders(p, rect, cx, cy, ry, face)

    head = _head_path(cx, cy, rx, ry, face.jaw)
    light, shade = QColor(face.skin[0]), QColor(face.skin[1])
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(light)
    p.drawPath(head)
    # The shadow side: an offset disc clipped to the face. One source, over
    # the subject's left, like every hull in the game.
    p.save()
    p.setClipPath(head, Qt.ClipOperation.IntersectClip)
    p.setBrush(shade)
    p.drawEllipse(QPointF(cx + rx * SHADOW_AT, cy + ry * 0.10),
                  rx * 1.5, ry * 1.8)
    p.restore()

    _ears(p, cx, cy, rx, ry, face)
    _features(p, cx, cy, rx, ry, face)
    _marks(p, cx, cy, rx, ry, face)
    # The rim goes *under* the hair. Drawn over it, the head's top arc cut a
    # bright band across the crown and everybody looked like they were
    # wearing a skullcap.
    _rim(p, head, face)
    _hair(p, cx, cy, rx, ry, face)
    if face.gone:
        p.fillRect(rect, QColor(4, 8, 8, 120))
    p.restore()


def _ground(p: QPainter, rect: QRectF, face: portrait.Face) -> None:
    """What is behind them: where they were photographed."""
    colour, pattern = face.ground
    p.fillRect(rect, QColor(colour))
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    pen = QColor(theme.LINE)
    p.setPen(QPen(pen, 1.0))
    if pattern == "windows":
        step = max(6.0, h * 0.11)
        lit = QColor(theme.tint("osteo"))
        lit.setAlpha(46)
        row = y + step * 0.6
        n = 0
        while row < y + h * 0.75:
            col = x + step * 0.4
            while col < x + w - step * 0.4:
                p.fillRect(QRectF(col, row, step * 0.34, step * 0.5),
                           lit if (n % 3) else QColor(0, 0, 0, 0))
                col += step * 0.8
                n += 1
            row += step
    elif pattern == "rock":
        edge = QColor(theme.LINE)
        edge.setAlpha(120)
        p.setPen(QPen(edge, 1.0))
        for n in range(4):
            at = y + h * (0.16 + 0.18 * n)
            p.drawLine(QPointF(x, at), QPointF(x + w, at + h * 0.05))
    elif pattern == "bulkhead":
        edge = QColor(theme.LINE)
        edge.setAlpha(150)
        p.setPen(QPen(edge, 1.0))
        for n in range(3):
            at = x + w * (0.18 + 0.32 * n)
            p.drawLine(QPointF(at, y), QPointF(at, y + h))


def _shoulders(p: QPainter, rect: QRectF, cx: float, cy: float, ry: float,
               face: portrait.Face) -> None:
    """The neck and what is under the collar."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    unit = min(w, h)
    heavy = 1.18 if "heavy" in face.marks or "neck" in face.marks else 1.0
    top = y + h * SHOULDER_Y
    half = unit * SHOULDER_W * 0.5 * heavy
    neck = unit * NECK_W * 0.5 * heavy
    chin = cy + ry * (1.0 + CHIN * face.jaw)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(face.skin[1]))
    p.drawRect(QRectF(cx - neck, chin - ry * 0.10, neck * 2, top - chin + ry))
    body = QPainterPath()
    body.moveTo(cx - half, y + h)
    body.cubicTo(cx - half * 0.92, top, cx - neck * 1.7, top - unit * 0.05,
                 cx - neck * 1.1, top - unit * 0.08)
    body.lineTo(cx + neck * 1.1, top - unit * 0.08)
    body.cubicTo(cx + neck * 1.7, top - unit * 0.05, cx + half * 0.92, top,
                 cx + half, y + h)
    body.closeSubpath()
    # Not `theme.PANEL`: against a dark ground the shoulders vanished and
    # every head floated over a thin dark wedge.
    cloth = QColor(face.collar).darker(320)
    cloth.setAlpha(255)
    p.setBrush(cloth)
    p.drawPath(body)
    # The collar of whatever service made them.
    p.setPen(QPen(QColor(face.collar), max(1.6, unit * 0.014)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(QPointF(cx - half * 0.66, top + unit * 0.03),
               QPointF(cx - neck * 0.9, top - unit * 0.06))
    p.drawLine(QPointF(cx + half * 0.66, top + unit * 0.03),
               QPointF(cx + neck * 0.9, top - unit * 0.06))


def _ears(p: QPainter, cx: float, cy: float, rx: float, ry: float,
          face: portrait.Face) -> None:
    """Two, and they are most of why a head reads as a head."""
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(face.skin[1]))
    for side in (-1, 1):
        p.drawEllipse(QPointF(cx + side * rx * 0.98, cy + ry * 0.12),
                      rx * 0.13, ry * 0.18)


def _features(p: QPainter, cx: float, cy: float, rx: float, ry: float,
              face: portrait.Face) -> None:
    """Brow, eyes, nose, mouth. Four marks and no more."""
    ink = QColor(theme.INK)
    ink.setAlpha(190)
    dark = QColor(face.skin[1]).darker(150)
    eye_y = cy + ry * 0.06
    gap = rx * 0.44
    wide = rx * 0.20
    # Eyes.
    p.setPen(Qt.PenStyle.NoPen)
    for side in (-1, 1):
        p.setBrush(QColor(face.eyes))
        p.drawEllipse(QPointF(cx + side * gap, eye_y), wide, wide * 0.62)
    # Brows, angled by temperament rather than by mood.
    p.setPen(QPen(dark, max(1.2, rx * 0.09)))
    lift = ry * 0.10 * face.brow
    for side in (-1, 1):
        p.drawLine(QPointF(cx + side * (gap + wide), eye_y - ry * 0.26 + lift),
                   QPointF(cx + side * (gap - wide), eye_y - ry * 0.30 - lift))
    # Nose: a shadow down one side only, which is what a hard light does.
    p.setPen(QPen(dark, max(1.0, rx * 0.06)))
    p.drawLine(QPointF(cx + rx * 0.06, eye_y + ry * 0.04),
               QPointF(cx + rx * 0.10, eye_y + ry * 0.40))
    # Mouth: what they think of the way the ship is run.
    mouth_y = cy + ry * (0.62 + 0.10 * face.jaw)
    bend = ry * 0.20 * face.mood
    path = QPainterPath()
    path.moveTo(cx - rx * 0.34, mouth_y - bend * 0.35)
    path.quadTo(cx, mouth_y + bend, cx + rx * 0.34, mouth_y - bend * 0.35)
    p.setPen(QPen(QColor(dark).darker(130), max(1.6, rx * 0.11)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(path)
    # The years, in two lines and a hollow under the eye.
    if face.age > 0.55:
        line = QColor(dark)
        line.setAlpha(int(90 + 120 * min(1.0, (face.age - 0.55) / 0.45)))
        p.setPen(QPen(line, max(1.0, rx * 0.05)))
        for side in (-1, 1):
            p.drawLine(
                QPointF(cx + side * (gap + wide * 1.3), eye_y + ry * 0.16),
                QPointF(cx + side * (gap - wide * 0.2), eye_y + ry * 0.22))
        p.drawLine(QPointF(cx - rx * 0.30, mouth_y - ry * 0.22),
                   QPointF(cx - rx * 0.36, mouth_y + ry * 0.06))


def _marks(p: QPainter, cx: float, cy: float, rx: float, ry: float,
           face: portrait.Face) -> None:
    """What a clinic has fitted, where it shows.

    The reason the portrait is worth drawing: strain is a number on one
    screen and an argument on another, and here it is somebody you can see
    is partly a machine.
    """
    lumen = QColor(theme.tint("lumen"))
    warn = QColor(theme.tint("warn"))
    steel = QColor(theme.tint("steel"))
    eye_y = cy + ry * 0.06
    gap, wide = rx * 0.44, rx * 0.20
    p.setBrush(Qt.BrushStyle.NoBrush)
    if "eye" in face.marks:
        p.setPen(QPen(lumen, max(1.4, rx * 0.09)))
        p.drawEllipse(QPointF(cx - gap, eye_y), wide * 1.25, wide * 0.9)
        glow = QColor(lumen)
        glow.setAlpha(150)
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx - gap, eye_y), wide * 0.45, wide * 0.45)
        p.setBrush(Qt.BrushStyle.NoBrush)
    if "temples" in face.marks:
        p.setPen(QPen(lumen, max(1.4, rx * 0.10)))
        for side in (-1, 1):
            at = cx + side * rx * 0.86
            p.drawLine(QPointF(at, cy - ry * 0.34),
                       QPointF(at, cy - ry * 0.04))
    if "plate" in face.marks:
        p.setPen(QPen(steel, max(1.2, rx * 0.07)))
        for n in range(3):
            at = cy + ry * (0.18 + 0.14 * n)
            p.drawLine(QPointF(cx + rx * 0.44, at),
                       QPointF(cx + rx * 0.78, at - ry * 0.05))
    if "gills" in face.marks:
        p.setPen(QPen(steel, max(1.2, rx * 0.08)))
        chin = cy + ry * (1.0 + CHIN * face.jaw)
        for n in range(3):
            at = chin + ry * (0.14 + 0.13 * n)
            p.drawLine(QPointF(cx - rx * 0.30, at), QPointF(cx - rx * 0.10, at))
    if "seam" in face.marks:
        p.setPen(QPen(warn, max(1.4, rx * 0.09)))
        path = QPainterPath()
        path.moveTo(cx - rx * 0.82, cy - ry * 0.10)
        path.lineTo(cx - rx * 0.52, cy + ry * 0.18)
        path.lineTo(cx - rx * 0.66, cy + ry * 0.44)
        path.lineTo(cx - rx * 0.38, cy + ry * 0.72)
        p.drawPath(path)
    if "scar" in face.marks:
        p.setPen(QPen(QColor(face.skin[1]).lighter(150), max(1.0, rx * 0.06)))
        p.drawLine(QPointF(cx + rx * 0.30, cy - ry * 0.40),
                   QPointF(cx + rx * 0.52, cy - ry * 0.02))
    if "patch" in face.marks:
        patch = QColor(face.skin[0]).lighter(118)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(patch)
        path = QPainterPath()
        path.moveTo(cx + rx * 0.20, cy + ry * 0.10)
        path.lineTo(cx + rx * 0.74, cy - ry * 0.04)
        path.lineTo(cx + rx * 0.66, cy + ry * 0.52)
        path.lineTo(cx + rx * 0.26, cy + ry * 0.44)
        path.closeSubpath()
        p.drawPath(path)
        p.setBrush(Qt.BrushStyle.NoBrush)


def _hair(p: QPainter, cx: float, cy: float, rx: float, ry: float,
          face: portrait.Face) -> None:
    """Over the skull, and greying from the prime."""
    if face.bald > 0.92:
        return
    colour = QColor(face.hair)
    grey = QColor(portrait.GREY)
    mix = max(0.0, min(1.0, face.grey))
    colour = QColor(
        int(colour.red() * (1 - mix) + grey.red() * mix),
        int(colour.green() * (1 - mix) + grey.green() * mix),
        int(colour.blue() * (1 - mix) + grey.blue() * mix))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(colour)
    p.drawPath(_hair_path(cx, cy, rx, ry, face.bald))


def _rim(p: QPainter, head: QPainterPath, face: portrait.Face) -> None:
    """The light down one edge, tinted by how much of them is not them."""
    rim = QColor(portrait.strain_tint(face.strain))
    rim.setAlpha(int(120 + 100 * min(1.0, face.strain / 3.0)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(rim, 1.6))
    p.drawPath(head)


class Portrait(painting.Painted, QWidget):
    """One face, at a fixed size."""

    def __init__(self, game, officer, size: int = 72):
        super().__init__()
        self.face = portrait.of(game, officer)
        self._size = size
        self.setFixedSize(QSize(size, int(size * 1.18)))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setAccessibleName(f"Portrait of {getattr(officer, 'name', '')}")
        self.setToolTip(self.face.note)

    def draw(self, p: QPainter) -> None:
        rect = QRectF(0, 0, self.width(), self.height())
        paint(p, rect, self.face)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(theme.LINE), 1.0))
        p.drawRect(rect.adjusted(0.5, 0.5, -0.5, -0.5))


def chip(game, officer, size: int = 72) -> Portrait:
    """A portrait sized for a roster card."""
    return Portrait(game, officer, size)


def plate(game, officer, size: int = 150) -> Portrait:
    """A portrait sized for a sheet."""
    return Portrait(game, officer, size)
