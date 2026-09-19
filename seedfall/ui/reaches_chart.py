"""The Far Reaches on the sector chart: one frame per region, and the gates.

`ui/star_chart.py` draws whichever region its tab is showing — the Verge, or
one of the three past the rim, each in its own frame (`world/regions.Region.w`
and `h`), because the coordinates of two regions mean nothing to each other.
What is particular to the Reaches lives here, so the chart's own paint stays
the shape it was:

- **A region not yet opened is a silhouette**: a haze where it will be and
  what relighting its anchor takes, step by step. Nothing of it exists until
  then — it is not generated — so the haze is seeded from the region's name
  and the chronicle's seed, and never from the game's own luck.
- **Deep anchors** get their own mark on the Verge — a diamond, violet once
  relit and a dim outline before — and a tooltip saying where each goes and
  what it still needs. On a region's tab the far end wears the same mark, and
  the Hollow's own rings are drawn in its colour.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient

from ..core.rng import RNG
from ..data.regions import REGIONS_BY_ID, VERGE
from ..world import regions as world_regions
from . import theme

#: The deep gates' colour: not the Weave's gold, because they are not the
#: Weave's and charge nobody anything.
DEEP = QColor(176, 132, 238)
DEEP_DARK = QColor(104, 86, 132)


def is_open(game, region: str) -> bool:
    from ..sim import regions as regions_sim
    return region == VERGE or region in regions_sim.opened(game)


def frame(game, region: str) -> tuple:
    """(width, height) in light years of the frame this tab draws."""
    if region == VERGE:
        return game.galaxy.w, game.galaxy.h
    opened = world_regions.region(game.galaxy, region)
    spec = REGIONS_BY_ID[region]
    return (opened.w, opened.h) if opened else (spec.w, spec.h)


def systems(game, region: str) -> list:
    """The stars this tab draws, and can be clicked on."""
    if region == VERGE:
        from ..world.galaxy import verge
        return verge(game.galaxy)
    return world_regions.systems_of(game.galaxy, region)


def _diamond(p: QPainter, at: QPointF, size: float) -> None:
    p.drawPolygon([QPointF(at.x(), at.y() - size), QPointF(at.x() + size, at.y()),
                   QPointF(at.x(), at.y() + size), QPointF(at.x() - size, at.y())])


def draw_deep(chart, p: QPainter, game) -> None:
    """The deep anchors on the Verge; the far end and the rings past the rim."""
    from ..sim import weave as weave_sim
    shown = {s.id for s in systems(game, chart.region)}
    p.setBrush(Qt.BrushStyle.NoBrush)
    drawn = set()
    for gate in weave_sim.deep_gates(game):
        if gate.system_id not in shown:
            continue
        at = chart._to_screen(game.galaxy.systems[gate.system_id])
        if gate.kind == "inner":
            for other in gate.links:
                pair = (min(gate.system_id, other), max(gate.system_id, other))
                if pair in drawn or other not in shown:
                    continue
                drawn.add(pair)
                p.setPen(QPen(DEEP, 1.6, Qt.PenStyle.DashLine))
                p.drawLine(at, chart._to_screen(game.galaxy.systems[other]))
            continue
        p.setPen(QPen(DEEP if gate.lit else DEEP_DARK, 1.8 if gate.lit else 1.2))
        _diamond(p, at, 13.0)
        if gate.lit:
            _diamond(p, at, 16.5)


def draw_sealed(chart, p: QPainter, game) -> None:
    """An unopened region: a haze where it will be, and what opening it takes."""
    from ..sim import relight as relight_sim
    spec = REGIONS_BY_ID[chart.region]
    scale, ox, oy = chart._projection()
    rng = RNG(f"{game.seed}:silhouette:{spec.id}")
    tint = QColor(DEEP_DARK)
    for _ in range(spec.count):
        x = ox + rng.float(0.1, 0.9) * spec.w * scale
        y = oy + rng.float(0.1, 0.9) * spec.h * scale
        r = rng.float(18, 46)
        glow = QRadialGradient(QPointF(x, y), r)
        glow.setColorAt(0.0, QColor(tint.red(), tint.green(), tint.blue(), 60))
        glow.setColorAt(1.0, QColor(tint.red(), tint.green(), tint.blue(), 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(x, y), r, r)
    said = relight_sim.preview(game, spec.id)
    lines = [spec.name, spec.character, ""]
    anchor = said["anchor"]
    lines.append(f"Behind the deep anchor at {anchor.name}." if anchor
                 else "No rim to stand an anchor on.")
    for _key, done, text in said["steps"]:
        lines.append(("✓ " if done else "· ") + text)
    font = QFont(theme.mono_family(), 9)
    p.setFont(font)
    box = QRectF(24, 24, max(10.0, chart.width() - 48.0),
                 max(10.0, chart.height() - 48.0))
    p.setPen(QColor(200, 186, 228, 220))
    p.drawText(box, int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
               "\n".join(lines))


def tooltip(chart, game, pos) -> str:
    """What a deep anchor under the cursor says: where it goes, what it needs."""
    from ..sim import relight as relight_sim
    from ..sim import weave as weave_sim
    shown = {s.id for s in systems(game, chart.region)}
    for gate in weave_sim.deep_gates(game):
        if gate.kind != "deep" or gate.system_id not in shown:
            continue
        at = chart._to_screen(game.galaxy.systems[gate.system_id])
        if math.hypot(at.x() - pos.x(), at.y() - pos.y()) > 16:
            continue
        rid = relight_sim.region_at(game, gate.system_id)
        if rid is None:
            # The far end: its region is whichever this tab is showing.
            return f"{gate.name} — the way back to the Verge. No toll."
        said = relight_sim.preview(game, rid)
        spec = REGIONS_BY_ID[rid]
        if relight_sim.is_open(game, rid):
            return f"{gate.name} — relit. Through it: {spec.name}. No toll."
        return f"{gate.name} — dark. It reaches {spec.name}. {said['why']}"
    return ""
