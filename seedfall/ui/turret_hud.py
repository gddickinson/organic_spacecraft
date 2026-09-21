"""The glass in front of a gunner: the bore, the pip, the brackets, the gauges.

Drawn over `ui/turret_scene.py`'s picture, and it holds no state of its own —
everything here is a read of the action, so the HUD cannot say one thing while
the gun does another.

**The vocabulary is FreeSpace 2's**, because that game settled it and nothing
since has improved on it. Four pieces do most of the work:

- **The reticle** is where the gun is pointing, dead centre, always.
- **The lead pip** is where to point it. They are *different marks*, and
  learning to put the pip on the target rather than the reticle is the whole
  of gunnery — see `sim/gunsight.lead_point`.
- **A bracket** round everything the sight holds, in the colour of whose it
  is, so a consort in your arc reads as a consort before you pull.
- **A rim arc** for anything worth shooting that is outside the window,
  because a gunner with a 27° lens spends most of an action looking at the
  wrong part of the sky.

The target monitor, the contact ball and the directive list are the other
half — `ui/turret_panels.py`.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPen

from ..sim import gunsight, skirmish, turret as turret_sim
from . import theme

#: How big the bracket round a contact may get, and the least it may be. A
#: bracket that shrank to the thing's true angular size would vanish on a
#: missile at eight kilometres, which is the one it matters most on.
BRACKET_MIN = 9.0
BRACKET_MAX = 90.0

#: Inside this many degrees of the bore, the lead pip is *on* the reticle and
#: drawing both is two marks on one spot. Past it they separate and the
#: gunner has something to do.
PIP_MERGE = 0.6

#: Where the rim marks for off-screen contacts sit, as a share of the frame.
RIM = 0.44


def draw(p, action, spots: dict, w: int, h: int) -> None:
    """Everything on the glass. `spots` is `turret_scene.draw`'s answer."""
    _brackets(p, action, spots, w, h)
    _rim(p, action, spots, w, h)
    _reticle(p, action, w, h)
    _pip(p, action, w, h)
    _arc_stops(p, action, w, h)
    _gauges(p, action, w, h)
    _warnings(p, action, w, h)


def _tint(name: str) -> QColor:
    return QColor(theme.tint(name))


def _bracket_span(spot) -> float:
    return max(BRACKET_MIN, min(BRACKET_MAX, spot["radius"] * 1.7))


