"""Taking the conn on nothing in particular: flying the ship because you want to.

Every manual control in this game hung off an *approach to a thing*.
`sim/berthing.can_conn` is the only door into the flight pad, and it wants a
contact: the six axes, the main drive, the cameras, the plotting board and the
3D windows all live on a `Conn`, and a `Conn` was built from something to come
alongside. It said so in as many words —

    "A position in empty space is somewhere to steer for, not something to
     come alongside."

— and refused. Between one structure and the next, movement was the plotting
board: you plotted a transfer and it happened. That is a fine way to cross a
system and it is not flying.

So this is an approach with **no target**: open space, at the ship's own
position, with the ship at the origin of its own frame. Everything that reads
a `Conn` keeps working, because it is a `Conn` — the same axes, the same tank,
the same cameras, the same physics. What changes is what it means to be at
`pos`: not "so far off the quay" but "so far from where I let go".

**It moves the ship, for real.** `sim/flight.ship_position` is the one door for
where the hull is (#103) and `flight.stand_off` is the writer, so securing from
a free flight writes down where you actually drifted to. A captain who takes
the conn, burns for an hour and secures is somewhere else afterwards, on every
screen that plots the system.

Two ways out, and both are the pilot's:

- **Secure** — stop flying, wherever you are. Nothing ends a free flight by
  itself: there is no berth to reach, nothing to fall into, and drifting away
  from where you started is the *point* rather than a failure.
- **Hand over** — pick something out there and this becomes an approach to it,
  carrying the way you have on. The flying you have already done is not thrown
  away and re-flown by the computer from a standing start.
"""

from __future__ import annotations

import math

from . import flight
from .berthing import KM_PER_AU, REACH_KM
from .targets import OPEN, Target, is_open

#: What the conn calls the empty space it is flying in — defined in
#: `sim/targets` because `Conn` is built there and has to ask the question
#: before this module can be imported. A target of this kind has no radius to
#: hit, no mass to be pulled by and no berths, so every gate that asks "have I
#: arrived" answers no and keeps answering it.

#: How far out a free flight goes before the conn stops being the right
#: instrument, as a share of `berthing.REACH_KM` — the range inside which a
#: captain may take the conn on something at all.
#:
#: **Not a wall.** Nothing stops the ship; `standing` simply says that the
#: thrusters have become the slow way to do this and the plotting board is
#: the fast one. Derived rather than chosen, and the derivation was checked
#: against what a hull can actually do: a full 20 t of reaction mass, spent
#: flat out, moves this ship about 17,000 km. A flat 20,000 was the first
#: draft and no flight could ever have reached it — advice nobody can be
#: given is not advice.
FAR_SHARE = 0.05

def target_of(game) -> Target:
    """The 'thing' a free flight is flying relative to: where you let go.

    A real `Target`, because everything downstream expects one — but with no
    radius, no mass and no berths, so `sim/outcome` cannot decide the flight
    has ended on its own.
    """
    return Target(id="open-space", name="open space", kind=OPEN,
                  radius_km=0.0, mu=0.0,
                  detail="Under way, on the conn.")


def is_free(conn) -> bool:
    """Is this approach a free flight rather than an approach to something?"""
    return is_open(getattr(conn, "target", None))


def begin(game):
    """Take the conn on open space. Returns `(conn, why_not)`.

    The gate is the ship's, not a structure's: there is nobody to clear you to
    fly around your own system. What can stop you is having nothing to push
    with.

    The caller owns the approach — `ui/conn_window` holds it, and the flight
    panel reads that same object — so this does not try to register it
    anywhere. There is no `game.docking`: the first draft of this module
    invented one and set it to None on the way out, which would have been a
    second place to look for the approach and a way for the two to disagree.
    """
    from . import conn as conn_sim
    if float(game.ship.cargo.get("volatiles", 0)) < conn_sim.RCS_COST:
        return None, ("Not a gram of reaction mass aboard. The thrusters "
                      "cannot even nudge.")
    conn = conn_sim.start(game, target_of(game), range_km=0.0, drift=0.0)
    conn.log.append("The conn is yours. No destination set.")
    return conn, ""


def where(game, conn) -> tuple[float, float]:
    """Where the ship has got to, in AU, in the system's own frame.

    The conn works in km on a local x/y/z; the system works in AU on a plane.
    A free flight starts at the ship's position, so this is that position plus
    however far it has been flown — and `z` is dropped, because the sector is
    a plane and always has been. A captain who spends the whole flight
    climbing out of it ends up where they would have without the climb, which
    is the honest consequence of a 2D sector rather than a hidden one: the
    screens say what the plane is.
    """
    sx, sy = flight.ship_position(game)
    return (sx + conn.pos[0] / KM_PER_AU, sy + conn.pos[1] / KM_PER_AU)


def toward(game, conn, contact) -> list:
    """The vector from the ship to a contact, in the conn's own km frame.

    **The fact free flight was missing.** An approach knows where its target
    is — it is the origin, so `-conn.pos` points at it, which is what
    `attitude.heading_note` assumes when nothing is passed. A free flight has
    no target, so there was no answer to "which way is that" for anything the
    pilot could see, and the main drive pushed along whatever nose the hull
    happened to start with. Measured before this existed: a hull 5,698 km off,
    main drive, full throttle, 600 burns on *Ahead* — the range went 5,698 to
    22,695 km. Flying at something you could see moved you away from it.

    The frames are the same axes; only the units and the origin differ, which
    is what `hand_over` relies on too. `z` is zero because the sector is a
    plane — see `where`.
    """
    sx, sy = where(game, conn)
    ax, ay = track_at(game, contact)
    return [(ax - sx) * KM_PER_AU, (ay - sy) * KM_PER_AU, 0.0]


