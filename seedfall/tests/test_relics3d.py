"""Twelve artefacts, four makers, and whether you can tell them apart.

The last catalogue in the game that was words only. Measured before
`data/relics3d.py` existed: the codex had ten tabs — fleet classes, colony
classes, machines, fittings, the sky, powers, life, field notes, glossary,
about — and not one of them was this. A captain could carry a Pressure Song
for a whole chronicle and never see it.

The claim a picture makes here is narrower than a hull's and wider than a
fitting's, and it is stated so the shapes are not asked to do more than they
can:

- **Which culture left it** — the silhouette *and* the colour. The strong
  claim, and the one these checks pin.
- **How much there is to learn** — `study` runs 120 to 340 and that is bulk.
- **Whether it does anything to a ship** — eight of twelve carry a `bonus` and
  get a lit core; the other four teach a technology and read as inert.

Not "which of the three Abyssal relics is this". Three artefacts of one dead
culture cannot be three pictures without inventing a distinction the cards do
not make — the honesty `parts3d` settled on for eighteen armour plates.

The wrong turn is worth keeping. The four languages first measured at a **66%
worst pair** (ossuary against tessellate). Widening the tessellate stack to
separate it pulled abyssal-vs-tessellate from 52% down to 43% — and pushed
weft-vs-tessellate from 62% *up* to 70%, so the worst pair got worse. Four
shapes sharing one bounding frame trade against each other, and the number
that matters is the worst pair, not the pair being worked on.
"""

from __future__ import annotations

import itertools

from ..data import relics3d
from ..data.xenotech import CULTURES, XENOTECH
from .harness import Suite

SIZE = 160

#: How alike two makers' outlines may be before the picture stops claiming
#: anything. Tighter than `parts3d`'s 0.72, because that separates seven slots
#: while this separates four cultures built deliberately unlike each other.
ALIKE = 0.70

_APP = []


def _app():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PyQt6.QtWidgets import QApplication
    if not _APP:
        _APP.append(QApplication.instance() or QApplication([]))
    return _APP[0]


def _shot(relic):
    """(lit pixels, the shades among them) for one relic's portrait."""
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
    thumb3d.paint(painter, camera, "relic", relic)
    painter.end()
    lit = {(x, y) for y in range(SIZE) for x in range(SIZE)
           if image.pixel(x, y) != sky.rgb()}
    return lit, {image.pixel(x, y) for x, y in lit}


def _shot_mesh(mesh):
    """(lit pixels, shades) for a bare mesh, with no relic behind it.

    The maker's *language* alone — `relics3d.BY_CULTURE` is built at a
    standard bulk with no bonus mark, which is exactly what a check comparing
    the four ways of building wants. Going through a relic instead would let a
    depth of study or a gold node answer for the shape.
    """
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
    render3d.draw(painter, camera, mesh, (0.0, 0.0, thumb3d.ROBOT_AT), 1.0,
                  thumb3d.LIGHT, spin=thumb3d.RELIC_SPIN,
                  tilt=thumb3d.RELIC_TILT)
    painter.end()
    lit = {(x, y) for y in range(SIZE) for x in range(SIZE)
           if image.pixel(x, y) != sky.rgb()}
    return lit, {image.pixel(x, y) for x, y in lit}


