"""The marks a contact leaves on a picture: the flash, what flies off, the cracks.

Every function here takes a painter, a point and an age, and draws one thing.
None of them knows what a `Conn` is, what a second is, or which window it is
painting into — `ui/effects.py` owns the clock and `ui/effect_paint.py` owns
the frame. This is the hand.

**Everything is deterministic in a seed.** A repaint is not a new event: the
six camera thumbnails, the main screen and the outside view all draw the same
collision in the same beat, and if the sparks were drawn from a fresh random
number each time the eight pictures would disagree and the one picture would
shimmer. `core/rng.RNG` takes a string and gives the same stream every time —
and, critically, it is *not* `game.rng`, which would advance the chronicle's
own seed once per repaint. This project has been bitten by exactly that in the
docking instrument and again in the starfield.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen, QPolygonF, QRadialGradient

from ..core.rng import RNG

#: How the sparks and the debris are thrown, as a share of the frame's
#: shorter side: how far the fastest one gets by the time it is gone.
SPARK_REACH = 0.42
DEBRIS_REACH = 0.30

#: The most sparks and the most pieces a contact throws. Both scale down
#: with the power of it, so a scrape throws three and a crash throws forty.
SPARKS_MOST = 40
DEBRIS_MOST = 16

#: How far a fracture runs across the glass at full power, as a share of the
#: frame diagonal, and how many there may be.
CRACK_REACH = 0.62
CRACKS_MOST = 11


def _fade(colour: QColor, alpha: float) -> QColor:
    """The same colour at a given opacity, 0..1. Clamped, because an alpha
    worked out from a decay curve can land a hair outside and Qt throws."""
    out = QColor(colour)
    out.setAlpha(int(max(0.0, min(1.0, alpha)) * 255))
    return out


def ease(age: float) -> float:
    """Fast at first, slow at the end — what a blast front actually does."""
    return 1.0 - (1.0 - min(1.0, max(0.0, age))) ** 2.4


def flash(p, at: QPointF, radius: float, colour: QColor,
          core: str = "#fffdf2") -> None:
    """The bloom at the point of contact: white in the middle, its own colour
    at the edge, nothing beyond it.

    A gradient rather than a disc, because the thing a real flash does to an
    eye is wash out what is behind it near the middle and leave the edges
    readable — a flat disc just hides the target the pilot is trying to see.
    """
    if radius <= 0.5:
        return
    glow = QRadialGradient(at, radius)
    glow.setColorAt(0.0, QColor(core))
    glow.setColorAt(0.30, _fade(colour, 0.85))
    glow.setColorAt(1.0, _fade(colour, 0.0))
    p.setBrush(glow)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(at, radius, radius)


def ring(p, at: QPointF, radius: float, colour: QColor, alpha: float,
         width: float = 2.0) -> None:
    """The blast front, as the circle it is. Thin, so it reads as a front
    rather than as a second flash."""
    if radius <= 1.0 or alpha <= 0.01:
        return
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(_fade(colour, alpha), max(0.6, width)))
    p.drawEllipse(at, radius, radius)


def sparks(p, at: QPointF, seed: str, power: float, age: float,
           colour: QColor, span: float) -> None:
    """What comes off two structures meeting: streaks, thrown and dying.

    Drawn as *streaks* rather than points because that is what the eye reads
    as speed. Each one is a segment from where it is now back toward where it
    came from, so a fast one is long and a slow one is a dot, without any of
    them being told how fast it is.
    """
    count = max(3, int(SPARKS_MOST * power))
    if age >= 1.0 or count <= 0:
        return
    rng = RNG(f"{seed}:sparks")
    reach = span * SPARK_REACH
    gone = ease(age)
    left = (1.0 - age) ** 1.6
    for _ in range(count):
        angle = rng.float(0.0, math.tau)
        pace = rng.float(0.25, 1.0)
        bright = rng.float(0.4, 1.0)
        out = reach * pace * gone
        tail = max(1.5, reach * pace * 0.16 * (1.0 - age))
        ux, uy = math.cos(angle), math.sin(angle)
        head = QPointF(at.x() + ux * out, at.y() + uy * out)
        back = QPointF(head.x() - ux * tail, head.y() - uy * tail)
        p.setPen(QPen(_fade(colour, left * bright), 1.0 + bright))
        p.drawLine(back, head)


def debris(p, at: QPointF, seed: str, power: float, age: float,
           colour: QColor, span: float) -> None:
    """Pieces of the two of you, tumbling away and going dark.

    Slower than the sparks and longer-lived, because that is the difference
    between a spark and a piece of hull, and the picture wants both: the
    sparks say "that was violent" in the first tenth of a second and these say
    "and something came off" for the rest of it.
    """
    count = max(2, int(DEBRIS_MOST * power))
    if age >= 1.0:
        return
    rng = RNG(f"{seed}:debris")
    reach = span * DEBRIS_REACH
    gone = ease(age) * 0.85 + age * 0.15
    left = (1.0 - age) ** 1.2
    for _ in range(count):
        angle = rng.float(0.0, math.tau)
        pace = rng.float(0.2, 1.0)
        size = span * rng.float(0.006, 0.019) * (0.5 + power)
        spin = rng.float(-6.0, 6.0)
        out = reach * pace * gone
        cx = at.x() + math.cos(angle) * out
        cy = at.y() + math.sin(angle) * out
        turn = spin * age
        corners = []
        for step in range(4):
            a = turn + step * math.pi / 2.0 + 0.35
            corners.append(QPointF(cx + math.cos(a) * size,
                                   cy + math.sin(a) * size * 0.7))
        p.setBrush(_fade(colour, left * 0.55))
        p.setPen(QPen(_fade(colour, left), 0.9))
        p.drawPolygon(QPolygonF(corners))


def cracks(p, at: QPointF, seed: str, power: float, age: float, w: int, h: int,
           colour: QColor) -> None:
    """Fractures running out from where it hit, on the camera's own glass.

    Drawn from the contact point so the damage has a direction: a hull struck
    on the beam cracks the beam camera at the edge the blow came from, and
    the pilot can read *where* from the picture rather than from a sentence.
    Not a shatter — a shattered screen is a screen you cannot fly on, and the
    point of this is to be flown on while it is there.
    """
    count = max(3, int(CRACKS_MOST * power))
    span = math.hypot(w, h) * CRACK_REACH * (0.45 + 0.55 * power)
    # Snaps into place, then stays: a fracture does not grow back out.
    grown = min(1.0, age / 0.14) if age < 0.14 else 1.0
    left = 1.0 if age < 0.3 else max(0.18, 1.0 - (age - 0.3) / 0.7)
    rng = RNG(f"{seed}:cracks")
    for _ in range(count):
        angle = rng.float(0.0, math.tau)
        run = span * rng.float(0.35, 1.0) * grown
        steps = 5
        point = QPointF(at.x(), at.y())
        p.setPen(QPen(_fade(colour, 0.55 * left), 1.4))
        for step in range(steps):
            angle += rng.float(-0.38, 0.38)
            leg = run / steps
            nxt = QPointF(point.x() + math.cos(angle) * leg,
                          point.y() + math.sin(angle) * leg)
            p.drawLine(point, nxt)
            # One branch per fracture, half way along. More than one and the
            # glass reads as frosted rather than cracked.
            if step == 2:
                off = angle + rng.float(-1.1, 1.1)
                p.setPen(QPen(_fade(colour, 0.30 * left), 1.0))
                p.drawLine(nxt, QPointF(nxt.x() + math.cos(off) * leg * 0.8,
                                        nxt.y() + math.sin(off) * leg * 0.8))
                p.setPen(QPen(_fade(colour, 0.55 * left), 1.4))
            point = nxt


def lines_across(p, ship: QPointF, berth: QPointF, age: float,
                 colour: QColor) -> None:
    """Mooring lines going over and coming taut: a berthing, as an event.

    Three of them, thrown one after another, each sagging when it lands and
    straightening as it takes the strain. It is the one moment in the game
    where the ship stops being a dot beside a structure and becomes attached
    to it, and until now it was the word "Alongside" in a status line.
    """
    if age >= 1.0:
        return
    for index in range(3):
        start = index * 0.16
        if age < start:
            continue
        taut = min(1.0, (age - start) / 0.34)
        left = 1.0 - max(0.0, (age - 0.6) / 0.4)
        # The line runs from a point a little off the hull each time, so the
        # three do not lie on top of one another.
        offset = (index - 1) * 9.0
        frm = QPointF(ship.x() + offset, ship.y() + offset * 0.4)
        sag = (1.0 - taut) * 26.0
        mid = QPointF((frm.x() + berth.x()) / 2.0,
                      (frm.y() + berth.y()) / 2.0 + sag)
        p.setPen(QPen(_fade(colour, 0.85 * left), 1.0 + taut))
        last = frm
        for step in range(1, 9):
            t = step / 8.0
            inv = 1.0 - t
            point = QPointF(
                inv * inv * frm.x() + 2 * inv * t * mid.x() + t * t * berth.x(),
                inv * inv * frm.y() + 2 * inv * t * mid.y() + t * t * berth.y())
            p.drawLine(last, point)
            last = point
        if taut >= 1.0:
            p.setBrush(_fade(colour, 0.9 * left))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(berth, 2.4, 2.4)
            p.setBrush(Qt.BrushStyle.NoBrush)


def edge_arc(p, w: int, h: int, angle: float, alpha: float,
             colour: QColor) -> None:
    """Which way the blow came from, when it came from outside the picture.

    The thing every first-person view needs and this one did not have:
    photographed, a hull struck a Fleet Hub at 55 m/s with the nose 180° off
    and the structure in the *aft* camera — so the pilot's own window showed
    a starfield, a crosshair and no hint that anything had happened at all.
    An arc on the rim, in the direction of it, is the whole fix.
    """
    if alpha <= 0.02:
        return
    cx, cy = w / 2.0, h / 2.0
    p.setBrush(Qt.BrushStyle.NoBrush)
    # Qt measures arcs in sixteenths of a degree, counter-clockwise, from
    # three o'clock — and the screen's y runs down, so the angle is negated.
    start = int(math.degrees(-angle) * 16) - 26 * 16
    # Three arcs rather than one: a single stroke at this size reads as a
    # stray curve in the picture, and the thing it has to say — *the blow
    # came from over there* — is the one thing a pilot looking at the wrong
    # camera has to be able to read without hunting for it.
    for spread, weight, share in ((0.40, 11.0, 0.22), (0.44, 6.0, 0.55),
                                  (0.47, 2.0, 0.85)):
        radius = min(w, h) * spread
        pen = QPen(_fade(colour, alpha * share), weight)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawArc(int(cx - radius), int(cy - radius),
                  int(radius * 2), int(radius * 2), start, 52 * 16)