def track_at(game, contact) -> tuple:
    """Where a contact is, through the one door that knows: `sim/track`."""
    from . import track as track_sim
    return track_sim.at(game, contact, game.day)


def steer(game, conn, contact) -> float:
    """Lay the ship's course on a contact. Returns the heading set, in radians.

    **`Conn.heading` is the door, and nothing had ever written it.** The first
    attempt here slewed `conn.nose` straight at the contact and the range did
    not move a metre over four hundred burns while the tank drained — because
    `conn.apply` re-derives where the main drive should point on every tick,
    from the axis button *rotated by the heading*, and slews the nose back
    onto that. Pointing the nose by hand was arguing with the flight computer
    and losing. The heading is what the computer reads.

    So the machinery for turning was all present and correct — `apply` spends
    a whole tick swinging the hull when the nose is off the asked-for heading,
    which is `sim/attitude`'s "turn, burn, and turn again" — and the only
    thing missing was any way to say *which way is ahead*. It was zero, always,
    so "Ahead" meant +y for every hull in every flight for ever.

    `rotate` takes the forward axis (0, 1, 0) to `(-sin h, cos h)`, so putting
    that on the bearing to the contact is `atan2(-dx, dy)`.
    """
    dx, dy, _dz = toward(game, conn, contact)
    if not (dx or dy):
        return conn.heading
    conn.heading = math.atan2(-dx, dy)
    return conn.heading


def off_course(game, conn, contact) -> float:
    """Degrees between where the nose is and the contact. For a panel to say."""
    from . import attitude as attitude_sim
    return math.degrees(
        attitude_sim.angle_between(conn.nose, toward(game, conn, contact)))


def secure(game, conn) -> str:
    """Stop flying, wherever you are, and write it down. Returns one line.

    **The one writer.** `flight.stand_off` is how the game records a hull that
    is not alongside anything, and a free flight ends in exactly that state.
    Anything else — storing a second position on the conn, or leaving the ship
    where it was before it flew — would be the two-doors fault this project
    has been bitten by more than any other.
    """
    at = where(game, conn)
    flew_km = math.dist(conn.pos, (0.0, 0.0, 0.0))
    flight.stand_off(game, at)
    conn.outcome = conn.outcome or "secured"
    # **No log line here.** `berthing.commit` is what charges the chronicle
    # for an approach — the mass, the hours, the line in the ledger — and a
    # free flight is charged through exactly that door. Writing one here too
    # would put the same flight in the log twice, once before it had been
    # paid for.
    return (f"Secured from the conn {flew_km:,.0f} km from where she was "
            f"let go, {spent(conn):.2f} t of reaction mass gone.")


def far_km() -> float:
    """The range past which the screens advise plotting rather than flying."""
    return REACH_KM * FAR_SHARE


def standing(game, conn) -> str:
    """One line for the screens: how the flight is going, and when to stop.

    A free flight has no range-to-target, no closing rate and no berth, so
    every readout the conn window was built around says nothing. This is what
    replaces them: how far she has come, how fast, and — past `FAR_KM` — that
    the thrusters are now the slow way to do this.
    """
    out = math.dist(conn.pos, (0.0, 0.0, 0.0))
    said = (f"{out * 1000:,.0f} m out" if out < 1.0 else f"{out:,.1f} km out")
    said += f", {conn.speed:,.1f} m/s, {conn.rcs:.2f} t aboard"
    if out >= far_km():
        said += (f" — past {far_km():,.0f} km the conn is the slow way. "
                 "Secure and plot a transfer.")
    return said


def spent(conn) -> float:
    """Reaction mass this free flight has used, in tonnes."""
    return max(0.0, conn.opening_rcs - conn.rcs)


def hand_over(game, conn, contact):
    """Turn a free flight into an approach to something, keeping the way on.

    A pilot who has spent twenty minutes lining up on a quay should not have
    the computer start again from the arrival range with a fresh drift. So the
    ship's velocity carries across, and its position is taken from where it
    really is relative to the thing it is now approaching.

    Returns `(conn, why_not)`; on a refusal the free flight is untouched and
    the ship is left where it was standing, because a hand-over that is
    refused should neither strand the pilot nor move the hull.
    """
    from . import berthing as berth_sim
    ok, why = berth_sim.can_conn(game, contact)
    if not ok:
        return None, why
    here = where(game, conn)
    was_body, was_xy = (getattr(game, "orbit_body", None),
                        getattr(game, "ship_xy", None))
    flight.stand_off(game, here)
    fresh, why = berth_sim.begin(game, contact)
    if fresh is None:
        # Put the ship back where it was standing: a refused hand-over must
        # not also move the hull.
        game.orbit_body, game.ship_xy = was_body, was_xy
        return None, why
    # The way she has on, carried across. The frames are both km on the same
    # axes — the conn's origin moves, the units do not.
    fresh.vel = list(conn.vel)
    fresh.nose = list(conn.nose)
    fresh.rcs = conn.rcs
    fresh.log.append(
        f"Handed over to the computer with {math.dist(conn.vel, (0, 0, 0)):.1f}"
        " m/s on.")
    return fresh, ""
