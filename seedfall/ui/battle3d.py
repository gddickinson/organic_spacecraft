"""The engagement from the bridge: two hulls, and what passed between them.

`ui/tactical_plot.py` draws the geometry from above — headings, range bands,
firing arcs — and it is the right tool for *deciding*. This is the other half:
what it looked like. A captain who has just ordered a broadside should see the
broadside.

Everything here is read from `battle.shots`, which `sim/gunfire.py` records as
the exchange resolves, so the picture is of what actually happened rather than
a decoration playing alongside it. A round that never left the tube because
the mount would not train that far is drawn too — as a stub at the muzzle,
because *that* is the thing worth seeing and it is the whole argument for
having come about.

The camera sits behind and above your own hull, looking at the enemy, which is
the one view where relative bearing reads without having to be labelled.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import (QColor, QFont, QPainter, QPen, QRadialGradient)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..data import hulls3d, models3d
from ..sim import gunfire
from ..sim import tactical as tac
from . import render3d, theme
from .viewport import STARS
from . import painting

#: Half the field of view. Tighter than the conn's, because an engagement is
#: something you watch rather than fly.
HALF_FOV = math.radians(26.0)

#: How big a hull is drawn, in tactical units. The plane is a few hundred
#: units across and a hull is a hundred metres, so a literal scale would be a
#: pixel. This is the same lie every naval plot has ever told.
HULL_SIZE = 34.0

#: How the hull models are laid down. Every mesh in this package is authored
#: nose along +z, and a tactical plot wants them lying in the plane pointing
#: where they are going — so they are tilted onto their side and then swung
#: round by `render3d.draw`'s `yaw`. `LIE_YAW` is the quarter turn that puts
#: the nose back on the heading after the tilt has dropped it onto -y.
LIE_FLAT = math.pi / 2
LIE_YAW = math.pi / 2

#: How much bigger the largest hull is drawn than the smallest. The chassis
#: masses run from a SPORE to a LEVIATHAN, which is a factor of far more than
#: this in tonnes — drawn true to mass, the small hulls would be a pixel. The
#: cube root of the mass ratio is the honest compromise: a shape's *size* on a
#: plot goes as its linear dimension, and mass goes as the cube of that.
SIZE_SPREAD = 2.6

#: The mass a hull of exactly `HULL_SIZE` has, in tonnes: the median of the
#: thirty-five chassis. Measured rather than chosen — the masses run 60 t for a
#: SPORE to **twelve billion** for a LEVIATHAN, and 99% of them sit under
#: 160,000. Anchoring on one hull and taking a cube root put every chassis
#: above a NAVIS hard against the ceiling; anchoring on the median and using a
#: gentler root spends the scale where the ships actually are.
SIZE_AT_T = 15_000.0

#: Which root of the mass ratio the drawn size follows. A sixth: mass goes as
#: the cube of a linear dimension, and half again on top of that keeps a
#: three-order-of-magnitude spread inside a plot a person can read.
SIZE_ROOT = 6.0


def _family(side) -> str:
    """Which of the five families this combatant was built in."""
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(getattr(side.ship, "chassis", "") or "")
    return getattr(chassis, "family", "") or "fabricated"


def _hull_scale(side) -> float:
    """How big to draw it, from what it actually masses."""
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(getattr(side.ship, "chassis", "") or "")
    mass = float(getattr(chassis, "mass_t", 0) or SIZE_AT_T)
    ratio = max(1e-6, mass / SIZE_AT_T) ** (1.0 / SIZE_ROOT)
    return max(1.0 / SIZE_SPREAD, min(SIZE_SPREAD, ratio))

#: Where the eye sits relative to your own hull, as a share of the gap to the
#: enemy: behind and above. Proportional rather than fixed, so the pair stay
#: framed at contact range and at extreme — a fixed stand-off put two hulls
#: on top of each other at band 3 and left most of the picture empty.
EYE_BACK_SHARE = 0.34
EYE_UP_SHARE = 0.16
EYE_BACK_MIN = 150.0
EYE_UP_MIN = 60.0

#: Where the camera looks, between you and them. Past the middle, so your own
#: hull sits low in the frame and the thing you are shooting at is in it.
AIM_SHARE = 0.62

#: What each kind of weapon looks like going off.
LOOKS = {
    gunfire.BEAM: ("#8fe8ff", 3.2),
    gunfire.ROUND: ("#ffd98a", 2.0),
    gunfire.SEEKING: ("#ff9a6a", 2.4),
    gunfire.FLAK: ("#c8d4cc", 1.4),
}


class Battle3D(QWidget):
    """The exchange, drawn where it happened."""

    def __init__(self, battle):
        super().__init__()
        self.battle = battle
        self.setMinimumSize(360, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Expanding)

    # ── the camera ─────────────────────────────────────────────────────────

    def _camera(self, w: int, h: int):
        """Behind and above your own hull, looking at the enemy."""
        b = self.battle
        me, them = b.player.body, b.enemy.body
        span = max(1.0, tac.separation(me, them))
        toward = ((them.x - me.x) / span, (them.y - me.y) / span, 0.0)
        back = max(EYE_BACK_MIN, span * EYE_BACK_SHARE)
        up = max(EYE_UP_MIN, span * EYE_UP_SHARE)
        eye = (me.x - toward[0] * back, me.y - toward[1] * back, up)
        aim = (me.x + (them.x - me.x) * AIM_SHARE,
               me.y + (them.y - me.y) * AIM_SHARE, 0.0)
        forward = (aim[0] - eye[0], aim[1] - eye[1], aim[2] - eye[2])
        return render3d.Camera(at=eye, forward=forward, up=(0.0, 0.0, 1.0),
                               width=w, height=h, half_fov=HALF_FOV)

    # ── painting ───────────────────────────────────────────────────────────

    @painting.safe_paint
    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        if not painting.alive(self, p):
            return
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.fillRect(0, 0, w, h, QColor("#04080b"))
        b = self.battle
        camera = self._camera(w, h)

        self._stars(p, camera, w, h)
        light = render3d.unit((-0.55, -0.7, -0.45))

        # The enemy first, then yours: whichever is further away is drawn
        # first, which is all the depth sorting two hulls need.
        # Each combatant as the hull it actually is. Both were `models3d.HULL`
        # at one size, so a SPORE and a LEVIATHAN were the same object and so
        # were you and whatever was shooting at you — thirty-five chassis in
        # five families, and the plot showed one ship.
        pairs = [(b.enemy, "warn"), (b.player, "lumen")]
        pairs.sort(key=lambda row: -math.dist(
            (row[0].body.x, row[0].body.y, 0.0), camera.at))
        for side, _tint in pairs:
            render3d.draw(p, camera, hulls3d.mesh_for(_family(side)),
                          (side.body.x, side.body.y, 0.0),
                          HULL_SIZE * _hull_scale(side), light,
                          spin=0.0, tilt=LIE_FLAT,
                          yaw=math.radians(-side.body.heading) + LIE_YAW)

        self._shots(p, camera)
        self._labels(p, camera, w, h)
        p.end()

    def _stars(self, p: QPainter, camera, w: int, h: int) -> None:
        for x, y, z, bright in STARS:
            at = camera.project((camera.at[0] + x * 1e6,
                                 camera.at[1] + y * 1e6,
                                 camera.at[2] + z * 1e6))
            if at is None:
                continue
            point, _ahead = at
            if not (0 <= point.x() < w and 0 <= point.y() < h):
                continue
            shade = int(70 + 130 * bright)
            p.setPen(QPen(QColor(shade, shade, min(255, shade + 16)), 1.0))
            p.drawPoint(point)

    def _shots(self, p: QPainter, camera) -> None:
        """Everything that was fired, and everything that would not fire."""
        for shot in getattr(self.battle, "shots", ()):
            colour, width = LOOKS.get(shot.look, ("#ffffff", 2.0))
            a = camera.project((shot.frm_at[0], shot.frm_at[1], 6.0))
            z = camera.project((shot.to_at[0], shot.to_at[1], 6.0))
            if a is None or z is None:
                continue
            start, end = a[0], z[0]

            if shot.outcome in (gunfire.NO_ARC, gunfire.NO_BEAR, gunfire.DRY):
                # A stub at the muzzle: it never left. Dashed, and short.
                pen = QPen(QColor(120, 120, 120, 150), 1.4)
                pen.setStyle(Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.drawLine(start, QPointF(start.x() + (end.x() - start.x()) * 0.12,
                                          start.y() + (end.y() - start.y()) * 0.12))
                continue

            tint = QColor(colour)
            if shot.outcome == gunfire.MISS:
                # Past the shoulder rather than into it.
                end = QPointF(end.x() + (end.y() - start.y()) * 0.10,
                              end.y() - (end.x() - start.x()) * 0.10)
                tint.setAlpha(150)
            p.setPen(QPen(tint, width))
            if shot.look == gunfire.SEEKING:
                self._arc(p, start, end)
            else:
                p.drawLine(start, end)

            if shot.outcome == gunfire.HIT:
                self._flash(p, end, shot.damage)
            elif shot.outcome == gunfire.SWATTED:
                self._flash(p, QPointF((start.x() + end.x()) / 2,
                                       (start.y() + end.y()) / 2), 4.0,
                            "#c8d4cc")

    def _arc(self, p: QPainter, start: QPointF, end: QPointF) -> None:
        """A seeking round does not fly straight, and should not look as if
        it did."""
        mid = QPointF((start.x() + end.x()) / 2
                      + (end.y() - start.y()) * 0.16,
                      (start.y() + end.y()) / 2
                      - (end.x() - start.x()) * 0.16)
        last = start
        for step in range(1, 13):
            t = step / 12.0
            inv = 1.0 - t
            point = QPointF(
                inv * inv * start.x() + 2 * inv * t * mid.x() + t * t * end.x(),
                inv * inv * start.y() + 2 * inv * t * mid.y() + t * t * end.y())
            p.drawLine(last, point)
            last = point

    def _flash(self, p: QPainter, at: QPointF, damage: float,
               colour: str = "#ffd08a") -> None:
        radius = max(6.0, min(34.0, 6.0 + damage * 0.55))
        glow = QRadialGradient(at, radius)
        tint = QColor(colour)
        glow.setColorAt(0.0, QColor(255, 255, 235, 235))
        glow.setColorAt(0.35, QColor(tint.red(), tint.green(), tint.blue(), 190))
        glow.setColorAt(1.0, QColor(tint.red(), tint.green(), tint.blue(), 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(at, radius, radius)

    def _labels(self, p: QPainter, camera, w: int, h: int) -> None:
        b = self.battle
        p.setFont(QFont(theme.mono_family(), 9))
        for side, name, tint in ((b.player, b.player.ship.name, "lumen"),
                                 (b.enemy, b.enemy_name, "warn")):
            at = camera.project((side.body.x, side.body.y, HULL_SIZE * 1.2))
            if at is None:
                continue
            p.setPen(QColor(theme.tint(tint)))
            p.drawText(QPointF(at[0].x() + 8, at[0].y()), name)

        said = gunfire.summary(b)
        p.setPen(QColor(theme.INK3))
        span = tac.separation(b.player.body, b.enemy.body)
        p.drawText(QPointF(8, 15),
                   f"BAND {tac.band_for(span)}  ·  {span:,.0f}")
        if said["fired"]:
            p.drawText(QPointF(8, h - 8),
                       f"{said['fired']} fired · {said['hits']} struck · "
                       f"{said['damage']:,.0f} dealt"
                       + (f" · {said['refused']} would not bear"
                          if said["refused"] else ""))
        elif said["refused"]:
            p.drawText(QPointF(8, h - 8),
                       f"{said['refused']} mount(s) would not bear")