def _brackets(p, action, spots: dict, w: int, h: int) -> None:
    """Corner brackets round every contact in the window, named and ranged."""
    locked = action.turret.locked
    p.setFont(QFont(theme.mono_family(), 8))
    for cid, spot in spots.items():
        contact = spot["contact"]
        at, span = spot["at"], _bracket_span(spot)
        if not (-span < at.x() < w + span and -span < at.y() < h + span):
            continue
        held = cid == locked
        ink = _tint(spot["tint"])
        ink.setAlpha(255 if held else 150)
        p.setPen(QPen(ink, 2.0 if held else 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        arm = span * 0.34
        for sx in (-1, 1):
            for sy in (-1, 1):
                cx, cy = at.x() + sx * span, at.y() + sy * span
                p.drawLine(QPointF(cx, cy), QPointF(cx - sx * arm, cy))
                p.drawLine(QPointF(cx, cy), QPointF(cx, cy - sy * arm))
        if held or span > 16.0:
            p.setPen(ink)
            p.drawText(QPointF(at.x() + span + 9, at.y() - span - 3),
                       contact.name)
            p.drawText(QPointF(at.x() + span + 9, at.y() - span + 8),
                       f"{contact.range_km:,.1f} km")
        if contact.share < 1.0:
            _hull_pip(p, at, span, contact.share, ink)


def _hull_pip(p, at: QPointF, span: float, share: float, ink: QColor) -> None:
    """A little bar under a bracket: how much of it is left."""
    wide = span * 1.4
    left = at.x() - wide / 2
    top = at.y() + span + 4
    p.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 90), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(left, top, wide, 3))
    p.setBrush(ink)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(left, top, wide * share, 3))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _rim(p, action, spots: dict, w: int, h: int) -> None:
    """Which way to swing for what the lens cannot hold.

    A gunner's window is 27° of a sphere. Without this, everything that is
    not already in front of them is invisible and the only way to find a
    contact is to sweep — which is what the drills teach, and not what an
    action leaves time for.
    """
    turret = action.turret
    cx, cy = w / 2.0, h / 2.0
    radius = min(w, h) * RIM
    for contact in skirmish.live(action):
        spot = spots.get(contact.id)
        if spot is not None:
            at = spot["at"]
            if (spot["ahead"] > 0 and 0 <= at.x() < w and 0 <= at.y() < h):
                continue
        bearing, elevation, _r = gunsight.polar(contact.at)
        across = gunsight.delta(turret.bearing, bearing)
        up = elevation - turret.elevation
        angle = math.atan2(-up, across)
        ink = _tint("bad" if contact.behaviour == "home"
                    else ("chloro" if not contact.hostile else "warn"))
        ink.setAlpha(190 if contact.hostile else 130)
        pen = QPen(ink, 3.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        start = int(math.degrees(-angle) * 16) - 7 * 16
        p.drawArc(int(cx - radius), int(cy - radius),
                  int(radius * 2), int(radius * 2), start, 14 * 16)


def _reticle(p, action, w: int, h: int) -> None:
    """Where the gun is pointing: the one mark that never moves."""
    cx, cy = w / 2.0, h / 2.0
    ok, _why = turret_sim.can_fire(action.turret)
    ink = _tint("chloro" if ok else "osteo")
    ink.setAlpha(210)
    p.setPen(QPen(ink, 1.4))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(cx, cy), 13, 13)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        p.drawLine(QPointF(cx + dx * 20, cy + dy * 20),
                   QPointF(cx + dx * 14, cy + dy * 14))
    p.setPen(QPen(ink, 1.0))
    p.drawPoint(QPointF(cx, cy))


def _pip(p, action, w: int, h: int) -> None:
    """The lead pip: where to put the reticle so the round arrives with it.

    Only for what the sight is actually on, and only when the gun would
    reach — a pip on something out of range is an instruction to waste
    ammunition.
    """
    mark = skirmish.aim_now(action)
    if mark is None:
        return
    turret = action.turret
    across = gunsight.delta(turret.bearing, mark["aim"][0])
    up = mark["aim"][1] - turret.elevation
    if abs(across) < PIP_MERGE and abs(up) < PIP_MERGE:
        return
    focal = (min(w, h) * 0.5) / math.tan(
        __import__("seedfall.ui.turret_scene", fromlist=["x"]).HALF_FOV)
    x = w / 2.0 + math.tan(math.radians(across)) * focal
    y = h / 2.0 - math.tan(math.radians(up)) * focal
    if not (-40 < x < w + 40 and -40 < y < h + 40):
        return
    ink = _tint("lumen" if mark["in_reach"] else "dim")
    p.setPen(QPen(ink, 1.6))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawEllipse(QPointF(x, y), 6, 6)
    p.drawLine(QPointF(x - 10, y), QPointF(x - 7, y))
    p.drawLine(QPointF(x + 7, y), QPointF(x + 10, y))
    # A thread from the reticle to the pip, so which way to swing is a line
    # and not an inference.
    thin = QColor(ink)
    thin.setAlpha(90)
    p.setPen(QPen(thin, 1.0, Qt.PenStyle.DotLine))
    p.drawLine(QPointF(w / 2.0, h / 2.0), QPointF(x, y))
    if mark["seconds"] > 0.05:
        p.setPen(ink)
        p.setFont(QFont(theme.mono_family(), 8))
        p.drawText(QPointF(x + 12, y + 14), f"{mark['seconds']:.1f} s")


