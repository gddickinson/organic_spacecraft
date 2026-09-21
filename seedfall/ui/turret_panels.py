"""The gunner's three boards: what is locked, what is around, what is wanted.

The other half of `ui/turret_hud.py`, split at the seam the two halves already
had: that file draws marks *on the world* — a bracket round a thing, a pip
where to aim — and this draws panels *beside* it, in corners, in screen space,
about things the world cannot show.

- **The target monitor**, bottom left. What the director is on: its name, what
  it is, how far, how fast it is closing, what is left of it, and — the piece
  that makes a station worth attacking rather than merely shooting — the list
  of fittings that can be taken off it one at a time.
- **The contact ball**, bottom right. Everything within reach plotted on a
  sphere seen from above and behind, so the half of the sky the gunner is not
  looking at is still a picture. FreeSpace called it a radar; *Battlestar*
  called it DRADIS; either way it is the gauge that stops a turret being a
  tunnel.
- **The directive list**, top right, which ticks itself off while you fire.
  `sim/drills.directives` answers it fresh every frame, so it cannot drift.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from ..sim import gunsight, skirmish
from . import theme

#: How big the boards are, in pixels. Fixed rather than a share of the frame:
#: a target monitor that grew with the window would be unreadable on one
#: screen and absurd on another, and these are instruments.
MONITOR = (232, 150)
BALL = 118

#: How far the contact ball reaches, in km. Past this a contact is drawn on
#: the rim rather than inside, which is what "further than this matters less"
#: looks like.
BALL_KM = 24.0


def _tint(name: str) -> QColor:
    return QColor(theme.tint(name))


def _panel(p, at: QRectF, title: str) -> None:
    """The frame every board sits in."""
    p.setBrush(QColor(4, 9, 12, 190))
    p.setPen(QPen(QColor(theme.LINE), 1))
    p.drawRect(at)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QColor(theme.INK3))
    p.setFont(QFont(theme.mono_family(), 8))
    p.drawText(QPointF(at.x() + 7, at.y() + 12), title.upper())


def draw(p, action, w: int, h: int, drill=None) -> None:
    """All three boards. `drill` is None outside the gunnery school."""
    monitor(p, action, w, h)
    ball(p, action, w, h)
    if drill is not None:
        directives(p, action, drill, w, h)


# ── the target monitor ─────────────────────────────────────────────────────

def monitor(p, action, w: int, h: int) -> None:
    """What the director is on, and what can be shot off it."""
    wide, tall = MONITOR
    at = QRectF(14, h - tall - 92, wide, tall)
    held = skirmish.marked(action)
    _panel(p, at, "target" if held is not None else "no target")
    if held is None:
        p.setPen(QColor(theme.INK3))
        p.setFont(QFont(theme.mono_family(), 9))
        p.drawText(QPointF(at.x() + 8, at.y() + 34), "Nothing locked.")
        p.drawText(QPointF(at.x() + 8, at.y() + 48), "Tab takes the next.")
        return
    got = skirmish.solution(action, held)
    ink = _tint("chloro" if not held.hostile else "warn")
    p.setPen(ink)
    p.setFont(QFont(theme.mono_family(), 10, QFont.Weight.Bold))
    p.drawText(QPointF(at.x() + 8, at.y() + 28), held.name[:26])
    p.setFont(QFont(theme.mono_family(), 8))
    p.setPen(QColor(theme.INK2))
    closing = -sum(a * b for a, b in zip(held.vel, held.at)) \
        / max(1e-6, held.range_km)
    p.drawText(QPointF(at.x() + 8, at.y() + 42),
               f"{held.kind}  ·  {got['range_km']:,.2f} km")
    p.drawText(QPointF(at.x() + 8, at.y() + 54),
               f"{closing * 1000:+,.0f} m/s  ·  lead {got['lead']:,.1f}°")
    # The hull bar, then every fitting under it.
    p.setPen(QColor(theme.INK3))
    p.drawText(QPointF(at.x() + 8, at.y() + 68), f"hull {held.share:.0%}")
    _meter(p, QRectF(at.x() + 64, at.y() + 62, wide - 74, 6), held.share,
           ink, "")
    row = at.y() + 84
    for piece in held.parts[:5]:
        shade = _tint("dim" if piece.dead else "lumen")
        p.setPen(shade)
        p.setFont(QFont(theme.mono_family(), 8))
        name = piece.name if not piece.dead else f"{piece.name} — gone"
        p.drawText(QPointF(at.x() + 8, row), name[:22])
        _meter(p, QRectF(at.x() + wide - 74, row - 7, 62, 5), piece.share,
               shade, "")
        row += 12
    if not held.parts:
        p.setPen(QColor(theme.INK3))
        p.drawText(QPointF(at.x() + 8, row), "No fittings to take off it.")


def _meter(p, at: QRectF, share: float, ink: QColor, label: str) -> None:
    p.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 100), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(at)
    p.setBrush(ink)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(at.x(), at.y(), at.width() * max(0.0, min(1.0, share)),
                      at.height()))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if label:
        p.setPen(QColor(theme.INK3))
        p.setFont(QFont(theme.mono_family(), 8))
        p.drawText(QPointF(at.x() + at.width() + 6, at.y() + 6), label)


# ── the contact ball ───────────────────────────────────────────────────────

def ball(p, action, w: int, h: int) -> None:
    """Everything around the hull, including the half you are not facing.

    An oblique sphere: the ring is the hull's own plane, a contact's angle
    round it is its bearing, its distance from the middle is its range, and
    it is squashed vertically so *above* and *below* read without a second
    gauge. The bore is drawn as a spoke, so "where am I looking" is on the
    same picture as "where is everything".
    """
    span = BALL
    cx, cy = w - span - 22, h - span - 30
    mid = QPointF(cx + span / 2, cy + span / 2)
    radius = span * 0.44
    p.setBrush(QColor(4, 9, 12, 180))
    p.setPen(QPen(QColor(theme.LINE), 1))
    p.drawEllipse(mid, radius, radius)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(theme.LINE2), 1))
    p.drawEllipse(mid, radius, radius * 0.42)
    p.drawLine(QPointF(mid.x() - radius, mid.y()),
               QPointF(mid.x() + radius, mid.y()))
    # The hull's nose, so the ring has a front.
    p.setPen(QColor(theme.INK3))
    p.setFont(QFont(theme.mono_family(), 7))
    p.drawText(QPointF(mid.x() - 4, cy - 2), "BOW")

    turret = action.turret
    bore = math.radians(turret.bearing)
    p.setPen(QPen(_tint("chloro"), 1.4))
    p.drawLine(mid, QPointF(mid.x() + math.sin(bore) * radius,
                            mid.y() - math.cos(bore) * radius * 0.92))
    for contact in skirmish.live(action):
        bearing, elevation, span_km = gunsight.polar(contact.at)
        share = min(1.0, span_km / BALL_KM)
        rad = math.radians(bearing)
        x = mid.x() + math.sin(rad) * radius * share
        y = mid.y() - math.cos(rad) * radius * share * 0.92
        rise = math.sin(math.radians(elevation)) * radius * 0.30
        ink = _tint("bad" if contact.behaviour == "home"
                    else ("chloro" if not contact.hostile else "warn"))
        # A stalk to the plane, which is how an oblique plot says "above".
        thin = QColor(ink)
        thin.setAlpha(110)
        p.setPen(QPen(thin, 1.0))
        p.drawLine(QPointF(x, y), QPointF(x, y - rise))
        p.setBrush(ink)
        p.setPen(Qt.PenStyle.NoPen)
        size = 3.4 if contact.id == turret.locked else 2.2
        p.drawEllipse(QPointF(x, y - rise), size, size)
    p.setBrush(Qt.BrushStyle.NoBrush)


# ── the directive list ─────────────────────────────────────────────────────

def directives(p, action, drill, w: int, h: int) -> None:
    """What was asked for, ticking itself off while the gunner works."""
    from ..sim import drills as drill_sim
    rows = drill_sim.directives(action, drill)
    wide = 250
    at = QRectF(w - wide - 16, 40, wide, 22 + 15 * len(rows))
    _panel(p, at, "directives")
    p.setFont(QFont(theme.mono_family(), 8))
    row = at.y() + 28
    for line in rows:
        if line["done"]:
            mark, tint = "✓", "chloro"
        elif line["failed"]:
            mark, tint = "✗", "bad"
        else:
            mark, tint = "·", "dim" if not line["primary"] else "ink"
        p.setPen(_tint(tint))
        say = line["say"] if line["primary"] else f"({line['say']})"
        p.drawText(QPointF(at.x() + 8, row), f"{mark} {say}"[:34])
        p.setPen(QColor(theme.INK3))
        p.drawText(QPointF(at.x() + wide - 62, row), line["how"][:10])
        row += 15


def clock(p, action, w: int, h: int, drill=None) -> None:
    """The action's own clock and its tally, along the top."""
    stand = skirmish.standing(action)
    said = f"{action.clock:,.0f} s"
    if drill is not None and drill.seconds:
        said = f"{action.clock:,.0f} / {drill.seconds:,.0f} s"
    said += (f"   ·   {stand['hostiles']} hostile"
             f"   ·   {stand['hits']}/{stand['fired']} landed")
    if stand["seekers"]:
        said += f"   ·   {stand['seekers']} inbound"
    p.setPen(QColor(theme.INK2))
    p.setFont(QFont(theme.mono_family(), 9))
    p.drawText(QRectF(0, 6, w - 16, 14), Qt.AlignmentFlag.AlignRight, said)
