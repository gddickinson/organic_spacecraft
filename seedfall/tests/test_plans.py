"""Ship plans — the model has to be the ship, and the solid has to be solid.

The numbers on the ship screen were all true and none of them were a picture.
You could read that a Polyp Laboratory was fitted and that the ablative layer
was at 41% and still have no idea what you were flying.

These hold the model to being built out of the actual ship, and hold the
renderer to the one thing a software rasteriser gets wrong silently: winding.
A face wound the wrong way is culled when it should be drawn, and the result
is not a crash or a blank screen — it is a ship that renders beautifully as an
x-ray of its own far wall, with the cargo floating in front of the hull. That
shipped in the first draft and looked deliberate.
"""

from __future__ import annotations

import math

from ..core import solid as solid_mod
from ..core.state import new_game
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.hullforms import FORMS, SLOT_SHAPE, form_for
from ..data.part_types import SLOT_ORDER
from ..data.parts import PARTS_BY_ID
from ..sim import plans as plans_sim
from .harness import Suite


def _outward(face, axis=None) -> float:
    """+1 if the face looks away from the solid's own centre, -1 if inward.

    `axis` gives the reference for a torus, whose inner faces point at the
    tube's centreline and are perfectly correct while pointing at the origin.
    Comparing them to the origin is how the first version of this check
    reported forty inside-out faces on a ring that was wound properly.
    """
    centre = solid_mod.centre_of(face.points)
    if axis is not None:
        flat = math.hypot(centre[0], centre[1]) or 1e-9
        centre = solid_mod.sub(centre, (centre[0] / flat * axis,
                                        centre[1] / flat * axis, 0.0))
    if solid_mod.length(centre) < 1e-6:
        return 1.0
    return solid_mod.dot(solid_mod.unit(centre), solid_mod.normal_of(face.points))


