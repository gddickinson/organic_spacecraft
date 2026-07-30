"""Painting a world's features onto its disc.

`ui/spheres.py` draws a world as a lit disc with latitude caps clipped inside
it. This adds the other axis: a feature sits at a latitude *and a longitude*,
so it comes round with the world and the far side is a different view.

**A circle drawn on a sphere projects to an ellipse**, and the honest way to get
that ellipse is to ask the camera rather than to derive it. Take the feature's
centre `n` and two perpendicular tangents `t1`, `t2`; the cap's rim in those
directions is `cos(a)·n ± sin(a)·t`, which are points on the sphere like any
other. Project the centre and one rim point per tangent, and the two screen
vectors that come back are conjugate radii of exactly the ellipse wanted — so
the outline is `centre + v1·cos φ + v2·sin φ`, and it is right at any range,
foreshortening at the limb included, without a single trigonometric special
case. The first draft sized the ellipse from the disc's screen radius and a
cosine, which is the orthographic answer and visibly wrong from 200 km up,
where the disc's radius is four screens wide.

Everything is painted *before* `spheres.draw` multiplies the light over the
disc, so a feature on the night side is dark for the same reason the ground
under it is. Nothing here decides where a feature is — that is
`data/surfaces.py`, which keeps a world looking like itself.
"""

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPolygonF

from . import render3d

#: How many points an outline is drawn with, at the ends of its range. A fixed
#: twelve was fine for a continent seen from a distance and read as a visible
#: dodecagon once ground texture put a blob a hundred pixels wide in the frame,
#: so it is chosen from the size on screen instead: cheap where it is small,
#: round where it is large.
OUTLINE_MIN, OUTLINE_MAX = 8, 22

#: A feature nearer the limb than this — measured as the cosine of the angle
#: between it and the direction to the eye — is dropped. At the limb itself the
#: ellipse degenerates to a line and the projection of its rim starts landing
#: behind the camera on a close pass.
EDGE_COSINE = 0.12


def tangents(lat: float, lon: float, spin: float, tilt: float) -> tuple:
    """East and north at a point on the globe, in the camera's frame.

    Not an arbitrary pair. The first version took any two vectors perpendicular
    to the feature's normal, which is fine for a round blotch and wrong the
    moment one is stretched: a gas giant's storms came out splayed along
    whatever direction the arbitrary basis happened to pick, and the giant read
    as a splash rather than as weather. Weather on a banded world runs *along
    the band*, so the stretch has to be along the line of latitude, which is
    east — and east is a thing with a definition.
    """
    heading = lon + spin
    east = (-math.sin(heading), math.cos(heading), 0.0)
    ct, st = math.cos(tilt), math.sin(tilt)
    east = (east[0], east[1] * ct - east[2] * st, east[1] * st + east[2] * ct)
    n = direction(lat, lon, spin, tilt)
    return render3d.unit(east), render3d.unit(render3d.cross(n, east))


def direction(lat: float, lon: float, spin: float, tilt: float) -> tuple:
    """Where a feature points, in the camera's frame.

    The same spin-then-tilt the meshes get in `render3d.draw`, so a feature and
    the mesh of the same world would agree about which way round it is.
    """
    x = math.cos(lat) * math.cos(lon + spin)
    y = math.cos(lat) * math.sin(lon + spin)
    z = math.sin(lat)
    ct, st = math.cos(tilt), math.sin(tilt)
    return (x, y * ct - z * st, y * st + z * ct)


#: How far a feature's rim wanders from a circle, as a share of its radius.
#: Circles are what a cap of a sphere honestly is, and a frame full of them
#: reads as bokeh rather than as ground — the overlaps in particular, each a
#: perfect lens. Two harmonics of the polar angle is the cheapest thing that
#: turns a disc into a blotch, and it costs nothing: the outline was already a
#: polygon and this only moves its points.
WOBBLE = 0.34


