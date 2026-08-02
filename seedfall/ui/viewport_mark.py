"""The ring on whatever the course is laid on, drawn out of the window.

**A free flight has no `conn.target`**, so `Viewport._target` returns at once
— its own comment says "station keeping: there is no target, only sky" — and
laying a course on a contact changed the picture not at all. Measured: the
viewport rendered *byte-identical* before and after `fly_at`, so a pilot
flying at Held Breath had no way to tell which of the dots out of the window
Held Breath was. The whole promise of the screen is that what you can see, you
can go to; without this it is a row of text to cross-reference against a
starfield.

It lives here rather than in `ui/viewport.py` because that file is a recorded
debt at 533 lines and a feature is not a reason to grow one.

The screen hands down a **direction and a name**, from
`sim/freeflight.toward`, so nothing here looks anything up: this module knows
how to draw a ring, and not what a contact is.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from . import theme

#: Radius of the ring, and how far the tick marks stand off it.
RING = 13.0
TICK = 6.0


def draw_sights(p, sights, project, cam, w: int, h: int) -> int:
    """Name the quays and hulls out there. Returns how many were drawn.

    **The Conn and the Pilot window showed the same scene differently, and a
    player noticed.** Standing 12 km off the Fleet Hub, the conn draws it
    inside a dashed reticle reading "Fleet Hub · 12.0 km", because it is
    `conn.target` and `Viewport._target` gives a target its real angular size.
    A free flight has no target, so the same Hub was one 1.6-pixel speck among
    the stars in `_sky` — invisible, and indistinguishable from a star if you
    did find it.

    The sky data was never the problem: measured, the free flight's `sky` has
    **more** in it than the approach's — ten entries against nine, including
    the anchorages the approach leaves out. Only the drawing was missing.

    Quays and hulls are named; worlds are not, because `_sky` already draws
    those as lit discs and nobody loses a planet.
    """
    drawn = 0
    for vec, name, near in sights:
        at = _screen(vec, project, cam, w, h)
        if at is None:
            continue
        x, y = at
        tint = QColor(theme.tint("lumen" if near else "steel"))
        p.setPen(QPen(tint, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(x, y), 4.0, 4.0)
        p.setFont(QFont(theme.mono_family(), 6))
        room = p.fontMetrics().horizontalAdvance(name)
        left = x + 8
        if left + room > w - 4:
            left = max(4.0, x - 8 - room)
        p.drawText(QPointF(left, y + 3), name)
        drawn += 1
    return drawn


def _screen(vec, project, cam, w: int, h: int):
    """Where a bearing lands, or `None` if it is not in this window."""
    length = sum(c * c for c in vec) ** 0.5
    if length <= 1e-9:
        return None
    at = project([c / length for c in vec], cam, w, h)
    return None if at is None else (at[0], at[1])


def draw(p, mark, project, cam, w: int, h: int) -> bool:
    """Ring and name the marked bearing. Returns whether anything was drawn.

    `project` is handed in rather than imported so this cannot drift from the
    camera the rest of the window is drawn with.
    """
    if not mark:
        return False
    vec, name = mark
    at = _screen(vec, project, cam, w, h)
    if at is None:
        return False            # behind the camera, or no bearing at all
    x, y = at
    tint = QColor(theme.tint("warn"))
    p.setPen(QPen(tint, 1.3))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(x, y), RING, RING)
    for near, far in ((-RING - TICK, -RING), (RING, RING + TICK)):
        p.drawLine(QPointF(x + near, y), QPointF(x + far, y))
        p.drawLine(QPointF(x, y + near), QPointF(x, y + far))
    # **The name goes on whichever side has room.** Drawn always to the
    # right, a mark near the edge of the window lost its label to the frame —
    # rendered, "Held Breath" came out as "H". The window knows its own
    # width; the label can be asked to fit in it.
    p.setFont(QFont(theme.mono_family(), 7))
    room = p.fontMetrics().horizontalAdvance(name)
    left = x + RING + 5
    if left + room > w - 4:
        left = max(4.0, x - RING - 5 - room)
    p.drawText(QPointF(left, y - RING - 3), name)
    return True
