"""The astronomical catalogue: stars that differ, and worlds you can tell apart.

The sector has had eight spectral classes since it was written — an M dwarf, a
K, a G, an F, an A, a binary pair, a white dwarf and a neutron star, each with
its own name and tint on the chart. Every one was drawn as the same
seven-hundred-thousand-kilometre ball, because the sky held one number for a
star's size and never asked which star. They are not the same size: a white
dwarf is about as big as a rocky world and a neutron star is twelve kilometres
across. That is a range of **fifty-eight thousand to one**, and it was free —
the data already said which was which.

The bodies were the same story. A 12 km comet, a 7,000 km ocean and a 71,000
km gas giant all came out as one ball with a different tint. The cheapest
thing that fixes it is **latitude**: colour a sphere's bands by how far up
them you are and polar caps come for nothing, vary the bands and you have a
gas giant, and a flat annulus round it is a ring system.

The claims:

- **No two kinds of world look the same.** The general one, measured in
  pixels rather than asserted from the table that made them.
- **A star's size is its class's**, and the classes really do differ.
- **Rings are concentric, only on giants, and always the same worlds.**
- **The catalogue is complete**: every body kind the galaxy makes has a mesh.
"""

from __future__ import annotations

import math

from ..data import worlds3d
from ..world.planets import BODY_KINDS
from .harness import Suite


