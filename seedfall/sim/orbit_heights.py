"""How high an orbit: the height ladder, and what each rung costs to climb.

Split out of `sim/orbits.py` at 485 lines. `orbits` answers *is this an
orbit* — circular speed, eccentricity, the band that counts as circular.
This answers *which one*: the rungs a captain may choose, the delta-v to
climb between them, which rungs a hull's thrusters can hold and which the
computer can honestly quote, and the trade a height is — dear to leave low
down, blind high up. `orbits` re-exports every name, so `orbits.heights_for`
and `orbits.climb_dv` answer where they always did.

`ORBIT_FLOOR_KM` and `ORBIT_ECCENTRICITY` are the shared definition of an
orbit and stay in `orbits`; they are read inside the three functions that
need them, because `orbits` imports this module and the other direction at
module scope is a cycle.
"""

from __future__ import annotations

import math

#: How many pulses of authority inside the eccentricity budget a rung needs
#: before `climb_dv` can be believed about it — and therefore before the conn
#: will sell it. This is not `holdable`, which asks whether the thrusters are
#: fine enough at all; it is the line above which the *quote* is honest.
#:
#: Measured by flying every rung of every body across five sectors on the tank a
#: NAVIS carries, and comparing what the climb spent against what `climb_dv`
#: said it would. Sorted by the ratio, the two regimes separate cleanly:
#:
#:      ratio   spend / ideal
#:       11.3       5.4x
#:       13.7      14.3x        <- overshot to 139% of the height
#:       18.0      11.2x
#:       25.7       9.1x        <- the worst offender that still arrived
#:      100.7       1.4x        <- and from here on, honest
#:      147.0       0.9x
#:      279.3       0.5x
#:
#: **The highest ratio that wasted is 25.7 and the lowest that did not is 100.7**,
#: so the line belongs between them and 60 sits with better than a factor of two
#: in hand on each side. A first draft put it at 25 — just under the worst
#: offender — and `test_climbs` caught it immediately: a rung quoted at 2.88 t
#: went on to eat 18.83 of a 20 t tank.
QUOTABLE = 60.0


# ── how high an orbit ──────────────────────────────────────────────────────
#
# There was one orbit, and it was wherever you happened to be when you asked
# for it: `autopilot` circularised at the current range and `game.orbit_body`
# recorded *which* body without a word about how far off. So every orbit in
# the game was the same orbit, and the only number that decided it was where
# the transfer happened to drop you.
#
# A height is worth choosing only if the choice costs something. It does, and
# the arithmetic is not invented: the speed you must throw away to leave is
# sqrt(2·mu/r), so a low orbit is dearer to leave than a high one by the
# square root of the ratio of their radii. That is the whole trade — low sees
# more and costs more to quit, high is cheap to hold and quit and shows you
# less.

#: The ladder, as (id, label, altitude above the orbit floor).
#:
#: Measured from the floor rather than from the surface, and additive rather
#: than multiplicative, because a rock and a gas giant differ by two hundred
#: times in radius and any single scheme keyed on one of them inverts on the
#: other. An asteroid's floor is 80 km up and a giant's is 80 km up; what
#: differs is how much room there is above it, which is what `share` reads.
#: The middle rung is `targets.approach_range` exactly — see `height_km`.
#: The outer two are as far apart as the physics allows: a body's surface is
#: at zero, so a low orbit can only ever be a little under the standard one,
#: while a high orbit can be most of a radius further out. That asymmetry is
#: not a design choice, it is where the ground is.
ORBIT_HEIGHTS = (
    ("low", "Low", 1.5, 0.02),
    ("standard", "Standard", 4.0, 0.10),
    ("high", "High", 20.0, 0.80),
)

#: The height an orbit is held at when nobody says otherwise.
DEFAULT_HEIGHT = "standard"

#: How sharply what you can see falls off with height.
#:
#: Well under 1. The honest optical figure is 1 — resolved ground scale is
#: linear in range — but a low orbit is already about 2.4 times closer than a
#: high one at a world, and a linear benefit would make a low orbit strictly
#: correct every time for a tenth more fuel. At 0.45 a low orbit resolves
#: about a fifth more than standard and a high one about a fifth less, which
#: is worth choosing between rather than obvious.
LOOK_EXPONENT = 0.45


