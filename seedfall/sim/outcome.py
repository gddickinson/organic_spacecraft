"""How an approach ends: alongside, in orbit, aground, or drifted away.

Lifted out of `sim/conn.py`, which took the file past five hundred lines. The
seam is a real one rather than a line count: `conn` answers *what the ship
does* when you fire a thruster, and this answers *whether the approach is
over* — a question asked once a tick, about the state the physics has just
produced, and one that has proved much subtler than it looks.

Three of the four outcomes are about a distance. The fourth is not: an orbit
is a shape, and asking about it at an instant is the mistake that took four
control laws and three contradicting screens to find. See `orbits.in_orbit`.
"""

from __future__ import annotations

from .moorings import spin_of
from .orbits import in_orbit, semi_major_km

#: How near the height you asked for counts as arriving at it. Wider than the
#: autopilot's own tolerance, so the flight computer settles inside the band
#: rather than chasing an edge it can never quite hold.
ORBIT_HEIGHT_SLACK = 0.035


def at_wanted_height(conn) -> bool:
    """Is this the orbit that was actually asked for?

    Without this the approach ended the instant the ship was in *any* orbit,
    which is why a captain could not choose one: asked for a standard orbit
    from an arrival 400 km up, the conn resolved at the first circular pass it
    fell into and reported success 21% low. Asked for a high one, 59% low. An
    orbit you cannot choose the height of is not a choice, and a screen that
    says "orbit" while sitting somewhere else is worse than no screen.
    """
    want = conn.orbit_want_km
    if want <= 0:
        return True                 # no height asked for: anywhere will do
    # The orbit's own size, not where the ship is on it — see
    # `orbits.semi_major_km`. Asked against the instantaneous range, a ship in
    # a perfectly sound orbit at the right mean height read several per cent
    # out depending on which part of it you caught, and never arrived.
    return abs(semi_major_km(conn) - want) <= max(want * ORBIT_HEIGHT_SLACK,
                                                  1.0)


def _dry(conn) -> bool:
    """Can this hull no longer fire even one thruster pulse?

    Asked through `pilot.burn_cost`, which is the one door onto what a burn
    costs — the same function `conn.can_burn` refuses on and `conn.apply` spends
    through, so the outcome cannot disagree with them about whether a pulse is
    affordable.
    """
    from . import pilot
    return conn.rcs < pilot.burn_cost(conn, False)


def alongside(conn, alongside_km: float, alongside_rate: float) -> bool:
    """Near enough, slow enough, **and at a berth**.

    The third one is new. `radius_km` is a bounding sphere, so a hull that
    crept up on the far side of a Fleet Hub — nowhere near a mast — and
    stopped was moored, and the structure the window spends the whole approach
    drawing had nothing to do with it. `sim/moorings.py` asks where the berths
    actually are, off the same numbers `data/berths3d.py` draws them from.
    """
    if conn.target.kind == "body":
        return False          # a world is orbited, not moored to
    from . import moorings
    return (conn.range_km <= alongside_km + conn.target.radius_km
            and conn.speed <= alongside_rate
            and moorings.at_berth(conn)
            # At a standoff nothing is made fast until the boom has you. The
            # ship is holding station in open space off the end of a gantry:
            # near enough and slow enough is the *start* of the manoeuvre.
            and moorings.captured(conn))


