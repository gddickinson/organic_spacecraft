"""A world drawn as a lit disc rather than as a bag of polygons.

**Why this exists.** Worlds were flat-shaded meshes, and flat shading gives every
face one colour, so a world filling the window read as the polyhedron it is. The
previous cycle tried four ways to smooth the *shading* with a `QLinearGradient`
per face and every one of them failed for the same structural reason: a linear
gradient is constant perpendicular to its own axis where real Gouraud varies, and
that error alternates with a quad's orientation, so each attempt put a
checkerboard on the sphere. Finer geometry helped — 60x44 instead of 22x30 — but
it only makes the facets smaller, and it costs four times the faces.

A sphere does not need geometry. It projects to a **circle**, and a Lambertian
sphere's brightness across that circle is exactly a radial gradient whose centre
is offset toward the light: at the sub-stellar point the surface faces the star
squarely, and brightness falls to nothing along the terminator. So:

- one radial gradient for the light, which is *exact* rather than interpolated,
  and has no facets at any size;
- the latitude structure as nested ellipse caps, because a circle of latitude on
  a sphere projects to an ellipse — that is what makes the bands curve round the
  limb and read as a ball instead of a striped coin;
- the whole thing multiplied together, so a cap's colour and the light are one
  surface.

The mesh path stays for hulls, stations and gates, which are not spheres, and for
ring systems, which genuinely want geometry because they interpenetrate the world
they circle.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF
from PyQt6.QtGui import (QBrush, QColor, QPainter, QPainterPath,
                         QRadialGradient)

from . import render3d

#: How many latitude caps a world is painted in. Cheap — each is one clipped
#: fill against 2,640 polygons for the fine mesh — so this is set by what the eye
#: resolves rather than by what the budget allows. The caps crowd toward the
#: poles, where the cap colour also changes fastest, so a coarser count showed a
#: stack of arcs over the ice: ninety-six puts them under a pixel there and costs
#: about 3 ms more.
CAPS = 96

#: How far the lit pole of the gradient sits from the disc's centre, as a share
#: of the radius, when the star is directly to one side. Not 1.0: the sub-stellar
#: point is *on* the sphere, and at full profile it sits on the limb, but putting
#: the gradient's centre there leaves the lit half flat. Pulling it in gives the
#: falloff room to be a curve.
LIT_OFFSET = 0.62

#: The lighting law is `render3d`'s own — `AMBIENT + DIFFUSE * cos` — read from
#: there rather than restated here. **A first draft invented its own numbers and
#: drew every world far darker than the mesh it replaced**, which is the two-doors
#: fault in a new place: one surface lit two ways.
#:
#: What is different is only *how* it is evaluated. The mesh works it out per
#: face; this works it out along a radial gradient, which is exact for a sphere
#: because the angle from the sub-stellar point is what sets the brightness and
#: that angle maps to a screen distance.

#: How much of the light above unity actually reaches the picture. A multiply
#: cannot brighten, so the excess goes on as an additive grey — and added light is
#: flatter than multiplied light, so the whole of it would blow the subsolar point
#: out to white. Two thirds keeps the surface's own colour visible under it.
OVER_BRIGHT = 0.66

#: How much of the limb is lifted by a thin bright edge, and how wide it is as a
#: share of the radius. This is the atmosphere seen edge-on, which is the one
#: cue that most makes a drawn ball look like a world.
LIMB_LIFT = 0.30
LIMB_WIDTH = 0.06


def _tint(base: QColor, level: float) -> QColor:
    """A colour at a brightness, clamped to the byte range."""
    return QColor(max(0, min(255, int(base.red() * level))),
                  max(0, min(255, int(base.green() * level))),
                  max(0, min(255, int(base.blue() * level))))


def pole_on_screen(camera: render3d.Camera, spin: float, tilt: float) -> tuple:
    """Where the world's axis points, as seen: (screen 2-vector, depth).

    The screen part says which way north lies on the picture; the depth part is
    how much of the axis is pointing at or away from the eye, and it is what
    squashes a circle of latitude into an ellipse. At depth 1 the pole faces the
    eye and the latitudes are concentric circles; at 0 the pole lies across the
    view and they are straight lines.
    """
    # The mesh path spins about the model's own pole then tilts it over, so the
    # axis ends up here. Same order, so a world drawn either way is oriented the
    # same and the two can be compared.
    axis = (0.0, math.sin(tilt), math.cos(tilt))
    right, up, ahead = (render3d.dot(axis, camera.right),
                        render3d.dot(axis, camera.up),
                        render3d.dot(axis, camera.fwd))
    flat = math.hypot(right, up)
    if flat < 1e-9:
        return (0.0, -1.0), 1.0
    # Screen y runs downward, so up on the picture is negative.
    return (right / flat, -up / flat), min(1.0, abs(ahead))


#: How many segments an ellipse of latitude is drawn with. It is a smooth curve
#: on the picture, so this only has to beat the pixel grid at the limb.
ARC = 40


def _cap_path(centre: QPointF, radius: float, pole: tuple, depth: float,
              lat: float) -> QPainterPath:
    """Everything south of one circle of latitude, clipped later to the disc.

    A circle of latitude projects to an ellipse: its centre sits `lat` of the way
    along the axis, its half-width across the axis is the circle's own radius,
    and its half-width *along* the axis is that squashed by how much the pole
    leans toward the eye. Painting the caps from north to south, each over the
    last, leaves a band of every colour between one boundary and the next.

    Built from explicit vectors rather than by rotating a box. A first draft used
    a `QTransform` and put the pole on the local *x* axis while the ellipse and
    the skirt both ran along *y* — ninety degrees out, which drew every world as
    a vertical split with the polar colour flooding the rest.
    """
    across = math.sqrt(max(0.0, 1.0 - lat * lat)) * radius
    along = across * depth
    px, py = pole
    qx, qy = -py, px                      # across the axis
    cx = centre.x() + px * lat * radius
    cy = centre.y() + py * lat * radius

    path = QPainterPath()
    # The ellipse, as a closed curve.
    first = True
    for step in range(ARC + 1):
        angle = math.tau * step / ARC
        ox, oy = math.cos(angle) * across, math.sin(angle) * along
        point = QPointF(cx + qx * ox + px * oy, cy + qy * ox + py * oy)
        if first:
            path.moveTo(point)
            first = False
        else:
            path.lineTo(point)
    path.closeSubpath()

    # And the skirt: from the ellipse's two extremes across the axis, away from
    # the pole and well past the disc, so the union is "this boundary and
    # everything south of it".
    far = radius * 3.0
    skirt = QPainterPath()
    left = QPointF(cx + qx * across, cy + qy * across)
    right = QPointF(cx - qx * across, cy - qy * across)
    skirt.moveTo(left)
    skirt.lineTo(right)
    skirt.lineTo(QPointF(right.x() - px * far, right.y() - py * far))
    skirt.lineTo(QPointF(left.x() - px * far, left.y() - py * far))
    skirt.closeSubpath()
    return path.united(skirt)


def _limb(painter: QPainter, disc: QPainterPath, centre: QPointF,
          radius: float, glare: float) -> None:
    """A thin bright ring where the atmosphere is seen edge-on.

    Added rather than multiplied, because it is light the world is putting out.
    It is the one cue that most makes a drawn ball read as a world rather than a
    coin, and it costs one more fill.
    """
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    halo = QRadialGradient(centre, radius)
    halo.setColorAt(0.0, QColor(0, 0, 0))
    halo.setColorAt(max(0.0, 1.0 - LIMB_WIDTH), QColor(0, 0, 0))
    edge = int(255 * LIMB_LIFT * min(1.0, glare))
    halo.setColorAt(1.0, QColor(edge, edge, edge))
    painter.setBrush(QBrush(halo))
    painter.drawPath(disc)


def draw(painter: QPainter, camera: render3d.Camera, paint, at,
         radius_km: float, light, spin: float = 0.0, tilt: float = 0.0,
         glare: float = 1.0) -> float:
    """Paint one world. Returns its screen radius, or 0 if nothing was drawn.

    `paint(lat)` is the same latitude-to-colour hook the meshes are built from —
    see `data/worlds3d.py` — so a world looks like itself whichever way it is
    drawn. `at` is the world's centre in the camera's frame and `light` is the
    direction the starlight travels *from*.
    """
    seen = camera.project(at)
    if seen is None:
        return 0.0
    centre, ahead = seen
    radius = render3d.screen_radius(camera, ahead, radius_km)
    if radius < 0.6:
        return 0.0

    pole, depth = pole_on_screen(camera, spin, tilt)
    disc = QPainterPath()
    disc.addEllipse(QRectF(centre.x() - radius, centre.y() - radius,
                           radius * 2, radius * 2))

    painter.save()
    painter.setClipPath(disc)
    painter.setPen(QColor(0, 0, 0, 0))

    # The surface: caps from north to south, each over the last.
    for step in range(CAPS + 1):
        lat = 1.0 - 2.0 * step / CAPS
        colour = QColor(paint(lat))
        painter.setBrush(colour)
        painter.drawPath(_cap_path(centre, radius, pole, depth, lat))

    # The light, multiplied over it. **The gradient's centre is the sub-stellar
    # point itself, projected** — not a screen direction worked out from the
    # light vector. A first draft did the latter and came out evenly lit, because
    # the signs of "the direction light travels from" and "which way is up on the
    # picture" both had to be right at once and one of them was not.
    #
    # `render3d.draw` lights a face by `dot(normal, -light)`, so the brightest
    # point on the sphere is the one whose normal *is* `-light`: that is the
    # sub-stellar point, and it sits at `centre + -light * radius`. Projecting it
    # asks the camera the same question the mesh asks, so the two agree by
    # construction — and when the star is behind the world it lands off the disc
    # and leaves a crescent, which is what should happen.
    lit_from = render3d.unit(light)
    # How lit the middle of the disc is: its normal points at the eye, and
    # `render3d.draw` lights a face by `dot(normal, -light)`. So this one number
    # says which phase the world is in — +1 the star behind the camera and the
    # whole disc is day, 0 half and half, -1 the star behind the world.
    toward_eye = render3d.unit((camera.at[0] - at[0], camera.at[1] - at[1],
                                camera.at[2] - at[2]))
    mu = max(-1.0, min(1.0, render3d.dot(toward_eye,
                                         (-lit_from[0], -lit_from[1],
                                          -lit_from[2]))))
    # Which way the star lies on the picture. Taken from the projected
    # sub-stellar point, whose *direction* from the centre is right even when it
    # is round the back and its distance is not.
    sub = camera.project((at[0] - lit_from[0] * radius_km,
                          at[1] - lit_from[1] * radius_km,
                          at[2] - lit_from[2] * radius_km))
    dx, dy = 0.0, 0.0
    if sub is not None:
        dx, dy = sub[0].x() - centre.x(), sub[0].y() - centre.y()
        span = math.hypot(dx, dy)
        if span > 1e-9:
            dx, dy = dx / span, dy / span
    # **And how far along it the bright pole sits, from the phase rather than
    # from the projection.** A first draft used the projected distance and lit an
    # eclipsed world fully: the sub-stellar point can be on the *far* hemisphere,
    # where it still projects inside the disc and reads as noon. This puts it at
    # the centre at full day, on the limb at half, and clear of the disc when the
    # star is behind the world — which is a crescent and then nothing.
    off = radius * (1.0 - mu)
    hot = QPointF(centre.x() + dx * off, centre.y() + dy * off)
    # The falloff runs over a radius of surface, because that is what
    # `sin(theta)` spans from the sub-stellar point to the terminator.
    reach = radius

    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
    if dx == 0.0 and dy == 0.0:
        # **The star is exactly behind the camera or exactly behind the world,
        # and either way the disc is evenly lit.** There is no direction to run a
        # gradient along, and a first draft centred one on the disc anyway — which
        # drew an eclipsed world with a bright middle and a dark rim, the one
        # phase it cannot be. `mu` still says which of the two it is.
        flat = (render3d.AMBIENT
            + render3d.DIFFUSE * max(0.0, mu) * glare)
        painter.setBrush(_tint(QColor("#ffffff"), min(1.6, flat * glare)))
        painter.drawPath(disc)
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver)
        _limb(painter, disc, centre, radius, glare)
        painter.restore()
        return radius

    # Stops taken at known angles from the sub-stellar point. On a sphere the
    # surface `theta` away from that point is lit by `cos(theta)`, and it lands
    # `sin(theta)` of the radius away on the picture — so a stop at `sin(theta)`
    # carrying `AMBIENT + DIFFUSE * cos(theta)` is the real law, sampled.
    #
    # **Two passes, because a multiply can only darken.** `AMBIENT + DIFFUSE` is
    # 1.45 at the sub-stellar point, and a multiply by white at 1.45 is a multiply
    # by white at 1.0 — a no-op. So the first version lost the whole range above
    # unity: a grey surface that should have run 223 down to 62 ran *154* down to
    # 62, flat across the entire lit half, with the terminator a cliff 6% of the
    # face wide instead of a falloff.
    #
    # It also hid a mutation. Flattening every stop to full brightness changed
    # nothing on the picture, because every one of those stops was already clipped
    # to white — so the check on the terminator could not tell the difference, and
    # the surviving mutation was pointing straight at the defect. Which is what a
    # sweep is for.
    #
    # So: the multiply carries the part at or below unity, and a `Plus` pass
    # carries the excess above it. That excess goes on as grey rather than scaled
    # by the surface, because `Plus` has no way to know what is under it — which
    # lifts a bright subsolar point toward white. An overexposed one does look
    # like that, and this is an approximation said out loud rather than a law
    # claimed.
    shade = QRadialGradient(hot, reach)
    hotter = QRadialGradient(hot, reach)
    for degrees in (0, 20, 40, 55, 70, 82, 90):
        theta = math.radians(degrees)
        level = (render3d.AMBIENT
                 + render3d.DIFFUSE * math.cos(theta) * glare)
        where = min(1.0, math.sin(theta))
        shade.setColorAt(where, _tint(QColor("#ffffff"), min(1.0, level)))
        over = max(0.0, min(1.0, (level - 1.0) * OVER_BRIGHT))
        grey = int(255 * over)
        hotter.setColorAt(where, QColor(grey, grey, grey))
    # Past the terminator there is only what the sky lends it.
    shade.setColorAt(1.0, _tint(QColor("#ffffff"), render3d.AMBIENT))
    hotter.setColorAt(1.0, QColor(0, 0, 0))

    painter.setBrush(QBrush(shade))
    painter.drawPath(disc)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
    painter.setBrush(QBrush(hotter))
    painter.drawPath(disc)

    _limb(painter, disc, centre, radius, glare)

    painter.restore()
    return radius
