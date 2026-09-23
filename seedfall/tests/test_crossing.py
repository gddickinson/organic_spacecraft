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
            # The boat is the craft on the cradle (`sim/craft.py`): take it
            # away and there is nothing to send.
            kept, game.craft = list(game.craft), []
            boatless = {w.id: w for w in crossing.ways(game, station)}
            game.craft = kept
        finally:
            crossing.range_km = real
        assert near["suits"].ok, near["suits"].why
        assert not boatless["boat"].ok and "cradle" in boatless["boat"].why
        return (f"boat free, shuttle {fare:,} cr, suits only inside "
                f"{crossing.EVA_KM:g} km; an empty cradle has no boat")

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

    @check("the boat is aboard: the craft on the cradle, and a deck to walk to her on")
    def _():
        from ..sim import craft as craft_sim
        game = new_game("crossing-bay")
        laid = afoot_plans.plan(game, afoot_sites.own_hull(game))
        cradle = [r.name for r in laid.rooms if "Cradle deck" in r.name]
        assert cradle and crossing.has_boat(game), [r.name for r in laid.rooms]
        # The boat is the craft: take her off and there is none.
        kept, game.craft = list(game.craft), []
        carried = crossing.has_boat(game)
        game.craft = kept
        assert not carried, "an empty cradle is still a boat"
        got = craft_sim.aboard(game)[0]
        return (f"{cradle[0]} aboard the {game.ship.name}, with "
                f"{got.name} on it; an empty cradle is no boat")

    @check("the boat seats what she seats, and a bigger party takes another way")
    def _():
        from ..sim import craft as craft_sim
        game = _at_hub_with_station()
        station = _neighbour(game)
        # The boat is the roomiest craft on the cradle (`the_boat`), which
        # on the starting hull is her lander.
        craft = crossing.the_boat(game)
        kind = craft_sim.kind_of(craft)
        seats = crossing.seats_of(craft)
        assert seats == max(1, kind.seats - 1), (seats, kind.seats)
        assert crossing.has_boat(game, seats)
        assert not crossing.has_boat(game, seats + 1)
        crowded = {w.id: w for w in crossing.ways(game, station, seats + 1)}
        assert not crowded["boat"].ok, f"a {kind.name} took one too many"
        assert kind.name in crowded["boat"].why, crowded["boat"].why
        assert str(seats + 1) in crowded["boat"].why, crowded["boat"].why
        # And a fighter alone is one at a pinch, which is the other end of
        # the same rule.
        game.craft = [c for c in game.craft if c is not craft]
        fighter = crossing.the_boat(game)
        assert crossing.seats_of(fighter) == 1, fighter
        assert not crossing.has_boat(game, 2)
        return (f"a {kind.name} takes {seats} across besides the pilot and "
                f"refuses {seats + 1}: “{crowded['boat'].why[:48]}…”; a "
                "fighter takes one at a pinch")

    @check("what a walk finds comes home by the way it went, and the rest stays")
    def _():
        from ..sim import afoot_ends, craft as craft_sim
        def haul(way: str, tonnes: float = 12.0):
            game = new_game("crossing-haul")
            site = next(s for s in afoot.sites(game) if s.kind == "ship")
            assert afoot.begin(game, site.key, ["captain"])["ok"]
            walk = game.afoot
            walk.way = way
            walk.found["cargo"] = {"ore": tonnes}
            had = float(game.ship.cargo.get("ore", 0))
            out = afoot_ends.close(game, walk, "left")
            return (float(game.ship.cargo.get("ore", 0)) - had, out["said"],
                    game)
        by_hand, said, game = haul("suits")
        assert by_hand <= crossing.SUIT_T + 1e-6, by_hand
        assert any("left where it lay" in line for line in said), said
        by_boat, _said, game = haul("boat")
        room = crossing.lift_t(game, "boat")
        assert abs(by_boat - room) < 0.01, (by_boat, room)
        assert room <= crossing.LIFT_MOST, (room, crossing.LIFT_MOST)
        alongside, said_all, _g = haul("dock")
        assert alongside == 12.0, alongside
        assert not any("left where it lay" in line for line in said_all)
        return (f"12 t found: {alongside:g} t home made fast, {by_boat:g} t "
                f"by the boat ({crossing.BOAT_TRIPS} trips of her hold, "
                f"{crossing.LIFT_MOST:g} t at the most), {by_hand:g} t on a "
                "line")