def height_km(radius_km: float, height_id: str) -> float:
    """The radius from the body's centre, in km, for a named height.

    `radius + max(floor · lift, radius · share)`, which is deliberately the
    same shape as `targets.approach_range` — and the standard rung is exactly
    it, so **a transfer drops you at the standard orbit** and low and high
    are each a real piece of flying away from it.

    That matching is the whole of why this is written the way it is. A first
    draft scaled the ladder off the orbit floor alone, which put a comet's
    three heights at 97, 108 and 151 km when the transfer arrives at 335 —
    every rung below where the ship starts, all three within a whisker of
    each other, and the autopilot chasing a descent it could not fly. The two
    formulae have to agree or the ladder is somewhere the captain is not.

    Monotone by construction: both terms only grow along the ladder.
    """
    from .orbits import ORBIT_FLOOR_KM
    radius_km = max(0.0, radius_km)
    for hid, _label, lift, share in ORBIT_HEIGHTS:
        if hid == height_id:
            return radius_km + max(ORBIT_FLOOR_KM * lift, radius_km * share)
    return radius_km + max(ORBIT_FLOOR_KM * 4.0, radius_km * 0.10)


def heights(radius_km: float) -> list[tuple[str, str, float]]:
    """Every height for a body: (id, label, radius from centre in km)."""
    return [(hid, label, height_km(radius_km, hid))
            for hid, label, _lift, _share in ORBIT_HEIGHTS]


def holdable(mu: float, r_km: float, pulse: float) -> bool:
    """Could a ship whose thrusters come in `pulse`-sized lumps hold this?

    Not every body can be orbited to order. A four-kilometre comet has a
    circular speed of about two metres a second; a hull's attitude clusters
    move it half a metre at a time. Asking such a ship to hold a particular
    orbit there is asking it to steer with an instrument coarser than the
    thing being steered, and it cannot be done — measured, every comet under
    twenty kilometres failed to reach any height asked of it, at every gain
    and every control law tried.

    The bound is derived rather than fitted. An orbit counts as one below
    `ORBIT_ECCENTRICITY`, which at circular speed `v` is a velocity budget of
    `v · e`; the ship needs at least a couple of pulses of authority inside
    that budget to converge on it rather than clatter across it. So
    `v · e ≥ 2 · pulse`.

    **This is about the thrusters and nothing else.** Whether the *tank* is big
    enough is a different question with a different answer — see `heights_for`,
    which asks both. Folding fuel in here was tried and `test_orbits` refused it:
    those rungs are flyable given mass, so a predicate about fineness must not
    deny them.
    """
    from .orbits import ORBIT_ECCENTRICITY
    if mu <= 0 or r_km <= 0:
        return False
    v = math.sqrt(mu / r_km) * 1000.0
    return v * ORBIT_ECCENTRICITY >= 2.0 * max(pulse, 1e-9)


#: What the quote is multiplied by before it is compared with the tank.
#:
#: `climb_dv` is the ideal figure and the computer is not ideal. Measured over
#: every offered rung of every body across seven sectors, flying each one on the
#: tank a NAVIS carries and comparing the mass gone with the ideal:
#:
#:      2.03x   <- the worst, Quill Rise II low
#:      0.67x
#:      0.65x
#:      0.53x
#:      0.46x   <- the median: most climbs cost *less* than the ideal, because
#:      0.46x      an arrival's axis is already part of the way there
#:      ...
#:      0.00x   <- and some are already inside `HEIGHT_TOLERANCE`
#:
#: One case in twelve came out over the ideal and it came out at twice it, so a
#: promise of "no more than this" has to clear 2.03. **A first draft said 1.4 and
#: `test_climbs` caught it on that very rung** — quoted 2.54 t, spent 3.69.
#: 2.5 clears the worst by a fifth, and what is left over is deliberate: a hull
#: that arrives with an empty tank has to be *given* a way out, which is the
#: whole of task #83.
CLIMB_MARGIN = 2.5


#: How near the height you asked for counts as being at it, as a share of that
#: height. Wide enough that the ship settles instead of hunting.
#:
#: It lived in `sim/autopilot.py`, which spends it, and belongs here, which owns
#: the ladder — because the *price* of a rung has to stop at the same line the
#: *flying* stops at. It did not, and `test_climbs` found the consequence at
#: once: `quotable` refused the standard rung at sixteen bodies of thirty-nine,
#: and the standard rung is where a transfer arrives. A captain was being told
#: they could not afford to circularise where they already were.
HEIGHT_TOLERANCE = 0.02


