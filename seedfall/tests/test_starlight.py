"""Nine star classes, and whether the sky can tell them apart.

`data/starclasses.py` has carried a `core` colour per class since it was
written. `ui/viewport._star` worked that colour out into a local called `tint`
and then drew:

    p.setBrush(QColor(255, 253, 244))
    p.drawEllipse(point, radius, radius)

The same off-white, nine times. The catalogue held an M dwarf's salmon, a
G-type's cream, an A-type's blue-white and a black hole's violet, and the
window put one white dot in the sky for all of them — so **the black hole,
whose own entry says there is nothing to see and that the accretion disc is the
only reason you know where it is, was drawn as the brightest object in the
picture.**

There is a comment two lines above that fill congratulating an earlier cycle for
noticing the *corona* colour was unused. It fixed the halo and left the core.

The claims:

- **A class is drawn in its own colour**, and changing that colour changes the
  picture — which is the property the dropped local failed.
- **The nine are nine**, measured as rendered pictures.
- **A black hole is an absence**, darker than every star in the sector.
- **The corona follows luminosity**, over a range of 0.0002 to 22, and stays
  bounded at both ends.
- **A star still reads at any range**, down to the point where it is one pixel.
"""

from __future__ import annotations

import math

from ..data.starclasses import STAR_CLASSES
from ..sim.sky import Sight
from .harness import Suite

SIZE = 120


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _sight(key: str, distance_km: float | None = None, want_px: float = 22.0):
    """One star, placed so its disc comes out about `want_px` across."""
    from ..ui import render3d
    star = STAR_CLASSES[key]
    _app()
    camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                             width=SIZE, height=SIZE,
                             half_fov=math.radians(30))
    if distance_km is None:
        distance_km = star.radius_km / math.tan(math.atan(want_px / camera.focal))
    seen = Sight(name=star.name, kind="star", at=(0.0, 0.0, distance_km),
                 radius_km=star.radius_km, tint=star.core, look=key,
                 halo=star.halo)
    return camera, seen


