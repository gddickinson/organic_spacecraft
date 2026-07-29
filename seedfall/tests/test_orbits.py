"""Gravity that knows which star it is, and an orbit you choose the height of.

Two faults, one system.

**Every star weighed one Sun.** `flight.period_days` was `YEAR_AT_1AU · a^1.5`
— Kepler's third law with the `sqrt(M)` left out. The sector has had eight
spectral classes since it was written, and a world at one AU took the same
year round a 0.32-solar M dwarf as round an A-type nearly six times heavier.
That is a factor of 2.4 in where everything is on any given day, visible on
the helm chart and in every launch window.

**And there was one orbit.** `autopilot` circularised at whatever range the
transfer happened to drop you at, and `game.orbit_body` recorded *which* body
without a word about how far off — so the only number that decided the orbit
was where you arrived. A captain could not ask for a different one.

The claims:

- **A world's year is its star's.** Absolute, not "the table says what the
  table says": the classes really do differ, and the sky uses them.
- **Every height offered can be flown to**, and the ones withheld really are
  beyond the hull rather than merely declared so.
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
from ..data.starclasses import SOLAR_MU, STAR_CLASSES, mu_of
from ..sim import autopilot, conn as conn_sim, flight, orbits
from ..sim import track as track_sim
from .harness import Suite


class _OneAU:
    """A body at exactly one AU, for comparing star classes against."""

    id, name = "probe", "probe"
    orbit = (1.0 - flight.R_INNER) / (flight.R_OUTER - flight.R_INNER)


def _fly(game, contact, want_km: float, limit: int = 60000):
    """Take the conn and ask for an orbit at a height. Returns the conn."""
    conn = conn_sim.start(game, contact)
    conn.rcs = 99999.0                  # the fuel is checked elsewhere
    conn.orbit_want_km = want_km
    for _tick in range(limit):
        axis, main, throttle = autopilot.autopilot(conn, "orbit")
        conn_sim.apply(conn, axis, main, throttle)
        if conn.over:
            break
    return conn


def _bodies(game):
    """Every body in the system, with the contact that reaches it."""
    for index, body in enumerate(game.system.bodies):
        contact = next((c for c in track_sim.contacts(game, game.system)
                        if c.body_index == index), None)
        if contact is not None:
            yield index, body, contact


def run(suite: Suite) -> None:
    check = suite.check

    @check("a world's year is its star's, not the Sun's")
    def _():
        # The general one. Kepler's third law has a sqrt(M) in it and the
        # game left it out, so every star in the sector weighed exactly one
        # Sun as far as its planets were concerned.
        probe = _OneAU()
        years = {cid: flight.period_days(probe, spec.mass_solar * SOLAR_MU)
                 for cid, spec in STAR_CLASSES.items()}
        for cid, spec in STAR_CLASSES.items():
            assert spec.mass_solar > 0, cid
            # And the law itself, against the closed form rather than
            # against another call to the same function.
            a_au = flight.orbit_radius(probe)
            expect = flight.YEAR_AT_1AU * a_au ** 1.5 / math.sqrt(spec.mass_solar)
            assert abs(years[cid] - expect) < 1.0, (cid, years[cid], expect)

        assert years["M"] > years["A"] * 2.0, (
            f"a world at one AU takes {years['M']:,.0f} days round an M dwarf "
            f"and {years['A']:,.0f} round an A-type — the mass is not "
            "reaching the arithmetic")
        assert years["X"] < years["G"] * 0.5, (
            f"eight solar masses of black hole gives a {years['X']:,.0f}-day "
            f"year against a G-type's {years['G']:,.0f}")

        # And the sector uses it: bodies really are somewhere else.
        moved = same = 0
        for seed in range(4):
            game = new_game(f"kepler-{seed}")
            for system in game.galaxy.systems:
                for body in system.bodies:
                    real = flight.position(body, 400, mu_of(system))
                    solar = flight.position(body, 400, SOLAR_MU)
                    if math.dist(real, solar) > 0.01:
                        moved += 1
                    else:
                        same += 1
        assert moved > same * 0.3, (
            f"only {moved} of {moved + same} bodies sit anywhere different "
            "from where a one-solar-mass sector would put them")
        return (f"{years['M']:,.0f} days at one AU round an M dwarf against "
                f"{years['A']:,.0f} round an A-type and {years['X']:,.0f} "
                f"round a black hole; {moved} bodies moved")

    @check("every orbit height offered can actually be flown to")
    def _():
        # Measured by flying them, not by asserting the ladder is monotone.
        # Four control laws were tried before one worked at both ends of a
        # range that spans a four-kilometre comet and a fifty-thousand
        # kilometre gas giant, and each of the first three looked perfectly
        # reasonable written down.
        reached = missed = withheld = unsound = 0
        worst = 0.0
        for seed in ("orb-a", "orb-b", "orb-c"):
            game = new_game(seed)
            for _index, body, contact in _bodies(game):
                probe = conn_sim.start(game, contact)
                offered = orbits.heights_for(probe.target, probe.rcs_dv)
                withheld += len(orbits.ORBIT_HEIGHTS) - len(offered)
                for _hid, label, want in offered:
                    conn = _fly(game, contact, want)
                    got = orbits.semi_major_km(conn)
                    off = abs(got - want) / want
                    # Sound: an orbit at all, whether or not it is the one
                    # asked for. Aground, adrift or unbound is a different
                    # and much worse kind of failure.
                    if not orbits.in_orbit(conn) or conn.outcome in (
                            "aground", "adrift"):
                        unsound += 1
                        print(f"       UNSOUND {body.name} {label}: "
                              f"{conn.outcome or 'never resolved'} "
                              f"e={orbits.eccentricity(conn):.3f}")
                    if off <= 0.05 and conn.outcome == "orbit":
                        reached += 1
                        worst = max(worst, off)
                    else:
                        missed += 1
                        print(f"       short: {body.name} {label} asked "
                              f"{want:,.0f} got {got:,.0f} "
                              f"({100 * (got - want) / want:+.1f}%, "
                              f"e={orbits.eccentricity(conn):.3f}, "
                              f"{conn.outcome or 'never resolved'})")
        assert reached > 20, reached
        # Every offered height must yield a *sound* orbit — bound, clear of
        # the ground, and round. That part is absolute: an approach that ends
        # in a fall or a departure is a bug, and four control laws were tried
        # before none of them did.
        assert unsound == 0, (
            f"{unsound} offered heights ended in something that is not an "
            "orbit at all")
        # And all but one land within 5% of the height asked for. The
        # exception is measured rather than waved at: the high rung at a
        # 153 km asteroid settles into a round orbit (e = 0.049) at 94% of
        # the height, because circular speed there is forty-four metres a
        # second and the hull's thrusters move it half a metre at a time, so
        # the last few per cent of a fourfold climb costs more precision than
        # the ship has. Short of the mark and safe, which is the right way to
        # miss. Task #83 holds it.
        assert missed <= 1, (
            f"{missed} of {reached + missed} offered orbit heights came out "
            "more than 5% from the height asked for — one such case is known "
            "and recorded, more than one is a regression")
        assert withheld > 0, (
            "no height was ever withheld, so the holdability test is not "
            "doing anything and a comet is being offered orbits it cannot "
            "hold")
        return (f"{reached} of {reached + missed} heights flown to within "
                f"{worst:.1%}; every one a sound orbit; "
                f"{withheld} rungs withheld as unholdable")

    @check("a height withheld really is beyond the hull")
    def _():
        # The other half. A rule that withholds everything would pass the
        # check above trivially, so this flies the ones that were withheld
        # and asserts they do in fact fail — the claim is about the ship,
        # not about the predicate.
        tried = failed = 0
        for seed in ("orb-a", "orb-b", "orb-c"):
            game = new_game(seed)
            for _index, _body, contact in _bodies(game):
                probe = conn_sim.start(game, contact)
                offered = {h[0] for h in orbits.heights_for(probe.target,
                                                            probe.rcs_dv)}
                for hid, _label, _lift, _share in orbits.ORBIT_HEIGHTS:
                    if hid in offered:
                        continue
                    want = orbits.height_km(probe.target.radius_km, hid)
                    conn = _fly(game, contact, want, limit=20000)
                    tried += 1
                    got = orbits.semi_major_km(conn)
                    if conn.outcome != "orbit" or abs(got - want) > want * 0.05:
                        failed += 1
        assert tried > 0, "nothing was withheld, so there is nothing to check"
        assert failed >= tried * 0.8, (
            f"{tried - failed} of {tried} withheld heights turned out to be "
            "perfectly flyable — the hull is being denied orbits it could "
            "hold")
        return (f"{failed} of {tried} withheld heights could not be flown, "
                "as claimed")

    @check("a hull can turn to face dead astern")
    def _():
        # This was a real bug and nothing was holding it: `attitude.turned`
        # sweeps the shortest great circle, and to a point *exactly* opposite
        # there is no shortest one — every great circle between them is the
        # same length, so the perpendicular component is zero and the slerp
        # had nothing to sweep through. It returned the nose unchanged, for
        # ever. `conn.apply` spends a whole tick slewing and delivers no
        # thrust while it does, so a hull asked to reverse burned nothing and
        # turned nowhere until the approach ran out.
        #
        # Nothing in the game asked for a reversal until the orbit computer
        # did, which is why it went unnoticed — and why the mutation that
        # restores it was missed by every other check here.
        from ..sim import attitude as attitude_sim

        for nose in ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                     (0.6, -0.8, 0.0)):
            astern = tuple(-c for c in nose)
            moved = attitude_sim.turned(nose, astern, 0.4)
            assert attitude_sim.angle_between(moved, nose) > 0.35, (
                f"asked to reverse from {nose}, the nose did not move")
            # And it gets all the way round given enough time.
            at = nose
            for _step in range(20):
                at = attitude_sim.turned(at, astern, 0.4)
            assert attitude_sim.angle_between(at, astern) < 1e-6, (
                f"from {nose}, twenty swings still {attitude_sim.angle_between(at, astern):.3f} "
                "rad short of astern")

        # A quarter turn still works, which is the case that always did.
        side = attitude_sim.turned((0.0, 1.0, 0.0), (1.0, 0.0, 0.0), 0.5)
        assert abs(attitude_sim.angle_between(side, (0.0, 1.0, 0.0)) - 0.5) < 1e-6
        return "four hulls turned through 180°, and a quarter turn unaffected"

    @check("climbing to the orbit you asked for is not drifting away")
    def _():
        # `adrift` is measured against the range the approach opened at, and
        # at a small body the high rung is nearly four times that — so
        # climbing to the orbit the screen had just offered was reported as
        # losing the target astern. The yardstick is now whichever is further,
        # where we started or where we were told to go.
        #
        # Constructed rather than hoped for: the ship is placed beyond four
        # times its opening range, which is exactly the old limit, and asked
        # whether that is a lost approach.
        game = new_game("adrift")
        body = max(game.system.bodies, key=lambda b: b.radius_km)
        index = game.system.bodies.index(body)
        contact = next(c for c in track_sim.contacts(game, game.system)
                       if c.body_index == index)
        probe = conn_sim.start(game, contact)
        far = probe.start_km * (conn_sim.ADRIFT_MULTIPLE + 1.0)

        def place(want_km: float):
            """The same ship, in the same place, still climbing outward."""
            conn = conn_sim.start(game, contact)
            conn.orbit_want_km = want_km
            conn.pos = [0.0, -far, 0.0]
            # Radially outward, so this is not an orbit and cannot resolve as
            # one — both cases have to fall through to the adrift test, or the
            # comparison is between two different questions. A first draft gave
            # them circular velocity, and the control resolved as a perfectly
            # good orbit 227,000 km out, which it was.
            conn.vel = [0.0, -orbits.orbital_speed(conn, far) * 1.6, 0.0]
            conn_sim._resolve(conn)
            return conn.outcome

        told = place(far)
        stray = place(0.0)
        assert told != "adrift", (
            f"climbing to the {far:,.0f} km orbit it was told to hold, and "
            "the conn calls it a lost approach")
        assert stray == "adrift", (
            f"{far:,.0f} km out and opening with no orbit asked for reads as "
            f"{stray or 'still in progress'} — the limit has stopped meaning "
            "anything")
        return (f"{far:,.0f} km out and opening: '{told or 'still flying'}' "
                f"when that height was asked for, '{stray}' when it was not, "
                f"against an opening range of {probe.start_km:,.0f}")

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
                    conn_sim.apply(conn, axis, main, throttle)
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
