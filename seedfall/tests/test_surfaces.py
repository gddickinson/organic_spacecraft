"""A world you are in orbit over should look like a place.

Measured at the top of this cycle, with the conn's own viewport: at 200 km over
a 3,000 km world — which is where berthing happens, so it is the backdrop to
the whole docking activity — the frame was **one flat colour with three banding
arcs across it**. `data/worlds3d.py` paints a world by latitude, which buys
polar caps and a gas giant's belts for nothing and has one consequence nobody
had looked at: a world painted by latitude alone is *the same picture from every
side*, and from low orbit it is no picture at all.

`data/surfaces.py` gives a world features at a longitude as well as a latitude,
in two sizes: named ones the size of a continent, and a lattice of ground
texture fixed to the ground and sized to whatever the frame is holding.

The claims:

- **A world from low orbit has something in it.** The defect, measured the way
  it was found — as the variety of what is actually on the screen.
- **A world looks like itself.** Same body, same face, every time and every
  process — `hash()` is salted per run and would have re-skinned every world at
  every start.
- **Two worlds of a kind are two worlds**, not one repeated.
- **The far side is a different view.**
- **The ground holds still.** The lattice is named by where it is on the globe,
  so moving the camera does not re-seed it. Anything camera-seeded would boil
  as the hull manoeuvred, which is worse than a flat wash.
- **Nothing escapes the disc**, at any range.
- **A giant keeps its bands** and gets no blotches.
- **The cost is bounded** however close the hull gets.
"""

from __future__ import annotations

import math

