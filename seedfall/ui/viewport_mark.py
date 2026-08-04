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

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from . import theme

#: Radius of the ring, and how far the tick marks stand off it.
RING = 13.0
TICK = 6.0

#: How far outside the frame a sight may still be worth drawing, in pixels.
#: A little slack, so a marker on the very edge is not lost to rounding.
EDGE = 8.0

#: The circle drawn on a sight, in pixels. The name starts `DOT + 4` to its
#: right, which is where it has always been drawn.
DOT = 4.0

#: Breathing room around a label. **Not** a guess at how wide a name is —
#: that is measured from the font — only enough that two readings do not touch.
#:
#: What it replaced was a single 46-pixel box compared centre to centre, and
#: measured against the real font it was wrong in both directions at once. A
#: label is **9 px tall**, so vertically the box over-rejected by five times
#: and dropped names that would have read perfectly ten pixels apart. And a
#: label reaches `8 + width` from its dot — up to **85 px** for "Second
#: Signature" at 77 px — so horizontally it under-rejected by up to 39 px, and
#: rendered on the Conn's aft camera "Held Breath II" at x=315 ran straight
#: into the target reticle at x=391. Extents are cheap to ask for and a guess
#: about them is a picture nobody checked.
PAD = 3.0


def draw_sights(p, sights, project, cam, w: int, h: int, taken=()) -> int:
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

    `taken` is boxes the window has already used and this must keep off —
    today the target's reticle, which `Viewport._target` draws with its own
    name and range on it.
    """
    # **Nearest first, and nothing drawn on top of anything.** Measured on one
    # scene: four hulls — Second Signature, Margin Call, Long Consent, Quiet
    # Increment — projected to *exactly the same pixel*, dx=0 dy=0, because
    # they are hundreds of millions of kilometres off in almost the same
    # bearing. Four labels stacked on one spot is worse than three of them
    # missing, and nothing is lost: the "In view" board lists every one with
    # its range. `sights` arrives nearest first, so the one that is skipped is
    # always the further away.
    placed = [tuple(r) for r in taken]
    drawn = 0
    p.setFont(QFont(theme.mono_family(), 6))
    fm = p.fontMetrics()
    for vec, name, near in sights:
        at = _screen(vec, project, cam, w, h)
        if at is None:
            continue
        x, y = at
        left, box = _label_box(x, y, name, fm, w)
        if any(_overlaps(box, seen) for seen in placed):
            continue
        placed.append(box)
        tint = QColor(theme.tint("lumen" if near else "steel"))
        p.setPen(QPen(tint, 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(x, y), DOT, DOT)
        p.drawText(QPointF(left, y + 3), name)
        drawn += 1
    return drawn


def _label_box(x, y, name, fm, w: int):
    """`(left, box)` — where the name starts, and every pixel the sight uses.

    One door: `draw_sights` decides whether there is room and then draws in
    exactly the place it measured. Working `left` out twice is how a label
    comes to be tested in one spot and painted in another.
    """
    room = fm.horizontalAdvance(name)
    # **Whichever side has room.** Always to the right and a sight near the
    # edge loses its name to the frame.
    left = x + DOT + 4
    if left + room > w - 4:
        left = max(4.0, x - DOT - 4 - room)
    top = y + 3 - fm.ascent()
    return left, (min(x - DOT, left) - PAD, top - PAD,
                  max(x + DOT, left + room) + PAD, top + fm.height() + PAD)


def _overlaps(a, b) -> bool:
    """Do two `(x0, y0, x1, y1)` boxes share any pixel?"""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _screen(vec, project, cam, w: int, h: int):
    """Where a bearing lands, or `None` if it is not in this window."""
    length = sum(c * c for c in vec) ** 0.5
    if length <= 1e-9:
        return None
    at = project([c / length for c in vec], cam, w, h)
    if at is None:
        return None             # behind the lens
    # **In the picture, not merely in front of the camera.** `project` returns
    # a point for anything with a positive component along the view axis, so a
    # contact eighty degrees off the nose comes back at x=2,000 in a 464-pixel
    # window — drawn off the edge of the pixmap and counted as drawn.
    # Measured: the fore camera reported one sight and showed none.
    x, y = at[0], at[1]
    if not (-EDGE <= x <= w + EDGE and -EDGE <= y <= h + EDGE):
        return None
    return (x, y)


#: How far in from the frame an off-picture pointer sits, in pixels.
POINTER_PAD = 16.0

#: How far outside the picture a mark may be and still be worth pointing at,
#: as a multiple of the frame's half-diagonal.
#:
#: **The bound is the whole of the argument with `draw_sights`.** That refuses
#: to draw anything outside the frame, deliberately and for a good reason:
#: `project` answers for anything with a positive component along the view
#: axis, so a contact eighty degrees off the nose comes back at x=2,000 in a
#: 464-pixel window, and a camera once reported a sight drawn and showed none.
#: A chevron for every such contact in every camera would be six windows of
#: arrows pointing at things beside you, and the "In view" board already lists
#: them with their ranges.
#:
#: The *mark* is one thing — the single contact a course is laid on — and the
#: case that matters is the one measured when orbits gained a tilt: 35.7° out
#: of the plane put it 54° off the nearest axis and just past three edges, at
#: 266, 301 and 364 pixels from the middle of a frame whose half-diagonal is
#: 264. Two half-diagonals takes all three and leaves the eighty-degree case
#: — thousands of pixels out — where `draw_sights` leaves it.
POINTER_REACH = 2.0


def _edge_at(x: float, y: float, w: int, h: int) -> tuple:
    """Where a bearing off the picture meets the frame, and which way it lies.

    The point is pushed back onto a rectangle inset by `POINTER_PAD`, along
    the line from the middle of the view — so a mark eighty degrees off the
    nose gives a pointer on the edge nearest to it rather than a ring drawn
    two thousand pixels outside the pixmap.
    """
    cx, cy = w / 2.0, h / 2.0
    dx, dy = x - cx, y - cy
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return cx, cy, 0.0
    steps = []
    if abs(dx) > 1e-9:
        steps.append((cx - POINTER_PAD) / abs(dx))
    if abs(dy) > 1e-9:
        steps.append((cy - POINTER_PAD) / abs(dy))
    step = max(0.0, min(steps))
    return cx + dx * step, cy + dy * step, math.atan2(dy, dx)


def _pointer(p, x: float, y: float, angle: float, name: str, w: int) -> None:
    """A chevron on the frame, pointing at something out of the picture."""
    tint = QColor(theme.tint("warn"))
    p.setPen(QPen(tint, 1.3))
    p.setBrush(Qt.BrushStyle.NoBrush)
    nose = (x + math.cos(angle) * 7.0, y + math.sin(angle) * 7.0)
    for turn in (2.5, -2.5):
        p.drawLine(QPointF(*nose),
                   QPointF(x + math.cos(angle + turn) * 8.0,
                           y + math.sin(angle + turn) * 8.0))
    p.setFont(QFont(theme.mono_family(), 7))
    room = p.fontMetrics().horizontalAdvance(name)
    left = min(max(4.0, x - room / 2.0), max(4.0, w - 4.0 - room))
    p.drawText(QPointF(left, y - 10.0), name)


def draw(p, mark, project, cam, w: int, h: int) -> bool:
    """Ring and name the marked bearing. Returns whether anything was drawn.

    `project` is handed in rather than imported so this cannot drift from the
    camera the rest of the window is drawn with.

    **Off the picture is still an answer.** Six cameras on six axes do not
    cover a sphere — they leave a cone between each pair — and while every
    orbit lay in one plane that never showed, because everything a pilot laid
    a course on was somewhere near the ring of the four side views. With
    orbits tilted (`sim/elements`) a mark is regularly forty degrees out of
    the plane, and one was measured landing fifty to sixty degrees off the
    three nearest axes: ringed in *none* of the six windows. A course laid on
    something no camera will admit exists is worse than no course, so a mark
    in front of the lens but outside the frame gets a chevron on the edge
    pointing the way to turn.
    """
    if not mark:
        return False
    vec, name = mark
    length = sum(c * c for c in vec) ** 0.5
    if length <= 1e-9:
        return False
    spot = project([c / length for c in vec], cam, w, h)
    if spot is None:
        return False            # genuinely behind the camera
    x, y = spot[0], spot[1]
    if not (-EDGE <= x <= w + EDGE and -EDGE <= y <= h + EDGE):
        half = math.hypot(w, h) / 2.0
        if math.dist((x, y), (w / 2.0, h / 2.0)) > half * POINTER_REACH:
            return False        # beside you, not ahead — see `POINTER_REACH`
        _pointer(p, *_edge_at(x, y, w, h), name=name, w=w)
        return True
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
