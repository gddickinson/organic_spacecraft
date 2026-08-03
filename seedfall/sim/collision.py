"""What the hull is about to run into, and whether it can still be stopped.

**The one door for "are we going to hit that".** Before this, the only thing
in the game that knew about contact was `sim/outcome`, which decides it after
it has happened — so a captain could fly a hundred metres a second at a Fleet
Hub with every screen reading calmly, and learn about it from the wreck.

Three questions, in the order a pilot asks them:

* **What is in the way?** Not only the target: `Conn.sky` carries every world,
  quay and hull placed in the approach's own frame, and a ship burning across
  a system passes plenty of things it is not approaching.
* **How long have we got?** Range to the *solid* part — `bays.hull_km`, not
  the bounding sphere — over the closing rate.
* **Can we still stop?** `v²/2a` against the room left, on the thrust the
  hull actually has. This is the number that matters, because it goes from
  yes to no while everything else still looks fine, and after that no amount
  of braking helps.

**Contact is allowed. It has to be meant.** Ramming a hull, cutting into a
berth and putting the ship down on a world are all real acts with their own
orders, and this refuses none of them — `Conn.safeties` is what the computer
and the manual guard read, the deliberate orders (`landing.ditching`,
`forcing.forcing`) speak for themselves, and a hull inside a bay's corridor
is going somewhere it was invited.
"""

from __future__ import annotations

import math

from . import bays
from .conn import TICK
from .targets import is_open

#: How much more room than the stopping distance counts as comfortable. Below
#: this the computer starts shedding speed; above it, nothing is said.
EASY = 2.2

#: Below this the computer is braking hard and the screens say so — there is
#: still room, but not much of it.
TIGHT = 1.3

#: Seconds to contact under which a warning is shouted whatever the room
#: arithmetic says. A pilot wants to hear "twenty seconds" even when the
#: brakes would technically cope.
SOON = 45.0


class Threat:
    """One thing in the way, and what it would take to not hit it."""

    def __init__(self, name, kind, km, closing, room_km, stop_km, seconds):
        self.name = name
        self.kind = kind
        self.km = km                  # centre-to-centre, km
        self.closing = closing        # m/s, positive is closing
        self.room_km = room_km        # to the solid part
        self.stop_km = stop_km        # what stopping would take
        self.seconds = seconds        # to contact at this rate
        #: The instruments' own fix on it, or None for the target, which is
        #: the thing the approach is *about* and never in doubt.
        self.track = None

    @property
    def slack(self) -> float:
        """Room over stopping distance. Under 1.0 she cannot be stopped."""
        if self.stop_km <= 1e-9:
            return float("inf")
        return self.room_km / self.stop_km

    @property
    def level(self) -> str:
        """clear · watch · brake · imminent — what a screen paints it as."""
        if self.slack < 1.0:
            return "imminent"
        if self.slack < TIGHT or self.seconds <= SOON * 0.4:
            return "brake"
        if self.slack < EASY or self.seconds <= SOON:
            return "watch"
        return "clear"

    @property
    def must_brake(self) -> bool:
        return self.level in ("brake", "imminent")


def _accel(conn) -> float:
    """The best deceleration this hull can hold, in m/s per second."""
    from . import pilot
    best = max(conn.rcs_dv, conn.main_dv * pilot.usable_throttle(conn, True))
    return max(1e-6, best / TICK)


def _stopping_km(conn, closing: float) -> float:
    """How far she runs before she is stopped, shedding all she can."""
    if closing <= 0:
        return 0.0
    return (closing * closing) / (2.0 * _accel(conn)) / 1000.0


