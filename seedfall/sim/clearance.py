"""Being cleared to dock: the structure assigns the berth and says how.

Berthing was something the *ship* worked out. `sim/moorings.py` read a table
of fittings, picked the nearest, and flew at it — and nobody ever asked the
quay whether it would have you. A hostile patrol and a Charter Fleet Hub
offered exactly the same welcome, which is to say none, because neither was
ever asked.

So the authority moves to where it belongs. A structure that is willing to
take a hull **issues a clearance**: which berth it has assigned, where that
berth is and how it is moving, where to hold before the run in, and the rate
it may be crossed at. The ship flies what it is told.

That is truer to the fiction and it is also the thing every later kind of
berth needs. A dock standing off the structure on a boom, or a bay inside one
big enough to fly into, cannot be inferred from a mesh by an approaching
pilot: they are *procedures*, and a procedure has to be sent.

**A refusal is an answer.** A hull that means you harm does not clear you. A
Weave gate is a relic with nothing to tie up to. A world is orbited, not
docked with. Each says so in its own words, because "no" with a reason is a
thing a captain can act on and a greyed-out button is not.

`sim/moorings.py` stays the geometry — where the fittings are, and where an
approach is flying. This is the authority over which one you get.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..core.save import register
from . import bays
from . import control
from . import tug as tug_sim
from . import moorings

#: Standing below which a port turns you away from its quays. Well under the
#: point where a faction is hostile: a power that dislikes you will still sell
#: you fuel, and one that has been shot at by you will not.
WELCOME_AT = -40.0


@register
@dataclass
class Clearance:
    """What a structure has told an approaching hull."""

    granted: bool
    why: str = ""
    #: Which berth, and where it is *now*, in the target's own frame.
    berth: str = ""
    at: tuple = (0.0, 0.0, 0.0)
    #: What sort of berth it is. `arm` and `mast` are fittings on the hull of
    #: the structure; the sorts that stand off it or lie inside it are the
    #: next slice of this, and are named here so the field means something
    #: before they exist rather than being widened later.
    sort: str = "fitting"
    #: How the structure is moving, so the approach can match it: seconds for
    #: one turn, and the speed the berth itself travels at.
    turn_seconds: float = 0.0
    berth_speed: float = 0.0
    #: Where to hold before the run in, and how near counts as arrived.
    hold_km: float = 0.0
    reach_km: float = 0.0
    #: The condition the structure imposes, in m/s.
    max_closing: float = 0.0
    #: How wide the way in is, for a structure you fly into. Zero for the
    #: rest, which is every berth you come alongside.
    bore_km: float = 0.0
    #: Whether this structure keeps boats. A cleared hull that holds steady in
    #: the corridor is taken in on the tug's mass rather than its own — which
    #: is what being cleared *buys*, as against merely being allowed.
    tug: bool = False
    #: Who is speaking, for the log and the screens.
    station: str = ""
    services: tuple = field(default_factory=tuple)


def request(game, contact, conn=None) -> Clearance:
    """Ask a structure for a berth. The one door for "may I dock, and where".

    `conn` is optional: with an approach in hand the structure assigns the
    fitting nearest the ship, which is what any port would do. Without one it
    still answers — a captain is entitled to know whether they would be
    welcome before they burn the mass to get there.
    """
    if contact is None:
        return Clearance(False, "Nothing selected.")
    kind = getattr(contact, "kind", "")
    if kind in ("body", "star"):
        # **A settled world names whoever is on it**, and that is the whole of
        # how it gets a say. `control.has_control` asks whether anybody spoke;
        # an empty world says nothing and can be flown at as freely as it
        # always could, while one with a settlement on it is a place with
        # somebody in charge of the sky. What they do about it is
        # `sim/interdiction.py`, and they do nothing at all about an orbit.
        from . import interdiction
        who = interdiction.claim(game, contact)
        return Clearance(
            False, f"{contact.name} is a world. You orbit it; "
                   "there is nothing to tie up to."
            + (f" {who.name} is down there and watching."
               if who is not None else ""),
            station=(who.name if who is not None else ""))
    if kind == "point":
        return Clearance(False, "There is nothing there to dock with.")
    if getattr(contact, "hostile", False):
        return Clearance(False, f"{contact.name} does not answer, and is "
                                "closing. Nobody is clearing you anywhere.")
    if kind == "anchorage" and getattr(contact, "berth", "") == "gate":
        return Clearance(False, f"{contact.name} is a Weave gate. It has hung "
                                "there since before the Verge was settled and "
                                "has no provision for tying up to.")

    standing = _standing(game, contact)
    if standing is not None and standing < WELCOME_AT:
        return Clearance(False, f"{contact.name} refuses you the quay: "
                                f"standing {standing:+.0f}.")

    target = _target_of(game, contact, conn)
    berths = _berths(game, contact, conn)
    if not berths:
        # (`control` is imported at module scope. A second `from . import`
        # down here would make the name local to this whole function and
        # unbind it at the *earlier* uses — the exact trap `core/clock` fell
        # into when the machines' tick was added.)
        if control.full(game, contact):
            # A different refusal from "there is nothing here": every berth
            # is worked and somebody is on it. Hold off and wait, or go.
            return Clearance(
                False,
                f"{contact.name} is full — "
                + control.waiting_line(game, contact)
                + " Hold off until one clears.",
                station=contact.name)
        return Clearance(False, f"{contact.name} has no berth to offer.")
    name, at = _assign(berths, conn)
    period = (moorings.turn_seconds(target)
              if kind == "anchorage" and target is not None else 0.0)
    return Clearance(
        granted=True,
        why=f"{contact.name} clears you for {name}.",
        berth=name, at=tuple(at),
        # A structure you fly *into* gives a different instruction from one
        # you come alongside, and the field was named for it before it
        # existed — "the sorts that stand off it or lie inside it are the
        # next slice of this". This is that slice.
        sort=("collar" if kind == "hull"
              else "bay" if bays.is_bay(getattr(target, "berth", "") or "")
              else moorings.sort_of(target)),
        turn_seconds=period,
        berth_speed=moorings.rim_speed() if period > 0.0 else 0.0,
        hold_km=(moorings.corridor_km(target) if kind == "anchorage"
                 else float(getattr(target, "radius_km", 0.0) or 0.0) * 2.0),
        reach_km=(moorings.reach_km(target) if kind == "anchorage"
                  else float(getattr(target, "radius_km", 0.0) or 0.0)
                  * HULL_REACH),
        bore_km=(bays.bore_km(target) if kind == "anchorage" else 0.0),
        tug=tug_sim.has_tug(game, contact),
        max_closing=(moorings.hold_rate(target)
                     if kind == "anchorage"
                     and moorings.sort_of(target) == "standoff"
                     else _max_closing()),
        station=contact.name,
        services=tuple(getattr(contact, "services", ()) or ()),
    )


def _standing(game, contact):
    """What the power behind this berth thinks of you, or None if nobody is."""
    faction = getattr(contact, "faction", None)
    if not faction or game is None:
        return None
    return float(game.rep.get(faction, 0.0))


#: Where a hull's own hard point sits, as a share of its radius, and how near
#: counts as on it. A ship being docked with has no masts and no arms — it has
#: a place amidships where a collar mates — so it offers exactly one, and the
#: tolerance is generous because two hulls station-keeping have no structure
#: between them to be careful of.
HULL_POINT = 1.0
HULL_REACH = 0.6


def _target_of(game, contact, conn):
    """The thing with a size, which a `Contact` is not.

    `sim/track.Contact` carries a name and a kind; the radius lives on the
    `Target` an approach is built around. With an approach in hand that is
    `conn.target`; without one it is built the same way `conn.start` builds
    it, so a captain asking from the chart gets the same answer they will get
    from the cockpit.
    """
    if conn is not None and getattr(conn, "target", None) is not None:
        return conn.target
    from . import conn as conn_sim
    try:
        return conn_sim.target_from_contact(game, contact)
    except Exception:
        return None


def _berths(game, contact, conn) -> list:
    """The fittings this structure has, in its own frame, turned to now."""
    target = _target_of(game, contact, conn)
    if target is None:
        return []
    kind = getattr(contact, "kind", "")
    if kind == "hull":
        # One hard point amidships. A hull is not a station and does not
        # pretend to be: it offers a collar, and that is the whole provision.
        radius = float(getattr(target, "radius_km", 0.0) or 0.0)
        if radius <= 0.0:
            return []
        return [("the collar", (radius * HULL_POINT, 0.0, 0.0))]
    if kind != "anchorage":
        return []
    spin = moorings.spin_at(target, getattr(conn, "elapsed", 0.0))
    # Only what is actually free. A structure with four masts and three hulls
    # already on them has one berth to offer, and had four for ever until
    # `sim/control` gave it a way to know who was there.
    taken = control.holders(game, contact)
    return [(name, at) for name, at in moorings.points(target, spin)
            if name not in taken]


def _assign(berths: list, conn):
    """Which berth the structure gives you: the one nearest, as any port would.

    The *structure* choosing is the point. It happens to choose the same berth
    `moorings.assign` would, and that is a policy rather than a coincidence —
    a port with one hull inbound puts it on the nearest free fitting.
    """
    if conn is None:
        return berths[0]
    import math
    return min(berths, key=lambda row: math.dist(conn.pos, row[1]))


def _max_closing() -> float:
    """The rate a structure will let you cross its threshold at."""
    from .conn import ALONGSIDE_RATE
    return ALONGSIDE_RATE


def line(cleared: Clearance) -> str:
    """One line for a screen, whichever way the answer went."""
    if not cleared.granted:
        return cleared.why
    if cleared.sort == "bay":
        # The manoeuvre nobody was told about. ARCA's berths are on the inner
        # wall of a drum: you fly the centreline in, and then you have to stop
        # and cross to the wall — carry on down the middle and you strike the
        # far end, which is what the physics does and what no screen said.
        said = (f"{cleared.station}: you are cleared inside for "
                f"{cleared.berth}. The way in is "
                f"{cleared.bore_km * 2000:,.0f} m across — hold the "
                f"centreline, mind the rim, and check up before you cross to "
                f"the berth at {cleared.max_closing:.1f} m/s or under")
        if cleared.berth_speed > 0.01:
            said += f"; the berth travels {cleared.berth_speed:.2f} m/s"
        return said + "."
    if cleared.sort == "standoff":
        # A different instruction, because it is a different act: nobody is
        # asking the hull to come alongside anything. It holds station off the
        # end of a gantry and the arm comes out and takes it.
        said = (f"{cleared.station}: cleared for {cleared.berth}. Hold "
                f"station off the boom at {cleared.max_closing:.2f} m/s or "
                "steadier and it will come out to you")
        if cleared.berth_speed > 0.01:
            said += f"; the gantry travels {cleared.berth_speed:.2f} m/s"
        return said + "."
    said = (f"{cleared.station}: cleared for {cleared.berth}, "
            f"hold at {cleared.hold_km * 1000:,.0f} m, "
            f"{cleared.max_closing:.1f} m/s or under")
    if cleared.tug:
        said += "; hold steady in the corridor and our boats will take you in"
    if cleared.berth_speed > 0.01:
        said += (f"; the berth travels {cleared.berth_speed:.2f} m/s, "
                 f"round once in {cleared.turn_seconds / 60:.0f} min")
    return said + "."