from ..data import surfaces, worlds3d
from .harness import Suite


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _render(kind: str, name: str, dist_km: float, radius_km: float = 3000.0,
            spin: float = 0.0, size=(320, 260), detail: bool = True):
    """One world, painted the way the viewport paints it."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import render3d, spheres

    _app()
    image = QImage(size[0], size[1], QImage.Format.Format_RGB32)
    image.fill(QColor("#05070a"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                             width=size[0], height=size[1],
                             half_fov=math.radians(32))
    hook = None
    if detail:
        def hook(lat, lon, span, k=kind, n=name):
            return surfaces.detail_near(k, n, lat, lon, span)
    spheres.draw(painter, camera, worlds3d.paint_for(kind),
                 (0.0, 0.0, dist_km), radius_km, light=(-0.5, -0.3, 0.8),
                 spin=spin, tilt=0.35,
                 features=surfaces.features_for(kind, name),
                 stretch=surfaces.stretch_for(kind), detail=hook)
    painter.end()
    return image


def _tones(image, step: int = 3) -> set:
    """The distinct colours on a picture, coarsely quantised."""
    out = set()
    for y in range(0, image.height(), step):
        for x in range(0, image.width(), step):
            rgb = image.pixel(x, y)
            out.add(((rgb >> 16 & 0xFF) >> 3, (rgb >> 8 & 0xFF) >> 3,
                     (rgb & 0xFF) >> 3))
    return out


def _edges(image, step: int = 2) -> float:
    """How much local contrast a picture carries — the mark of structure.

    A smooth wash has almost none: the lit sphere's gradient moves a point or
    two between neighbouring pixels. Anything with edges in it — blotches,
    coastlines, craters — moves several. This is the honest measure of "is
    there something to look at", where counting distinct tones is not: the
    gradient alone already carries hundreds of tones and none of them are a
    feature.
    """
    total = seen = 0
    for y in range(0, image.height() - step, step):
        for x in range(0, image.width() - step, step):
            a, b = image.pixel(x, y), image.pixel(x + step, y)
            total += (abs((a >> 16 & 0xFF) - (b >> 16 & 0xFF))
                      + abs((a >> 8 & 0xFF) - (b >> 8 & 0xFF)))
            seen += 1
    return total / max(1, seen)


def _differ(a, b, step: int = 3) -> float:
    """The share of the *world* where two pictures disagree.

    Sampled over pixels that are world in one picture or the other rather than
    over the whole frame: a disc a tenth of the frame across can differ by at
    most a tenth of the frame however different it is, so a threshold set on the
    frame is really a threshold on the disc's size. The first version of this
    check measured the frame and read a picture that had changed over half the
    world as a 6% difference.
    """
    from PyQt6.QtGui import QColor
    sky = QColor("#05070a").rgb()
    seen = same = 0
    for y in range(0, a.height(), step):
        for x in range(0, a.width(), step):
            pa, pb = a.pixel(x, y), b.pixel(x, y)
            if pa == sky and pb == sky:
                continue
            seen += 1
            same += int(pa == pb)
    return 1.0 - same / max(1, seen)


def run(suite: Suite) -> None:
    check = suite.check

    @check("a world from low orbit is a place, not a wash of colour")
    def _():
        # The reading this cycle started from, taken the same way: at 200 km
        # over a 3,000 km world the frame is all world, and before this it held
        # one colour and the latitude banding.
        flat = _render("rocky", "Iron Bight I", 3200.0, detail=False)
        full = _render("rocky", "Iron Bight I", 3200.0, detail=True)
        bare, ground = _edges(flat), _edges(full)
        assert ground > bare * 2.0, (
            f"from low orbit the bare world carries {bare:.2f} of local "
            f"contrast and the surfaced one {ground:.2f} — there is still "
            "nothing in the frame to look at")
        moved = _differ(flat, full)
        assert moved > 0.25, (
            f"ground texture changes only {moved:.0%} of the world from 200 km")
        # And it is not merely noise: the picture still has large smooth
        # regions, which is what ground looks like rather than static.
        assert ground < 12.0, (
            f"{ground:.2f} of local contrast is not a surface, it is a rash")
        return (f"local contrast {bare:.2f} bare against {ground:.2f} with its "
                f"ground, over {moved:.0%} of the world")

    @check("a world looks like itself, in this run and the next")
    def _():
        # `hash()` is salted per process, so a world seeded from it would have
        # worn a different face at every start — the one thing a place must not
        # do. Pinned against written values rather than against the function.
        once = surfaces.features_for("rocky", "Iron Bight I")
        twice = surfaces.features_for("rocky", "Iron Bight I")
        assert once == twice
        assert len(once) == surfaces.RECIPES["rocky"]["count"]
        # A written figure: this body's first feature, to three places. If the
        # seeding ever becomes process-dependent this is what notices.
        lat, lon, size, _tone, _alpha = once[0]
        assert abs(lat - -0.040) < 0.002 and abs(lon - 3.132) < 0.002, (
            f"Iron Bight I's first feature has moved to {lat:.3f}, {lon:.3f}")
        assert abs(size - 0.399) < 0.002, size
        return (f"{len(once)} features, first at lat {lat:.3f} lon {lon:.3f}, "
                "stable across calls")

    @check("two worlds of a kind are two worlds")
    def _():
        names = ["Iron Bight I", "Iron Bight II", "Sable Terminus",
                 "Quill's Rise", "Amber Mouth"]
        sets = [surfaces.features_for("rocky", n) for n in names]
        for i, a in enumerate(sets):
            for b in sets[i + 1:]:
                assert a != b, "two bodies with the same surface"
        shots = [_render("rocky", n, 12000.0) for n in names[:3]]
        worst = min(_differ(shots[0], shots[1]), _differ(shots[0], shots[2]))
        assert worst > 0.25, (
            f"two rocky worlds differ over only {worst:.0%} of the world")
        return (f"{len(names)} rocky worlds, all different; the closest pair "
                f"differs over {worst:.0%} of the picture")

    @check("the far side is a different view")
    def _():
        near = _render("rocky", "Iron Bight I", 12000.0, spin=0.0)
        far = _render("rocky", "Iron Bight I", 12000.0, spin=math.pi)
        moved = _differ(near, far)
        assert moved > 0.30, (
            f"turning the world half way round changes {moved:.0%} of it — "
            "it is still the same from every longitude")
        return f"half a turn changes {moved:.0%} of the frame"

    @check("the ground holds still when the camera moves")
    def _():
        # The lattice is named by where it is on the globe. A lattice seeded
        # from the camera would give a different answer every frame and the
        # surface would boil, which is worse than a flat wash: a flat wash is
        # at least still.
        span = 0.30
        here = dict(((round(f[0], 6), round(f[1], 6)), f)
                    for f in surfaces.detail_near("rocky", "Iron Bight I",
                                                  0.2, 1.0, span))
        # The same patch, looked at from a camera that has slid a little along
        # the ground. Every cell they share must be identical.
        there = surfaces.detail_near("rocky", "Iron Bight I", 0.2 + span * 0.12,
                                     1.0, span)
        shared = agreed = 0
        for f in there:
            key = (round(f[0], 6), round(f[1], 6))
            if key in here:
                shared += 1
                agreed += int(here[key] == f)
        assert shared >= 8, f"only {shared} cells in common to compare"
        assert agreed == shared, (
            f"{shared - agreed} of {shared} shared cells changed when the "
            "camera moved — the ground is seeded from the wrong thing")
        return f"{shared} cells in common, every one unchanged"

    @check("nothing is painted outside the world's edge")
    def _():
        from PyQt6.QtGui import QColor
        size = (320, 260)
        image = _render("rocky", "Iron Bight I", 26000.0, size=size)
        # The disc is centred and its radius is known from the same call the
        # renderer makes, so this is the renderer's own answer for where the
        # edge is, not a guess.
        from ..ui import render3d
        camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                                 width=size[0], height=size[1],
                                 half_fov=math.radians(32))
        radius = render3d.screen_radius(camera, 26000.0, 3000.0)
        assert 20 < radius < size[1] / 2, radius
        sky = QColor("#05070a").rgb()
        stray = 0
        for y in range(0, size[1], 2):
            for x in range(0, size[0], 2):
                dx, dy = x - size[0] / 2, y - size[1] / 2
                if math.hypot(dx, dy) > radius + 3:
                    stray += int(image.pixel(x, y) != sky)
        assert stray == 0, f"{stray} sampled pixels of world outside its disc"
        return f"a disc of {radius:.0f} px, and nothing painted beyond it"

    @check("a giant keeps its bands, and gets no blotches")
    def _():
        assert "gas" in surfaces.NO_GROUND
        assert surfaces.detail_near("gas", "Vaunt IV", 0.0, 0.0, 0.4) == ()
        assert surfaces.stretch_for("gas") > 1.5, (
            "a giant's storms should be sheared along the band")
        assert surfaces.stretch_for("rocky") == 1.0
        # And it still reads as banded: sampling a column down the middle of
        # the disc crosses several distinct tones.
        image = _render("gas", "Vaunt IV", 240000.0, radius_km=60000.0)
        column = {image.pixel(image.width() // 2, y) >> 3
                  for y in range(60, image.height() - 60, 2)}
        assert len(column) > 8, (
            f"a column down the giant crosses {len(column)} tones — the bands "
            "have gone")
        # And "along the band" is a geometric claim, not a number: the axis a
        # storm is stretched along must be east — tangent to the world at that
        # point, and square to the pole. Checked here because the picture
        # cannot tell: with five storms on a giant, shearing them the wrong way
        # moves too few pixels for a rendered check to notice, which is exactly
        # what the mutation sweep found.
        from ..ui import surface as surface_ui
        for lat, lon in ((0.0, 0.0), (0.4, 1.9), (-0.7, 4.2)):
            east, north = surface_ui.tangents(lat, lon, 0.3, 0.35)
            here = surface_ui.direction(lat, lon, 0.3, 0.35)
            # The pole exactly, not a latitude a micro-radian short of it:
            # `direction(pi/2 - 1e-6, ...)` leans by that micro-radian and the
            # check failed on its own approximation rather than on the code.
            pole = (0.0, -math.sin(0.35), math.cos(0.35))
            from ..ui import render3d
            assert abs(render3d.dot(east, here)) < 1e-9, (
                "east is not tangent to the world")
            assert abs(render3d.dot(east, pole)) < 1e-9, (
                f"east at lat {lat} leans {render3d.dot(east, pole):.3f} "
                "toward the pole — a storm sheared along it crosses the bands")
            assert abs(render3d.dot(north, here)) < 1e-9
        return (f"no ground lattice, storms sheared "
                f"{surfaces.stretch_for('gas'):.1f}x along an axis square to "
                f"the pole, {len(column)} tones down the middle")

    @check("the lattice is bounded however close the hull gets")
    def _():
        # A list fine enough for low orbit would be tens of thousands of
        # features. A lattice is sized to the view, so the count is about the
        # same at every range — which is the property that makes it affordable.
        counts = []
        for span in (1.2, 0.6, 0.3, 0.08, 0.02, 0.004):
            got = surfaces.detail_near("rocky", "Iron Bight I", 0.1, 0.5, span)
            counts.append(len(got))
        assert max(counts) <= 200, (
            f"the lattice reaches {max(counts)} features in one frame: {counts}")
        # The floor is allowed to thin it: once a cell cannot subdivide further
        # the hull is metres off the surface and one cell fills the frame. What
        # must not happen is a *swing* at the ranges anybody flies at.
        flown = counts[:5]
        assert min(flown) >= 60, f"the lattice thins to {min(flown)}: {counts}"
        assert max(flown) <= min(flown) * 2, (
            f"the count swings {min(flown)}–{max(flown)} across ordinary "
            f"ranges: {counts}")
        # And the cell never subdivides past its floor, however close.
        assert surfaces.cell_angle(1e-9) == surfaces.CELL_MIN
        assert surfaces.cell_angle(50.0) == surfaces.CELL_MAX
        return (f"{min(counts)}–{max(counts)} features across a range of "
                f"{len(counts)} spans, clamped at both ends")
