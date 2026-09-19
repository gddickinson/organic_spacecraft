"""Standing off: a structure that does not want you, leaving.

Split out of `sim/control.py` (487 lines) with the section it already had.
`control` decides what the structure has told you and how far up the ladder
it has gone; this is what it *does* at the rung where words run out and it
has no guns to back them — it works itself away. `control` re-exports every
name, so `control.sheer_step` and `control.SHEER_RATE` answer where they
always did.

`has_control` and `welcome` are imported inside `sheers`, not at the top:
`control` imports this module to re-export it, so the other direction at
module scope is a cycle.
"""

from __future__ import annotations

import math

# The measure a structure has when it has no guns, and takes as well when it
# does: it is simply not there when you arrive. `sim/knock` already holds
# "and then it was shoved" as a velocity with a date on it, read by `track.at`
# — the one door for where anything is — so a station that sheers off is off
# station on the plot, in the readiness board's ranges and in every forecast,
# because all of them ask the same function.

#: How fast a structure will work itself away from a hull it does not want,
#: in metres a second.
#:
#: Slow, because a station is enormous and this is station-keeping thrust
#: rather than a manoeuvre. At half a metre a second an hour's stubbornness
#: opens 1.8 km — real against a twelve-kilometre approach, and catchable by
#: a captain willing to spend the mass. Being unwelcome should cost fuel
#: rather than be forbidden.
SHEER_RATE = 0.5

#: The rung at which a structure starts moving. It warns first: sheering off
#: without a word would read as the station being broken.
SHEER_FROM = 2


def sheers(conn) -> bool:
    """Is this structure working itself away from the hull?

    Only one that has somebody aboard to do it. A Weave anchor does not sheer
    off, and neither does a derelict — `knock.keeps_station` is the same
    question asked of a shove, and the same answer serves.
    """
    from .control import has_control, welcome
    if welcome(conn) or not has_control(conn):
        return False
    return int(getattr(conn, "told", 0)) >= SHEER_FROM


def sheer_step(conn, seconds: float) -> float:
    """Open the range by what the structure managed this tick, in km.

    In the approach's frame the structure is the origin, so its moving away
    is the hull's position growing. Applied to the position rather than the
    velocity on purpose: the station is not pushing the ship, it is leaving,
    and a hull that stops burning simply finds the berth further off than it
    was.
    """
    if not sheers(conn):
        return 0.0
    from . import moorings
    gone = SHEER_RATE * float(seconds) / 1000.0
    here = math.dist(conn.pos, (0.0, 0.0, 0.0))
    if here <= 1e-9:
        return 0.0
    grew = (here + gone) / here
    conn.pos = [c * grew for c in conn.pos]
    conn.sheered = round(getattr(conn, "sheered", 0.0) + gone, 6)
    # A berth that is running from you is not a berth you are at.
    moorings.boom_step(conn, 0.0)
    return gone


def sheer_line(conn) -> str:
    """What a pilot watching the range open is being told."""
    gone = float(getattr(conn, "sheered", 0.0))
    if gone <= 0.0:
        return ""
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    return (f"{station} is under way and opening the range — {gone * 1000:,.0f} m "
            "so far. Whatever you meant to tie up to is leaving.")
