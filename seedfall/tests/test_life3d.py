"""Sixteen body plans, eight biochemistries, and whether any of it is visible.

The Life tab was the last catalogue page in the game with no picture on it. The
difference from the hull, station and machine catalogues is that **there is no
bestiary to illustrate**: `world/planets._make_lifeform` assembles an organism from a
body plan, a metabolism and up to two traits, so a picture has to be built the
same way the creature was.

It is, and off the record itself — `Lifeform.name` *is* the body plan, because
`_make_lifeform` passes `rng.pick(FORMS)` straight into it.

The claims:

- **Every body plan the generator can pick has a body**, and they are different
  pictures — measured as rendered silhouettes.
- **The biochemistry is visible**, because a photoautotroph being green and a
  radiotroph not is the one thing the card says that a picture can show.
- **A trait you can see, you can see** — on every plan, not just the roomy ones.
  This is the check that caught a magnetotactic organism whose aligned chains
  changed *zero* pixels, and a grazer whose glass spines changed three.
- **An organism from the generator arrives with a body**, through the real
  `_make_lifeform`, so nothing depends on a table anybody has to remember to update.
"""

from __future__ import annotations

from ..data import life3d
from ..data.lifeforms import FORMS, METABOLISMS
from .harness import Suite

SIZE = 150

#: What the closest pair of body plans may share.
#:
#: Measured: the worst is a jointed swimmer against a luminous shoal at 79% —
#: two segmented animals of similar build, which is what they are. Sixteen
#: plans over five silhouettes will always cluster; the bar is set just above
#: the honest worst so the margin is real.
ALIKE = 0.82

#: The smallest change a trait may make to a picture, in pixels.
#:
#: Derived from what "you can see it" means at this size: forty pixels is about
#: a five-by-eight patch, the smallest mark that reads as deliberate rather than
#: as an artefact. Both defects this caught were far below it — a magnetotactic
#: organism at **0** and an armoured grazer's silaffin spines at **3**.
SHOWS = 40


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _mask(spec) -> set:
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
    thumb3d.paint(painter, camera, "life", spec)
    painter.end()
    return {(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def _colours(spec) -> set:
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
    thumb3d.paint(painter, camera, "life", spec)
    painter.end()
    return {image.pixel(x, y) for y in range(SIZE) for x in range(SIZE)
            if image.pixel(x, y) != sky.rgb()}


def run(suite: Suite) -> None:
    check = suite.check

    @check("every body plan the generator can pick has a body")
    def _():
        missing = [form for form in FORMS if form not in life3d.PLAN]
        assert not missing, f"plans the generator picks and nothing draws: {missing}"
        for form in FORMS:
            shape = life3d.SHAPES_BY_PLAN[form]
            assert shape.mesh[0] and shape.mesh[1], form
        used = {life3d.plan_of(form)[0] for form in FORMS}
        assert used <= set(life3d.SHAPES), used
        return (f"{len(FORMS)} body plans across {len(used)} silhouettes, "
                "every one built")

    @check("they are different pictures, not different tuples")
    def _():
        masks = {form: _mask((form, "photo", ())) for form in FORMS}
        for form, mask in masks.items():
            assert len(mask) > 300, f"{form} covers only {len(mask)} pixels"
        names = sorted(masks)
        worst, pair = 0.0, None
        for i, one in enumerate(names):
            for other in names[i + 1:]:
                a, b = masks[one], masks[other]
                share = len(a & b) / len(a | b)
                if share > worst:
                    worst, pair = share, (one, other)
        assert worst < ALIKE, f"{pair} share {worst:.0%} of their outline"
        return (f"{len(names)} plans, worst pair {pair[0]} / {pair[1]} at "
                f"{worst:.0%} against a {ALIKE:.0%} bar")

    @check("the biochemistry is visible")
    def _():
        # The one thing the card says that a picture can show: what it runs on.
        seen = {}
        for met in METABOLISMS:
            assert met[0] in life3d.LIVERY, f"{met[0]} has no livery"
            seen[met[0]] = _colours(("drifting bell", met[0], ()))
        for one, other in ((a, b) for i, a in enumerate(seen)
                           for b in list(seen)[i + 1:]):
            shared = len(seen[one] & seen[other]) / len(seen[one] | seen[other])
            assert shared < 0.5, (
                f"{one} and {other} are painted {shared:.0%} the same")
        return (f"{len(seen)} biochemistries, every one its own colour on the "
                "same body")

    @check("a trait you can see, you can see — on every plan")
    def _():
        # The defect this exists for: a magnetotactic organism's aligned chains
        # were drawn inside the body and changed **zero** pixels, and once that
        # was fixed a long low animal's marks were scaled off its height and
        # came out between three and sixteen. A mark is sized to the creature.
        faint = []
        worst = (10 ** 9, "")
        for form in FORMS:
            bare = _mask((form, "photo", ()))
            for trait in life3d.VISIBLE_TRAITS:
                got = _mask((form, "photo", ((trait, "", "", ""),)))
                moved = len(got ^ bare)
                if moved < worst[0]:
                    worst = (moved, f"{form} + {trait}")
                if moved < SHOWS:
                    faint.append(f"{form}+{trait}={moved}")
        assert not faint, f"traits drawn and invisible: {faint}"
        return (f"{len(life3d.VISIBLE_TRAITS)} visible traits across "
                f"{len(FORMS)} plans · faintest {worst[1]} at {worst[0]} px")

    @check("an organism out of the generator arrives with a body")
    def _():
        # Through the real generator, so nothing depends on a table somebody
        # has to remember to update when a body plan is added.
        from ..core.state import new_game
        from ..world.planets import _make_lifeform

        game = new_game("xeno")
        made = [_make_lifeform(game.rng(f"life-{i}"), "verdant")
                for i in range(60)]
        plans, liveries, marks = set(), set(), set()
        for life in made:
            shape = life3d.for_lifeform(life)
            assert shape.mesh[1], life.name
            plans.add(shape.plan)
            liveries.add(life.metabolism)
            marks |= set(shape.marks)
            # `marks` is what the picture shows, so it never claims a trait
            # the organism does not have.
            assert set(shape.marks) <= {t[0] for t in life.traits}
        assert len(plans) >= 4, plans
        assert len(liveries) >= 5, liveries
        return (f"{len(made)} organisms: {len(plans)} silhouettes, "
                f"{len(liveries)} biochemistries, {len(marks)} visible traits")

    @check("the catalogue shows them")
    def _():
        keep = _app()
        assert keep is not None
        from ..core.state import new_game
        from ..ui.life_panel import build as life_catalogue
        from ..ui.thumb3d import Thumb

        game = new_game("life-cards")
        # Catalogue everything the sector holds, so the panel has rows.
        drawn = 0
        for system in game.galaxy.systems[:6]:
            for body in system.bodies:
                for life in getattr(body, "lifeforms", []) or []:
                    life.catalogued = True
                    drawn += 1
        panel = life_catalogue(game)
        thumbs = [t for t in panel.findChildren(Thumb) if t.kind == "life"]
        panel.deleteLater()
        assert drawn, "no life in the first six systems to catalogue"
        assert thumbs, f"{drawn} organisms catalogued and no portrait drawn"
        return f"{drawn} catalogued, {len(thumbs)} portraits on the panel"
