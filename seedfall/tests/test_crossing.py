"""Getting from the hull into a place: made fast alongside, or across.

- **a chronicle starts made fast at its home quay** — the hull at the berth
  on the flight deck, not hundreds of kilometres off it, and the crew free
  to walk in;
- **moving the hull casts off**: arriving is being in orbit near things,
  alongside none of them, and their doors are shut to a crew still aboard;
- **the harbour's pilot brings her in** when the berth is clear and the
  quay will have you, and says no in the same words a conn would hear;
- **the ship's boat, their shuttle and suits on a line** each cost what they
  say: a boat only on a hull big enough to carry one, a fare a head, a line
  only across a couple of kilometres of open space and only with suits
  aboard for whoever breathes;
- **a walk crosses first**, by the way the start page shows; **a base's
  pad** is a berth like any other, with the way down included;
- **the boat is aboard**: a hull that carries one has a boat bay to walk to.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.chassis import CHASSIS
from ..sim import (afoot, afoot_plans, afoot_sites, anchorage, crossing,
                   flight, places, shore, track)
from . import afoot_kit
from .harness import Suite


def _hub(game):
    return next(p for p in places.here(game) if p.kind == "port")


def _neighbour(game):
    """Somewhere at the home quay's world that is not the quay: a station
    of the trade's, or failing that the first place over the world."""
    return next((p for p in places.here(game)
                 if p.kind == "station"), None)


