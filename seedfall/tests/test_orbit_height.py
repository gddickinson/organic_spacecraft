"""The height of an orbit: a real trade, quoted honestly, read the same way.

Split out of `tests/test_orbits.py` when it reached 567 lines. That file
holds gravity that knows which star it is and that every offered height can
be flown to; this one holds what choosing a height *means*:

- **The height is a trade**: low costs more to leave and resolves more, high
  the reverse, and the arithmetic is the same at a comet and a gas giant.
- **The forecast matches the act** — the fuel the helm quotes for leaving an
  orbit is the fuel the transfer spends.
- **The readout agrees with the sim** about whether this is an orbit.
- **An orbit's height is its semi-major axis**, not where the ship is on it.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import autopilot, conn as conn_sim, flight, orbits
from ..sim import track as track_sim
from .harness import Suite
from .test_orbits import _bodies


def run(suite: Suite) -> None:
    check = suite.check

    @check("the height of an orbit is a real trade")
    def _():
        # Low sees more and costs more to leave; high the reverse. Both from
        # the same geometry — the escape speed is sqrt(2mu/r), so `mu`
        # cancels and the ratio is pure radii.
        spread = []
        for seed in ("trade-a", "trade-b"):
            game = new_game(seed)
            for _index, body, _contact in _bodies(game):
                rungs = orbits.heights(body.radius_km)
                radii = [r for _h, _l, r in rungs]
                assert radii == sorted(radii), (body.name, radii)
                leave = [orbits.departure_factor(body.radius_km, r)
                         for r in radii]
                look = [orbits.look_factor(body.radius_km, r) for r in radii]
                # Strictly decreasing, not merely "sorted descending". A
                # mutation that made `look_factor` return a flat 1.0 sailed
                # through the sorted() form, because a constant list is
                # trivially sorted either way — which is a check that cannot
                # fail rather than a check that passes.
                for name, row in (("leave", leave), ("look", look)):
                    for a, b in zip(row, row[1:]):
                        assert a > b * 1.001, (
                            f"{body.name}: {name} goes {row} across the "
                            "ladder — the rungs are not a trade")
                assert abs(leave[1] - 1.0) < 1e-9, (
                    "the standard rung is the one everything else is "
                    "measured against and must cost exactly one")
                spread.append(leave[0] / leave[-1])
        assert min(spread) > 1.15, (
            f"the dearest orbit to leave is only {min(spread):.2f} times the "
            "cheapest — the choice is not worth making")

        # And the standard rung is where a transfer actually drops you, so
        # arriving is free and the other two are a piece of flying.
        from ..sim.targets import approach_range, target_from_body
        game = new_game("trade-a")
        for _index, body, _contact in _bodies(game):
            arrive = approach_range(target_from_body(body))
            standard = orbits.height_km(body.radius_km, "standard")
            assert abs(arrive - standard) < 1.0, (
                f"{body.name}: a transfer arrives at {arrive:,.0f} km and the "
                f"standard orbit is {standard:,.0f} — the ladder is not where "
                "the captain is")
        return (f"low costs {min(spread):.2f}–{max(spread):.2f}x what high "
                "does to leave; standard is exactly where you arrive")

    @check("the fuel quoted for leaving an orbit is the fuel it spends")
    def _():
        # The forecast against the act, which is the check this project has
        # needed in four other places. The lift belongs in `quote` precisely
        # so there is one number rather than two.
        game = new_game("leave")
        body = max(game.system.bodies, key=lambda b: b.radius_km)
        game.orbit_body = body.id
        other = next(i for i, b in enumerate(game.system.bodies)
                     if b.id != body.id)
        seen = {}
        for hid, _label, radius in orbits.heights(body.radius_km):
            game.orbit_alt_km = radius
            quoted = flight.quote(game, game.system.bodies[other])
            fresh = new_game("leave")
            fresh.orbit_body = body.id
            fresh.orbit_alt_km = radius
            fresh.ship.cargo["volatiles"] = 999
            before = fresh.ship.cargo["volatiles"]
            flight.travel_to(fresh, other, "standard")
            spent = before - fresh.ship.cargo["volatiles"]
            assert spent == quoted["fuel"], (
                f"{hid}: the helm quoted {quoted['fuel']} t and the transfer "
                f"spent {spent}")
            seen[hid] = (quoted["fuel"], quoted["departure_lift"])
        assert seen["low"][1] > seen["high"][1], seen
        # And the lift has to reach the *fuel*, not merely be reported beside
        # it. A mutation that computed the factor and never applied it passed
        # everything above, because the quote and the act agreed with each
        # other perfectly — they were both simply wrong.
        assert seen["low"][0] > seen["high"][0], (
            f"low orbit quotes {seen['low'][0]} t and high quotes "
            f"{seen['high'][0]} — the departure cost is being computed and "
            "then not charged")

        # The other half of the trade, measured where the game reads it: the
        # survey. `look_factor` returning a flat 1.0 was invisible until this.
        from ..sim import survey as survey_sim
        game.orbit_alt_km = orbits.height_km(body.radius_km, "low")
        close = survey_sim.look_bonus(game, body)
        game.orbit_alt_km = orbits.height_km(body.radius_km, "high")
        far = survey_sim.look_bonus(game, body)
        assert close > far * 1.05, (
            f"a survey from a low orbit resolves {close:.3f} against "
            f"{far:.3f} from a high one — the height buys nothing")
        return (" · ".join(f"{k}: {v[0]} t (x{v[1]:.2f})"
                           for k, v in seen.items())
                + f" · survey {close:.2f} low against {far:.2f} high")

    @check("the readout and the sim agree about what an orbit is")
    def _():
        # They disagreed the moment `in_orbit` started asking about the
        # ellipse rather than the instant: the conn reported an orbit made
        # and the panel beside it called the same tick a departure.
        disagreed = looked = 0
        for seed in ("agree-a", "agree-b", "agree-c"):
          game = new_game(seed)
          for _index, body, contact in _bodies(game):
            probe = conn_sim.start(game, contact)
            for _hid, _label, want in orbits.heights_for(probe.target,
                                                         probe.rcs_dv):
                conn = conn_sim.start(game, contact)
                conn.rcs = 99999.0
                conn.orbit_want_km = want
                for _tick in range(3000):
                    axis, main, throttle = autopilot.autopilot(conn, "orbit")
                    conn_sim.apply(conn, axis, main, throttle=throttle)
                    said = orbits.orbit_note(conn)
                    is_orbit = orbits.in_orbit(conn)
                    looked += 1
                    if is_orbit != said.startswith("Circular"):
                        disagreed += 1
                    if conn.over:
                        break
        assert looked > 500, looked
        assert disagreed == 0, (
            f"{disagreed} of {looked} ticks where the panel and the sim gave "
            "different answers about whether this is an orbit")
        return f"{looked} ticks, the panel and the sim agreeing on every one"

    @check("an orbit's height is its semi-major axis, not where the ship is")
    def _():
        # A ship on a slightly elliptical orbit at the right mean height is
        # in the orbit it asked for. Asked against the instantaneous range it
        # read several per cent out depending on which part you caught, and
        # the arrival never registered at all.
        game = new_game("ellipse")
        body = max(game.system.bodies, key=lambda b: b.radius_km)
        index = game.system.bodies.index(body)
        contact = next(c for c in track_sim.contacts(game, game.system)
                       if c.body_index == index)
        conn = conn_sim.start(game, contact)
        a = orbits.semi_major_km(conn)
        assert a > body.radius_km, (a, body.radius_km)

        # A circle: the axis is the range, and the eccentricity is nothing.
        conn.pos = [a, 0.0, 0.0]
        conn.vel = [0.0, math.sqrt(conn.target.mu / a) * 1000.0, 0.0]
        assert abs(orbits.semi_major_km(conn) - a) < a * 1e-6, (
            orbits.semi_major_km(conn), a)
        assert orbits.eccentricity(conn) < 1e-6, orbits.eccentricity(conn)
        assert orbits.in_orbit(conn)

        # An ellipse with the same axis, caught at periapsis: the range is
        # well short of the height, and the orbit is still that height.
        ecc = 0.03
        peri = a * (1 - ecc)
        conn.pos = [peri, 0.0, 0.0]
        conn.vel = [0.0, math.sqrt(conn.target.mu * (2 / peri - 1 / a)) * 1000.0,
                    0.0]
        assert abs(orbits.semi_major_km(conn) - a) < a * 1e-4, (
            orbits.semi_major_km(conn), a)
        assert abs(orbits.eccentricity(conn) - ecc) < 1e-3, (
            orbits.eccentricity(conn))
        assert conn.range_km < a * 0.98, (conn.range_km, a)
        assert orbits.in_orbit(conn), "a round orbit caught low is still one"

        # And a departure is not an orbit at any point of it.
        conn.vel = [0.0, math.sqrt(2.2 * conn.target.mu / peri) * 1000.0, 0.0]
        assert orbits.semi_major_km(conn) == float("inf") or \
            orbits.semi_major_km(conn) < 0, orbits.semi_major_km(conn)
        assert not orbits.in_orbit(conn)
        return (f"axis {a:,.0f} km held across a circle and an e={ecc} "
                f"ellipse whose range at periapsis reads "
                f"{100 * (1 - peri / a):.0f}% low")