def _one_each():
    """One relic per culture, the shallowest, so bulk is not doing the work."""
    out = {}
    for relic in sorted(XENOTECH, key=lambda r: r.study):
        out.setdefault(relic.culture, relic)
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("every relic in the game has a picture")
    def _():
        missing = [r.id for r in XENOTECH if relics3d.mesh_for(r) is None]
        assert not missing, f"no picture for {missing}"
        # And every one of them draws something rather than an empty frame.
        thin = []
        for relic in XENOTECH:
            lit, _shades = _shot(relic)
            if len(lit) < 200:
                thin.append((relic.id, len(lit)))
        assert not thin, f"drawn and all but invisible: {thin}"
        assert relics3d.mesh_for("not_a_relic") is None
        assert relics3d.is_relic(XENOTECH[0]) and not relics3d.is_relic("nope")
        return (f"{len(XENOTECH)} relics across {len(CULTURES)} makers, every "
                "one drawn")

    @check("the four makers are told apart by outline")
    def _():
        shots = {c: _shot_mesh(m)[0]
                 for c, m in relics3d.BY_CULTURE.items()}
        worst, pair = 0.0, None
        for a, b in itertools.combinations(sorted(shots), 2):
            share = (len(shots[a] & shots[b])
                     / max(1, len(shots[a] | shots[b])))
            if share > worst:
                worst, pair = share, (a, b)
        assert worst < ALIKE, (
            f"{pair} share {worst:.0%} of their outline against a "
            f"{ALIKE:.0%} bar — the picture is not claiming a maker")
        return (f"worst pair {pair[0]} / {pair[1]} at {worst:.0%}, "
                f"against a {ALIKE:.0%} bar")

    @check("and by colour, which is the other half of the claim")
    def _():
        # A silhouette check alone would pass on four grey shapes. Whose hands
        # made it is carried by the palette as much as the form.
        # The languages alone: a bonus mark is *meant* to be the same gold on
        # every maker, so comparing finished relics would report the makers
        # wearing each other's paint when they are only sharing one node.
        shades = {c: _shot_mesh(m)[1]
                  for c, m in relics3d.BY_CULTURE.items()}
        for a, b in itertools.combinations(sorted(shades), 2):
            both = shades[a] & shades[b]
            assert len(both) <= 4, (
                f"{a} and {b} share {len(both)} shades — the makers are "
                "wearing each other's paint")
        return " · ".join(f"{c} {len(v)} shades" for c, v in sorted(shades.items()))

    @check("how much there is to learn is how big it draws")
    def _():
        # Within one maker, so the language is held still and only the study
        # cost moves. Otherwise a form's own bulk would answer for it.
        said = []
        for culture in sorted({r.culture for r in XENOTECH}):
            theirs = sorted((r for r in XENOTECH if r.culture == culture),
                            key=lambda r: r.study)
            if len(theirs) < 2:
                continue
            shallow, deep = theirs[0], theirs[-1]
            small = len(_shot(shallow)[0])
            large = len(_shot(deep)[0])
            assert large > small, (
                f"{deep.id} at {deep.study} study draws {large} pixels "
                f"against {small} for {shallow.id} at {shallow.study} — "
                "depth of study is not reaching the picture")
            said.append(f"{culture} {small}→{large} px")
            assert relics3d.bulk_of(deep) > relics3d.bulk_of(shallow)
        return " · ".join(said)

    @check("a relic that fits a ship is marked; one that teaches is not")
    def _():
        fits = [r for r in XENOTECH if r.bonus]
        teaches = [r for r in XENOTECH if not r.bonus]
        assert fits and teaches, (
            "every relic is the same sort, so the mark claims nothing")
        for relic in fits:
            assert "live" in relics3d.marks_of(relic), relic.id
        for relic in teaches:
            assert not relics3d.marks_of(relic), relic.id
        # And the mark is *drawn and visible*, on every maker — not merely
        # recorded. The first version probed a single relic and passed with
        # the mark buried at the centre of the form, because that one maker's
        # prism stack leaks light between its tiers. One shape's gaps are not
        # evidence about the other three.
        said = []
        for culture in sorted({r.culture for r in XENOTECH}):
            theirs = [r for r in fits if r.culture == culture]
            assert theirs, f"no {culture} relic carries a bonus to mark"
            probe = min(theirs, key=lambda r: r.study)
            bare = type(probe)(**{**vars(probe), "bonus": {}})
            gained = _shot(probe)[0] - _shot(bare)[0]
            assert len(gained) > 40, (
                f"{probe.id} gains {len(gained)} pixels from its bonus — a "
                "difference that is drawn and cannot be seen is not a "
                "difference")
            said.append(f"{culture} +{len(gained)}px")
        return (f"{len(fits)} carry a bonus and light up, {len(teaches)} "
                f"teach a technology and stay dark · {' · '.join(said)}")

    @check("the codex has a page for them")
    def _():
        # The gap this closes: ten tabs and none of them was this one.
        _app()
        from ..core.state import new_game
        from ..ui import codex_view
        from ..ui.app import MainWindow

        window = MainWindow(new_game("relic-codex"))
        view = codex_view.CodexView(window)
        view.tab = "relics"
        view.build()
        assert view.col.count() > len(CULTURES), (
            "the relics tab built almost nothing")
        return f"a page grouped by maker, {len(XENOTECH)} cards"
