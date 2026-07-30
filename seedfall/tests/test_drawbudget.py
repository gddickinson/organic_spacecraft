"""What a frame costs, and that paying less buys the same picture.

Measured in the conn's own window during an approach — the live 3D view the
whole docking activity happens inside:

    conn window          47.0 ms   ->  21 frames a second
    six camera feeds     31.2 ms   of that
    the 782x455 main     12.0 ms

The six feeds are **170x92 pixels each** and cost more together than the main
view at twenty times the area, because the cost was never pixel-bound. Each one
drew all ninety-six latitude bands of a world whose disc was 301 pixels across
and of which the frame showed a corner, and asked for an outline for every
feature of the ground lattice whether or not it could land on the picture.

Two culls, and both must be *exactly* invisible:

- a latitude band paints nothing when every corner of the frame lies north of
  its boundary;
- a feature outline paints nothing when its bounding box misses the frame.

The claims:

- **The picture is identical.** Not "close" — the same pixels, at several sizes
  and on several kinds of subject.
- **The frame is cheaper**, measured on the window that was slow.
- **A cull's bound is never optimistic**, which is the property that makes the
  first claim hold rather than a coincidence of the seeds tried.
"""

from __future__ import annotations

import math
import time

from ..core.state import new_game
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import track as track_sim
from .harness import Suite


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _approach(kind: str = "anchorage", range_km: float | None = 1.4,
              seed: str = "budget"):
    game = new_game(seed)
    flight.travel_to(game, 0)
    contact = next(c for c in track_sim.contacts(game) if c.kind == kind)
    return conn_sim.start(game, contact, range_km=range_km)


def _world_fills_the_frame(conn) -> bool:
    """Is there a world here big enough for the bands to be worth counting?"""
    from ..sim import sky as sky_sim
    return any(s.kind == "body" and s.radius_km > 2000.0
               for s in sky_sim.shapes(conn.sky))


def _shot(conn, size, view: str = "fore"):
    from ..ui.viewport import Viewport
    keep = _app()
    assert keep is not None
    feed = Viewport(conn, view)
    feed.resize(size[0], size[1])
    return feed.grab().toImage()


def _differ(a, b) -> int:
    return sum(1 for y in range(a.height()) for x in range(a.width())
               if a.pixel(x, y) != b.pixel(x, y))


