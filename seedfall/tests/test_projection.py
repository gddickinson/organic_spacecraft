"""How big a world is on screen, and where its edge actually falls.

`ui/spheres.py` drew a world as a disc: project the centre, take
`render3d.screen_radius`, clip everything to a circle of that radius. It passed
`camera.project`'s second return value as the range — and that value is the
component of the offset **along the view axis**, not the distance.

On the axis the two agree, which is why every synthetic render of a world ever
made for this project looked right. Off the axis `ahead` falls toward zero
however far away the world is, and `screen_radius` is `tan(asin(r/d))·focal`,
which runs away as `d` drops under `r`.

Measured in the conn on an ordinary approach to a station — the case the whole
docking view exists for — a 2,419 km world 2,981 km off, 73° from the view axis:

    screen radius drawn      5,611 px      on a 360x290 frame
    screen radius true         335 px
    frame covered in ground       99%  ->  15%

So a berthing approach looked out at a featureless wall of planet, and two
cycles of surface work went into ground that was being drawn thirty metres from
the lens. The picture now shows space, stars, the lit station, the sun, and the
world's limb curving across a corner of the frame.

The claims:

- **A world is sized by its distance**, and the two agree on the axis.
- **A world off the axis does not fill the frame**, and space is still visible.
- **The outline is the true silhouette** — the tangent circle projected — which
  is an ellipse off-axis and reaches into the frame where a screen circle about
  the projected centre does not.
- **A silhouette partly behind the lens is clipped, not abandoned**, which is
  exactly the close approach the outline was written for.
"""

from __future__ import annotations

import math

from ..data import surfaces, worlds3d
from .harness import Suite

FRAME = (360, 290)


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _camera(at=(0.0, -1.4, 0.0), forward=(0.0, 1.0, 0.0)):
    from ..ui import render3d
    _app()
    return render3d.Camera(at=at, forward=forward, up=(0.0, 0.0, 1.0),
                           width=FRAME[0], height=FRAME[1],
                           half_fov=math.radians(30))