def _rim(phase: float, angle: float) -> float:
    """The radius multiplier for a blotch at this angle round its rim.

    A function of the *angle*, not of the point index, so the shape is the same
    shape whether it is drawn with eight points or twenty-two — which it is,
    since the step count follows the size on screen.
    """
    # Three harmonics, and — the part the first version missed — *weights* that
    # vary with the feature's own phase. Fixed weights gave every blotch on the
    # world the same three-lobed notch, so a frame of them read as one shape
    # stamped out forty times, which is its own kind of pattern. The second
    # harmonic is the useful one: it stretches a blotch into an oval, which is
    # what most ground actually looks like.
    two = 0.30 + 0.40 * (0.5 + 0.5 * math.sin(phase * 1.7))
    three = 0.22 + 0.34 * (0.5 + 0.5 * math.sin(phase * 2.9 + 1.1))
    five = 0.14 + 0.22 * (0.5 + 0.5 * math.sin(phase * 4.3 + 2.2))
    return (1.0
            + WOBBLE * (two * math.sin(2.0 * angle + phase)
                        + three * math.sin(3.0 * angle + phase * 1.7)
                        + five * math.sin(5.0 * angle + phase * 2.3)))


def outline(camera: render3d.Camera, at, radius_km: float, n,
            size: float, stretch: float = 1.0,
            phase: float = 0.0, axes=None) -> QPolygonF | None:
    """The screen outline of a cap of angular radius `size` centred at `n`.

    None when it is round the back, over the limb, or off the lens.
    """
    toward_eye = render3d.unit((camera.at[0] - at[0], camera.at[1] - at[1],
                                camera.at[2] - at[2]))
    facing = render3d.dot(n, toward_eye)
    if facing < EDGE_COSINE:
        return None

    t1, t2 = axes if axes is not None else (
        render3d.unit(render3d.cross(n, (0.0, 0.0, 1.0)
                                     if abs(n[2]) < 0.9 else (1.0, 0.0, 0.0))),
        (0.0, 0.0, 0.0))
    if axes is None:
        t2 = render3d.unit(render3d.cross(n, t1))
    centre = camera.project((at[0] + n[0] * radius_km,
                             at[1] + n[1] * radius_km,
                             at[2] + n[2] * radius_km))
    if centre is None:
        return None
    middle = centre[0]

    arms = []
    for tangent, width in ((t1, size * stretch), (t2, size)):
        span = min(1.4, width)
        rim = tuple(math.cos(span) * n[i] + math.sin(span) * tangent[i]
                    for i in range(3))
        got = camera.project((at[0] + rim[0] * radius_km,
                              at[1] + rim[1] * radius_km,
                              at[2] + rim[2] * radius_km))
        if got is None:
            return None
        arms.append((got[0].x() - middle.x(), got[0].y() - middle.y()))

    (ax, ay), (bx, by) = arms
    reach = max(math.hypot(ax, ay), math.hypot(bx, by))
    steps = max(OUTLINE_MIN, min(OUTLINE_MAX, int(reach / 6) + OUTLINE_MIN))
    points = []
    for i in range(steps):
        phi = math.tau * i / steps
        wob = _rim(phase, phi)
        cs, sn = math.cos(phi) * wob, math.sin(phi) * wob
        points.append(QPointF(middle.x() + ax * cs + bx * sn,
                              middle.y() + ay * cs + by * sn))
    return QPolygonF(points)


def _latlon(v, spin: float, tilt: float) -> tuple:
    """A direction in the camera's frame, back to a place on the globe.

    The inverse of `direction`, which is what makes the detail lattice hold
    still: the cells are named by where they are on the *ground*, so the same
    patch answers the same way however the hull is moving.
    """
    ct, st = math.cos(tilt), math.sin(tilt)
    y = v[1] * ct + v[2] * st
    z = -v[1] * st + v[2] * ct
    lat = math.asin(max(-1.0, min(1.0, z)))
    lon = math.atan2(y, v[0]) - spin
    return lat, lon


