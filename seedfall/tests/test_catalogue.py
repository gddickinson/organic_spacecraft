"""The catalogue screen, and whether it shows the catalogue.

The Codex's "Fleet classes" tab listed **thirty-five hull classes** — name,
binomial, tier, blurb, role, crew, mass, hull, hold, jump, build time — and not
one picture. Nor did the nineteen colony and station classes. Meanwhile the sky
had been drawing five hull silhouettes, four berths, nine classes of star and
seven kinds of world for cycles, and none of it appeared on the one page whose
whole job is to show you what is out there.

And five silhouettes across thirty-five classes would not have been much of a
catalogue either, so a class's *proportions* now come from its own entry: hold
against mass gives beam, jump range gives length. Both are printed in words on
the same card, so the portrait and the specification cannot disagree.

The claims:

- **The catalogue screen renders.** Cards carry pictures, not just text.
- **Thirty-five classes are thirty-five pictures**, and a hauler is fatter than
  a courier because the numbers say so.
- **The sky tab holds everything the sky draws** — no kind of world, class of
  star, errand of traffic or sort of berth quietly missing.
- **A star's glow stays on its own card**, so nine classes do not appear to sit
  on nine differently-coloured backgrounds.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data import hulls3d
from ..data.berths3d import BERTHS
from ..data.chassis import CHASSIS, CHASSIS_BY_ID
from ..data.starclasses import STAR_CLASSES
from ..sim.traffic import ERRANDS
from ..data.worlds3d import WORLD_PAINTS
from .harness import Suite

TILE = (150, 96)


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _portrait(kind: str, subject):
    """One catalogue portrait, drawn the way the card draws it."""
    from PyQt6.QtGui import QColor, QImage, QPainter
    from ..ui import render3d, thumb3d

    keep = _app()
    assert keep is not None
    image = QImage(TILE[0], TILE[1], QImage.Format.Format_RGB32)
    image.fill(QColor(thumb3d.VOID))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    camera = render3d.Camera(at=(0.0, 0.0, 0.0), forward=(0.0, 0.0, 1.0),
                             up=(0.0, 1.0, 0.0), width=TILE[0], height=TILE[1],
                             half_fov=thumb3d.HALF_FOV)
    thumb3d.paint(painter, camera, kind, subject)
    painter.end()
    return image


def _drawn(image) -> set:
    from PyQt6.QtGui import QColor
    from ..ui import thumb3d
    void = QColor(thumb3d.VOID).rgb()
    return {(x, y) for y in range(image.height()) for x in range(image.width())
            if image.pixel(x, y) != void}


def _overlap(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def run(suite: Suite) -> None:
    check = suite.check

    @check("the catalogue screen actually shows the catalogue")
    def _():
        # The defect: a page of specifications with nothing drawn on it.
        keep = _app()
        assert keep is not None
        from ..ui.thumb3d import Thumb
        from ..ui.window import MainWindow

        game = new_game("codex")
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("codex")
        view = win.views["codex"]
        counts = {}
        for tab in ("classes", "sky"):
            view.tab = tab
            view.refresh()
            counts[tab] = len(view.findChildren(Thumb))
        win.close()
        assert counts["classes"] >= len(CHASSIS), (
            f"the fleet tab lists {len(CHASSIS)} classes and draws "
            f"{counts['classes']} of them")
        assert counts["sky"] >= (len(WORLD_PAINTS) + len(STAR_CLASSES)
                                 + len(BERTHS) + len(ERRANDS)), counts
        return (f"{counts['classes']} hull portraits on the fleet tab, "
                f"{counts['sky']} on the sky tab")

    @check("thirty-five classes are thirty-five pictures")
    def _():
        builds = {(c.family, round(hulls3d.proportions(c).beam, 3),
                   round(hulls3d.proportions(c).length, 3)) for c in CHASSIS}
        assert len(builds) == len(CHASSIS), (
            f"{len(CHASSIS)} classes collapse to {len(builds)} builds")
        # And it shows: the fattest and the leanest of one family, rendered.
        grown = [c for c in CHASSIS if c.family == "grown"]
        fat = max(grown, key=lambda c: hulls3d.proportions(c).beam)
        lean = min(grown, key=lambda c: hulls3d.proportions(c).beam)
        share = _overlap(_drawn(_portrait("hull", fat)),
                         _drawn(_portrait("hull", lean)))
        assert share < 0.80, (
            f"{fat.name} and {lean.name} are the widest and narrowest grown "
            f"hulls and share {share:.0%} of their portrait")
        return (f"{len(builds)} distinct builds; {fat.name} against "
                f"{lean.name} shares {share:.0%} of its portrait")

    @check("a class's build comes from its own entry")
    def _():
        # Hold against mass gives beam, jump gives length — both printed on the
        # same card in words, so the picture cannot contradict the figures.
        pairs = [(c, hulls3d.proportions(c)) for c in CHASSIS]
        by_hold = sorted(pairs, key=lambda row: row[0].cargo
                         / max(1.0, row[0].mass_t))
        assert by_hold[0][1].beam < by_hold[-1][1].beam, (
            "the emptiest hull in the game is not the narrowest")
        by_jump = sorted(pairs, key=lambda row: row[0].jump)
        assert by_jump[0][1].length < by_jump[-1][1].length, (
            "the shortest-legged hull is not the shortest")
        # Bounded, so a freak entry cannot produce a hull the card cannot hold
        # — **against written figures, never against `CLASS_SPREAD` itself.**
        # The first version of these two lines asserted
        # `1 - CLASS_SPREAD <= beam <= 1 + CLASS_SPREAD`, which moves with the
        # constant it claims to bound and passed happily with the spread set to
        # nine. Measured as shipped: the widest hull sits at 1.42 beams and the
        # longest at 1.37, so nothing may pass 1.5 either way.
        for entry, build in pairs:
            assert 0.5 <= build.beam <= 1.5, (entry.id, build.beam)
            assert 0.5 <= build.length <= 1.5, (entry.id, build.length)
        widest = max(pairs, key=lambda row: row[1].beam)
        longest = max(pairs, key=lambda row: row[1].length)
        return (f"widest {widest[0].name} at {widest[1].beam:.2f} beams, "
                f"longest {longest[0].name} at {longest[1].length:.2f}")

    @check("the sky tab holds everything the sky draws")
    def _():
        from ..ui import codex_view
        # Every kind the renderers know must be on the page, and every entry on
        # the page must be a kind they know — a catalogue with a gap either way
        # is a catalogue nobody can trust.
        for kind in WORLD_PAINTS:
            assert kind in codex_view.WORLD_BLURB, f"no line for a {kind} world"
        for key in BERTHS:
            assert key in codex_view.BERTH_NAME, f"no name for a {key} berth"
            assert key in codex_view.BERTH_BLURB, f"no line for a {key} berth"
        stray = [k for k in codex_view.WORLD_BLURB if k not in WORLD_PAINTS]
        assert not stray, f"the codex describes worlds nobody draws: {stray}"
        # And each one actually paints something.
        for kind in WORLD_PAINTS:
            assert len(_drawn(_portrait("world", kind))) > 300, kind
        for key in STAR_CLASSES:
            assert len(_drawn(_portrait("star", key))) > 200, key
        for key in BERTHS:
            assert len(_drawn(_portrait("berth", key))) > 120, key
        # The traffic too. Five errands the sky has drawn since `ships3d` was
        # written, and the one page whose job is to show you what is out there
        # had none of them — so a captain could not learn what an unmarked
        # hull looks like except by meeting one.
        for errand in ERRANDS:
            assert len(_drawn(_portrait("ship", errand))) > 120, errand
        return (f"{len(WORLD_PAINTS)} worlds, {len(STAR_CLASSES)} stars, "
                f"{len(ERRANDS)} errands and {len(BERTHS)} berths, every one "
                "named and drawn")

    @check("a star's glow stays on its own card")
    def _():
        # Uncapped the corona runs to eleven disc radii, so on a tile this size
        # every class sat on a differently-tinted background and the page read
        # as a layout fault rather than as light.
        worst, who = 0, None
        for key in STAR_CLASSES:
            image = _portrait("star", key)
            for x, y in ((1, 1), (TILE[0] - 2, 1), (1, TILE[1] - 2),
                         (TILE[0] - 2, TILE[1] - 2)):
                rgb = image.pixel(x, y)
                lit = (rgb >> 16 & 0xFF) + (rgb >> 8 & 0xFF) + (rgb & 0xFF)
                if lit > worst:
                    worst, who = lit, key
        # The void itself is #05070a, which sums to 22.
        assert worst < 45, (
            f"a {who} tints its own corner to {worst} — its corona is running "
            "off the card")
        return f"the brightest corner on any of the nine is {who} at {worst}"
