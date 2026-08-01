"""Forcing a berth: the ship's answer to a structure that will not open.

`sim/control.py` is the authority a dock has over the volume round it — who
holds which berth, what you were cleared for, and the quiet refusal that is
every structure's floor: no boom swung out, no hatch opened, no lines across.
This is the other side of that conversation, and the only thing in the game
that gets a hull alongside somewhere it was told to stay away from.

**It is deliberately not a die roll.** Forcing a berth is holding station on a
fitting nobody is working and cutting your way into it — so it takes time
measured in tens of minutes, it costs the hull doing the grinding, and,
crucially, *the ward does not stop while you do it*. That is the whole design.
A wayside quay with nothing but a radio can be forced by anybody patient
enough. A capital port cannot, because its guns are still firing for the whole
half hour the cut takes, and the arithmetic of that is not close. The
structure's `control.means` sets both the time and whether anything is
shooting, so the two halves cannot drift apart.

And it is where an approach finally becomes political. `grievance` is the one
door between the flying and the sector's memory: below being fired on, nothing
is remembered, because a grudge has to mean something.
"""

from __future__ import annotations

from . import control

#: How long cutting into a fitting takes where nothing much is stopping you.
#:
#: Ten minutes, which is ten ticks — long enough that it is a decision to
#: commit to and short enough to sit through. Under about four ticks a captain
#: could force a berth almost absent-mindedly while station-keeping, and the
#: refusal would stop meaning anything.
FORCE_SECONDS = 600.0

#: What each rung of a structure's `means` adds to that.
#:
#: Not because a capital's collars are thicker but because there is more in the
#: way of them: guards, interlocks, and people. Four rungs takes a cut from ten
#: minutes to half an hour, which at the top of the ladder is longer than a
#: hull survives.
FORCE_PER_MEANS = 300.0

#: What grinding your own bow against somebody else's collar costs you, in
#: hull a second.
#:
#: Small per second and not per tick: over the ten-minute floor it comes to
#: about twelve points, which is a repair bill rather than an injury. The thing
#: that kills you while forcing is the ward, and this must stay well under it
#: or the cost would be the wrong shape — a hull should be able to force an
#: undefended quay and live.
FORCE_BITE = 0.02

#: The rung from which the power holding a structure remembers the approach.
#:
#: `LADDER` index 3 is "warded" — shot at. Being hailed and being warned are
#: things that happen to careless captains all the time, and a sector where
#: every power bore a grudge over a radio call would have no room left for the
#: ones that matter.
GRIEVANCE_FROM = 3

#: What forcing scores on the same scale, above the top of the ladder.
FORCED_RUNG = 5


def forcible(conn) -> str:
    """Why this berth cannot be forced, or "" if it can.

    The interesting refusal is the second one. **A standoff berth cannot be
    forced at all**, and that falls out of the physics rather than being a
    rule: there is nothing to cut. A hull at a standoff berth is holding
    station in open space and the boom that would reach it is inboard, on the
    far side of the structure, where no amount of determination reaches. So
    the berths that come out to meet you are also the berths that can simply
    decline to — which is a genuine defensive property of a kind of dock, and
    the game did not have one before.
    """
    if not control.withheld(conn):
        return "Nothing is being withheld here."
    from . import moorings
    if moorings.sort_of(conn.target) == "standoff":
        return ("Nothing here to force. The boom is theirs and it stays "
                "inboard — a hull holding station in open space has nothing "
                "to get hold of.")
    found = moorings.nearest(conn)
    if found is None or not found["at_it"]:
        return "You have to be on the berth before you can cut into it."
    return ""


def force(conn) -> str:
    """Give the order, and say what the ship is being told.

    An order rather than a state, because it must be a decision: the hull is
    already sitting on the berth doing nothing when it is given, and a cut
    that started itself would be a chronicle-ending act nobody chose.
    """
    why = forcible(conn)
    if why:
        conn.forcing = False
        return why
    conn.forcing = True
    return force_line(conn)


def force_seconds(conn) -> float:
    """How long the cut takes here, from what the structure has."""
    watch = getattr(conn, "watch", None) or {}
    return FORCE_SECONDS + FORCE_PER_MEANS * float(watch.get("means", 0) or 0)


def forced(conn) -> bool:
    """Is the hatch open because this ship opened it?"""
    return float(getattr(conn, "cut", 0.0)) >= 1.0


def force_step(conn, seconds: float) -> float:
    """One tick of cutting. Returns how far through, 0 to 1.

    Progress is *kept* when the hull drifts off the berth, unlike the boom,
    which runs back in. A cut is a cut: the metal does not heal because you
    lost station for a minute. What presence buys is the right to carry on,
    and holding a berth for half an hour while being shot at is quite hard
    enough without the work undoing itself.
    """
    done = float(getattr(conn, "cut", 0.0))
    if not getattr(conn, "forcing", False) or done >= 1.0:
        return done
    if forcible(conn):
        return done
    conn.cut = min(1.0, done + float(seconds) / force_seconds(conn))
    conn.damage = round(conn.damage + FORCE_BITE * float(seconds), 1)
    return conn.cut


def force_line(conn) -> str:
    """What a hull cutting its way in has to show for it."""
    if forced(conn):
        said = getattr(conn, "cleared", None)
        station = (getattr(said, "station", "") if said else "") or "The berth"
        return (f"{station}'s collar is open — because you opened it. Nobody "
                "is going to forget this.")
    if not getattr(conn, "forcing", False):
        return ""
    done = float(getattr(conn, "cut", 0.0))
    left = force_seconds(conn) * (1.0 - done) / 60.0
    return (f"Cutting in: {done * 100:,.0f}% through, about {left:,.0f} "
            f"minutes to go, and they are still out there.")


def provoked(conn) -> int:
    """How far this approach pushed a structure, for the aftermath to price."""
    if forced(conn):
        return FORCED_RUNG
    return int(getattr(conn, "told", 0))


def grievance(conn) -> dict:
    """What the power holding this structure will remember, if anything.

    The one door between an approach and the sector's politics. Empty for
    everything up to and including a warning, because a grudge has to mean
    something: what goes in the books is being *fired on* and, worse, getting
    in anyway.
    """
    rung = provoked(conn)
    if rung < GRIEVANCE_FROM:
        return {}
    # The kinds are `sim/memory.WEIGHT` entries, and that is not a detail:
    # a note whose kind nobody weighs is a memory nobody feels. Both of these
    # went in as `approach` and `forced` first, weighed nothing, and moved a
    # power's opinion of the captain by exactly 0.00 either way.
    watch = getattr(conn, "watch", None) or {}
    said = getattr(conn, "cleared", None)
    where = (getattr(said, "station", "") if said else "") or "one of its docks"
    if forced(conn):
        return {"faction": watch.get("faction", "") or "",
                "kind": "forced",
                "text": f"Cut into a berth at {where} that was refused them.",
                "salience": 2.0}
    return {"faction": watch.get("faction", "") or "",
            "kind": "trespass",
            "text": f"Came on at {where} until it opened fire.",
            "salience": 1.0}
