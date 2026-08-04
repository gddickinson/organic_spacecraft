"""Orbits with a shape, a tilt and a direction — and the claims that hold them.

Every orbit in the game used to be the same orbit. `flight.position` read one
element, the radius, and returned `r·cos θ, r·sin θ` for it, so every body in
every system ran a circle, in one plane, all the same way round. A player
looking at the plotting board said exactly that, and it was not a drawing
fault: there was nothing else to draw.

The claims here are the ones that make an orbit a path rather than a ring:

* a circle is the **special case**, reproduced exactly, and almost nothing is
  one any more;
* the near point and the far point are **real places**;
* equal areas in equal times — the second law, which is what makes an
  eccentric orbit a *speed* as well as a shape;
* an orbit keeps its own plane, and the planes are not one plane;
* past a right angle a body runs **the other way**;
* and the same body keeps the same orbit across interpreters and saves,
  because none of this is stored.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from ..core.state import new_game
from ..data import orbit_shapes as shapes
from ..data.starclasses import mu_of
from ..sim import elements, flight
from .harness import Suite

SEEDS = ("verge-7", "aurel", "kite", "mossbank", "det")


def _all_bodies():
    """Every body in five galaxies, with its orbit and its year."""
    for seed in SEEDS:
        game = new_game(seed)
        for system in game.galaxy.systems:
            mu = mu_of(system)
            for body in system.bodies:
                yield body, flight.elements_of(body), flight.period_days(
                    body, mu)


def _sweep(el, period, steps=1500):
    """Distances from the star over one whole year."""
    return [math.dist(elements.at(el, period * i / steps, period),
                      (0.0, 0.0, 0.0)) for i in range(steps)]


def run(suite: Suite) -> bool:
    check = suite.check

    @check("a circle is the special case, and almost nothing is one")
    def _():
        # Exactness first: with the elements zeroed this must reproduce the
        # old function to the last bit, because that is what makes it safe to
        # change every caller at once. A flat orbit is now a value, not a
        # second path through the code.
        flat = elements.Elements(a=2.5, e=0.0, incl=0.0, node=0.0, peri=0.0,
                                 m0=1.1)
        worst = max(
            abs(elements.at(flat, d, 700.0)[0]
                - 2.5 * math.cos(1.1 + math.tau * d / 700.0))
            for d in range(0, 700, 7))
        assert worst < 1e-9, f"the degenerate case drifted by {worst:.2e} AU"
        # And having proved the circle is reachable, prove it is rare.
        round_ones = sum(1 for _b, el, _T in _all_bodies() if el.e < 0.01)
        total = sum(1 for _ in _all_bodies())
        assert round_ones / total < 0.10, (
            f"{round_ones} of {total} orbits are still effectively circles")
        return (f"exact to {worst:.1e} AU · only {round_ones} of {total} "
                f"bodies still run a near-circle")

    @check("the near point and the far point are real places")
    def _():
        game = new_game("verge-7")
        mu = mu_of(game.system)
        widest, spread = None, 0.0
        for body in game.system.bodies:
            el = flight.elements_of(body)
            rs = _sweep(el, flight.period_days(body, mu))
            assert abs(min(rs) - el.perihelion) < 3e-3, (
                f"{body.name}: nearest {min(rs):.4f} against a stated "
                f"perihelion of {el.perihelion:.4f}")
            assert abs(max(rs) - el.aphelion) < 3e-3, (
                f"{body.name}: furthest {max(rs):.4f} against a stated "
                f"aphelion of {el.aphelion:.4f}")
            if el.aphelion - el.perihelion > spread:
                widest, spread = body, el.aphelion - el.perihelion
        assert spread > 0.05, "no body in the system varies its distance"
        el = flight.elements_of(widest)
        return (f"{widest.name} runs {el.perihelion:.2f}–{el.aphelion:.2f} AU "
                f"— {spread:.2f} AU of difference across its year")

    @check("equal areas in equal times")
    def _():
        # The second law is what makes eccentricity a *speed* and not only a
        # shape: a body must hurry at the near end. Without it an ellipse
        # would be a drawing, and a transfer window would still mean nothing.
        game = new_game("kite")
        mu = mu_of(game.system)
        body = max(game.system.bodies, key=lambda b: flight.elements_of(b).e)
        el = flight.elements_of(body)
        period = flight.period_days(body, mu)
        areas = []
        for k in range(8):
            swept, start = 0.0, period * k / 8
            for j in range(300):
                p = elements.at(el, start + period / 8 * j / 300, period)
                q = elements.at(el, start + period / 8 * (j + 1) / 300, period)
                cx = p[1] * q[2] - p[2] * q[1]
                cy = p[2] * q[0] - p[0] * q[2]
                cz = p[0] * q[1] - p[1] * q[0]
                swept += 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
            areas.append(swept)
        off = (max(areas) - min(areas)) / (sum(areas) / len(areas))
        assert off < 1e-3, f"areas swept differ by {off:.3%}"
        # And the speed really does vary, which is the point of the law.
        near = math.dist(elements.at(el, 0.0, period),
                         elements.at(el, 0.5, period))
        far = math.dist(elements.at(el, period / 2, period),
                        elements.at(el, period / 2 + 0.5, period))
        quick, slow = max(near, far), min(near, far)
        return (f"{body.name} (e={el.e:.2f}): areas equal to {off:.1e}, and "
                f"it travels {quick / slow:.2f}× faster at one end than the other")

    @check("an orbit keeps its own plane, and the planes are not one plane")
    def _():
        game = new_game("aurel")
        mu = mu_of(game.system)
        poles = []
        for body in game.system.bodies:
            el = flight.elements_of(body)
            period = flight.period_days(body, mu)
            pole = (math.sin(el.incl) * math.sin(el.node),
                    -math.sin(el.incl) * math.cos(el.node),
                    math.cos(el.incl))
            off = max(abs(sum(c * n for c, n in zip(
                elements.at(el, period * i / 60, period), pole)))
                for i in range(60))
            assert off < 1e-9, (
                f"{body.name} left its own plane by {off:.2e} AU")
            poles.append(pole)
        # Two bodies at the same tilt but different nodes are still in
        # different planes, so compare the poles rather than the angles.
        widest = max(
            math.degrees(math.acos(max(-1.0, min(1.0, sum(
                a * b for a, b in zip(p, q))))))
            for p in poles for q in poles)
        assert widest > 3.0, (
            f"every orbit in the system shares a plane to within {widest:.1f}°")
        return (f"{len(poles)} bodies, each true to its own plane; the two "
                f"most unlike are {widest:.1f}° apart")

    @check("past a right angle a body runs the other way")
    def _():
        backwards = [(b, el) for b, el, _T in _all_bodies() if el.retrograde]
        assert backwards, "not one body in five galaxies runs retrograde"
        # Direction is the sign of the angular momentum, and it must agree
        # with what the inclination says — one number carrying both, so they
        # cannot get out of step.
        for body, el in backwards[:12]:
            period = flight.period_days(body, 1.0)
            p = elements.at(el, 0.0, period)
            q = elements.at(el, 0.5, period)
            assert p[0] * q[1] - p[1] * q[0] < 0.0, (
                f"{body.name} is inclined {math.degrees(el.incl):.0f}° and "
                "still going round the same way as everything else")
        total = sum(1 for _ in _all_bodies())
        kinds = sorted({b.kind for b, _el in backwards})
        return (f"{len(backwards)} of {total} bodies run backwards "
                f"({len(backwards) / total * 100:.1f}%) — {', '.join(kinds)}")

    @check("nothing dives into the star, and nothing leaves the chart")
    def _():
        # The two bounds in the table exist because a comet at the outer edge
        # would otherwise swing to 17 AU — off every chart and out of every
        # quoted transfer — and one at the inner edge would pass through the
        # star. Both bite by lowering the eccentricity, never by moving the
        # orbit, so this also proves they are reached rather than decorative.
        worst_near, worst_far, trimmed = 9e9, 0.0, 0
        for body, el, _T in _all_bodies():
            worst_near = min(worst_near, el.perihelion)
            worst_far = max(worst_far, el.aphelion)
            # Whether a bound bit is a question about the *draw*, not about
            # the result: the cap lowers an eccentricity toward the range it
            # came from, so a trimmed orbit can still sit inside the table.
            shape = shapes.of(body.kind)
            ident = f"{body.id}|{body.name}"
            raw = elements._draw(f"ecc|{ident}", shape.e_lo, shape.e_hi)
            if el.e < raw - 1e-9:
                trimmed += 1
        assert worst_near >= shapes.PERIHELION_FLOOR_AU - 1e-6, (
            f"something passes {worst_near:.3f} AU of the star, inside the "
            f"floor of {shapes.PERIHELION_FLOOR_AU}")
        assert worst_far <= shapes.APHELION_CAP_AU + 1e-6, (
            f"something swings out to {worst_far:.2f} AU, past the cap")
        assert trimmed, "neither bound ever fired — they are decoration"
        return (f"closest approach {worst_near:.2f} AU · furthest "
                f"{worst_far:.2f} AU · {trimmed} orbits reined in")

    @check("the same body keeps the same orbit tomorrow")
    def _():
        # None of this is saved: the elements are drawn off a stable hash of
        # the body's identity, so an old chronicle grows real orbits on load
        # and no two screens can roll differently. The builtin `hash` is
        # salted per process and would break both — the fault `flight._phase`
        # was already written to avoid, and which is invisible inside one run.
        root = Path(__file__).resolve().parents[2]
        code = (
            f"import sys; sys.path.insert(0, {str(root)!r})\n"
            "from seedfall.core.state import new_game\n"
            "from seedfall.sim import flight\n"
            "g = new_game('determinism')\n"
            "print([(round(e.e, 9), round(e.incl, 9), round(e.node, 9))\n"
            "       for b in g.system.bodies\n"
            "       for e in [flight.elements_of(b)]])\n")
        seen = set()
        for salt in ("0", "1", "12345"):
            import os
            out = subprocess.run(
                [sys.executable, "-c", code],
                env=dict(os.environ, PYTHONHASHSEED=salt),
                capture_output=True, text=True, timeout=180)
            assert out.returncode == 0, out.stderr[-400:]
            seen.add(out.stdout.strip())
        assert len(seen) == 1, (
            f"one seed produced {len(seen)} different sets of orbits")
        return "identical elements across three interpreters"

    return True
