"""Bodies that come and go: a comet's passage and a rogue's flyby.

**The delicate part.** A body is referenced from all over the chronicle — by
id (`Game.orbit_body`, a contract's target, a holding, a landing party) and
by index into its system's list (a trench, an in-system crossing, the conn's
target and sky, a knock). So a transient body is kept to three rules:

1. **It is always last.** Appended at the end of the list, and a system holds
   at most one (`data/phenomena.TRANSIENT_SLOT`) — so when it leaves, not one
   other body's index moves.
2. **Nothing permanent may be put on it.** A holding (`colony.can_found`),
   the powers' settlers (`settlement.sites_for`), a landing party and a
   ground contract (`landing.kind_allows`) all refuse a body that is passing
   through; a quay's or a Weave anchor's body is never one (`anchorage`).
3. **Whatever was left on it is cleaned up when it goes**, here, in `leave`:
   a hull holding at it stands off with a log line, a trench on it is
   backfilled, a party on it is recalled, a survey posting that counted it
   is cut to what is left, a landed conn's view, the knock and the lee are
   dropped. Two things cannot be settled from inside the clock — a conn
   being flown (billing it advances the clock) and a crossing under way to
   the body (it holds the index) — so the body waits for them to end
   (`can_leave`), and `flight.travel_to` will not start a flight that would
   arrive after it has gone.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..data import phenomena as data
from ..data.shocks import COMET_GLUT
from ..world.planets import Body


def body_id(event) -> str:
    """A transient's id: never a number, so never a resident's."""
    return f"{event.kind}-{event.system_id}-{event.start}"


def make(game, event, system) -> Body:
    """The body an event brings, derived from the event's own key."""
    rng = RNG(f"{game.seed}:sky:{event.id}:body")
    if event.kind == "comet":
        return _comet(rng, event, system)
    return _rogue(rng, event, system)


def _grade(rng, low_high) -> float:
    lo, hi = low_high
    return lo + (hi - lo) * rng.next()


def _comet(rng, event, system) -> Body:
    lo, hi = data.COMET_KM
    radius = lo + int(rng.next() * (hi - lo + 1))
    orbit = _grade(rng, data.COMET_ORBIT)
    return Body(
        id=body_id(event), name=f"C/{event.start // 365 + 1} {system.name}",
        kind="comet", biome="cryo", orbit=orbit, radius_km=radius,
        gravity=0.001 + 0.03 * rng.next(),
        temp_k=round(60 + system.heat * 300 * (1 - orbit)),
        resources={cid: round(_grade(rng, span), 3)
                   for cid, span in data.COMET_GRADES.items()},
        transient_until=event.end)


def _rogue(rng, event, system) -> Body:
    from ..data.xenotech import XENOTECH
    lo, hi = data.ROGUE_KM
    radius = lo + int(rng.next() * (hi - lo + 1))
    kind = "ice" if rng.next() < 0.5 else "rocky"
    relic = None
    if rng.next() < data.ROGUE_RELIC and XENOTECH:
        relic = XENOTECH[int(rng.next() * len(XENOTECH)) % len(XENOTECH)].id
    return Body(
        id=body_id(event), name=f"Rogue {event.pick * 9000 + 1000:.0f}",
        kind=kind, biome="barren", orbit=_grade(rng, data.ROGUE_ORBIT),
        radius_km=radius, gravity=0.05 + 0.6 * rng.next(), temp_k=40,
        resources={"ore": round(_grade(rng, (0.3, 0.8)), 3),
                   "volatiles": round(_grade(rng, (0.1, 0.6)), 3),
                   "phosphate": round(_grade(rng, (0.0, 0.3)), 3),
                   "biomass": 0.0},
        relic=relic, sunless=True, transient_until=event.end)


def arrive(game, sky, event) -> Body | None:
    """Put the body in its system. Its glut is `gluts`', derived, not here."""
    system = game.galaxy.systems[event.system_id]
    from .phenomena import transient_bodies
    if transient_bodies(system):
        return None                       # one at a time, always last
    body = make(game, event, system)
    system.bodies.append(body)
    sky.transients[event.id] = [system.id, body.id]
    return body


_GLUTS: dict = {}


def glut_on(game, system_id: int, cid: str) -> list:
    """The comet gluts on one good at one quay today — `market.factor`'s
    question, answered without building the sky for goods it never moves."""
    if cid not in COMET_GLUT.goods:
        return []
    return gluts(game).get(system_id, [])


