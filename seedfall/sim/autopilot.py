"""The flight computer: what it would do with the conn, one tick at a time.

Split out of `sim/conn.py`, which holds the physics. The seam is real rather
than a line count: `conn` says what the ship *does* when you fire a thruster,
and this says which thruster a competent pilot would fire. Nothing here
changes state — `autopilot` returns an axis and whether to use the main drive,
and the caller decides whether to take the advice.

Three modes, each a thing a pilot asks for out loud:

* **null** — kill the relative velocity and hold where you are.
* **close** — bring the range down and berth. Across before along: velocity
  across the line of sight is the part that makes you *miss*, and no amount of
  managing the closing rate removes it.
* **orbit** — get across the line of sight at circular speed for the height.

The braking law is the interesting one. See `safe_rate`.
"""

from __future__ import annotations

import math

from .conn import (AXES, AXES_BY_ID, ALONGSIDE_KM, ALONGSIDE_RATE, TICK,
                   Conn, apply, can_burn)
from .orbits import HEIGHT_TOLERANCE as orbits_HEIGHT_TOLERANCE
from .orbits import (ORBIT_ECCENTRICITY, ORBIT_FLOOR_KM, eccentricity,
                     orbit_band, orbital_speed, semi_major_km)
from .conn import rotate

#: How near the height you asked for counts as being at it. Lives in
#: `sim/orbits.py`, which owns the ladder, and is re-exported here because this
#: is where it is spent. One copy: `orbits.climb_dv` prices nothing for a rung
#: inside it and this law stops inside it, so the quote and the act agree about
#: where "there" is.
HEIGHT_TOLERANCE = orbits_HEIGHT_TOLERANCE

#: The tangential speed, in m/s, below which the direction the ship is going
#: round is not a reliable answer. See `_across`.
ACROSS_FLOOR = 1.0

#: A correction the thrusters can finish inside this many ticks is thruster
#: work, and the main drive is not offered for it however favourably the
#: swing arithmetic comes out. See `worth_turning`.
TURN_WORTH_TICKS = 40.0


