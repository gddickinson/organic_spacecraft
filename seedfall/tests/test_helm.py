"""The burn board: whether the numbers on it are accounted for.

A quoted burn carries a risk, and that risk is the profile's own plus two
surcharges the helm applies on top — `hot_risk` for the heat already in the
hull, and `_heat_risk` for working close to the star. Both were charged
silently in cases the screen had no words for:

- **The heat you are carrying.** A captain fresh off a run of hard burns saw
  coast quoted at 0.34 where its profile says 0.06, with nothing anywhere on
  the screen accounting for the other 0.28.
- **The star at your back.** `_heat_risk` takes the *nearer* of the two ends
  of a leg, so a hull parked at 0.40 AU paid the surcharge on every departure
  — including one nine AU outward — while `path_note` only ever described the
  arrival. Somebody had already fixed the note to talk about the destination,
  for the good reason that a warning identical across every choice is
  furniture; the risk was never brought into line with it.

The claim that matters is the general one, and it is the one that would have
caught both at once: **nothing on the board costs more than its profile says
without the screen saying why.**

Two more arrived from a player, and both were about the same thing: the Fleet
Hub was drawn on the chart and could not be used.

* **"Set course" did nothing.** The button reads "Set course — 4 d, 2 t" and
  its tooltip says "Fly to Fleet Hub"; it called `course_to`, which only
  *aims* the helm. A quay's body is very often the body already targeted, so
  it set what was already set. Clicked, measured: `target` 0 → 0,
  `orbit_body` None → None, day 0 → 0, fuel 20 → 20. Nothing at all.
* **The Hub could not be clicked.** The painter drew its mark 11 px off the
  planet; the hit test only ever walked `system.bodies`, with an 18 px
  radius. So a click on the station landed on the planet — which was
  usually already selected. `QUAY_OFFSET` is one number now, used by the
  painter and the hit test alike.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..data.crossings import CROSSINGS
from ..data.starclasses import mu_of
from ..sim import flight
from ..sim.actions import jump_quote
from ..world.galaxy import distance
from .harness import Suite


def _hot(seed: str, legs: int = 6):
    """A hull fresh off a run of hard burns."""
    game = new_game(seed)
    for leg in range(legs):
        game.ship.cargo["volatiles"] = 9999
        flight.travel_to(game, leg % len(game.system.bodies), "hard")
    return game


def _parked_deep(seed: str):
    """A hull sitting inside the star's heat, wherever it goes next."""
    game = new_game(seed)
    game.ship.cargo["volatiles"] = 9999
    inner = min(range(len(game.system.bodies)),
                key=lambda i: flight.orbit_radius(game.system.bodies[i]))
    flight.travel_to(game, inner, "economy")
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a quay's Set course actually takes the ship there")
    def _():
        # Reported by a player: clicking "Set course" on the Fleet Hub did
        # nothing whatever. Driven through the real button, and asked of the
        # outcome — is the ship *there* — rather than of any intermediate.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication, QPushButton
        from ..core.rng import RNG
        from ..sim import anchorage as anchorage_sim
        from ..sim import transit as transit_sim
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        flown = 0
        for seed in range(6):
            game = new_game(f"setcourse-{seed}")
            places = [a for a in anchorage_sim.in_system(game) if not a.here]
            if not places:
                continue
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.go("helm")
            for _ in range(2):
                app.processEvents()
            view = win.views["helm"]
            buttons = [b for b in view.findChildren(QPushButton)
                       if b.text().startswith("Set course") and b.isEnabled()]
            if not buttons:
                win.close()
                continue
            was = game.orbit_body
            buttons[0].click()
            for _ in range(2):
                app.processEvents()
            assert win.transit is not None, (
                f"seed {seed}: Set course was clicked and no crossing began — "
                "the button does nothing, which is what was reported")
            crossing = win.transit
            rng = RNG(f"cross{seed}")
            guard = 0
            while not crossing.over and guard < 80:
                transit_sim.stand(game, crossing, rng)
                guard += 1
            transit_sim.finish(game, crossing)
            win.close()
            target = game.system.bodies[crossing.body_index]
            assert game.orbit_body == target.id, (
                f"seed {seed}: the crossing finished and the ship is at "
                f"{game.orbit_body}, not {target.id}")
            assert game.orbit_body != was or was == target.id
            flown += 1
        assert flown >= 3, f"only {flown} boards offered a course to fly"
        return f"{flown} quays: clicked, crossed, and the hull is alongside"

    @check("a quay can be picked off the chart")
    def _():
        # The other half of the same report. The mark is drawn offset from
        # its planet and the hit test only knew about planets, so clicking a
        # station selected the world underneath it — usually already the
        # target, so nothing appeared to happen.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication
        from ..sim import anchorage as anchorage_sim
        from ..ui.helm_view import OrbitChart
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        picked = 0
        for seed in range(5):
            game = new_game(f"quaypick-{seed}")
            places = anchorage_sim.in_system(game)
            if not places:
                continue
            win = MainWindow(game)
            win.toast = lambda *a, **k: None
            win.resize(1300, 950)
            win.show()
            win.go("helm")
            for _ in range(2):
                app.processEvents()
            chart = win.views["helm"].findChild(OrbitChart)
            assert chart is not None
            for place in places:
                if place.body_index >= len(game.system.bodies):
                    continue
                chart.place = None
                mark = chart.place_mark(game, place)
                event = QMouseEvent(
                    QMouseEvent.Type.MouseButtonPress, mark, mark,
                    Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                    Qt.KeyboardModifier.NoModifier)
                chart.mousePressEvent(event)
                assert chart.place == place.id, (
                    f"clicking {place.name} where it is drawn selected "
                    f"{chart.place!r} instead")
                assert win.views["helm"].place == place.id, (
                    "the chart knows which quay was picked and the view "
                    "does not")
                picked += 1
            win.close()
        assert picked >= 4, picked
        return f"{picked} quays clicked where they are drawn, every one picked"

    @check("a planet and its quay are each clickable in their own right")
    def _():
        # The rule underneath `QUAY_OFFSET`. Its exact value is a matter of
        # taste and no check should pin it — the painter and the hit test
        # both read it, so moving it moves both answers together and they
        # agree all the way down, which is the point of having one number.
        #
        # What must hold is that the two marks are separable: quays are
        # tested first, so an offset of zero would put the station exactly on
        # its world and make the world unclickable for ever.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QMouseEvent
        from PyQt6.QtWidgets import QApplication
        from ..sim import anchorage as anchorage_sim
        from ..sim import flight
        from ..ui.helm_view import OrbitChart
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        assert app is not None
        game = new_game("bothclick")
        places = anchorage_sim.in_system(game)
        assert places, "no quay in this system to test with"
        win = MainWindow(game)
        win.toast = lambda *a, **k: None
        win.resize(1300, 950)
        win.show()
        win.go("helm")
        for _ in range(2):
            app.processEvents()
        chart = win.views["helm"].findChild(OrbitChart)

        def click(at):
            chart.mousePressEvent(QMouseEvent(
                QMouseEvent.Type.MouseButtonPress, at, at,
                Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier))
            return chart.place

        checked = 0
        for place in places:
            if place.body_index >= len(game.system.bodies):
                continue
            body = game.system.bodies[place.body_index]
            chart.place = None
            assert click(chart.place_mark(game, place)) == place.id, (
                f"{place.name} is not clickable where it is drawn")
            chart.place = None
            on_world = chart._to_screen(*flight.position(body, game.day, mu_of(game.system)))
            assert click(on_world) is None, (
                f"clicking {body.name} itself selected the quay in orbit of "
                "it — the two marks are on top of each other")
            assert win.views["helm"].target == place.body_index
            checked += 1
        win.close()
        assert checked >= 1, checked
        return (f"{checked} quay/world pairs, each mark selecting itself and "
                "not the other")

    @check("no burn costs more than its profile without the screen saying why")
    def _():
        # The general invariant. Both surcharges were live and unexplained,
        # and this catches either of them coming back — or a third one being
        # added without words.
        # Each surcharge is checked *separately*. Asking only "is there any
        # note at all" was too weak and I caught it being too weak: with the
        # star-arrival warning deleted, the distance note kept the quote
        # looking explained and nothing failed.
        states = [("a cold hull, well out", new_game("cold")),
                  ("fresh off hard burns", _hot("hot")),
                  ("parked inside the star's heat", _parked_deep("deep"))]
        silent, checked = [], 0
        for label, game in states:
            sx, sy = flight.ship_position(game)
            for body in game.system.bodies:
                for burn in flight.BURNS:
                    q = flight.quote(game, body, burn.id)
                    note = flight.path_note(game, body, burn.id) or ""
                    checked += 1
                    # Floors written here, not taken from the module: a
                    # surcharge small enough to be noise may go unsaid, and
                    # that is the point of the thresholds. Raising a threshold
                    # to hide a *large* one is caught by `unstated` below.
                    parts = [
                        ("distance", min(flight.LONG_LEG_CAP,
                                         q["au"] * flight.PER_AU),
                         0.03, "AU on this arc"),
                        ("the star", flight._heat_risk(sx, sy, *q["aim"]),
                         0.01, "from the star"),
                        ("carried heat", flight.hot_risk(game),
                         0.07, "carrying"),
                    ]
                    unstated = 0.0
                    for name, amount, floor, words in parts:
                        if words in note:
                            continue
                        unstated += amount
                        if amount >= floor:
                            silent.append(
                                f"{label}: {burn.id} to {body.name} is "
                                f"charged {amount:+.3f} for {name} and the "
                                f"screen says {note or 'nothing'!r}")
                    assert unstated < 0.09, (
                        f"{label}: {burn.id} to {body.name} carries "
                        f"{unstated:.3f} of risk that nothing on the screen "
                        "accounts for")
                    # And the total has to add up to what is quoted.
                    total = (burn.risk + sum(a for _n, a, _f, _w in parts))
                    assert abs(total - q["risk"]) < 1e-6, (
                        f"{burn.id} to {body.name}: quoted {q['risk']:.3f}, "
                        f"components sum to {total:.3f} — there is a fourth "
                        "surcharge nobody has named")
        assert checked > 30, checked
        assert not silent, (
            f"{len(silent)} unexplained surcharges: " + "; ".join(silent[:3]))
        return (f"{checked} quotes across three hulls, every component "
                "named and the total reconciled")

    @check("the heat in the hull is named, and so is what it costs")
    def _():
        game = _hot("named")
        cap = game.ship_stats.heat_cap
        assert game.ship.heat > cap, (
            f"six hard burns left the hull at {game.ship.heat:.0f} against a "
            f"cap of {cap:.0f} — this hull is not hot enough to test with")
        body = game.system.bodies[-1]
        note = flight.path_note(game, body, "coast") or ""
        added = flight.hot_risk(game)
        assert f"{added:.2f}" in note, (
            f"the note never states the {added:.2f} it is charging: {note!r}")
        assert f"{game.ship.heat:.0f}" in note, (
            f"the note never states how much heat is aboard: {note!r}")
        assert "cooking" in note, (
            f"the hull is over its cap and taking damage for it, and the "
            f"note does not mention it: {note!r}")
        return note[:96]

    @check("a cold hull well clear of the star is told nothing at all")
    def _():
        # A warning on every screen forever is furniture. This is the check
        # that stops the fix for silence becoming noise instead.
        game = new_game("quiet")
        here = math.hypot(*flight.ship_position(game))
        assert here > flight.HOT_RADIUS, here
        assert game.ship.heat < game.ship_stats.heat_cap * flight.WORTH_SAYING
        said = 0
        for body in game.system.bodies:
            for burn in flight.BURNS:
                note = flight.path_note(game, body, burn.id)
                if note and ("carrying" in note or "starting" in note):
                    said += 1
        assert said == 0, (
            f"{said} quotes warned a cold hull about heat it does not have")
        return "nothing said to a cold hull well out"

    @check("leaving from inside the star's heat is stated, not just arriving")
    def _():
        game = _parked_deep("depart")
        here = math.hypot(*flight.ship_position(game))
        assert here < flight.HOT_RADIUS, (
            f"parked at {here:.2f} AU, which is not inside the heat")
        outward = [b for b in game.system.bodies
                   if math.hypot(*flight.intercept(game, b, "economy")["aim"])
                   >= flight.HOT_RADIUS]
        assert outward, "no body in this system is outside the star's heat"
        for body in outward:
            quoted = flight.quote(game, body, "economy")["risk"]
            note = flight.path_note(game, body, "economy") or ""
            assert quoted > 0, quoted
            assert "starting" in note, (
                f"a burn from {here:.2f} AU out to "
                f"{math.hypot(*flight.intercept(game, body, 'economy')['aim']):.2f} "
                f"AU is surcharged and says only: {note!r}")
        return (f"parked at {here:.2f} AU — every outward burn says why it is "
                f"dearer ({len(outward)} of them)")

    @check("a crossing quote states both clocks and they disagree properly")
    def _():
        # The helm's other half: a jump is priced on sector time and lived on
        # ship time, and the two only agree on a steady transit.
        game = new_game("clocks")
        target = min((s for s in game.galaxy.systems
                      if s.id != game.location_id),
                     key=lambda s: distance(game.system, s))
        rows = []
        for crossing in CROSSINGS:
            q = jump_quote(game, target, crossing.id)
            assert q["days"] >= 1 and q["ship_days"] >= 1, q
            if crossing.dilation == 1.0:
                assert q["ship_days"] == q["days"], (
                    f"{crossing.id} does not dilate and the clocks still "
                    f"differ: {q['days']} against {q['ship_days']}")
            else:
                assert q["ship_days"] < q["days"], (
                    f"{crossing.id} dilates {crossing.dilation}x and the crew "
                    f"still lives {q['ship_days']} of {q['days']} days")
            rows.append(f"{crossing.id} {q['days']}/{q['ship_days']}d "
                        f"{q['fuel']}t")
        return " · ".join(rows)