def _paint(camera, at, radius_km: float):
    """Draw one world on a black frame and hand back (image, screen radius)."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import spheres

    image = QImage(FRAME[0], FRAME[1], QImage.Format.Format_RGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    radius = spheres.draw(painter, camera, worlds3d.paint_for("rocky"), at,
                          radius_km, light=(-0.5, -0.3, 0.8), tilt=0.42,
                          features=surfaces.features_for("rocky", "Probe"),
                          detail=lambda a, b, c: surfaces.detail_near(
                              "rocky", "Probe", a, b, c))
    painter.end()
    return image, radius


def _covered(image) -> float:
    """The share of the frame that is not empty space."""
    from PyQt6.QtGui import QColor
    black = QColor("#000000").rgb()
    seen = painted = 0
    for y in range(0, image.height(), 3):
        for x in range(0, image.width(), 3):
            seen += 1
            painted += int(image.pixel(x, y) != black)
    return painted / max(1, seen)


def run(suite: Suite) -> None:
    check = suite.check

    @check("a world is sized by how far away it is, not by how far ahead")
    def _():
        from ..ui import render3d
        camera = _camera()
        # The reading from the conn: 2,419 km of world, 2,981 km off, 73° from
        # the axis. `ahead` for that geometry is 851 km — under the radius, so
        # the old arithmetic asked for the tangent of nearly a right angle.
        at = (-110.3, 849.2, -2854.4)
        radius_km = 2419.0
        rel = tuple(at[i] - camera.at[i] for i in range(3))
        span = math.sqrt(render3d.dot(rel, rel))
        ahead = render3d.dot(rel, camera.fwd)
        assert ahead < radius_km < span, (ahead, radius_km, span)

        _image, drawn = _paint(camera, at, radius_km)
        want = render3d.screen_radius(camera, span, radius_km)
        wrong = render3d.screen_radius(camera, ahead, radius_km)
        assert abs(drawn - want) < 1.0, (drawn, want)
        assert wrong > want * 8, (
            "this geometry no longer separates the two readings")
        return (f"{radius_km:,.0f} km at {span:,.0f} km and "
                f"{math.degrees(math.acos(ahead / span)):.0f}° off axis: drawn "
                f"at {drawn:.0f} px, not the {wrong:.0f} px the forward "
                "distance asks for")

    @check("and on the axis the two answers are the same")
    def _():
        # The fix must not move the case that was already right — which is
        # every synthetic render this project has ever judged a world by.
        from ..ui import render3d
        camera = _camera(at=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0))
        at = (0.0, 0.0, 12000.0)
        _image, drawn = _paint(camera, at, 3000.0)
        want = render3d.screen_radius(camera, 12000.0, 3000.0)
        assert abs(drawn - want) < 0.01, (drawn, want)
        return f"dead ahead, {drawn:.1f} px — unchanged"

    @check("a world off the axis leaves the rest of the sky alone")
    def _():
        # The defect as a picture: the frame was 99% ground.
        camera = _camera()
        image, _radius = _paint(camera, (-110.3, 849.2, -2854.4), 2419.0)
        share = _covered(image)
        # Bounded on both sides and measured, not merely "less than everything".
        # The geometry puts 15% of the frame under this world. A first version
        # allowed anything under 55% and let a silhouette **71% oversized** —
        # the tangent ring drawn at the sphere's full radius rather than at
        # `r·sqrt(1 - (r/d)²)` — pass at 38%, which is the mutation sweep
        # earning its keep.
        assert 0.06 < share < 0.26, (
            f"the world covers {share:.0%} of the frame; from this geometry it "
            "holds about 15% of it and leaves the rest to space")
        return f"{share:.0%} of the frame is world, and the rest is sky"

    @check("the outline is the true silhouette, not a circle at the centre")
    def _():
        # A sphere's outline is a circle only when you look straight at it. For
        # this geometry the projected centre is off the top of the frame and a
        # circle of the true radius about it does not touch the picture at all,
        # so a renderer that clipped to one would show nothing — while the real
        # silhouette reaches well into frame.
        from ..ui import render3d, surface
        camera = _camera()
        at, radius_km = (-110.3, 849.2, -2854.4), 2419.0
        rel = tuple(at[i] - camera.at[i] for i in range(3))
        span = math.sqrt(render3d.dot(rel, rel))
        centre = camera.project(at)
        assert centre is not None
        radius = render3d.screen_radius(camera, span, radius_km)
        # The circle: centred off the frame, and not reaching back to it. Which
        # side it falls on depends on the camera's `up`, so the claim is that it
        # misses — not that it misses upward, which is how the first version of
        # this line was written and why it failed on a camera held the other way.
        misses = (centre[0].y() + radius < 0
                  or centre[0].y() - radius > FRAME[1])
        assert misses, (
            f"a circle at y={centre[0].y():.0f} of radius {radius:.0f} already "
            "touches the frame — this case no longer tells the two apart")

        edge = surface.limb(camera, at, radius_km)
        assert len(edge) >= 3, "no silhouette at all"
        assert any(0 <= point.y() <= FRAME[1] for point in edge), (
            "the true outline never enters the frame either")
        image, _r = _paint(camera, at, radius_km)
        assert _covered(image) > 0.02, "and nothing was painted"
        near = min(abs(p.y()) for p in edge)
        gap = (centre[0].y() - radius if centre[0].y() > 0
               else abs(centre[0].y() + radius))
        return (f"{len(edge)} points of limb, reaching within {near:.0f} px of "
                f"the frame where a circle stops {gap:.0f} px short")

    @check("a silhouette partly behind the lens is clipped, not abandoned")
    def _():
        # The first version of `limb` returned nothing as soon as one point of
        # the tangent circle fell behind the camera — which is the close pass
        # it exists for. Walk a world in until part of it is behind the lens
        # and check the outline survives all the way.
        from ..ui import surface
        camera = _camera(at=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0))
        radius_km = 3000.0
        kept = 0
        for distance in (12000.0, 6000.0, 3600.0, 3100.0, 3010.0):
            at = (radius_km * 0.9, 0.0, distance)
            edge = surface.limb(camera, at, radius_km)
            assert len(edge) >= 3, (
                f"no outline at {distance:,.0f} km with the world off to one "
                "side — the close approach is exactly the case that matters")
            kept += 1
        # And inside the world there is no picture to draw, which is said
        # rather than guessed at.
        assert surface.limb(camera, (0.0, 0.0, 1000.0), radius_km) == []
        return f"{kept} closing ranges, an outline at every one"
