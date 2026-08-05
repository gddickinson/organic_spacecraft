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
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
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
    # Buttons as well as labels: a price a captain reads off the thing they are
    # about to press is on the screen as much as one in a row. The chart's own
    # price lives on its button, and a check reading only labels could not see it.
    text = " ".join(w.text() for w in view.findChildren(QLabel) if w.text())
    text += " " + " ".join(b.text() for b in view.findChildren(QPushButton)
                           if b.text())
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

    @check("how many bodies are down there waits for a chart too")
    def _():
        # The same rule as the Bloom halo and the faction name, applied to the
        # one fact a chart exists to sell. `LEVELS[0]` calls a registry entry
        # "a body count the registry will not stand behind" and `LEVELS[1]`
        # promises "the bodies are real" — and the panel printed
        # `len(sys.bodies)` at every rank, so the two rungs differed by a
        # faction name and the shade of a dot.
        game = new_game("bodies")
        dark = next(s for s in game.galaxy.systems
                    if intel.level(game, s) == 0 and len(s.bodies) >= 2)
        assert intel.body_count(game, dark) is None, (
            "an uncatalogued system is handing over its body count")
        text = _panel_text(game, dark)
        assert f"{len(dark.bodies)} catalogued bodies" not in text, (
            f"{dark.name} is uncatalogued and the panel counts its bodies")
        assert "nobody has said" in text, (
            f"the panel neither counts them nor says it cannot: {text[:300]}")

        # And a chart delivers it.
        game.credits = 500_000
        assert intel.buy_chart(game, dark)["ok"]
        assert intel.body_count(game, dark) == len(dark.bodies)
        after = _panel_text(game, dark)
        assert f"{len(dark.bodies)} catalogued bodies" in after, (
            f"bought the chart and the count is still withheld: {after[:300]}")
        return (f"{dark.name}: \"nobody has said\" before the chart, "
                f"{len(dark.bodies)} bodies after it")

    @check("the marker does not measure out a count nobody has")
    def _():
        # The panel is words and the marker is a radius, so reading labels
        # cannot see it: a mutation putting `r = 2.6 + len(sys.bodies) * 0.3`
        # back left every check green while the chart drew the withheld number.
        #
        # A first draft of this counted *pixels*, in the idiom of the halo check
        # above, and it was no good: eleven against six on unmutated code, and
        # red in the full suite but not on its own. A marker is nine pixels
        # across on a chart full of links, hatching and labels, and there is not
        # enough ink in it to difference. So the rule itself is a function now,
        # and this reads it.
        from ..ui.map_view import marker_radius

        game = new_game("marker")
        dark = [s for s in game.galaxy.systems if intel.level(game, s) == 0]
        small = min(dark, key=lambda s: len(s.bodies))
        big = max(dark, key=lambda s: len(s.bodies))
        assert len(big.bodies) - len(small.bodies) >= 3, (
            f"{len(small.bodies)} and {len(big.bodies)} bodies — not far enough "
            "apart to tell one marker from the other")
        assert marker_radius(game, small) == marker_radius(game, big), (
            f"{len(small.bodies)} bodies draws r="
            f"{marker_radius(game, small):.2f} and {len(big.bodies)} draws "
            f"{marker_radius(game, big):.2f} — the marker is measuring out the "
            "count the panel is withholding")

        # And once they are known, the size means something again.
        game.credits = 500_000
        assert intel.buy_chart(game, small)["ok"]
        assert intel.buy_chart(game, big)["ok"]
        assert marker_radius(game, big) > marker_radius(game, small), (
            "charted, and the two stars still draw the same size — the marker "
            "has stopped saying anything at all")
        return (f"{len(small.bodies)} and {len(big.bodies)} bodies draw the same "
                f"marker unknown, and {marker_radius(game, small):.1f} against "
                f"{marker_radius(game, big):.1f} once charted")

    @check("the price of a chart is not the answer written on the tag")
    def _():
        # **Measured before the fix: `900 + 260 a body`.** Forty-one unknown
        # systems, thirteen distinct prices, and the count inverted exactly —
        # 1,160 meant one body, 1,420 two, 1,680 three. A captain who could do a
        # subtraction never needed to buy a chart at all.
        #
        # Correlation rather than a formula, because the claim is about what the
        # price *tells* you and not about which terms are in it.
        import statistics

        def pearson(xs, ys):
            mx, my = statistics.mean(xs), statistics.mean(ys)
            num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
            den = (sum((x - mx) ** 2 for x in xs)
                   * sum((y - my) ** 2 for y in ys)) ** 0.5
            return num / den if den else 0.0

        worst = 0.0
        seeds = ("tag-a", "tag-b", "tag-c")
        for seed in seeds:
            game = new_game(seed)
            rows = [(intel.chart_price(game, s), len(s.bodies))
                    for s in game.galaxy.systems if intel.level(game, s) == 0]
            assert len(rows) > 20, len(rows)
            prices = [r[0] for r in rows]
            counts = [r[1] for r in rows]
            old_way = [900 + 260 * n for n in counts]
            assert abs(pearson(old_way, counts) - 1.0) < 1e-9, (
                "the old formula is supposed to be the perfectly leaky one")
            leak = abs(pearson(prices, counts))
            worst = max(worst, leak)
            assert leak < 0.35, (
                f"{seed}: the price still tracks the body count at r={leak:.2f}")
        return (f"over {len(seeds)} sectors the worst price-to-body-count "
                f"correlation is {worst:.2f}, against 1.00 for the old formula")

    @check("the offer says what a chart buys")
    def _():
        # #39's rule, on the one purchase in the game whose value was entirely
        # inferable from its price: say what it gives you.
        game = new_game("offer")
        game.credits = 500_000
        dark = next(s for s in game.galaxy.systems if intel.level(game, s) == 0)
        offer = intel.chart_offer(game, dark)
        assert offer["can"] and offer["buys"], offer
        text = _panel_text(game, dark)
        for line in offer["buys"]:
            assert line in text, (
                f"the offer promises {line!r} and the panel does not say it")
        from ..core.util import credits as cr
        assert cr(offer["price"]) in text, (
            f"{cr(offer['price'])} wanted and the panel says otherwise")

        # A captain who cannot pay is told the price, not offered the button.
        broke = new_game("offer")
        broke.credits = 10
        shut = intel.chart_offer(broke, dark)
        assert not shut["can"] and "credits for it" in shut["why"], shut
        return (f"the panel names the price and all {len(offer['buys'])} things "
                "the chart buys")

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

    @check("the Holdings panel counts what you have seen, not what is there")
    def _():
        # `intel.sees_bloom` covers the chart, and the Holdings panel went
        # straight round it: every infested system in the sector counted and
        # the sector-wide burden printed, above a picket whose `watch` is
        # sold on telling you what happens where you are not.
        from ..sim import threat as threat_sim
        game = new_game("holdings-fog")
        truly = len(threat_sim.bloom_systems(game))
        known = threat_sim.known_bloom(game)
        assert truly > 0, "this sector has no growth to hide"
        assert known["count"] < truly, (
            f"the panel knows about {known['count']} of {truly} infested "
            "systems without having looked at any of them")
        assert known["unscouted"] > 0
        assert known["burden"] <= game.bloom_total

        # Look at one, and it appears — which is what makes looking worth it.
        hidden = next(s for s in game.galaxy.systems
                      if s.bloom > 0.02 and not intel.sees_bloom(game, s))
        hidden.visited = True
        after = threat_sim.known_bloom(game)
        assert after["count"] == known["count"] + 1, (
            "visiting an infested system did not add it to the census")
        assert after["burden"] > known["burden"]

        # **The ending is decided by what is true.** Fogging the display is
        # right; fogging the achievement would let a captain take
        # Containment by keeping their eyes shut.
        shown = threat_sim.victory_progress(game, seen_only=True)
        truth = threat_sim.victory_progress(game)
        assert shown["containment"][0] != truth["containment"][0], (
            "the containment bar reads the same fogged or not")
        assert shown["containment"][2] is truth["containment"][2] is False
        return (f"{known['count']} of {truly} known before looking, "
                f"{after['count']} after; the ending still reads the truth")
