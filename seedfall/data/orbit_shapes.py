"""What shape of orbit each sort of body keeps, and how far off the plane.

Every orbit in the game was a circle. `sim/flight.position` was
`r·cos θ, r·sin θ` with a constant `r` and an angle that only ever increased,
so every body in every system was on the same circular, coplanar, prograde
track — differing in nothing but radius. A player looking at the plotting
board said so: *every object in the system is orbiting the sun in the same
way*, which was exactly true.

A shape is a range rather than a number, because two rocky worlds should not
be identical either. `sim/elements.py` draws from these ranges off a stable
hash of the body's own identity — never stored, so an existing chronicle
grows real orbits the moment it is loaded and the save does not gain a byte.

**The ordering is the astronomy.** Planets keep nearly circular orbits close
to the plane because that is what is left after a disc settles. Asteroids are
scattered. Comets are the ones that were *thrown* — steep, eccentric, and
often going round the wrong way, which is the single most legible sign that
an orbit is a history rather than a diagram.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Shape:
    """The range of orbits a kind of body keeps.

    Angles in degrees, because that is how an astronomer says them and how
    the checks read; `sim/elements` turns them into radians once.
    """

    e_lo: float
    e_hi: float
    incl_lo: float
    incl_hi: float
    blurb: str


#: **Every bound below is a real body, so none of it is a taste.** The first
#: draft was tuned by eye and came out timid — a median eccentricity of 0.064
#: and 2.4° of tilt, which is defensible astronomy and still reads as one
#: circle on a chart. The Solar System is bolder than that, and quoting it is
#: how these numbers can be argued with rather than merely preferred.

#: Rocky and wet worlds. The top of the range is **Mercury** (e=0.206,
#: i=7.0°), the bottom nearer Earth (e=0.017, i=0.0°).
PLANET = Shape(0.01, 0.15, 0.5, 7.0,
               "Settled — a near circle close to the plane.")
#: Gas giants, the most placid things in any system: **Jupiter** is e=0.049,
#: i=1.3°, and **Neptune** e=0.009, i=1.8°.
GIANT = Shape(0.00, 0.09, 0.3, 3.0,
              "Placid — the roundest orbits in the system.")
#: The cold ones, which is where the tilt starts to tell: **Pluto** is
#: e=0.249, i=17.2°.
ICY = Shape(0.02, 0.25, 1.0, 17.0, "Cold, and tilted with it.")
#: Bodies of a size that got pushed about while things were settling.
MINOR = Shape(0.02, 0.20, 1.0, 12.0, "Nudged — noticeably off the plane.")
#: Rubble that never settled, and shows it: **Pallas** is e=0.231, i=34.8°.
RUBBLE = Shape(0.05, 0.35, 0.0, 31.0,
               "Scattered — an eccentric track well off the plane.")
#: Thrown, and about half of them running backwards. Conservative against the
#: real thing: **Halley** is e=0.967 at i=162°, which is retrograde.
THROWN = Shape(0.45, 0.90, 5.0, 165.0,
               "Thrown — a long ellipse steeply out of the plane, and as "
               "likely as not running against the traffic.")

BY_KIND = {
    "rocky": PLANET, "ocean": Shape(0.01, 0.13, 0.5, 6.0, PLANET.blurb),
    "gas": GIANT, "ice": ICY,
    "moon": MINOR, "asteroid": RUBBLE, "comet": THROWN,
}

#: Anything not named above. A body kind added tomorrow gets a sane orbit
#: rather than a circle, and the check that reads this table will say so.
DEFAULT = PLANET

#: **Two bounds the ranges above are allowed to want but not to have.**
#:
#: An eccentricity is drawn against the body's own semi-major axis, and a
#: comet at the outer edge with e=0.88 would swing to 17 AU — off the chart,
#: out of every quoted transfer, and a body nobody could reach. The far one
#: is a cap on aphelion; the near one keeps a perihelion out of the star,
#: which at 0.4 AU an e of 0.9 would not. Both bite by *lowering the
#: eccentricity* of the orbit that wanted too much, never by moving it.
APHELION_CAP_AU = 14.0
PERIHELION_FLOOR_AU = 0.12


def of(kind: str) -> Shape:
    return BY_KIND.get(kind or "", DEFAULT)


def bounded(e: float, a: float) -> float:
    """The most eccentricity this axis may keep, given the two bounds."""
    if a <= 0.0:
        return 0.0
    far = max(0.0, APHELION_CAP_AU / a - 1.0)
    near = max(0.0, 1.0 - PERIHELION_FLOOR_AU / a)
    return max(0.0, min(e, far, near))


def retrograde(incl_deg: float) -> bool:
    """Going round the other way — which is inclination past a right angle,
    rather than a flag of its own. One number carries both "how tilted" and
    "which way", the way the sky actually reports it."""
    return incl_deg > 90.0


def sense_of(incl: float) -> str:
    """What a board calls the direction, from an inclination in radians."""
    return "retrograde" if incl > math.pi / 2 else "prograde"