def _measure(conn, name, kind, at, radius_km, track=None) -> Threat | None:
    """One object: how close, how fast, how much room, how long.

    **A poor track is read at the worse end of its error bar.** An uncertain
    closing rate is inflated and the room shrunk, so a bad array warns early
    and loudly rather than late and precisely — see `sim/detection`, which
    says how good the fix is.
    """
    toward = [a - p for a, p in zip(at, conn.pos)]
    km = math.dist(toward, (0.0, 0.0, 0.0))
    if km < 1e-9:
        return None
    unit = [c / km for c in toward]
    closing = sum(v * u for v, u in zip(conn.vel, unit))
    if closing <= 0.0:
        return None                      # opening, or holding: nothing to say
    noise = track.noise if track is not None else 0.0
    closing *= 1.0 + noise
    room = max(0.0, km - max(0.0, radius_km)) * (1.0 - noise * 0.5)
    seconds = room * 1000.0 / closing if closing > 0 else float("inf")
    threat = Threat(name, kind, km, closing, room, _stopping_km(conn, closing),
                    seconds)
    threat.track = track
    return threat


def toggle_safeties(game, conn) -> tuple:
    """Flip the envelope guard, and hand back the words to say about it.

    One door, because there are two switches — the conn console and the
    flight panel — and they had a copy of the sentence each. Two copies of a
    sentence is how one screen ends up calling it something else, which is
    the whole complaint this flight deck was rebuilt over.
    """
    if conn is None:
        return "", ""
    conn.safeties = not getattr(conn, "safeties", True)
    if game is not None:
        from .tutorial_watch import deed
        deed(game, "safeties")
    if conn.safeties:
        return "Safeties on.", ""
    return "Safeties off — nothing will brake for you.", "bad"


def scan(game, conn) -> Threat | None:
    """The worst thing in the way right now, or None if the sky is clear.

    Worst by *slack* rather than by range: a world eight hundred kilometres
    off that cannot be stopped for is a bigger problem than a quay two
    kilometres away being crept up on.
    """
    if conn is None or conn.over or conn.landed:
        return None
    found = []
    # The target, unless the pilot has said they mean it, or she is inside
    # the way in — a bay's corridor is somewhere she was invited.
    #
    # **Never filtered through `detection`, deliberately.** The thing you
    # chose to approach is on your plot by definition: you have a lock on it,
    # you are flying an approach to it, and a guard that lost your own berth
    # to a sensor range would be worse than no guard. Detection decides what
    # *else* is out there — see the loop below.
    target = getattr(conn, "target", None)
    if target is not None and not is_open(target):
        deliberate = (getattr(conn, "ditching", False)
                      or getattr(conn, "forcing", False))
        from . import moorings
        inside = bays.in_corridor(conn, moorings.spin_of(conn))
        if not deliberate and not inside:
            got = _measure(conn, target.name, getattr(target, "kind", ""),
                           (0.0, 0.0, 0.0), bays.hull_km(target))
            if got is not None:
                found.append(got)
    # And everything else placed in this frame. A ship crossing a system
    # passes plenty of things it is not approaching, and none of them were
    # ever asked about.
    # **Only what the instruments actually hold.** A hull running dark is not
    # on the plot until it is close, and a cloaked one barely then — which is
    # what a cloak is *for*, and why flying fast through a busy system in a
    # cheap hull is now a real risk rather than a free one.
    from . import detection
    for sight in getattr(conn, "sky", ()) or ():
        kind = getattr(sight, "kind", "")
        if kind not in ("body", "anchorage", "hull"):
            continue
        fix = detection.track(game, conn, getattr(sight, "name", "?"), kind,
                              getattr(sight, "at", (0.0, 0.0, 0.0)),
                              getattr(sight, "look", ""))
        if fix is None:
            continue                     # nothing on it: no warning to give
        got = _measure(conn, fix.name, kind,
                       getattr(sight, "at", (0.0, 0.0, 0.0)),
                       float(getattr(sight, "radius_km", 0.0) or 0.0), fix)
        if got is not None:
            found.append(got)
    if not found:
        return None
    worst = min(found, key=lambda t: (t.slack, t.seconds))
    return worst if worst.level != "clear" else None