def _at_hub_with_station(seeds: int = 20):
    for n in range(seeds):
        game = new_game(f"crossing-{n}")
        if _neighbour(game) is not None and any(
                p.kind == "port" for p in places.here(game)):
            return game
    raise AssertionError("no station beside a home quay in twenty sectors")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a chronicle starts made fast at its home quay, and alongside it on the flight deck")
    def _():
        game = new_game("crossing-start")
        hub = _hub(game)
        assert game.berth == hub.id and game.ashore == hub.id, (
            game.berth, game.ashore)
        contact = next(c for c in track.contacts(game)
                       if c.kind == "anchorage" and c.name == hub.name)
        import math
        km = math.dist(flight.ship_position(game), track.at(
            game, contact, game.day)) * anchorage.KM_PER_AU
        assert km < 1.0, f"{km:,.1f} km off the berth she is made fast to"
        assert anchorage.where_am_i(game).startswith("Made fast alongside")
        assert crossing.across(game, hub) and not shore.barred(game, hub)
        return f"made fast at {hub.name}, {km * 1000:.0f} m off its centre"

    @check("moving the hull casts off: in orbit near things is alongside none of them")
    def _():
        game = new_game("crossing-cast-off")
        hub = _hub(game)
        body = flight.current_body(game)
        flight.hold_at(game, body)           # as a transfer's arrival does
        hub = _hub(game)
        assert game.berth == "" and game.ashore == "", "still made fast"
        assert not crossing.across(game, hub)
        said = anchorage.where_am_i(game)
        assert "alongside none of them" in said, said
        got = shore.buy(game, hub, "vacc_suit")
        assert not got["ok"] and "not at" in got["why"], got
        ways = {w.id: w for w in crossing.ways(game, hub)}
        assert ways["dock"].ok, ways["dock"].why
        return f"“{said}” — and the shelf says “{got['why'][:48]}…”"

    @check("the harbour's pilot brings her in — or says no as it would to a conn")
    def _():
        game = new_game("crossing-pilot")
        body = flight.current_body(game)
        flight.hold_at(game, body)
        hub = _hub(game)
        got = crossing.cross(game, hub, "dock")
        assert got["ok"] and game.berth == hub.id and game.ashore == hub.id
        assert got["minutes"] == crossing.MINUTES["dock"], got
        flight.hold_at(game, body)
        faction = game.system.port.faction
        game.rep[faction] = -100.0
        hub = _hub(game)
        cash = game.credits
        way = next(w for w in crossing.ways(game, hub) if w.id == "dock")
        refused = crossing.cross(game, hub, "dock")
        assert not way.ok and not refused["ok"] and game.berth == ""
        assert game.credits == cash and "standing" in way.why, way.why
        return f"brought in in an hour; at standing −100: “{way.why}”"

    @check("the ship's boat, their shuttle and suits on a line each cost what they say")
    def _():
        game = _at_hub_with_station()
        station = _neighbour(game)
        ways = {w.id: w for w in crossing.ways(game, station)}
        assert crossing.has_boat(game) and ways["boat"].ok
        assert not ways["suits"].ok and "open space" in ways["suits"].why
        fare = ways["shuttle"].cr
        assert fare == crossing.FARE * max(1, station.amenity), fare
        cash = game.credits
        got = crossing.cross(game, station, "shuttle")
        assert got["ok"] and game.credits == cash - fare
        assert crossing.across(game, places.by_id(game, station.id))
        assert game.berth == _hub(game).id, "a shuttle moved the hull"
        # A line reaches a couple of kilometres, with suits for breathers.
        game.ashore = ""
        real = crossing.range_km
        crossing.range_km = lambda g, p: 1.2
        try:
            near = {w.id: w for w in crossing.ways(game, station)}
            small = next(c for c in CHASSIS if 0 < int(c.crew or 0)
                         < crossing.BOAT_CREW)
            kept, game.ship.chassis = game.ship.chassis, small.id
            boatless = {w.id: w for w in crossing.ways(game, station)}
            game.ship.chassis = kept
        finally:
            crossing.range_km = real
        assert near["suits"].ok, near["suits"].why
        assert not boatless["boat"].ok and "boat" in boatless["boat"].why
        return (f"boat free, shuttle {fare:,} cr, suits only inside "
                f"{crossing.EVA_KM:g} km; a {small.name} carries no boat")

    @check("a walk crosses first, by the way chosen, and the doors open after")
    def _():
        game = _at_hub_with_station()
        station = _neighbour(game)
        site = next(s for s in afoot.sites(game)
                    if s.key == f"place:{station.id}")
        refused = afoot.begin(game, site.key, ["captain"], across="suits")
        assert not refused["ok"] and game.afoot is None, refused
        cash = game.credits
        got = afoot.begin(game, site.key, ["captain"], across="shuttle")
        assert got["ok"], got
        assert game.ashore == station.id and game.credits < cash
        first = game.afoot.log[0][1]
        assert "shuttle" in first, first
        game.afoot = None
        assert shore.barred(game, places.by_id(game, station.id)) == ""
        return f"“{first}”"

    @check("a base's pad is a berth, and coming alongside takes the crew down")
    def _():
        game, site = afoot_kit.at_establishment(("mining_base",))
        base = places.by_id(game, site.place_id)
        assert not crossing.across(game, base)
        got = crossing.cross(game, base, "dock")
        assert got["ok"], got
        assert game.berth == base.id and crossing.across(
            game, places.by_id(game, base.id))
        pad = crossing.made_fast(game)
        assert pad is not None and pad.kind == "field", pad
        return f"made fast at {pad.name}'s pad, and down its field"

    @check("the boat is aboard: a hull that carries one has a boat bay to walk to")
    def _():
        game = new_game("crossing-bay")
        laid = afoot_plans.plan(game, afoot_sites.own_hull(game))
        bays = [r.name for r in laid.rooms if r.name == "Boat bay"]
        assert bays and crossing.has_boat(game), [r.name for r in laid.rooms]
        small = next(c for c in CHASSIS if 0 < int(c.crew or 0)
                     < crossing.BOAT_CREW)
        kept, game.ship.chassis = game.ship.chassis, small.id
        carried = crossing.has_boat(game)
        game.ship.chassis = kept
        assert not carried, small.id
        return (f"a boat bay aboard the {game.ship.name}; none on a "
                f"{small.name}")