def resolve(conn, *, safe_closing: float, impact_base: float,
            alongside_km: float, alongside_rate: float,
            adrift_multiple: float) -> None:
    """Has this ended? Writes `conn.outcome`, and the damage if any.

    The thresholds come in from `sim/conn.py` rather than being duplicated
    here. This module decides *which question* to ask; the numbers stay in one
    place, because a constant written twice is the fault this project has been
    bitten by more than any other.

    **A free flight has no answer to this question, and that is the point.**
    There is nothing to come alongside, nothing to fall into, and drifting
    away from where you let go is what flying *is*. Without this the first
    tick ended it: a free flight opens at zero range with a target of radius
    zero, so `r <= hull` is true at 0 ≤ 0 and the pilot was reported as having
    hit open space before touching a control. It ends when the pilot secures —
    `sim/freeflight.secure` — and at no other time.
    """
    from .targets import is_open
    if is_open(conn.target):
        return
    r = conn.range_km
    # **What you can hit, not how big it is.** `radius_km` is the bounding
    # sphere the window draws the structure at, furniture and all — and seven
    # of the nineteen holdings had berths inside it, so flying at an ARCA
    # Habitat reported a collision 3,995 m from the mast it was aiming for.
    # `sim/bays.hull_km` is the solid middle, and for a structure with a way
    # in it is not solid at the aperture at all.
    from . import bays
    hull = bays.hull_km(conn.target)

    def hurt(speed: float) -> float:
        """What this hull takes, and what it does to the other one.

        **The one door for a collision.** `impact_damage` was the whole event
        — a number off the player and nothing else — so a quay could be used
        as a backstop and a hull rammed on purpose was neither moved nor
        marked. `sim/impulse.py` answers for both sides off the two masses,
        and writes what the other one took onto the approach so `berthing`
        can carry it out to the sector.

        Calibrated to leave this side unchanged: the reference case is the
        ship this game ships with meeting the hub it starts beside, and it
        still costs exactly what it always did.
        """
        from . import impulse
        both = impulse.collide(getattr(conn, "mass_t", 24_000.0),
                               getattr(conn, "target_mass_t", 60_000.0),
                               speed)
        conn.struck_damage = both["harm_b"]
        conn.struck_dv = both["dv_b"]
        return both["harm_a"]

    # **An approach with nothing left to burn is over.** Found by flying the
    # heights the conn offers with the tank a hull actually carries: at the high
    # rung of a 153 km asteroid the computer spent all twenty tonnes in about
    # two thousand ticks getting to 95% of the height, and then went on ordering
    # a burn every tick for another eighteen thousand — refused each time by
    # `conn.can_burn`, so nothing moved and nothing was said. The approach never
    # resolved, and a captain watching the conn saw the computer working and the
    # numbers not changing.
    #
    # Two cases, and they end differently. A dry hull that *is* in a sound
    # orbit has an orbit — just not the one it asked for — and the orbit branch
    # below accepts it and says which. A dry hull that is not in orbit and no
    # longer closing has nothing left that can change, so the approach is over.
    # One that is still closing might yet arrive on momentum, and is left to.
    if _dry(conn) and not in_orbit(conn) and conn.closing <= 0:
        conn.outcome = "dry"
        conn.log.append(
            f"The thruster tanks are dry {r - hull:,.0f} km off "
            f"{conn.target.name}, and the computer has stopped asking.")
        return

    if conn.target.kind == "body":
        if r <= hull:
            conn.outcome = "aground"
            conn.damage = hurt(conn.speed)
            conn.log.append(
                f"The hull is down on {conn.target.name} at "
                f"{conn.speed:,.0f} m/s. That was not a landing.")
            return
        # `or _dry(conn)`: an orbit you cannot improve on is the orbit you
        # have. Without it a hull that spent its tank climbing to 95% of the
        # height asked for went on ordering refused burns for the rest of the
        # flight and the approach never ended — measured, eighteen thousand
        # ticks of a computer working and nothing changing.
        if in_orbit(conn) and (at_wanted_height(conn) or _dry(conn)):
            conn.outcome = "orbit"
            axis = semi_major_km(conn)
            want = conn.orbit_want_km
            short = (want > 0 and abs(axis - want)
                     > max(want * ORBIT_HEIGHT_SLACK, 1.0))
            conn.log.append(
                f"Orbit at {r - hull:.0f} km, "
                f"{conn.speed:.0f} m/s. The drive can rest."
                + (f" {axis:,.0f} km against the {want:,.0f} asked for, and "
                   "the tanks are dry — this is the orbit you have."
                   if short else ""))
            return
    elif r <= hull and not bays.in_corridor(conn, spin_of(conn)):
        # **Contact is a berthing only at a berth.** There are two roads to
        # "alongside" — this one, where the hull touches the structure, and
        # the station-keeping branch below — and gating only the second left
        # this one accepting a touch anywhere on the skin. Found by flying an
        # approach *by hand* from the flight-controls window: it berthed 477 m
        # from the mast with a 140 m reach, because it had bumped the hull.
        #
        # A gentle touch away from a fitting is not a mooring, it is a scrape,
        # and `sim/impulse.py` already prices it — at a couple of metres a
        # second that is a few points off both of them.
        from . import moorings
        speed = conn.speed
        if speed <= safe_closing and moorings.at_berth(conn):
            conn.outcome = "alongside"
            conn.log.append(f"Alongside {conn.target.name}.")
        else:
            conn.outcome = "collision"
            conn.damage = hurt(speed)
            where = moorings.nearest(conn)
            aside = ("" if where is None or where["at_it"] else
                     f" — {where['km'] * 1000:,.0f} m from {where['name']}")
            conn.log.append(
                f"{conn.target.name} at {speed:,.0f} m/s{aside}. "
                "The frames took it.")
        return

    if alongside(conn, alongside_km, alongside_rate):
        conn.outcome = "alongside"
        conn.log.append(
            f"Station held on {conn.target.name}: {r * 1000:.0f} m, "
            f"{conn.speed:.1f} m/s relative. Lines across.")
        return

    # Drifting away is measured against where the approach opened — but a
    # captain who asks for a high orbit is *supposed* to end up a long way
    # out, and at a small body the high rung is nearly four times the arrival
    # range. So the yardstick is whichever is further: where we started, or
    # where we were told to go. Without this, climbing to the orbit the screen
    # had just offered was reported as losing the target astern.
    limit = max(conn.start_km, conn.orbit_want_km) * adrift_multiple
    if r > limit:
        conn.outcome = "adrift"
        conn.log.append(
            f"{conn.target.name} is {r:,.0f} km astern and opening. "
            "The approach is off.")