def target_velocity(conn: Conn, mode: str) -> list | None:
    """The velocity the ship *should* have right now, in m/s.

    This is the whole flight computer. Every mode is a statement about what
    the velocity ought to be, and the burn is always the same act: cancel the
    difference between that and what it is.

    The first draft was a ladder of branches — correct the drift, else correct
    the closing rate, else coast — each with its own threshold and its own
    idea of how hard to push. It worked at the flat delta-v the conn used to
    assume and fell apart the moment real engines arrived: across a 160-fold
    range of acceleration the branches fought each other, and the drift a hull
    could recover from went 60, then 2, then 140 m/s over three drives of
    increasing thrust. That is a limit cycle, not a handling characteristic.
    """
    if mode == "null":
        return [0.0, 0.0, 0.0]
    # **`close` and `orbit` need something to be close to.** Measured on a
    # free flight, both returned [0, 0, 0] — the same answer as `null` — so a
    # console offering "Close and berth" out in open space would quietly stop
    # the ship and call it an approach. There is no berth; say so.
    from .targets import is_open
    if is_open(conn.target):
        return None
    if mode == "close":
        # Toward the **berth**, at the fastest rate the room left can still
        # absorb. Lateral drift needs no special case: it is simply velocity
        # this vector does not have.
        #
        # It used to aim at the middle of the structure, which is inside it —
        # so the computer flew at whatever face happened to be in the way and
        # `alongside` accepted the far side of a hub as a mooring. It flies to
        # a mast now, and the rate is still measured against the room to the
        # *structure*, because that is what has to be stopped in.
        r = conn.range_km
        if r < 1e-9:
            return [0.0, 0.0, 0.0]
        from . import moorings
        aim = moorings.aim(conn)
        toward = [a - p for a, p in zip(aim, conn.pos)]
        span = math.dist(toward, (0.0, 0.0, 0.0))
        if span < 1e-9:
            return [0.0, 0.0, 0.0]
        inward = [c / span for c in toward]
        return [c * safe_rate(conn) for c in inward]
    if mode == "orbit":
        r = conn.range_km
        # Where the pilot asked to be, not merely where they happen to be.
        # `orbit_want_km` of zero is the old behaviour — circularise here —
        # and it is still what you get if nobody chooses a height.
        aim = conn.orbit_want_km or r
        aim = max(aim, conn.target.radius_km + ORBIT_FLOOR_KM * 1.4)
        want = orbital_speed(conn, aim)
        if want <= 0:
            return [0.0, 0.0, 0.0]
        side = _across(conn)
        length = math.dist(side, (0.0, 0.0, 0.0)) or 1.0

        # Circular speed **for the radius the ship is actually at**, nudged
        # up or down to move the size of the orbit toward the height asked
        # for. Two properties, and both matter:
        #
        #   * A purely tangential demand at circular speed drives the orbit
        #     *round*. Any radial velocity is error the same law cancels, so
        #     circularisation needs no second branch.
        #   * The nudge moves the semi-major axis, which is what "height"
        #     means — see `orbits.semi_major_km`.
        #
        # A vis-viva transfer solution was tried instead and is the reason
        # this comment is long. `v² = mu(2/r − 1/a)` re-solved from wherever
        # the ship is looks exactly right and needs no constants at all — but
        # it only ever burns prograde at the ship's current position, and a
        # prograde burn raises the *opposite* apse. So it lifted apoapsis
        # towards the target for ever and never once raised periapsis:
        # measured at an asteroid, periapsis 418 km and apoapsis 1,630 with
        # e pinned at 0.52 for sixty thousand ticks, arriving nowhere. A
        # Hohmann transfer is two burns at opposite ends of the orbit, and a
        # receding-horizon controller that re-solves every tick does the
        # first one over and over.
        #
        # Both faults underneath this were real and are fixed rather than
        # tuned around: `attitude.turned` could not reverse a hull at all (no
        # great circle is shortest to a point dead astern), and
        # `worth_turning` would order the main drive for a trim the thrusters
        # should have done, then spend every tick slewing.
        here = orbital_speed(conn)
        a_now = semi_major_km(conn)
        if a_now == float("inf") or a_now <= 0 or eccentricity(conn) > ORBIT_ECCENTRICITY:
            # Round it off first. Circular speed for the radius the ship is
            # at, held tangentially — any radial velocity is then error the
            # same law cancels, so this both circularises and needs no second
            # branch to do it. An approach can arrive very eccentric indeed:
            # measured, e = 0.855 at an asteroid, which is a fall rather than
            # an orbit and nothing sensible can be transferred from.
            return [side[i] / length * here for i in range(3)]
        # Round already: now move it. Vis-viva for the transfer from here to
        # the height asked for, `v² = mu(2/r − 1/a)` with `a` the semi-major
        # axis of the ellipse between them — no constant of any kind.
        #
        # **A thrust-limited spiral was tried here and is worse**, which is
        # worth recording because it is the obvious next idea. Demanding
        # circular speed nudged by one pulse toward the aim keeps the orbit
        # round the whole way up and settles beautifully at a small body — and
        # at a large one it *descends into the ground*. The demand `side` is the
        # tangent **in the xy plane**, so an inclined arrival is asked to flatten
        # itself, and that plane change is worth thousands of metres a second at
        # a 57,000 km world: measured, the axis fell 62,133 → 56,737 km over
        # 1,288 ticks with the main drive at full throttle the whole way, and the
        # hull went aground. The full transfer demand is big enough to climb
        # *while* being dragged into the plane; a one-pulse demand is not.
        #
        # **That plane-change diagnosis was wrong, and the retraction is worth
        # more than the claim was.** Measured across every arrival: `hz/|h|` is
        # 1.000 and the plane-change Δv is 0.0 m/s everywhere. Every orbit in this
        # game is already in the xy plane, so demanding the xy tangent costs
        # nothing. Task #101 is closed as a wrong diagnosis.
        #
        # What the spiral was really doing, measured by tracing it at a 2,159 km
        # world: **the demand is purely tangential, so it asks for zero radial
        # velocity** — and at e=0.005 with v≈4,840 the orbit's own radial
        # breathing is ±25 m/s, or fifty-five pulses. The whole of the thrust went
        # into braking an oscillation it could never win, and braking removes
        # energy: the axis fell 2,427 → 2,165 km over 3,266 ticks and the hull
        # went aground. Keeping the radial component and demanding only a
        # tangential magnitude fixes that, and then a second mechanism appears:
        # demanding *circular speed at the radius you are at* pumps energy into an
        # eccentric orbit, because the ship lingers near apoapsis where that
        # demand says "go faster". An apsidal law — prograde at apoapsis to raise,
        # retrograde at periapsis to lower, each of which also reduces
        # eccentricity — is right on both counts and flew the asteroid for 3.1 t
        # against this law's 1,205.
        #
        # **And it was still not shipped, because on the tank the game actually
        # flies it is no better.** With 20 t aboard, this law reaches 71–81% of a
        # high rung and the apsidal one 69–79%, and the apsidal one puts the hull
        # *aground* at an asteroid whose arrival periapsis is already 148 km
        # inside the rock, where this one accidentally survives — its energy
        # pumping lifts the periapsis out. The 1,205 t figure in task #102 was
        # measured with an unlimited tank, which is not a ship. The waste is real
        # and bounded by the tank; what was actually broken was the *offer*, and
        # that is fixed in `orbits.heights_for` and `pilot.climb_options`.
        transfer = (r + aim) * 0.5
        speed = math.sqrt(max(0.0, conn.target.mu * (2.0 / r - 1.0 / transfer)))
        return [side[i] / length * speed * 1000.0 for i in range(3)]
    return None


