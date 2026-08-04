"""Where a thing on an orbit actually is: six elements and Kepler's equation.

**Every orbit in the game was the same orbit.** `flight.position` read one
element — the radius — and returned `r·cos θ, r·sin θ` for it, so every body
in every system ran a perfect circle, in one shared plane, all the same way
round. A player looking at the plotting board saw it immediately: *every
object in the system is orbiting the sun in the same way*. It was not a
drawing fault. There was nothing else to draw.

Six elements, and each answers a question the old model could not be asked:

* **a** — how far out, which is all there used to be.
* **e** — what shape. Distance from the star now varies over the year, so
  perihelion and aphelion are real places and a transfer's cost depends on
  *when* you fly it.
* **i** — how steeply the plane is tilted. Past a right angle the body runs
  the other way round, so "different directions" is this number and not a
  flag beside it — which is how the sky reports it, and it means a retrograde
  orbit cannot get out of step with its own inclination.
* **Ω** — where the tilted plane cuts the reference one.
* **ω** — where the ellipse's near point sits within that plane.
* **M₀** — where the body was on day zero. This one already existed, as
  `flight._phase`, derived from a stable hash rather than stored; the other
  five follow it exactly.

**Nothing here is saved.** `data/orbit_shapes.py` states the range each kind
of body keeps and the elements are drawn off `rng.hash_seed` of the body's
own identity — so a chronicle saved last week grows real orbits the moment it
is loaded, no migration, and two screens asking about one body get one answer
because neither of them rolled anything.

The degenerate case is exact, deliberately: at `e=0, i=0, Ω=0, ω=0` this
returns precisely the circle the old function did. Flat orbits are a special
case of the model rather than a second path through it, which is what makes
the change safe to make everywhere at once.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..core.rng import hash_seed
from ..data import orbit_shapes as shapes

#: How hard the solver tries before it accepts what it has. Kepler's equation
#: has no closed form; Newton converges in a handful of steps for the near
#: circles most bodies keep, and needs the room at a comet's eccentricity.
SOLVER_STEPS = 64
SOLVER_CLOSE = 1e-13

#: Above this eccentricity, Newton is seeded at π rather than at M. Seeded at
#: M a very eccentric orbit can step outside the bracket and take a long walk
#: back; this is the standard remedy and it costs nothing on a round orbit.
HARD_ECCENTRICITY = 0.8


@dataclass(frozen=True)
class Elements:
    """One orbit, in the frame the system is drawn in."""

    a: float          #: semi-major axis, AU
    e: float          #: eccentricity, 0 (a circle) to just under 1
    incl: float       #: inclination, radians — past π/2 is retrograde
    node: float       #: longitude of the ascending node, radians
    peri: float       #: argument of periapsis, radians
    m0: float         #: mean anomaly on day zero, radians

    @property
    def retrograde(self) -> bool:
        return self.incl > math.pi / 2

    @property
    def perihelion(self) -> float:
        """The near point, in AU. A real place now, not a synonym for `a`."""
        return self.a * (1.0 - self.e)

    @property
    def aphelion(self) -> float:
        return self.a * (1.0 + self.e)

    @property
    def note(self) -> str:
        """One phrase for a board: shape, tilt and sense."""
        return (f"{self.perihelion:.2f}–{self.aphelion:.2f} AU · "
                f"{math.degrees(self.incl):.1f}° · "
                f"{shapes.sense_of(self.incl)}")


def _draw(key: str, lo: float, hi: float) -> float:
    """A stable number in a range, off the body's identity.

    `hash_seed` rather than the builtin, for the reason `flight._phase` was
    already using it: Python salts `hash()` per process, so the same seed
    grew the same galaxy and then scattered its orbits on every launch.
    """
    return lo + (hash_seed(key) % 100_000) / 100_000.0 * (hi - lo)


def of(body, a: float) -> Elements:
    """The orbit this body keeps. Derived, never stored.

    `a` is passed rather than read because the mapping from a body's `orbit`
    field to AU belongs to `sim/flight` and always has; this module is about
    the shape of the path, not where the scale comes from.
    """
    ident = f"{getattr(body, 'id', '?')}|{getattr(body, 'name', '')}"
    shape = shapes.of(getattr(body, "kind", ""))
    e = shapes.bounded(_draw(f"ecc|{ident}", shape.e_lo, shape.e_hi), a)
    incl = math.radians(_draw(f"incl|{ident}", shape.incl_lo, shape.incl_hi))
    return Elements(
        a=a, e=e, incl=incl,
        node=_draw(f"node|{ident}", 0.0, math.tau),
        peri=_draw(f"peri|{ident}", 0.0, math.tau),
        # The phase `flight._phase` has always used, unchanged and by the same
        # key, so a body that used to sit at a given angle on day zero still
        # starts there — the orbit under it is what has changed.
        m0=(hash_seed(f"{getattr(body, 'id', '?')}|"
                      f"{getattr(body, 'name', '')}") % 3600) / 3600.0
        * math.tau,
    )


def eccentric_anomaly(mean: float, e: float) -> float:
    """Solve `M = E − e·sin E` for E. Newton, from a safe seed."""
    m = (mean + math.pi) % math.tau - math.pi
    ecc = m if e < HARD_ECCENTRICITY else math.copysign(math.pi, m or 1.0)
    for _ in range(SOLVER_STEPS):
        step = ((ecc - e * math.sin(ecc) - m)
                / max(1e-12, 1.0 - e * math.cos(ecc)))
        ecc -= step
        if abs(step) < SOLVER_CLOSE:
            break
    return ecc


def at(el: Elements, day: float, period: float) -> tuple:
    """Where this orbit puts a body on a day, in AU, in three dimensions.

    The period is asked for rather than worked out here: Kepler's third law
    needs the star's mass, `sim/flight.period_days` already knows it, and a
    second copy of that arithmetic is how two screens start disagreeing about
    what year it is.
    """
    mean = el.m0 + math.tau * (day / max(1e-9, period))
    ecc = eccentric_anomaly(mean, el.e)
    nu = 2.0 * math.atan2(math.sqrt(1.0 + el.e) * math.sin(ecc / 2.0),
                          math.sqrt(1.0 - el.e) * math.cos(ecc / 2.0))
    r = el.a * (1.0 - el.e * math.cos(ecc))
    u = el.peri + nu
    cn, sn = math.cos(el.node), math.sin(el.node)
    cu, su = math.cos(u), math.sin(u)
    ci, si = math.cos(el.incl), math.sin(el.incl)
    return (r * (cn * cu - sn * su * ci),
            r * (sn * cu + cn * su * ci),
            r * (su * si))


def path(el: Elements, steps: int = 96) -> list:
    """The whole orbit as points, for a chart to draw.

    Stepped in *true* anomaly rather than in time, so the near end of a long
    ellipse — where a body is moving fastest and the curve is tightest — gets
    the same number of points as the far end, and a comet's turn round the
    star is drawn as a curve rather than a corner.
    """
    out = []
    for k in range(steps + 1):
        nu = math.tau * k / steps
        r = (el.a * (1.0 - el.e * el.e)
             / max(1e-9, 1.0 + el.e * math.cos(nu)))
        u = el.peri + nu
        cn, sn = math.cos(el.node), math.sin(el.node)
        cu, su = math.cos(u), math.sin(u)
        ci, si = math.cos(el.incl), math.sin(el.incl)
        out.append((r * (cn * cu - sn * su * ci),
                    r * (sn * cu + cn * su * ci),
                    r * (su * si)))
    return out
