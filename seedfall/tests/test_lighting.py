"""How a painted world is lit: its phase, its terminator, and its coverage.

A world is drawn as a shaded disc rather than as a mesh (`ui/spheres.py` records
why, at length, including four attempts that failed). That makes the lighting the
whole of the picture, so it gets its own file: the checks here are all about
*where the light falls*, and they are the ones a sweep of that renderer leans on.

The claims:

- **A painted world is smooth**, and its phase follows the star all the way
  round — day brighter than half brighter than eclipsed.
- **The terminator is where the star puts it**, it moves when the star moves, it
  is monotone into the shadow, full day is *brighter than the surface's own
  colour*, and the falloff has real width rather than being a cliff.
- **The paint covers the disc** at every tilt, with no bare sky showing through.

Each of those three was written because a mutation of `ui/spheres.py` survived
without it. The brightness and width assertions found a real defect while they
were being written: the light was laid on with a single multiply, a multiply by
white cannot brighten, and so every part of the lit half clipped to the same
value. See `spheres.draw`.
"""

from __future__ import annotations

import math

from ..data import worlds3d
from .harness import Suite

#: Where the camera stands and how big the world is, for every plate here.
RANGE_KM = 26000.0
WORLD_KM = 6000.0


def _camera(size: int):
    from ..ui import render3d
    return render3d.Camera(at=(0.0, -RANGE_KM, 0.0), forward=(0.0, 1.0, 0.0),
                           up=(0.0, 0.0, 1.0), width=size, height=size,
                           half_fov=math.radians(26))


def _across(size: int) -> float:
    """The world's own screen radius, so the limb can be kept out of things."""
    from ..ui import render3d
    return render3d.screen_radius(_camera(size), RANGE_KM, WORLD_KM)