def _arc_stops(p, action, w: int, h: int) -> None:
    """A bar along the edge when the mounting is against its stops.

    The hull is in the way, and a gunner holding the stick into a stop with
    nothing happening should be able to see why in the picture rather than
    work it out from a number on a panel.
    """
    turret, kind = action.turret, action.turret.kind
    marks = []
    if abs(abs(turret.bearing) - kind.arc) < 0.6:
        marks.append("x" if turret.bearing > 0 else "-x")
    if abs(turret.elevation - kind.up) < 0.6:
        marks.append("up")
    if abs(turret.elevation + kind.down) < 0.6:
        marks.append("down")
    if not marks:
        return
    ink = _tint("osteo")
    ink.setAlpha(150)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    thick = 5
    for mark in marks:
        if mark == "x":
            p.drawRect(QRectF(w - thick, h * 0.25, thick, h * 0.5))
        elif mark == "-x":
            p.drawRect(QRectF(0, h * 0.25, thick, h * 0.5))
        elif mark == "up":
            p.drawRect(QRectF(w * 0.25, 0, w * 0.5, thick))
        else:
            p.drawRect(QRectF(w * 0.25, h - thick, w * 0.5, thick))
    p.setBrush(Qt.BrushStyle.NoBrush)


def _bar(p, at: QRectF, share: float, ink: QColor, label: str) -> None:
    """One gauge: a frame, a fill and a word."""
    p.setPen(QPen(QColor(ink.red(), ink.green(), ink.blue(), 110), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(at)
    p.setBrush(ink)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(at.x(), at.y(), at.width() * max(0.0, min(1.0, share)),
                      at.height()))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QColor(theme.INK3))
    p.setFont(QFont(theme.mono_family(), 8))
    p.drawText(QPointF(at.x(), at.y() - 3), label)


def _gauges(p, action, w: int, h: int) -> None:
    """Heat, the magazine, and the hull you are standing on."""
    turret, kind = action.turret, action.turret.kind
    left, wide, tall = 18.0, 150.0, 7.0
    base = h - 30.0
    hot = turret.heat / turret_sim.COOKED
    _bar(p, QRectF(left, base, wide, tall), hot,
         _tint("bad" if turret.jammed else "osteo" if hot > 0.6 else "lumen"),
         f"HEAT {turret.heat:.0f}" + ("  COOKED" if turret.jammed else ""))
    if kind.rounds:
        share = turret.rounds / kind.rounds
        _bar(p, QRectF(left, base - 24, wide, tall), share,
             _tint("warn" if share < 0.25 else "chloro"),
             f"ROUNDS {turret.rounds}/{kind.rounds}"
             + (f"  FEEDING {turret.reloading:.1f}s"
                if turret.reloading > 0 else ""))
    share = action.hp / action.max_hp if action.max_hp else 0.0
    _bar(p, QRectF(left, base - 48, wide, tall), share,
         _tint("bad" if share < 0.3 else "chloro"),
         f"HULL {share:.0%}")


def _warnings(p, action, w: int, h: int) -> None:
    """The two things a gunner must not miss: a seeker, and a dead gun."""
    said = []
    seekers = [c for c in skirmish.live(action, hostile=True)
               if c.behaviour == "home"]
    if seekers:
        near = min(seekers, key=lambda c: c.range_km)
        seconds = near.range_km / max(0.01, near.pace)
        said.append(("INCOMING · " + f"{len(seekers)} seeker"
                     + ("s" if len(seekers) > 1 else "")
                     + f" · nearest {seconds:,.0f} s", "bad"))
    ok, why = turret_sim.can_fire(action.turret)
    if not ok and why:
        said.append((why.upper(), "osteo"))
    if not said:
        return
    p.setFont(QFont(theme.mono_family(), 10, QFont.Weight.Bold))
    for index, (line, tint) in enumerate(said):
        ink = _tint(tint)
        # A seeker warning throbs; a cold gun does not need to.
        if tint == "bad":
            beat = 0.5 + 0.5 * math.sin(action.clock * 7.0)
            ink.setAlpha(int(150 + 105 * beat))
        p.setPen(ink)
        p.drawText(QRectF(0, 22 + index * 18, w, 16),
                   Qt.AlignmentFlag.AlignHCenter, line)