def autopilot(conn: Conn, mode: str) -> tuple[str | None, bool, float]:
    """What the flight computer would do this tick.

    Returns the axis to burn along, whether to use the main drive, and how far
    to open it. `None` means it would coast.

    Three modes, and each is a thing a pilot asks for out loud:

    * **null** — kill the relative velocity and hold where you are.
    * **close** — bring the range down and berth.
    * **orbit** — get across the line of sight at circular speed.

    All three are the same act underneath: `target_velocity` says what the
    velocity should be, and this cancels the difference.
    """
    if conn.over:
        return None, False, 0.0
    want = target_velocity(conn, mode)
    if want is None:
        return None, False, 0.0
    return hold(conn, want)


def hold(conn: Conn, want) -> tuple[str | None, bool, float]:
    """Burn to make the velocity `want`. The whole flight computer, once.

    Every mode above is a statement about what the velocity ought to be, and
    the act is always this one: cancel the difference. It is public because a
    free flight has modes of its own — running for a contact it can see — and
    a second copy of "cancel the difference" is how a computer that flies a
    berth and one that flies at an asteroid start disagreeing about the same
    hull.
    """
    error = [w - v for w, v in zip(want, conn.vel)]
    need = math.dist(error, (0.0, 0.0, 0.0))
    # A deadband, so the hull is not for ever chasing a drift smaller than one
    # pulse of its own thrusters.
    if need < conn.rcs_dv * 0.5:
        return None, False, 0.0
    return _toward(conn, error, need)



def safe_rate(conn: Conn, dv: float | None = None) -> float:
    """The fastest closing rate that can still be stopped in the room left.

    Shedding `dv` a tick, a ship at `v` travels about `TICK · v² / 2dv`
    before it stops, so the rate the remaining distance can absorb is
    `sqrt(2 · dv · d / TICK)`. Two thirds of it, because the thrust comes in
    lumps and the last lump must not be the one that arrives late.

    The first draft capped the rate at a flat 20 m/s instead, which is a fine
    number at ten kilometres and a collision at two hundred metres — the
    autopilot drove into a quay at 70 m/s and called it a berth.
    """
    if dv is None:
        dv = conn.rcs_dv
    stop_at = conn.target.radius_km + ALONGSIDE_KM * 0.5
    room = max(0.0, (conn.range_km - stop_at) * 1000.0)
    # **And the room to where it is actually going.** Since the approach flies
    # a corridor, the next thing to arrive *at* is the hold point, not the
    # structure — and a rate measured only against the structure lets a strong
    # engine blow straight through the waypoint and then chase it back.
    #
    # Measured by an existing check, which is the one that caught this: with
    # the room to the structure alone, three hulls flew *worse* for a better
    # engine — a SPORE on a plasma drive recovered 80 m/s of drift and the
    # same hull on a stronger fusion torch only 5. More thrust must never be
    # worse, and it was, because the harder it pushed the further past the
    # hold point it went.
    from . import moorings
    aim = moorings.aim(conn)
    if any(aim):
        to_aim = math.dist(conn.pos, aim) * 1000.0
        room = min(room, to_aim) if room > 0.0 else to_aim
    return rate_for(room / 1000.0, dv)


