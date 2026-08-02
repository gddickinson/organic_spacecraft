"""Approach control: who holds which berth, and what you were told.

Measured before this file existed, by flying it. A conn opened on a Fleet Hub
is cleared — and then nothing ever asks again:

    Fleet Hub: cleared for mast 4, hold at 555 m, 1.5 m/s or under.
    ... flew in regardless -> berthed at mast 3

**The clearance was advisory.** `sim/clearance` assigned mast 4, `sim/moorings`
picked whichever mast was nearest on the way in, and `sim/outcome` moored the
ship to that one without asking whether it was the one granted. A *refusal*
stopped nothing at all: the record came back `granted=False` and the physics
never read it, so a hull told to keep its distance flew in and made fast.

And the berths were empty in the strongest sense. Four masts on a hub, and
`moorings.assign` chose between them with no notion of anybody being there —
while five hulls of traffic worked the same system and not one of them was ever
at a dock. A structure with four berths had four berths for ever, whoever else
was in the sector.

So this is the authority a structure has over the volume around it, and it
answers three questions the game could not ask:

- **Who is in each berth**, derived rather than stored — the same discipline as
  `sim/anchorage`, which builds a quay's whole existence fresh every call. A
  hull that has arrived somewhere is at one of its berths, and which one is a
  function of the hull, so nothing has to be saved and nothing can drift.
- **What you were cleared for**, kept on the approach and consulted at the end
  of it rather than printed once at the start.
- **What the structure withholds.** This is the quiet one and it is the most
  useful: a dock that does not want you does not have to shoot. It declines to
  swing the boom out, and a standoff berthing simply cannot be completed. The
  machinery for that already existed — `moorings.boom_step` runs the arm out
  and `moorings.captured` asks whether it has you — and had no way to say no.
"""

from __future__ import annotations

import math

from . import traffic as traffic_sim

#: How far along its leg a hull has to be before it counts as arrived.
#:
#: `traffic.Hull.along` runs 0 to 1 across the leg it is flying, so this is the
#: last few per cent of the run in. Deliberately not 1.0: a hull exactly at the
#: end is a hull about to turn round, and a berth that only fills at the very
#: last instant would read as never full.
DOCKED_FROM = 0.88

#: Which errands tie up at a structure at all. A patrol holds station *near* a
#: berth without occupying one, and a prospector is at a body rather than a
#: dock — so neither takes a berth another hull could have used.
DOCKING = ("trader", "courier")


def _berth_names(game, contact) -> list:
    from .targets import target_from_contact
    from . import moorings
    try:
        target = target_from_contact(game, contact)
    except Exception:
        return []
    return [name for name, _at in moorings.points(target, 0.0)]


def holders(game, contact) -> dict:
    """Which berths are taken, as `{berth: the hull in it}`.

    Derived from where the traffic actually is, so a berth fills when somebody
    arrives and empties when they leave, and none of it is stored. Which berth
    a given hull takes is a function of its id: stable across a reload, and
    stable across the tick, without a field to save.
    """
    names = _berth_names(game, contact)
    index = getattr(contact, "body_index", None)
    if not names or index is None:
        return {}
    out: dict = {}
    for hull in traffic_sim.in_system(game):
        if hull.errand not in DOCKING or hull.to_body != index:
            continue
        if hull.along < DOCKED_FROM:
            continue
        seat = sum(ord(c) for c in hull.id) % len(names)
        out.setdefault(names[seat], hull.name)
    return out


def free(game, contact) -> list:
    """The berths a structure could actually offer right now."""
    taken = holders(game, contact)
    return [name for name in _berth_names(game, contact) if name not in taken]


def full(game, contact) -> bool:
    """Every berth taken. A real answer to "may I come in" and a common one."""
    names = _berth_names(game, contact)
    return bool(names) and not free(game, contact)


def waiting_line(game, contact) -> str:
    """What the structure says about its own occupancy."""
    names = _berth_names(game, contact)
    if not names:
        return ""
    taken = holders(game, contact)
    if not taken:
        return f"{len(names)} berths, all of them clear."
    who = ", ".join(f"{berth} ({hull})" for berth, hull in sorted(taken.items()))
    return (f"{len(names) - len(taken)} of {len(names)} berths clear; "
            f"{who} occupied.")


# ── what the structure told you, and whether it is still true ──────────────

def has_control(conn) -> bool:
    """Whether anybody is running this structure's approaches.

    A Weave anchor has nobody in it — it is a ring somebody left, and it grants
    nothing, withholds nothing and cannot be defied. Control is a thing a
    *station* has, so the test is whether one spoke.
    """
    said = getattr(conn, "cleared", None)
    return bool(said is not None and getattr(said, "station", ""))


