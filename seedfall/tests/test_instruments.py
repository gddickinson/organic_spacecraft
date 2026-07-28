"""Instrument checks — a gauge has to agree with the ship and with itself.

The monitors are pop-out windows a player leaves open while flying, so two
things matter and neither is cosmetic. They must read the *live* game rather
than a snapshot taken when they opened, and every face must agree with itself:
the first crew dial drew a needle over "0/0 d" while its own caption on the
same face said "124 days of air", because `Dial` reads `now`/`cap` and the crew
reading supplied neither.

The readings live in `sim/telemetry.py` precisely so this can check what an
instrument says without painting it.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import telemetry
from .harness import Suite

#: Instruments drawn as a dial, which reads `now` against `cap`.
DIALS = ("power", "heat", "crew")


def _battered(seed: str):
    game = new_game(seed)
    game.ship.heat = game.ship_stats.heat_cap * 1.2
    game.ship.layers[0].hp = 0
    game.ship.cargo = {"ore": game.ship_stats.cargo}
    game.recompute()
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("every instrument reads, on a fresh ship and a wrecked one")
    def _():
        for seed, game in (("fresh", new_game("inst-fresh")),
                           ("battered", _battered("inst-worn"))):
            readings = telemetry.all_readings(game)
            assert set(readings) == set(telemetry.INSTRUMENTS_BY_ID), readings
            for name, reading in readings.items():
                assert reading.get("title"), f"{name} has no title"
                assert reading.get("note"), f"{name} says nothing"
                assert reading.get("band") in ("good", "watch", "bad"), (
                    f"{name} band {reading.get('band')!r}")
                fraction = reading.get("fraction")
                assert isinstance(fraction, float) and fraction >= 0, (
                    f"{name} fraction {fraction!r}")
        return f"{len(telemetry.INSTRUMENTS)} instruments on two ships"

    @check("a dial agrees with itself: a needle, a number and a caption")
    def _():
        # The defect this exists for. A dial paints `now`/`cap` in the middle
        # of the face and `note` along the bottom, so a reading that omits
        # `now` draws "0/0" under a caption saying something else entirely.
        for name in DIALS:
            for game in (new_game("dial-fresh"), _battered("dial-worn")):
                reading = telemetry.read(game, name)
                assert "now" in reading and "cap" in reading, (
                    f"{name} is drawn as a dial and supplies no now/cap — the "
                    f"face would read 0/0 beside {reading.get('note')!r}")
                assert reading["cap"] > 0, f"{name} has no scale"
                expected = min(1.5, reading["now"] / reading["cap"])
                assert abs(reading["fraction"] - min(1.0, expected)) < 0.02 \
                    or reading["fraction"] >= 1.0, (
                    f"{name}: needle at {reading['fraction']:.2f} for "
                    f"{reading['now']:.0f}/{reading['cap']:.0f}")
        return f"{len(DIALS)} dials, needle and number from the same numbers"

    @check("the bands move when the ship is actually in trouble")
    def _():
        calm = new_game("band-calm")
        assert telemetry.heat(calm)["band"] == "good"
        assert telemetry.hold(calm)["band"] == "good"
        assert telemetry.integrity(calm)["band"] == "good"

        hot = new_game("band-hot")
        hot.ship.heat = hot.ship_stats.heat_cap * 1.1
        assert telemetry.heat(hot)["band"] == "bad", "cooking reads as fine"
        assert "cooking" in telemetry.heat(hot)["note"]

        full = new_game("band-full")
        full.ship.cargo = {"ore": full.ship_stats.cargo}
        assert telemetry.hold(full)["band"] == "bad", "a full hold reads fine"

        holed = new_game("band-holed")
        for layer in holed.ship.layers:
            layer.hp = 0
        assert telemetry.integrity(holed)["band"] == "bad"
        assert "pressure vessel" in telemetry.integrity(holed)["note"]
        return "heat, hold and integrity each turn bad when they should"

    @check("the scope shows what is actually in range")
    def _():
        from ..world.galaxy import distance
        game = new_game("scope")
        reading = telemetry.scope(game)
        assert len(reading["contacts"]) == len(game.system.bodies)
        reach = reading["reach"]
        for star in reading["neighbours"]:
            found = next(s for s in game.galaxy.systems
                         if s.name == star["name"])
            assert distance(found, game.system) <= reach + 0.01, (
                f"{star['name']} is on the scope and out of range")
        beyond = [s for s in game.galaxy.systems
                  if s.id != game.location_id
                  and distance(s, game.system) <= reach]
        assert len(reading["neighbours"]) == len(beyond), (
            f"{len(reading['neighbours'])} on the scope, {len(beyond)} in range")
        return (f"{len(reading['contacts'])} bodies and "
                f"{len(reading['neighbours'])} stars inside {reach:.1f} ly")

    @check("an instrument window opens, paints, closes and reopens")
    def _():
        try:
            from .test_ui import _use_offscreen
            _use_offscreen()
            from PyQt6.QtWidgets import QApplication
        except ImportError as err:          # pragma: no cover
            return f"skipped: {err}"
        from ..ui import theme
        from ..ui.monitors import SHAPES, close_all, open_all, toggle
        from ..ui.window import MainWindow

        app = QApplication.instance() or QApplication([])
        app.setStyleSheet(theme.stylesheet())
        game = _battered("inst-ui")
        win = MainWindow(game)
        win.resize(1200, 800)
        win.show()

        open_all(win)
        assert set(win.monitors) == set(SHAPES), sorted(win.monitors)
        painted = 0
        for monitor in win.monitors.values():
            monitor.resize(340, 260)
            app.processEvents()
            assert not monitor.grab().isNull()
            painted += 1

        # Live, not a snapshot: change the ship and pull again.
        power = win.monitors["power"]
        before = power.gauge.reading["now"]
        from ..data.parts import PARTS_BY_ID
        drawing = next(p for p in game.ship.fitted
                       if PARTS_BY_ID[p].fx.get("draw", 0) > 0)
        game.ship.fitted = [p for p in game.ship.fitted if p != drawing]
        game.recompute()
        power.pull()
        assert power.gauge.reading["now"] != before, (
            f"pulled {PARTS_BY_ID[drawing].name} and the gauge kept the "
            f"reading it opened with ({before})")

        close_all(win)
        assert not win.monitors, sorted(win.monitors)
        toggle(win, "scope")
        assert "scope" in win.monitors, "it would not reopen"
        close_all(win)
        win.close()
        return (f"{painted} instruments painted, live-updating, closed and "
                f"reopened")
