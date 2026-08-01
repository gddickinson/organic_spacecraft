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

    The sixth was `boom`, caught the same way. At a standoff berth the arm is
    already part way out, and how far it has come is the whole state of the
    manoeuvre: a twin starting it from nought would forecast a hull still
    ninety seconds from capture when it is in fact about to be taken, and a
    twin that drifts would forecast the arm running back in from the wrong
    place. It is carried, and `outcome.alongside` reads it through
    `moorings.captured` on the twin exactly as it does on the ship.

    The seventh was `cleared`, the berth the port assigned — and it was the
    first that broke a check rather than being caught by the guard. Once
    `moorings.assign` began returning the granted berth, a twin without it
    aimed at the nearest fitting instead, and the plot quoted a course to a
    berth that would not have opened: 1.7503 km predicted against 1.7390
    flown.

    The eighth was the approach-control ladder — `watch`, `told`, `told_for`
    and `warded_for` — and the guard had them within the minute. All four are
    carried, and the reason is the same one that carried `boom`: a hull being
    fired on is *in* something, and a forecast that quoted the next burn as
    though nobody were shooting would be exactly as wrong as one that forgot
    an arm was half way out. What it will leave you with includes what the
    station will take off you while you make it.

    `sheered` is deliberately *not* carried, and it is the exception that
    proves the rule about `cleared`: a twin has to know what the structure
    granted, because that decides which berth it flies to — but it may not
    bill the station for having stood off, any more than for a collision that
    has not happened.

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
                berth=conn.berth, boom=conn.boom,
                cleared=conn.cleared, watch=conn.watch, told=conn.told,
                told_for=conn.told_for, warded_for=conn.warded_for)

def track(conn, mode: str | None = None, ticks: int = 60,
          every: int = 6) -> list:
    """Where this approach will be, tick by tick — a dry run of the flying.

    **The same act, not a second model.** It flies a throwaway twin with the
    real `conn.apply`, under the flight computer if `mode` is given and
    coasting if it is not, and writes down where it gets to. A predicted
    course worked out from a formula would be a second answer to a question
    the game already answers by doing it — which is the fault this project
    has chased out of the docking forecast, the turn plan and the readiness
    board, and it is not coming back in through the navigation display.

    Returns `(seconds, position, range_km, speed)` every `every` ticks, so a
    plot can mark the time as well as the path. The list stops early if the
    approach ends: a course that arrives is a course that stops.
    """
    from . import autopilot as pilot

    trial = _copy(conn)
    out = [(0.0, tuple(trial.pos), trial.range_km, trial.speed)]
    for step in range(1, max(1, ticks) + 1):
        if trial.over:
            break
        if mode:
            axis, main, throttle = pilot.autopilot(trial, mode)
            apply(trial, axis, main=main, throttle=throttle)
        else:
            apply(trial, None)
        if step % max(1, every) == 0 or trial.over:
            out.append((trial.elapsed - conn.elapsed, tuple(trial.pos),
                        trial.range_km, trial.speed))
    return out