def cleared_for(conn) -> str:
    """The berth this hull was granted, or "" if it was refused one.

    `Conn.cleared` has carried the whole `Clearance` since the protocol landed,
    with a docstring saying it is there "so a berth assigned by the port cannot
    be quietly swapped for one the ship preferred". Flown, it could: cleared for
    mast 4 and moored to mast 3, because nothing downstream read the field.
    """
    said = getattr(conn, "cleared", None)
    if said is None or not getattr(said, "granted", False):
        return ""
    return getattr(said, "berth", "") or ""


def welcome(conn) -> bool:
    """Is this hull here with permission?

    **A world does not mind you in orbit. It minds you coming down.** That is
    the whole difference between a structure's authority and a settlement's,
    and it falls out of what each is: a station's question is which berth you
    were given, and a world has no berths and no opinion whatever about the
    sky above it — right up until a hull starts down through it.

    So the same ladder serves both. Nothing here is a second copy of the
    hailing, the warning, the ward or the grievance; a settled world simply
    stops being welcoming at the moment the order to descend is given.
    """
    if getattr(getattr(conn, "target", None), "kind", "") == "body":
        from . import landing
        return not (has_control(conn) and landing.ditching(conn))
    return not has_control(conn) or bool(cleared_for(conn))


def at_own_berth(conn) -> bool:
    """Is the hull actually on the berth it was cleared for?

    **Structural rather than a rule.** `moorings.assign` returns the berth the
    port gave, so `moorings.nearest` measures the gap to *that* fitting and no
    other — a hull sitting perfectly on mast 2 while cleared for mast 4 is
    eight hundred metres from the only berth that counts. Nothing has to forbid
    it; there is simply nowhere else to tie up.

    That came out of a regression. Enforcing the assignment while the flight
    computer still steered for the nearest fitting sent a hand-flown approach
    to a berth that would not open, and it burned to dry 22 m off it.
    """
    from . import moorings
    if not cleared_for(conn):
        return False
    found = moorings.nearest(conn)
    return bool(found and found["at_it"])


def withheld(conn) -> bool:
    """Is the structure declining to work its equipment for this hull?

    The quiet defence, and the one every dock has whatever else it has: no
    boom swung out, no hatch opened, no lines across. A hull that came in
    uncleared can sit perfectly on the berth for as long as it likes.

    Only the welcome is asked here. Being on the *wrong* berth is handled a
    layer down and more simply — see `at_own_berth`.
    """
    if not has_control(conn):
        return False
    if not welcome(conn):
        from . import forcing
        # Unless the ship opened it itself. See `sim/forcing.py`: a hatch cut
        # open is open, and everything downstream — the boom, `at_berth`, the
        # whole berthing — must agree, or forcing would be a progress bar that
        # bought nothing.
        return not forcing.forced(conn)
    return False


def refusal_line(conn) -> str:
    """What a hull sitting at a berth nobody will work is being told."""
    if not withheld(conn):
        return ""
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    if not welcome(conn):
        return (f"{station} has not cleared you and is not opening. Nothing "
                "here is going to reach out and take your lines.")
    want = cleared_for(conn)
    return (f"{station} made {want} ready and you are not on it. The berth "
            "you are against is somebody else's, and it stays shut.")


# ── the ladder ─────────────────────────────────────────────────────────────
#
# What a structure does about a hull it has not cleared, in order. Each rung
# is a thing the station can actually do, and how far up it will go is set by
# what it *has* rather than by how cross it is.

#: The rungs, in order. An index into this is what `Conn.told` carries.
LADDER = ("clear", "hailed", "warned", "warded", "repelled")

#: What each rung says, in the words a bridge would hear it.
SAID = {
    1: "{station}: unidentified hull inside our approaches. State your "
       "intentions.",
    2: "{station}: you are not cleared and you are still closing. Come about "
       "now.",
    3: "{station} is firing. Point defence, ranging shots across your bow.",
    4: "{station} has vectored an armed response onto you.",
}

#: Ticks of continued closing before the structure goes up a rung.
#:
#: Six minutes at a tick a minute. Long enough that a captain who blunders in
#: and corrects is hailed and forgiven, short enough that ignoring three
#: warnings is a decision rather than an accident.
GRACE = 6

#: What standing does to that patience, as a multiplier on the grace. A power
#: that likes you gives you longer to explain yourself; one that does not goes
#: up the ladder in half the time. Neither changes the ceiling — a friendly
#: quay with no guns still has no guns.
PATIENCE = ((40.0, 1.75), (10.0, 1.25), (-20.0, 1.0), (-60.0, 0.6), (-1e9, 0.4))

