"""Where a free flight thinks it is, and which way it is pointing.

Split out of `tests/test_freeflight.py` when it passed five hundred lines.
The seam is a real one: the other file is about *flying* — the computer
closing, handing over, being refused, and the ledger paying for it. This one
is about the **frame**: that one place is one place however it is asked for,
that closing is measured on the mark rather than on the place she left, and
that a course can point out of the plane at all.

That last claim is the newest and the one that had never been made. Every
orbit shared a plane until `sim/elements`, so "Ahead" pointing only across
the plane cost nothing and nobody noticed the heading had no second angle.
"""

from __future__ import annotations

import math

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import conn as conn_sim
from ..sim import engage as engage_sim
from ..sim import flight
from ..sim import freeflight as free_sim
from ..sim import track as track_sim
from .harness import Suite


def run(suite: Suite) -> bool:
    check = suite.check

    @check("where the ship is agrees with the conn's own range, in either frame")
    def _():
        # **One fact, two answers, and the wrong one fed `engage.range_km`.**
        # `conn.pos` is an offset from the frame's origin: where she let go in
        # a free flight, and the *target* in an approach — where
        # `flight.ship_position` is not written again until
        # `berthing.commit`. Measured before the fix, with the ship stood off
        # 10,164 km from a quay and then given the conn on it: `where` said
        # 10,152 km and `conn.range_km` said 12.0. It read right on a fresh
        # game only because the ship is moored *at* the quay's body, so the
        # two origins coincide — which is why nothing had caught it.
        import math
        from ..sim import berthing as berth_sim
        from ..sim import targets as targets_sim

        seen = {}
        for kind in ("anchorage", "hull", "body"):
            game = new_game("frames")
            # Stand well off first, so the two origins cannot coincide.
            fly, why = free_sim.begin(game)
            assert fly is not None, why
            for _ in range(400):
                conn_sim.apply(fly, "forward", main=True, ticks=1)
            free_sim.secure(game, fly)

            target = next((c for c in track_sim.contacts(game)
                           if c.kind == kind), None)
            assert target is not None, f"no {kind} to approach"
            conn, why = berth_sim.begin(game, target)
            assert conn is not None, f"{kind}: {why}"
            assert not free_sim.is_open(conn.target), kind

            here = free_sim.where(game, conn)
            there = track_sim.at(game, target, game.day)
            km = math.dist(here, there) * free_sim.KM_PER_AU
            assert abs(km - conn.range_km) < 1.0, (
                f"{kind}: where puts her {km:,.1f} km off and the conn says "
                f"{conn.range_km:,.1f}")
            # And the range everything else asks for agrees.
            assert abs(engage_sim.range_km(game, conn, target)
                       - conn.range_km) < 1.0, kind
            seen[kind] = km

        # A free flight still measures from where she let go, unchanged.
        game = new_game("frames")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        for _ in range(50):
            conn_sim.apply(conn, "forward", main=True, ticks=1)
        sx, sy, sz = flight.ship_position(game)
        want = (sx + conn.pos[0] / free_sim.KM_PER_AU,
                sy + conn.pos[1] / free_sim.KM_PER_AU,
                sz + conn.pos[2] / free_sim.KM_PER_AU)
        assert free_sim.where(game, conn) == want, (
            "a free flight no longer measures from where she was let go")

        # A hull target keeps what is needed to find it again — it used to
        # drop the id, so nothing could ask where the target was.
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        made = targets_sim.target_from_contact(game, hull)
        assert made.hull_id == hull.hull_id and made.hull_id, (
            f"a hull target carries hull_id={made.hull_id!r}")
        return " · ".join(f"{k} {v:,.0f} km" for k, v in seen.items())

    @check("closing is measured on the mark, not on the place she left")
    def _():
        # **`Conn.closing` is the wrong number out here.** It is measured
        # against the conn's origin, which in a free flight is where she was
        # let go — so a ship braking hard onto a contact reads as *opening* on
        # the place she came from, which is true and useless.
        game = new_game("closing")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")

        assert abs(free_sim.closing_on(game, conn, hull)) < 1e-6, (
            "a ship at rest is closing on something")

        # Burn at it and the rate is positive; burn away and it is negative,
        # and `conn.closing` disagrees because it is answering a different
        # question.
        free_sim.steer(game, conn, hull)
        for _ in range(40):
            conn_sim.apply(conn, "forward", main=True, ticks=1)
        toward_it = free_sim.closing_on(game, conn, hull)
        assert toward_it > 1.0, f"burned at it and closing reads {toward_it}"

        for _ in range(120):
            conn_sim.apply(conn, "back", main=True, ticks=1)
        away = free_sim.closing_on(game, conn, hull)
        assert away < -1.0, f"burned away and closing reads {away}"

        # And the range agrees with the sign, which `conn.closing` need not.
        was = engage_sim.range_km(game, conn, hull)
        for _ in range(30):
            conn_sim.apply(conn, None, ticks=1)
        now = engage_sim.range_km(game, conn, hull)
        assert now > was, (f"closing said {away:,.1f} m/s (opening) and the "
                           f"range went {was:,.0f} -> {now:,.0f} km")
        return (f"at rest 0, burning at it {toward_it:+,.0f} m/s, "
                f"burning away {away:+,.0f}")

    @check("a course can point out of the plane, not only across it")
    def _():
        # `Conn.heading` is one angle about the vertical, so "Ahead" could
        # only ever lie in the orbital plane — free while every orbit was in
        # that plane, and wrong the moment `sim/elements` tilted them.
        # Measured on the flight deck before `Conn.pitch`: a course laid on a
        # contact 15.4° up left the nose 15.4° under it, and five hundred
        # burns on the torch closed 5,952 km to 1,514 and sailed past.
        import math
        game = new_game("pitchtest")
        conn, why = free_sim.begin(game)
        assert conn is not None, why
        game.conn = conn
        steepest, lean = None, 0.0
        for contact in track_sim.contacts(game):
            if contact.kind == "star":
                continue
            vec = free_sim.toward(game, conn, contact)
            flat = math.hypot(vec[0], vec[1])
            if flat > 1e-9:
                up = abs(math.degrees(math.atan2(vec[2], flat)))
                if up > lean:
                    steepest, lean = contact, up
        assert steepest is not None and lean > 3.0, (
            f"nothing in this sky is off the plane (best {lean:.1f}°)")
        free_sim.steer(game, conn, steepest)
        assert abs(math.degrees(conn.pitch)) > 3.0, (
            f"a course laid on something {lean:.1f}° off the plane set a "
            f"pitch of {math.degrees(conn.pitch):.1f}°")
        # And "ahead" now really points at it: the drive pushes along the
        # nose, and the nose is what `apply` swings onto the asked heading.
        want = conn_sim.rotate((0.0, 1.0, 0.0), conn.heading, conn.pitch)
        aim = free_sim.toward(game, conn, steepest)
        span = math.dist(aim, (0.0, 0.0, 0.0))
        off = math.degrees(math.acos(max(-1.0, min(1.0, sum(
            w * a / span for w, a in zip(want, aim))))))
        assert off < 1.0, f"ahead points {off:.1f}° away from the mark"
        return (f"{steepest.name} is {lean:.1f}° off the plane; the course "
                f"pitches {math.degrees(conn.pitch):+.1f}° and lies {off:.2f}° "
                f"off the bearing")

    return True
