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

Two things make this more than a joystick. The first is that closing speed is
not free: arrive fast and `contact` is a collision, scaled by how fast. The
second is that a planet pulls. `mu` comes from the body's own `radius_km` and
`gravity`, so a heavy world genuinely demands a faster orbit and genuinely
falls on you if you dawdle — the numbers are the body's, not a difficulty knob.

Nothing here writes to the chronicle. `apply` returns what the manoeuvre did
and the caller decides what it costs; the sim layer must not touch Qt and this
must not touch the save.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .orbits import (ORBIT_BAND, ORBIT_BAND_SHARE, ORBIT_FLOOR_KM, in_orbit,
                     orbit_band, orbit_note, orbital_speed)
from .targets import (G0, Target, approach_range, target_from_body,
                      target_from_contact)

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

#: The six directions a hull carries cameras in, as unit vectors in the
#: ship's own frame: along its nose, its tail, its beams, its back and belly.
VIEWS = [
    ("fore", "Fore", (0.0, 1.0, 0.0)),
    ("aft", "Aft", (0.0, -1.0, 0.0)),
    ("port", "Port", (-1.0, 0.0, 0.0)),
    ("starboard", "Starboard", (1.0, 0.0, 0.0)),
    ("dorsal", "Dorsal", (0.0, 0.0, 1.0)),
    ("ventral", "Ventral", (0.0, 0.0, -1.0)),
]

#: The axes a pilot translates along, in the ship's frame.
AXES = [
    ("forward", "Ahead", (0.0, 1.0, 0.0)),
    ("back", "Astern", (0.0, -1.0, 0.0)),
    ("left", "Port", (-1.0, 0.0, 0.0)),
    ("right", "Starboard", (1.0, 0.0, 0.0)),
    ("up", "Up", (0.0, 0.0, 1.0)),
    ("down", "Down", (0.0, 0.0, -1.0)),
]
AXES_BY_ID = {a[0]: a for a in AXES}


@dataclass
class Conn:
    """A close-quarters approach in progress."""

    target: Target
    #: Where the ship is relative to the target, in km.
    pos: list = field(default_factory=lambda: [0.0, -12.0, 0.0])
    #: How fast, in m/s, in the same frame.
    vel: list = field(default_factory=lambda: [0.0, 0.0, 0.0])
    #: Which way the nose points, radians, 0 = along +y.
    heading: float = 0.0
    #: Reaction mass left for close work, and what the hull started with.
    rcs: float = 40.0
    #: Seconds since the approach began.
    elapsed: float = 0.0
    #: The range the approach opened at, which is what "adrift" is measured
    #: against — a fixed distance cannot serve both a quay and a gas giant.
    start_km: float = 12.0
    #: What the tank held when the approach opened. `sim/berthing.py` charges
    #: the difference to the ship; nothing here spends anything real.
    opening_rcs: float = 40.0
    #: Set once the chronicle has been charged for this approach.
    landed: bool = False
    log: list = field(default_factory=list)
    #: Set once, when the approach is resolved one way or the other.
    outcome: str = ""
    #: Damage taken coming in, for the caller to charge.
    damage: float = 0.0

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
    conn = Conn(target=target, pos=[0.0, -r, 0.0], vel=[0.0, abs(drift), 0.0],
                start_km=r, rcs=aboard, opening_rcs=aboard)
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


def _rotate(vec, heading: float) -> tuple:
    """Turn a vector from the ship's frame into the target's."""
    c, s = math.cos(heading), math.sin(heading)
    x, y, z = vec
    return (x * c - y * s, x * s + y * c, z)


def can_burn(conn: Conn, main: bool) -> tuple[bool, str]:
    """Is there mass to do this? The gate the panel greys its buttons on."""
    if conn.over:
        return False, "The approach is finished."
    need = MAIN_COST if main else RCS_COST
    if conn.rcs < need:
        return False, ("No reaction mass for the drive."
                       if main else "The thruster tanks are dry.")
    return True, ""


def forecast(conn: Conn, axis_id: str, main: bool = False,
             ticks: int = 1) -> dict:
    """What this burn will leave you with, in the terms the panel shows.

    The pilot reads range, closing rate and relative speed; so this quotes
    range, closing rate and relative speed. A forecast in units nobody is
    looking at is not a forecast.
    """
    # On a copy, and it pays for the burn: quoting the tank as it stands
    # while the burn empties it is the same lie as quoting the wrong range.
    trial = _copy(conn)
    apply(trial, axis_id, main=main, ticks=ticks)
    return {"range_km": trial.range_km, "closing": trial.closing,
            "speed": trial.speed, "rcs": trial.rcs,
            "alongside": alongside(trial), "safe": trial.closing <= SAFE_CLOSING}


