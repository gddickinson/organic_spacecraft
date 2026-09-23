"""Single-seat craft: the cradle, the ticket, the sortie, and what she is for.

A player asked for fighters — launched off a carrier, flown from their own
cockpit, and good for a look or a lift as well as a fight.

- **she is aboard from the first day**, in a cradle deck with a hatch
  through to her, which the party can walk to (`sim/afoot_program`);
- **somebody has to be certified**: a Pilot ticket, which the captain holds
  and so does the navigator, and nobody else takes her out;
- **a sortie is a flight of her own** — the craft's thrust, tank and array
  in the same `sim/conn` the ship is flown with, and the ship's own conn
  untouched beside it;
- **teeth and eyes**: a firing run at a hull in reach, an hour's looking at
  a body for real survey data, and both refused at a range she cannot make;
- **she is the ship's boat**: a crew crosses in her (`sim/crossing`), and
  cannot while she is out.
"""

from __future__ import annotations

from ..core.rng import RNG
from ..core.state import new_game
from ..data import craft as table
from ..sim import (afoot_plans, afoot_sites, craft as craft_sim, crossing,
                   engage, flight, track)
from .harness import Suite


def _out(seed: str = "craft"):
    """A chronicle with her fighter away and the sortie in hand."""
    game = new_game(seed)
    craft = next(c for c in craft_sim.aboard(game)
                 if craft_sim.kind_of(c).role == "fighter")
    got = craft_sim.launch(game, craft)
    assert got["ok"], got
    return game, craft, game.sortie


def _hull(game):
    return next(c for c in track.contacts(game) if c.kind == "hull")


