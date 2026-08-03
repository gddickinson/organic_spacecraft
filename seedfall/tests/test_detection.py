"""What the instruments actually see, and what hides from them.

The collision guard shipped omniscient: it read the sky, which is a perfect
noiseless list, so a raider "running dark" — a phrase `sim/traffic` has used
since it was written — was tracked exactly as precisely as a lit quay, by any
hull, at any range.

The claims here are the ones that make a sensor rating mean something at the
scale a collision happens on, and a countermeasure mean something at all:

* a world is never lost and a hull can be;
* a better array sees further, in proportion;
* what hides is *seen later*, in the order the table says;
* and the number that decides whether that matters is not the range but the
  **stopping distance** — a cloak beats your brakes before it beats your eyes.
"""

from __future__ import annotations

import dataclasses
import math

from ..core.state import new_game
from ..data import countermeasures as cm
from ..sim import collision
from ..sim import detection
from ..sim import freeflight as free_sim
from .harness import Suite


def _flight(seed="det"):
    game = new_game(seed)
    conn, why = free_sim.begin(game)
    assert conn is not None, why
    game.conn = conn
    conn.rcs = 60.0
    return game, conn


def _ahead(conn, km: float, look: str, name="Contact"):
    """Put one hull dead ahead at `km`, doing `look`, and aim at it."""
    seed = next(s for s in conn.sky if s.kind == "hull")
    unit = [0.0, 1.0, 0.0]
    rock = dataclasses.replace(
        seed, name=name, look=look, radius_km=0.08,
        at=tuple(p + u * km for p, u in zip(conn.pos, unit)))
    conn.sky = [rock]
    return rock, unit


