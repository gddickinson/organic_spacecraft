"""A world as a map, and what is on it.

The game had two scales of ground and nothing between them: a body was a
line on a survey — kind, biome, gravity, a resource table — and a landing
zone was a 7×7 grid a party walked one tile at a time. There was no answer
to "what is this world like", and nowhere to put a city.

`sim/worldmap.py` is the scale between, and `sim/worldsites.py` is who is on
it. The claims:

- **It is derived, not stored**: the same sector and the same body give the
  same map every time, in a fresh process, with nothing written to a save.
- **The profile decides the water.** A world the Traveller profile calls
  seven tenths water has seven tenths of its cells under water, so the
  survey screen and the map cannot disagree.
- **Cold is only ice where there is something to freeze** — a barren
  asteroid at 114 K is regolith that happens to be cold, not an ice shelf.
- **The terrain vocabulary is the one the game already has**, so the ground
  the map shows is the ground a landing party walks.
- **What the game already knows goes on the map**: a colony, an NPC
  settlement and a ground base are placed rather than invented again.
- **Population decides the rest**, and some of it has failed — a world with
  a ruin and a worked-out mine on it has a history you can read.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data.developments import DEVELOPMENTS_BY_ID, LADDER
from ..data.expedition import TERRAIN
from ..sim import profile as profile_sim
from ..sim import worldmap, worldsites
from ..world.planets import BODY_KINDS
from .harness import Suite


def _worlds(game) -> list:
    return [b for b in game.system.bodies if BODY_KINDS[b.kind][2]]


def _some(seeds: int = 8) -> list:
    """A handful of chronicles with something to stand on."""
    out = []
    for n in range(seeds):
        game = new_game(f"worldmap-{n}")
        for body in _worlds(game):
            out.append((game, body))
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("the same sector gives the same world, every time it is asked")
    def _():
        game = new_game("derived")
        body = _worlds(game)[0]
        once = worldmap.of(game, body)
        # A fresh chronicle on the same seed, with the cache cleared, so
        # this is the derivation and not the memo.
        worldmap._MADE.clear()
        worldmap._GRIDS.clear()
        again = worldmap.of(new_game("derived"), _worlds(new_game("derived"))[0])
        assert [c.terrain for c in once.cells] == [c.terrain for c in
                                                   again.cells]
        assert [c.height for c in once.cells] == [c.height for c in
                                                  again.cells]
        # And a different sector is a different world.
        other = worldmap.of(new_game("derived-2"),
                            _worlds(new_game("derived-2"))[0])
        assert [c.terrain for c in other.cells] != [c.terrain for c in
                                                    once.cells]
        assert len(once.cells) == worldmap.WIDE * worldmap.HIGH
        return (f"{worldmap.WIDE}×{worldmap.HIGH} cells, identical across "
                "two derivations and different across two sectors")

    @check("the profile decides the water, and the map agrees with it")
    def _():
        rows = []
        for game, body in _some(6):
            got = profile_sim.profile(game, game.system, body)
            world = worldmap.of(game, body)
            want = min(10, int(got.hydrographics or 0)) / 10.0
            assert abs(world.water - want) <= 0.08, (
                f"{body.name}: the profile says {want:.0%} water and the "
                f"map is {world.water:.0%}")
            rows.append((body.name, want, world.water))
        assert len(rows) >= 6, f"only {len(rows)} worlds in six sectors"
        wet = max(rows, key=lambda r: r[2])
        dry = min(rows, key=lambda r: r[2])
        return (f"{len(rows)} worlds within 8 points of their own profile; "
                f"{wet[0]} at {wet[2]:.0%}, {dry[0]} at {dry[2]:.0%}")

    @check("cold is only ice where there is something to freeze")
    def _():
        icy = dry = None
        for game, body in _some(10):
            world = worldmap.of(game, body)
            if body.temp_k >= worldmap.FREEZING:
                continue
            frozen = world.count("shelf") + world.count("crevasse")
            if world.hydro > 0 and icy is None:
                icy = (body, frozen / len(world.cells))
            if world.hydro == 0 and dry is None:
                dry = (body, frozen / len(world.cells))
        assert icy is not None and dry is not None, (icy, dry)
        assert icy[1] > 0.5, f"{icy[0].name} is cold and wet and not iced"
        assert dry[1] == 0.0, (
            f"{dry[0].name} has no water and {dry[1]:.0%} ice")
        return (f"{icy[0].name} at {icy[0].temp_k} K with water: "
                f"{icy[1]:.0%} ice · {dry[0].name} at {dry[0].temp_k} K "
                f"without: {dry[1]:.0%}")

    @check("every cell is ground a landing party already knows how to walk")
    def _():
        seen = set()
        for game, body in _some(8):
            for cell in worldmap.of(game, body).cells:
                assert cell.terrain in TERRAIN, cell.terrain
                seen.add(cell.terrain)
                assert 0.0 <= cell.height <= 1.0 and 0.0 <= cell.wet <= 1.0
                assert -90.0 <= cell.lat <= 90.0
                assert -180.0 <= cell.lon <= 180.0
        assert len(seen) >= 6, f"only {sorted(seen)} in eight sectors"
        return (f"{len(seen)} of the {len(TERRAIN)} terrains turned up: "
                + ", ".join(sorted(seen)))

    @check("what the game already knows is on the map, and the profile fills the rest")
    def _():
        anchored = []
        ladder = set()
        dead = 0
        for game, body in _some(10):
            here = worldsites.of(game, body)
            people = int(profile_sim.profile(game, game.system,
                                             body).population or 0)
            for site in here:
                assert site.kind in DEVELOPMENTS_BY_ID, site.kind
                cell = worldmap.of(game, body).at(site.x, site.y)
                assert not cell.water, f"{site.name} is in the sea"
                if site.anchor:
                    anchored.append(site)
                if site.kind in LADDER:
                    ladder.add(site.kind)
                dead += 1 if site.empty else 0
            if people == 0:
                # Nothing this map *invented* lives on a world the profile
                # says nobody lives on. Something the sector actually put
                # there — a garrison, a mining base, a colony — is a real
                # thing with real people in it and belongs on the map
                # whatever the digit says.
                assert not [s for s in here if s.heads > 0 and not s.anchor], (
                    f"{body.name} has nobody and a town on it")
        assert ladder, "no world in ten sectors had anybody living on it"
        assert dead, "nothing has ever failed anywhere"
        return (f"{len(ladder)} rungs of the ladder in play "
                f"({', '.join(sorted(ladder))}), {dead} abandoned, "
                f"{len(anchored)} anchored to something the game already "
                "held")

    @check("a place stands where it would actually stand")
    def _():
        checked = 0
        for game, body in _some(10):
            world = worldmap.of(game, body)
            for site in worldsites.of(game, body):
                want = site.what
                cell = world.at(site.x, site.y)
                assert cell.terrain not in want.avoids, (
                    f"{want.name} on {cell.terrain}")
                checked += 1
        assert checked >= 10, checked
        return (f"{checked} places, none of them on ground their own kind "
                "refuses")
