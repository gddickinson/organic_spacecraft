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

    @check("a free flight's panel answers a free flight's questions")
    def _():
        # **Three rows were answering an approach's questions.** `readout`
        # had two branches, orbiting and not, and "not" meant berthing:
        # `conn.range_km` is the distance from the origin of the conn's frame,
        # which is the target in an approach and *where she let go* in a free
        # flight — so it was printed as "Range" and marked amber past the
        # 40 km at which a berthing is going badly. Measured on a flight out
        # to a hull: "Range 8,590.0 km" in amber with the contact she was
        # flying at 2,968 km off, and "Relative 583.2 m/s" in amber because
        # 583 m/s is a lot for coming alongside a quay and nothing at all for
        # crossing a system.
        from ..sim import conn as conn_sim
        from ..sim import engage as engage_sim
        from ..sim import freeflight as free_sim
        from ..sim import instruments as panel_sim
        from ..sim import track as track_sim

        game = new_game("panel")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        free_sim.steer(game, conn, hull)
        for _ in range(300):
            conn_sim.apply(conn, "forward", main=True, ticks=1)

        rows = panel_sim.readout(conn)
        names = [k for k, _v, _kind in rows]
        assert "Flown" in names, names
        assert "Speed" in names, names
        # No row may claim to be a range, because the only honest range out
        # here is to the mark, and the mark lives on the screen that holds it.
        assert "Range" not in names, (
            "a free flight's panel prints a Range; the number it has is the "
            "distance from where she let go, which is not a range to anything")
        assert "Closing" not in names, (
            "a free flight's panel prints a Closing; there is nothing out "
            "here being closed on")

        # And nothing cries wolf. Flying fast and far is the point.
        flown = dict((k, (v, kind)) for k, v, kind in rows)
        assert flown["Flown"][1] == "ok", flown["Flown"]
        assert flown["Speed"][1] == "ok", flown["Speed"]
        assert conn.speed > 100.0, f"the fixture never got moving: {conn.speed}"
        assert conn.range_km > 1000.0, conn.range_km

        # The distance flown is not the range to the mark, and saying so is
        # the whole point: they differ, and the panel names the one it has.
        to_mark = engage_sim.range_km(game, conn, hull)
        assert abs(to_mark - conn.range_km) > 1000.0, (
            f"flown {conn.range_km:,.0f} km and the mark {to_mark:,.0f} km "
            f"off — too close together for this check to prove anything")
        return (f"Flown {conn.range_km:,.0f} km at {conn.speed:,.0f} m/s, "
                f"both ok, with the mark {to_mark:,.0f} km off")

    @check("an approach and an orbit keep the rows they had")
    def _():
        # The free-flight branch went in *above* the orbiting one, which is
        # exactly where a mistake would silently take the other two with it.
        from ..sim import berthing as berth_sim
        from ..sim import instruments as panel_sim
        from ..sim import track as track_sim

        game = new_game("panel")
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        names = [k for k, _v, _kind in panel_sim.readout(conn)]
        for row in ("Range", "Closing", "Relative"):
            assert row in names, (f"an approach lost its {row} row", names)
        assert "Flown" not in names, names

        body = next(c for c in track_sim.contacts(game) if c.kind == "body")
        circling, why = berth_sim.begin(game, body)
        assert circling is not None, why
        assert circling.target.mu > 0, "the fixture is not a world to orbit"
        circling.pos = [0.0, circling.target.radius_km + 400.0, 0.0]
        names = [k for k, _v, _kind in panel_sim.readout(circling)]
        for row in ("Altitude", "Circular here"):
            assert row in names, (f"an orbit lost its {row} row", names)
        assert "Flown" not in names and "Range" not in names, names
        return "approach keeps Range/Closing/Relative; orbit keeps Altitude"

    @check("an instrument with nowhere to paint declines, rather than dying")
    def _():
        # **This ended a 174-suite run twice, at two different suites.**
        # `QPainter(widget)` fails when there is no paint device to hand out —
        # a zero-sized instrument, or a backing store the platform refused —
        # and PyQt then reports every call on the dead painter as "first
        # argument of unbound method must have type 'QPainter'". Raised inside
        # `paintEvent`, where Qt cannot propagate it, it killed the process at
        # whichever window happened to be painting: gunnery on one run, verbs
        # on the next two. Guarding `ui/gauges` moved it to `ui/viewport`,
        # which is what made it a class of fault rather than a site — so the
        # guard is one door, `ui/painting.Painted`, and both go through it.
        from .test_ui import _use_offscreen
        _use_offscreen()
        from PyQt6.QtWidgets import QApplication
        from ..ui import gauges, painting

        app = QApplication.instance() or QApplication([])
        readings = telemetry.all_readings(new_game("inst-paint"))
        reading = next(iter(readings.values()))
        was = len(painting.MISSES)
        made = []
        for cls in (gauges.Dial, gauges.Stack, gauges.Scope):
            widget = cls(reading)
            # Nowhere to draw: no width, and never shown, so Qt has given it
            # no backing store at all. The *height* stays at whatever
            # `Instrument.__init__` set as a minimum — measured, 160 for a
            # Dial and 240 for a Scope — so zero width is the whole cause.
            widget.resize(0, 0)
            widget.paintEvent(None)      # must not raise
            made.append(cls.__name__)
        app.processEvents()
        missed = painting.MISSES[was:]
        assert len(missed) == len(made), (
            f"painted {made} at zero size and only {missed} declined — an "
            f"instrument drew on a painter that never began")
        assert all(w == 0 or h == 0 for _n, w, h, _why in missed), missed

        # **And a healthy instrument must still paint.** `paintEvent` catches
        # what a failed paint raises, which is exactly the shape of guard that
        # can turn a real regression green — a `draw` that threw on every
        # single frame would look identical from outside. It does not get to:
        # given a size and a backing store, nothing is allowed to miss.
        mark = len(painting.MISSES)
        for cls in (gauges.Dial, gauges.Stack, gauges.Scope):
            widget = cls(reading)
            widget.resize(220, 240)
            widget.grab()
        app.processEvents()
        clean = painting.MISSES[mark:]
        assert not clean, f"an instrument with room to draw still missed: {clean}"

        # **A paint that fails halfway must not reach Qt.** This is the case
        # the full runs actually hit and the one no fixture can conjure — the
        # painter's C++ instance went away three calls into `_face`, with
        # `isActive()` having just said yes. What can be staged is the shape
        # of it: a draw that raises where Qt cannot catch it. It is recorded
        # and it does not propagate.
        class Broken(gauges.Dial):
            def draw(self, p):
                raise RuntimeError("the painter went away")

        mark = len(painting.MISSES)
        broken = Broken(reading)
        broken.resize(220, 240)
        broken.grab()                      # must not raise
        app.processEvents()
        caught = painting.MISSES[mark:]
        assert len(caught) == 1, f"a failed paint was not recorded: {caught}"
        assert "went away" in caught[0][3], caught[0]

        # **And the camera view goes through the same door**, because guarding
        # the gauges alone just moved the crash into `ui/viewport`.
        from ..sim import freeflight
        from ..ui.viewport import Viewport
        assert issubclass(Viewport, painting.Painted), (
            "the viewport paints without the guard that the gauges have")
        conn, why = freeflight.begin(new_game("inst-view"))
        assert conn is not None, why
        mark = len(painting.MISSES)
        feed = Viewport(conn, "fore")
        feed.resize(0, 0)
        feed.paintEvent(None)              # must not raise
        assert len(painting.MISSES) == mark + 1, (
            "the viewport drew on a painter that never began")
        mark = len(painting.MISSES)
        feed.resize(320, 200)
        feed.grab()
        assert len(painting.MISSES) == mark, (
            f"a viewport with room to draw missed: {painting.MISSES[mark:]}")

        return (", ".join(f"{n} {w}×{h}" for n, w, h, _why in missed)
                + " declined to paint instead of ending the run")

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