def rate_for(room_km: float, dv: float) -> float:
    """The fastest closing rate that can still be stopped in `room_km`.

    The arithmetic on its own, so an approach and a free flight cannot end up
    with two answers to "how fast may I close". `safe_rate` works out the room
    an approach has — the structure's radius, the hold point, the corridor —
    and hands it here; a free flight has no corridor and no berth, only the
    range to the thing it is running at, so it hands that.
    """
    room = max(0.0, room_km) * 1000.0
    return max(0.0, math.sqrt(2.0 * dv * room / TICK) * 0.66)


def lateral(conn: Conn) -> list:
    """The part of the velocity across the line of sight, m/s.

    The control law no longer branches on this — `target_velocity` has no
    lateral component, so drift is simply velocity the answer does not want,
    and cancelling it needs no special case. It stays because it is how a
    reading is taken: what the panel names, and how a check asks whether an
    approach really is off-axis. Its companion `drift_allowed` did not stay;
    it described a tolerance the single law does not have, and
    `test_reachable` caught it the moment it went dead.

    Closing rate is the part along it. Together they are the whole velocity,
    and a pilot has to null both: the first gets you there, the second
    decides whether you arrive or go past.
    """
    r = conn.range_km
    if r < 1e-9:
        return list(conn.vel)
    unit = [p / r for p in conn.pos]
    along = sum(v * u for v, u in zip(conn.vel, unit))
    return [v - along * u for v, u in zip(conn.vel, unit)]


def _across(conn: Conn) -> list:
    """A direction at right angles to the line of sight, in the orbit plane.

    Which of the two right angles is decided by the way the ship is already
    going, so the computer does not reverse the orbit it is halfway into
    establishing — but only when there is enough angular momentum for the
    answer to mean anything.

    That guard is not decoration. The sense used to come from the sign of a
    dot product with the velocity, and near a small body the tangential
    velocity is a couple of metres a second: the sign flipped between ticks,
    so the computer demanded prograde and then retrograde and then prograde,
    and pumped energy into the orbit instead of shaping it. Measured, a
    comet's 6.8 m/s orbit was driven from 335 km out to 1,340 and adrift.
    Below the threshold, commit to one sense and stay with it.
    """
    px, py, _pz = conn.pos
    r = math.hypot(px, py) or 1.0
    spin = px * conn.vel[1] - py * conn.vel[0]      # angular momentum, km·m/s
    if abs(spin) / r < max(conn.rcs_dv, ACROSS_FLOOR):
        return [-py, px, 0.0]
    return [-py, px, 0.0] if spin > 0 else [py, -px, 0.0]


