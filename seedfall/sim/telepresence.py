"""How far away a machine is, and how much of it survives the delay.

Split out of `sim/robots.py` when that went past five hundred lines, along the
seam the file had drawn for itself — its own banner read "── the law ──", and
this is the whole of what was under it.

**The one physical fact in the machine rules.** A hand you are driving from
orbit is not the hand you would have standing beside it: light takes time, and
what the delay costs depends on how much of the work the machine can do
without being told. `grip` is that trade, `gap_au` is the distance the trade is
paid over, and `effective` is the two multiplied — everything the roster does
about capability reads it and nothing computes it twice.

**It is a leaf, deliberately.** `gap_au` needs the station markers and
`ward_from` needs the roster, and both are imported *inside* the function
rather than at the top: `sim/robots` imports this module at module level, so
the seam runs one way and neither file has to be loaded before the other.
"""

from __future__ import annotations

import math

from ..world import galaxy
from . import flight

#: Seconds of round trip at which each autonomy level has lost half its worth.
#:
#: Moved here with `grip`, its only reader. `ABOARD` and `STOWED` stayed in
#: `sim/robots`, where eight other functions read them.
HALF_LIFE_S = {1: 4.0, 2: 1_200.0, 3: 21_600.0, 4: 31_557_600.0}

#: The share of a level's work that needs nobody, and so never decays.
STANDING = {1: 0.0, 2: 0.05, 3: 0.25, 4: 0.60}

#: Light, in seconds per AU, and AU per light year: the delay is real.
LIGHT_S_PER_AU = 499.005
AU_PER_LY = 63_241.077

#: Inside this, a machine and its supervisor are in the same place.
ALONGSIDE_AU = 1e-6


import math


# ── the law ────────────────────────────────────────────────────────────────

def grip(autonomy: int, lag_s: float) -> float:
    """How much of a machine's level survives the delay to its supervisor.

    Two parts, and the second is the one the first draft was missing. What it
    does **on its own account** never goes away — `STANDING` — and the rest is
    the share that needed you, which decays with the round trip.

    A hyperbola rather than an exponential for that second part, deliberately:
    teleoperation does not fall off a cliff at some latency, it gets steadily
    and unboundedly worse, and a hand at 4% is a hand you can still watch
    failing. Alongside, every rung is whole; out of contact, every rung falls
    to exactly what it can do by itself.
    """
    rung = int(autonomy)
    half = HALF_LIFE_S.get(rung, HALF_LIFE_S[2])
    alone = STANDING.get(rung, STANDING[2])
    return alone + (1.0 - alone) / (1.0 + max(0.0, float(lag_s)) / half)


def gap_au(game, robot) -> float:
    """How far this machine is from the ship, in AU.

    Aboard is zero. A holding in this system is the distance from the hull to
    the body it sits on — which moves, because both of them are in orbit. A
    holding in another system is measured across the sector and comes out in
    light *years* converted to AU, which is the honest answer and a brutal one.
    """
    from .robots import ABOARD, STOWED   # a leaf: see the module note
    posting = robot.posting or STOWED
    if posting in (ABOARD, STOWED):
        return 0.0
    colony = _colony_of(game, robot)
    if colony is None:
        return 0.0
    if colony.system_id == game.system.id:
        body = next((b for b in game.system.bodies if b.id == colony.body_id),
                    None)
        if body is None:
            return 0.0
        gap = flight.distance_to(game, body)
        # Alongside is alongside. Without this a machine on the very body the
        # hull is holding station over pays grip for a few hundred kilometres
        # of orbit, which is a lag of about a millisecond and reads on the
        # panel as a teleoperated frame mysteriously below its rating.
        return 0.0 if gap < ALONGSIDE_AU else gap
    from ..world import galaxy
    here = game.system
    there = next((s for s in game.galaxy.systems if s.id == colony.system_id),
                 None)
    if there is None:
        return 0.0
    return galaxy.distance(here, there) * AU_PER_LY


def lag_seconds(game, robot) -> float:
    """The round trip, in seconds. Out and back, because an order needs both."""
    return 2.0 * gap_au(game, robot) * LIGHT_S_PER_AU


def effective(game, robot) -> float:
    """What this machine is actually worth where it is standing.

    Its level, through its autonomy at this distance, through how worn it is.
    A broken one is worth nothing at all, which is the point of `BROKEN_AT`.
    """
    if robot.broken:
        return 0.0
    klass = robot.definition
    return klass.level * grip(klass.autonomy, lag_seconds(game, robot)) \
        * robot.condition


#: What one point of effective machine is worth as a colony's ward.
#:
#: Sized against the thing it stands beside: a `garrison` work is worth 0.28,
#: so at 0.03 a level-3 machine standing right there is worth 0.09 and three
#: of them come to about one garrison. Machines supplement infrastructure;
#: they do not replace it.
WARD_PER_POINT = 0.03

#: The duty a machine needs before it is any use defending a place. Four of
#: the twenty carry it, and the data already draws the line this feature is
#: about: `loader` is level 3, teleoperated, 1,800 credits, and `servitor` is
#: level 3, goal-directed, 9,000. Five times the price for autonomy, and
#: until now the two defended a holding equally well — which is to say,
#: neither of them did.
GUARD_DUTY = "ground"


def ward_from(game, system_id: int) -> float:
    """What the machines posted in this system add to its defence.

    **The one door**, and the reason `sim/robots.grip` finally reaches
    something that is not colony piecework. A machine left to guard a holding
    is worth what it can do *at the distance its supervisor is standing*: a
    teleoperated hand is worth almost nothing the moment the ship leaves
    orbit, and a goal-directed one is worth the same in the next system as it
    is alongside.

    Measured, a level-3 guard at each rung, in ward:

        alongside   E1 0.090   E2 0.090   E3 0.090   E4 0.090
        0.5 AU      E1 0.001   E2 0.065   E3 0.088   E4 0.090
        another system         E2 0.005   E3 0.027   E4 0.090

    That is the whole of "the controller is the objective", and it is a
    strategic law and not a tactical one — see `test_swarm`, which measures
    what light-lag does at combat range and finds it does nothing at all.
    """
    total = 0.0
    from .robots import owned            # a leaf: see the module note
    for robot in owned(game):
        colony = _colony_of(game, robot)
        if colony is None or not colony.online:
            continue
        if colony.system_id != system_id:
            continue
        if GUARD_DUTY not in robot.definition.duties:
            continue
        total += effective(game, robot)
    return total * WARD_PER_POINT


def _colony_of(game, robot):
    posting = robot.posting or ""
    if not posting.startswith("colony:"):
        return None
    want = posting.split(":", 1)[1]
    return next((c for c in getattr(game, "colonies", [])
                 if str(c.id) == want), None)