def run(suite: Suite) -> None:
    check = suite.check

    @check("a hull carries a craft from the first day, in a cradle the crew can walk to")
    def _():
        game = new_game("craft-aboard")
        carried = craft_sim.aboard(game)
        # Two cradles and something in each: the launch she fights with and
        # the lander that puts a party on a world (`sim/descent.py`).
        assert len(carried) == 2, carried
        craft = next(c for c in carried
                     if craft_sim.kind_of(c).role == "fighter")
        pod = next(c for c in carried
                   if craft_sim.kind_of(c).role == "lander")
        kind = craft_sim.kind_of(craft)
        assert craft.state == "cradled" and craft.hp == kind.hull
        assert kind.role == "fighter" and kind.seats == 1, kind
        assert craft_sim.kind_of(pod).lands and pod.state == "cradled"
        laid = afoot_plans.plan(game, afoot_sites.own_hull(game))
        cradles = [r for r in laid.rooms if "Cradle deck" in r.name]
        assert len(cradles) == 2, [r.name for r in laid.rooms]
        cradle = cradles[0]
        assert any(kind.name.title() in r.name for r in cradles), cradles
        # And the way to her is a way, not a wall: the deck she is on is
        # walked like any other (`afootshapes` holds the whole hull).
        from ..sim import afoot
        site = next(s for s in afoot.sites(game) if s.kind == "ship")
        assert afoot.begin(game, site.key, ["captain"])["ok"]
        walk = game.afoot
        assert any("Cradle deck" in r.name for r in walk.rooms)
        game.afoot = None
        return (f"{craft.name}, a {kind.name} on the cradle deck: "
                f"{kind.hull} of hull, {kind.fuel_t:g} t in her tank")

    @check("only a certified pilot takes her out, and the captain and the navigator are")
    def _():
        game = new_game("craft-ticket")
        craft = craft_sim.aboard(game)[0]
        rows = craft_sim.pilots(game, craft)
        able = [name for _k, name, _w, ok, _why in rows if ok]
        assert any(n.startswith("Captain") for n in able), able
        assert len(able) >= 2, f"only {able} may fly her"
        shut = [(name, why) for _k, name, _w, ok, why in rows if not ok]
        assert shut and all("Pilot" in why for _n, why in shut), shut
        key = next(k for k, _n, _w, ok, _why in rows if not ok)
        refused = craft_sim.launch(game, craft, key)
        assert not refused["ok"] and "Pilot" in refused["why"], refused
        assert game.sortie is None and craft.state == "cradled"
        # A heavier fighter asks for a rating above trained.
        heavier = table.CRAFT_BY_ID["shrike"]
        assert heavier.needs > table.CRAFT_BY_ID["wasp"].needs
        return (f"{len(able)} aboard hold the ticket ({', '.join(able)}); "
                f"{shut[0][0]} does not: “{shut[0][1][:44]}…”")

    @check("a sortie is a flight of her own: her numbers, her tank, and the ship's conn untouched")
    def _():
        game, craft, conn = _out("craft-sortie")
        kind = craft_sim.kind_of(craft)
        from ..sim.conn import TICK
        assert game.conn is None, "the sortie took the ship's own conn"
        assert abs(conn.main_dv - kind.thrust_g * 9.80665 * TICK) < 1e-6
        assert conn.rcs_dv == kind.rcs and conn.array == kind.sensor
        assert conn.mass_t == kind.mass_t
        hold = float(game.ship.cargo.get("volatiles", 0))
        day = game.day
        for _n in range(10):
            craft_sim.beat(game, "forward", main=True, ticks=3)
        assert craft.fuel < kind.fuel_t, "her tank never emptied"
        assert float(game.ship.cargo.get("volatiles", 0)) == hold, (
            "a sortie drank the ship's reaction mass")
        assert game.day >= day and conn.elapsed > 0
        far = craft_sim.out_km(game)
        assert far > 1.0, far
        shut, why = craft_sim.can_recover(game)
        assert not shut and "off the cradle" in why, why
        return (f"{far:,.0f} km out on {kind.thrust_g:g} g, "
                f"{craft.fuel:.1f} t left in her, the hold untouched")

    @check("teeth and eyes: a firing run in reach, and an hour's looking")
    def _():
        game, craft, conn = _out("craft-teeth")
        hull = _hull(game)
        # Out of reach, a run is refused in the range's own words.
        far = engage.range_km(game, conn, hull)
        ok, why = craft_sim.can_strike(game, hull)
        if far > engage.REACH_KM:
            assert not ok and "run is made inside" in why, why
        # Fly her up to it: the sortie's frame hangs off the hull she left,
        # so the offset to the contact is where she has to be.
        from ..sim import flight as flight_sim
        from ..sim import track as track_sim
        from ..sim.anchorage import KM_PER_AU
        at = track_sim.at(game, hull, game.day)
        home = flight_sim.base_position(game)
        conn.pos = [(a - b) * KM_PER_AU for a, b in zip(at, home)]
        ok, why = craft_sim.can_strike(game, hull)
        assert ok, why
        before = craft.fuel
        got = craft_sim.strike(game, hull, RNG("run"))
        assert got["ok"] and got["dealt"] > 0, got
        assert craft.fuel < before and craft.struck == 1
        from ..sim import hostiles
        assert hostiles.is_marked(game, getattr(hull, "hull_id", hull.id))
        # And the eyes: an hour over a body is survey data on the bench.
        from ..sim import inquiry
        body = next(c for c in track.contacts(game) if c.kind == "body")
        was = inquiry.store(game.research).get("survey", 0.0)
        look = craft_sim.scout(game, body)
        assert look["ok"] and look["data"] > 0, look
        assert inquiry.store(game.research).get("survey", 0.0) > was
        return (f"{got['dealt']} through her flank at "
                f"{engage.range_km(game, conn, hull):,.0f} km; "
                f"{look['data']:.0f} of survey off one pass")

    @check("she is the ship's boat, and is not while she is out")
    def _():
        game = new_game("craft-boat")
        place = next(p for p in __import__(
            "seedfall.sim.places", fromlist=["x"]).here(game)
            if p.kind == "port")
        flight.hold_at(game, flight.current_body(game))   # cast off
        assert crossing.has_boat(game), "a craft in the cradle is no boat"
        ways = {w.id: w for w in crossing.ways(game, place)}
        assert ways["boat"].ok, ways["boat"].why
        # The boat is whichever craft takes the most across — the lander,
        # on a hull that carries one.
        boat = crossing.the_boat(game)
        assert craft_sim.kind_of(boat).seats == max(
            craft_sim.kind_of(c).seats for c in craft_sim.aboard(game))
        craft_sim.launch(game, boat)
        assert crossing.the_boat(game) is not boat, "out, and still the boat"
        got = craft_sim.recover(game)
        assert got["ok"], got
        assert crossing.the_boat(game) is boat
        # An empty cradle is no boat at all.
        kept, game.craft = list(game.craft), []
        assert not crossing.has_boat(game)
        game.craft = kept
        return (f"the boat is {craft_sim.kind_of(boat).name}, the roomiest "
                "on the cradle, and only while she is on it")

    @check("she comes home to the cradle, and what the boats put in her tank")
    def _():
        game, craft, conn = _out("craft-home")
        kind = craft_sim.kind_of(craft)
        craft.fuel = 1.0
        conn.rcs = 1.0
        got = craft_sim.recover(game)
        assert got["ok"], got
        assert craft.state == "cradled" and craft.pilot == ""
        assert game.sortie is None
        assert craft.fuel > 1.0 and craft.fuel <= kind.fuel_t, craft.fuel
        assert craft_sim.flying(game) is None
        # Lost is lost: she is off the cradle list.
        was = len(craft_sim.aboard(game))
        craft_sim.launch(game, craft)
        craft_sim.lose(game, "shot to pieces")
        assert len(craft_sim.aboard(game)) == was - 1 and game.sortie is None
        assert craft not in craft_sim.aboard(game)
        return (f"{got['fuelled']:.1f} t into her tank off the ship's own "
                "hold; a craft lost is off the list")
