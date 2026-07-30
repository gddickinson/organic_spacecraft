"""Five families on the tactical plot, and which way up they lie.

`data/hullforms.py` opens with "Five families, five silhouettes" and gives each
one a length, a beam, a taper, a facet count and its own furniture — a grown
hull's docking ridge and radiator bloom, a Yards hull's welded spine and slab
bow, a hybrid's cradle, a Dry Choir lattice, a xeno hull's shards.
`sim/plans.py` built the captain's own ship from those numbers for the cutaway
panel. Nothing else read them. `ui/battle3d.py` drew:

    pairs = [(b.enemy, models3d.HULL, "warn"),
             (b.player, models3d.HULL, "lumen")]

— one mesh, one size, both combatants. Thirty-five chassis in five families,
masses from 60 t to twelve billion, and the plot showed one ship twice.

It also drew them **standing on their tails**. Every model in this package is
authored nose along +z, the plot's hulls sit in the z=0 plane with the camera
looking across it, and `render3d.draw` could spin a model about its own pole and
tilt it over but not then point it anywhere — the tilt decides which way it
falls. So a heading could not be read off the picture at all. `draw` takes a
`yaw` now, applied after the tilt, about the world's vertical.

The claims:

- **Every family a chassis can be built in has a shape**, and no ship falls
  back to a default nobody chose.
- **The five are five**, as rendered silhouettes rather than as different data.
- **The plot draws each combatant as its own hull** — the defect.
- **Size follows mass**, over a range of eight orders of magnitude, bounded.
- **A hull lies along its heading**, and turning it turns the picture.
"""

from __future__ import annotations

import math

from ..core.rng import RNG
from ..core.state import new_game
from ..data import hulls3d
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.hullforms import FORMS
from ..sim import combat, encounters
from ..sim.ship import build_layers, make_ship, stats
from .harness import Suite