def brake_velocity(conn, threat: Threat) -> list:
    """The velocity that keeps her stoppable: the excess taken off the line.

    Only the component *toward* the hazard is touched. Lateral motion is not
    the problem and cancelling it would be the computer fighting the pilot
    over something that was never dangerous.
    """
    toward = [-p for p in conn.pos] if threat.km <= 0 else None
    # Rebuild the bearing from the same measurement the scan used.
    if toward is None:
        toward = [0.0, 0.0, 0.0]
    unit = _bearing(conn, threat)
    allowed = safe_closing(conn, threat)
    excess = threat.closing - allowed
    if excess <= 0:
        return list(conn.vel)
    return [v - u * excess for v, u in zip(conn.vel, unit)]


def _bearing(conn, threat: Threat) -> list:
    """A unit vector from the ship to whatever the threat is.

    Recovered from the geometry rather than stored, so a threat measured a
    tick ago and acted on now points where the hazard is *now*.
    """
    for sight in getattr(conn, "sky", ()) or ():
        if getattr(sight, "name", None) == threat.name:
            at = getattr(sight, "at", (0.0, 0.0, 0.0))
            vec = [a - p for a, p in zip(at, conn.pos)]
            span = math.dist(vec, (0.0, 0.0, 0.0)) or 1.0
            return [c / span for c in vec]
    span = math.dist(conn.pos, (0.0, 0.0, 0.0)) or 1.0
    return [-p / span for p in conn.pos]


def safe_closing(conn, threat: Threat) -> float:
    """The fastest she may close on this and still be stopped in the room.

    The same shape as `autopilot.rate_for`, which is the braking law an
    approach already flies to — asked here of a hazard rather than of a
    berth, and with the comfortable margin `EASY` built in so the computer
    aims to be *easy*, not merely possible.
    """
    room = max(0.0, threat.room_km * 1000.0 / EASY)
    return math.sqrt(max(0.0, 2.0 * _accel(conn) * room))


def allow_burn(conn, axis: str | None, main: bool, threat) -> tuple[bool, str]:
    """May the pilot make this burn by hand? The safety guard, and its reason.

    Deliberately narrow. Flying by hand is allowed to be dangerous — that is
    most of why anyone does it — so this refuses one thing only: a burn that
    would push her *harder* into something she can no longer stop for. Every
    other burn, including a leisurely drift into a quay, is the pilot's.

    Switch `Conn.safeties` off and it refuses nothing at all.
    """
    if axis is None or threat is None or not getattr(conn, "safeties", True):
        return True, ""
    if threat.level != "imminent":
        return True, ""
    from .conn import thrust_axis
    push = thrust_axis(conn, axis, main)
    unit = _bearing(conn, threat)
    if sum(a * b for a, b in zip(push, unit)) <= 0.05:
        return True, ""                  # away from it, or across: allowed
    return False, (
        f"Safeties: {threat.name} is {threat.room_km * 1000:,.0f} m off at "
        f"{threat.closing:,.1f} m/s and she cannot be stopped in that. That "
        "burn makes it worse. Turn the safeties off if you mean it.")


def line(threat) -> str:
    """One sentence for a screen. Empty when there is nothing to say."""
    if threat is None:
        return ""
    when = (f"{threat.seconds:,.0f} s" if threat.seconds < 600
            else f"{threat.seconds / 60:,.0f} min")
    fix = getattr(threat, "track", None)
    if fix is not None and (fix.estimated or fix.hiding.share < 1.0):
        when += " (estimated"
        when += (f", {fix.hiding.name})" if fix.hiding.share < 1.0 else ")")
    if threat.level == "imminent":
        return (f"COLLISION — {threat.name} in {when} at "
                f"{threat.closing:,.1f} m/s, and she cannot be stopped in the "
                "room left.")
    if threat.level == "brake":
        return (f"Closing {threat.name}: {when} at {threat.closing:,.1f} m/s. "
                "Braking now leaves little to spare.")
    return (f"{threat.name} ahead — {when} at {threat.closing:,.1f} m/s. "
            f"Stopping wants {threat.stop_km * 1000:,.0f} m of the "
            f"{threat.room_km * 1000:,.0f} left.")


def tint(threat) -> str:
    return {"imminent": "bad", "brake": "warn"}.get(
        getattr(threat, "level", ""), "osteo")
