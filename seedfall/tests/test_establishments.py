"""The establishments: yards, hotels, palaces, surgeries, springs, wheels,
markets and bases — real places, found, open, flown to and walked.

- they are **drawn from the seed alone**: the same system has the same yard
  every time, and reading them spends no luck;
- each opens **its own signature doors, and they open nowhere else**, and
  of everybody else's only the kinds of business it is;
- **a yard lays down hulls** where the port has no slips, and refits a hull
  alongside it;
- **a station is a berth on the chart**, with its own look in the sky, and
  hails with a way aboard; a base stands on the ground and is not a berth;
- **every kind is laid out whole**, in the shape its table gives it, and so
  is every new kind of wreck — a quarantined hospital ship, a gutted yard,
  a ring that went quiet;
- **a stake is a tenth of a house**, bought alongside, paid out of its
  takings each month on the one clock, reported each quarter by despatch,
  and sold back at a loss;
- **some of the trade runs to the houses**, not the quay.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..data import establishments as est_table
from ..data.establishments import ESTABLISHMENT_BY_ID, ESTABLISHMENTS, MESH
from ..data.venues import VENUES
from ..sim import (afoot, afoot_plans, afoot_sites, anchorage, comms,
                   establishments, hail, places, shipyard, shore, track,
                   traffic)
from . import afoot_kit
from .harness import Suite

SECTORS = ("est-a", "est-b", "est-c", "est-d", "est-e", "est-f")


def _everywhere():
    """(game, system, place) for every establishment over the test sectors."""
    for seed in SECTORS:
        game = new_game(seed)
        for system in game.galaxy.systems:
            for place in places.in_system(game, system):
                if place.kind in ("station", "base"):
                    yield game, system, place


def run(suite: Suite) -> None:
    check = suite.check

    @check("establishments are drawn from the seed alone, and every kind is found")
    def _():
        kinds, count = Counter(), 0
        for seed in SECTORS:
            game = new_game(seed)
            was = game.rng_seed
            for system in game.galaxy.systems:
                first = [(f.kind.id, f.name, f.body_id)
                         for f in establishments.here(game, system)]
                again = [(f.kind.id, f.name, f.body_id)
                         for f in establishments.here(game, system)]
                assert first == again, system.name
                for kid, _name, body in first:
                    kinds[kid] += 1
                    count += 1
                    kind = ESTABLISHMENT_BY_ID[kid]
                    assert not kind.needs_port or system.port is not None
                    at = next(b for b in system.bodies if b.id == body)
                    assert at.kind in kind.at, (kid, at.kind)
            assert game.rng_seed == was, "reading establishments cost luck"
        missing = [e.id for e in ESTABLISHMENTS if not kinds[e.id]]
        assert not missing, f"never found in {len(SECTORS)} sectors: {missing}"
        return (f"{count} establishments over {len(SECTORS)} sectors, all "
                f"{len(ESTABLISHMENTS)} kinds found")

    @check("each opens its own signature doors, and they open nowhere else")
    def _():
        mine = {e.id: {v.id for v in VENUES if e.id in v.at}
                for e in ESTABLISHMENTS}
        assert all(mine.values()), [k for k, v in mine.items() if not v]
        seen = 0
        for game, _system, place in _everywhere():
            doors = shore.open_here(game, place)
            got = {v.id for v in doors if v.at}
            assert got == mine[place.look], (place.name, got ^ mine[place.look])
            kind = ESTABLISHMENT_BY_ID[place.look]
            stray = [v.id for v in doors if not v.at and v.kind not in
                     kind.kinds]
            assert not stray, (place.name, stray)
            seen += 1
        game = new_game(SECTORS[0])
        for system in game.galaxy.systems:
            for place in places.in_system(game, system):
                if place.kind in ("station", "base"):
                    continue
                strays = [v.id for v in shore.open_here(game, place) if v.at]
                assert not strays, (place.name, strays)
        return f"{seen} establishments, every signature door at home and only there"

    @check("a yard lays down hulls where the port has no slips, and refits alongside")
    def _():
        welded = CHASSIS_BY_ID["pike"]
        for game, system, place in _everywhere():
            if place.look != "shipyard":
                continue
            services = system.port.services if system.port else ()
            game.colonies.clear()
            ok, why = shipyard.can_build_here(game, system, welded)
            assert ok, why
            if "shipyard" in services:
                continue
            game.location_id = system.id
            game.orbit_body = place.body_id
            game.recompute()
            here, why = shipyard.can_refit_here(game)
            assert here, why
            return (f"{place.name}: a {welded.name} can be laid down, and a "
                    "hull alongside refitted, with no yard at the port")
        raise AssertionError("no yard found away from a port's own slips")

    @check("a station is a berth on the chart, a base keeps a pad over it, and each hails with a way in")
    def _():
        seen, said = {"station": 0, "field": 0}, {}
        for game, system, place in _everywhere():
            berths = {a.id: a for a in anchorage.in_system(game, system)}
            berth = berths[place.id]
            if place.kind == "base":
                assert berth.kind == "field" and berth.look == "field", berth
            else:
                assert berth.kind == "station" and \
                    berth.look == MESH[place.look], berth
            seen[berth.kind] += 1
            if berth.kind in said:
                continue
            game.location_id = system.id
            game.orbit_body = place.body_id
            game.recompute()
            contact = next(c for c in track.contacts(game)
                           if c.kind == "anchorage" and c.name == berth.name)
            board = next((o for o in hail.options(game, contact)
                          if o.id == "board"), None)
            assert board is not None and board.ok, board
            said[berth.kind] = board.label
        assert all(seen.values()), seen
        assert said == {"station": "Go aboard", "field": "Go down"}, said
        return (f"{seen['station']} stations on the chart, and "
                f"{seen['field']} bases' pads over their worlds")

    @check("breakers wake a derelict REVENANT, never an ANTIPHON; a nursery refits what it grows")
    def _():
        revenant, antiphon = CHASSIS_BY_ID["revenant"], CHASSIS_BY_ID["antiphon"]
        found = None
        for game, system, place in _everywhere():
            if place.look == "breakers_yard":
                found = (game, system, place)
                break
        assert found, "no breakers' yard in the test sectors"
        game, system, place = found
        game.colonies.clear()
        ok, why = shipyard.can_build_here(game, system, revenant)
        assert ok, why
        ok, why = shipyard.can_build_here(game, system, antiphon)
        assert not ok and "array" in why, why
        game.location_id = system.id
        game.orbit_body = place.body_id
        game.recompute()
        berth = next(a for a in anchorage.in_system(game)
                     if a.id == place.id)
        assert berth.offers("xenoyard") and shipyard.can_refit_here(game)[0]
        nursery = next(((g, s, p) for g, s, p in _everywhere()
                        if p.look == "hull_nursery"
                        and not (s.port and "shipyard" in s.port.services)),
                       None)
        assert nursery, "no nursery away from a port's slips"
        g, s, p = nursery
        g.colonies.clear()
        g.location_id, g.orbit_body = s.id, p.body_id
        g.recompute()
        grown = g.ship.chassis
        assert shipyard.can_refit_here(g)[0], (grown, "a nursery refused")
        return (f"{place.name} wakes a REVENANT; an ANTIPHON wants an array; "
                f"{p.name} refits a {grown.upper()}")

    @check("every kind of establishment is laid out whole, in its own shape, and can be walked")
    def _():
        done, bad = {}, []
        for game, system, place in _everywhere():
            if place.look in done:
                continue
            game.location_id = system.id
            game.orbit_body = place.body_id
            game.recompute()
            site = afoot_sites._from_place(game, place)
            painted = afoot_plans._paint(game, site, RNG("probe"))
            lost = [w.name for p in painted for w in p.sheet.lost()]
            if lost:
                bad.append(f"{place.look}: dropped {lost[:3]}")
            got = afoot.begin(game, site.key, ["captain"])
            if not got["ok"]:
                bad.append(f"{place.look}: {got}")
                continue
            walk = game.afoot
            if any(t.kind == "lift" and t.link < 0 for t in walk.things):
                bad.append(f"{place.look}: a lift that goes nowhere")
            game.afoot = None
            done[place.look] = len(walk.decks)
        assert not bad, bad[:6]
        assert set(done) == set(ESTABLISHMENT_BY_ID), set(
            ESTABLISHMENT_BY_ID) - set(done)
        return f"{len(done)} kinds walked, none short of a room"

    @check("a quarantined hospital ship, a gutted yard and a ring gone quiet can each be boarded")
    def _():
        out = []
        for kind in ("plague_ship", "gutted_yard", "dead_habitat"):
            game, site = afoot_kit.at_wreck((kind,))
            got = afoot.begin(game, site.key, ["captain"])
            assert got["ok"], (kind, got)
            walk = game.afoot
            kinds = {r.kind for r in walk.rooms}
            if kind == "plague_ship":
                assert "isolation" in kinds, kinds
                assert any(t.kind == "spores" for t in walk.things)
            if kind == "gutted_yard":
                assert "slipway" in kinds and not walk.decks[0].air, kinds
            if kind == "dead_habitat":
                assert [d.name for d in walk.decks] == ["The hub", "The ring"]
            out.append(f"{kind}: {len(walk.rooms)} rooms")
        return "; ".join(out)

    @check("a stake is bought alongside, pays monthly on the clock, reports quarterly, sells at a loss")
    def _():
        game, site = afoot_kit.at_establishment(("grand_hotel",))
        place = places.by_id(game, site.place_id)
        from ..sim import crossing
        refused = establishments.stake_terms(game, place)
        assert not refused["ok"] and "aboard" in refused["why"], refused
        assert crossing.cross(game, place, "shuttle")["ok"]
        game.credits = 5_000_000
        terms = establishments.stake_terms(game, place)
        assert terms["ok"] and terms["price"] == int(
            est_table.WORTH[place.look] * est_table.STAKE_SHARE), terms
        got = establishments.buy_stake(game, place)
        assert got["ok"] and game.credits == 5_000_000 - terms["price"]
        assert not establishments.buy_stake(game, place)["ok"], "bought twice"
        cash = game.credits
        game.day += est_table.STAKE_DAYS - 1
        establishments.tick(game, 1)
        assert game.credits == cash, "paid for a month not yet traded"
        game.day += 1
        establishments.tick(game, 1)
        assert game.credits == cash + terms["monthly"], (game.credits, cash)
        held = game.stakes[place.id]
        paid = held["paid"]
        game.advance_days(est_table.STATEMENT_DAYS)
        assert held["paid"] > paid, "the clock never paid the stake"
        told = [m for m in comms.inbox(game, "news")
                if m.subject == f"{place.name}: the quarter"]
        assert told, "no quarter's statement"
        game.orbit_body = None                  # standing off
        place = places.by_id(game, site.place_id)
        refused = establishments.sell_stake(game, place)
        assert not refused["ok"] and "alongside" in refused["why"], refused
        game.orbit_body, game.ashore = place.body_id, place.id
        place = places.by_id(game, site.place_id)
        cash = game.credits
        sold = establishments.sell_stake(game, place)
        assert sold["ok"] and game.credits == cash + int(
            terms["price"] * est_table.SELL_BACK), sold
        assert place.id not in game.stakes
        return (f"{terms['price']:,} cr for a tenth of {place.name}, "
                f"{terms['monthly']:,} cr a month, {sold['back']:,} cr back")

    @check("some of the trade runs to the houses, not the quay")
    def _():
        bound = []
        for seed in SECTORS[:3]:
            game = new_game(seed)
            for system in game.galaxy.systems:
                houses = {f.name: f.body_id for f in
                          establishments.here(game, system)}
                for hull in traffic.in_system(game, system):
                    if hull.bound:
                        assert hull.bound in houses, hull.bound
                        assert (system.bodies[hull.to_body].id
                                == houses[hull.bound]), hull
                        bound.append(hull.bound)
        assert bound, "no hull ever bound for a house"
        return (f"{len(bound)} hulls bound for {len(set(bound))} houses, "
                "each flying to the house's own body")
