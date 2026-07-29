"""Flight and helm checks.

The helm claims two things the code did not used to do: that a seed grows one
fixed system, and that the ship aims at where a body *will be* rather than
where it is. These hold both to account, and check that a course cannot be
plotted through the middle of a star.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

from ..core.state import new_game
from ..data.starclasses import mu_of
from ..sim import flight
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("orbits are the same in every process, not just this one")
    def _():
        # Python randomises str hashing per process, so a phase derived from
        # hash() moved every planet on every launch — including between saving
        # a game and loading it. Two interpreters, two hash seeds, one answer.
        root = Path(__file__).resolve().parents[2]
        script = (
            "import sys; sys.path.insert(0, %r)\n"
            "from seedfall.core.state import new_game\n"
            "from seedfall.data.starclasses import mu_of\n"
            "from seedfall.sim import flight\n"
            "g = new_game('determinism')\n"
            "print([round(v, 6) for b in g.system.bodies\n"
            "       for v in flight.position(b, g.day, mu_of(g.system))])\n" % str(root)
        )
        seen = []
        for hashseed in ("0", "1", "12345"):
            env = dict(os.environ, PYTHONHASHSEED=hashseed)
            out = subprocess.run([sys.executable, "-c", script], env=env,
                                 capture_output=True, text=True, timeout=120)
            assert out.returncode == 0, out.stderr[-400:]
            seen.append(out.stdout.strip())
        assert len(set(seen)) == 1, (
            f"same seed, {len(set(seen))} different sets of orbital positions")
        return f"identical across 3 hash seeds ({len(seen[0])} chars)"

    @check("a transfer aims where the body will be, not where it is")
    def _():
        g = new_game("lead")
        # The body that moves most while you fly to it makes the point.
        best, gap = None, 0.0
        for body in g.system.bodies:
            q = flight.intercept(g, body, "coast")
            if q["lead"] > gap:
                best, gap = body, q["lead"]
        assert best is not None
        q = flight.intercept(g, best, "coast")
        assert gap > 0.05, f"nothing moves enough to test with (best {gap:.3f} AU)"

        # The aim point must be where the body actually is on arrival.
        truth = flight.position(best, q["arrival_day"], mu_of(g.system))
        miss = math.hypot(q["aim"][0] - truth[0], q["aim"][1] - truth[1])
        assert miss < 1e-6, f"aim point misses the body by {miss:.4f} AU"

        # And it must differ from a naive shot at the body's present position.
        now = flight.position(best, g.day, mu_of(g.system))
        naive = math.hypot(q["aim"][0] - now[0], q["aim"][1] - now[1])
        assert naive > 0.05, "the aim point is just the current position"
        return f"{best.name}: leads {gap:.2f} AU over {q['days']} d"

    @check("the intercept solve converges instead of chasing its tail")
    def _():
        worst, solves = 0, 0
        for seed in ("a", "b", "c", "d"):
            g = new_game(seed)
            for index in range(min(5, len(g.galaxy.systems))):
                g.system_id = g.galaxy.systems[index].id
                for body in g.system.bodies:
                    for burn in flight.BURNS:
                        q = flight.intercept(g, body, burn.id)
                        worst = max(worst, q["passes"])
                        solves += 1
        assert worst < 7, f"an intercept never settled ({worst} passes)"
        return f"{solves} solves, worst {worst} passes"

    @check("no course is plotted through the middle of a star")
    def _():
        # A chord between two points at similar radii always sags inward, so
        # the promise is not "never dips" — it is that the course clears the
        # star by a real margin instead of flying through it, and that going
        # the long way round costs the distance it should.
        bent = worst_ratio = 0
        worst = None
        for seed in ("a", "b", "c"):
            g = new_game(seed)
            for index in range(min(4, len(g.galaxy.systems))):
                g.system_id = g.galaxy.systems[index].id
                sx, sy = flight.ship_position(g)
                for body in g.system.bodies:
                    q = flight.intercept(g, body, "coast")
                    legs, (tx, ty) = q["legs"], q["aim"]
                    clear = min(flight.HOT_RADIUS, math.hypot(sx, sy),
                                math.hypot(tx, ty))
                    near = min(flight._closest_approach(ax, ay, bx, by)
                               for (ax, ay), (bx, by) in zip(legs, legs[1:]))
                    ratio = near / clear if clear else 1.0
                    if worst is None or ratio < worst_ratio:
                        worst, worst_ratio = body.name, ratio
                    assert ratio > 0.55, (
                        f"the course to {body.name} passes {near:.3f} AU from "
                        f"the star, well inside its {clear:.2f} AU clearance")
                    direct = math.hypot(tx - sx, ty - sy)
                    if len(legs) > 2:
                        bent += 1
                        assert q["au"] > direct + 1e-9, (
                            "a course bent around the star that costs nothing")
                    assert q["detour"] >= -1e-9, "a detour that saves distance"
        return (f"{bent} courses bent round the star; tightest pass "
                f"{worst_ratio:.0%} of clearance ({worst})")

    @check("flying somewhere actually puts you there")
    def _():
        g = new_game("arrive")
        target = max(range(len(g.system.bodies)),
                     key=lambda i: flight.orbit_radius(g.system.bodies[i]))
        body = g.system.bodies[target]
        g.ship.cargo["volatiles"] = 400
        before = g.day
        res = flight.travel_to(g, target, "standard")
        assert res["ok"], res.get("why")
        assert not res.get("dead"), "died on a routine transfer"
        assert g.orbit_body == body.id, "the burn did not arrive"
        assert g.day > before, "the transfer took no time"
        return f"{body.name} in {g.day - before} d"
