"""What the pilot has set on the console, and what it comes to on this hull.

`sim/conn.py` has taken a `throttle` since the drive learned to throttle, and
`apply` has taken `ticks` since it was written. **Neither was ever reachable
from the conn.** The window fired `apply(conn, axis, main=self.use_main)` and
nothing else, so the pilot's main drive was a switch: full power, one minute.

That is the exact fault the *autopilot* was fixed for. `conn.apply` still
carries the note — "one tick of a fusion torch on a SPORE is 124 m/s, so the
computer lit it to trim ten, overshot, corrected the overshoot, and never
converged" — and the answer was to let the computer throttle. The human was
left with the firework. Measured on the hulls as they are built: a SPORE under
a Fusion Torch moves **41.9 m/s per press**, so nulling ten metres a second of
drift needs 0.24 of a press. There is no way to ask for that.

So: a throttle, and a coast. Two controls, because `apply` does two things and
they are not the same thing —

- **`throttle`** is how hard the one impulse is. The clusters are pulsed rather
  than throttled, which is `conn.thrust_axis`'s business and not changed here,
  so the throttle governs the main drive only.
- **`coast_min`** is how many minutes of flight to let run afterwards. `apply`
  fires once and *then* steps time `ticks` times — it is one burn followed by a
  coast, not a longer burn — so calling this a burn length would be a lie about
  what the button does.

`quote` is the only door for "what will this do", so the tooltip on a button
cannot drift from the act behind it. That is not hypothetical: `conn._copy`
dropped a field three times and the forecast lied by a little each time.
"""

from __future__ import annotations

from .conn import MAIN_COST, RCS_COST, Conn
from .thrusters import TRIM_COST_SHARE

#: The throttle settings offered, as fractions of full power.
#:
#: Four rungs rather than a continuous slider, because the useful range is
#: decided by the hull and not by the pilot's patience: on the hulls in the
#: game the finest correction wanted is around a tenth and the coarsest is
#: everything. A tenth of a Fusion Torch on a SPORE is 4.2 m/s, which is the
#: order of a berthing correction; a tenth of a Reaction-Mass Organ on a
#: LEVIATHAN is 0.6, which is a nudge.
THROTTLE_STEPS = (0.10, 0.25, 0.50, 1.00)

#: How long an action may let the clock run, in minutes. One tick is a minute.
#:
#: Fifteen is the top because `ADRIFT_MULTIPLE` ends an approach at four times
#: where it began: coasting longer than this from a standing start is a way to
#: lose the approach by holding a button down, and a control whose worst use is
#: invisible is a trap rather than a choice.
COAST_MINUTES = (1, 5, 15)


def usable_throttle(conn: Conn, main: bool, throttle: float = 1.0) -> float:
    """What the drive will actually open to, 0..1.

    The clamp, and then the lopsided-hull cap. Attitude clusters do not
    throttle, so they are always fully open.
    """
    if not main:
        return 1.0
    return min(max(0.0, min(1.0, throttle)), conn.hold)


def burn_cost(conn: Conn, main: bool, throttle: float = 1.0) -> float:
    """The reaction mass one press spends, in tonnes.

    **The one door.** `conn.can_burn` used to ask for a whole `MAIN_COST`
    whatever the throttle, so a hull with 0.119 t aboard was told "No reaction
    mass for the drive" for a burn that costs 0.012 — the gate refusing an act
    it could afford. `apply` and `can_burn` both come here now, so the gate
    cannot disagree with the act again.
    """
    part = usable_throttle(conn, main, throttle)
    if not main:
        return RCS_COST
    spend = MAIN_COST * part
    if conn.hold < 1.0:
        spend *= 1.0 + TRIM_COST_SHARE * (1.0 - conn.hold)
    return spend


def dv_of(conn: Conn, main: bool, throttle: float | None = None) -> float:
    """What one press is worth in m/s, at what the pilot has set."""
    want = conn.throttle if throttle is None else throttle
    part = usable_throttle(conn, main, want)
    return (conn.main_dv if main else conn.rcs_dv) * part


def finest(conn: Conn) -> float:
    """The smallest main-drive correction this hull can be asked for, m/s.

    What the console can actually offer, which is the number that decides
    whether the main drive is usable for close work at all.
    """
    return dv_of(conn, True, min(THROTTLE_STEPS))


def set_throttle(conn: Conn, value: float) -> float:
    """Snap to the nearest rung and keep it. Returns what was set."""
    conn.throttle = min(THROTTLE_STEPS, key=lambda s: abs(s - value))
    return conn.throttle


def set_coast(conn: Conn, minutes: int) -> int:
    """Snap to the nearest offered coast and keep it."""
    conn.coast_min = min(COAST_MINUTES, key=lambda m: abs(m - minutes))
    return conn.coast_min


def quote(conn: Conn, axis_id: str | None, main: bool = False) -> dict:
    """What this press will do, at what the pilot has set.

    Everything the console says about a button comes through here, so the
    promise and the act read the same settings.
    """
    from . import preview
    said = preview.forecast(conn, axis_id, main=main, ticks=conn.coast_min,
                            throttle=conn.throttle)
    said["dv"] = dv_of(conn, main) if axis_id else 0.0
    said["cost"] = burn_cost(conn, main, conn.throttle) if axis_id else 0.0
    said["throttle"] = usable_throttle(conn, main, conn.throttle)
    said["minutes"] = conn.coast_min
    return said
