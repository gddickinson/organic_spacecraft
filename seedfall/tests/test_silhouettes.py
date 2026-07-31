"""One shape per sort of thing, and the sky knowing which sort it is looking at.

Measured before this suite existed. `ui/viewport._sky` drew **everything that is
not a world** with a single mesh:

    render3d.draw(p, camera, models3d.SHIPYARD, sight.at, ...)

Across four sectors that is 67 quays, 36 Weave gates and 16 Fleet Hubs, plus
five errands of traffic — all of it the same shipyard. Not the same shape
recoloured: the same shape.

The information was there and thrown away. `track.Contact.berth` has said quay,
hub, holding or gate since it was written — its own docstring says "a screen
should not have to read an id to know whether it is looking at a shipyard or at
something older than the Charter" — and `sky.build` set `look=""` for every
anchorage and every hull it produced.

The claims:

- **The sky knows what it is drawing.** A gate arrives at the window as a gate.
- **Every sort the game can produce has a silhouette**, berths and errands
  alike, and nothing is left to a default nobody chose.
- **They are different pictures**, measured as rendered silhouettes rather than
  as different tuples — two meshes can differ in every vertex and read as the
  same blob.
- **A ship is shown broadside.** Every hull here is authored nose along +z, and
  at the tilt the sky used they were all the same foreshortened lump: the
  silhouettes existed and none of them was visible.
- **The sky and the approach agree**, so what you pick out at range is what you
  come alongside.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import berths3d, models3d, ships3d
from ..sim import sky as sky_sim
from ..sim import track as track_sim
from ..sim import traffic as traffic_sim
from .harness import Suite

SIZE = 150


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _mask(kind: str, look: str) -> set:
    """The pixels one sort of thing covers, at the attitude it is shown at."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import render3d

    _app()
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    sky = QColor("#000000")
    image.fill(sky)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                             width=SIZE, height=SIZE,
                             half_fov=math.radians(30))
    shown = models3d.present(kind, look, elapsed=0.0)
    render3d.draw(painter, camera, shown["mesh"], (0.0, 0.0, 3.4), 1.0,
                  light=(-0.55, -0.35, 0.75), spin=shown["spin"] + 0.6,
                  tilt=shown["tilt"])
    painter.end()
    return {(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def _overlap(a: set, b: set) -> float:
    """How alike two silhouettes are, 0 (nothing shared) to 1 (identical)."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the sky knows what sort of thing it is drawing")
    def _():
        # The defect itself: `look` was "" for every anchorage and every hull,
        # so the window had a kind and nothing else to pick a mesh by.
        game = new_game("silhouette")
        seen = sky_sim.build(game, None)
        anchorages = [s for s in seen if s.kind == "anchorage"]
        hulls = [s for s in seen if s.kind == "hull"]
        assert anchorages, "no anchorage in the sky to check"
        assert hulls, "no traffic in the sky to check"
        assert all(s.look for s in anchorages), (
            "an anchorage reached the window with no sort on it: "
            f"{[s.name for s in anchorages if not s.look]}")
        assert all(s.look for s in hulls), (
            "a hull reached the window with no errand on it: "
            f"{[s.name for s in hulls if not s.look]}")
        # And the sort is the one the plot uses, not a second vocabulary.
        by_name = {c.name: c for c in track_sim.contacts(game)}
        for sight in anchorages:
            assert sight.look == by_name[sight.name].berth, (
                f"{sight.name}: sky says {sight.look!r}, plot says "
                f"{by_name[sight.name].berth!r}")
        return (f"{len(anchorages)} berths and {len(hulls)} hulls, every one "
                "carrying what it is")

    @check("every sort the game produces has a shape of its own")
    def _():
        # Nothing left to a default nobody chose. Both vocabularies, read from
        # the modules that own them rather than listed here.
        missing = [e for e in traffic_sim.ERRANDS if e not in ships3d.SHIPS]
        assert not missing, f"errands with no silhouette: {missing}"
        berths = set()
        for seed in ("s1", "s2", "s3", "s4"):
            game = new_game(seed)
            for system in game.galaxy.systems:
                for contact in track_sim.contacts(game, system):
                    if contact.kind == "anchorage":
                        berths.add(contact.berth)
        # Your own holdings turn up as berth sorts too — one per colony class,
        # drawn by `data/works3d` rather than by the four here — so a fresh
        # sector is not the whole vocabulary. Plant one of everything.
        from ..data import works3d
        from ..data.colonies import COLONIES
        from ..sim import colony as colony_sim
        settled = new_game("settled")
        ground = settled.system.bodies[-1]
        for index, klass in enumerate(COLONIES):
            settled.colonies.append(colony_sim.Colony(
                id=index + 1, class_id=klass.id, name=klass.name,
                system_id=settled.system.id, body_id=ground.id,
                need=0, online=True))
        for contact in track_sim.contacts(settled):
            if contact.kind == "anchorage":
                berths.add(contact.berth)
        stray = sorted(b for b in berths
                       if b not in berths3d.BERTHS and not works3d.is_work(b))
        assert not stray, f"berth sorts the sector makes and nothing draws: {stray}"
        assert len(berths) >= 3, berths
        return (f"{len(traffic_sim.ERRANDS)} errands and {len(berths)} berth "
                f"sorts in play, all drawn: {', '.join(sorted(berths))}")

    @check("they are different pictures, not different tuples")
    def _():
        # Two meshes can differ in every vertex and still render as the same
        # blob. This compares what lands on the screen.
        sorts = ([("anchorage", b) for b in sorted(berths3d.BERTHS)]
                 + [("hull", e) for e in sorted(traffic_sim.ERRANDS)])
        masks = {(k, s): _mask(k, s) for k, s in sorts}
        for key, mask in masks.items():
            assert len(mask) > 120, f"{key} covers only {len(mask)} pixels"
        worst, pair = 0.0, None
        for i, one in enumerate(sorts):
            for other in sorts[i + 1:]:
                # A raider is deliberately drawn as an unmarked hull — it has
                # no transponder, and telling one from a stranger at range is
                # the tension the encounter is built on.
                if {one[1], other[1]} == {"raider", "unmarked"}:
                    continue
                share = _overlap(masks[one], masks[other])
                if share > worst:
                    worst, pair = share, (one[1], other[1])
        # The bar, and the margin, both measured. As shipped the worst pair
        # shares 66% of its outline; before this cycle every one of these
        # sorts was the same mesh and every pair shared 100%. Fattening the
        # prospector's spine — a deliberate attempt to make two of them alike
        # again — only reaches 67%, because the boom and the cradle still
        # carry the shape, so the mutation is mild rather than the check being
        # slack. The bar sits at 72%: above anything the sweep could reach by
        # blunting one hull, and far below one-mesh-for-all.
        assert worst < 0.72, (
            f"{pair[0]} and {pair[1]} share {worst:.0%} of their silhouette — "
            "that is one shape with a variation, not two things")
        return (f"{len(sorts)} sorts drawn; the closest pair "
                f"({pair[0]}/{pair[1]}) shares {worst:.0%} of its outline")

    @check("a ship is shown broadside, so its silhouette is visible")
    def _():
        # Every hull is authored nose along +z. At the tilt the sky used, all
        # five errands rendered as the same foreshortened lump — the shapes
        # were real and the picture could not show them.
        from PyQt6.QtGui import QColor, QImage, QPainter
        from ..ui import render3d

        def spread(look: str, tilt: float) -> float:
            """How wide the picture of a hull is against how tall."""
            _app()
            image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
            image.fill(QColor("#000000"))
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1),
                                     up=(0, 1, 0), width=SIZE, height=SIZE,
                                     half_fov=math.radians(30))
            render3d.draw(painter, camera, ships3d.ship_mesh(look),
                          (0.0, 0.0, 3.4), 1.0, light=(-0.55, -0.35, 0.75),
                          spin=0.6, tilt=tilt)
            painter.end()
            on = [(x, y) for y in range(SIZE) for x in range(SIZE)
                  if image.pixel(x, y) != QColor("#000000").rgb()]
            assert on, look
            tall = max(y for _x, y in on) - min(y for _x, y in on) + 1
            wide = max(x for x, _y in on) - min(x for x, _y in on) + 1
            return tall / max(1, wide)

        shipped = models3d.ATTITUDE["hull"][1]
        assert shipped > 1.0, (
            f"hulls are shown at a tilt of {shipped:.2f}, which is nose-on")
        for look in ("courier", "trader", "patrol"):
            nose_on = spread(look, 0.42)
            side_on = spread(look, shipped)
            assert side_on > nose_on * 1.4, (
                f"{look}: nose-on it is {nose_on:.2f} tall for its width and "
                f"at the shipped attitude {side_on:.2f} — the profile is not "
                "being shown")
        return (f"at a tilt of {shipped:.2f} a hull reads as a profile, "
                "half again longer than the nose-on view")

    @check("the sky and the approach draw the same thing")
    def _():
        # One door. What you pick out at forty kilometres has to be what you
        # come alongside, or the catalogue is two catalogues.
        game = new_game("silhouette")
        from ..sim import targets as target_sim
        for contact in track_sim.contacts(game):
            if contact.kind not in ("anchorage", "hull"):
                continue
            target = target_sim.target_from_contact(game, contact)
            look = (target.berth if contact.kind == "anchorage"
                    else target.errand)
            plot_look = (contact.berth if contact.kind == "anchorage"
                         else contact.errand)
            assert look == plot_look, (contact.name, look, plot_look)
            assert (models3d.present(contact.kind, look)["mesh"]
                    is models3d.present(contact.kind, plot_look)["mesh"])
        return "every berth and hull resolves to one mesh from both doors"
