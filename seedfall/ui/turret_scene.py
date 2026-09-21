"""The sky out of a gun blister: your own hull, what is out there, and the tracers.

The camera sits **at the muzzle and looks down the bore**, so traversing the
gun swings the whole picture — which is the one thing that makes a turret feel
like a turret rather than a diagram of one. Everything is in the hull's frame
in kilometres, which is `sim/skirmish`'s frame, so nothing here converts
anything.

Three layers, painted back to front:

- **The setting.** Stars, the system's star, and whatever the action is
  happening over — a world's limb, a station's flank, or nothing at all.
- **The sky.** Every contact as the solid it is, at its true angular size,
  with the fittings a gunner can shoot off it marked on the one they have
  locked.
- **The seat.** Your own hull, which is *behind and below you* and is why the
  mounting has an arc at all, and the blister's own rim and barrel in screen
  space, so the gunner can see what they are sitting in.

The aids on the glass — the reticle, the lead pip, the brackets, the
directive list — are `ui/turret_hud.py`. This draws the world; that draws what
the gunner is told about it.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPen, QPolygonF, QRadialGradient

from ..data import hulls3d, models3d, worlds3d
from ..sim import gunsight
from ..sim.skirmish import HULL_KM
from . import render3d, spheres, theme
from .viewport import STARS

#: How wide the gunner's window is. Tighter than the conn's cameras: a sight
#: is something you look *through*, and a wide lens makes everything small
#: and the lead pip meaningless.
HALF_FOV = math.radians(27.0)

#: What each kind of contact is drawn as, and the tint its bracket takes.
LOOKS = {
    "hull": ("hull", "warn"),
    "corvette": ("hull", "warn"),
    "consort": ("hull", "chloro"),
    "drone": ("drone", "warn"),
    "missile": ("seeker", "bad"),
    "torpedo": ("seeker", "bad"),
    "station": ("station", "warn"),
    "blister": ("drone", "warn"),
    "battery": ("battery", "warn"),
    "rig": ("rig", "warn"),
    "dome": ("dome", "warn"),
    "buoy": ("buoy", "lumen"),
}

#: The colour a tracer reads in, by what left the tube.
TRACER = {"beam": "#8ff0ff", "round": "#ffd08a", "flak": "#ffe9b0",
          "seeking": "#ff9d6b"}

#: How far out the backdrop sits, in km. Far enough that it does not move
#: with the gun's own position on the hull — a world does not slide about
#: because you traversed a mounting twelve metres.
FAR_KM = 900.0

_MESHES: dict = {}


def mesh_for(look: str):
    """The solid one kind of contact is drawn as, made once and kept."""
    if look in _MESHES:
        return _MESHES[look]
    if look == "station":
        made = models3d.shipyard()
    elif look == "battery":
        made = models3d.recoloured(models3d.asteroid(3), "#7d6a55")
    elif look == "rig":
        made = models3d.recoloured(models3d.shipyard(), "#8a7d63")
    elif look == "dome":
        made = models3d.recoloured(models3d.sphere(10, 14), "#93826a")
    elif look == "buoy":
        made = models3d.recoloured(models3d.sphere(6, 8), "#5fd6c8")
    elif look == "seeker":
        made = models3d.recoloured(models3d.hull(), "#d8b48a")
    elif look == "drone":
        made = models3d.recoloured(models3d.hull(), "#b9c6bd")
    else:
        made = hulls3d.mesh_for("navis")
    _MESHES[look] = made
    return made


def camera(action, w: int, h: int):
    """The eye, at the muzzle, looking down the bore.

    `up` is the hull's own back except when the gun is pointing very nearly
    at it, where any vector in the plane will do and the nose is the one that
    keeps the horizon level rather than rolling.
    """
    from ..sim import turret as turret_sim
    turret = action.turret
    bore = gunsight.vector(turret.bearing, turret.elevation)
    up = (0.0, 0.0, 1.0)
    if abs(bore[2]) > 0.96:
        up = (0.0, 1.0, 0.0)
    return render3d.Camera(at=turret_sim.muzzle(turret), forward=bore, up=up,
                           width=w, height=h, half_fov=HALF_FOV)


def light(action) -> tuple:
    """Which way the starlight falls, as the renderer wants it."""
    return render3d.unit(tuple(-c for c in action.star))


def draw(p, action, w: int, h: int) -> dict:
    """The whole picture. Returns where each contact landed, for the HUD."""
    p.fillRect(0, 0, w, h, QColor("#03070a"))
    cam = camera(action, w, h)
    _stars(p, cam, w, h)
    _setting(p, action, cam, w, h)
    spots = _sky(p, action, cam, w, h)
    _tracers(p, action, cam, w, h)
    _blister(p, action, w, h)
    return spots


def _stars(p, cam, w: int, h: int) -> None:
    """The fixed field, the same one every window in the game looks at."""
    for x, y, z, bright in STARS:
        got = cam.project((cam.at[0] + x * 1e6, cam.at[1] + y * 1e6,
                           cam.at[2] + z * 1e6))
        if got is None:
            continue
        point, _ahead = got
        if not (0 <= point.x() < w and 0 <= point.y() < h):
            continue
        shade = int(80 + 140 * bright)
        p.setPen(QPen(QColor(shade, shade, min(255, shade + 16)),
                      1.4 if bright > 0.82 else 1.0))
        p.drawPoint(point)


def _setting(p, action, cam, w: int, h: int) -> None:
    """What the action is happening over. Drawn once, a long way off."""
    star = tuple(c * FAR_KM * 3 for c in action.star)
    got = cam.project(star)
    if got is not None:
        point, _ahead = got
        if -w < point.x() < w * 2 and -h < point.y() < h * 2:
            glow = QRadialGradient(point, min(w, h) * 0.18)
            glow.setColorAt(0.0, QColor(255, 252, 240, 235))
            glow.setColorAt(0.25, QColor(255, 236, 198, 120))
            glow.setColorAt(1.0, QColor(255, 220, 170, 0))
            p.setBrush(glow)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(point, min(w, h) * 0.18, min(w, h) * 0.18)
    if action.setting == "world":
        spheres.draw(p, cam, worlds3d.paint_for("rocky"),
                     (0.0, FAR_KM * 0.55, -FAR_KM * 0.62), FAR_KM * 0.52,
                     light(action), tilt=0.3)
    elif action.setting == "station":
        render3d.draw(p, cam, mesh_for("station"),
                      (-FAR_KM * 0.06, FAR_KM * 0.22, -FAR_KM * 0.04),
                      FAR_KM * 0.03, light(action), tilt=0.4)


def _sky(p, action, cam, w: int, h: int) -> dict:
    """Every contact, as its own solid at its own size. Farthest first."""
    from ..sim import skirmish
    spots: dict = {}
    rows = sorted(skirmish.live(action), key=lambda c: -c.range_km)
    glare = light(action)
    for contact in rows:
        look, tint = LOOKS.get(contact.kind, ("hull", "warn"))
        got = cam.project(contact.at)
        if got is None:
            continue
        point, ahead = got
        radius = render3d.screen_radius(cam, ahead, contact.radius_km)
        spots[contact.id] = {"at": point, "ahead": ahead, "radius": radius,
                             "tint": tint, "contact": contact}
        if radius < 1.6:
            # Too far to be a shape: a point of light, which is what a hull
            # at forty kilometres actually is out of a window.
            ink = QColor(theme.tint(tint))
            p.setBrush(ink)
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(point, 2.0, 2.0)
            continue
        render3d.draw(p, cam, mesh_for(look), contact.at, contact.radius_km,
                      glare, spin=action.clock * 0.12,
                      tilt=0.35 if contact.kind in ("station", "rig") else 0.0,
                      yaw=_yaw_of(contact))
        if contact.share < 1.0:
            _burning(p, point, radius, contact.share)
    return spots


def _yaw_of(contact) -> float:
    """Which way a moving contact is pointing: where it is going."""
    vx, vy = contact.vel[0], contact.vel[1]
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return 0.0
    return math.atan2(vx, vy)


def _burning(p, at: QPointF, radius: float, share: float) -> None:
    """A hurt contact glows where the plate has gone."""
    heat = 1.0 - max(0.0, min(1.0, share))
    if heat < 0.08:
        return
    span = max(3.0, radius * 0.9)
    glow = QRadialGradient(at, span)
    glow.setColorAt(0.0, QColor(255, 170, 90, int(150 * heat)))
    glow.setColorAt(1.0, QColor(255, 120, 60, 0))
    p.setBrush(glow)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(at, span, span)


def _tracers(p, action, cam, w: int, h: int) -> None:
    """What has been fired lately, ours going out and theirs coming in."""
    from ..sim.skirmish import TRACER_LIFE
    for shot in action.tracers:
        age = (action.clock - shot.born) / max(1e-6, TRACER_LIFE)
        if age >= 1.0:
            continue
        a = cam.project(shot.frm)
        b = cam.project(shot.to)
        if a is None or b is None:
            continue
        ink = QColor(TRACER.get(shot.look, "#ffd08a"))
        ink.setAlpha(int(235 * (1.0 - age) ** 1.4))
        wide = 2.6 if shot.look == "beam" else 1.6
        p.setPen(QPen(ink, wide if shot.mine else 1.2))
        # Ours streak out from the muzzle; theirs arrive at it, and the
        # difference has to read at a glance in the middle of an action.
        head = a[0] if shot.mine else b[0]
        tail = b[0] if shot.mine else a[0]
        run = head + (tail - head) * min(1.0, age * 2.2 + 0.2)
        p.drawLine(head, run)
        if shot.hit and age < 0.5:
            _spark(p, tail, 1.0 - age * 2.0)


def _spark(p, at: QPointF, strength: float) -> None:
    span = 4.0 + 10.0 * strength
    glow = QRadialGradient(at, span)
    glow.setColorAt(0.0, QColor(255, 250, 225, int(230 * strength)))
    glow.setColorAt(1.0, QColor(255, 180, 90, 0))
    p.setBrush(glow)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(at, span, span)


def _blister(p, action, w: int, h: int) -> None:
    """The mounting itself, in screen space: the hull under you, the rim, the gun.

    Screen space on purpose. These are the parts of the gun the gunner's own
    head is inside, and they do not move when the mounting traverses — the
    *sky* moves. Drawing them in the world would put the barrel somewhere in
    front of the camera and swing it with the picture, which is exactly
    backwards.

    **The ship is furniture here, not a model.** The first draft drew the
    whole hull at the origin, which is what a gunner standing on it would
    see — and the camera is a hundred and forty metres from a hull a hundred
    and twenty across, so it filled the middle of the window with the inside
    of a mesh and hid the thing being shot at. A hull horizon along the
    bottom says the same thing and leaves the sky to the sky.
    """
    from ..sim import turret as turret_sim
    # The ship's own back, curving away under the mounting: a dark arc that
    # says which way is "down the hull" without occluding anything.
    span = min(w, h)
    lean = math.radians(max(-80.0, min(80.0, action.turret.elevation)))
    horizon = h * 0.99 + math.sin(lean) * span * 0.5
    hull = QColor("#151d19")
    p.setBrush(hull)
    p.setPen(QPen(QColor("#2b3a32"), 1.4))
    p.drawEllipse(QPointF(w * 0.5, horizon + span * 0.62), w * 0.95,
                  span * 0.62)
    rim = QRadialGradient(QPointF(w * 0.5, h * 0.5), min(w, h) * 0.78)
    rim.setColorAt(0.0, QColor(0, 0, 0, 0))
    rim.setColorAt(0.62, QColor(0, 0, 0, 0))
    rim.setColorAt(1.0, QColor(2, 5, 8, 215))
    p.setBrush(rim)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(0, 0, w, h)

    # The gun itself, running away from the eye to a muzzle: drawn as the
    # taper it is, because a rectangle reads as a panel and a taper reads as
    # something you are looking along.
    wide = span * 0.085
    top = h - span * 0.20
    p.setPen(QPen(QColor("#4b5a51"), 1.2))
    p.setBrush(QColor("#2d362f"))
    p.drawPolygon(QPolygonF([
        QPointF(w * 0.5 - wide * 0.42, top),
        QPointF(w * 0.5 + wide * 0.42, top),
        QPointF(w * 0.5 + wide * 1.15, h),
        QPointF(w * 0.5 - wide * 1.15, h)]))
    # The muzzle brake: two rings near the end, which is what tells the eye
    # which way along the barrel it is looking.
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor("#6d7d72"), 1.4))
    for share in (0.0, 0.16):
        y = top + span * 0.20 * share
        half = wide * (0.42 + 0.73 * share)
        p.drawLine(QPointF(w * 0.5 - half, y), QPointF(w * 0.5 + half, y))
    # And the mounting's own cheeks, either side of the seat.
    p.setBrush(QColor("#222a25"))
    p.setPen(QPen(QColor("#3c473f"), 1.0))
    for side in (-1, 1):
        p.drawPolygon(QPolygonF([
            QPointF(w * 0.5 + side * wide * 1.3, h),
            QPointF(w * 0.5 + side * wide * 3.4, h),
            QPointF(w * 0.5 + side * wide * 2.6, h - span * 0.07),
            QPointF(w * 0.5 + side * wide * 1.5, h - span * 0.055)]))
    # The muzzle glows for a moment after a pull, and cooks when the mounting
    # has been worked too hard — the one place the heat number is a picture.
    turret = action.turret
    kind = turret.kind
    warm = min(1.0, turret.heat / max(1.0, turret_sim.COOKED))
    just = max(0.0, 1.0 - turret.cooldown
               / max(0.05, __import__("seedfall.data.turrets",
                                      fromlist=["x"]).seconds_between(kind)))
    if warm > 0.15 or just > 0.7:
        glow = QRadialGradient(QPointF(w * 0.5, top), wide * 1.6)
        heat = max(warm, just * 0.9)
        glow.setColorAt(0.0, QColor(255, int(200 - 120 * warm), 90,
                                    int(200 * heat)))
        glow.setColorAt(1.0, QColor(255, 120, 60, 0))
        p.setBrush(glow)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(w * 0.5, top), wide * 1.6, wide * 1.6)