def run(suite: Suite) -> None:
    check = suite.check

    @check("every primitive is wound so its faces look outward")
    def _():
        # The bug this exists for. Half the faces are culled either way, so
        # the face count says nothing; only the normals do.
        cases = {
            "ellipsoid": (solid_mod.ellipsoid(1, 1, 1.4, "x", rings=9,
                                              segments=14), None),
            "tapered": (solid_mod.ellipsoid(1, 1, 1.4, "x", rings=9,
                                            segments=14, taper=0.2), None),
            "tube": (solid_mod.tube((0, 0, -1), (0, 0, 1), 0.6, "x"), None),
            "cone": (solid_mod.tube((0, 0, -1), (0, 0, 1), 0.6, "x",
                                    radius1=0.05), None),
            "box": (solid_mod.box(1.2, 1.2, 1.2, "x"), None),
            "ring": (solid_mod.ring_of(1.0, 0.25, "x"), 1.0),
        }
        for name, (faces, axis) in cases.items():
            inward = [f for f in faces if _outward(f, axis) < 0]
            assert not inward, (
                f"{name}: {len(inward)} of {len(faces)} faces wound inward — "
                "the near half of the solid will be culled and you will see "
                "through it")
        return " · ".join(f"{k} {len(v[0])}f" for k, v in cases.items())

    @check("a solid actually occludes what is inside it")
    def _():
        # The symptom, checked directly rather than through the normals: put a
        # small box inside a big sphere and confirm nothing of the box is
        # drawn in front of the shell.
        faces = (solid_mod.ellipsoid(1, 1, 1, "hull", rings=12, segments=18)
                 + solid_mod.box(0.3, 0.3, 0.3, "cargo", tag="cargo"))
        painted = solid_mod.project(faces, solid_mod.View())
        assert painted, "nothing drew at all"
        nearest = painted[-1]
        assert nearest.tag != "cargo", (
            "the innermost box is drawn nearest the eye — the shell is "
            "inside out")
        hull_depths = [f.depth for f in painted if f.tag != "cargo"]
        cargo_depths = [f.depth for f in painted if f.tag == "cargo"]
        assert min(hull_depths) < min(cargo_depths), (
            "no part of the shell is nearer than the box it contains")
        return (f"{len(painted)} faces drawn, shell nearest at "
                f"{min(hull_depths):.2f} against box at {min(cargo_depths):.2f}")

    @check("every hull in the game builds a model that projects")
    def _():
        game = new_game("plans-all")
        families, faces = set(), 0
        for chassis in CHASSIS:
            game.ship.chassis = chassis.id
            game.ship.fitted = []
            model = plans_sim.build(game)
            assert model["solids"], f"{chassis.id} built nothing"
            all_faces = [f for s in model["solids"] for f in s.faces]
            for face in all_faces:
                assert len(face.points) >= 3, f"{chassis.id}: degenerate face"
                for point in face.points:
                    assert all(math.isfinite(v) for v in point), (
                        f"{chassis.id}: non-finite point {point}")
            painted = solid_mod.project(all_faces, solid_mod.View())
            assert painted, f"{chassis.id} projected to nothing"
            for one in painted:
                assert math.isfinite(one.depth) and 0 <= one.shade <= 1
            families.add(chassis.family)
            faces += len(all_faces)
        assert families == set(FORMS), f"families drawn: {families}"
        return (f"{len(CHASSIS)} hulls across {len(families)} families, "
                f"{faces:,} faces, all finite")

    @check("the model is the fitted list, so a refit changes the ship")
    def _():
        game = new_game("plans-refit")
        before = plans_sim.build(game)
        tags = {s.tag for s in before["solids"]}

        # Something in every slot the hull has, so nothing is drawn nowhere.
        chassis = CHASSIS_BY_ID[game.ship.chassis]
        added = []
        for slot in SLOT_ORDER:
            if not chassis.slots.get(slot):
                continue
            part = next((p for p in PARTS_BY_ID.values()
                         if p.slot == slot and p.id not in game.ship.fitted), None)
            if part:
                added.append(part.id)
        after = plans_sim.build(game, fitted=list(game.ship.fitted) + added)
        grown = {s.tag for s in after["solids"]} - tags
        assert set(added) <= grown, (
            f"fitted {added} and the model gained {sorted(grown)}")
        assert after["faces"] > before["faces"], "the model did not grow"

        # And taking everything off leaves a bare hull.
        bare = plans_sim.build(game, fitted=[])
        for pid in game.ship.fitted:
            assert pid not in {s.tag for s in bare["solids"]}, (
                f"{pid} is drawn on a ship with nothing fitted")
        return (f"{len(added)} fittings added → {len(grown)} new solids, "
                f"{before['faces']:,} → {after['faces']:,} faces")

    @check("the hold and the berths draw what is really aboard")
    def _():
        game = new_game("plans-hold")
        game.ship.cargo = {"ore": 40, "biomass": 12}
        model = plans_sim.build(game)
        drawn = {s.tag: s for s in model["solids"]}
        assert "cargo:ore" in drawn and "cargo:biomass" in drawn, sorted(drawn)
        assert "cargo:xenolith" not in drawn, "drew a hold of something absent"
        assert "40" in drawn["cargo:ore"].detail, drawn["cargo:ore"].detail

        # More ore than biomass, so its block must be the taller of the two.
        def height(tag):
            points = [p for f in drawn[tag].faces for p in f.points]
            return max(p[2] for p in points) - min(p[2] for p in points)
        assert height("cargo:ore") > height("cargo:biomass"), (
            "forty tonnes draws no bigger than twelve")

        berths = [s for s in model["solids"] if s.tag.startswith("berth:")]
        filled = [s for s in berths if s.name != "empty berth"]
        assert len(filled) == len(game.officers), (
            f"{len(filled)} berths lit for {len(game.officers)} officers")
        assert game.officers[0].name in {s.name for s in filled}
        return (f"{len(berths)} berths, {len(filled)} filled by name; "
                f"ore block {height('cargo:ore'):.3f} against biomass "
                f"{height('cargo:biomass'):.3f}")

    @check("a cutaway takes the skin off and leaves everything else")
    def _():
        game = new_game("plans-cut")
        whole = plans_sim.build(game)
        cut = plans_sim.build(game, cutaway=True)
        assert "hull" in {s.tag for s in whole["solids"]}
        assert "hull" not in {s.tag for s in cut["solids"]}, (
            "the cutaway still draws the skin")
        assert {s.tag for s in cut["solids"]} | {"hull"} == \
               {s.tag for s in whole["solids"]}, (
            "the cutaway dropped something other than the skin")
        return (f"{whole['faces']:,} faces with the skin on, "
                f"{cut['faces']:,} with it off")

    @check("every slot a hull has is somewhere to put something")
    def _():
        # A part fitted to a slot with no mount would be silently invisible —
        # the same shape of defect as a work gated behind a phantom tech.
        missing = []
        for chassis in CHASSIS:
            form = form_for(chassis.family)
            for slot, count in chassis.slots.items():
                if count and not form.mounts.get(slot):
                    missing.append(f"{chassis.id}:{slot}")
                if count and slot not in SLOT_SHAPE:
                    missing.append(f"{chassis.id}:{slot} has no shape")
        assert not missing, f"slots that draw nowhere: {sorted(set(missing))}"
        return (f"{len(CHASSIS)} hulls, every slot they carry has a mount "
                f"and a shape")

    @check("a fitting on the flank sits on the skin, not inside it")
    def _():
        # Mounts are written as a radius and a height, which buries them: the
        # first draft put every pod inside the beam and the ship looked bare.
        # Axial mounts are exempt on purpose — a compute core belongs inside,
        # and the cutaway is how you look at it.
        buried, seated, axial = [], 0, 0
        for family, form in FORMS.items():
            for slot, mounts in form.mounts.items():
                for mount in mounts:
                    size = form.beam * 0.34 * mount.size
                    x, y, z = plans_sim._seat(form, mount, size)
                    if math.hypot(*mount.at[:2]) < 1e-6:
                        axial += 1
                        continue
                    skin = plans_sim._radius_at(form, z)
                    if math.hypot(x, y) < skin:
                        buried.append(f"{family}:{slot}")
                    else:
                        seated += 1
        assert not buried, f"flank mounts inside the hull: {sorted(set(buried))}"
        assert seated > 20, f"only {seated} flank mounts checked"
        return (f"{seated} flank mounts on the skin across {len(FORMS)} "
                f"families, {axial} axial ones left inside on purpose")
