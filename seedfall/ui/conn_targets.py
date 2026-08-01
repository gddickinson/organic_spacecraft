"""Which contact the conn should open on.

Split out of `ui/conn_window.py` when that file went past five hundred lines,
along a real seam rather than an arbitrary one: *what to fly at* is a policy
question, and the window around it is plumbing. The Pilot screen (#137) needs
the same answer for what to show and what to offer, so this is a door two
screens can share rather than a private helper of one.

`conn_window` re-exports it, because that is where two checks import it from
and moving a name is not the point of a split.
"""

from __future__ import annotations

from ..sim import berthing as berth_sim
from ..sim import track as track_sim


#: What to conn when the captain has not said. Ordered by what a pilot at
#: close quarters would actually be looking at.
#:
#: A station is what you dock with, and it is the thing worth watching come
#: up in the windows. Standing alongside the Fleet Hub, the first draft of
#: this opened the conn on **the planet** — because `track.contacts` lists
#: bodies before anchorages and the window took the first row in reach. You
#: are already in orbit of the body; approaching it is not a manoeuvre.
#:
#: The body came last on the reasoning that approaching what you are already
#: orbiting is not a manoeuvre. That was true when an orbit had no height.
#: It is not true now — see `orbits.ORBIT_HEIGHTS` — so a world you are
#: standing at is something a captain can act on, and it outranks a stranger's
#: hull that happens to be passing.
DEFAULT_ORDER = ("anchorage", "body", "hull")


def default_target(game):
    """The most useful thing in reach to open an approach on.

    **Where the ship actually is comes first.** Traffic drifts, and once
    bodies moved onto their real orbits a passing freighter could easily be
    the nearest thing in the system — so the conn opened on `Patient Ledger`
    while the hull sat in orbit around a world it was not being shown. Anything
    co-located with the ship wins, in the order above; only then does the rest
    of the system get a look in.
    """
    reachable = [c for c in track_sim.contacts(game)
                 if c.kind != "star" and berth_sim.can_conn(game, c)[0]]
    here_id = getattr(game, "orbit_body", None)
    index = next((i for i, b in enumerate(game.system.bodies)
                  if b.id == here_id), None) if here_id else None

    def at_the_ship(contact) -> bool:
        return index is not None and contact.body_index == index

    for group in (True, False):
        pool = [c for c in reachable if at_the_ship(c) is group]
        for kind in DEFAULT_ORDER:
            found = [c for c in pool if c.kind == kind]
            if found:
                return found[0]
    return None