def _meets(camera: render3d.Camera, at, radius_km: float, ray) -> tuple:
    """Where a ray from the eye meets the globe, as a direction from its centre.

    A ray that misses falls back to its closest approach, so a world at the
    edge of the frame still answers about the sliver of it that shows.
    """
    oc = (camera.at[0] - at[0], camera.at[1] - at[1], camera.at[2] - at[2])
    b = render3d.dot(oc, ray)
    c = render3d.dot(oc, oc) - radius_km * radius_km
    disc = b * b - c
    step = -b
    if disc >= 0.0:
        near = -b - math.sqrt(disc)
        if near > 0.0:
            step = near
    step = max(0.0, step)
    return render3d.unit((oc[0] + ray[0] * step, oc[1] + ray[1] * step,
                          oc[2] + ray[2] * step))


def looking_at(camera: render3d.Camera, at, radius_km: float, spin: float,
               tilt: float) -> tuple:
    """The place on the globe the camera's axis actually meets.

    **Not the point nearest the camera.** The first version used the
    sub-camera point — where the ground comes closest to the eye — which is
    the same place only when the world is dead ahead. In the conn's own window
    a world sits off to one side while the lens looks at a station: measured
    at 40° off the axis, the lattice was generated around a patch of ground
    that was not in the picture at all, and the frame stayed the flat wash the
    whole surface cycle set out to fix. Two bugs, and the same cause both
    times: asking about the world's *centre* when the question is about a
    direction.

    A ray that misses the disc falls back to its closest approach, so a world
    at the edge of the frame still textures the sliver of it that shows.
    """
    return _latlon(_meets(camera, at, radius_km, camera.fwd), spin, tilt)


def visible_span(camera: render3d.Camera, at, radius_km: float,
                 screen_radius: float = 0.0) -> float:
    """How much of the ground the frame holds, in radians of arc.

    **Measured with rays, not with a ratio of radii.** Two drafts got this
    wrong in the same direction and both left the docking view a flat wash:

    * the first divided the frame's half-diagonal by the disc's screen radius
      and took an arcsine, which is the orthographic answer — it assumes the
      whole hemisphere maps inside that radius. From 561 km over a 2,419 km
      world it said the frame held 0.043 radians of ground where the true
      figure is nearer 0.3, so the lattice cut cells eight times too fine and
      every feature came out about **one pixel**;
    * before that it took the horizon from the world's *forward* distance
      rather than its real one, which collapsed to nothing for any world off
      the axis.

    So: cast the axis ray and a corner ray at the globe and take the angle
    between where they land. No projection model, no small-angle assumption,
    and right whether the eye is a diameter away or skimming the surface.
    """
    axis = _meets(camera, at, radius_km, camera.fwd)
    focal = max(1e-6, camera.focal)
    corner = render3d.unit((
        camera.fwd[0] + (camera.right[0] * camera.w
                         + camera.up[0] * camera.h) * 0.5 / focal,
        camera.fwd[1] + (camera.right[1] * camera.w
                         + camera.up[1] * camera.h) * 0.5 / focal,
        camera.fwd[2] + (camera.right[2] * camera.w
                         + camera.up[2] * camera.h) * 0.5 / focal))
    edge = _meets(camera, at, radius_km, corner)
    spread = math.acos(max(-1.0, min(1.0, render3d.dot(axis, edge))))
    return max(1e-4, min(math.pi * 0.5, spread))


def draw(painter, camera: render3d.Camera, at, radius_km: float,
         features, spin: float = 0.0, tilt: float = 0.0,
         stretch: float = 1.0) -> int:
    """Paint a world's features. Returns how many landed.

    The caller has already clipped to the world's disc, so a feature that
    overruns the limb is cut by the world's own edge rather than by arithmetic.
    """
    if not features:
        return 0
    painter.setPen(QColor(0, 0, 0, 0))
    landed = 0
    for lat, lon, size, colour, alpha in features:
        n = direction(lat, lon, spin, tilt)
        # The phase is taken from where the feature *is*, so a blotch keeps its
        # own shape as the world turns rather than rippling.
        phase = (lat * 7.13 + lon * 3.77) % math.tau
        shape = outline(camera, at, radius_km, n, size, stretch, phase,
                        axes=tangents(lat, lon, spin, tilt))
        if shape is None:
            continue
        tone = QColor(colour)
        tone.setAlpha(alpha)
        painter.setBrush(tone)
        painter.drawPolygon(shape)
        landed += 1
    return landed


