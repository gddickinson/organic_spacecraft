"""The conn: flying the ship at close quarters, in kilometres and metres a second.

Everything else in the game moves the ship in *days* and *AU*. `flight.travel_to`
takes a body index and a burn and hands back an arrival — the hull teleports
across the system and the calendar pays for it. That is the right grain for a
transfer and the wrong grain for the last ten kilometres, where the whole
question is whether you can match velocity with something before you hit it.

This is that last ten kilometres. A local frame centred on whatever you are
approaching, the ship's position and velocity relative to it, and two ways to
change them:

* **Reaction control.** Small, precise, cheap: `RCS_DV` a pulse. What you
  berth on, and a careful pilot can do everything with it given time.
* **The main drive.** `MAIN_DV` a burn — thirty times the shove for about six
  times the mass. It closes distance, and it is a poor tool for the last
  hundred metres; the damage model says so.

Three things make this more than a joystick. Closing speed is not free: arrive
fast and contact is a collision, scaled by how fast. A planet pulls, with a
`mu` from its own `radius_km` and `gravity`. And the main drive only pushes
along the nose (`sim/attitude.py`), so a burn in a new direction is a turn
first, and the turn takes the time this hull's clusters need.

Nothing here writes to the chronicle. `apply` returns what the manoeuvre did
and the caller decides what it costs; the sim layer must not touch Qt and this
must not touch the save.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# The six camera directions and the six thruster axes are both hull geometry,
# so they live with the mounts. Re-exported because every caller in the conn
# and its windows reaches for them through this module.
from ..data.mounts import AXES, AXES_BY_ID, VIEWS  # noqa: F401
from ..data.starclasses import of as star_class
from . import outcome as outcome_sim
from .orbits import (ORBIT_BAND, ORBIT_BAND_SHARE, ORBIT_FLOOR_KM, in_orbit,
                     orbit_band, orbit_note, orbital_speed, semi_major_km)
from .targets import (G0, Target, approach_range, is_open, starlight,
                      target_from_body, target_from_contact)

#: Delta-v from one thruster pulse and one main-drive burn, in m/s.
RCS_DV = 0.4
MAIN_DV = 12.0

#: Reaction mass a pulse and a burn cost, in the same units the tank is in.
#: The main drive is thirty times the shove for six times the mass, so it is
#: the efficient way to cross a gap and the wasteful way to nudge.
RCS_COST = 0.02
MAIN_COST = 0.12

#: Alongside: near enough to pass lines across, slow enough to survive it.
ALONGSIDE_KM = 0.25
ALONGSIDE_RATE = 1.5
#: Faster than this into something solid and it is a collision, not a berth.
SAFE_CLOSING = 4.0

#: What an impact at exactly `SAFE_CLOSING` takes off the hull. Damage goes
#: as the *square* of the speed: linear and capped, a five-km/s arrival cost
#: sixty of 336 and a captain could aim at a planet as a shortcut. Now four
#: m/s is a scrape and thirty ends a starting hull.
IMPACT_BASE = 6.0

#: One tick of the conn, in seconds: long enough that a pulse visibly moves
#: her, short enough to correct inside a hundred metres.
TICK = 60.0
#: How far past the opening range counts as having lost the approach — scaled,
#: because 400 km is a long way off a quay and inside a planet's crust.
ADRIFT_MULTIPLE = 4.0

@dataclass
class Conn:
    """A close-quarters approach in progress."""

    target: Target
    #: Where the ship is relative to the target, in km.
    pos: list = field(default_factory=lambda: [0.0, -12.0, 0.0])
    #: How fast, in m/s, in the same frame.
    vel: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    #: Which way the nose points, as a unit vector in the target's frame.
    #: The main drive pushes along this and nowhere else.
    nose: list = field(default_factory=lambda: [0.0, 1.0, 0.0])
    #: Kept for the camera basis, which works in the hull's own frame.
    heading: float = 0.0
    #: This hull's propulsion, read from what is actually fitted. The bare
    #: constants below are only the fallback for a Conn built without a ship.
    main_dv: float = MAIN_DV
    rcs_dv: float = RCS_DV
    slew_rate: float = 0.02
    turn_rate_cost: float = 0.0
    #: What the pilot has set on the throttle, 0..1. See `sim/pilot.py`: the
    #: drive has been able to throttle since the autopilot was fixed for firing
    #: everything at once, and until now the console could not ask for it.
    throttle: float = 1.0
    #: How many minutes an action lets the clock run afterwards. `apply` fires
    #: once and *then* steps time, so this is a coast and not a burn length.
    coast_min: int = 1
    #: **The armed state is the flight's, not any window's** — as private
    #: window attributes, the drive armed on the bridge read "off" on the
    #: conn, and two windows' clocks flew one hull at double time.
    #: `auto`: "" | "null" | "close" | "orbit" | "run" (which needs `mark`,
    #: a contact *name*); `clock_on` is written only by `set_conn_clock`.
    auto: str = ""
    arm_main: bool = False
    clock_on: bool = False
    mark: str = ""
    #: How far the main drive can be opened and still be held straight, 0..1.
    #: Three places in the tables promised this and none was true: a hull on
    #: one engine of two flew as straight as one on two, only slower. The cap
    #: is off-axis thrust against attitude authority — a NAVIS on one of two
    #: holds 0.62, a LEVIATHAN under a Fusion Torch only 0.20 — so the
    #: liability is a big engine on a hull with few stations. See
    #: `thrusters.yaw_torque` and `holdable_throttle`.
    hold: float = 1.0
    #: Reaction mass left for close work, and what the hull started with.
    rcs: float = 40.0
    #: Seconds since the approach began.
    elapsed: float = 0.0
    #: Seconds the chronicle has already been charged for. An approach tells
    #: the clock once at the end; a screen that flies with the clock running
    #: tells it as it goes, and `berthing.charge_flown` is the one door so
    #: neither can bill the same minute twice.
    charged: float = 0.0
    #: `charged`'s twin for the tonnes: billed as burned (#149), exact (#148).
    charged_rcs: float = 0.0
    #: Opened already in a sound orbit: a state, not an outcome (`start`).
    opened_orbiting: bool = False
    #: **The flight envelope guard** (`sim/collision.py`): on, the computer
    #: will not fly her into what it could still stop for and a hand-burn
    #: that worsens an unstoppable closure is refused; off, nothing brakes
    #: and nothing is refused, which is how a captain rams on purpose.
    #: `avoiding` is what it has already announced, so it says so once.
    safeties: bool = True
    avoiding: str = ""
    #: The range the approach opened at, which is what "adrift" is measured
    #: against — a fixed distance cannot serve both a quay and a gas giant.
    start_km: float = 12.0
    #: What the tank held when the approach opened. `sim/berthing.py` charges
    #: the difference to the ship; nothing here spends anything real.
    opening_rcs: float = 40.0
    #: Which way the starlight travels, in this frame. The star sits at the
    #: system's centre and the target out from it, so light falls along the
    #: target's own position vector — which puts a world's terminator on the
    #: correct side.
    star_dir: list = field(default_factory=lambda: [0.0, 1.0, 0.0])
    #: How bright this system's star is, against the Sun. A *fact* about the
    #: star; how many stops of it a screen can show is the window's business.
    #: `StarClass.luminosity` has existed since the classes were written and
    #: its docstring claimed it drove the light on everything else. It drove
    #: nothing: every world in the sector was lit identically.
    star_lum: float = 1.0
    #: Everything else in the system, placed in this frame. Built once when
    #: the approach opens — bodies move on a scale of months and an approach
    #: is over in hours.
    sky: list = field(default_factory=list)
    #: The array this hull looks through, in ly (`Stats.sensor`), stamped
    #: when the approach opens — nobody refits a sensor in flight. It lives
    #: here because `instruments.readout` holds a Conn and no Game: a panel
    #: guessing at a default array while the computer used the real one is
    #: the two-screens-disagree fault this deck was rebuilt to end.
    array: float = 2.0
    #: The radius from the target's centre, in km, that the pilot has asked
    #: to hold. Zero means "wherever we are" — which is what every orbit in
    #: the game used to be, because `autopilot` circularised at the current
    #: range and nothing ever asked for a different one.
    orbit_want_km: float = 0.0
    #: Set once the chronicle has been charged for this approach.
    landed: bool = False
    log: list = field(default_factory=list)
    #: Set once, when the approach is resolved one way or the other.
    outcome: str = ""
    #: Damage taken coming in, for the caller to charge.
    damage: float = 0.0
    #: The masses on both sides of this approach, in tonnes, recorded when it
    #: opens the way `star_dir` and `star_lum` are. A collision needs both —
    #: momentum is not a property of one body — and `sim/outcome.py` decides
    #: outcomes without a `game` to ask, so the figures come with the approach
    #: rather than being looked up mid-contact.
    mass_t: float = 24_000.0
    target_mass_t: float = 60_000.0
    #: What the *other* thing took, and how hard it was shoved, in the same
    #: contact that damaged this hull. Zero on every approach that ends
    #: alongside; a quay used as a backstop carries these away with it.
    struck_damage: float = 0.0
    struck_dv: float = 0.0
    #: Which berth on the structure this approach is for. Chosen once by
    #: `sim/moorings.assign` and held: a computer that re-picks the nearest
    #: fitting every tick chases a moving aim and runs its tanks dry between
    #: two of them.
    berth: str = ""
    #: **What the ship actually fired last tick**, so a screen can light the
    #: control used. Recorded by `apply`, never re-asked of the computer: a
    #: second call is a fresh forecast and disagrees the moment anything
    #: moves. `fired_axis` is None on a coast; `fired_share` is how far the
    #: throttle really opened, which is not always what was asked for.
    fired_axis: str | None = None
    fired_main: bool = False
    fired_share: float = 0.0
    #: True on a tick spent swinging the hull round instead of burning.
    fired_turning: bool = False
    #: What the structure said when it was asked. `sim/clearance.py` issues
    #: it; the approach carries it so every screen quotes the same words, and
    #: so a berth assigned by the port cannot be quietly swapped for one the
    #: ship preferred.
    cleared: object = None
    #: How far a standoff berth's boom has come out, 0 to 1. Only a standoff
    #: has one; see `sim/moorings.boom_step`. It runs out while the hull holds
    #: station in reach and steady, and back in when it does not.
    boom: float = 0.0
    #: What this structure can do about a hull it has not cleared, and how
    #: patient it is — see `sim/control.post`. Set once when the approach
    #: opens, so the tick loop can run the ladder without a handle on the
    #: world. None for anything with nobody in it.
    watch: object = None
    #: How far up that ladder the structure has gone: an index into
    #: `control.LADDER`. Zero for a hull that is welcome, and it falls back to
    #: zero the moment one becomes welcome.
    told: int = 0
    #: Ticks of continued closing at the present rung, and ticks spent under
    #: fire. The first decides when the structure loses patience; the second is
    #: why point defence hurts more the longer you take it.
    told_for: float = 0.0
    warded_for: int = 0
    #: How far a tug has come out to this hull, 0 to 1, and how far it has
    #: walked it in. Only a structure that keeps boats has one; see
    #: `sim/tug.tug_step`. What it buys is reaction mass — the tug's drive
    #: does the work, so a cleared hull that waits berths for nothing.
    tug: float = 0.0
    towed: float = 0.0
    #: How far the structure has worked itself away from this hull, in km.
    #: Carried out to the sector by `sim/berthing.commit` as a knock, so a
    #: station that sheered off is off station on every screen afterwards.
    sheered: float = 0.0
    #: The order to cut into a berth that will not open, and how far through
    #: the cut is, 0 to 1. See `sim/forcing.py`: the order is a decision the
    #: captain makes, and the cut is the only thing in the game that gets a
    #: hull alongside somewhere it was refused.
    forcing: bool = False
    cut: float = 0.0
    #: The order to put the ship down on a world it cannot land on. See
    #: `sim/landing.py`: a hull that merely flew badly is `aground`, and only
    #: one whose captain *chose* the ground gets credited with having flown
    #: it in.
    ditching: bool = False

    @property
    def over(self) -> bool:
        return bool(self.outcome)

    @property
    def range_km(self) -> float:
        return math.dist(self.pos, (0.0, 0.0, 0.0))

    @property
    def speed(self) -> float:
        """Relative speed, m/s — how fast the target is moving in the window."""
        return math.dist(self.vel, (0.0, 0.0, 0.0))

    @property
    def closing(self) -> float:
        """Closing rate, m/s. Positive is closing, negative is opening.

        `pos / r` is a unit vector and carries no units, so this is a velocity
        in the units `vel` is already in. The first draft divided by another
        thousand "to convert km to m" and reported **+0.01 m/s while the ship
        flew in at twelve** — which the autopilot believed, so it went on
        accelerating all the way to the hull.
        """
        r = self.range_km
        if r < 1e-9:
            return 0.0
        # The component of velocity along the line of sight, inward.
        return -sum(p * v for p, v in zip(self.pos, self.vel)) / r


def __getattr__(name):
    """`observe` and `start` live in `sim/conn_open.py`.

    Lazily, and here rather than at the top of the file, because `conn_open`
    imports this module for `Conn` — importing it up top would be a cycle.
    Every caller that reaches for `conn.start` still finds it (PEP 562).
    """
    if name in ("observe", "start"):
        from . import conn_open
        return getattr(conn_open, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")



def rotate(vec, heading: float) -> tuple:
    """Turn a vector from the ship's frame into the target's."""
    c, s = math.cos(heading), math.sin(heading)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def can_burn(conn: Conn, main: bool,
             throttle: float | None = None) -> tuple[bool, str]:
    """Is there mass to do this? The gate the panel greys its buttons on.

    **It has to be asked at the throttle the burn will actually use.** This
    took a whole `MAIN_COST` whatever was set, so a hull holding 0.119 t was
    told "No reaction mass for the drive" for a burn costing 0.012 — a gate
    refusing an act it could well afford, which is the fault this project has
    swept every other gate for. `pilot.burn_cost` is the one door now, and
    `apply` spends through it too, so the two cannot drift apart.
    """
    from . import pilot
    if conn.over:
        return False, "The approach is finished."
    want = conn.throttle if throttle is None else throttle
    if main and pilot.usable_throttle(conn, True, want) <= 0.0:
        return False, "The throttle is closed."
    if conn.rcs < pilot.burn_cost(conn, main, want):
        return False, ("No reaction mass for the drive."
                       if main else "The thruster tanks are dry.")
    return True, ""


def thrust_axis(conn: Conn, axis_id: str, main: bool) -> tuple:
    """Which way a burn actually pushes the ship.

    The attitude clusters shove along whichever axis was asked for — that is
    what they are for, and why close work is done on them. **The main drive
    only ever pushes along the nose.** Before this it pushed whichever way the
    button said, which made the six clusters decoration and attitude a
    variable nobody wrote to.
    """
    if main:
        return tuple(conn.nose)
    _aid, _label, vec = AXES_BY_ID[axis_id]
    return rotate(vec, conn.heading)


def apply(conn: Conn, axis_id: str | None, main: bool = False,
          *, ticks: int = 1, throttle: float = 1.0) -> dict:
    """Fire along an axis (or coast, with no axis) and let time run.

    Returns what happened. It never raises on an empty tank: an out-of-mass
    pilot still coasts, which is exactly the situation the model has to be
    able to represent.

    **`ticks` and `throttle` are keyword-only, and that is a bug fix.** They
    used to be positional, and four checks called `apply(conn, axis, main,
    throttle)` — putting the throttle into `ticks`, where `max(1, ticks)`
    quietly rounded it to one tick, and leaving `throttle` at its default. So
    every flight those checks flew had **the main drive wide open**, which is
    the one thing `pilot.usable_throttle` exists to prevent: this module's own
    comment records that an unthrottled drive made a bigger engine *worse*,
    because one tick of a fusion torch is 124 m/s and the computer lit it to
    trim ten. The checks were verifying a ship the game does not fly. A
    keyword-only parameter cannot be passed by accident.
    """
    if conn.over:
        return {"ok": False, "why": "The approach is finished."}
    from . import attitude as attitude_sim

    burned = turning = False
    conn.fired_axis, conn.fired_main = None, bool(main)
    conn.fired_share, conn.fired_turning = 0.0, False
    if axis_id:
        ok, _why = can_burn(conn, main, throttle)
        if ok and main:
            # The main drive pushes along the nose. If the nose is not on the
            # heading asked for, this tick is spent swinging the hull round
            # instead of burning — which is what makes a hard burn to port on
            # a loaded freighter a decision rather than a button.
            _aid, _label, vec = AXES_BY_ID[axis_id]
            want = rotate(vec, conn.heading)
            if not attitude_sim.pointed_at(conn.nose, want):
                attitude_sim.slew(conn, want, TICK)
                turning = conn.fired_turning = True
                ok = False
        if ok:
            # The main drive throttles — the difference between an engine and
            # a firework. Without it a bigger drive made every hull *worse*:
            # one tick of a fusion torch on a SPORE is 124 m/s, so the
            # computer lit it to trim ten and never converged. Clusters are
            # pulsed, not throttled. The clamp, the lopsided cap and the trim
            # surcharge live in `pilot` — the console quotes them before the
            # pilot commits, and a second copy here is how a forecast lies.
            from . import pilot
            part = pilot.usable_throttle(conn, main, throttle)
            dv = (conn.main_dv if main else conn.rcs_dv) * part
            wx, wy, wz = thrust_axis(conn, axis_id, main)
            conn.vel[0] += wx * dv
            conn.vel[1] += wy * dv
            conn.vel[2] += wz * dv
            conn.rcs = round(
                conn.rcs - pilot.burn_cost(conn, main, throttle), 4)
            burned = part > 0
            if burned:
                conn.fired_axis, conn.fired_share = axis_id, part
    # **Lazily, to keep the seam one-way.** `sim/conn_step` reads this
    # module's constants — eleven other modules read them too, so they stay
    # here — and importing it up top would be a cycle. `apply` already
    # imports `sim/attitude` this way.
    from .conn_step import step
    for _ in range(max(1, ticks)):
        step(conn, TICK)
        if conn.over:
            break
    return {"ok": True, "burned": burned, "turning": turning,
            "range_km": conn.range_km, "closing": conn.closing,
            "speed": conn.speed, "outcome": conn.outcome}





def alongside(conn: Conn) -> bool:
    """Near enough and slow enough to call it a berth."""
    return outcome_sim.alongside(conn, ALONGSIDE_KM, ALONGSIDE_RATE)


def readout(conn: Conn) -> list[tuple[str, str, str]]:
    """The instrument panel. Lives in `sim/instruments.py`; re-exported here
    because every caller reaches for the conn first."""
    from .instruments import readout as _readout
    return _readout(conn)
