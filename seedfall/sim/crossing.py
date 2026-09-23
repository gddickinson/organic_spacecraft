"""Getting from the hull into a place: made fast alongside it, or across.

A player found the chronicle opening with the hull hundreds of kilometres
off the Fleet Hub on the flight deck while the Hub's doors stood open to
them. The game had one fact — "in orbit of the world the quay is over" —
and read it both as *near* and as *inside*. Now they are two:

- **made fast** (`Game.berth`): the hull lies at a berth and the crew walks
  across the gangway. A chronicle starts that way at its home quay; coming
  alongside — the harbour's pilot (`dock`), or a conn that ends alongside —
  is how it gets that way anywhere else, and moving the hull casts off;
- **across** (`Game.ashore`): the crew is in a place the hull is not made
  fast to, having gone
  - by **the ship's boat** — a hull with a crew of `BOAT_CREW` or more
    carries one in a boat bay (walked afoot): no fare, to anything in this
    orbit, up in it or down on the ground;
  - by **their shuttle** — a quay, a station, a base's field, a drum or a
    settlement runs one up to hulls in orbit, for `FARE` a head at each
    step of amenity; your own holding's is yours;
  - in **suits on a line** — across open space to something in orbit no
    more than `EVA_KM` off, never down a gravity well. Whoever breathes
    goes in a vacc suit from the ship's lockers; a lineage that does not
    breathe goes as it is.

`ways` is every way there is here and why each of the others is not;
`cross` takes one; `across` is what every door asks and `barred` says it in
words. Business done from orbit — the cargo market, a yard's quote, repairs
— goes by lighter, as it always has: this is about people.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

#: The least crew a hull keeps a cradle deck for (`sim/afoot_program`): a
#: boat bay is a compartment, whether or not there is a craft in it.
BOAT_CREW = 6
#: The furthest a crew goes across open space on a line, in km.
EVA_KM = 2.0
#: A shuttle's fare a head, at each step of the place's amenity.
FARE = 12
#: How long each way takes, in minutes — on the one clock.
MINUTES = {"dock": 60, "boat": 25, "shuttle": 45, "suits": 20}
#: Places up in orbit, which a line can reach; the rest are on the ground.
ORBITAL = ("port", "station", "habitat", "kith")
#: Places that run a shuttle up to the hulls in orbit.
SHUTTLED = ("port", "station", "base", "habitat", "holding", "downside",
            "kith")

#: **What each way can carry home**, in tonnes. The way out is the way back,
#: and a party that went across on a line does not return with a hold's
#: worth of anything: they return with what is on their backs. Made fast
#: alongside there is no limit at all — the hold is right there.
#:
#: A boat carries her own hold (`data/craft.hold_t`) and can make this many
#: trips while the party is ashore; a shuttle takes a crate or two as
#: freight; suits carry this much a head.
BOAT_TRIPS, SHUTTLE_T, SUIT_T = 3, 2.0, 0.2
#: And the most any boat shifts in one visit, however big her hold. A
#: ship's boat is not a lighter: she has one pilot, one ramp and the hours
#: the party is ashore, and a lander with a season's supplies in her would
#: otherwise have made `sim/quayside`'s lighterage free for most of a
#: chronicle's trade.
LIFT_MOST = 12.0


@dataclass(frozen=True)
class Way:
    """One way across, and what it costs — or why not."""

    id: str
    label: str
    ok: bool
    why: str = ""
    cr: int = 0
    minutes: int = 0
    note: str = ""


# ── where a place is berthed ────────────────────────────────────────────────

def berth_for(place) -> str:
    """The anchorage a place's berth is (`sim/anchorage` id), or ""."""
    pid = str(getattr(place, "id", place))
    if pid.startswith(("port-", "est-")):
        return pid
    if pid.startswith("holding-"):
        return "colony-" + pid.split("holding-", 1)[1]
    return ""


def place_for(berth: str) -> str:
    """The place a berth belongs to (`sim/places` id)."""
    if berth.startswith("colony-"):
        return "holding-" + berth.split("colony-", 1)[1]
    return berth


def made_fast(game):
    """The anchorage the hull is made fast to, or None."""
    berth = getattr(game, "berth", "")
    if not berth:
        return None
    from . import anchorage
    return next((a for a in anchorage.in_system(game) if a.id == berth), None)


def across(game, place) -> bool:
    """Is the crew in this place, or free to walk into it?"""
    if place is None:
        return False
    if getattr(place, "kind", "") == "ship":
        return True
    berth = berth_for(place)
    return (getattr(game, "ashore", "") == place.id
            or bool(berth) and berth == getattr(game, "berth", ""))