def _render(look: str, ringed: bool = False, size: int = 220):
    """One world, alone, at a fixed distance and light. Returns the image."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtGui import QColor, QPainter
    from PyQt6.QtWidgets import QApplication, QWidget

    from ..ui import render3d, spheres

    app = QApplication.instance() or QApplication([])
    assert app is not None

    class Plate(QWidget):
        def paintEvent(self, _event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.fillRect(self.rect(), QColor("#04080b"))
            r = 1000.0
            light = render3d.unit((-0.8, -0.5, -0.35))
            camera = render3d.Camera(at=(0.0, -r * 6.0, r * 1.8),
                                     forward=(0.0, 1.0, -0.30),
                                     up=(0.0, 0.0, 1.0),
                                     width=self.width(), height=self.height(),
                                     half_fov=math.radians(24))
            # **Through the renderer the game actually uses.** This drew from
            # `mesh_for` until worlds became painted discs, at which point every
            # check in this file was testing a path nothing in the game took: a
            # sweep of the painted renderer caught 1 mutation of 7, because the
            # catalogue checks were all looking the other way.
            if ringed:
                render3d.draw(painter, camera, worlds3d.RINGS_MESH,
                              (0, 0, 0), r, light, tilt=0.42)
            spheres.draw(painter, camera, worlds3d.paint_for(look),
                         (0, 0, 0), r, light, tilt=0.42)
            if ringed:
                render3d.draw(painter, camera, worlds3d.RINGS_FRONT,
                              (0, 0, 0), r, light, tilt=0.42)
            painter.end()

    plate = Plate()
    plate.resize(size, size)
    return plate.grab().toImage()


def _fingerprint(image) -> tuple:
    """A signature of what a world looks like: colour, size and structure.

    Over the **lit** pixels only. A first draft averaged a grid of cells
    across the whole plate, three quarters of which is identical black sky,
    and duly reported that seventeen pairs of world looked alike — it was
    measuring the background. And a bare mean cannot see *banding*, which is
    the whole of what makes a gas giant a gas giant, so the vertical profile
    goes in as well: eight stripes down the picture, each averaged.
    """
    lit = []
    stripes = [[0, 0, 0, 0] for _ in range(8)]
    r = g = b = n = 0
    height = image.height()
    for x in range(0, image.width(), 2):
        for y in range(0, height, 2):
            px = image.pixelColor(x, y)
            if px.red() + px.green() + px.blue() <= 90:
                continue
            r += px.red()
            g += px.green()
            b += px.blue()
            n += 1
            row = stripes[min(7, y * 8 // height)]
            row[0] += px.red()
            row[1] += px.green()
            row[2] += px.blue()
            row[3] += 1
    if not n:
        return ((0, 0, 0), 0, tuple((0, 0, 0) for _ in range(8)))
    lit = (r // n, g // n, b // n)
    profile = tuple((s[0] // max(s[3], 1), s[1] // max(s[3], 1),
                     s[2] // max(s[3], 1)) for s in stripes)
    return (lit, n, profile)


def _distance(a: tuple, b: tuple) -> float:
    """How unlike two worlds are: colour, then area, then structure."""
    colour = sum(abs(x - y) for x, y in zip(a[0], b[0]))
    area = abs(a[1] - b[1]) / 40.0
    banding = sum(abs(x - y) for pa, pb in zip(a[2], b[2])
                  for x, y in zip(pa, pb)) / 8.0
    return colour + area + banding


def run(suite: Suite) -> None:
    check = suite.check

    @check("no two kinds of world look the same")
    def _():
        # The general one, and measured in pixels: a check that compared the
        # colour table against itself would pass however identically the
        # things actually drew.
        kinds = [k for k in BODY_KINDS if k != "star"]
        shots = {kind: _fingerprint(_render(kind)) for kind in kinds}
        shots["gas+rings"] = _fingerprint(_render("gas", ringed=True))

        same = []
        names = list(shots)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                gap = _distance(shots[a], shots[b])
                if gap < 25:
                    same.append(f"{a} and {b} differ by only {gap:,.0f}")
        assert not same, (
            f"{len(same)} pair(s) of world that render alike: {same[:4]}")

        closest = min(
            ((_distance(shots[a], shots[b]), a, b)
             for i, a in enumerate(names) for b in names[i + 1:]),
            key=lambda row: row[0])
        return (f"{len(names)} kinds, all distinct; the nearest pair is "
                f"{closest[1]}/{closest[2]} at {closest[0]:,.0f}")

    @check("a solid body draws solid, with no seams between its faces")
    def _():
        # Every sphere in the game wore a faint wireframe, and it took a
        # contact sheet to see it. Two adjacent antialiased polygons each
        # cover about half the pixel on the edge they share and each blends
        # its half with the background, so a solid hull came out ruled with
        # hairlines of empty space.
        #
        # Measured as one-pixel-wide dark lines *inside* the silhouette,
        # which is exactly what the artifact is: a pixel darker than both of
        # its neighbours on either side. 1,194 of them before the fix.
        image = _render("gas", size=260)

        def bright(x: int, y: int) -> int:
            px = image.pixelColor(x, y)
            return px.red() + px.green() + px.blue()

        seams = 0
        for y in range(1, 259):
            for x in range(1, 259):
                here = bright(x, y)
                if here <= 90:
                    continue                      # background, not the world
                if (bright(x - 1, y) > here + 24
                        and bright(x + 1, y) > here + 24):
                    seams += 1
                if (bright(x, y - 1) > here + 24
                        and bright(x, y + 1) > here + 24):
                    seams += 1
        assert seams < 200, (
            f"{seams} pixels inside the world are darker than both their "
            "neighbours — the faces are not meeting, and the body is drawn "
            "with a wireframe over it")
        return f"{seams} seam pixels across a 260px world, against 1,194 before"

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
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtGui import QColor, QImage, QPainter
        from PyQt6.QtWidgets import QApplication

        from ..ui import render3d, spheres

        app = QApplication.instance() or QApplication([])
        assert app is not None

        def plate(light, size=320, kind="rocky"):
            image = QImage(size, size, QImage.Format.Format_RGB32)
            image.fill(QColor("#000000"))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            camera = render3d.Camera(at=(0.0, -26000.0, 0.0),
                                     forward=(0.0, 1.0, 0.0), up=(0.0, 0.0, 1.0),
                                     width=size, height=size,
                                     half_fov=math.radians(26))
            spheres.draw(painter, camera, worlds3d.paint_for(kind),
                         (0.0, 0.0, 0.0), 6000.0, light, tilt=0.35)
            painter.end()
            return image

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
        image = plate((-0.8, 0.5, -0.2), 320)
        # The world's own screen radius, so the limb can be kept out of it.
        camera = render3d.Camera(at=(0.0, -26000.0, 0.0), forward=(0.0, 1.0, 0.0),
                                 up=(0.0, 0.0, 1.0), width=320, height=320,
                                 half_fov=math.radians(26))
        across = render3d.screen_radius(camera, 26000.0, 6000.0)
        steps = max(worst_step(image, 160, across),
                    worst_step(image, 130, across),
                    worst_step(image, 190, across))
        assert steps < 18, (
            f"the brightest step across the disc is {steps:.0f} levels — that is "
            "a facet, and a painted sphere should not have one")

        # And the phase follows the star all the way round: brightest with it
        # behind the camera, darkest with it behind the world.
        def middle(light):
            image = plate(light, 200)
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
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtGui import QColor, QImage, QPainter
        from PyQt6.QtWidgets import QApplication

        from ..ui import render3d, spheres

        app = QApplication.instance() or QApplication([])
        assert app is not None
        size = 300

        def profile(light):
            """Brightness across the disc, left to right, inside the limb."""
            image = QImage(size, size, QImage.Format.Format_RGB32)
            image.fill(QColor("#000000"))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            camera = render3d.Camera(at=(0.0, -26000.0, 0.0),
                                     forward=(0.0, 1.0, 0.0), up=(0.0, 0.0, 1.0),
                                     width=size, height=size,
                                     half_fov=math.radians(26))
            # A plain grey world, so what is measured is the light and not the
            # surface: a cap or a belt would show up as a step of its own.
            spheres.draw(painter, camera, lambda lat: "#9a9a9a",
                         (0.0, 0.0, 0.0), 6000.0, light, tilt=0.35)
            painter.end()
            across = render3d.screen_radius(camera, 26000.0, 6000.0)
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
        assert abs(square - oblique) > 0.06, (
            f"the terminator sits at {square:.2f} of the way across with the "
            f"star square on and {oblique:.2f} with it swung round — it is not "
            "moving with the light")
        return (f"{left[0]:.0f} → {left[-1]:.0f} across the face; half-light at "
                f"{square:.2f} square on and {oblique:.2f} oblique")

    @check("a gas giant is banded, and nothing else in the sky is")
    def _():
        # Banding is the *whole* of what makes a giant read as a giant, and
        # nothing asserted it: a mutation that flattened the belts into one
        # smooth gradient sailed through every other check here, because a
        # gradient is still many colours and still unlike a rocky world.
        #
        # Measured as direction reversals down the world's latitude profile,
        # which is what a belt is: light, dark, light again. A capped world
        # goes one way — ground out to a pole — and turns at most a couple of
        # times on the way.
        def reversals(mesh) -> int:
            verts, faces = mesh
            rows = []
            for idx, colour in faces:
                z = sum(verts[i][2] for i in idx) / len(idx)
                lum = sum(int(colour[1 + 2 * k:3 + 2 * k], 16)
                          for k in range(3)) / 3
                rows.append((z, lum))
            rows.sort()
            bands, run, last = [], [], None
            for z, lum in rows:
                if last is not None and abs(z - last) > 1e-6:
                    bands.append(sum(run) / len(run))
                    run = []
                run.append(lum)
                last = z
            if run:
                bands.append(sum(run) / len(run))
            steps = [1 if b > a + 0.5 else -1 if b < a - 0.5 else 0
                     for a, b in zip(bands, bands[1:])]
            steps = [s for s in steps if s]
            return sum(1 for a, b in zip(steps, steps[1:]) if a != b)

        turns = {kind: reversals(mesh)
                 for kind, mesh in worlds3d.WORLD_MESHES.items()}
        others = {k: v for k, v in turns.items() if k != "gas"}
        assert turns["gas"] >= 8, (
            f"a gas giant's colour turns {turns['gas']} time(s) from pole to "
            "pole — that is a gradient, not a belted world")
        assert turns["gas"] > max(others.values()) + 2, (
            f"the giant turns {turns['gas']} times and "
            f"{max(others, key=others.get)} turns "
            f"{max(others.values())} — the banding is not distinctive")
        return (f"the giant's colour turns {turns['gas']} times pole to pole; "
                f"the rest turn " +
                "-".join(str(v) for v in sorted(set(others.values()))))