def _copy(conn: Conn) -> Conn:
    """A throwaway twin for a forecast to fly.

    It has to carry `start_km`, which is what "adrift" is measured against.
    The first draft left it at the 12 km default, so a forecast for a body
    approach — which opens thousands of kilometres out — decided it had
    drifted off before it had moved, and quoted a range nine kilometres away
    from what the burn actually left.
    """
    return Conn(target=conn.target, pos=list(conn.pos), vel=list(conn.vel),
                heading=conn.heading, rcs=conn.rcs, elapsed=conn.elapsed,
                start_km=conn.start_km, opening_rcs=conn.opening_rcs)


def apply(conn: Conn, axis_id: str | None, main: bool = False,
          ticks: int = 1) -> dict:
    """Fire along an axis (or coast, with no axis) and let time run.

    Returns what happened. It never raises on an empty tank: an out-of-mass
    pilot still coasts, which is exactly the situation the model has to be
    able to represent.
    """
    if conn.over:
        return {"ok": False, "why": "The approach is finished."}
    burned = False
    if axis_id:
        ok, _why = can_burn(conn, main)
        if ok:
            _, _label, vec = AXES_BY_ID[axis_id]
            dv = MAIN_DV if main else RCS_DV
            wx, wy, wz = _rotate(vec, conn.heading)
            conn.vel[0] += wx * dv
            conn.vel[1] += wy * dv
            conn.vel[2] += wz * dv
            conn.rcs = round(conn.rcs - (MAIN_COST if main else RCS_COST), 3)
            burned = True
    for _ in range(max(1, ticks)):
        _step(conn, TICK)
        if conn.over:
            break
    return {"ok": True, "burned": burned, "range_km": conn.range_km,
            "closing": conn.closing, "speed": conn.speed,
            "outcome": conn.outcome}


def _substeps(conn: Conn, dt: float) -> int:
    """How finely to cut a tick so the orbit is not integrated into nonsense.

    A ship in a low orbit crosses a good fraction of it in a minute, and one
    Euler step across that arc adds energy every time — the ship climbs out
    of an orbit it is actually in. Cutting the tick until it moves under a
    hundredth of its radius keeps it honest, and costs nothing anywhere else
    because a hull alongside a quay needs exactly one.
    """
    if conn.target.mu <= 0:
        return 1
    r = conn.range_km
    if r <= 1e-6:
        return 1
    travel = (conn.speed / 1000.0) * dt            # km this tick
    return int(min(120, max(1, math.ceil(travel / (r * 0.01)))))


def _sweep_min(a, b) -> float:
    """The nearest the straight path from `a` to `b` comes to the origin.

    Without this, contact is only ever tested at the *endpoints* of a tick,
    and a ship fast enough to cross the target inside one minute goes clean
    through it. Measured: an approach at 45 m/s covers 2.7 km a tick, passed
    through a station 400 m across, and was reported **adrift** — no impact,
    no damage, the hull untouched. Since impact damage is quadratic, the
    fastest and most dangerous approaches were precisely the ones escaping.
    """
    ax, ay, az = a
    dx, dy, dz = b[0] - ax, b[1] - ay, b[2] - az
    span = dx * dx + dy * dy + dz * dz
    if span < 1e-18:
        return math.dist(a, (0.0, 0.0, 0.0))
    # Where along the segment the closest point falls, clamped to it.
    t = -(ax * dx + ay * dy + az * dz) / span
    t = max(0.0, min(1.0, t))
    return math.dist((ax + dx * t, ay + dy * t, az + dz * t),
                     (0.0, 0.0, 0.0))


def _step(conn: Conn, dt: float) -> None:
    """Integrate one tick: gravity, then motion, then see what we hit.

    Velocity first, then position, from the *new* velocity — semi-implicit,
    which is what keeps a closed orbit closed instead of slowly unwinding.
    """
    subs = _substeps(conn, dt)
    h = dt / subs
    for _ in range(subs):
        was = list(conn.pos)
        r = conn.range_km
        if conn.target.mu > 0 and r > 1e-6:
            # Newton, in km and seconds, converted to the m/s velocity is in.
            pull = conn.target.mu / (r * r)            # km/s²
            for i in range(3):
                conn.vel[i] -= (conn.pos[i] / r) * pull * h * 1000.0
        for i in range(3):
            conn.pos[i] += conn.vel[i] * h / 1000.0    # m/s · s → km
        conn.elapsed += h
        # Contact anywhere along the path, not merely at the end of it.
        if _sweep_min(was, conn.pos) <= conn.target.radius_km:
            _touch(conn)
            if conn.over:
                return
        _resolve(conn)
        if conn.over:
            return


