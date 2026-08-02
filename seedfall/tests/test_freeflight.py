"""Taking the conn on nothing in particular, and having it count.

Reported: *"There still doesn't seem to be a way to independently pilot the
ship when not engaged in some prescribed activity, such as berthing or going
into orbit."* Measured, that was exactly right. `berthing.can_conn` was the
only door into the flight pad and it wants a contact —

    "A position in empty space is somewhere to steer for, not something to
     come alongside."

— so the six axes, the main drive, the cameras and the 3D windows all existed
and none of them could be used unless the ship was arriving somewhere. Between
structures, movement was the plotting board, which is plotting rather than
flying.

The claims:

- **A captain can take the conn with nothing in reach**, and the pad is live:
  the burns are real burns and the tank goes down.
- **It moves the ship**, in the system, through the one door — the distance
  flown on the conn is the distance the hull has moved when it is secured.
- **Nothing ends it but the pilot.** A free flight opens at zero range on a
  target of radius zero, which is every arrival threshold in `sim/outcome`
  true at once; it must survive that and keep flying.
- **It is charged for.** The mass, the hours and a line in the ledger, through
  `berthing.commit` like any other approach, and the line says what it was.
- **Handing over keeps the way on**, so flying by hand and then giving the
  computer the last of it is one continuous approach rather than two.
- **The window offers it**, and the button says which act it is about to do.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot as auto_sim
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import flight
from ..sim import freeflight as free_sim
from ..sim import engage as engage_sim
from ..sim import track as track_sim
from .harness import Suite

KM_PER_AU = berth_sim.KM_PER_AU

_HELD = None


def _app():
    from .test_ui import _use_offscreen
    _use_offscreen()
    from PyQt6.QtWidgets import QApplication
    global _HELD
    _HELD = QApplication.instance() or QApplication([])
    return _HELD


def _flying(seed: str = "free"):
    """A game with the conn taken on open space."""
    game = new_game(seed)
    flight.travel_to(game, 0)
    conn, why = free_sim.begin(game)
    assert conn is not None, why
    return game, conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("the computer brings her alongside something she can see, and stops")
    def _():
        # The request said it plainly: fly to the asteroid, "or also engage
        # the auto-pilot to come alongside" it. `sim/autopilot`'s own `close`
        # cannot — it aims at a mooring mast through `sim/moorings` and
        # measures its room against a structure's radius. Out here there is
        # neither. `run_for` is the mode that belongs in open space, and it
        # decides nothing new: the rate is `autopilot.rate_for`, the burn is
        # `autopilot.hold`.
        seen = {}
        for seed in ("auto", "flighttest"):
            game = new_game(seed)
            conn, why = free_sim.begin(game)
            assert conn is not None, why
            hulls = sorted((engage_sim.range_km(game, conn, c), c)
                           for c in track_sim.contacts(game)
                           if c.kind == "hull")
            km0, hull = hulls[0]
            assert km0 > free_sim.ALONGSIDE_KM * 10, (
                f"{hull.name} is already there, at {km0:,.0f} km")
            ticks = None
            for beat in range(3000):
                axis, main, throttle = free_sim.run_for(game, conn, hull)
                conn_sim.apply(conn, axis, main=main, ticks=1,
                               throttle=throttle)
                if free_sim.alongside(game, conn, hull):
                    ticks = beat + 1
                    break
            assert ticks, (
                f"ran for {hull.name} for 3,000 ticks and got to "
                f"{engage_sim.range_km(game, conn, hull):,.0f} km")
            speed = math.dist(conn.vel, (0.0, 0.0, 0.0))
            assert speed < 2.0, (
                f"arrived alongside {hull.name} still doing {speed:,.1f} m/s")
            # Alongside means the guns can speak — 50 km is well inside the
            # 10,000 km `engage.reach_km`, and that is the point of arriving.
            ok, said = engage_sim.may_engage(game, conn, hull)
            assert ok, said
            seen[seed] = (km0, ticks, speed)
        return " · ".join(
            f"{seed}: {km:,.0f} km in {t/60:.1f} h at {sp:.2f} m/s"
            for seed, (km, t, sp) in seen.items())

    @check("a mode that needs a berth refuses in open space, rather than pretending")
    def _():
        # **Measured before this was fixed:** on a free flight `close` and
        # `orbit` both returned [0, 0, 0] — the same answer as `null` — so a
        # console offering "Close and berth" out here would have stopped the
        # ship and called it an approach.
        game = new_game("open-modes")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        for mode in ("close", "orbit"):
            assert auto_sim.target_velocity(conn, mode) is None, (
                f"{mode!r} claimed a velocity with nothing to fly to")
            assert auto_sim.autopilot(conn, mode) == (None, False, 0.0), (
                f"{mode!r} burned with nothing to fly to")
        # `null` is meaningful anywhere: stop drifting. It has to still work.
        for _ in range(30):
            conn_sim.apply(conn, "forward", main=True, ticks=1)
        was = math.dist(conn.vel, (0.0, 0.0, 0.0))
        assert was > 5.0, f"the fixture never got moving: {was}"
        for _ in range(400):
            axis, main, throttle = auto_sim.autopilot(conn, "null")
            conn_sim.apply(conn, axis, main=main, ticks=1, throttle=throttle)
            if math.dist(conn.vel, (0.0, 0.0, 0.0)) < 0.05:
                break
        now = math.dist(conn.vel, (0.0, 0.0, 0.0))
        assert now < 0.05, f"null left her doing {now:.3f} m/s"
        return f"close and orbit refuse; null killed {was:.1f} m/s to {now:.3f}"

    @check("how fast she may close is one answer, not two")
    def _():
        # `safe_rate` works out the room an approach has — the structure, the
        # hold point, the corridor — and `run_for` has none of that, only the
        # range to the thing it is running at. Both hand their room to
        # `rate_for`, so a berth and an asteroid cannot end up with different
        # ideas of what is stoppable.
        game = new_game("rates")
        conn, _why = free_sim.begin(game)
        for room, dv in ((10.0, 0.4), (100.0, 0.4), (10.0, 12.0)):
            longhand = math.sqrt(2.0 * dv * room * 1000.0 / conn_sim.TICK) * 0.66
            assert abs(auto_sim.rate_for(room, dv) - longhand) < 1e-9, (
                f"rate_for({room}, {dv}) is not the braking arithmetic")
        assert auto_sim.rate_for(0.0, 0.4) == 0.0
        assert auto_sim.rate_for(-5.0, 0.4) == 0.0, "negative room is not speed"
        # Four times the room is twice the rate: it is a square root, and a
        # linear cap here is exactly the bug that drove a hull into a quay.
        assert abs(auto_sim.rate_for(40.0, 0.4)
                   - 2.0 * auto_sim.rate_for(10.0, 0.4)) < 1e-9
        return (f"10 km at 0.4 m/s/tick -> {auto_sim.rate_for(10.0, 0.4):.2f} "
                f"m/s; 40 km -> {auto_sim.rate_for(40.0, 0.4):.2f}")

    @check("a captain can take the conn with nothing to approach")
    def _():
        game, conn = _flying()
        assert free_sim.is_free(conn)
        # The gate that used to refuse this, asked about the same ship: it
        # still refuses to *berth* on empty space, which is correct and is
        # not the same question.
        empty = next((c for c in track_sim.contacts(game)
                      if c.kind == "point"), None)
        if empty is not None:
            ok, why = berth_sim.can_conn(game, empty)
            assert not ok and "come alongside" in why, why
        # And the pad is live: a burn is a burn.
        had = conn.rcs
        conn_sim.apply(conn, "forward", main=True, throttle=1.0)
        assert conn.speed > 0.0, "the drive did nothing"
        assert conn.rcs < had, "the burn cost nothing"
        return (f"the conn opens on {conn.target.name} with "
                f"{had:.1f} t aboard; one burn makes {conn.speed:.1f} m/s")

    @check("nothing ends a free flight but the pilot")
    def _():
        # **The threshold trap.** A free flight opens at zero range against a
        # target of radius zero, so `r <= hull` is 0 <= 0 and every arrival
        # test in `sim/outcome` is true at once. Before this was handled the
        # first tick reported the ship as having struck open space.
        game, conn = _flying("stay")
        assert conn.range_km == 0.0 and conn.target.radius_km == 0.0
        for _ in range(600):
            conn_sim.apply(conn, "forward", main=True, throttle=1.0)
            if conn.over:
                break
        assert not conn.over, (
            f"the flight ended by itself: {conn.outcome!r} after "
            f"{conn.elapsed / 60:.0f} minutes")
        # Including a long way out, where an approach would have been "adrift".
        far = math.dist(conn.pos, (0.0, 0.0, 0.0))
        assert far > 1000.0, far
        # And past the range where the conn is the right instrument, the
        # screens say so rather than the sim stopping the ship. FAR_KM is a
        # piece of advice, not a wall: this flight is well beyond it and is
        # still flying.
        line = free_sim.standing(game, conn)
        assert far > free_sim.far_km(), (far, free_sim.far_km())
        assert "plot a transfer" in line, line
        near = free_sim.standing(game, _flying("near")[1])
        assert "plot a transfer" not in near, near
        said = free_sim.secure(game, conn)
        assert conn.over and conn.outcome == "secured", conn.outcome
        return (f"{far:,.0f} km out, past the {free_sim.far_km():,.0f} km the "
                f"screens advise, and still flying — “{said.split(',')[0]}”")

    @check("what was flown on the conn is where the ship has got to")
    def _():
        # The one door: `flight.ship_position` reads it, `flight.stand_off`
        # writes it, and a free flight has to land in exactly that state or
        # the flying is a screensaver.
        game, conn = _flying("moved")
        was = flight.ship_position(game)
        for _ in range(240):
            conn_sim.apply(conn, "forward", main=True, throttle=0.6)
        flew = math.dist(conn.pos, (0.0, 0.0, 0.0))
        free_sim.secure(game, conn)
        now = flight.ship_position(game)
        moved = math.dist(was, now) * KM_PER_AU
        assert flew > 50.0, flew
        # The conn flies in three dimensions and the sector is a plane, so
        # what lands is the part of the flight that was in it. Flown straight
        # ahead from a standing start, that is all of it.
        assert abs(moved - flew) < max(1.0, flew * 0.01), (
            f"flew {flew:,.0f} km and the ship moved {moved:,.0f}")
        assert getattr(game, "orbit_body", None) is None, (
            "a ship that has flown off on the conn is still recorded as "
            "alongside what it left")
        return (f"{flew:,.0f} km flown, {moved:,.0f} km moved, and the hull "
                "is standing off nothing")

    @check("a free flight is charged for, and the ledger says what it was")
    def _():
        game, conn = _flying("paid")
        had = float(game.ship.cargo.get("volatiles", 0))
        for _ in range(120):
            conn_sim.apply(conn, "forward", main=True, throttle=0.5)
        free_sim.secure(game, conn)
        out = berth_sim.commit(game, conn)
        left = float(game.ship.cargo.get("volatiles", 0))
        assert out["ok"] and out["fuel"] > 0.0, out
        assert abs((had - left) - out["fuel"]) < 0.005, (had, left, out)
        assert out["hours"] > 0.0, out
        assert out["moved"] is None, (
            "a free flight moored the ship to something")
        said = game.log[-1][1] if isinstance(game.log[-1], tuple) else ""
        assert "conn" in said.lower() and "flown" in said.lower(), said
        assert "broke off" not in said.lower(), (
            "a flight that went where it meant to was logged as a failure")
        return f"“{said}” — {had:.2f} t aboard, {left:.2f} t left"

    @check("handing over to the computer keeps the way on")
    def _():
        game, conn = _flying("hand")
        for _ in range(60):
            conn_sim.apply(conn, "forward", main=True, throttle=0.4)
        making = conn.speed
        assert making > 5.0, making
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        fresh, why = free_sim.hand_over(game, conn, quay)
        assert fresh is not None, why
        assert abs(fresh.speed - making) < 1e-6, (fresh.speed, making)
        assert fresh.target.name == quay.name
        assert not free_sim.is_free(fresh)
        return (f"{making:.1f} m/s on, handed to the computer at "
                f"{fresh.range_km:.1f} km off {fresh.target.name}, still "
                f"making {fresh.speed:.1f}")

    @check("a refused hand-over strands nobody and moves nothing")
    def _():
        # The ship is put back where it was standing. A hand-over that cannot
        # happen must not be a way of teleporting.
        game, conn = _flying("refuse")
        for _ in range(30):
            conn_sim.apply(conn, "forward", main=True, throttle=0.4)
        was = flight.ship_position(game)
        # Something genuinely out of reach: the conn is the last few
        # kilometres, and half a million km of planet is not that. There are
        # no "point" contacts in a fresh system, so asking for one picked
        # nothing and the check tested itself.
        far = max(track_sim.contacts(game),
                  key=lambda c: berth_sim.reach_to(game, c))
        assert berth_sim.reach_to(game, far) > berth_sim.REACH_KM, far.name
        fresh, why = free_sim.hand_over(game, conn, far)
        assert fresh is None and why, (fresh, why)
        assert math.dist(was, flight.ship_position(game)) < 1e-12, "moved"
        # **And the refusal that comes from the *structure*.** The one above
        # is turned away by `can_conn` before anything is written, so it can
        # never exercise the restore — a mutation deleting that restore
        # passed. A hostile hull gets past the ship's own gate and is refused
        # by the clearance, which is after the position has been stood off.
        import dataclasses
        near = next(c for c in track_sim.contacts(game)
                    if berth_sim.can_conn(game, c)[0] and c.kind == "hull")
        angry = dataclasses.replace(near, hostile=True)
        fresh, why = free_sim.hand_over(game, conn, angry)
        assert fresh is None and why, (fresh, why)
        now = flight.ship_position(game)
        assert math.dist(was, now) * KM_PER_AU < 1e-6, (was, now)
        assert not conn.over, "the free flight was ended by a refusal"
        return (f"{far.name} out of reach and {angry.name} refusing to clear "
                f"— “{why[:38]}…” — and the hull has not moved")

    @check("the window offers it, and the button says which act it will do")
    def _():
        # Read off the widgets, because the whole complaint was that the way
        # in did not exist. A label that says "break off" while the pad is on
        # a free flight would be the same fault in miniature.
        from ..ui.conn_window import open_conn
        from ..ui.window import MainWindow

        keep = _app()
        assert keep is not None
        game = new_game("freeui")
        flight.travel_to(game, 0)
        win = MainWindow(game)
        win.resize(1200, 820)
        panel = open_conn(win)
        assert panel.conn is not None
        assert not free_sim.is_free(panel.conn)
        before = panel.controls.free_btn.text()
        assert before == "Break off", before
        was = flight.ship_position(game)
        panel._free_flight()
        assert free_sim.is_free(panel.conn), "the window did not take the conn"
        after = panel.controls.free_btn.text()
        assert after == "Secure from the conn", after
        for _ in range(90):
            panel._burn("forward")
            if panel.conn.over:
                break
        flew = math.dist(panel.conn.pos, (0.0, 0.0, 0.0))
        panel._break_off()
        moved = math.dist(was, flight.ship_position(game)) * KM_PER_AU
        assert flew > 10.0 and abs(moved - flew) < max(1.0, flew * 0.02), (
            flew, moved)
        _shut(panel, win)
        return (f"“{before}” → “{after}”, {flew:,.0f} km flown by hand and "
                f"{moved:,.0f} km moved")


def _shut(*windows) -> None:
    """Close pop-outs before their parents.

    A window closed after the parent that owns it is a window being painted
    after Qt has taken its backing store away, which is a segfault rather than
    a failure.
    """
    for window in windows:
        try:
            window.close()
        except Exception:
            pass
