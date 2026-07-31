"""Eighty-four fittings, and the three things a picture of one has to say.

The last page in the catalogue that was words only: the shipyard listed every
part as a name, a tonnage and a sentence.

**The claim here is deliberately narrower than for a hull or an organism**, and
the checks are written to that claim rather than to an aspiration. A fitting is
a component; at a glance a captain needs to know what kind of thing it is, whose
yard built it, and roughly how much hull it will eat. Not *which* of the
eighteen defensive plates this is — eighteen plates cannot be eighteen pictures,
and asserting they were would be the same lie as five silhouettes across
thirty-five hull classes, pointing the other way: a distinction drawn where
none exists.

The claims:

- **A slot is a silhouette.** A railgun does not look like a radiator.
- **A yard is a colour**, so a grown organ does not look like a Yards weld.
- **Tonnage is bulk**, measured between the lightest and heaviest of a slot.
- **What it does shows**: something that fires has a barrel, something with an
  ability has an emitter.
- **Every part has a picture**, and the catalogue shows them.
"""

from __future__ import annotations

from ..data import parts3d
from ..data.part_types import SLOT_ORDER
from ..data.parts import PARTS
from .harness import Suite

SIZE = 150

#: What two *slots* may share. These are simple components on a black card;
#: the honest worst as shipped is a power cell against a utility can, both of
#: which are a drum with things on it.
ALIKE = 0.72


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    assert app is not None
    return app


def _shot(part):
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
    thumb3d.paint(painter, camera, "part", part)
    painter.end()
    lit = [(x, y) for y in range(SIZE) for x in range(SIZE)
           if image.pixel(x, y) != sky.rgb()]
    return set(lit), {image.pixel(x, y) for x, y in lit}


class _Probe:
    """A part that is only the fields the picture reads."""

    def __init__(self, slot, family="any", mass=20.0, wpn=None, ability=None,
                 civilian=False):
        self.id = f"probe-{slot}-{family}-{mass}"
        self.slot, self.family, self.mass = slot, family, mass
        self.wpn, self.ability, self.civilian = wpn, ability, civilian


def run(suite: Suite) -> None:
    check = suite.check

    @check("a slot is a silhouette")
    def _():
        drawn = [slot for slot in SLOT_ORDER if slot in parts3d.SHAPES]
        assert len(drawn) == len(SLOT_ORDER), (
            f"slots the shipyard offers and nothing draws: "
            f"{set(SLOT_ORDER) - set(parts3d.SHAPES)}")
        masks = {}
        for slot in drawn:
            mask, _tints = _shot(_Probe(slot))
            assert len(mask) > 250, f"{slot} covers only {len(mask)} pixels"
            masks[slot] = mask
        worst, pair = 0.0, None
        for i, one in enumerate(drawn):
            for other in drawn[i + 1:]:
                a, b = masks[one], masks[other]
                share = len(a & b) / len(a | b)
                if share > worst:
                    worst, pair = share, (one, other)
        assert worst < ALIKE, f"{pair} share {worst:.0%} of their outline"
        return (f"{len(drawn)} slots, worst pair {pair[0]}/{pair[1]} at "
                f"{worst:.0%}")

    @check("a yard is a colour")
    def _():
        seen = {}
        for family in parts3d.YARD:
            _mask, tints = _shot(_Probe("utility", family=family))
            seen[family] = tints
        names = sorted(seen)
        for i, one in enumerate(names):
            for other in names[i + 1:]:
                shared = (len(seen[one] & seen[other])
                          / len(seen[one] | seen[other]))
                assert shared < 0.5, (
                    f"{one} and {other} are painted {shared:.0%} the same")
        return f"{len(names)} yards, every one its own colour on the same can"

    @check("tonnage is bulk, and it is the part's own tonnage")
    def _():
        # Between the lightest and the heaviest fitting the game ships, on the
        # same slot, the picture has to change size.
        light = min(PARTS, key=lambda p: p.mass)
        heavy = max(PARTS, key=lambda p: p.mass)
        assert parts3d.bulk_of(heavy) > parts3d.bulk_of(light) * 1.4, (
            parts3d.bulk_of(light), parts3d.bulk_of(heavy))
        small, _t = _shot(_Probe("drive", mass=light.mass))
        big, _t = _shot(_Probe("drive", mass=heavy.mass))
        assert len(big) > len(small) * 1.5, (
            f"a {light.mass:g} t fitting covers {len(small)} px and a "
            f"{heavy.mass:g} t one {len(big)} — the tonnage is not read")
        return (f"{light.name} at {light.mass:g} t covers {len(small)} px, "
                f"{heavy.name} at {heavy.mass:g} t covers {len(big)}")

    @check("what a fitting does shows on it")
    def _():
        bare, _t = _shot(_Probe("weapon"))
        armed, _t = _shot(_Probe("weapon", wpn=object()))
        assert len(armed ^ bare) > 80, (
            f"a barrel changes {len(armed ^ bare)} pixels")
        plain, _t = _shot(_Probe("utility"))
        able, _t = _shot(_Probe("utility", ability=object()))
        assert len(able ^ plain) > 80, (
            f"an emitter changes {len(able ^ plain)} pixels")
        # And the marks a fitting carries are the fields it declares.
        for part in PARTS:
            marks = set(parts3d.build(part).marks)
            assert ("barrel" in marks) == (part.wpn is not None), part.id
            assert ("emitter" in marks) == (part.ability is not None), part.id
        armed_now = [p for p in PARTS if p.wpn is not None]
        return (f"{len(armed_now)} armed fittings carry a barrel and nothing "
                "else does")

    @check("every fitting has a picture, and the catalogue shows them")
    def _():
        for part in PARTS:
            fitting = parts3d.FITTINGS.get(part.id)
            assert fitting is not None, part.id
            assert fitting.mesh[0] and fitting.mesh[1], part.id
        keep = _app()
        assert keep is not None
        from ..core.state import new_game
        from ..ui.thumb3d import Thumb
        from ..ui.window import MainWindow

        window = MainWindow(new_game("fittings"))
        window.toast = lambda *a, **k: None
        window.go("codex")
        view = window.views["codex"]
        view.tab = "fittings"
        view.refresh()
        shown = [t for t in view.findChildren(Thumb) if t.kind == "part"]
        window.close()
        assert len(shown) == len(PARTS), (
            f"{len(shown)} portraits on {len(PARTS)} fittings")
        return f"{len(PARTS)} fittings built and drawn on the codex"