def run(suite: Suite) -> bool:
    check = suite.check

    @check("a world is never lost, and a hull can be")
    def _():
        game, conn = _flight()
        # A planet at five thousand kilometres subtends degrees and a quay
        # squawks because being found is its job. A guard that could lose a
        # world is a guard nobody would believe about a raider.
        for kind in ("body", "anchorage", "star"):
            assert detection.always_seen(kind), kind
            assert detection.range_for(game, kind, "", "x") == float("inf")
        assert not detection.always_seen("hull")
        reach = detection.range_for(game, "hull", "trader", "Held Breath")
        assert reach < float("inf") and reach > 0, reach
        return f"worlds and quays unmissable; a lit hull at {reach:,.0f} km"

    @check("a better array sees further, in proportion")
    def _():
        game, conn = _flight()
        game.ship_stats.sensor = 2.0
        near = detection.range_for(game, "hull", "trader", "a")
        game.ship_stats.sensor = 6.0
        far = detection.range_for(game, "hull", "trader", "a")
        assert abs(far / near - 3.0) < 1e-6, (near, far)
        # And the flight is asked before the game, so the panel — which holds
        # a Conn and no Game — cannot read a different sky from the computer.
        conn.array = 2.0
        assert detection.range_for(game, "hull", "trader", "a", conn) == near, (
            "the flight's own array did not win over the ship's")
        return f"2.0 ly → {near:,.0f} km · 6.0 ly → {far:,.0f} km"

    @check("what hides is seen later, and in the order the table says")
    def _():
        game, conn = _flight()
        ranges = {c.id: detection.SENSOR_KM * detection.sensor_of(game) * c.share
                  for c in cm.ALL}
        assert (ranges["loud"] > ranges["dark"] > ranges["shrouded"]
                > ranges["cloaked"]), ranges
        # And it is not merely a number: a hull far enough out is simply not
        # on the plot, which is what running dark buys.
        rock, _unit = _ahead(conn, ranges["cloaked"] * 2.0, "raider", "Ghost")
        real = detection.hiding_of
        detection.hiding_of = lambda *a, **k: cm.CLOAKED
        try:
            assert detection.track(game, conn, rock.name, "hull", rock.at,
                                   rock.look) is None, "a cloak hid nothing"
            detection.hiding_of = lambda *a, **k: cm.LOUD
            assert detection.track(game, conn, rock.name, "hull", rock.at,
                                   rock.look) is not None, (
                "a transponding hull at the same range was lost")
        finally:
            detection.hiding_of = real
        return " · ".join(f"{k} {v:,.0f} km" for k, v in ranges.items())

    @check("a cloak beats the brakes before it beats the eyes")
    def _():
        # The number that decides whether a countermeasure matters is not the
        # detection range but the **stopping distance**: a contact seen with
        # less room than that is a contact you cannot do anything about.
        game, conn = _flight()
        stop = collision._stopping_km(conn, 300.0)
        told = {}
        for hiding in cm.ALL:
            reach = (detection.SENSOR_KM * detection.sensor_of(game)
                     * hiding.share)
            told[hiding.id] = reach > stop
        assert told["loud"] and told["dark"], told
        assert not told["cloaked"], (
            f"a cloaked hull is seen {told} — at 300 m/s, needing "
            f"{stop:,.0f} km to stop, it should not be in time")
        return (f"at 300 m/s she needs {stop:,.0f} km; cloaked shows at "
                f"{detection.SENSOR_KM * detection.sensor_of(game) * cm.CLOAKED.share:,.0f}")

    @check("the guard warns about what is tracked and nothing else")
    def _():
        game, conn = _flight()
        # Close enough that the arithmetic is frightening either way; the
        # only difference is whether the instruments hold it.
        # Beyond a cloak's reach but inside a transponder's, and fast enough
        # that the room left is less than the stopping distance either way.
        rock, unit = _ahead(conn, 800.0, "raider", "Ghost")
        conn.vel = [u * 260.0 for u in unit]
        real = detection.hiding_of
        try:
            detection.hiding_of = lambda *a, **k: cm.LOUD
            lit = collision.scan(game, conn)
            detection.hiding_of = lambda *a, **k: cm.CLOAKED
            hidden = collision.scan(game, conn)
        finally:
            detection.hiding_of = real
        assert lit is not None and lit.must_brake, lit
        assert hidden is None, (
            "a cloaked hull on a collision course raised a warning anyway")
        # And when it *is* tracked but poorly, the words say so.
        assert "Ghost" in collision.line(lit), collision.line(lit)
        return "lit: warned and braking · cloaked: nothing on the plot"

    @check("the same raider is the same raider tomorrow")
    def _():
        # The first draft rolled this off the builtin `hash`, which is salted
        # per process: a hull came up cloaked this session and dark the next,
        # and a chronicle reloaded was a different sky. Within one run that is
        # invisible, so the claim has to be made across an interpreter — the
        # same reason `core/rng` exists at all.
        import subprocess
        import sys
        ids = ["hull-3", "hull-17", "Kestrel", "42", "a"]
        code = ("from seedfall.sim import detection;"
                "print(','.join(detection.for_hull('raider', i).id for i in "
                f"{ids!r}))")
        runs = {subprocess.run([sys.executable, "-c", code],
                               capture_output=True, text=True,
                               cwd="/Users/george/claude_test/organic_spacecraft"
                               ).stdout.strip() for _ in range(3)}
        assert len(runs) == 1, f"three interpreters disagreed: {runs}"
        got = runs.pop()
        assert got and "," in got, got
        # And the table's odds are what actually comes out of the roll.
        seen = [detection.for_hull("raider", f"h{n}").id for n in range(6_000)]
        cloaks = seen.count("cloaked") / len(seen)
        shrouds = seen.count("shrouded") / len(seen)
        assert abs(cloaks - 1 / cm.CLOAK_IN) < 0.02, cloaks
        assert abs(shrouds - 1 / cm.SHROUD_IN) < 0.02, shrouds
        # An honest errand is never hiding, however the roll falls.
        assert all(detection.for_hull(e, f"h{n}") is cm.LOUD
                   for e in ("trader", "patrol", "courier", "prospector")
                   for n in range(50))
        return (f"stable across three interpreters · {cloaks * 100:.1f}% "
                f"cloaked, {shrouds * 100:.1f}% shrouded, honest hulls never")

    @check("a poor track is read pessimistically, not optimistically")
    def _():
        # A smear at the edge of the envelope is a real reading, and treating
        # it as exact is what kills you. The guard inflates the closing rate
        # it cannot trust, so a bad array warns early rather than late.
        game, conn = _flight()
        rock, unit = _ahead(conn, 400.0, "trader", "Smear")
        conn.vel = [u * 200.0 for u in unit]   # inside the stopping distance
        real = detection.hiding_of
        try:
            detection.hiding_of = lambda *a, **k: cm.LOUD
            conn.array = 60.0                    # a superb array: solid fix
            good = collision.scan(game, conn)
            conn.array = 0.11                    # barely reaches it at all
            poor = collision.scan(game, conn)
        finally:
            detection.hiding_of = real
        assert good is not None and poor is not None
        assert poor.closing > good.closing, (
            f"a poor fix read {poor.closing:.1f} m/s against a good one's "
            f"{good.closing:.1f} — it is not being read pessimistically")
        assert poor.room_km < good.room_km, (poor.room_km, good.room_km)
        assert "estimated" in collision.line(poor), collision.line(poor)
        return (f"good fix {good.closing:,.1f} m/s · poor fix "
                f"{poor.closing:,.1f} m/s, and the word 'estimated' with it")

    return True
