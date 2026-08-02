"""The conn: flying the ship at close quarters, in kilometres and metres a second.

Everything else in the game moves the ship in *days* and *AU*. `flight.travel_to`
takes a body index and a burn and hands back an arrival — the hull teleports
across the system and the calendar pays for it. That is the right grain for a
transfer and the wrong grain for the last ten kilometres, where the whole
question is whether you can match velocity with something before you hit it.

This is that last ten kilometres. A local frame centred on whatever you are
approaching, the ship's position and velocity relative to it, and two ways to
change them:

* **Reaction control.** Small, precise, cheap: `RCS_DV` a pulse. This is what
  you berth on, and a careful pilot can do everything with it given time.
* **The main drive.** `MAIN_DV` a burn, thirty times the shove for about six
  times the mass. It closes distance. It is a poor tool for the last hundred
  metres and the damage model says so.

Three things make this more than a joystick. Closing speed is not free: arrive
fast and contact is a collision, scaled by how fast. A planet pulls, with a
`mu` from its own `radius_km` and `gravity`. And the main drive only pushes
along the nose — see `sim/attitude.py` — so a burn in a new direction is a
turn first, and the turn takes the time this hull's clusters need.

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

#: What an impact at exactly `SAFE_CLOSING` takes off the hull.
#:
#: Impact damage goes as the *square* of the speed, because that is where the
#: energy is. Both curves here used to be linear and capped — `min(60, 6 +
#: speed * 1.5)` — so putting the hull down on a world at five kilometres a
#: second cost sixty points of three hundred and thirty-six, and a captain
#: could aim at a planet as a shortcut. Now four metres a second is a scrape,
#: twenty is serious, and thirty ends a starting hull.
IMPACT_BASE = 6.0

#: One tick of the conn, in seconds. A minute is long enough that a pulse
#: visibly moves the ship and short enough to correct inside a hundred metres.
TICK = 60.0

#: How far past where you started counts as having lost the approach. Scaled
#: to the approach, because 400 km is a long way off a quay and inside the
#: crust of a planet.
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
    #: How far the main drive can be opened and still be held straight, 0..1.
    #:
    #: `data/mounts.py` has said since it was written that a two-slot hull
    #: "carries them either side of the centreline, so losing one leaves the
    #: thrust off-axis", and `thrusters.offset` computed exactly how far off,
    #: claiming "the flight computer has to trim against" it. Nothing computed
    #: the torque and nothing trimmed anything: a hull on one engine flew as
    #: straight as one on two, only slower.
    #:
    #: A NAVIS running one of two engines holds 0.62 — three fifths of the
    #: engine it has left. A LEVIATHAN shrugs a missing engine off entirely,
    #: because its inertia beats the torque; the penalty falls hardest on the
    #: hulls light enough to be turned by their own drive.
    hold: float = 1.0
    #: Reaction mass left for close work, and what the hull started with.
    rcs: float = 40.0
    #: Seconds since the approach began.
    elapsed: float = 0.0
    #: Seconds of that the chronicle has already been charged for.
    #:
    #: An approach tells the clock once, at the end. A screen that flies with
    #: the clock running has to tell it as it goes, and the two must not both
    #: charge the same minute — see `berthing.charge_flown`, which is the one
    #: door either way.
    charged: float = 0.0
    #: The range the approach opened at, which is what "adrift" is measured
    #: against — a fixed distance cannot serve both a quay and a gas giant.
    start_km: float = 12.0
    #: What the tank held when the approach opened. `sim/berthing.py` charges
    #: the difference to the ship; nothing here spends anything real.
    opening_rcs: float = 40.0
    #: Which way the starlight travels, in this frame. The star sits at the
    #: system's centre and the target somewhere out from it, so light falls
    #: along the target's own position vector — which is what gives a world
    #: a terminator on the correct side.
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
    #: control that was used. Recorded by `apply` rather than asked of the
    #: autopilot again: what a pilot needs to see is the burn that happened,
    #: and a second call to the computer would be a fresh forecast, which is
    #: not the same thing and would disagree the moment anything moved.
    #: `fired_axis` is None on a tick that coasted; `fired_main` says whether
    #: it was the drive or the clusters; `fired_share` is how far the throttle
    #: was actually opened, which is not always what was asked for.
    fired_axis: str | None = None
    fired_main: bool = False
    fired_share: float = 0.0
    #: True on a tick spent swinging the hull round instead of burning. The
    #: console has always had this in `apply`'s return and thrown it away.
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
                opening_rcs=float(game.ship.cargo.get("volatiles", 0)))
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
        conn.log.append(
            f"Closing {target.name} at {r - target.radius_km:,.0f} km, "
            f"{short:,.0f} m/s under circular and falling.")
        return conn
    conn.log.append(f"Approach begun on {target.name}, "
                    f"{r:.1f} km off, {drift:.1f} m/s of way on.")
    return conn


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
            # The main drive throttles. It is the difference between an engine
            # and a firework, and without it a bigger drive made every hull
            # *worse*: one tick of a fusion torch on a SPORE is 124 m/s, so the
            # computer lit it to trim ten, overshot, corrected the overshoot,
            # and never converged. Attitude clusters are pulsed, not throttled.
            # The clamp, the lopsided-hull cap and the trim surcharge all live
            # in `pilot`, because the console has to quote them before the pilot
            # commits, and a second copy here is how a forecast starts lying.
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