def _toward(conn: Conn, vec, need: float) -> tuple[str | None, bool, float]:
    """The axis to burn along, which drive to use, and how far to open it.

    One decision point. `need` is the metres a second the manoeuvre is asking
    for, and it settles all three answers: the direction comes from `vec`, the
    drive from whether the swing is worth it, and the throttle from how much
    of that drive a burn of `need` actually uses. The first draft computed
    `need` in two places — once here and once in `fly` — which is the
    arrangement this project has been bitten by more than any other.

    The main drive has to be *aimed*, and aiming costs whole ticks. So asking
    for it when the nose is somewhere else is only worth it when the burn is
    big enough to pay for the swing — otherwise the computer spends every
    tick turning, corrects nothing, and the approach runs away from it. That
    is exactly what happened when attitude first went in: four of eight
    off-axis approaches ended in a collision or adrift at 49 km.
    """
    length = math.dist(vec, (0.0, 0.0, 0.0))
    if length < 1e-9 or need <= 0:
        return None, False, 0.0
    want = [v / length for v in vec]
    best, score = None, 0.0
    for axis_id, _label, body_vec in AXES:
        world = rotate(body_vec, conn.heading, conn.pitch)
        dot = sum(a * b for a, b in zip(world, want))
        if dot > score:
            best, score = axis_id, dot
    if best is None:
        return None, False, 0.0
    # Only the part of the error this axis can actually cancel. Thrust comes
    # in six directions, so the nearest one is up to 45 degrees off the way
    # the correction wants to go — burning the *whole* error along it
    # overshoots in that axis and creates error in another, and the computer
    # chases itself round. Measured: a NAVIS hunting between left, back,
    # down, right and up at 650 m, never berthing.
    need = need * score
    if need <= 0:
        return None, False, 0.0
    main = worth_turning(conn, best, need)
    ok, _why = can_burn(conn, main)
    if not ok and main:
        main = False
    throttle = (max(0.0, min(1.0, need / conn.main_dv))
                if main and conn.main_dv > 0 else 1.0)
    return best, main, throttle


def worth_turning(conn: Conn, axis_id: str, need: float) -> bool:
    """Is the burn big enough to be worth swinging the hull round for?

    Ticks spent turning are ticks not spent correcting, and the target keeps
    closing throughout. The trade is simple: how many ticks the swing costs
    against how many the thrusters would take to do the same job.
    """
    from . import attitude as attitude_sim
    _aid, _label, vec = AXES_BY_ID[axis_id]
    angle = attitude_sim.angle_between(
        conn.nose, rotate(vec, conn.heading, conn.pitch))
    if conn.slew_rate <= 0 or conn.main_dv <= 0:
        return False
    if angle <= attitude_sim.POINTED_RAD:
        return True                       # already aimed; it costs nothing
    on_rcs = need / max(1e-6, conn.rcs_dv)
    # A small correction is thruster work, whatever the swing arithmetic says.
    #
    # The closed-form turn time below is optimistic about what the hull then
    # does with the tick — `apply` spends a whole tick slewing and delivers no
    # thrust at all while it does — so for a trim of a few metres a second the
    # computer would order the main drive, turn for tick after tick, and
    # correct nothing. At an asteroid, where circular speed is forty metres a
    # second and every correction is small, an orbit the ship had reached the
    # height of would not round off: measured, eccentricity stuck at 0.476
    # against the 0.05 that counts as an orbit, for sixty thousand ticks.
    #
    # So the main drive clears a floor as well as winning the comparison.
    # Below it the thrusters are quicker in wall-clock and cannot be wrong.
    if on_rcs <= TURN_WORTH_TICKS:
        return False
    swing = 2.0 * math.sqrt(angle / conn.slew_rate) / TICK
    on_main = swing + need / max(1e-6, conn.main_dv)
    return on_main < on_rcs


def _against(conn: Conn, vec) -> tuple[str | None, bool, float]:
    """Burn to cancel a velocity, using the drive only when it is worth it."""
    speed = math.dist(vec, (0.0, 0.0, 0.0))
    if speed < conn.rcs_dv * 0.5:
        return None, False, 0.0
    return _toward(conn, [-v for v in vec], speed)


def fly(conn: Conn, mode: str, ticks: int = 240) -> Conn:
    """Hand the conn to the computer until it resolves or the ticks run out.

    This is what the *Engage* button does, and what a check drives to find out
    whether the mode actually works.

    The mode is written onto the flight for the run, because that is what
    "hand the conn to the computer" means — and because `Conn.auto` is what
    every screen and `sim/outcome` read to know who is flying. A batch run
    that left it unset was a computer nothing could see.
    """
    conn.auto = mode or ""
    for _ in range(ticks):
        if conn.over:
            break
        axis, main, throttle = autopilot(conn, mode)
        apply(conn, axis, main=main, throttle=throttle)
    return conn
