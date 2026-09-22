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
  a ring that went quiet.
"""

from __future__ import annotations

from collections import Counter

from ..core.rng import RNG
from ..core.state import new_game
from ..data.chassis import CHASSIS_BY_ID
from ..data.establishments import ESTABLISHMENT_BY_ID, ESTABLISHMENTS, MESH
from ..data.venues import VENUES
from ..sim import (afoot, afoot_plans, afoot_sites, anchorage, establishments,
                   hail, places, shipyard, shore, track)
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

    @check("a station is a berth on the chart, a base is not, and a station hails with a way aboard")
    def _():
        stations = bases = 0
        for game, system, place in _everywhere():
            berths = {a.id: a for a in anchorage.in_system(game, system)}
            if place.kind == "base":
                assert place.id not in berths, place.name
                bases += 1
                continue
            berth = berths[place.id]
            assert berth.kind == "station" and berth.look == MESH[place.look]
            stations += 1
            if stations == 1:
                game.location_id = system.id
                game.orbit_body = place.body_id
                game.recompute()
                contact = next(c for c in track.contacts(game)
                               if c.kind == "anchorage"
                               and c.name == berth.name)
                options = {o.id for o in hail.options(game, contact)}
                assert "board" in options, options
        assert stations and bases
        return f"{stations} stations on the chart, {bases} bases on the ground"

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