def _paint(key: str, distance_km: float | None = None, core: str | None = None,
           want_px: float = 22.0):
    """Render one class and hand back the image and its screen radius."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import stars3d

    camera, seen = _sight(key, distance_km, want_px)
    if core is not None:
        # `Sight` is frozen, so a recolour is a new one — which is also the
        # honest test: the renderer must read the colour off the sight it is
        # given rather than off the class it looks up.
        from dataclasses import replace
        seen = replace(seen, tint=core)
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    image.fill(QColor("#000000"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    radius = stars3d.draw(painter, camera, seen)
    painter.end()
    return image, radius


def _at(image, dx: float, dy: float = 0.0) -> tuple:
    """The colour a fraction of the way out from the middle of the frame."""
    x = int(SIZE / 2 + dx * SIZE / 2)
    y = int(SIZE / 2 + dy * SIZE / 2)
    rgb = image.pixel(max(0, min(SIZE - 1, x)), max(0, min(SIZE - 1, y)))
    return (rgb >> 16 & 0xFF, rgb >> 8 & 0xFF, rgb & 0xFF)


def _apart(a: tuple, b: tuple) -> int:
    return sum(abs(one - two) for one, two in zip(a, b))


def run(suite: Suite) -> None:
    check = suite.check

    @check("a class is drawn in its own colour, and the colour is consumed")
    def _():
        # The defect exactly: the class's colour was worked out and dropped, so
        # changing it changed nothing. Rendering the same class twice with
        # different cores has to give two different pictures.
        image, radius = _paint("M")
        assert radius > 6, radius
        # Sampled off-centre, where the disc's own colour rules: the middle is
        # pushed toward white by luminosity on purpose.
        own = _at(image, 0.0)
        warm = _at(image, radius / SIZE * 1.2)
        recoloured, _r = _paint("M", core="#66ff88")
        moved = _apart(warm, _at(recoloured, radius / SIZE * 1.2))
        assert moved > 60, (
            f"changing an M dwarf's core colour moved the picture by {moved} — "
            "the colour is being computed and dropped")
        # And a warm class is warm: more red than blue on the face of it.
        assert warm[0] > warm[2] + 20, (
            f"an M-type red dwarf renders {warm}, which is not a red dwarf")
        # And at the size a star is usually seen. Most of them are a few
        # pixels across from anywhere in a system, where the *centre* is the
        # whole of the picture — so a check that only samples off-centre lets
        # a fixed white middle through, which the mutation sweep proved by
        # walking straight past it.
        small = {}
        for key in ("M", "K", "A", "N"):
            image, radius = _paint(key, want_px=3.0)
            assert radius <= 4.0, (key, radius)
            small[key] = _at(image, 0.0)
        assert _apart(small["M"], small["A"]) > 40, (
            f"at three pixels an M dwarf renders {small['M']} and an A-type "
            f"{small['A']} — the size most stars are seen at is the size they "
            "all look alike")
        # And the middle of a warm star is warm. Measured: an M dwarf's centre
        # renders (255, 189, 157) — 98 points of red over blue. Pushing the
        # innermost stop to a fixed white leaves it (255, 228, 209), which is
        # 46, and still passes a bare `red > blue`; it also still reads as
        # different from an A-type, which is how that mutation walked past the
        # first two versions of this check. The bar is between the two.
        warmth = small["M"][0] - small["M"][2]
        assert warmth > 70, (
            f"an M dwarf's centre renders {small['M']}, only {warmth} points "
            "of red over blue — the class's colour is not reaching the middle "
            "of its own disc")
        assert small["A"][2] >= small["A"][0] - 8, small["A"]
        return (f"M dwarf renders {warm} off-centre against {own} in the "
                f"middle; recolouring it moves the picture by {moved}; at "
                f"three pixels M is {small['M']} and A {small['A']}")

    @check("the nine are nine, as pictures")
    def _():
        shots = {key: _paint(key)[0] for key in STAR_CLASSES}
        tones = {}
        for key, image in shots.items():
            radius = _paint(key)[1]
            tones[key] = _at(image, radius / SIZE * 1.1)
        worst, pair = 10_000, None
        keys = list(tones)
        for i, one in enumerate(keys):
            for other in keys[i + 1:]:
                gap = _apart(tones[one], tones[other])
                if gap < worst:
                    worst, pair = gap, (one, other)
        # Before this cycle every one of these was (255, 253, 244) and every
        # pair scored 0.
        assert worst > 8, (
            f"{pair[0]} and {pair[1]} render within {worst} of each other on "
            "the face of the disc — that is one star with nine names")
        return (f"{len(tones)} classes, the closest pair ({pair[0]}/{pair[1]}) "
                f"{worst} apart in colour")

    @check("a black hole is an absence, not the brightest thing in the sky")
    def _():
        dark, radius = _paint("X")
        middle = _at(dark, 0.0)
        assert sum(middle) < 40, (
            f"the horizon renders {middle} — a black hole is drawn as a light")
        # Darker than every star there is, at the same place on the frame.
        for key in STAR_CLASSES:
            if key == "X":
                continue
            other, _r = _paint(key)
            assert sum(_at(other, 0.0)) > sum(middle) + 120, (
                f"{key} is no brighter in the middle than a black hole")
        # And the ring is there: something bright just outside the horizon.
        ring = _at(dark, radius / SIZE * 2.3)
        assert sum(ring) > sum(middle) + 30, (
            f"nothing outside the horizon: middle {middle}, ring {ring} — the "
            "accretion disc is the only reason you know where it is")
        return (f"horizon {middle}, ring {ring}: an absence with something "
                "burning round it")

    @check("the corona follows how bright the star actually is")
    def _():
        from ..ui import stars3d
        reach = {key: stars3d.corona_reach(star)
                 for key, star in STAR_CLASSES.items()}
        assert reach["A"] > reach["G"] > reach["M"], reach
        assert reach["A"] > reach["N"], reach
        # Bounded at both ends: the range of luminosity is 0.0002 to 22, and a
        # linear law would give eight of the nine classes no corona at all.
        assert min(reach.values()) >= stars3d.CORONA_MIN - 1e-9
        assert max(reach.values()) <= stars3d.CORONA_MAX + 1e-9
        assert max(reach.values()) < min(reach.values()) * 6, (
            "the spread of coronae is wider than the picture can hold")
        # And the picture agrees. Measured as how far the glow reaches out
        # along a row, not as lit area — a bright class saturates a small frame
        # and the first version of this line read A and G as identical at 3,600
        # pixels each, which is the frame's size and not the star's.
        def spread(key: str) -> int:
            image, _r = _paint(key, want_px=8.0)
            middle = SIZE // 2
            far = 0
            for x in range(middle, SIZE):
                rgb = image.pixel(x, middle)
                if (rgb >> 16 & 0xFF) + (rgb >> 8 & 0xFF) + (rgb & 0xFF) > 20:
                    far = x - middle
            return far

        lit = {key: spread(key) for key in ("A", "G", "M")}
        assert lit["A"] > lit["G"] > lit["M"], lit
        return (f"reach A {reach['A']:.1f} · G {reach['G']:.1f} · "
                f"M {reach['M']:.1f} disc radii; glow reaches {lit} px")

    @check("a star still reads when it is a pixel across")
    def _():
        # Most stars in the game are seen from across a system. The floor is
        # what keeps one from rounding away to nothing.
        from ..ui import stars3d
        AU = 149_597_870.7
        for key in ("A", "M", "N"):
            image, radius = _paint(key, distance_km=4.0 * AU)
            assert radius >= 2.4 - 1e-9, (key, radius)
            assert sum(_at(image, 0.0)) > 60, (
                f"{key} at four AU is invisible: {_at(image, 0.0)}")
        # A black hole at that range is still not a light.
        far, _r = _paint("X", distance_km=4.0 * AU)
        assert sum(_at(far, 0.0)) < 120, _at(far, 0.0)
        return "A, M and N all visible at four AU; X still dark"