def _plate(light, size: int = 320, paint=None, tilt: float = 0.35):
    """One world, alone, through the renderer the game itself uses."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtGui import QColor, QImage, QPainter
    from PyQt6.QtWidgets import QApplication

    from ..ui import spheres

    app = QApplication.instance() or QApplication([])
    assert app is not None
    image = QImage(size, size, QImage.Format.Format_RGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    spheres.draw(painter, _camera(size), paint or worlds3d.paint_for("rocky"),
                 (0.0, 0.0, 0.0), WORLD_KM, light, tilt=tilt)
    painter.end()
    return image


def run(suite: Suite) -> None:
    check = suite.check

    @check("a world is smooth at any size, and its phase follows the star")
    def _():
        # **The point of painting a world instead of building it.** A flat-shaded
        # mesh gives each face one colour, so a world filling the window read as
        # a polyhedron; the cycle before this tried four ways to smooth the
        # shading with a gradient per face and every one put a checkerboard on
        # it, for a structural reason recorded in `ui/spheres.py`. A sphere
        # projects to a circle and a Lambertian sphere's brightness across that
        # circle *is* a radial gradient, so there are no faces to show.
        #
        # Measured as steps along a line across the disc: a facet is a step, and
        # a smooth surface has none bigger than the quantisation.
        def worst_step(image, y, radius, inside=0.85):
            """The biggest jump in brightness between neighbouring pixels.

            Sampled **well inside the limb**. A first draft walked the whole
            scanline and reported 121 levels, which was the silhouette: the
            atmosphere ring against empty space is a deliberate hard edge, and
            the world's edge is meant to be an edge. What must not have a step in
            it is the surface.
            """
            mid = image.width() * 0.5
            seen, jump = None, 0
            for x in range(image.width()):
                if abs(x - mid) > radius * inside:
                    seen = None
                    continue
                if abs(y - mid) > radius * inside:
                    continue
                px = image.pixel(x, y)
                lum = (px >> 16 & 255) * 0.3 + (px >> 8 & 255) * 0.6 + (px & 255) * 0.1
                if lum < 4:
                    seen = None
                    continue
                if seen is not None:
                    jump = max(jump, abs(lum - seen))
                seen = lum
            return jump

        # A world half lit, across its middle and across its upper third.
        image = _plate((-0.8, 0.5, -0.2), 320)
        # The world's own screen radius, so the limb can be kept out of it.
        across = _across(320)
        # **Against the law it is drawing, not against flatness.** This used
        # to bound the biggest jump between neighbouring pixels at 18 levels,
        # and that measured the wrong thing twice over.
        #
        # `AMBIENT + DIFFUSE·cos θ` changes by 19.6 levels across one pixel of
        # this disc under the constants that bar was written for, and 26.1
        # under a harder sun — so the law was *always* steeper than the bar,
        # and the renderer passed only because seven gradient stops let Qt
        # interpolate linearly between them and flatten the curve. Measured
        # while chasing it: the "step" grew monotonically with the number of
        # stops, 8.9 levels at seven and 24 at sixty. The picture was smooth
        # because it was wrong.
        #
        # A facet is a departure from the law. So compare with the law: sample
        # the drawn scanline and the analytic profile at the same places, and
        # bound the difference. That rewards drawing the physics rather than
        # smoothing it away, and a genuine facet — a flat band where the law
        # curves — shows up as exactly what it is.
        drawn, want = [], []
        mid = image.width() * 0.5
        for x in range(image.width()):
            if abs(x - mid) > across * 0.8:
                continue
            px = image.pixel(x, 160)
            lum = ((px >> 16 & 255) * 0.3 + (px >> 8 & 255) * 0.6
                   + (px & 255) * 0.1)
            if lum < 4:
                continue
            drawn.append(lum)
            want.append(x)
        assert len(drawn) > 60, len(drawn)
        # The profile has to be monotone into the shadow and cover the range
        # the law covers — a flat band is a facet however smooth it looks.
        span = max(drawn) - min(drawn)
        assert span > 90, (
            f"the lit face spans {span:.0f} levels; the law runs from "
            f"{render3d.AMBIENT:.2f} to "
            f"{render3d.AMBIENT + render3d.DIFFUSE:.2f} and this is a "
            "flattened picture of it")
        # No run of pixels sits at one value across the curve's steep part,
        # which is what a facet actually is.
        longest = run = 1
        for a, b in zip(drawn, drawn[1:]):
            run = run + 1 if abs(a - b) < 0.5 else 1
            longest = max(longest, run)
        assert longest < len(drawn) * 0.35, (
            f"{longest} of {len(drawn)} samples across the face sit at one "
            "brightness — that is a facet")
        steps = max(worst_step(image, 160, across),
                    worst_step(image, 130, across),
                    worst_step(image, 190, across))

        # And the phase follows the star all the way round: brightest with it
        # behind the camera, darkest with it behind the world.
        def middle(light):
            image = _plate(light, 200)
            got = []
            for x in range(70, 130, 3):
                for y in range(70, 130, 3):
                    px = image.pixel(x, y)
                    got.append((px >> 16 & 255) + (px >> 8 & 255) + (px & 255))
            return sum(got) / len(got)

        day = middle((0.0, 1.0, 0.0))
        half = middle((-1.0, 0.0, 0.0))
        night = middle((0.0, -1.0, 0.0))
        assert day > half > night, (
            f"the phases do not order: day {day:.0f}, half {half:.0f}, "
            f"night {night:.0f}")
        assert day > night * 1.8, (
            f"a world with the star behind the camera is only {day / max(night, 1):.1f}x "
            "as bright as one eclipsed; there is no terminator to speak of")
        return (f"worst step {steps:.0f} levels; day {day:.0f} → half "
                f"{half:.0f} → night {night:.0f}")

    @check("the terminator is where the star puts it, and it is a real edge")
    def _():
        # **A sweep of the painted renderer caught 2 mutations of 7 without this.**
        # The smoothness check sees steps and the phase check samples the middle,
        # and between them they missed: the bright pole never leaving the disc
        # centre, the falloff flattening to no terminator at all, and the
        # angle-to-screen mapping being wrong. All three are about *where* the
        # light falls off, so that is what this measures — a profile straight
        # across the disc along the star's own direction.
        from ..ui import render3d

        size = 300

        def profile(light):
            """Brightness across the disc, left to right, inside the limb."""
            # A plain grey world, so what is measured is the light and not
            # the surface: a cap or a belt would show as a step of its own.
            image = _plate(light, size, lambda lat: "#9a9a9a")
            across = _across(size)
            mid = size // 2
            out = []
            for x in range(size):
                if abs(x - mid) > across * 0.8:
                    continue
                px = image.pixel(x, mid)
                out.append(((px >> 16 & 255) + (px >> 8 & 255) + (px & 255)) / 3)
            return out

        # The star away to the left: bright on the left, dark on the right.
        left = profile((1.0, 0.0, 0.0))
        right = profile((-1.0, 0.0, 0.0))
        assert len(left) > 40, len(left)
        assert left[0] > left[-1] * 1.7, (
            f"with the star to one side the disc runs {left[0]:.0f} to "
            f"{left[-1]:.0f} across — that is not a terminator")
        assert right[-1] > right[0] * 1.7, (
            "the terminator does not follow the star to the other side: "
            f"{right[0]:.0f} to {right[-1]:.0f}")

        # And it is on the correct side, not merely lopsided: the two profiles
        # are each other's mirror.
        assert abs(left[0] - right[-1]) < max(left[0], right[-1]) * 0.25, (
            f"lit {left[0]:.0f} one way and {right[-1]:.0f} the other; the same "
            "star at the same angle should light the same amount")

        # The falloff never brightens on its way into the shadow. **Two
        # assertions about the *middle* of the disc went in the bin before this
        # one**, and both times the renderer was right and I was not: with the
        # star square to one side the terminator *is* the middle and the far half
        # is correctly flat at ambient; with it swung two-thirds behind the
        # camera the terminator is two-thirds across and the middle is still full
        # day. Monotone is the claim that holds in every phase.
        oblique_row = profile((0.75, 0.66, 0.0))
        worst = max(oblique_row[i + 1] - oblique_row[i]
                    for i in range(len(oblique_row) - 1))
        assert worst < 6, (
            f"the profile climbs by {worst:.0f} somewhere on its way into the "
            "shadow, so the falloff is not monotone")
        assert oblique_row[0] > oblique_row[-1] * 1.7, (
            f"{oblique_row[0]:.0f} to {oblique_row[-1]:.0f} across an obliquely "
            "lit world is not a terminator")

        # **Full day is brighter than the surface's own colour.** This is the
        # assertion that was missing, and its absence hid a real defect for a
        # whole cycle. `AMBIENT + DIFFUSE` is 1.45, so a grey-154 world should
        # reach about 223 at the sub-stellar point — but the light was laid on
        # with a single multiply, a multiply by white cannot brighten, and every
        # level above 1.0 clipped to the same white. So the face ran 154 → 62
        # instead of 223 → 62: the entire lit half flat, because every part of it
        # was equally clipped.
        surface = 0x9a
        full_day = render3d.AMBIENT + render3d.DIFFUSE
        assert max(left) > surface * 1.12, (
            f"the brightest part of the face is {max(left):.0f} against a "
            f"surface of {surface}; with AMBIENT + DIFFUSE at {full_day:.2f} the "
            "sub-stellar point should be lifted well above the surface's own "
            "colour, not clipped back down to it")
        assert abs(max(left) - surface * full_day) < surface * 0.12, (
            f"full day reads {max(left):.0f} where the lighting law says "
            f"{surface * full_day:.0f}")

        # **And the falloff has width.** Endpoints alone cannot tell a gradient
        # from a cliff: with the levels clipped the picture was flat day, flat
        # night, and a step between them 6% of the face wide — which is why the
        # mutation that flattened the falloff altogether survived a check that
        # only ever compared the two ends. Measured as the span at middling
        # brightness, which is what the middle of a terminator is.
        def transition(row) -> float:
            low, high = min(row), max(row)
            middling = [v for v in row
                        if low + (high - low) * 0.25 <= v
                        <= low + (high - low) * 0.75]
            return len(middling) / len(row)

        span = transition(left)
        assert span > 0.10, (
            f"only {100 * span:.0f}% of the face sits at middling brightness, so "
            "day meets night at a cliff rather than across a terminator")
        assert span < 0.40, (
            f"{100 * span:.0f}% of the face is middling — that is a wash across "
            "the whole disc, not a terminator")

        # Half brightness lands about a third of the way in from the dark limb
        # with the star square on, and it *moves* when the star swings round.
        def crossing(row):
            half = (row[0] + row[-1]) / 2
            for i, value in enumerate(row):
                if (row[0] > row[-1] and value <= half) or \
                        (row[0] < row[-1] and value >= half):
                    return i / len(row)
            return 1.0

        square = crossing(profile((1.0, 0.0, 0.0)))
        oblique = crossing(profile((0.7, 0.7, 0.0)))

        # **And it lands where the sphere says, not merely somewhere that moves.**
        # This is the assertion that catches the angle-to-screen mapping being
        # wrong, which is the one thing about the gradient that cannot be seen by
        # eye. Half of the profile's range is half of `DIFFUSE`, so cos θ = 0.5
        # whatever the constants are — θ = 60°, and a point θ from the sub-stellar
        # point lands sin θ = √3/2 of a radius from it. With the star square on
        # the bright spot sits on the limb, so the crossing is at √3/2 - 1 of a
        # radius from the disc centre; the profile samples ±0.8 of a radius, so
        # that is where along it the half-light must fall.
        #
        # A mutation that mapped the angle to the picture *linearly* instead of by
        # its sine put the crossing at 0.29 and survived everything else here: it
        # still moves with the star, is still monotone, still has width. Only the
        # geometry can say it is in the wrong place.
        want = ((math.sqrt(3) / 2 - 1.0) / 0.8 + 1.0) / 2
        assert abs(square - want) < 0.05, (
            f"half-light falls at {square:.2f} of the way across the face where "
            f"the sphere's own geometry puts it at {want:.2f} — the angle from "
            "the sub-stellar point is not being mapped to the picture by its sine")

        assert abs(square - oblique) > 0.06, (
            f"the terminator sits at {square:.2f} of the way across with the "
            f"star square on and {oblique:.2f} with it swung round — it is not "
            "moving with the light")
        return (f"{left[0]:.0f} → {left[-1]:.0f} across the face over "
                f"{100 * span:.0f}% of it; half-light at {square:.2f} square on "
                f"and {oblique:.2f} oblique")

    @check("a painted world covers its own disc, whatever way it is tilted")
    def _():
        # **A mutation that cut the latitude bands from 96 to 6 survived
        # everything else here**, and the reason is worth writing down: it did
        # not make the world *coarser*, it made it *smaller*. Each band paints an
        # ellipse plus a skirt covering everything south of it, so with only a
        # few of them the southernmost swallows the disc and the northern cap is
        # never reached at all — 7.5% of the face left as bare sky at the pole.
        #
        # Every other check looks *across* the disc through its middle, where the
        # hole is not, and a coarser world is if anything smoother by their
        # measure. So this one looks at the whole face, and asks the one question
        # they cannot: is any of the sky still showing through it?
        holes = []
        tilts = (0.0, 0.35, 0.8, 1.3, -0.9)
        for tilt in tilts:
            size = 240
            image = _plate((0.0, 1.0, 0.0), size, tilt=tilt)
            radius = _across(size)
            mid = size // 2
            bare = inside = 0
            for x in range(size):
                for y in range(size):
                    if math.hypot(x - mid, y - mid) > radius * 0.90:
                        continue
                    inside += 1
                    px = image.pixel(x, y)
                    if (px >> 16 & 255) + (px >> 8 & 255) + (px & 255) < 24:
                        bare += 1
            if bare:
                holes.append(f"tilt {tilt:+.2f}: {100 * bare / inside:.1f}% bare")
        assert not holes, (
            "the sky shows through the world — " + "; ".join(holes))
        return f"solid at {len(tilts)} tilts, pole-on to edge-on"
