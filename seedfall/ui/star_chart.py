"""The star chart itself: forty-odd stars, the jump circle, the Weave, and
the growing red stain in one corner of it.

Split out of `ui/map_view.py` when that file passed five hundred lines; the
seam is the one between the picture and the screen that hosts it. The screen
re-exports `StarChart` and `marker_radius`, which the fog and Weave checks
import from there.

**Labels no longer print over each other.** Every known star wrote its name
into a fixed box under itself, and in the sector's dense core two or three
names overprinted into an unreadable smudge. Names are placed in a second
pass now — under the star, else over it, else beside it — and one that has
nowhere to go is left off rather than drawn through another; the star you are
at and the one you have picked always keep theirs.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..sim import intel as intel_sim
from ..sim import reach as reach_sim
from ..sim import rumours as rumour_sim
from ..world.galaxy import distance
from . import mesh_panel, painting, reaches_chart, theme
from . import hunt_marks
from . import kith_codex
from . import sky_chart

FACTION_COLOUR = {k: theme.tint(v) for k, v in theme.FACTION_TINT.items()}


#: What an uncatalogued star's marker is drawn as, in bodies. A fixed stand-in,
#: because the alternative is the true count — and the marker was measuring out
#: the very number the panel withholds and the chart's price used to quote.
UNKNOWN_MARKER_BODIES = 2


def marker_radius(game, system) -> float:
    """How big to draw a star, in pixels. Sized by bodies only where known."""
    counted = intel_sim.body_count(game, system)
    if counted is None:
        counted = UNKNOWN_MARKER_BODIES
    return 2.6 + counted * 0.3


class StarChart(QWidget):
    picked = pyqtSignal(int)

    def __init__(self, win):
        super().__init__()
        self.win = win
        self.selected: int | None = None
        #: Which region's frame this is drawing — a tab on the chart screen.
        self.region: str = "verge"
        self.setMinimumHeight(420)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(360)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._names: list = []
        #: Where each name went on the last paint, `(system id, rect)`.
        self.placed: list = []
        # A picture has no text for a screen reader to find. The keyboard's
        # way in is the destination list beside it (`ui/map_view.py`).
        self.setAccessibleName("Sector chart")
        self.setAccessibleDescription(
            "Stars of the Verge. Choose a destination from the list beside it.")

    # geometry -------------------------------------------------------------

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return True

    def heightForWidth(self, w: int) -> int:  # noqa: N802
        """As tall as the frame is at this width, and no taller. Stretched to
        the height of a long panel beside it, the chart drew its stars in the
        middle of 1,461 px and the part on screen was black (play-test,
        2026-09-18); `map_view` sets it top-aligned so this is honoured."""
        fw, fh = reaches_chart.frame(self.win.game, self.region)
        pad = 30
        tall = (w - pad * 2) * fh / max(fw, 1e-9) + pad * 2
        return int(max(self.minimumHeight(), min(tall, 900)))

    def _projection(self):
        # The frame is the region's own: see `ui/reaches_chart.py`.
        fw, fh = reaches_chart.frame(self.win.game, self.region)
        pad = 30
        w, h = self.width(), self.height()
        scale = min((w - pad * 2) / fw, (h - pad * 2) / fh)
        ox = (w - fw * scale) / 2
        oy = (h - fh * scale) / 2
        return scale, ox, oy

    def _to_screen(self, sys) -> QPointF:
        s, ox, oy = self._projection()
        return QPointF(ox + sys.x * s, oy + sys.y * s)

    def _pick(self, pos) -> int | None:
        best, bd = None, 16.0
        for sys in reaches_chart.systems(self.win.game, self.region):
            p = self._to_screen(sys)
            d = math.hypot(p.x() - pos.x(), p.y() - pos.y())
            if d < bd:
                best, bd = sys.id, d
        return best

    def mousePressEvent(self, ev):  # noqa: N802
        sid = self._pick(ev.position())
        if sid is not None:
            self.selected = sid
            self.picked.emit(sid)
            self.update()

    def mouseMoveEvent(self, ev):  # noqa: N802
        hit = self._pick(ev.position()) is not None
        self.setCursor(Qt.CursorShape.PointingHandCursor if hit
                       else Qt.CursorShape.CrossCursor)
        self.setToolTip(reaches_chart.tooltip(self, self.win.game, ev.position()))

    # painting -------------------------------------------------------------

    @painting.safe_paint
    def paintEvent(self, _ev):  # noqa: N802
        g = self.win.game
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#060f0d"))
        if not reaches_chart.is_open(g, self.region):
            # A region nobody has opened: a silhouette and what it takes.
            reaches_chart.draw_sealed(self, p, g)
            p.end()
            return

        scale, _ox, _oy = self._projection()
        here = g.system
        hs = self._to_screen(here)
        reach = g.ship_stats.jump
        # The ship's own marks only on the tab of the region it is in.
        home = getattr(here, "region", "verge") == self.region
        shown = reaches_chart.systems(g, self.region)

        # jump envelope
        pen = QPen(QColor(84, 207, 124, 90), 1, Qt.PenStyle.DashLine)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if home:
            p.drawEllipse(hs, reach * scale, reach * scale)

        # reachable lanes
        p.setPen(QPen(QColor(150, 196, 176, 38), 1))
        for sys in shown:
            if sys.id != here.id and distance(sys, here) <= reach:
                p.drawLine(hs, self._to_screen(sys))

        # The Weave. Lit rings first, in gold, because they are the only
        # lines on this chart that cost no time at all — and the dark ones
        # behind them, so a captain can see what the sector *would* be.
        self._draw_weave(p, g)
        reaches_chart.draw_deep(self, p, g)     # the deep anchors and rings

        # Which stars are reachable *at all*, by hopping. The dashed ring
        # only ever said what is one jump away, so a star behind a gap no
        # amount of hopping closes was drawn exactly like the one next door.
        within = reach_sim.component(g)
        self._names = []
        for sys in shown:
            # Another region's stars are not walled off, only elsewhere.
            self._draw_system(p, sys, here, reach, sys.id in within or not home)
        self._draw_names(p, here.id)
        hunt_marks.draw_sightings(p, self, g)      # where rivals were last seen
        kith_codex.draw(self, p, g)                # the Kith's gatherings
        sky_chart.draw(p, self, g)                 # flares, comets, the nova

        if home:
            self._draw_marker(p, hs, QColor(theme.tint("chloro")), 13)
        if self.selected is not None and any(s.id == self.selected
                                             for s in shown):
            self._draw_marker(p, self._to_screen(g.galaxy.systems[self.selected]),
                              QColor(theme.tint("lumen")), 10)
        p.end()

    def _draw_weave(self, p: QPainter, g) -> None:
        """Ancient rings and the anchors that stand on them."""
        if self.region != "verge":
            return                      # the ancient Weave is the Verge's
        from ..sim import weave as weave_sim
        anchors = {gate.system_id: gate for gate in weave_sim.gates(g)}
        drawn = set()
        for gate in anchors.values():
            for other in gate.links:
                if other not in anchors or (other, gate.system_id) in drawn:
                    continue
                drawn.add((gate.system_id, other))
                far = anchors[other]
                both = gate.lit and far.lit
                a = self._to_screen(g.galaxy.systems[gate.system_id])
                b = self._to_screen(g.galaxy.systems[other])
                if both:
                    p.setPen(QPen(QColor(226, 186, 96, 190), 2.0))
                else:
                    pen = QPen(QColor(120, 104, 74, 70), 1.0)
                    pen.setStyle(Qt.PenStyle.DotLine)
                    p.setPen(pen)
                p.drawLine(a, b)
        for gate in anchors.values():
            at = self._to_screen(g.galaxy.systems[gate.system_id])
            tint = QColor(226, 186, 96) if gate.lit else QColor(120, 104, 74)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(tint, 1.6 if gate.lit else 1.0))
            p.drawEllipse(at, 11, 11)
            if gate.lit:
                p.drawEllipse(at, 14, 14)

    def _draw_system(self, p: QPainter, sys, here, reach,
                     reachable: bool = True) -> None:
        g = self.win.game
        pt = self._to_screen(sys)
        rank = intel_sim.level(g, sys)
        known = rank >= 1 or any(c.system_id == sys.id for c in g.colonies)

        if sys.bloom > 0.02 and intel_sim.sees_bloom(g, sys):
            radius = 9 + sys.bloom * 24
            grad = QRadialGradient(pt, radius)
            grad.setColorAt(0.0, QColor(224, 104, 95, int(70 * sys.bloom + 30)))
            grad.setColorAt(1.0, QColor(224, 104, 95, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawEllipse(pt, radius, radius)

        r = marker_radius(g, sys)
        # How well a system is known reads off the marker: an outline for a
        # name in a registry, a filled disc once you have been, and a ring
        # around anything charted to the last body.
        if rank >= 2:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(sys.tint))
            p.drawEllipse(pt, r, r)
        elif rank == 1:
            faded = QColor(sys.tint)
            faded.setAlpha(120)
            p.setPen(QPen(QColor(150, 196, 176, 110), 1))
            p.setBrush(faded)
            p.drawEllipse(pt, r, r)
        else:
            p.setPen(QPen(QColor(150, 196, 176, 70), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r, r)

        if rank >= 3:
            p.setPen(QPen(QColor(theme.tint("chloro")), 1.0, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 5.5, r + 5.5)

        # Anything anybody has told you about sits on the chart as a caret.
        if rumour_sim.about(g, sys.id):
            p.setPen(QPen(QColor(theme.tint("xeno")), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            top = QPointF(pt.x(), pt.y() - r - 9)
            p.drawLine(QPointF(top.x() - 4, top.y() + 5), top)
            p.drawLine(top, QPointF(top.x() + 4, top.y() + 5))

        if sys.port and known:
            colour = QColor(FACTION_COLOUR.get(sys.faction, theme.INK3))
            p.setPen(QPen(colour, 1.6 if sys.port.capital else 1.0))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 3.6, r + 3.6)

        if any(c.system_id == sys.id for c in g.colonies):
            pen = QPen(QColor(84, 207, 124, 150), 1, Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(pt, r + 6.8, r + 6.8)

        if not reachable:
            # A bar through the star: this one is not far, it is walled off.
            p.setPen(QPen(QColor(224, 104, 95, 130), 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawLine(QPointF(pt.x() - r - 4, pt.y() - r - 4),
                       QPointF(pt.x() + r + 4, pt.y() + r + 4))

        if mesh_panel.chart_mark(g, sys):        # see `ui/mesh_panel`
            self._draw_marker(p, pt, QColor(224, 104, 95), r + 4.5)

        if known:
            self._names.append((sys, pt, r, reachable))

    def _draw_names(self, p: QPainter, here_id: int) -> None:
        """Every known star's name, where it does not print over another.

        The star you are at and the one picked go first, so they always get
        their name; then the rest, nearest the centre of attention first.
        """
        font = QFont(theme.mono_family(), 8)
        p.setFont(font)
        metrics = QFontMetricsF(font)
        first = {here_id, self.selected}
        order = sorted(self._names, key=lambda n: n[0].id not in first)
        taken: list[QRectF] = []
        self.placed = []
        # Discs are obstacles too: a name over another star hides the star.
        for sys, pt, r, _reach in self._names:
            taken.append(QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r))
        for sys, pt, r, reachable in order:
            # The here and picked stars wear corner marks 13 and 10 px out;
            # their names go outside those rather than through them.
            clear = 13 if sys.id == here_id else 10 if sys.id in first else r
            spot = place_name(metrics, sys.name, pt, max(r, clear), taken,
                              always=sys.id in first)
            if spot is None:
                continue
            taken.append(spot)
            self.placed.append((sys.id, spot))
            p.setPen(QColor(169, 194, 182, 190 if reachable else 90))
            p.drawText(spot, Qt.AlignmentFlag.AlignCenter, sys.name)

    def _draw_marker(self, p: QPainter, pt: QPointF, colour: QColor, size: float):
        p.setPen(QPen(colour, 1.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            p.drawLine(QPointF(pt.x() + dx * size, pt.y() + dy * size * 0.55),
                       QPointF(pt.x() + dx * size, pt.y() + dy * size))
            p.drawLine(QPointF(pt.x() + dx * size, pt.y() + dy * size),
                       QPointF(pt.x() + dx * size * 0.55, pt.y() + dy * size))




def place_name(metrics, name: str, pt, r: float, taken: list,
               always: bool = False):
    """Where a star's name goes: under it, over it, right, left — the first
    that overlaps nothing already placed. None when all four collide, unless
    `always`, which takes the spot under the star regardless."""
    w, h = metrics.horizontalAdvance(name) + 4, metrics.height()
    spots = (QRectF(pt.x() - w / 2, pt.y() + r + 3, w, h),
             QRectF(pt.x() - w / 2, pt.y() - r - 3 - h, w, h),
             QRectF(pt.x() + r + 5, pt.y() - h / 2, w, h),
             QRectF(pt.x() - r - 5 - w, pt.y() - h / 2, w, h))
    for spot in spots:
        # A disc that is this star's own does not count against it.
        if not any(spot.intersects(t) and not t.contains(pt) for t in taken):
            return spot
    return spots[0] if always else None