#: How many points the true silhouette of a world is drawn with. A sphere seen
#: off-axis has an elliptical outline, and 40 points is smooth at any size a
#: world is ever drawn — including one filling the frame, where the visible arc
#: is a small part of the whole and every point of it counts.
LIMB_POINTS = 40

#: How far in front of the lens the silhouette is clipped, in km. Not zero: a
#: point exactly on the lens plane projects to infinity.
NEAR_PLANE = 1e-4


def limb(camera: render3d.Camera, at, radius_km: float) -> list:
    """The world's true outline on screen, as projected points.

    **A sphere's silhouette is only a circle when you are looking straight at
    it.** `spheres.draw` took the projected centre and drew a screen circle of
    `render3d.screen_radius` around it, which is exact on the axis and steadily
    wrong off it. Measured in the conn during an approach: a 2,419 km world
    2,981 km away sat 73° off the view axis with an angular radius of 54°, so
    the frame should have shown a curved limb across part of it — and instead
    the whole picture was filled, because the stand-in circle had a radius of
    5,392 pixels and a centre far off screen. Everything painted afterwards —
    the latitude bands, the terminator, the ground texture — was clipped to
    that, which is why a docking approach looked out at a flat wash of colour
    however much detail was drawn.

    The honest outline is the tangent circle itself: the points where the line
    of sight grazes the sphere lie on a circle perpendicular to the direction
    to the centre, at `r²/d` back from it, of radius `r·sqrt(1 - r²/d²)`. Those
    are points in space like any others, so projecting them asks the camera the
    same question everything else asks.

    Returns an empty list when the eye is inside the sphere, which is not a
    picture this renderer has any answer for.
    """
    rel = (at[0] - camera.at[0], at[1] - camera.at[1], at[2] - camera.at[2])
    span = math.sqrt(render3d.dot(rel, rel))
    if span <= radius_km * 1.0001:
        return []
    to_centre = (rel[0] / span, rel[1] / span, rel[2] / span)
    back = radius_km * radius_km / span
    ring = radius_km * math.sqrt(max(0.0, 1.0 - (radius_km / span) ** 2))
    hub = (at[0] - to_centre[0] * back,
           at[1] - to_centre[1] * back,
           at[2] - to_centre[2] * back)
    seed = (0.0, 0.0, 1.0) if abs(to_centre[2]) < 0.9 else (1.0, 0.0, 0.0)
    t1 = render3d.unit(render3d.cross(to_centre, seed))
    t2 = render3d.unit(render3d.cross(to_centre, t1))
    # The silhouette in space, before it is projected.
    ring_points = []
    for i in range(LIMB_POINTS):
        angle = math.tau * i / LIMB_POINTS
        cs, sn = math.cos(angle) * ring, math.sin(angle) * ring
        ring_points.append((hub[0] + t1[0] * cs + t2[0] * sn,
                            hub[1] + t1[1] * cs + t2[1] * sn,
                            hub[2] + t1[2] * cs + t2[2] * sn))

    # Clipped against the lens before projecting, not abandoned at it. A world
    # near enough and far enough off the axis has part of its own silhouette
    # behind the camera, and the first version returned nothing at all in that
    # case — which is precisely the close approach the true outline was written
    # for. Each edge that crosses the plane contributes the point where it
    # crosses, which is what keeps the outline closed.
    def ahead_of(point) -> float:
        return render3d.dot((point[0] - camera.at[0], point[1] - camera.at[1],
                             point[2] - camera.at[2]), camera.fwd)

    kept = []
    for index, point in enumerate(ring_points):
        nxt = ring_points[(index + 1) % len(ring_points)]
        here, there = ahead_of(point), ahead_of(nxt)
        if here > NEAR_PLANE:
            kept.append(point)
        if (here > NEAR_PLANE) != (there > NEAR_PLANE):
            share = (NEAR_PLANE - here) / (there - here)
            kept.append(tuple(point[k] + (nxt[k] - point[k]) * share
                              for k in range(3)))
    if len(kept) < 3:
        return []

    out = []
    for point in kept:
        got = camera.project(point)
        if got is None:
            return []
        out.append(got[0])
    return out
