"""Painting what just happened, on the picture the pilot is already looking at.

Two doors, because there are two kinds of picture in the flight deck and a
contact has to land on both:

- **`over`** — a first-person camera (`ui/viewport.py`). The flash goes where
  the thing actually is, which is often *not in this window*, so a blow from
  outside the frame is marked on the rim instead. Six thumbnails and a main
  screen call this every frame and must agree with each other to the pixel.
- **`plot`** — the outside view (`ui/approach_window.py`), where the two
  objects are drawn together. Here the contact has a place in the picture
  rather than a bearing, and what the *other* one took can be shown: a hub
  shoved off station is a fact the game has modelled since `sim/impulse` and
  never drawn.

The timing is `ui/effects.py`'s and the marks are `ui/effect_marks.py`'s. What
is decided here is the composition: what goes over what, what a thumbnail is
too small to be worth, and where the words go.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen, QRadialGradient

from . import effect_marks as marks
from ..sim import shock as shock_sim
from . import effects, theme
from .viewport_math import project

#: How big the bloom gets at full power, as a share of the frame's shorter
#: side, and how big the blast front gets. The front outruns the bloom, which
#: is what makes the pair read as an explosion rather than as a dot.
FLASH_SHARE = 0.26
FRONT_SHARE = 0.55

#: Under this many pixels across, a picture is a thumbnail: it gets the wash,
#: the rim mark and nothing else. Words and fractures on a 120 px feed are
#: noise, and there are six of them in a row.
COMPACT_UNDER = 200

#: The tint each kind throws, as a theme name. Warm for anything that hurt,
#: cool for anything that went well.
SPARK_TINT = {
    "collision": "osteo", "aground": "osteo", "ditched": "osteo",
    "scrape": "osteo", "ward": "warn", "cut": "warn", "gunfire": "warn",
    "down": "chloro", "alongside": "chloro", "orbit": "lumen",
    "captured": "lumen",
}

#: What the debris is made of, as a colour: hull, lit along one edge.
HULL_GREY = "#9aa9a2"


def _tint(name: str) -> QColor:
    return QColor(theme.tint(name))


def _spot(bearing, cam, w: int, h: int):
    """Where a bearing lands in this camera, and whether it is in the frame.

    Returns `(QPointF, inside)`. A bearing behind the lens has no point at
    all, and the caller marks the rim instead.
    """
    got = project(bearing, cam, w, h)
    if got is None:
        return None, False
    x, y, _ahead = got
    return QPointF(x, y), (0 <= x < w and 0 <= y < h)


def _rim_angle(bearing, cam) -> float:
    """Which way round the rim a bearing lies, in screen radians.

    Worked out in the camera's own axes rather than from a projected point,
    because a point behind the lens projects to nothing and to the *wrong
    side* if the sign is ignored — which is how a hit from dead astern comes
    to be marked dead ahead.
    """
    _fwd, right, up = cam
    across = sum(a * b for a, b in zip(bearing, right))
    upward = sum(a * b for a, b in zip(bearing, up))
    if abs(across) < 1e-9 and abs(upward) < 1e-9:
        return 0.0
    return math.atan2(-upward, across)      # screen y runs down


def over(p, conn, cam, w: int, h: int) -> None:
    """Everything live, on one camera's picture. Draws nothing when nothing
    has happened, which is almost always."""
    small = min(w, h) < COMPACT_UNDER
    now = effects.clock()
    got = effects.live(now)
    if got:
        span = float(min(w, h))
        for effect in got:
            _one(p, effect, cam, w, h, span, now, small)
        wash(p, w, h, now=now)
        if not small:
            _fractures(p, got, cam, w, h, now)
            _banner(p, w, h, now)
    if not small:
        _alarm(p, conn, w, h, now)


def _one(p, effect, cam, w: int, h: int, span: float, now: float,
         small: bool) -> None:
    """One effect, at the bearing it happened on."""
    hit = effect.shock
    age = effect.age(now)
    power = effect.power
    colour = _tint(SPARK_TINT.get(hit.kind, "osteo"))
    at, inside = _spot(hit.bearing, cam, w, h)
    if at is None or not inside:
        # Off the glass: the rim says which way, and nothing else is drawn —
        # a flash painted at a projected point behind the lens lands in the
        # wrong half of the picture and tells the pilot a lie.
        marks.edge_arc(p, w, h, _rim_angle(hit.bearing, cam),
                       (1.0 - age) * (0.35 + 0.55 * power), colour)
        return
    if hit.kind in ("alongside", "captured"):
        _berthing(p, at, hit, cam, w, h, age, colour, small)
        return
    if hit.kind in ("orbit", "down"):
        _arrival(p, at, w, h, age, colour)
        return
    reach = span * FLASH_SHARE * (0.25 + 0.75 * power)
    if age < 0.34:
        marks.flash(p, at, reach * (1.0 - age / 0.34) ** 0.4, colour)
    marks.ring(p, at, span * FRONT_SHARE * power * marks.ease(age),
               colour, (1.0 - age) ** 2 * 0.8, 3.0 * (1.0 - age))
    marks.sparks(p, at, hit.seed, power, age, colour, span)
    if hit.violent and not small:
        marks.debris(p, at, hit.seed, power, age, QColor(HULL_GREY), span)


def _arrival(p, at: QPointF, w: int, h: int, age: float,
             colour: QColor) -> None:
    """Getting somewhere on purpose: two rings, one closing and one opening.

    Not the impact treatment with the numbers turned down. Sparks and tumbling
    debris say *something came apart*, and nothing came apart — an orbit
    established is the drive being allowed to rest, and it should look like
    arriving rather than like a small crash.
    """
    span = float(min(w, h))
    marks.ring(p, at, span * 0.30 * (1.0 - 0.72 * marks.ease(age)), colour,
               (1.0 - age) * 0.75, 1.6)
    marks.ring(p, at, span * 0.11 * marks.ease(age), colour,
               (1.0 - age) ** 2 * 0.7, 1.2)
    marks.flash(p, at, span * 0.05 * (1.0 - age), colour)


def _berthing(p, at: QPointF, hit, cam, w: int, h: int, age: float,
              colour: QColor, small: bool) -> None:
    """Coming alongside: a soft pulse at the fitting, and the lines going over.

    The lines run from the bottom of the frame, which is where the hull is in
    a first-person view — the camera is *on* her, so she has no place in her
    own picture and pretending otherwise would draw a ship in front of the
    window she is looking out of.
    """
    marks.ring(p, at, min(w, h) * 0.10 * (1.0 - (1.0 - age) ** 2),
               colour, (1.0 - age) * 0.7, 1.6)
    if small:
        return
    marks.lines_across(p, QPointF(w * 0.5, h * 0.94), at, age, colour)


#: Where the rim wash starts, as a share of the way out from the middle of
#: the frame. Inside this the picture is untouched — which is the whole point
#: of a vignette over a flat fill: the instruments, the structure and the
#: controls stay readable while the edge of vision says you have been hit.
VIGNETTE_FROM = 0.38


def wash(p, w: int, h: int, scene: str = shock_sim.FLIGHT,
         now: float | None = None) -> None:
    """The whole-frame wash: the flash, and then the colour of the news.

    Two different things wearing one name. The flash is flat, because a flash
    *is* flat — for a tenth of a second the eye has nothing else. What
    follows is a vignette at the rim, because a filter over the whole picture
    is not a reaction to being hit, it is a broken screen.
    """
    now = effects.clock() if now is None else now
    name, alpha = effects.veil(now, scene)
    if alpha <= 0.01:
        return
    if name == "ink":
        wash = QColor(theme.INK)
        wash.setAlpha(int(min(1.0, alpha) * 255))
        p.fillRect(0, 0, w, h, wash)
        return
    tint = QColor(theme.tint(name))
    span = math.hypot(w, h) / 2.0
    glow = QRadialGradient(QPointF(w / 2.0, h / 2.0), span)
    glow.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), 0))
    glow.setColorAt(VIGNETTE_FROM,
                    QColor(tint.red(), tint.green(), tint.blue(), 0))
    glow.setColorAt(1.0, QColor(tint.red(), tint.green(), tint.blue(),
                                int(min(1.0, alpha) * 255)))
    p.setBrush(glow)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(0, 0, w, h)


def _fractures(p, got, cam, w: int, h: int, now: float) -> None:
    """The cracks, over everything, because the glass is in front of it all."""
    for effect in got:
        hit = effect.shock
        if not hit.cracks:
            continue
        at, inside = _spot(hit.bearing, cam, w, h)
        if at is None or not inside:
            # It hit somewhere this camera cannot see, but the glass is the
            # ship's and the ship was struck: the fractures start at the rim
            # on the side it came from.
            angle = _rim_angle(hit.bearing, cam)
            at = QPointF(w / 2.0 + math.cos(angle) * w * 0.42,
                         h / 2.0 + math.sin(angle) * h * 0.42)
        marks.cracks(p, at, hit.seed, effect.power, effect.age(now), w, h,
                     QColor(theme.INK))


#: Where the words sit, as a share of the way down the frame. Low, and
#: measured: at a third of the way down they cut across the structure that
#: was hit — photographed on a 6 m/s bump into a Fleet Hub, the caption lay
#: over the bloom it was captioning. The top belongs to the camera's name and
#: the target's, and the middle is where the pilot is looking.
BANNER_DOWN = 0.74


def _banner(p, w: int, h: int, now: float, down: float = BANNER_DOWN) -> None:
    """The words, large, in the middle of the picture.

    Large on purpose. What this replaces is a nine-point italic line along the
    bottom of the window, which is where the game put "COLLISION — Fleet Hub
    at 55 m/s" — the end of a starting chronicle, in the smallest type on the
    screen.
    """
    head, line, fade = effects.banner(now)
    if not head or fade <= 0.02:
        return
    band = QRectF(0, h * down, w, 58)
    shade = QColor(4, 8, 11)
    shade.setAlpha(int(150 * fade))
    p.fillRect(band, shade)
    warm = "bad" if "COLLISION" in head or "AGROUND" in head else "chloro"
    if head.startswith(("SCRAPED", "CUTTING", "UNDER", "PUT")):
        warm = "osteo"
    ink = _tint(warm)
    ink.setAlpha(int(255 * fade))
    # A rule top and bottom, in the news's own colour: it is then plainly a
    # thing the interface put there, rather than a grey stripe across the
    # window that reads as a fault in the picture.
    rule = QColor(ink)
    rule.setAlpha(int(110 * fade))
    p.setPen(QPen(rule, 1.0))
    p.drawLine(QPointF(0, band.top()), QPointF(w, band.top()))
    p.drawLine(QPointF(0, band.bottom()), QPointF(w, band.bottom()))
    p.setPen(QPen(ink, 1.0))
    p.setFont(QFont(theme.mono_family(), 15, QFont.Weight.Bold))
    p.drawText(QRectF(0, h * down + 4, w, 24),
               Qt.AlignmentFlag.AlignHCenter, head)
    if line:
        quiet = QColor(theme.INK2)
        quiet.setAlpha(int(230 * fade))
        p.setPen(quiet)
        p.setFont(QFont(theme.mono_family(), 10))
        p.drawText(QRectF(0, h * down + 30, w, 20),
                   Qt.AlignmentFlag.AlignHCenter, line)


def _alarm(p, conn, w: int, h: int, now: float) -> None:
    """A border that throbs while something is still in the way.

    Not an event — a standing condition, and the difference matters: a crash
    is over and this is not. `sim/collision` already says how bad it is and
    `ui/viewport_hud` rings the thing itself; what was missing was a signal
    the pilot cannot miss while looking at the wrong part of the frame.
    """
    if conn is None or conn.over or conn.landed:
        return
    from . import viewport_hud
    hazard = viewport_hud.world(conn).get("hazard")
    level = getattr(hazard, "level", "")
    if level not in ("brake", "imminent"):
        return
    hard = level == "imminent"
    beat = effects.pulse(now, 2.4 if hard else 1.3)
    ink = _tint("bad" if hard else "osteo")
    ink.setAlpha(int((70 + 150 * beat) * (1.0 if hard else 0.6)))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(ink, 4.0 if hard else 2.5))
    p.drawRect(2, 2, w - 5, h - 5)


# ── the outside view ───────────────────────────────────────────────────────

def plot(p, camera, w: int, h: int) -> None:
    """Everything live, on the picture that draws both objects together.

    The one view that can show the *other* side of a collision: `sim/impulse`
    has worked out what the struck structure took and how hard it was shoved
    since the day it was written, `sim/knock` carries it out to the sector,
    and no screen in the game had ever drawn it.
    """
    now = effects.clock()
    got = effects.live(now)
    if not got:
        return
    span = float(min(w, h))
    for effect in got:
        hit = effect.shock
        spot = camera.project(tuple(hit.at))
        if spot is None:
            continue
        at, _ahead = spot
        age, power = effect.age(now), effect.power
        colour = _tint(SPARK_TINT.get(hit.kind, "osteo"))
        if age < 0.34:
            marks.flash(p, at, span * 0.14 * (0.3 + 0.7 * power)
                        * (1.0 - age / 0.34) ** 0.4, colour)
        marks.ring(p, at, span * 0.34 * power * marks.ease(age), colour,
                   (1.0 - age) ** 2 * 0.8, 2.4 * (1.0 - age))
        marks.sparks(p, at, hit.seed, power, age, colour, span)
        if hit.violent:
            marks.debris(p, at, hit.seed, power, age, QColor(HULL_GREY), span)
        _missed(p, camera, hit, at, age)
        _shove(p, camera, hit, age)
    wash(p, w, h, now=now)
    # Low, because the middle of this picture is the structure that was hit
    # and the words would cover the one thing worth looking at.
    _banner(p, w, h, now, down=0.68)


def _missed(p, camera, hit, at, age: float) -> None:
    """Where she hit, against where she was going: the berth, and the gap.

    The log has said "772 m from mast 4" since `sim/moorings` learned to
    answer it, and a distance in a sentence is a distance nobody pictures.
    Drawn, it is the whole lesson of the approach in one line: the mast was
    *there*, and the frames went in *here*.

    No label on it. The banner under the picture already says "mast 4
    missed", and at a five-kilometre frame the structure is eighty pixels
    across — photographed, three captions in that space wrote over each
    other and over the berth names the window already draws.
    """
    if hit.kind not in ("collision", "scrape") or not hit.where or age >= 1.0:
        return
    berth = next((spot for name, spot in hit.berths if name == hit.where), None)
    if berth is None:
        return
    to = camera.project(tuple(berth))
    if to is None:
        return
    end, _ahead = to
    ink = _tint("lumen")
    ink.setAlpha(int(200 * (1.0 - age)))
    p.setPen(QPen(ink, 1.0, Qt.PenStyle.DashLine))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(at, end)
    p.drawEllipse(end, 5.0, 5.0)


def _shove(p, camera, hit, age: float) -> None:
    """What the struck thing was pushed to, drawn as the push it was.

    An arrow out of the structure's centre along the line of the blow, with
    the figure on it. It is the answer to "did that matter to them" — and for
    a quay used as a backstop the answer is yes: 1.7 m/s, and 649 km off
    station a fortnight later (`sim/knock`). The game has worked this out
    since `sim/impulse` was written and no screen had ever drawn it.

    The figure itself is in the banner; this is the picture of it, and a
    second copy of the number beside the arrow was one caption too many in a
    frame this size.
    """
    if hit.struck_dv < 0.01 or age >= 1.0:
        return
    # Scaled off the structure itself — the contact point is on its skin, so
    # its own distance is the one measure of "how big is this thing" the
    # shock carries — and started clear of it, because an arrow drawn from
    # the centre of a solid is an arrow drawn underneath it.
    skin = math.dist(hit.at, (0.0, 0.0, 0.0)) or 1.0
    near = camera.project(tuple(c * skin * 1.25 for c in hit.bearing))
    to = camera.project(tuple(c * skin * 6.0 for c in hit.bearing))
    if to is None or near is None:
        return
    start, _from = near
    end, _far = to
    ink = _tint("warn")
    ink.setAlpha(int(230 * (1.0 - age) ** 0.7))
    p.setPen(QPen(ink, 2.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawLine(start, end)
    angle = math.atan2(end.y() - start.y(), end.x() - start.x())
    for side in (2.6, -2.6):
        p.drawLine(end, QPointF(end.x() + math.cos(angle + side) * 11.0,
                                end.y() + math.sin(angle + side) * 11.0))