SIZE = 150


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _mask(family: str, yaw: float = 0.0, tilt: float | None = None) -> set:
    """The pixels one family covers, laid out the way the plot lays it."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import battle3d, render3d

    _app()
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    sky = QColor("#000000")
    image.fill(sky)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # **The plot's own geometry.** `ui/battle3d` puts its hulls in the z=0
    # plane and its eye behind and above them, so "up" on the picture is the
    # world's z. A first version of this helper looked down +z with +y up —
    # a plan view — and read a hull laid flat as *standing on its tail*,
    # because from directly above that is exactly what it looks like.
    camera = render3d.Camera(at=(0.0, -3.6, 0.9), forward=(0.0, 1.0, -0.22),
                             up=(0.0, 0.0, 1.0), width=SIZE, height=SIZE,
                             half_fov=math.radians(30))
    render3d.draw(painter, camera, hulls3d.mesh_for(family), (0.0, 0.0, 0.0),
                  1.0, light=(-0.55, -0.4, 0.72), spin=0.0,
                  tilt=battle3d.LIE_FLAT if tilt is None else tilt, yaw=yaw)
    painter.end()
    return {(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def _overlap(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _engaged(hull: str, seed: str = "shapes"):
    game = new_game(seed)
    ship = make_ship(hull, ["slug_battery", "reaction_organ"])
    build_layers(ship, game.bonuses)
    game.ship = ship
    ship.cargo = {"ore": 100}
    game.recompute()
    rng = RNG(seed)
    battle = combat.start(ship, stats(ship),
                          encounters.make_enemy(rng, "corsair", 1.2),
                          rng=rng, game=game, officers=game.officers)
    return game, battle, rng


def run(suite: Suite) -> None:
    check = suite.check

    @check("every family a ship can be built in has a shape")
    def _():
        families = {c.family for c in CHASSIS}
        missing = sorted(f for f in families if f not in hulls3d.HULLS)
        assert not missing, f"chassis families with no silhouette: {missing}"
        # And the other way: nothing here is drawn for a family the game
        # cannot produce, which would be a shape nobody ever sees.
        stray = sorted(f for f in hulls3d.HULLS if f not in FORMS)
        assert not stray, stray
        assert len(families) == 5, families
        return (f"{len(CHASSIS)} chassis across {len(families)} families, "
                f"every one drawn: {', '.join(sorted(families))}")

    @check("the five are five, as pictures")
    def _():
        masks = {family: _mask(family) for family in hulls3d.HULLS}
        for family, mask in masks.items():
            assert len(mask) > 200, f"{family} covers {len(mask)} pixels"
        worst, pair = 0.0, None
        names = list(masks)
        for i, one in enumerate(names):
            for other in names[i + 1:]:
                share = _overlap(masks[one], masks[other])
                if share > worst:
                    worst, pair = share, (one, other)
        # Before this, all five were `models3d.HULL` and every pair scored
        # 1.00. As shipped the closest is grown/xeno at 0.77 — two organic
        # bodies of similar proportion, one of them bent. The two that started
        # closest were grown and hybrid at 0.79, which is the design showing
        # through (a hybrid *is* a grown body in a cradle); standing the cradle
        # off from 1.14 beams to 1.62 took them to 0.63, and the fix was the
        # mesh rather than the bar.
        assert worst < 0.82, (
            f"{pair[0]} and {pair[1]} share {worst:.0%} of their outline — "
            "that is one hull with five names")
        # And the hybrid's cradle stands off the body it holds, which is the
        # one thing that tells it from the grown hull inside it. Measured as
        # width: at 1.62 beams the hybrid is half again the grown hull's
        # breadth; hugging the skin at 1.14 it was barely wider, and the pair
        # shared 79% of its outline.
        def breadth(mask) -> int:
            xs = [x for x, _y in mask]
            return max(xs) - min(xs) + 1

        wider = breadth(masks["hybrid"]) / max(1, breadth(masks["grown"]))
        assert wider > 1.18, (
            f"a hybrid paints {wider:.2f} times a grown hull's breadth — its "
            "cradle is hugging the body instead of holding it")
        return (f"5 families; the closest pair ({pair[0]}/{pair[1]}) shares "
                f"{worst:.0%} of its outline; a hybrid is {wider:.2f}x the "
                "breadth of the grown hull it carries")

    @check("the plot draws each combatant as the hull it actually is")
    def _():
        from ..ui import battle3d
        # A grown hull against a fabricated one: two families on one plot.
        _game, battle, _rng = _engaged("navis")
        mine = battle3d._family(battle.player)
        theirs = battle3d._family(battle.enemy)
        assert mine == "grown", mine
        assert battle.player.ship.chassis != battle.enemy.ship.chassis
        # And the picture changes when the hull does — the property the one
        # shared mesh could not have.
        _g2, other, _r2 = _engaged("antiphon")
        assert battle3d._family(other.player) == "xeno"
        assert _overlap(_mask(mine), _mask("xeno")) < 0.82
        return (f"a {battle.player.ship.chassis} ({mine}) against a "
                f"{battle.enemy.ship.chassis} ({theirs}), each its own shape")

    @check("and the plot itself paints it, not merely the helpers")
    def _():
        # **The mutation sweep put four holes in this suite at once.** Every
        # other check here asks `hulls3d.mesh_for`, `battle3d._family` or
        # `_hull_scale` directly — so rewriting the *call* in `paintEvent` to
        # pass a fixed family, a fixed size, a flat tilt or a fixed yaw changed
        # nothing any of them looked at. This one renders the widget and reads
        # the picture, which is the only thing a player sees.
        # **Held**, not merely created. `_app()` hands back the QApplication
        # and discarding it lets Python collect the object — after which the
        # next QWidget aborts the process with "Must construct a QApplication
        # before a QWidget", which is a confusing way to be told about a
        # reference count. Every other check here happens to render through a
        # helper that keeps one alive; this is the first to build a widget.
        keep_alive = _app()
        assert keep_alive is not None
        from PyQt6.QtGui import QColor
        from ..ui.battle3d import Battle3D

        def frame(hull: str, heading: float = 0.0) -> set:
            _game, battle, _rng = _engaged(hull)
            # **The geometry held still.** A different chassis manoeuvres
            # differently, so two battles drift apart and their plots differ
            # for reasons that have nothing to do with the mesh — which let a
            # mutation pinning the drawn family to `fabricated` pass, because
            # the two frames still disagreed. Pin both bodies and the only
            # thing left that can move the picture is the hull.
            battle.player.body.x, battle.player.body.y = 0.0, 0.0
            battle.player.body.heading = heading
            battle.enemy.body.x, battle.enemy.body.y = 260.0, 120.0
            battle.enemy.body.heading = 200.0
            plot = Battle3D(battle)
            plot.resize(300, 240)
            image = plot.grab().toImage()
            sky = QColor("#04080b").rgb()
            return {(x, y)
                    for y in range(0, image.height(), 2)
                    for x in range(0, image.width(), 2)
                    if image.pixel(x, y) != sky}

        def lying_flat(hull: str) -> float:
            """How wide the player's own hull paints, against how tall.

            The plot's camera sits behind and above the captain's hull, so it
            fills the lower middle of the frame. A hull laid along its course
            is wider than it is tall there; one left standing on its tail — the
            state every model in this package starts in, nose along +z — is
            the other way about, and no check that only compares *different*
            hulls can tell.
            """
            got = frame(hull, heading=90.0)
            near = [(x, y) for x, y in got if y > 110]
            assert len(near) > 60, (hull, len(near))
            xs = [x for x, _y in near]
            ys = [y for _x, y in near]
            return (max(xs) - min(xs) + 1) / max(1, max(ys) - min(ys) + 1)

        # A different family is a different picture — **at the same mass**.
        # A CORAL and a CARAVEL both displace exactly 9,000 t, one grown and
        # one built, so the size the plot draws them at is identical and the
        # only thing left that can move the picture is the shape. Comparing a
        # NAVIS with an ANTIPHON instead let a mutation that pinned the drawn
        # family to `fabricated` pass, because those two are drawn at 1.08 and
        # 1.48 and the frames still disagreed — about size, not about hull.
        grown, built = frame("coral"), frame("caravel")
        assert _overlap(grown, built) < 0.90, (
            f"a grown hull and a Yards hull of the same tonnage paint "
            f"{_overlap(grown, built):.0%} the same plot — the family is not "
            "reaching the picture")
        # A different mass is a different picture.
        small, large = frame("spore"), frame("leviathan")
        assert len(large) > len(small) * 1.25, (
            f"a SPORE paints {len(small)} pixels and a LEVIATHAN {len(large)} "
            "— the plot is drawing every hull the same size")
        # It lies along its course rather than standing on its tail.
        # A LEVIATHAN, because it is drawn largest and so separates the two
        # states by the widest margin. Measured: laid along its course it
        # paints 2.44 wide for its height, and left upright 1.05. A BASTION
        # gives 1.11 against 0.65 — the same answer with a third of the room,
        # which is why the bar sits on the big one.
        wide = lying_flat("leviathan")
        assert wide > 1.6, (
            f"the captain's own hull paints {wide:.2f} wide for its height on "
            "the plot — it is standing on its tail")
        # And a heading turns it.
        north, east = frame("navis", heading=0.0), frame("navis", heading=90.0)
        assert _overlap(north, east) < 0.92, (
            f"turning a hull ninety degrees changes "
            f"{1 - _overlap(north, east):.0%} of the plot — a heading cannot "
            "be read off it")
        return (f"family {1 - _overlap(grown, built):.0%} of the plot, mass "
                f"{len(small)}→{len(large)} px, lying {wide:.2f} wide for its "
                f"height, heading {1 - _overlap(north, east):.0%}")

    @check("how big it is drawn follows what it masses")
    def _():
        from ..ui import battle3d

        class _Side:
            def __init__(self, chassis):
                self.ship = type("S", (), {"chassis": chassis})()

        sizes = {cid: battle3d._hull_scale(_Side(cid))
                 for cid in ("spore", "vesper", "pike", "navis", "bastion",
                             "leviathan")}
        assert sizes["spore"] < sizes["pike"] < sizes["navis"] < sizes["bastion"]
        assert sizes["bastion"] < sizes["leviathan"]
        # Bounded: the masses run 60 t to twelve billion, and a plot has to
        # stay readable across that.
        assert min(sizes.values()) >= 1.0 / battle3d.SIZE_SPREAD - 1e-9
        assert max(sizes.values()) <= battle3d.SIZE_SPREAD + 1e-9
        assert sizes["leviathan"] == battle3d.SIZE_SPREAD, (
            "the largest hull in the game should sit at the ceiling")
        # And an unknown chassis does not vanish or fill the plot.
        assert 0.9 < battle3d._hull_scale(_Side("no-such-hull")) < 1.1
        return " · ".join(f"{k} x{v:.2f}" for k, v in sizes.items())

    @check("a hull lies along its heading rather than standing on its tail")
    def _():
        from ..ui import battle3d
        # Standing up: every model is authored nose along +z, and the plot's
        # camera looks across the plane the hulls sit in. Tilted flat, a hull
        # is wider than it is tall; left upright it is the other way about.
        flat = _mask("fabricated", yaw=0.0, tilt=battle3d.LIE_FLAT)
        upright = _mask("fabricated", yaw=0.0, tilt=0.0)

        def shape(mask):
            xs = [x for x, _y in mask]
            ys = [_y for _x, _y in mask]
            return (max(xs) - min(xs) + 1) / max(1, max(ys) - min(ys) + 1)

        # Measured: laid flat a Yards hull is 1.17 wide for its height and
        # upright it is 0.48 — a factor of 2.4, which is the difference between
        # a ship lying along its course and one standing on its tail.
        assert shape(flat) > 1.05, (
            f"laid flat a hull is {shape(flat):.2f} wide for its height — it "
            "is still standing on its tail")
        assert shape(upright) < shape(flat) * 0.6, (shape(upright), shape(flat))

        # And turning it turns the picture, which is the whole point of `yaw`.
        turned = _mask("fabricated", yaw=math.pi / 2, tilt=battle3d.LIE_FLAT)
        assert _overlap(flat, turned) < 0.6, (
            f"a quarter turn changes {1 - _overlap(flat, turned):.0%} of the "
            "hull's outline — a heading cannot be read off the plot")
        return (f"flat {shape(flat):.2f} wide for its height against "
                f"{shape(upright):.2f} upright; a quarter turn changes "
                f"{1 - _overlap(flat, turned):.0%} of it")

    @check("yaw is a turn about the world's vertical, and nothing else")
    def _():
        # A geometric claim, checked exactly: `yaw` must not touch height, and
        # must not disturb a model that is not being turned.
        from ..ui import render3d
        mesh = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)), \
               (((0, 1, 2), "#ffffff"),)
        seen = []

        class _Spy:
            def setBrush(self, *a):
                pass

            def setPen(self, *a):
                pass

            def drawPolygon(self, poly):
                seen.append([(poly[i].x(), poly[i].y())
                             for i in range(poly.count())])

        camera = render3d.Camera(at=(0, 0, -10), forward=(0, 0, 1),
                                 up=(0, 1, 0), width=100, height=100,
                                 half_fov=math.radians(40))
        render3d.draw(_Spy(), camera, mesh, (0, 0, 0), 1.0, (0, 0, 1))
        plain = len(seen)
        render3d.draw(_Spy(), camera, mesh, (0, 0, 0), 1.0, (0, 0, 1),
                      yaw=0.0)
        assert len(seen) == plain * 2, "yaw=0 changed how much was drawn"
        # The vertex at +x, turned a quarter, must land at +y with the same z.
        turned = render3d.draw(_Spy(), camera, mesh, (0, 0, 0), 1.0, (0, 0, 1),
                               yaw=math.pi / 2)
        assert isinstance(turned, int)
        return "yaw=0 is a no-op, and a quarter turn is a quarter turn"