def gluts(game) -> dict:
    """System id → today's comet gluts on its quay, as `market.Shock`s.

    A comet's volatiles, hauled in by everybody with a tank: a glut at the
    nearest `COMET_GLUT_PORTS` quays within `COMET_GLUT_LY` for as long as it
    is passing. **Derived from the sky, never stored in `Game.shocks`**, and
    read only through `market.factor` (the price) and `market.note_prices`
    (the register marks it): a stored one took a slot the market's own onset
    roll counts, which moved that roll's draws and so the whole chronicle's
    luck — measured, two idle years moved a Concordat purse 45,500 → 20,900
    on one seed, and every long fixture in the suite with it.
    """
    from . import phenomena as sky_sim
    key = (game.seed, game.day, len(game.galaxy.systems),
           sky_sim._signature(game))
    got = _GLUTS.get(key)
    if got is None:
        got = {}
        from ..world.galaxy import distance
        from .market import Shock
        quays = [s for s in game.galaxy.systems if s.market and s.port
                 and "volatiles" in s.market.stock]
        for events in sky_sim.live(game).values():
            for event in events:
                if event.kind != "comet":
                    continue
                at = game.galaxy.systems[event.system_id]
                near = sorted((distance(q, at), q.id) for q in quays
                              if distance(q, at) <= data.COMET_GLUT_LY)
                for _ly, sid in near[:data.COMET_GLUT_PORTS]:
                    got.setdefault(sid, []).append(Shock(
                        id=-1, kind="comet", system_id=sid,
                        commodity="volatiles", until=event.end))
        if len(_GLUTS) > 64:
            _GLUTS.clear()
        _GLUTS[key] = got
    return got


def find(game, event_id: str):
    """(system, index, body) for a transient still in the sky, or None."""
    sky = getattr(game, "sky", None)
    where = (sky.transients.get(event_id) if sky is not None else None)
    if not where:
        return None
    system = game.galaxy.systems[where[0]]
    for index, body in enumerate(system.bodies):
        if body.id == where[1]:
            return system, index, body
    return None


def can_leave(game, system, index: int) -> bool:
    """False while a flight in its system is still in hand: a conn being
    flown (settling one bills its time, which cannot be done from inside the
    day), or a crossing under way to the body itself (it holds the index,
    and arrives within its watches — `flight.travel_to` refuses to start one
    that would arrive after the body has gone)."""
    if game.location_id != system.id:
        return True
    conn = getattr(game, "conn", None)
    if conn is not None and not conn.landed:
        return False
    transit = getattr(game, "transit", None)
    return not (transit is not None and not transit.over
                and transit.body_index == index)


def leave(game, sky, event_id: str) -> bool:
    """Take a passing body out of the sky, and everything left on it.

    Returns False only when it has to wait a day (`can_leave`)."""
    found = find(game, event_id)
    if found is None:
        sky.transients.pop(event_id, None)
        return True
    system, index, body = found
    if not can_leave(game, system, index):
        return False
    here = game.location_id == system.id
    _clear(game, sky, system, index, body, here)
    del system.bodies[index]
    sky.transients.pop(event_id, None)
    if here or system.visited:
        game.add_log(f"{body.name} has passed out of {system.name}.", "")
    return True


def _clear(game, sky, system, index: int, body, here: bool) -> None:
    """Everything that pointed at the body, pointed elsewhere."""
    if here and getattr(game, "conn", None) is not None:
        game.conn = None                    # landed and billed: only a view
    dig = getattr(game, "dig", None)
    if (dig is not None and not dig.over and dig.system_id == system.id
            and dig.body_index == index):
        from . import dig as dig_sim
        dig_sim.stop(game, dig)
    party = getattr(game, "expedition", None)
    if (party is not None and not party.over
            and party.system_id == system.id and party.body_id == body.id):
        from . import expedition as exp_sim
        exp_sim.finish(party, "aborted")
    if here and game.orbit_body == body.id:
        from . import flight
        flight.stand_off(game)
        game.add_log(f"{body.name} is leaving the system; the helm stands "
                     "off rather than go with it.", "warn")
    if sky.lee == body.id:
        sky.lee = None
    if here:
        getattr(game, "knocks", {}).pop(f"body:{index}", None)
    from .phenomena import transient_bodies
    fixed = len(system.bodies) - len(transient_bodies(system))
    for contract in getattr(game, "contracts", ()) or ():
        if (not contract.done and not contract.failed
                and contract.kind == "survey"
                and contract.target_system == system.id
                and contract.amount > fixed):
            contract.amount = max(1, fixed)     # it cannot ask for a ghost
