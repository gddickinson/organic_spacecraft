"""What the chart shows about a star nobody of yours has looked at.

The sector chart has a careful knowledge system. `intel.level` ranks a system
0 to 3 — catalogued, named, visited, charted — the marker is an outline, a
disc or a ring accordingly, and the port ring is drawn only `if sys.port and
known`.

The Bloom was exempt from all of it. A red halo sized by `system.bloom` was
painted on every star in the sector however unknown, and the side panel
printed

    Bloom mass: 77% of this system converted.
    Knowledge: name only

one line above the other. So the one thing the whole game is about was the one
thing the fog did not cover — and it quietly undid the picket, whose `watch`
effect exists to tell you what is happening where you are not.

`intel.sees_bloom` is the single door: you have been there, you can see it
from where you stand, something of yours watches it, or you hold a colony in
it. A registry entry is not eyes — rank 1 can come from a catalogue as much as
from a sensor, and a catalogue does not know what has grown since.

The captain is not blinded, only made to scout: the Holdings screen still
reports the sector total — how many systems carry growth and what share of the
mass — because that is the sort of figure the Charter publishes. **How bad**
is public; **where** is earned.

The claims:

- **No unwatched system's Bloom reaches the screen.** The general one, asked
  of the rendered panel rather than of the code.
- **A picket buys the reading**, which is what `watch` is for.
- **The sector total is still told**, so scouting is a cost and not a wall.
- **Whose space it is waits for a registry entry too.**
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import intel
from ..sim.colony import Colony
from .harness import Suite


def _picket(game, system, uid: int = 1) -> Colony:
    colony = Colony(id=uid, class_id="vesper_picket", name="Eye",
                    system_id=system.id, body_id=system.bodies[0].id,
                    need=0, online=True, pop=0)
    game.colonies.append(colony)
    return colony


def _panel_text(game, system) -> str:
    """The chart's side panel for one system, as a player would read it."""
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication, QLabel
    from ..ui.window import MainWindow

    app = QApplication.instance() or QApplication([])
    assert app is not None
    win = MainWindow(game)
    win.toast = lambda *a, **k: None
    win.go("map")
    view = win.views["map"]
    view.selected = system.id
    view.refresh()
    for _ in range(3):
        app.processEvents()
    text = " ".join(lab.text() for lab in view.findChildren(QLabel)
                    if lab.text())
    win.close()
    return text


