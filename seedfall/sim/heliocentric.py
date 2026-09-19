"""Where a body is: heliocentric orbits, one door each.

Split out of `sim/flight.py` at 498 lines. Flight is the helm — quoting a
burn, committing to it, what goes wrong on the way — and all of it asks the
same few questions of the sky: how far out a body's orbit lies, how long its
year is round *this* star, and where it is on a given day. Those answers are
here, with no game in them, and `flight` re-exports every name so the
screens and checks that have always read `flight.position` still do.
"""

from __future__ import annotations

import math

from ..data.starclasses import SOLAR_MU
from . import elements

#: Orbital radius in AU for a body's normalised orbit slot (0 inner, 1 outer).
R_INNER, R_OUTER = 0.4, 9.0

#: Days for a one-AU circular orbit, scaled by Kepler's third law from there.
YEAR_AT_1AU = 365.0


def semi_major(body) -> float:
    """The long half-axis of this body's orbit, in AU.

    Was `orbit_radius`, and the rename is the point: an orbit no longer
    *has* a radius. `body.orbit` places the ellipse; `sim/elements` gives it
    a shape, a tilt and a direction, and how far the body actually is from
    the star is now a question about a day (`distance_from_star`).
    """
    return R_INNER + (R_OUTER - R_INNER) * body.orbit


def period_days(body, star_mu: float) -> float:
    """A body's year, in days. Kepler's third law, with the mass put back.

    `T = 2π·sqrt(a³/mu)`, so `T ∝ a^1.5 / sqrt(M)`. The `sqrt(M)` was missing:
    the game had one period function for the whole sector and it quietly
    assumed every star weighed exactly one Sun. A world at one AU took the
    same year round a 0.32-solar M dwarf as round an A-type nearly six times
    heavier, when the real difference is a factor of 2.4 — visible on the helm
    chart, in every launch window, and in where anything is on any given day.

    `star_mu` is required rather than defaulted on purpose. A default is how
    half the call sites end up quietly assuming the Sun while the other half
    do it properly, which is the same two-doors-disagreeing fault this file
    has been bitten by before.
    """
    r = semi_major(body)
    scale = math.sqrt(SOLAR_MU / max(star_mu, 1.0))
    return max(30.0, YEAR_AT_1AU * (r ** 1.5) * scale)


def elements_of(body) -> elements.Elements:
    """This body's orbit. **One door**, so nothing derives a second one.

    Six elements where there used to be a radius. They are not stored: see
    `sim/elements`, which draws them off a stable hash of the body's own
    identity, so an old chronicle grows real orbits the moment it is loaded
    and the save does not gain a byte.
    """
    return elements.of(body, semi_major(body))


def position(body, day: float, star_mu: float) -> tuple:
    """Where a body is, in AU, on a given day, round a star of this mass.

    **Three dimensions now, and not a circle.** This used to be
    `r·cos θ, r·sin θ` with a constant radius, which made every orbit in the
    game the same orbit: circular, in one shared plane, all going the same way
    round. A player looking at the plotting board said so, and they were
    right — there was nothing else to draw.
    """
    return elements.at(elements_of(body), day, period_days(body, star_mu))


def distance_from_star(body, day: float, star_mu: float) -> float:
    """How far out the body actually is today — which now varies over its
    year, and is the number `semi_major` used to be mistaken for."""
    return math.dist(position(body, day, star_mu), (0.0, 0.0, 0.0))


def separation(a, b, day: float, star_mu: float) -> float:
    """AU between two bodies right now."""
    return math.dist(position(a, day, star_mu), position(b, day, star_mu))
