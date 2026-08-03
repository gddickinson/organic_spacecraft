"""Heads-up flying aids, drawn on the picture the pilot already looks through.

Every number here existed on a board somewhere; what was missing was seeing
them *in the window*. Four aids, each off a door the sim already owns:

- **The predicted path** — `sim/preview.track`, a throwaway twin flown under
  the armed mode (or ballistic, when the computer has nothing), drawn as dots
  that shrink with time. The same dry run the approach window plots, brought
  to the first-person view.
- **Prograde and retrograde** — where she is actually going and its opposite,
  the two marks every real HUD starts with. The nose is not the velocity, and
  a pilot who can see both stops guessing.
- **The aim point** — where the approach is actually flying next
  (`moorings.aim`: the corridor's hold point, then the berth), as a chevron.
- **The way in** — a bay's mouth (`sim/bays`), drawn as the ring it is, on
  the axis `in_corridor` protects. Missing the ring is hitting the rim.

`points` computes, `draw` paints — split so a check can ask where everything
landed without rendering a pixel.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen

from ..sim import bays, moorings
from ..sim.targets import is_open
from . import theme
from .viewport_math import project

#: How far ahead the path is flown, in ticks (minutes), and every how many.
PATH_TICKS = 48
PATH_EVERY = 6


def _rel(conn, at) -> list:
    """A future or fixed position in the frame, as a bearing from the ship."""
    return [a - p for a, p in zip(at, conn.pos)]


def points(conn, cam, w: int, h: int) -> dict:
    """Everything the HUD would draw, as screen points. The testable half."""
    out = {"path": [], "prograde": None, "retrograde": None,
           "aim": None, "mouth": [], "threat": None}
    if conn is None or conn.landed:
        return out
    # What is in the way, from the one door that answers it.
    from ..sim import collision
    hazard = collision.scan(None, conn)
    if hazard is not None:
        vec = collision._bearing(conn, hazard)
        spot = project(vec, cam, w, h)
        if spot is not None:
            out["threat"] = (spot, hazard.level,
                             f"{hazard.name} · {hazard.seconds:,.0f}s")
    # The path: a twin flown under whatever has the conn. `preview.track`
    # coasts for modes it cannot fly ("run" needs the game), which is still
    # the honest ballistic answer.
    from ..sim import preview
    # `preview.track` flies a twin under `sim/autopilot`'s modes; the deck's
    # other verbs need the game, which a dry run has not got. `brake` is
    # `null` under another name, so it is flown honestly; `run` and `depart`
    # fall through to a coast, which is the true "if nothing changes" line.
    mode = {"brake": "null"}.get(conn.auto, conn.auto)
    if mode in ("run", "depart"):
        mode = None
    for _s, at, _km, _v in preview.track(conn, mode or None,
                                         ticks=PATH_TICKS, every=PATH_EVERY):
        vec = _rel(conn, at)
        if math.dist(vec, (0.0, 0.0, 0.0)) < 1e-6:
            continue
        spot = project(vec, cam, w, h)
        if spot is not None:
            out["path"].append(spot)
    speed = conn.speed
    if speed > 0.05:
        way = [v / speed for v in conn.vel]
        out["prograde"] = project(way, cam, w, h)
        out["retrograde"] = project([-c for c in way], cam, w, h)
    if not is_open(conn.target) and not conn.over:
        aim = moorings.aim(conn)
        vec = _rel(conn, aim)
        if math.dist(vec, (0.0, 0.0, 0.0)) > 1e-6:
            out["aim"] = project(vec, cam, w, h)
        out["mouth"] = _mouth_points(conn, cam, w, h)
    return out


def _mouth_points(conn, cam, w: int, h: int) -> list:
    """The way in, as a ring of screen points. Empty for anything mouthless."""
    target = conn.target
    sort = getattr(target, "berth", "") or ""
    got = bays.mouth_of(sort)
    if got is None:
        return []
    bore_share, plane = got
    radius = float(getattr(target, "radius_km", 0.0) or 0.0)
    way = bays.axis(target, moorings.spin_of(conn))
    centre = [c * plane * radius for c in way]
    # Two perpendiculars to the axis, for the circle to live in.
    seed = (0.0, 0.0, 1.0) if abs(way[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = [way[1] * seed[2] - way[2] * seed[1],
         way[2] * seed[0] - way[0] * seed[2],
         way[0] * seed[1] - way[1] * seed[0]]
    span = math.dist(u, (0.0, 0.0, 0.0)) or 1.0
    u = [c / span for c in u]
    v = [way[1] * u[2] - way[2] * u[1],
         way[2] * u[0] - way[0] * u[2],
         way[0] * u[1] - way[1] * u[0]]
    bore = bore_share * radius
    ring = []
    for step in range(12):
        a = step / 12.0 * math.tau
        at = [centre[i] + (u[i] * math.cos(a) + v[i] * math.sin(a)) * bore
              for i in range(3)]
        spot = project(_rel(conn, at), cam, w, h)
        if spot is not None:
            ring.append(spot)
    return ring


def draw(p, conn, cam, w: int, h: int) -> None:
    """Paint the aids. Quietly declines anything that does not project."""
    got = points(conn, cam, w, h)
    ink = QColor(theme.tint("chloro"))
    ink.setAlpha(150)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(ink)
    for index, spot in enumerate(got["path"]):
        size = max(1.0, 2.6 - index * 0.25)
        p.drawEllipse(QPointF(spot[0], spot[1]), size, size)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if got["prograde"] is not None:
        x, y, _d = got["prograde"]
        p.setPen(QPen(QColor(theme.tint("chloro")), 1.4))
        p.drawEllipse(QPointF(x, y), 5, 5)
        p.drawLine(QPointF(x - 8, y), QPointF(x - 5, y))
        p.drawLine(QPointF(x + 5, y), QPointF(x + 8, y))
        p.drawLine(QPointF(x, y - 8), QPointF(x, y - 5))
    if got["retrograde"] is not None:
        x, y, _d = got["retrograde"]
        p.setPen(QPen(QColor(theme.tint("osteo")), 1.2))
        p.drawEllipse(QPointF(x, y), 4, 4)
        p.drawLine(QPointF(x - 3, y - 3), QPointF(x + 3, y + 3))
        p.drawLine(QPointF(x - 3, y + 3), QPointF(x + 3, y - 3))
    if got["aim"] is not None:
        x, y, _d = got["aim"]
        p.setPen(QPen(QColor(theme.tint("lumen")), 1.4))
        for dx, dy in ((-6, 0), (6, 0), (0, -6), (0, 6)):
            p.drawLine(QPointF(x + dx, y + dy),
                       QPointF(x + dx * 0.4, y + dy * 0.4))
    threat = got.get("threat")
    if threat is not None and threat[0] is not None:
        # **The thing in the way, ringed and named, out of the window.** A
        # collision warning a pilot has to find on a panel is a warning they
        # find afterwards.
        (x, y, _d), level, text = threat
        ink = QColor(theme.tint("bad" if level == "imminent" else "warn"))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(ink, 2.0 if level == "imminent" else 1.4))
        p.drawRect(int(x - 14), int(y - 14), 28, 28)
        p.drawLine(QPointF(x - 20, y), QPointF(x - 14, y))
        p.drawLine(QPointF(x + 14, y), QPointF(x + 20, y))
        p.drawText(int(x + 18), int(y - 16), text)
    if len(got["mouth"]) >= 3:
        pen = QPen(QColor(theme.tint("lumen")), 1.2, Qt.PenStyle.DashLine)
        p.setPen(pen)
        ring = [QPointF(x, y) for x, y, _d in got["mouth"]]
        for a, b in zip(ring, ring[1:] + ring[:1]):
            p.drawLine(a, b)
