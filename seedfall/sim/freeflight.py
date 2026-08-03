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
    # **An approach measures from its target, not from the ship's last
    # recorded place.** `conn.pos` is an offset from the frame's origin, and
    # the origin is where she let go only in a free flight; in an approach it
    # is the thing being approached, and `flight.ship_position` is not written
    # again until `berthing.commit`. Measured with the ship stood off 10,164
    # km from a quay and then given the conn on it: this said 10,152 km and
    # `conn.range_km` — the conn's own answer — said 12.0, because
    # `berthing.begin` opens an approach at the arrival range. One fact, two
    # answers, and the wrong one fed `engage.range_km`.
    #
    # It read right on a fresh game only because the ship is moored *at* the
    # quay's body, so the two origins coincide.
    if is_open(conn.target):
        sx, sy = flight.ship_position(game)
    else:
        from . import track as track_sim
        sx, sy = track_sim.at(game, conn.target, game.day)
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


def closing_on(game, conn, contact) -> float:
    """How fast the range to a contact is shrinking, in m/s. Negative opens.

    **`Conn.closing` is the wrong number out here.** It is measured against
    the conn's origin, which in a free flight is where she was let go — so a
    ship braking hard onto a contact reads as *opening* on the place she came
    from, which is true and useless. This is the component of the velocity
    along the bearing to the thing the course is laid on.
    """
    vec = toward(game, conn, contact)
    span = math.dist(vec, (0.0, 0.0, 0.0))
    if span <= 1e-9:
        return 0.0
    return sum(v * c / span for v, c in zip(conn.vel, vec))


def off_course(game, conn, contact) -> float:
    """Degrees between where the nose is and the contact. For a panel to say."""
    from . import attitude as attitude_sim
    return math.degrees(
        attitude_sim.angle_between(conn.nose, toward(game, conn, contact)))


#: How close "alongside" is, out in open space, in kilometres.
#:
#: There is no berth to touch and no structure to stop against, so this is the
#: distance at which the computer stops closing and simply holds. Well inside
#: `engage.reach_km` (10,000 km), so a pilot who runs for a hull arrives with
#: the guns able to speak.
ALONGSIDE_KM = 50.0


def run_for(game, conn, contact) -> tuple:
    """What the computer would do this tick to come alongside a contact.

    Returns `(axis_id, main, throttle)` — the same shape `sim/autopilot`
    returns, because it *is* `sim/autopilot`: the closing rate comes from
    `autopilot.rate_for` and the burn from `autopilot.hold`, which is the one
    place in this game that turns "the velocity should be this" into a burn.
    Nothing new is decided here.

    **The mode `autopilot` already had does not fit.** `close` aims at a
    mooring mast through `sim/moorings` and measures its room against a
    structure's radius and a hold point; out here there is neither, and
    measured on a free flight it returned `[0, 0, 0]` — the same answer as
    `null`, so it would have stopped the ship and called it an approach. It
    refuses in open space now, and this is the mode that belongs there.
    """
    from . import autopilot as auto_sim
    toward_it = toward(game, conn, contact)
    span = math.dist(toward_it, (0.0, 0.0, 0.0))
    if span <= ALONGSIDE_KM:
        # Alongside: stop, and stay stopped.
        return auto_sim.hold(conn, [0.0, 0.0, 0.0])
    rate = auto_sim.rate_for(span - ALONGSIDE_KM, conn.rcs_dv)
    want = [c / span * rate for c in toward_it]
    return auto_sim.hold(conn, want)


def alongside(game, conn, contact) -> bool:
    """Has she arrived? Within `ALONGSIDE_KM` and not still running past."""
    return (math.dist(toward(game, conn, contact), (0.0, 0.0, 0.0))
            <= ALONGSIDE_KM)


#: What a run really costs over the up-and-down of the ideal, measured by
#: flying one: 4,784 km quoted 15.7 t ideal and burned 19.8 — corrections.
RUN_MARGIN = 1.3


def run_quote(game, conn, contact) -> dict:
    """The rough bill for running for a contact, before the pilot commits.

    Found by playing: "Run for Quiet Increment" — 4,834 km, well inside
    reach — quietly burned 19.8 of 20 t, and the first the pilot heard of it
    was an approach ending *dry*. The shape is the climb rungs' rule: a run
    is a fuel decision, and a screen that says nothing hides the decision.
    Work up to the safe rate and kill it again, priced the way `pilot.mass_for`
    prices everything, with the measured margin on top.
    """
    from . import autopilot as auto_sim
    from . import pilot as pilot_sim
    span = math.dist(toward(game, conn, contact), (0.0, 0.0, 0.0))
    room = max(0.0, span - ALONGSIDE_KM)
    if room <= 0.0:
        return {"km": span, "dv": 0.0, "mass": 0.0, "tank": conn.rcs,
                "afford": True}
    rate = auto_sim.rate_for(room, conn.rcs_dv)
    dv = 2.0 * rate
    mass = pilot_sim.mass_for(conn, dv) * RUN_MARGIN
    return {"km": span, "dv": dv, "mass": mass, "tank": conn.rcs,
            "afford": mass <= conn.rcs}


def marked(game, conn):
    """The contact the course is laid on, re-read from the sim, or None."""
    if not getattr(conn, "mark", ""):
        return None
    from . import track as track_sim
    for contact in track_sim.contacts(game):
        if contact.name == conn.mark:
            return contact
    return None


def hold_course(game, conn) -> None:
    """Keep the course on the mark, if one is laid. Called every beat.

    A contact rides its body round the star, so a course laid once stops
    pointing at it; laying it again each beat is what makes "Ahead" mean "at
    that" for the whole flight.
    """
    contact = marked(game, conn)
    if contact is not None:
        steer(game, conn, contact)


