"""What the picture of the ship shows, and whether it shows the ship.

A ship at 25% hull rendered pixel-for-pixel identically to one fresh out of
the yard. Every reading of the damage was a percentage in a side panel, while
the picture — the one thing always on the screen — said nothing at all.

And the shading was a single lambert term, so a grown membrane and a
fabricated plate were the same substance in two colours, and the silhouette
had nothing to sit against but flat black.

The claims:

- **Damage is on the hull**, in patches, and the patches spread as she is hurt.
- **It reaches the screen** — measured in pixels, not in fields.
- **The patches are stable**, and drawing never touches the chronicle's dice.
- **Materials look different**, because gloss varies by what a thing is made of.
- **Every hull family draws.**
"""

from __future__ import annotations

from ..core import solid as solid_mod
from ..core.state import new_game
from ..data.chassis import CHASSIS
from ..sim import plans
from .harness import Suite


def _hurt(seed: str, fraction: float):
    """A game whose outermost layer is worn down to `fraction`."""
    game = new_game(seed)
    layer = game.ship.layers[0]
    layer.hp = layer.max * fraction
    return game


def _scarred(model) -> tuple[int, int]:
    """(hurt faces, total faces) on the hull solid."""
    hull = model["solids"][0]
    return sum(1 for f in hull.faces if f.hurt > 0), len(hull.faces)


