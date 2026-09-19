"""The route a freight line runs, what it crosses, and what can happen there.

A line is two ports and the stars between them. Which stars is `reach`'s
question, not this module's: the hop list is the fewest-hops walk
`reach.routes_from` already makes at the hauler's own jump range, read
backwards from the far end — so a route is exactly the passage the chart would
show, and a hauler that could not make the crossing is refused rather than
quoted.

The risk is `piracy.lawlessness` for every system on the list, the Bloom in
each (which adds to the share of trouble that ends with no hull), and
`war.spoils` for any a belligerent may take. **One function prices it and one
function rolls it**, and they read the same four numbers, so the probability
the panel prints is the probability the trip is decided on.
"""

from __future__ import annotations

from ..data.freightlines import (BLOOM_LOST, DELAY_BASE, DELAY_DAYS,
                                 DELAY_SLOPE, FUEL_PER_LY, INCIDENT_BASE,
                                 INCIDENT_SLOPE, LAW_FLOOR, LOST_SHARE,
                                 PORT_DAYS, ROBBED_DAMAGE, SEIZE_AT_WAR)
from ..world.galaxy import distance, transit_days
from . import diplomacy as dip
from . import masters as masters_sim
from . import piracy
from . import reach
from . import war as war_sim
from .passage import joined
from .ship import stats as ship_stats


def hauler_stats(game, ship):
    """A hauler's own numbers — its drive, its hold — with the chronicle's
    research in them, and no officers: nobody from your bridge is aboard."""
    return ship_stats(ship, getattr(game, "bonuses", None))


def path(game, start_id: int, end_id: int, jump: float) -> list | None:
    """The systems a hauler crosses from one port to the other, both ends
    included, or None if her drive cannot make the passage at all."""
    if start_id == end_id:
        return [game.galaxy.systems[start_id]]
    found = reach.routes_from(game, jump, start_id)
    if end_id not in found:
        return None
    systems = game.galaxy.systems
    walk = [systems[end_id]]
    while walk[-1].id != start_id:
        here = walk[-1]
        step = found[here.id]["hops"] - 1
        back = [s for s in systems
                if s.id in found and found[s.id]["hops"] == step
                and (distance(s, here) <= jump or joined(s, here)
                     or joined(here, s))]
        walk.append(min(back, key=lambda s: (distance(s, here), s.id)))
    return list(reversed(walk))


def leg(route: list, speed: float) -> dict:
    """What one way along a route costs: days (port time included), reaction
    mass and distance — the same arithmetic as a jump the flagship makes."""
    days, fuel, ly = PORT_DAYS, 0, 0.0
    for a, b in zip(route, route[1:]):
        hop = distance(a, b)
        ly += hop
        days += transit_days(hop, speed)
        fuel += max(1, round(hop * FUEL_PER_LY))
    return {"days": days, "fuel": fuel, "ly": ly, "hops": len(route) - 1}


def contested(game) -> set:
    """Systems a belligerent may take — the war zone a line can be stopped in."""
    out = set()
    for power in dip.POWERS:
        out.update(s.id for s in war_sim.spoils(game, power))
    return out


def exposure(game, route: list) -> list:
    """Each system on the route, and what makes it dangerous."""
    fighting = contested(game)
    return [{"system": s, "lawless": piracy.lawlessness(game, s),
             "bloom": float(getattr(s, "bloom", 0.0) or 0.0),
             "war": s.id in fighting} for s in route]


def risk(game, route: list, master) -> dict:
    """The chance of each way a laden run can go wrong, and of a delay.

    Every system on the list is a separate exposure and the first thing that
    happens is what happens, so the chance of getting through clean is the
    product of each system's clean chance; the trouble is then shared among
    robbery, loss and seizure by how much each system contributed. The
    master's judgement scales all of it.
    """
    keep = masters_sim.judgement(master)
    clean, w_lost, w_rob, w_seize, loose = 1.0, 0.0, 0.0, 0.0, 0.0
    seen = exposure(game, route)
    for row in seen:
        incident = (INCIDENT_BASE + INCIDENT_SLOPE
                    * max(0.0, row["lawless"] - LAW_FLOOR)) * keep
        seize = SEIZE_AT_WAR * keep if row["war"] else 0.0
        lost_share = min(0.9, LOST_SHARE + BLOOM_LOST * row["bloom"])
        clean *= max(0.0, 1.0 - min(0.95, incident + seize))
        w_lost += incident * lost_share
        w_rob += incident * (1.0 - lost_share)
        w_seize += seize
        loose += row["lawless"]
    trouble = 1.0 - clean
    weight = w_lost + w_rob + w_seize
    share = (lambda w: trouble * w / weight) if weight > 0 else (lambda w: 0.0)
    mean_loose = loose / max(1, len(seen))
    return {"lost": share(w_lost), "robbed": share(w_rob),
            "seized": share(w_seize), "trouble": trouble,
            "delay": min(0.9, (DELAY_BASE + DELAY_SLOPE * mean_loose) * keep),
            "worst": max((r["lawless"] for r in seen), default=0.0),
            "war": any(r["war"] for r in seen),
            "bloom": max((r["bloom"] for r in seen), default=0.0)}


def roll(rng, odds: dict) -> dict:
    """Decide a trip, from its own dice. Always draws the same four numbers,
    so what one trip rolls never depends on what the last one did."""
    fate_u, delay_u, days_u, damage_u = (rng.next(), rng.next(), rng.next(),
                                         rng.next())
    if fate_u < odds["lost"]:
        fate = "lost"
    elif fate_u < odds["lost"] + odds["robbed"]:
        fate = "robbed"
    elif fate_u < odds["lost"] + odds["robbed"] + odds["seized"]:
        fate = "seized"
    else:
        fate = "done"
    lo, hi = DELAY_DAYS
    delay = (lo + int(days_u * (hi - lo + 1))) if delay_u < odds["delay"] else 0
    dlo, dhi = ROBBED_DAMAGE
    return {"fate": fate, "delay": delay,
            "damage": dlo + damage_u * (dhi - dlo)}


def route_for(game, line, ship=None) -> dict | None:
    """Both legs of a line for its hauler: the hop list, days and mass each
    way, and the risk on the laden one. None if the hauler cannot make it."""
    hull = ship if ship is not None else hull_of(game, line)
    if hull is None:
        return None
    st = hauler_stats(game, hull)
    out = path(game, line.origin, line.dest, st.jump)
    if out is None or len(out) < 2:
        return None
    back = list(reversed(out))
    master = master_of(game, line)
    return {"route": out, "out": leg(out, st.speed), "back": leg(back, st.speed),
            "risk": risk(game, out, master), "stats": st, "master": master}


def hull_of(game, line):
    """The hauler working a line, if she is still in the fleet."""
    return next((s for s in game.fleet if s.uid == line.hauler), None)


def master_of(game, line):
    """The master sailing a line, if they are still with the house."""
    house = getattr(game, "house", None)
    if house is None:
        return None
    return next((m for m in house.masters if m.id == line.master), None)
