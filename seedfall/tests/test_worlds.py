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

from ..core.state import new_game
from ..data import worlds3d
from ..data.starclasses import STAR_CLASSES, of as star_class
from ..sim import sky as sky_sim
from ..world.planets import BODY_KINDS
from .harness import Suite


def _render(look: str, ringed: bool = False, size: int = 220):
    """One world, alone, at a fixed distance and light. Returns the image."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtGui import QColor, QPainter
    from PyQt6.QtWidgets import QApplication, QWidget

    from ..ui import render3d

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
            if ringed:
                render3d.draw(painter, camera, worlds3d.RINGS_MESH,
                              (0, 0, 0), r, light, tilt=0.42)
            render3d.draw(painter, camera, worlds3d.mesh_for(look),
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

    @check("a star's size is its class's, and the classes differ")
    def _():
        # Absolute claims, not "the table says what the table says": a white
        # dwarf is about the size of a rocky world and a neutron star is a
        # city, and both used to be drawn as the Sun.
        sizes = {cid: spec.radius_km for cid, spec in STAR_CLASSES.items()}
        assert len(sizes) >= 8, sizes
        assert sizes["N"] < 100, f"a neutron star is {sizes['N']:,.0f} km"
        assert 1_000 < sizes["D"] < 40_000, (
            f"a white dwarf is {sizes['D']:,.0f} km — it should be about the "
            "size of a rocky world")
        assert sizes["A"] > sizes["M"] * 4, (
            f"an A-type is {sizes['A']:,.0f} km against an M dwarf's "
            f"{sizes['M']:,.0f} — barely a difference")
        assert max(sizes.values()) / min(sizes.values()) > 10_000, (
            "the whole catalogue of stars spans less than four orders of "
            "magnitude, which is not what stars do")
        for cid, spec in STAR_CLASSES.items():
            assert spec.core.startswith("#") and spec.halo.startswith("#"), cid
            assert spec.luminosity > 0, cid

        # And the sky uses them: it is the class that decides, not one number.
        seen = {}
        for seed in range(14):
            game = new_game(f"class-{seed}")
            spec = star_class(game.system)
            found = next(s for s in sky_sim.build(game, None)
                         if s.kind == "star")
            assert abs(found.radius_km - spec.radius_km) < 1.0, (
                f"{game.system.name} is a {spec.name} and its sky says "
                f"{found.radius_km:,.0f} km")
            seen[spec.id] = spec.name
        assert len(seen) >= 3, (
            f"fourteen sectors and only {len(seen)} class(es) of star: {seen}")
        return (f"{len(sizes)} classes spanning "
                f"{max(sizes.values()) / min(sizes.values()):,.0f} to one; "
                f"{len(seen)} of them seen in fourteen sectors")

    @check("rings are concentric, on giants only, and always the same worlds")
    def _():
        # The first draft alternated colour *per segment* and drew a
        # cartwheel of spokes, and keyed the "which worlds" decision on a
        # body id that is "1", "2" or "3" in every system — 1% ringed
        # against a target of 45%.
        bands = worlds3d.RING_BANDS
        assert len(bands) >= 4, bands
        for inner, outer, colour in bands:
            assert 1.0 < inner < outer < 4.0, (inner, outer)
            assert colour.startswith("#")
        for (a_in, a_out, _a), (b_in, _b_out, _b) in zip(bands, bands[1:]):
            assert b_in >= a_out - 1e-9, (
                f"ring bands overlap: {a_in}-{a_out} then {b_in}")

        # And concentric in the *mesh*, not merely in the table above. The
        # bug this replaced alternated colour per segment and drew a
        # cartwheel of spokes — the table it read was already concentric, so
        # inspecting the table could never have caught it. Every face at a
        # given radius must be the same colour; that is what "concentric"
        # means once it has been built.
        verts, faces = worlds3d.RINGS_MESH
        at_radius: dict = {}
        for idx, colour in faces:
            rad = sum(math.dist(verts[i][:2], (0.0, 0.0)) for i in idx)
            at_radius.setdefault(round(rad / len(idx), 4), set()).add(colour)
        spokes = [r for r, colours in at_radius.items() if len(colours) > 1]
        assert not spokes, (
            f"{len(spokes)} radius/radii carry more than one colour — the "
            "rings are drawn as spokes, not as bands")
        assert len(at_radius) >= len(bands), at_radius

        ringed = plain = 0
        by_kind: dict = {}
        by_id: dict = {}
        for seed in range(10):
            game = new_game(f"rings-{seed}")
            for system in game.galaxy.systems:
                for body in system.bodies:
                    has = sky_sim.has_rings(body)
                    if has:
                        by_kind[body.kind] = by_kind.get(body.kind, 0) + 1
                    if body.kind == "gas":
                        ringed += has
                        plain += not has
                        by_id.setdefault(body.id, []).append(bool(has))
        assert set(by_kind) <= {"gas"}, (
            f"something that is not a gas giant has rings: {by_kind}")
        share = ringed / max(1, ringed + plain)
        assert 0.25 < share < 0.65, (
            f"{share:.0%} of gas giants are ringed against a target of "
            f"{worlds3d.RINGED_SHARE:.0%}")

        # A ring system belongs to the *world*, not to its number in the
        # system. Keying the decision on `body.id` — which this once did —
        # cannot be caught by the share above: there are only seven distinct
        # ids across a hundred and ninety giants, so the share is seven coin
        # flips and lands near the target by luck. It shows up here instead,
        # as every third giant in the sector agreeing with every other third
        # giant.
        #
        # Only groups of eight or more count: the outermost slot holds a
        # single giant in the whole sector, and one body agreeing with itself
        # is not evidence of anything. At eight, unanimity by chance is under
        # one per cent.
        assert len(by_id) < ringed + plain, by_id
        crowded = {k: v for k, v in by_id.items() if len(v) >= 8}
        assert len(crowded) >= 3, (
            f"too few crowded orbits to tell: {[len(v) for v in by_id.values()]}")
        lockstep = sorted(k for k, outcomes in crowded.items()
                          if len(set(outcomes)) == 1)
        assert not lockstep, (
            f"all {[len(crowded[k]) for k in lockstep]} giant(s) numbered "
            f"{lockstep} in the sector agree about rings — the decision is "
            "keyed on the body's number, not the body")

        # And the same worlds every time, in a fresh process.
        import subprocess
        import sys
        code = ("from seedfall.core.state import new_game;"
                "from seedfall.sim import sky;"
                "g=new_game('rings-0');"
                "print([sky.has_rings(b) for s in g.galaxy.systems "
                "for b in s.bodies if b.kind=='gas'][:12])")
        done = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True, timeout=180)
        assert done.returncode == 0, done.stderr[-300:]
        game = new_game("rings-0")
        mine = [sky_sim.has_rings(b) for s in game.galaxy.systems
                for b in s.bodies if b.kind == "gas"][:12]
        assert str(mine) == done.stdout.strip(), (
            "which worlds carry rings changes between processes")
        return (f"{ringed} of {ringed + plain} giants ringed ({share:.0%}), "
                f"{len(bands)} concentric bands, identical in a fresh process")

    @check("a ringed world keeps its rings when you fly at it")
    def _():
        # Found by playing: the *sky* drew rings on a ringed giant from the
        # moment giants had them, and the thing being approached did not — so
        # a giant's rings vanished at exactly the point you got close enough
        # for them to be worth looking at. Two doors into the same question,
        # disagreeing, which is this project's most reliable bug shape.
        import dataclasses

        from ..sim import conn as conn_sim
        from ..sim import targets, track as track_sim

        # The doors agree, for every giant in the sector and not just one.
        # The seed is searched for rather than named: adding a star class
        # changes what every seed generates, and a check that hard-codes one
        # breaks for a reason that has nothing to do with what it is testing.
        game = None
        for seed in range(30):
            candidate = new_game(f"ringed-{seed}")
            if any(b.kind == "gas" and sky_sim.has_rings(b)
                   for b in candidate.system.bodies):
                game = candidate
                break
        assert game is not None, "thirty seeds and no ringed giant in reach"
        asked = agreed = 0
        for index, body in enumerate(game.system.bodies):
            built = targets.target_from_body(body, index=index)
            asked += 1
            agreed += built.ringed == sky_sim.has_rings(body)
        assert asked == agreed, (
            f"{asked - agreed} of {asked} bodies disagree between the sky and "
            "the thing you approach about whether they have rings")

        ringed = [(i, b) for i, b in enumerate(game.system.bodies)
                  if b.kind == "gas" and sky_sim.has_rings(b)]
        assert ringed, "no ringed giant in this chronicle to fly at"
        index, body = ringed[0]
        contact = next(c for c in track_sim.contacts(game, game.system)
                       if c.body_index == index)

        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.viewport import Viewport
        app = QApplication.instance() or QApplication([])
        assert app is not None

        conn = conn_sim.start(game, contact, range_km=body.radius_km * 5.0)
        assert conn.target.ringed, conn.target

        def lit(view) -> int:
            image = view.grab().toImage()
            return sum(1 for x in range(0, 360, 2) for y in range(0, 360, 2)
                       if sum(image.pixelColor(x, y).getRgb()[:3]) > 150)

        # Differenced against the identical approach with the rings taken
        # off, so what is measured is the rings and not the world.
        view = Viewport(conn, "fore")
        view.resize(360, 360)
        with_rings = lit(view)
        conn.target = dataclasses.replace(conn.target, ringed=False)
        without = lit(view)
        assert with_rings > without + 400, (
            f"a ringed giant lit {with_rings} samples against {without} for "
            "the same approach with the rings removed — the world you are "
            "flying at is not drawing them")
        return (f"{body.name} at {conn.range_km:,.0f} km lights "
                f"{with_rings} samples against {without} unringed; "
                f"{agreed}/{asked} bodies agree with the sky")

    @check("the catalogue covers everything the galaxy makes")
    def _():
        # A body kind with no mesh falls back to a grey ball, which is the
        # state this whole file exists to end. If the generator learns a new
        # kind, this says so rather than quietly drawing porridge.
        made = set()
        for seed in range(6):
            game = new_game(f"kinds-{seed}")
            for system in game.galaxy.systems:
                for body in system.bodies:
                    made.add(body.kind)
        missing = sorted(k for k in made if k not in worlds3d.WORLD_MESHES)
        assert not missing, (
            f"the galaxy makes {missing} and the catalogue has no mesh for "
            "them — they would draw as a plain grey ball")
        for kind in made:
            verts, faces = worlds3d.mesh_for(kind)
            assert len(verts) > 40 and len(faces) > 40, (kind, len(faces))
            assert len({colour for _idx, colour in faces}) > 1, (
                f"{kind} is a single flat colour, which is what a sphere "
                "already was")
        return (f"{len(made)} kinds in play, every one with a mesh of its "
                f"own: {', '.join(sorted(made))}")
