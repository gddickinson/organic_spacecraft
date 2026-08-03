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