def barred(game, place) -> str:
    """Why a door here is shut to the crew, or "" if they are across."""
    if across(game, place):
        return ""
    open_ = [w.label.lower() for w in ways(game, place) if w.ok]
    return (f"The crew is aboard, not at {place.name}. "
            + (f"Get across first: {', '.join(open_)}." if open_ else
               "There is no way across from here."))


# ── the ways ────────────────────────────────────────────────────────────────

def the_boat(game):
    """The craft the hull would send across, or None.

    **The boat is a craft in a cradle** (`sim/craft.py`) — a tender with
    seats behind the pilot, or a fighter with room for one more at a pinch —
    fuelled, on the cradle rather than out on a sortie, and with somebody
    aboard certified to fly it. A hull that carries none has no boat, and
    its crew crosses by somebody else's shuttle or on a line. Of several,
    the one that takes the most people.
    """
    from . import craft as craft_sim
    able = [got for got in craft_sim.aboard(game)
            if got.state == "cradled" and got.fuel > 0
            and craft_sim.best_pilot(game, got)]
    return max(able, key=seats_of, default=None)


def seats_of(craft) -> int:
    """How many people a craft takes across besides the one flying her.

    The pilot has a seat and it is not a passenger's: a DORY's four is the
    pilot and three behind them. A single-seater still squeezes one in at a
    pinch, which is what a cradle is for on a hull with no tender.
    """
    from . import craft as craft_sim
    return max(1, craft_sim.kind_of(craft).seats - 1)


def has_boat(game, heads: int = 1) -> bool:
    """Is there a boat, and will this many fit in it?"""
    boat = the_boat(game)
    return boat is not None and seats_of(boat) >= max(1, heads)


def lift_t(game, way_id: str, heads: int = 1) -> float:
    """Tonnes that can come home by this way.

    The rule the game implied and never enforced: a walk's haul went into
    the hold whole, however the party had got there — twelve tonnes carried
    back across two kilometres of vacuum on a line, by three people in
    suits. What comes home is what the way home holds.
    """
    if way_id in ("dock", "aboard", ""):
        return math.inf
    if way_id == "boat":
        boat = the_boat(game)
        if boat is None:
            return 0.0
        from . import craft as craft_sim
        return min(LIFT_MOST, craft_sim.kind_of(boat).hold_t * BOAT_TRIPS)
    if way_id == "shuttle":
        return SHUTTLE_T
    return SUIT_T * max(1, heads)


def range_km(game, place) -> float:
    """How far the hull is from a place's berth, in km (inf if it has
    none here)."""
    berth = berth_for(place)
    if not berth:
        return math.inf
    from . import anchorage, flight
    from ..data.starclasses import mu_of
    got = next((a for a in anchorage.in_system(game) if a.id == berth), None)
    if got is None:
        return math.inf
    body = game.system.bodies[got.body_index]
    at = flight.position(body, game.day, mu_of(game.system))
    off = anchorage.berth_orbit(berth, body, game.day)
    there = tuple(a + o for a, o in zip(at, off))
    return math.dist(flight.ship_position(game), there) * anchorage.KM_PER_AU


def _suited(game) -> tuple:
    """(ok, why): can this crew go across open space?"""
    from ..data.chassis import CHASSIS_BY_ID
    chassis = CHASSIS_BY_ID.get(getattr(game.ship, "chassis", ""))
    lockers = chassis is not None and int(chassis.crew or 0) > 0
    from . import afoot_people, lifespan
    begun = getattr(game, "beginning", None)
    lineage = afoot_people.LINEAGES_BY_ID.get(afoot_people.of_stock(
        getattr(begun, "stock", None))) or lifespan.lineage_of(None, game)
    if lockers or not getattr(lineage, "breathes", True):
        return True, ""
    return False, "No suit lockers aboard, and the captain breathes."


