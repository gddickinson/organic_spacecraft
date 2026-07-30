"""Stars, rings, and the catalogue: the sky's furniture beyond the worlds.

`test_worlds.py` next door holds the worlds themselves — that they look distinct,
that they draw solid, and that one close enough to show its facets is cut finely
enough to hide them. This holds what surrounds them.

Split out when the two together went past five hundred lines.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import worlds3d
from ..data.starclasses import STAR_CLASSES, of as star_class
from ..sim import sky as sky_sim
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

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
