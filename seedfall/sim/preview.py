"""What a burn will do, before you make it.

Split out of `sim/conn.py`, which does the flying, when that file went past
five hundred lines. The pair here is one idea: fly a throwaway twin of the ship
and report what it ends up with.

`sim/instruments.py` and `sim/outcome.py` came out of the same file for the same
reason, and the seam is the same one — `conn` is the act, and these are what is
said *about* the act.
"""

from __future__ import annotations

import math

from ..data.mounts import AXES_BY_ID
from .conn import SAFE_CLOSING, Conn, alongside, apply, rotate


def forecast(conn: Conn, axis_id: str, main: bool = False,
             ticks: int = 1, throttle: float = 1.0) -> dict:
    """What this burn will leave you with, in the terms the panel shows.

    The pilot reads range, closing rate and relative speed; so this quotes
    range, closing rate and relative speed. A forecast in units nobody is
    looking at is not a forecast.
    """
    # On a copy, and it pays for the burn: quoting the tank as it stands
    # while the burn empties it is the same lie as quoting the wrong range.
    trial = _copy(conn)
    apply(trial, axis_id, main=main, ticks=ticks, throttle=throttle)
    return {"range_km": trial.range_km, "closing": trial.closing,
            "speed": trial.speed, "rcs": trial.rcs,
            "alongside": alongside(trial), "safe": trial.closing <= SAFE_CLOSING,
            "nose_off": math.degrees(_off_by(conn, axis_id, main))}


def _off_by(conn: Conn, axis_id: str, main: bool) -> float:
    """How far the nose is from where this burn needs it, in radians."""
    from . import attitude as attitude_sim
    if not main or not axis_id:
        return 0.0
    _aid, _label, vec = AXES_BY_ID[axis_id]
    return attitude_sim.angle_between(conn.nose, rotate(vec, conn.heading))


def _copy(conn: Conn) -> Conn:
    """A throwaway twin for a forecast to fly.

    It has to carry `start_km`, which is what "adrift" is measured against.
    The first draft left it at the 12 km default, so a forecast for a body
    approach — which opens thousands of kilometres out — decided it had
    drifted off before it had moved, and quoted a range nine kilometres away
    from what the burn actually left.

    **That happened twice more, for the same reason: this is a hand-written
    field list.** Adding `orbit_want_km` left the twin aiming at zero, so a
    forecast during a climb to a high orbit measured its drift against a 12 km
    opening rather than the 20,000 km it was climbing to. Adding `hold` left
    the twin thinking it had both engines, so the forecast quoted a burn 0.095
    km away from the one the drive would actually make — the cap is on the act
    and was not on the quote. `test_conn.py` now guards the list itself, so the
    next field cannot be forgotten quietly.

    The fourth time was `throttle` and `coast_min`, and the guard caught them
    the same afternoon it was written — a forecast is handed both explicitly, so
    nothing was wrong yet, but a twin holding different console settings from the
    ship it stands for is a twin waiting to lie.

    The fifth time was `mass_t` and `target_mass_t`, and the guard caught them
    within the minute. Both change the flying now: contact damage is worked
    out from the two masses, so a twin carrying the dataclass defaults would
    forecast the collision of a different pair of objects.

    `landed`, `log`, `outcome` and `damage` are deliberately *not* carried: a
    twin flies from here, and an approach that has already ended cannot be
    forecast. Neither are `struck_damage` and `struck_dv`, for the same
    reason and one more: they are what the *other* body took, and a trial run
    may not bill a station for a collision that has not happened.
    """
    return Conn(target=conn.target, pos=list(conn.pos), vel=list(conn.vel),
                heading=conn.heading, rcs=conn.rcs, elapsed=conn.elapsed,
                start_km=conn.start_km, opening_rcs=conn.opening_rcs,
                nose=list(conn.nose), star_dir=list(conn.star_dir),
                sky=conn.sky, main_dv=conn.main_dv,
                rcs_dv=conn.rcs_dv, slew_rate=conn.slew_rate,
                turn_rate_cost=conn.turn_rate_cost,
                hold=conn.hold, star_lum=conn.star_lum,
                orbit_want_km=conn.orbit_want_km,
                throttle=conn.throttle, coast_min=conn.coast_min,
                mass_t=conn.mass_t, target_mass_t=conn.target_mass_t,
                berth=conn.berth)