def ways(game, place, heads: int = 1) -> list:
    """Every way across to this place from where the hull is, best first:
    come alongside, the ship's boat, their shuttle, suits on a line."""
    out = []
    if across(game, place):
        return out
    here = bool(getattr(place, "here", False))
    away = "" if here else "Not in this orbit: fly there first."
    kind = getattr(place, "kind", "")
    berth = berth_for(place)
    # Come alongside: the harbour's pilot brings the hull in.
    if berth:
        why = away or _berth_refusal(game, berth)
        out.append(Way("dock", "Come alongside", not why, why, 0,
                       MINUTES["dock"],
                       "The harbour's pilot brings her in, and the crew "
                       "walks across."))
    # The ship's boat: whatever is on the cradle (`sim/craft.py`), and only
    # as many as she seats.
    boat = the_boat(game)
    if boat is None:
        why = away or "Nothing on the cradle to take you across."
    else:
        seats = seats_of(boat)
        why = away or ("" if seats >= max(1, heads) else
                       f"{craft_name(game, boat)} takes {seats} across "
                       f"besides the pilot; {heads} are going.")
    out.append(Way("boat", "The ship's boat", not why, why, 0,
                   MINUTES["boat"],
                   f"Your own boat, there and back — {seats_of(boat)} across "
                   f"and {lift_t(game, 'boat', heads):g} t home."
                   if boat is not None else
                   "A craft on the cradle, if you had one."))
    # Their shuttle.
    if kind in SHUTTLED:
        mine = bool(getattr(place, "mine", False))
        fare = 0 if mine else FARE * max(1, int(getattr(place, "amenity",
                                                        1))) * max(1, heads)
        why = away or ("" if game.credits >= fare else
                       f"The fare is {fare:,} cr.")
        out.append(Way("shuttle", "Your own shuttle" if mine else
                       "Their shuttle", not why, why, fare,
                       MINUTES["shuttle"],
                       "It meets the hull in orbit and takes you in — and "
                       f"takes {SHUTTLE_T:g} t home as freight."))
    # Suits on a line.
    if kind in ORBITAL:
        far = range_km(game, place)
        ok, why = _suited(game)
        why = away or ("" if far <= EVA_KM else
                       f"{far:,.0f} km of open space — a line reaches "
                       f"{EVA_KM:g}.") or why
        out.append(Way("suits", "Suits on a line", not why, why, 0,
                       MINUTES["suits"],
                       "Across the gap in vacc suits, whoever breathes."))
    out.sort(key=lambda w: (not w.ok, ["dock", "boat", "shuttle",
                                        "suits"].index(w.id)))
    return out


def _berth_refusal(game, berth: str) -> str:
    """Why the harbour will not bring the hull in, or "" — asked of the same
    door a conn asks (`sim/clearance.request`): the law, your standing with
    whoever holds it, and whether a berth is clear."""
    from . import clearance, track
    contact = next((c for c in track.contacts(game)
                    if c.kind == "anchorage" and c.id == f"quay:{berth}"),
                   None)
    if contact is None:
        return "There is no berth to come alongside."
    got = clearance.request(game, contact)
    return "" if got.granted else got.why


def best(game, place, heads: int = 1):
    """The way a crew would take without being asked: the boat, then a
    shuttle, then suits — never moving the hull to a new berth."""
    return next((w for w in ways(game, place, heads)
                 if w.ok and w.id != "dock"), None)


def cross(game, place, way_id: str, heads: int = 1) -> dict:
    """Go across by one way: paid, timed on the clock, and said."""
    if across(game, place):
        return {"ok": True, "text": ""}
    way = next((w for w in ways(game, place, heads) if w.id == way_id), None)
    if way is None or not way.ok:
        return {"ok": False, "why": way.why if way else
                "There is no such way across from here."}
    if way.id == "dock":
        from . import anchorage, flight
        got = next(a for a in anchorage.in_system(game)
                   if a.id == berth_for(place))
        flight.hold_at(game, game.system.bodies[got.body_index])
        game.berth = got.id
        game.flags["berths"] = int(game.flags.get("berths", 0)) + 1
        text = f"Made fast at {place.name}; the crew walks across."
    else:
        game.credits -= way.cr
        text = {"boat": f"The boat runs the crew across to {place.name}.",
                "shuttle": f"{place.name}'s shuttle takes the crew in"
                           + (f" — {way.cr:,} cr." if way.cr else "."),
                "suits": f"Across to {place.name} on a line, in suits."
                }[way.id]
    game.ashore = place.id
    game.advance_days(way.minutes / 1440.0)
    game.add_log(text, "")
    return {"ok": True, "text": text, "way": way.id, "cr": way.cr,
            "minutes": way.minutes}


def dock_at(game, berth) -> dict:
    """Come alongside a berth on the chart (an `Anchorage`): the place
    behind it, by the harbour's pilot."""
    from . import places
    place = places.by_id(game, place_for(berth.id))
    if place is None:
        return {"ok": False, "why": "Nobody there to bring you in."}
    return cross(game, place, "dock")


def craft_name(game, craft) -> str:
    from . import craft as craft_sim
    return craft_sim.kind_of(craft).name


def wreck_ways(game) -> list:
    """Across to a dead hull: the boat, or suits — the hull stands off her
    within a line's length to board. No shuttle runs to a wreck."""
    ok, why = _suited(game)
    return [Way("boat", "The ship's boat", has_boat(game),
                "" if has_boat(game) else
                f"A hull of a crew under {BOAT_CREW} carries no boat.", 0,
                MINUTES["boat"]),
            Way("suits", "Suits on a line", ok, why, 0, MINUTES["suits"])]