def can_arm(game, conn, mode: str) -> tuple[bool, str]:
    """May this mode be armed on this flight? The gate every console greys on.

    `close` and `orbit` on an open-space target used to arm, stay lit, and
    coast for ever — `autopilot.target_velocity` refuses them (correctly),
    the window read the refusal as "still flying", and the clock ran with
    nothing at the controls. Refuse at the *button*, with the reason.
    """
    if conn is None or conn.over:
        return False, "Nothing is being flown."
    if not mode:
        return True, ""
    if mode == "run":
        if marked(game, conn) is None:
            return False, "Lay a course on something first."
        return True, ""
    if mode in ("close", "orbit") and is_open(conn.target):
        return False, ("Nothing to " + ("berth at" if mode == "close"
                       else "orbit") + " out here — lay a course and run, "
                       "or take the conn on something.")
    if mode == "close" and getattr(conn.target, "kind", "") == "hull":
        # `moorings.aim` has no fitting to fly to on another ship, so the
        # computer would close on its *centre* — which is a collision worn
        # as a mode. Coming alongside a hull is hand-flying.
        return False, ("Another hull keeps no mast for you. The computer "
                       "will not fly it — take her alongside by hand.")
    return True, ""


def computer(game, conn) -> tuple:
    """What the one flight computer does this beat, under `conn.auto`.

    `(axis, main, throttle)` — the shape `sim/autopilot` returns, because
    every branch is `sim/autopilot`. This is the single dispatcher every
    window's beat asks, so the bridge, the conn and the flight panel cannot
    fly three different computers at one hull.

    **The tug outranks it.** `tug_step` walks the hull in and zeroes the
    velocity every substep, and an armed mode reading that stillness as error
    burned against the boats each tick — spending the mass the tug exists to
    save, under a console printing "Hands off the drive". The computer keeps
    its hands off.
    """
    from . import autopilot as auto_sim
    from . import tug as tug_sim
    mode = getattr(conn, "auto", "")
    if not mode or conn is None or conn.over:
        return None, False, 1.0
    if tug_sim.under_tow(conn):
        return None, False, 1.0
    if mode == "run":
        aim = marked(game, conn)
        if aim is None:
            return None, False, 1.0
        if alongside(game, conn, aim):
            # Arrived. Say so once and hold station.
            conn.auto = "null"
            game.add_log(f"Alongside {aim.name}, "
                         f"{ALONGSIDE_KM:,.0f} km off.", "")
            return auto_sim.autopilot(conn, "null")
        return run_for(game, conn, aim)
    if mode == "brake":
        # Null with a hand-back: kill the way on; when still, say so and
        # give the conn back — was three presses for the commonest manoeuvre.
        if conn.speed <= conn.rcs_dv * 0.75:
            conn.auto = ""
            game.add_log("All stopped. The conn is yours.", "")
            return None, False, 1.0
        return auto_sim.hold(conn, [0.0, 0.0, 0.0])
    return auto_sim.autopilot(conn, mode)


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
    #
    # **And where she is, which this said it did and did not.** The docstring
    # above has always promised "its position is taken from where it really is
    # relative to the thing it is now approaching"; nothing set `fresh.pos`,
    # so `berthing.begin` opened at its own arrival range and the hull jumped.
    # Measured: 290.9 km off a Fleet Hub, handed over, and she was 12.0 km off
    # it — **302.9 km of teleport** in the middle of a flight the pilot had
    # just spent an hour on.
    from . import track as track_sim
    from .conn import ALONGSIDE_KM as alongside_km
    tx, ty = track_sim.at(game, contact, game.day)
    offset = [(here[0] - tx) * KM_PER_AU,
              (here[1] - ty) * KM_PER_AU, 0.0]
    # **Only when the offset is a real place to fly from.** A moored hull's
    # position *is* its structure's — the subtraction comes out 0.000 km, and
    # an approach opened there put the ship inside the skin: measured, one
    # press of "Ahead" and the log read "Struck Fleet Hub coming in". Inside
    # the structure's own radius plus the alongside margin, the hand-over
    # keeps `berthing.begin`'s opening range instead — casting off, not
    # materialising in the middle of the thing.
    floor_km = getattr(fresh.target, "radius_km", 0.0) + alongside_km
    if math.dist(offset, (0.0, 0.0, 0.0)) > floor_km:
        fresh.pos = offset
        # **And the range "adrift" is judged against.** `start_km` stayed at
        # `begin`'s arrival range, so a hand-over from 4,783 km out on a
        # 12 km opening was declared adrift — four times `start_km` — on the
        # very first beat, and the computer never got a tick in.
        fresh.start_km = max(fresh.start_km, fresh.range_km)
    fresh.vel = list(conn.vel)
    fresh.nose = list(conn.nose)
    fresh.rcs = conn.rcs
    # The hours too, and what has already been paid for them together — the
    # difference is what `berthing.charge_flown` bills, so carrying both bills
    # nothing twice and loses nothing. `charged_rcs` is the same meter for the
    # tonnes and travels for the same reason.
    fresh.elapsed = conn.elapsed
    fresh.charged = getattr(conn, "charged", 0.0)
    fresh.charged_rcs = getattr(conn, "charged_rcs", 0.0)
    # The console the pilot set, and whether time was running: a hand-over is
    # the same flight wearing a target, not a fresh ship.
    fresh.arm_main = getattr(conn, "arm_main", False)
    fresh.clock_on = getattr(conn, "clock_on", False)
    fresh.log.append(
        f"Handed over to the computer with {math.dist(conn.vel, (0, 0, 0)):.1f}"
        " m/s on.")
    return fresh, ""