#: What point defence takes off a hull each tick it is being warded, and how
#: much worse it gets for every further tick.
#:
#: Ranging shots first and then the real thing: at 1.4 a hull with a hundred
#: points of structure has about eleven ticks — eleven minutes — before this
#: alone kills it, and the first two or three cost almost nothing. Persisting
#: is what is expensive, which is the shape a warning should have.
WARD_BITE = 1.4
WARD_CLIMB = 0.35


def patience_for(rep: float) -> float:
    """How much grace this standing buys, as a multiple of `GRACE`."""
    for floor, factor in PATIENCE:
        if rep >= floor:
            return factor
    return PATIENCE[-1][1]


def means(game, contact) -> int:
    """How far up the ladder this structure can actually go.

    Off what it has, all of which already existed and none of which touched an
    approach: a port's `level`, whether it is a `capital`, and whether anything
    in the system is warding it. A wayside quay can shout and no more.
    """
    kind = getattr(contact, "kind", "")
    if kind == "body":
        from . import interdiction
        return interdiction.means(game, contact)
    if kind != "anchorage":
        return 0
    system = getattr(game, "system", None)
    port = getattr(system, "port", None) if system is not None else None
    if port is None:
        return 2                       # somebody is talking, and that is all
    top = 2
    from . import colony as colony_sim
    warded = colony_sim.is_warded(game, system.id) if system else False
    if port.level >= 2 or warded:
        top = 3
    if port.capital and _hulls_here(game, system, port):
        # **The top rung needs something that can come out after you.**
        # `repelled` is not a heavier gun, it is being driven off — and a
        # capital with no squadron on station cannot drive anybody anywhere,
        # however grand its berths are. See `sim/fleets`: what a power keeps
        # in space is what its margin sustains once its ports are paid for,
        # so a power that overextends loses the ability to see you off before
        # it loses anything else.
        top = 4
    return top


def _hulls_here(game, system, port) -> int:
    """How many of this port's own power's hulls are on station here."""
    from . import fleets
    return fleets.guard_at(game, system, getattr(port, "faction", "") or "")


def post(game, contact) -> dict:
    """Everything the approach needs to run the ladder without the game.

    Set once when the approach opens, the way the clearance is — so the tick
    loop in `sim/conn` can escalate without reaching for a world it has no
    handle on.
    """
    faction = getattr(contact, "faction", None) or _behind(game, contact)
    rep = float(getattr(game, "rep", {}).get(faction, 0.0)) if faction else 0.0
    return {"means": means(game, contact), "grace": max(
        1, round(GRACE * patience_for(rep))), "faction": faction,
        "floor": _floor(game, contact)}


def _behind(game, contact) -> str:
    """Which power answers for a world, for the aftermath to bill.

    A `Contact` for an anchorage carries its own `faction`; one for a body
    carries nothing, because until `sim/interdiction.py` no world answered for
    itself. So the claim supplies it, and the whole political tail — the
    grievance, the standing, the memory that can name the day — reaches a
    captain who shot their way down onto somebody's workings.

    Empty for a quiet site, deliberately: `Claim.who` is "" for a thing nobody
    admits to, so there is nobody to bear the grudge. Surviving one leaves no
    record anywhere, which is most of what makes it frightening.
    """
    if getattr(contact, "kind", "") != "body":
        return ""
    from . import interdiction
    said = interdiction.claim(game, contact)
    return said.who if said is not None else ""


def _floor(game, contact) -> int:
    """The rung this authority opens at. Zero for anything that hails first."""
    if getattr(contact, "kind", "") != "body":
        return 0
    from . import interdiction
    return interdiction.floor(game, contact)


def haste(conn) -> float:
    """How much faster than a berthing this hull is coming in.

    One at the rate the structure asked for, and it climbs from there. Flown,
    this is the difference between a station getting a word out and not: an
    approach pressed at full drive covers twelve kilometres in twenty ticks,
    and a ladder that advanced once every six of them managed a hail and a
    warning before the hull was on top of it — while a hull merely *drifting*
    in got the full four rungs, because it took two hundred ticks to arrive.
    Patience measured in ticks is patience measured in the wrong thing.
    """
    said = getattr(conn, "cleared", None)
    allowed = float(getattr(said, "max_closing", 0.0) or 0.0) if said else 0.0
    if allowed <= 0.0:
        return 1.0
    return max(1.0, float(getattr(conn, "closing", 0.0)) / allowed)