def climb_dv(mu: float, from_km: float, to_km: float) -> float:
    """What moving between two orbits costs, in m/s.

    The thrust-limited figure, `|v_circ(from) − v_circ(to)|`, and not a
    Hohmann's two burns. That is not an approximation of the wrong thing: the
    conn's computer flies a continuous law with attitude clusters, which is a
    spiral, and a spiral costs the difference of the circular speeds. Measured
    against a Hohmann at the same rungs, the two are within 1.3% of each other
    at these ratios, and the spiral figure is the one the flights matched.
    """
    if mu <= 0 or from_km <= 0 or to_km <= 0:
        return 0.0
    if abs(from_km - to_km) <= to_km * HEIGHT_TOLERANCE:
        return 0.0                          # already there; nothing to sell
    return abs(math.sqrt(mu / from_km) - math.sqrt(mu / to_km)) * 1000.0


def heights_for(target, pulse: float, budget_dv: float | None = None,
                from_km: float | None = None) -> list[tuple[str, str, float]]:
    """The heights *this* ship can actually hold at *this* body.

    What the conn should offer. Where nothing is holdable the answer is an
    empty list, and the honest thing for a screen to say is that this body
    cannot be orbited to order — which is not a failure, it is a four
    kilometre lump of ice.

    **Two questions, and until now this asked only the first.** `holdable` asks
    whether the thrusters are *fine* enough to settle on a rung. `budget_dv`
    asks whether the tank is *big* enough to get there, which is a different
    thing entirely and was nobody's job. Measured: the high rung at a 4,179 km
    world costs 1,419 m/s and a NAVIS carries about 450, so the conn offered a
    climb no starting hull could make — and a captain found out by spending the
    whole tank to arrive at 71% of the height, with nothing left to leave on.

    Pass `budget_dv` (m/s in the tank) and `from_km` (where the ship is now) to
    have the offer refuse what cannot be paid for. Omit them and the answer is
    the old one, which is what a screen wants when it means to show the ladder
    rather than the choice.
    """
    mu = getattr(target, "mu", 0.0)
    out = [row for row in heights(getattr(target, "radius_km", 0.0))
           if holdable(mu, row[2], pulse)]
    if budget_dv is None or from_km is None:
        return out
    kept = []
    for row in out:
        dv = climb_dv(mu, from_km, row[2])
        if dv <= 0:
            kept.append(row)                # the rung the ship is already on
        elif quotable(mu, row[2], pulse) and dv * CLIMB_MARGIN <= budget_dv:
            kept.append(row)
    return kept


def quotable(mu: float, r_km: float, pulse: float) -> bool:
    """Can `climb_dv` be believed about this rung, on these thrusters?

    See `QUOTABLE`. A rung under the line is one where the computer's spend is
    not the quote but some multiple of it, so a conn that offered it would be
    selling a price it cannot hold to.
    """
    from .orbits import ORBIT_ECCENTRICITY
    if mu <= 0 or r_km <= 0:
        return False
    v = math.sqrt(mu / r_km) * 1000.0
    return v * ORBIT_ECCENTRICITY >= QUOTABLE * max(pulse, 1e-9)


def nearest_height(radius_km: float, r_km: float) -> str:
    """Which rung of the ladder a given radius is closest to."""
    return min(heights(radius_km), key=lambda row: abs(row[2] - r_km))[0]


def departure_factor(radius_km: float, r_km: float) -> float:
    """What leaving costs from here, against leaving from a standard orbit.

    `sqrt(2·mu/r)` is the speed you must find to escape, so the ratio between
    two orbits is the square root of the inverse ratio of their radii — and
    `mu` cancels, which is why this needs only the geometry. A low orbit runs
    about a tenth dearer and a high one about a quarter cheaper.
    """
    standard = height_km(radius_km, DEFAULT_HEIGHT)
    if r_km <= 1e-6 or standard <= 1e-6:
        return 1.0
    return math.sqrt(standard / r_km)


def look_factor(radius_km: float, r_km: float) -> float:
    """How much better this height sees than a standard orbit does.

    The other half of the trade, and the reason to pay the departure cost. A
    survey run from close in resolves more than one run from a long way out,
    which is not a game rule so much as an optical one.
    """
    standard = height_km(radius_km, DEFAULT_HEIGHT)
    if r_km <= 1e-6 or standard <= 1e-6:
        return 1.0
    return (standard / r_km) ** LOOK_EXPONENT