def _shot(game, size: int = 300):
    """Render the ship plan offscreen and hand back the image."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    from ..ui.plans_panel import ShipPlan

    app = QApplication.instance() or QApplication([])
    assert app is not None
    widget = ShipPlan(plans.build(game), height=size)
    widget.resize(size, size)
    widget.view.spin, widget.view.tilt = 0.7, 0.32
    image = widget.grab().toImage()
    widget.deleteLater()
    return image


def _differs(a, b) -> int:
    """How many pixels two renders disagree on."""
    return sum(1 for y in range(a.height()) for x in range(a.width())
               if a.pixel(x, y) != b.pixel(x, y))


def run(suite: Suite) -> None:
    check = suite.check

    @check("a sound hull is unmarked and a hurt one is not")
    def _():
        sound, total = _scarred(plans.build(_hurt("mark", 1.0)))
        assert total > 100, f"only {total} faces on the hull"
        assert sound == 0, (
            f"{sound} faces of a hull straight out of the yard are already "
            "dying")
        hurt, _t = _scarred(plans.build(_hurt("mark", 0.5)))
        assert hurt > 0, (
            "a hull at half strength shows no damage at all — the picture "
            "and the percentage disagree")
        return f"{total} faces: none marked when sound, {hurt} at half"

    @check("the worse she is, the more of her is dying")
    def _():
        # Against numbers written here rather than against the slope that
        # produces them, so re-tuning the slope has to be re-measured.
        counts = {}
        for fraction in (1.0, 0.75, 0.5, 0.25):
            marked, total = _scarred(plans.build(_hurt("spread", fraction)))
            counts[fraction] = marked / total
        order = [counts[f] for f in (1.0, 0.75, 0.5, 0.25)]
        assert all(a <= b for a, b in zip(order, order[1:])), (
            f"damage does not grow as she is hurt: {counts}")
        assert counts[0.25] > 0.5, (
            f"a hull at a quarter shows {counts[0.25]:.0%} of itself dying — "
            "that is not a wreck, that is a blemish")
        assert counts[0.75] < 0.45, (
            f"a hull at three quarters is already {counts[0.75]:.0%} dead")
        return " · ".join(f"{f:.0%} hull → {counts[f]:.0%} marked"
                          for f in (1.0, 0.75, 0.5, 0.25))

    @check("the damage reaches the screen, measured in pixels")
    def _():
        # The point of the whole thing. Fields on a dataclass prove nothing;
        # two renders that differ prove the captain can see it.
        clean = _shot(_hurt("pix", 1.0))
        broken = _shot(_hurt("pix", 0.35))
        moved = _differs(clean, broken)
        total = clean.width() * clean.height()
        assert moved > total * 0.02, (
            f"a hull at 35% draws {moved} pixels differently from a sound "
            f"one out of {total} — the damage is invisible")
        # And the same ship twice is the same picture: no drift, no dice.
        again = _shot(_hurt("pix", 0.35))
        assert _differs(broken, again) == 0, (
            "the same ship drawn twice came out different")
        return f"{moved} of {total} pixels change between sound and hurt"

    @check("drawing the ship never touches the chronicle's dice")
    def _():
        # `speckle` exists precisely so the model can scatter without an RNG.
        # Drawing happens many times a second; if it advanced the save, two
        # captains who looked at their ship a different number of times would
        # get different chronicles.
        game = _hurt("dice", 0.4)
        before = game.rng().next()
        game = _hurt("dice", 0.4)
        for _ in range(5):
            plans.build(game)
        after = game.rng().next()
        assert before == after, (
            "building the model advanced the chronicle's random state")
        return "five builds, the dice untouched"

    @check("the patches are patches, not a checkerboard")
    def _():
        # Hashing each face on its own made every quad flip independently,
        # which reads as a broken texture rather than as a wound.
        #
        # Measured as *neighbour agreement*: how often two touching faces are
        # in the same state. My first attempt asked whether a marked face had
        # a marked neighbour, which with half the hull marked is true by
        # chance — per-face scattering scored 99% on it and the check could
        # not tell the two apart at all.
        model = plans.build(_hurt("patch", 0.5))
        hull = model["solids"][0]
        centres = [solid_mod.centre_of(f.points) for f in hull.faces]
        marked = [f.hurt > 0 for f in hull.faces]
        assert 0.2 < sum(marked) / len(marked) < 0.8, (
            "the hull is nearly all one state, so agreement means nothing")

        gaps = sorted(min(solid_mod.length(solid_mod.sub(a, b))
                          for j, b in enumerate(centres) if i != j)
                      for i, a in enumerate(centres))
        near = gaps[len(gaps) // 2] * 1.6
        pairs = [(i, j) for i in range(len(centres))
                 for j in range(i + 1, len(centres))
                 if solid_mod.length(
                     solid_mod.sub(centres[i], centres[j])) < near]
        assert len(pairs) > 200, len(pairs)
        agree = sum(1 for i, j in pairs if marked[i] == marked[j]) / len(pairs)

        # What agreement would be if each face flipped on its own — the exact
        # thing this check exists to rule out.
        share = sum(marked) / len(marked)
        chance = share ** 2 + (1 - share) ** 2
        assert agree > chance + 0.18, (
            f"touching faces agree {agree:.0%} of the time against {chance:.0%} "
            "by chance — the damage is a checkerboard, not wounds")
        return (f"touching faces agree {agree:.0%} of the time, against "
                f"{chance:.0%} for a hull speckled face by face")

    @check("what a thing is made of changes how it takes the light")
    def _():
        from ..ui.plans_panel import GLOSS
        from ..data.hullforms import LIVING, SYSTEM

        assert GLOSS[SYSTEM] > GLOSS[LIVING] * 2, (
            f"a fabricated plate is {GLOSS[SYSTEM]} glossy against a grown "
            f"membrane's {GLOSS[LIVING]} — they will look like the same stuff")

        # And the projector actually hands over the terms to use.
        faces = solid_mod.ellipsoid(1, 1.6, 1, LIVING)
        painted = solid_mod.project(faces, solid_mod.View())
        assert painted, "nothing survived the cull"
        for face in painted:
            assert 0.0 <= face.rim <= 1.0, face.rim
            assert 0.0 <= face.spec <= 1.0, face.spec
            assert 0.0 <= face.far <= 1.0, face.far
        assert max(f.rim for f in painted) > 0.4, (
            "no face is edge-on to the eye, so the silhouette gets no rim "
            "light and the hull has nothing to sit against")
        assert max(f.far for f in painted) - min(f.far for f in painted) > 0.9, (
            "every face is at the same depth — the distance fade does nothing")
        return (f"gloss: grown {GLOSS[LIVING]} · fabricated {GLOSS[SYSTEM]}; "
                f"rim to {max(f.rim for f in painted):.2f}")

    @check("the caption names the skin when the skin is what you can see")
    def _():
        # The blight follows the outermost layer, because that is what damage
        # lands on first and what you would actually see. Beside a bare
        # "hull 93%" a visibly rotten ship read as a rendering fault.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = _hurt("caption", 0.45)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("ship")
        for _ in range(3):
            app.processEvents()
        view = win.views["ship"]
        for button in view.findChildren(QPushButton):
            if button.text().strip() == "Plans":
                button.click()
                break
        for _ in range(3):
            app.processEvents()
        caption = next((lab.text() for lab in view.findChildren(QLabel)
                        if "fittings" in lab.text()), "")
        win.close()
        assert caption, "no legend under the model"
        skin = plans.layer_health(game.ship)[0]
        assert skin[0].lower() in caption.lower(), (
            f"the model shows {skin[0]} at {skin[1]:.0%} and the caption "
            f"only says {caption!r}")

        # And a sound ship does not get the extra clause for nothing.
        sound = MainWindow(new_game("caption"))
        sound.toast = lambda *a, **k: None
        sound.go("ship")
        for _ in range(3):
            app.processEvents()
        for button in sound.views["ship"].findChildren(QPushButton):
            if button.text().strip() == "Plans":
                button.click()
                break
        for _ in range(3):
            app.processEvents()
        clean = next((lab.text() for lab in sound.views["ship"].findChildren(QLabel)
                      if "fittings" in lab.text()), "")
        sound.close()
        assert skin[0].lower() not in clean.lower(), (
            f"an undamaged ship names its skin anyway: {clean!r}")
        return caption

    @check("every hull family draws")
    def _():
        drawn = []
        for chassis in CHASSIS:
            game = new_game("families")
            game.ship.chassis = chassis.id
            game.recompute()
            model = plans.build(game)
            assert model["faces"] > 50, (
                f"{chassis.id} draws {model['faces']} faces")
            image = _shot(game, size=200)
            lit = sum(1 for y in range(0, image.height(), 4)
                      for x in range(0, image.width(), 4)
                      if image.pixel(x, y) != image.pixel(0, 0))
            assert lit > 60, (
                f"{chassis.id} renders an almost empty frame ({lit} pixels "
                "differ from the corner)")
            drawn.append(f"{chassis.id} {model['faces']}f")
        return " · ".join(drawn)
