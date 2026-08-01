"""Twenty machines, and whether any of them is its own picture.

The Machines tab was the last catalogue page in the game that was a wall of
text. `data/robots3d.py` builds one body per class **out of the class's own
entry**, the way `works3d` builds a holding and `hulls3d` a hull — so a new
class gets a body without anybody drawing one, and the portrait cannot disagree
with the card.

The vocabulary is the one real robotics uses: what it stands on, what it works
with, what it senses with. A frame that lifts has an arm; one thrown at a body
and left has thrusters and no feet; one that is worn is a harness with a
person-shaped hole; a mind racked in a hold is neither.

The claims:

- **Every class has a body, and it is built from the card** — the duties, the
  family, the tonnage, the level and the autonomy rung, each drawn.
- **They are different pictures**, measured as rendered silhouettes. This check
  earned its keep three times in one cycle, every time on a difference that was
  drawn and invisible.
- **The catalogue shows them**, on the codex and in the shop.
"""

from __future__ import annotations

from ..data import robots3d
from ..data.robots import ROBOTS, ROBOTS_BY_ID
from .harness import Suite

SIZE = 150

#: What the closest pair may share.
#:
#: Measured, and higher than `test_silhouettes`' 72% on purpose. That bar is for
#: gates against couriers — long spindly things whose outlines barely meet.
#: These are compact frames that all stand on legs and carry arms, and two of
#: similar tonnage doing similar work genuinely look alike; the honest worst
#: pair is a Precentor against a Coral Tender at 86%, which differ by a family's
#: build, a second pair of manipulators and their paint.
#:
#: The margin is what makes it a check rather than a rubber stamp: the three
#: defects it caught this cycle sat at **100%** (a gun mount drawn exactly where
#: a hybrid's graft band already was), **95%** (bulk reaching only the trunk,
#: so a 2 t drone and a 4 t Myrmidon matched) and **89%** (level drawn nowhere,
#: so a senior machine looked like a junior one). All three were differences
#: that existed in the data and could not be seen.
ALIKE = 0.88


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _mask(look: str) -> set:
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import render3d, thumb3d

    _app()
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    sky = QColor("#000000")
    image.fill(sky)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    camera = render3d.Camera(at=(0, 0, 0), forward=(0, 0, 1), up=(0, 1, 0),
                             width=SIZE, height=SIZE,
                             half_fov=thumb3d.HALF_FOV)
    thumb3d.paint(painter, camera, "robot", look)
    painter.end()
    return {(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def run(suite: Suite) -> None:
    check = suite.check

    @check("every class has a body, and it is built from its own card")
    def _():
        for klass in ROBOTS:
            body = robots3d.BODIES.get(klass.id)
            assert body is not None, klass.id
            assert body.mesh[0] and body.mesh[1], klass.id
        # Each fact on the card is drawn somewhere. Not "it has parts" — the
        # specific part the specific words demand.
        want = {
            "stevedore": "hold",        # cargo
            "scarab": "rig",            # mining
            "hullwright": "arm",        # repair
            "lamplighter": "dish",      # survey
            "lamplighter2": None,
            "loader": "harness",        # worn, not sent
            "anchorite": "rack",        # a mind with no body
            "shardling": "swarm",
            "magazine": "guns",         # stands tactical
            "graftpilot": "graft",      # a person is in there
            "servitor": "pack",         # goes down a hole
        }
        for look, part in want.items():
            if part is None:
                continue
            parts = robots3d.parts_of(look)
            assert part in parts, f"{look} has no {part}: {parts}"
        # Autonomy is drawn: a machine that decides for itself has something to
        # decide with; one somebody else flies has a relay mast.
        for klass in ROBOTS:
            parts = robots3d.parts_of(klass.id)
            assert ("head" in parts) == (klass.autonomy >= 3), (
                f"{klass.id} is E{klass.autonomy} and carries {parts}")
        # And tonnage: the heaviest class reads bigger than the lightest.
        heavy = max(ROBOTS, key=lambda k: k.mass_t)
        light = min(ROBOTS, key=lambda k: k.mass_t)
        assert robots3d.bulk_of(heavy) > robots3d.bulk_of(light) * 1.3, (
            robots3d.bulk_of(heavy), robots3d.bulk_of(light))
        # No two classes are the same body.
        seen: dict = {}
        for klass in ROBOTS:
            key = (robots3d.parts_of(klass.id), klass.family,
                   round(robots3d.bulk_of(klass), 2))
            seen.setdefault(key, []).append(klass.id)
        same = {k: v for k, v in seen.items() if len(v) > 1}
        assert not same, f"classes built identically: {same}"
        return (f"{len(ROBOTS)} bodies, {len(seen)} distinct builds · "
                f"{heavy.name} at {robots3d.bulk_of(heavy):.2f} bulk against "
                f"{light.name} at {robots3d.bulk_of(light):.2f}")

    @check("they are different pictures, not different tuples")
    def _():
        masks = {k.id: _mask(k.id) for k in ROBOTS}
        for look, mask in masks.items():
            assert len(mask) > 600, f"{look} covers only {len(mask)} pixels"
        ids = sorted(masks)
        worst, pair = 0.0, None
        for i, one in enumerate(ids):
            for other in ids[i + 1:]:
                a, b = masks[one], masks[other]
                share = len(a & b) / len(a | b)
                if share > worst:
                    worst, pair = share, (one, other)
        assert worst < ALIKE, f"{pair} share {worst:.0%} of their outline"
        return (f"{len(ids)} machines, worst pair {pair[0]}/{pair[1]} at "
                f"{worst:.0%} against a {ALIKE:.0%} bar")

    @check("the catalogue and the shop both show them")
    def _():
        keep = _app()
        assert keep is not None
        from ..core.state import new_game
        from ..ui.thumb3d import Thumb
        from ..ui.window import MainWindow

        game = new_game("robot-cards")
        window = MainWindow(game)
        window.toast = lambda *a, **k: None
        window.go("codex")
        view = window.views["codex"]
        view.tab = "machines"
        view.refresh()
        on_codex = [t for t in view.findChildren(Thumb) if t.kind == "robot"]
        window.go("yard")
        yard = window.views["yard"]
        yard.tab = "machines"
        yard.refresh()
        in_shop = [t for t in yard.findChildren(Thumb) if t.kind == "robot"]
        window.close()
        assert len(on_codex) == len(ROBOTS), (
            f"{len(on_codex)} portraits on {len(ROBOTS)} codex cards")
        assert len(in_shop) == len(ROBOTS), (
            f"{len(in_shop)} portraits on {len(ROBOTS)} shop cards")
        return (f"{len(on_codex)} on the codex, {len(in_shop)} in the shop")

    @check("a machine that flies carries its ring under it, where it belongs")
    def _():
        # `robots3d.DRIVE_Z` places a drone's thruster ring and nothing outside
        # the mesh reads it, so it swept as protected while being pinned by
        # nothing — an arithmetic assertion would only restate it.
        #
        # **It reaches the picture, measured.** Doubling it to -0.84 and
        # re-rendering: lamplighter keeps 50.0% of its silhouette, verger
        # 61.0%, rigger 80.5% — and `loader`, which walks, is untouched at
        # 100.0%. So the geometry below is what a viewer sees, and the numbers
        # here are **absolute** rather than read off `DRIVE_Z`, which is the
        # whole point.
        from ..data.robots3d import HEAD_Z
        flying = sorted(l for l in robots3d.BODIES
                        if "thrusters" in robots3d.parts_of(l))
        walking = sorted(l for l in robots3d.BODIES
                         if "thrusters" not in robots3d.parts_of(l))
        assert flying == ["lamplighter", "rigger", "verger"], (
            f"the machines that fly are {flying}; the brackets below are "
            "absolute and must be re-measured by hand if that changes")
        assert len(walking) == 17, f"{len(walking)} walkers, not 17"

        def planes(look):
            return {round(v[2], 3) for v in robots3d.mesh_for(look)[0]}

        for look in flying:
            zs = [v[2] for v in robots3d.mesh_for(look)[0]]
            here = planes(look)
            # The ring is a tube 0.1 deep centred on the offset: -0.47 and
            # -0.37 with the offset at -0.42. Move the offset and both go.
            assert -0.47 in here and -0.37 in here, (
                f"{look} flies and has no ring at -0.47/-0.37: "
                f"{sorted(z for z in here if z < 0)}")
            # And it is **under** the machine: below the head, below the
            # midline, and the lowest thing on it. A ring on top would satisfy
            # a check that only asked whether one existed.
            assert min(zs) >= -0.60, (
                f"{look} reaches {min(zs):+.3f}, below the thruster boxes")
            assert -0.60 <= min(zs) <= -0.50, (
                f"{look}'s lowest geometry is {min(zs):+.3f}; the ring's own "
                "boxes should be the bottom of it")
            assert max(zs) > HEAD_Z > -0.37, (
                f"{look} is upside down: head at {HEAD_Z}, ring at -0.37")

        for look in walking:
            here = planes(look)
            assert -0.47 not in here and -0.37 not in here, (
                f"{look} walks and yet carries a thruster ring")
        return (f"{len(flying)} fly with the ring at -0.47/-0.37 and nothing "
                f"below -0.60; {len(walking)} walk and carry none")

    @check("a picture nobody drew: a new class gets a body")
    def _():
        # The whole claim of building shapes out of data rather than by hand.
        # A class that does not exist in `ROBOTS` still comes out with a body
        # that reads its entry.
        from dataclasses import replace
        base = ROBOTS_BY_ID["myrmidon"]
        invented = replace(base, id="invented", name="Invented Frame",
                           duties=("mine", "survey"), level=5, mass_t=11.0,
                           autonomy=4, family="fabricated")
        body = robots3d.build(invented)
        parts = body.parts
        assert "rig" in parts and "dish" in parts, parts
        assert "head" in parts, "an E4 class came out with a relay mast"
        assert "hands" in parts, "a level-five class got one pair of arms"
        assert len(body.mesh[1]) > 40, len(body.mesh[1])
        assert robots3d.bulk_of(invented) > robots3d.bulk_of(base)
        return f"a class nobody drew came out as {', '.join(parts)}"
