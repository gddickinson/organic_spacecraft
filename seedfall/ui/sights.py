"""Which contacts get a name in a window, and the bearing to each.

**One door, because two windows ask the same question.** The player's report
was that the Pilot screen showed nothing of what was out there while the Conn
drew its target properly; `ui/viewport_mark.draw_sights` fixed the Pilot half.
Measured afterwards on the Conn, standing 130.3 km off the Fleet Hub with
Ashkeep Gate I at the same range and a hull 4,726 km out: `screen.sights` was
`()` and `screen.mark` was `None`. A starfield, the system star, and an unnamed
crosshair. The same complaint, in the other window.

The choosing lives here and the drawing lives in `ui/viewport_mark`, so a
screen that wants names asks for them rather than working out its own rules —
which is how the two came to disagree in the first place.
"""

from __future__ import annotations

from ..sim import engage as engage_sim
from ..sim import freeflight as free_sim

#: How many of the nearest contacts are considered for a name.
#:
#: Not how many are drawn: `viewport_mark.draw_sights` drops any that would
#: overprint one already placed, and the "In view" board lists every one with
#: its range regardless. This only bounds the work.
CONSIDERED = 8

#: What is worth naming. Worlds are left out because `Viewport._sky` already
#: draws those as lit discs and nobody loses a planet.
NAMED = ("anchorage", "hull")


def _key(thing):
    """What identifies a contact or a target across the two frames."""
    return getattr(thing, "id", None) or getattr(thing, "name", None)


def out_there(game, conn, rows, skip=(), limit: int = CONSIDERED) -> list:
    """`(bearing, name, within_reach)` per contact worth naming, nearest first.

    `rows` is `(km, contact)` nearest first, as `ui/fire_panel.ranged` returns
    it. The bearing is `freeflight.toward`, which is an offset in kilometres
    rather than a unit vector — `viewport_math.project` divides through, so
    magnitude does not matter and a contact at zero range projects to nothing
    rather than to the middle of the screen.

    **Nothing the window already names is named again.** Rendered on the Conn's
    aft camera at 130.3 km, the first draft printed "Fleet Hub" as a sight
    directly on top of `Viewport._target`'s reticle, which reads "Fleet Hub ·
    130.3 km" — one thing wearing its name twice, a pixel apart. The target is
    dropped here rather than at each call site, because it is *this* function's
    business to know what a sight is for; `skip` carries the rest, which today
    means the contact a course is laid on, drawn as a ring by
    `viewport_mark.draw`.
    """
    named = {_key(c) for c in skip if c is not None}
    if conn is not None and not free_sim.is_free(conn):
        named.add(_key(getattr(conn, "target", None)))
    return [(free_sim.toward(game, conn, c), c.name,
             km <= engage_sim.reach_km())
            for km, c in rows[:limit]
            if c.kind in NAMED and _key(c) not in named]