def run(suite: Suite) -> None:
    check = suite.check

    @check("no unwatched system's Bloom reaches the screen")
    def _():
        # The general one, and asked of what is drawn rather than of the
        # source: infest a spread of stars nobody has been to, then read the
        # panel for each and look for the figure.
        leaked, checked = [], 0
        for seed in range(6):
            game = new_game(f"fog{seed}")
            unseen = [s for s in game.galaxy.systems
                      if not intel.sees_bloom(game, s)][:4]
            assert unseen, "every star is already watched in this sector"
            for share in (0.35, 0.77):
                for system in unseen:
                    system.bloom = share
                    figure = f"{round(share * 100)}%"
                    text = _panel_text(game, system)
                    checked += 1
                    if figure in text and "Bloom mass" in text:
                        leaked.append(f"{system.name}: {figure} shown with "
                                      "nothing of yours watching")
                    system.bloom = 0.0
        assert not leaked, (
            f"{len(leaked)} unwatched system(s) showing their infestation: "
            f"{leaked[:3]}")
        assert checked >= 24, checked
        return (f"{checked} readings of unwatched stars, none of them naming "
                "what has grown there")

    @check("the halo is painted only where it can be seen")
    def _():
        # The panel is words and the halo is pixels, so reading labels cannot
        # see it: the first draft of this suite missed a mutation that put
        # the glow back on every star. This grabs the chart and looks.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui.map_view import StarChart
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None

        def redness(with_picket: bool, bloom: float) -> int:
            game = new_game("halo")
            target = next(s for s in game.galaxy.systems
                          if not intel.sees_bloom(game, s))
            target.bloom = bloom
            if with_picket:
                _picket(game, target)
            game.recompute()
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.resize(1200, 900)
            win.show()
            win.go("map")
            chart = win.views["map"].findChild(StarChart)
            assert chart is not None, "no star chart on the map screen"
            for _ in range(3):
                app.processEvents()
            image = chart.grab().toImage()
            at = chart._to_screen(target)
            hot = 0
            for dx in range(-14, 15):
                for dy in range(-14, 15):
                    x, y = int(at.x()) + dx, int(at.y()) + dy
                    if not (0 <= x < image.width() and 0 <= y < image.height()):
                        continue
                    px = image.pixelColor(x, y)
                    # the halo is drawn in (224, 104, 95) over a dark chart
                    if px.red() > px.green() + 18 and px.red() > px.blue() + 18:
                        hot += 1
            win.close()
            return hot

        # Differenced against the same star with nothing growing on it,
        # because the chart has other red on it — the hatching over anything
        # beyond reach sits right there and the first draft counted it.
        blind_clean = redness(False, 0.0)
        blind_hot = redness(False, 0.95)
        seen_clean = redness(True, 0.0)
        seen_hot = redness(True, 0.95)
        assert seen_hot - seen_clean > 40, (
            f"a picket sits in a star at 95% and the glow adds only "
            f"{seen_hot - seen_clean} pixels — the halo is not being drawn")
        assert blind_hot == blind_clean, (
            f"a star nobody of yours has looked at glows "
            f"{blind_hot - blind_clean} pixels brighter for being infested — "
            "the halo is not respecting the fog")
        return (f"{seen_hot - seen_clean} pixels of glow where something is "
                f"watching, {blind_hot - blind_clean} where nothing is")

    @check("a picket buys the reading")
    def _():
        # The other half. `watch` gates the growth reports; it has to gate
        # this too, or the report was the only thing it bought.
        game = new_game("picket")
        target = next(s for s in game.galaxy.systems
                      if not intel.sees_bloom(game, s))
        target.bloom = 0.6
        blind = _panel_text(game, target)
        assert "Bloom mass" not in blind, blind[:120]
        assert "watching it" in blind, (
            "the panel goes quiet without saying it does not know")

        _picket(game, target)
        game.recompute()
        assert intel.sees_bloom(game, target)
        seeing = _panel_text(game, target)
        assert "Bloom mass: 60%" in seeing, (
            f"a picket in the system and the panel still will not say: "
            f"{seeing[:160]}")
        return "blind without, 60% with a picket in the system"

    @check("being there, or holding it, is enough")
    def _():
        # The other two ways of having eyes, so the rule is not "pickets
        # only" — a captain standing in a system can obviously see it.
        game = new_game("there")
        here = game.system
        assert intel.sees_bloom(game, here), (
            "the system the ship is sitting in reads as unknown")

        game2 = new_game("held")
        target = next(s for s in game2.galaxy.systems
                      if not intel.sees_bloom(game2, s))
        colony = Colony(id=9, class_id="lichen_dome", name="Dome",
                        system_id=target.id, body_id=target.bodies[0].id,
                        need=0, online=True, pop=10_000)
        game2.colonies.append(colony)
        assert intel.sees_bloom(game2, target), (
            "a colony of yours in the system and you cannot see the Bloom "
            "eating it")
        colony.online = False
        assert not intel.sees_bloom(game2, target), (
            "a colony that is not online yet is still reporting")
        return "where you stand, and where you hold, both count"

    @check("the sector total is still told")
    def _():
        # Scouting is a cost, not a wall. However dark the chart, the
        # Holdings screen still says how bad it is overall.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QLabel
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("total")
        unseen = [s for s in game.galaxy.systems
                  if not intel.sees_bloom(game, s)]
        for system in unseen[:9]:
            system.bloom = 0.5
        from ..sim import threat
        game.bloom_total = threat.bloom_burden(game)
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.go("empire")
        for _ in range(3):
            app.processEvents()
        text = " ".join(lab.text() for lab in
                        win.views["empire"].findChildren(QLabel) if lab.text())
        win.close()
        assert "carrying unlicensed growth" in text, (
            "the sector total is gone too, so the captain is blind rather "
            "than merely uninformed")
        assert "of the sector by mass" in text
        return "how bad it is stays public; where it is has to be scouted"

    @check("whose space it is waits for a registry entry")
    def _():
        # The same rule, applied to the line above it: a star nobody has
        # catalogued does not announce its owner and its creed.
        game = new_game("whose")
        dark = next(s for s in game.galaxy.systems
                    if intel.level(game, s) == 0 and s.faction)
        text = _panel_text(game, dark)
        from ..data.factions import FACTIONS_BY_ID
        owner = FACTIONS_BY_ID.get(dark.faction)
        assert owner is not None
        assert owner.name not in text, (
            f"{dark.name} is uncatalogued and the panel names {owner.name} "
            "as holding it")
        assert "nobody here has said" in text, (
            "the panel says nothing at all rather than saying it does not "
            "know")
        return f"an uncatalogued star keeps its flag to itself"
