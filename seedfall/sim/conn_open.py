"""Opening a flight: turning a game and a contact into a `Conn`.

Split out of `sim/conn.py`, which had grown past the ceiling. The seam is a
real one rather than a place to cut: *this* module reads the whole game — the
ship's cargo for the tank, its engines for the thrust, the star for the light,
the system for the sky — and hands back a flight. `conn.py` from there on
knows only the flight, and needs to know nothing else.

Both builders are re-exported from `sim/conn.py` (PEP 562), so every caller
that reaches for `conn.start` still finds it.
"""

from __future__ import annotations

from ..data.starclasses import of as star_class
from .conn import Conn, TICK
from .orbits import in_orbit, orbit_band, orbital_speed
from .targets import (Target, approach_range, is_open, starlight,
                      target_from_contact)


def observe(game) -> Conn:
    """The view from where the ship is standing, with nothing to approach.

    A captain with nothing in reach was shown an empty rectangle: the windows
    drew the approach target and a fixed field of stars, and with no target
    there was nothing but the field. There is always something to see — at
    0.40 AU the system's own star is 1.34° across — so the conn opens anyway
    and simply says it has no approach running.
    """
    from . import sky as sky_sim
    watching = Target(id="watch", name="Station keeping", kind="point",
                      radius_km=0.0, detail="Nothing within reach to close.")
    conn = Conn(target=watching, pos=[0.0, 0.0, 0.0], vel=[0.0, 0.0, 0.0],
                start_km=1.0, rcs=float(game.ship.cargo.get("volatiles", 0)),
                opening_rcs=float(game.ship.cargo.get("volatiles", 0)),
                array=float(getattr(game.ship_stats, "sensor", 2.0)))
    conn.outcome = "watching"
    conn.landed = True                      # nothing to charge for looking
    conn.sky = sky_sim.build(game, None)
    conn.star_lum = star_class(game.system).luminosity
    conn.log.append("Nothing within reach. The watch is kept.")
    return conn


def start(game, contact, range_km: float | None = None,
          drift: float = 2.0) -> Conn:
    """Begin an approach, arriving off the target with way on.

    You do not arrive stopped. The drift is what the transfer left you with,
    and killing it is the first thing a pilot does.

    At a world the transfer has already spent the kilometres a second, so the
    ship arrives *nearly* circular and a little out — which is the manoeuvre
    a conn is for. Trimming fifty metres a second is a few minutes' work;
    building five thousand from rest is not something a thruster does.
    """
    target = target_from_contact(game, contact)
    r = approach_range(target) if range_km is None else abs(range_km)
    # The tank is the ship's own. The first draft invented one from the hull's
    # speed rating — a captain with 20 t of volatiles aboard took the conn
    # with 36.8, and spent it without the ship noticing.
    aboard = float(game.ship.cargo.get("volatiles", 0))
    # What this hull can actually push with. A Fusion Torch on a SPORE is a
    # rocket and on a LEVIATHAN is a nudge; until the engines had places and
    # masses, both read as "speed +0.58" and flew identically.
    from . import attitude as attitude_sim
    from . import thrusters
    kit = thrusters.summary(game.ship)
    from . import impulse
    conn = Conn(target=target, pos=[0.0, -r, 0.0], vel=[0.0, abs(drift), 0.0],
                start_km=r, rcs=aboard, opening_rcs=aboard,
                mass_t=impulse.ship_mass(game),
                target_mass_t=impulse.mass_of(game, target),
                main_dv=kit["main_accel"] * TICK,
                hold=kit["hold"],
                rcs_dv=kit["rcs_accel"] * TICK,
                slew_rate=kit["slew_rate"],
                array=float(getattr(game.ship_stats, "sensor", 2.0)),
                turn_rate_cost=attitude_sim.turn_cost(game.ship, 6.283185))
    # Pointing at the target — except on a free flight, where the ship *is*
    # the origin and there is nothing to point at. `unit` of a zero vector has
    # no answer, so the nose keeps the heading the frame is built on and the
    # pilot turns it wherever they like.
    conn.nose = (list(attitude_sim.unit([-p for p in conn.pos]))
                 if r > 1e-9 else [0.0, 1.0, 0.0])
    conn.star_dir = list(starlight(game, contact))
    conn.star_lum = star_class(game.system).luminosity
    from . import sky as sky_sim
    # A free flight has no contact behind its target, and `sky.build` has
    # always known how to draw the view from wherever the ship is standing.
    conn.sky = sky_sim.build(game, None if is_open(target) else contact)
    if target.mu > 0:
        # Across the line of sight at circular speed, less the error the
        # transfer left. Radially inward a little, so it is falling: an
        # approach you can ignore is not an approach.
        want = orbital_speed(conn)
        short = orbit_band(conn) * 3.5
        conn.vel = [want - short, -drift, 0.0]
        # **Was she already in one when the conn opened?** Measured, **8 of
        # 11 body approaches opened already finished**: `outcome.resolve`
        # wrote "orbit" on the first tick, so the pad and every mode were
        # dead before a control could be touched. An outcome is what a
        # flight achieves, not the state it began in — see `outcome.resolve`.
        conn.opened_orbiting = in_orbit(conn)
        conn.log.append(
            f"Closing {target.name} at {r - target.radius_km:,.0f} km, "
            f"{short:,.0f} m/s under circular and falling."
            if not conn.opened_orbiting else
            f"On station in orbit of {target.name}, "
            f"{r - target.radius_km:,.0f} km up. She is yours.")
        return conn
    conn.log.append(f"Approach begun on {target.name}, "
                    f"{r:.1f} km off, {drift:.1f} m/s of way on.")
    return conn
