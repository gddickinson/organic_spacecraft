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
from PyQt6.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPolygonF,
                         QRadialGradient)

from . import render3d, surface

#: How many latitude caps a world is painted in. Cheap — each is one clipped
#: fill against 2,640 polygons for the fine mesh — so this is set by what the eye
#: resolves rather than by what the budget allows. The caps crowd toward the
#: poles, where the cap colour also changes fastest, so a coarser count showed a
#: stack of arcs over the ice: ninety-six puts them under a pixel there and costs
#: about 3 ms more.
CAPS = 96

#: The fewest bands worth drawing, and how many pixels of disc each band is
#: allowed to cover. Ninety-six was a fixed cost paid at every size — measured
#: in the conn's own window, `_cap_path` ran **97 times a frame for 5.4 ms of a
#: 25 ms budget**, and a world 40 pixels across was being cut into bands two
#: fifths of a pixel wide. The bands crowd toward the poles, so the count is
#: taken against the disc's *diameter* and still lands under a pixel there.
CAPS_MIN = 12
PIXELS_PER_CAP = 2.0


def cap_count(radius: float) -> int:
    """How many latitude bands are worth drawing at this size on screen."""
    return max(CAPS_MIN, min(CAPS, int(radius * 2.0 / PIXELS_PER_CAP)))

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

#: How large a world has to be on screen, as a share of the smaller side of the
#: frame, before ground texture is drawn under it. Below this the disc is small
#: enough that the named features are the whole story and a detail cell would be
#: sub-pixel — paying for a lattice to draw nothing.
#:
#: Set by looking rather than guessed. At 0.30 a world seen whole — the ordinary
#: view from a few diameters out, which is most of the time anybody looks at one
#: — got no texture at all and stayed the smooth ball this cycle set out to fix;
#: only the low-orbit case improved. 0.12 is a disc about a quarter of the frame
#: across, where a detail cell is still several pixels.
DETAIL_FROM = 0.12

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


def cap_shows(camera, centre: QPointF, radius: float, pole: tuple,
              depth: float, lat: float) -> bool:
    """Could this band paint anything the frame can see?

    A cap is "everything south of a circle of latitude", drawn north to south
    with each over the last — so one whose boundary ellipse lies entirely off
    the frame *and* whose southern side faces away paints nothing visible, and
    can be skipped without changing a pixel.

    This is where a close approach spends its afternoon. Measured in the conn's
    own window: six camera feeds of 170x92 pixels cost **31 ms of a 44 ms
    frame** — more than the 782x455 main view — because each one drew all
    ninety-six bands of a world whose disc was 301 pixels across and of which
    the frame showed a corner. The geometry cost did not scale with the widget
    at all.
    """
    across = math.sqrt(max(0.0, 1.0 - lat * lat)) * radius
    along = across * abs(depth)
    px, py = pole
    cx = centre.x() + px * lat * radius
    cy = centre.y() + py * lat * radius

    # The cap covers everything from its boundary southward, and the boundary
    # is an ellipse reaching `along` either side of the circle of latitude. So
    # it paints nothing here only when **every corner of the frame** lies north
    # of the boundary's southernmost edge.
    #
    # A first version compared the frame's *centre* against the cap's centre,
    # which is the same test with the ellipse shrunk to a point — and near the
    # limb the ellipse is wide enough for the frame to straddle it. That drew
    # sixteen pixels of a 782x455 approach differently, which is the whole
    # optimisation invalidated: a cull that changes the picture is not a cull.
    south_x, south_y = -px, -py
    for corner_x, corner_y in ((0.0, 0.0), (camera.w, 0.0),
                               (0.0, camera.h), (camera.w, camera.h)):
        reach = ((corner_x - cx) * south_x + (corner_y - cy) * south_y)
        if reach >= -along:
            return True
    return False


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
         glare: float = 1.0, features=(), stretch: float = 1.0,
         detail=None) -> float:
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
    # **How far away, not how far ahead.** `camera.project` hands back the
    # component of the offset along the view axis, and this passed that to
    # `screen_radius` as the range. On the axis the two agree and everything
    # looked right; off it, `ahead` shrinks toward zero however far away the
    # world is, and `screen_radius` — `tan(asin(r/d))` — runs away as `d` falls
    # under `r`.
    #
    # Measured in the conn on an ordinary approach: a 2,419 km world 2,981 km
    # off, sitting 73° from the view axis, was drawn with a screen radius of
    # **5,611 pixels instead of 335** — a wall of planet across a 360×290 frame,
    # where the true silhouette covers a corner of it. That is why every
    # berthing approach looked out at a flat wash of colour, and why the surface
    # work of the last two cycles kept failing to show: there was nothing wrong
    # with the ground, the ground was thirty metres from the lens.
    rel = (at[0] - camera.at[0], at[1] - camera.at[1], at[2] - camera.at[2])
    span = math.sqrt(render3d.dot(rel, rel))
    radius = render3d.screen_radius(camera, span, radius_km)
    if radius < 0.6:
        return 0.0

    pole, depth = pole_on_screen(camera, spin, tilt)
    # The world's *true* outline. A screen circle of `radius` about the
    # projected centre is right only on the axis: see `surface.limb`, and the
    # approach it made look out at a flat wash of colour.
    disc = QPainterPath()
    edge = surface.limb(camera, at, radius_km)
    if edge:
        disc.addPolygon(QPolygonF(edge))
        disc.closeSubpath()
    else:
        disc.addEllipse(QRectF(centre.x() - radius, centre.y() - radius,
                               radius * 2, radius * 2))

    painter.save()
    painter.setClipPath(disc)
    painter.setPen(QColor(0, 0, 0, 0))

    # The surface: caps from north to south, each over the last, at whatever
    # count this world's size on screen can actually show.
    caps = cap_count(radius)
    for step in range(caps + 1):
        lat = 1.0 - 2.0 * step / caps
        if not cap_shows(camera, centre, radius, pole, depth, lat):
            continue
        colour = QColor(paint(lat))
        painter.setBrush(colour)
        painter.drawPath(_cap_path(centre, radius, pole, depth, lat))

    # And what is on it at a longitude as well as a latitude. Painted here,
    # between the ground and the light, so a feature on the night side is dark
    # for the same reason the ground under it is — and clipped by the disc
    # already set, so one overrunning the limb is cut by the world's own edge.
    surface.draw(painter, camera, at, radius_km, features, spin, tilt, stretch)

    # Then the ground texture, at whatever scale the frame is holding. The
    # named features above are continents: right for looking at a globe, and
    # bigger than the picture from low orbit, where berthing happens and where
    # the whole frame was one flat colour before this. `surfaces.detail_near`
    # is a lattice fixed to the ground rather than a list, so it costs the
    # cells in view and the same patch looks the same every time.
    if detail and radius > DETAIL_FROM * min(camera.w, camera.h):
        span = surface.visible_span(camera, at, radius_km)
        lat0, lon0 = surface.looking_at(camera, at, radius_km, spin, tilt)
        surface.draw(painter, camera, at, radius_km,
                     detail(lat0, lon0, span), spin, tilt, stretch)

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