def step(conn, closing_in: bool) -> str:
    """One tick of a structure's patience. Returns a line, or "".

    De-escalates the moment the hull stops closing, so the ladder is a
    conversation about your vector rather than a countdown: check up or open
    the range and the station stops climbing. That is what makes it a warning
    instead of a sentence.

    And a tick of patience is spent faster the harder the hull is coming —
    see `haste`. The clock a station keeps is the range, not the calendar.
    """
    watch = getattr(conn, "watch", None)
    if not watch or welcome(conn) or not has_control(conn):
        conn.told = 0
        conn.told_for = 0
        return ""
    if not closing_in:
        conn.told_for = 0
        return ""
    conn.told_for = getattr(conn, "told_for", 0) + haste(conn)
    if conn.told_for < watch.get("grace", GRACE):
        return ""
    conn.told_for = 0
    ceiling = int(watch.get("means", 0))
    # **Not everything hails.** A structure works up the ladder a rung at a
    # time because it wants you to stop; a thing that would rather not be
    # looked at opens where it means to finish. `floor` is zero for every
    # station in the game and nonzero only for what `sim/interdiction.py`
    # calls a quiet site — see `Claim.floor`.
    start = max(int(conn.told), int(watch.get("floor", 0)) - 1)
    if start >= ceiling:
        return ""
    conn.told = min(ceiling, start + 1)
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    return SAID.get(conn.told, "").format(station=station)


def ward_bite(conn) -> float:
    """What being fired on costs this tick, in hull.

    Climbs the longer it goes on. The first shots are ranging and the hull
    barely feels them; a captain who keeps coming is being killed by degrees,
    and can see it happening.
    """
    if int(getattr(conn, "told", 0)) < 3:
        return 0.0
    held = int(getattr(conn, "warded_for", 0))
    return WARD_BITE + WARD_CLIMB * held


# ── standing off ───────────────────────────────────────────────────────────
#
# The measure a structure has when it has no guns, and takes as well when it
# does: it is simply not there when you arrive. `sim/knock` already holds
# "and then it was shoved" as a velocity with a date on it, read by `track.at`
# — the one door for where anything is — so a station that sheers off is off
# station on the plot, in the readiness board's ranges and in every forecast,
# because all of them ask the same function.

#: How fast a structure will work itself away from a hull it does not want,
#: in metres a second.
#:
#: Slow, because a station is enormous and this is station-keeping thrust
#: rather than a manoeuvre. At half a metre a second an hour's stubbornness
#: opens 1.8 km — real against a twelve-kilometre approach, and catchable by
#: a captain willing to spend the mass. Being unwelcome should cost fuel
#: rather than be forbidden.
SHEER_RATE = 0.5

#: The rung at which a structure starts moving. It warns first: sheering off
#: without a word would read as the station being broken.
SHEER_FROM = 2


def sheers(conn) -> bool:
    """Is this structure working itself away from the hull?

    Only one that has somebody aboard to do it. A Weave anchor does not sheer
    off, and neither does a derelict — `knock.keeps_station` is the same
    question asked of a shove, and the same answer serves.
    """
    if welcome(conn) or not has_control(conn):
        return False
    return int(getattr(conn, "told", 0)) >= SHEER_FROM


def sheer_step(conn, seconds: float) -> float:
    """Open the range by what the structure managed this tick, in km.

    In the approach's frame the structure is the origin, so its moving away
    is the hull's position growing. Applied to the position rather than the
    velocity on purpose: the station is not pushing the ship, it is leaving,
    and a hull that stops burning simply finds the berth further off than it
    was.
    """
    if not sheers(conn):
        return 0.0
    from . import moorings
    gone = SHEER_RATE * float(seconds) / 1000.0
    here = math.dist(conn.pos, (0.0, 0.0, 0.0))
    if here <= 1e-9:
        return 0.0
    grew = (here + gone) / here
    conn.pos = [c * grew for c in conn.pos]
    conn.sheered = round(getattr(conn, "sheered", 0.0) + gone, 6)
    # A berth that is running from you is not a berth you are at.
    moorings.boom_step(conn, 0.0)
    return gone


def sheer_line(conn) -> str:
    """What a pilot watching the range open is being told."""
    gone = float(getattr(conn, "sheered", 0.0))
    if gone <= 0.0:
        return ""
    said = getattr(conn, "cleared", None)
    station = (getattr(said, "station", "") if said else "") or "The station"
    return (f"{station} is under way and opening the range — {gone * 1000:,.0f} m "
            "so far. Whatever you meant to tie up to is leaving.")