def _touch(conn: Conn) -> None:
    """Put the ship on the target's skin, so contact is resolved there.

    The tick has already carried it past; this walks it back to where it
    actually met the hull, which is the position every reading and every log
    line should be quoting.
    """
    r = conn.range_km
    skin = max(conn.target.radius_km, 1e-6)
    if r > 1e-9:
        conn.pos = [p * (skin / r) for p in conn.pos]
    else:
        conn.pos = [0.0, -skin, 0.0]
    _resolve(conn)


def _resolve(conn: Conn) -> None:
    """Has this ended — alongside, in orbit, aground, or drifted away?"""
    r = conn.range_km
    hull = conn.target.radius_km
    if conn.target.kind == "body":
        if r <= hull:
            conn.outcome = "aground"
            conn.damage = impact_damage(conn.speed)
            conn.log.append(
                f"The hull is down on {conn.target.name} at "
                f"{conn.speed:,.0f} m/s. That was not a landing.")
            return
        if in_orbit(conn):
            conn.outcome = "orbit"
            conn.log.append(
                f"Orbit at {r - hull:.0f} km, "
                f"{conn.speed:.0f} m/s. The drive can rest.")
            return
    elif r <= hull:
        speed = conn.speed
        if speed <= SAFE_CLOSING:
            conn.outcome = "alongside"
            conn.log.append(f"Alongside {conn.target.name}.")
        else:
            conn.outcome = "collision"
            conn.damage = impact_damage(speed)
            conn.log.append(
                f"{conn.target.name} at {speed:,.0f} m/s — the frames took it.")
        return
    if alongside(conn):
        conn.outcome = "alongside"
        conn.log.append(
            f"Station held on {conn.target.name}: {r * 1000:.0f} m, "
            f"{conn.speed:.1f} m/s relative. Lines across.")
        return
    if r > conn.start_km * ADRIFT_MULTIPLE:
        conn.outcome = "adrift"
        conn.log.append(
            f"{conn.target.name} is {r:,.0f} km astern and opening. "
            "The approach is off.")


def impact_damage(speed: float) -> float:
    """What hitting something at this speed takes off the hull.

    Quadratic and uncapped. A cap is what let a five-kilometre-a-second
    lithobraking manoeuvre cost less than a bad week in the Bloom.
    """
    if speed <= 0:
        return 0.0
    return round((speed / SAFE_CLOSING) ** 2 * IMPACT_BASE, 1)


def alongside(conn: Conn) -> bool:
    """Near enough and slow enough to call it a berth."""
    if conn.target.kind == "body":
        return False          # a world is orbited, not moored to
    return (conn.range_km <= ALONGSIDE_KM + conn.target.radius_km
            and conn.speed <= ALONGSIDE_RATE)


def readout(conn: Conn) -> list[tuple[str, str, str]]:
    """The instrument panel: label, value, and how it reads (ok/warn/bad).

    Each row is judged against what the *approach* is trying to do. The first
    draft judged them all against berthing, so a ship correctly established in
    a 360 km orbit at 5,728 m/s had its range and its speed both marked in
    red — the two numbers it had just got right. A panel that cries wolf at a
    good orbit teaches the pilot to ignore it.
    """
    orbiting = conn.target.mu > 0
    r = conn.range_km
    if orbiting:
        want = orbital_speed(conn)
        band = orbit_band(conn)
        altitude = r - conn.target.radius_km
        rows = [
            ("Altitude", f"{altitude:,.0f} km",
             "ok" if altitude >= ORBIT_FLOOR_KM else "bad"),
            ("Closing", f"{conn.closing:+,.1f} m/s",
             "ok" if abs(conn.closing) <= band else "warn"),
            ("Relative", f"{conn.speed:,.1f} m/s",
             "ok" if abs(conn.speed - want) <= band else "warn"),
            ("Circular here", f"{want:,.0f} m/s", "ok"),
        ]
    else:
        rows = [
            ("Range", f"{r * 1000:,.0f} m" if r < 2 else f"{r:,.1f} km",
             "ok" if r < 40 else "warn"),
            ("Closing", f"{conn.closing:+,.1f} m/s",
             "bad" if conn.closing > SAFE_CLOSING else "ok"),
            ("Relative", f"{conn.speed:,.1f} m/s",
             "ok" if conn.speed <= ALONGSIDE_RATE else "warn"),
        ]
    rows.append(("Thruster mass", f"{conn.rcs:,.1f}",
                 "bad" if conn.rcs < MAIN_COST else "ok"))
    rows.append(("Elapsed", f"{conn.elapsed / 60:,.0f} min", "ok"))
    return rows