def run(suite: Suite) -> None:
    check = suite.check

    @check("culling a band or a blotch changes not one pixel")
    def _():
        # The claim the whole cycle rests on, checked by rendering each frame
        # twice — once as shipped, once with both culls forced off — and
        # comparing every pixel. The first version of the feature bound used
        # the longer of the ellipse's two arms rather than its actual extent,
        # and moved sixteen pixels of a 782x455 approach; the first version of
        # the band bound compared the frame's centre against the cap's, which
        # is the same test with the boundary shrunk to a point.
        from ..ui import spheres, surface

        seen = pixels = 0
        # The seeds matter: "cull" is the approach whose 782x455 frame caught
        # the first feature bound out by sixteen pixels, and a check that did
        # not fly it let two weakenings of that bound straight back through.
        for seed, kind, range_km in (("budget", "anchorage", 1.4),
                                     ("budget", "body", None),
                                     ("cull", "body", None),
                                     ("silhouette", "anchorage", 1.4)):
            conn = _approach(kind, range_km, seed=seed)
            for size in ((170, 92), (782, 455), (360, 290)):
                for view in ("fore", "port"):
                    shipped = _shot(conn, size, view)
                    show_all = spheres.cap_shows
                    outline = surface.outline
                    spheres.cap_shows = lambda *a, **k: True
                    surface.outline = _uncull(outline)
                    try:
                        plain = _shot(conn, size, view)
                    finally:
                        spheres.cap_shows = show_all
                        surface.outline = outline
                    pixels += _differ(shipped, plain)
                    seen += 1
        assert pixels == 0, (
            f"{pixels} pixels differ across {seen} renders — a cull that "
            "alters the picture is not a cull")
        return f"{seen} renders, two subjects, three sizes: not one pixel moved"

    @check("a bound used for culling is never optimistic")
    def _():
        # The property that makes the check above hold generally rather than on
        # the seeds it happens to try: the box a feature is culled against must
        # contain every point the outline actually reaches.
        from ..ui import render3d, surface

        keep = _app()
        assert keep is not None
        camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                                 width=400, height=300,
                                 half_fov=math.radians(30))
        at, radius_km = (0.0, 0.0, 9000.0), 3000.0
        worst = 0.0
        tried = 0
        for lat in (-1.1, -0.9, -0.6, -0.4, -0.1, 0.0, 0.3, 0.5, 0.8, 1.0):
            for lon in (0.0, 0.7, 1.3, 2.1, 2.9, 3.6, 4.4, 5.1, 5.9):
                n = surface.direction(lat, lon, 0.3, 0.35)
                shape = surface.outline(camera, at, radius_km, n, 0.28,
                                        axes=surface.tangents(lat, lon, 0.3,
                                                              0.35))
                if shape is None:
                    continue
                tried += 1
                box = shape.boundingRect()
                middle = camera.project(
                    (at[0] + n[0] * radius_km, at[1] + n[1] * radius_km,
                     at[2] + n[2] * radius_km))
                assert middle is not None
                # The half-extents the cull would have used.
                reach_x = max(abs(box.left() - middle[0].x()),
                              abs(box.right() - middle[0].x()))
                reach_y = max(abs(box.top() - middle[0].y()),
                              abs(box.bottom() - middle[0].y()))
                worst = max(worst, reach_x, reach_y)
        assert tried >= 12, tried
        # And the wobble bound itself: `_rim` may never exceed it.
        peak = max(surface._rim(phase / 7.0, angle / 11.0)
                   for phase in range(44) for angle in range(70))
        assert peak <= surface.WOBBLE_MAX, (
            f"a blotch's rim reaches {peak:.3f} times its radius and the cull "
            f"bounds it at {surface.WOBBLE_MAX}")
        return (f"{tried} outlines measured; the rim peaks at {peak:.2f} "
                f"against a bound of {surface.WOBBLE_MAX}")

    @check("and the frame got cheaper where it was slow")
    def _():
        # The reading that started this: six 170x92 feeds cost more than the
        # 782x455 main view. Measured as *work* rather than as wall-clock, so
        # it says the same thing on a slow machine.
        #
        # Two claims, and the second is asked of the cull directly rather than
        # through a render. Which bands a given sky happens to show depends on
        # where the world is — seed after seed I read zero bands drawn and took
        # it for a broken patch, when it was the cull correctly rejecting all
        # ninety-six of a world the frame missed. A claim about a rule is
        # better asked of the rule.
        from ..ui import render3d, spheres, surface

        conn = _approach(seed="silhouette")
        assert _world_fills_the_frame(conn), "no world here to draw"
        outlines = {}
        for size in ((170, 92), (782, 455)):
            asked = {"n": 0}
            real_out = surface.outline

            def out(*a, _r=real_out, **k):
                got = _r(*a, **k)
                asked["n"] += int(got is not None)
                return got

            surface.outline = out
            try:
                _shot(conn, size)
            finally:
                surface.outline = real_out
            outlines[size] = asked["n"]
        assert outlines[(170, 92)] < outlines[(782, 455)], outlines

        # And the bands: the same world, the same disc, two frames. A small one
        # can show fewer of them, so fewer should survive.
        keep = _app()
        assert keep is not None
        from PyQt6.QtCore import QPointF
        centre, radius = QPointF(90.0, 40.0), 300.0
        pole, depth = (0.32, -0.94), 0.55
        def kept(w: int, h: int, at: QPointF, size: float) -> int:
            camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1),
                                     up=(0, 1, 0), width=w, height=h,
                                     half_fov=math.radians(30))
            return sum(1 for step in range(spheres.CAPS + 1)
                       if spheres.cap_shows(camera, at, size, pole, depth,
                                            1.0 - 2.0 * step / spheres.CAPS))

        # Measured across three geometries rather than asserted at one, because
        # how much the cull saves depends entirely on where the world sits:
        #
        #   disc centre inside the frame     81 of 97 kept on a small frame
        #   disc centre off the frame        97 — nothing to save, and correct
        #   disc far larger than the frame   42 of 97, against 60 on a big one
        #
        # The middle row is the one worth writing down: a cull that saves
        # nothing at some geometries is not broken, and a bar set on the best
        # case would have called it so.
        survive = {}
        for w, h in ((170, 92), (782, 455)):
            survive[(w, h)] = kept(w, h, centre, radius)
        assert survive[(170, 92)] < survive[(782, 455)], survive
        huge = {size: kept(size[0], size[1], QPointF(-400.0, 600.0), 900.0)
                for size in ((170, 92), (782, 455))}
        assert huge[(170, 92)] < spheres.CAPS * 0.55, (
            f"a world far larger than a 170x92 frame still keeps "
            f"{huge[(170, 92)]} of {spheres.CAPS} bands")
        assert huge[(170, 92)] < huge[(782, 455)], huge

        # And the renderer really uses it: a frame that shows a world paints
        # fewer bands than the table holds. Counted at `_cap_path`, which only
        # runs for a band that survived.
        painted = {"n": 0}
        real_path = spheres._cap_path

        def path(*a, _r=real_path, **k):
            painted["n"] += 1
            return _r(*a, **k)

        spheres._cap_path = path
        try:
            _shot(conn, (360, 290))
        finally:
            spheres._cap_path = real_path
        assert painted["n"] < spheres.CAPS + 1, (
            f"a frame showing a world painted all {painted['n']} bands — the "
            "cull is not reaching the renderer")
        # The size law itself: a world a few pixels across cannot show ninety
        # six bands, and paying for them was a fixed cost at every scale.
        assert spheres.cap_count(6.0) <= spheres.CAPS_MIN
        assert spheres.cap_count(6.0) < spheres.cap_count(400.0)
        assert spheres.cap_count(10_000.0) == spheres.CAPS
        return (f"a small feed asks for {outlines[(170, 92)]} blotches against "
                f"{outlines[(782, 455)]}; of a world larger than the frame it "
                f"keeps {huge[(170, 92)]} bands against {huge[(782, 455)]}; "
                f"a 360x290 frame paints {painted['n']} of {spheres.CAPS + 1}")


def _uncull(real):
    """`surface.outline` with its frame test disabled, for the comparison."""
    def wide(camera, at, radius_km, n, size, stretch=1.0, phase=0.0, axes=None):
        class _Wide:
            w = 10 ** 7
            h = 10 ** 7

            def __init__(self, camera):
                self._camera = camera

            def __getattr__(self, name):
                return getattr(self._camera, name)

        return real(_Wide(camera), at, radius_km, n, size, stretch, phase, axes)
    return wide
