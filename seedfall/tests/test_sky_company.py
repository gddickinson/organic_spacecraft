"""Each hull in the other's sky: the launch from the bridge, the ship from
the launch.

A player asked to be able to take the ship into orbit of a world, send a
lander down, and *see* it happen from both windows. Two of those three were
already here and had never been joined: the Helm's transfer puts a hull in
orbit of a body (`game.orbit_body`), and `ui/viewport.py` has drawn the sky
out of a `sim/conn.Conn` since the conn was written — including the sky a
craft's own sortie flies in, because a sortie *is* a conn.

What was missing is the one thing in that sky which moves while you watch
it. `sim/sky.build` places the system round the target once, when the
approach opens, and says why: bodies move on a scale of months and an
approach is over in hours. A launch does not. She leaves the cradle, crosses
ten thousand kilometres and comes back inside one flight.

So `sim/sky.company` places your *own* other hull live, every beat, in
whichever frame is asking. The claims:

- **Both windows see it**, and they agree about the range.
- **Alongside she is a shape; far off she is a light** — the same rule the
  rest of the sky is drawn by, measured from the eye rather than from the
  frame's origin, which is the whole reason a `Sight` now knows where it is
  being looked at from.
- **They are drawn as themselves**: your hull's own family silhouette and a
  launch's own shape, not the unmarked hull every stranger gets.
- **The static sky stays static** while the company moves.
- **Orbit is the state a party goes down from**, and the screens say so.
"""

from __future__ import annotations

from ..core.state import new_game
from ..data import models3d
from ..sim import (craft as craft_sim, descent, flight, freeflight,
                   sky as sky_sim)
from ..world.planets import BODY_KINDS
from .harness import Suite


def _away(seed: str = "company"):
    """A chronicle with her lander out and the bridge's own conn open."""
    game = new_game(seed)
    craft = next(c for c in craft_sim.aboard(game)
                 if craft_sim.kind_of(c).role == "lander")
    got = craft_sim.launch(game, craft)
    assert got["ok"], got
    game.conn, why = freeflight.begin(game)
    assert game.conn is not None, why
    return game, craft, game.sortie, game.conn


def run(suite: Suite) -> None:
    check = suite.check

    @check("both windows see the other hull, and agree how far off it is")
    def _():
        game, craft, sortie, bridge = _away("both")
        for _n in range(4):
            craft_sim.beat(game, "forward", main=True, ticks=4)
        from_launch = sky_sim.refresh_company(game, sortie)
        from_bridge = sky_sim.refresh_company(game, bridge)
        assert len(from_launch) == 1 and len(from_bridge) == 1, (
            from_launch, from_bridge)
        assert from_launch[0].name == game.ship.name
        assert from_bridge[0].name == craft.name
        apart = craft_sim.out_km(game)
        assert abs(from_launch[0].range_km - apart) < max(1.0, apart * 0.02)
        assert abs(from_bridge[0].range_km - apart) < max(1.0, apart * 0.02)
        # And nobody sees themselves.
        assert all(s.name != craft.name for s in from_launch)
        assert all(s.name != game.ship.name for s in from_bridge)
        return (f"{apart:,.0f} km apart: the bridge has {craft.name} and "
                f"the cockpit has {game.ship.name}, to the kilometre")

    @check("alongside she is a shape, and a long way off she is a light")
    def _():
        game, craft, sortie, bridge = _away("shapes")
        rows = []
        for km in (0.2, 2.0, 60.0):
            sortie.pos = [km, 0.0, 0.0]
            ship = sky_sim.refresh_company(game, sortie)[0]
            launch = sky_sim.refresh_company(game, bridge)[0]
            rows.append((km, ship.apparent_deg, ship.is_shape,
                         launch.is_shape))
        assert rows[0][2] and rows[0][3], rows[0]
        assert not rows[-1][2] and not rows[-1][3], rows[-1]
        assert rows[0][1] > rows[1][1] > rows[2][1], rows
        # The measurement is from the eye. Judged from the frame's origin —
        # which is where the ship is — she would fill the window at every
        # range, which is what `Sight.seen_from` exists to stop.
        sortie.pos = [60.0, 0.0, 0.0]
        far = sky_sim.company(game, sortie)[0]
        assert far.seen_from is not None
        import math
        assert math.dist(far.at, (0.0, 0.0, 0.0)) < far.range_km / 100.0
        return "; ".join(f"{km:g} km: {deg:.2f}°"
                         + (" shape" if shape else " light")
                         for km, deg, shape, _l in rows)

    @check("your own hulls are drawn as themselves, not as a stranger")
    def _():
        game, craft, _sortie, _bridge = _away("meshes")
        mine = models3d.present("hull", game.ship.chassis)["mesh"]
        hers = models3d.present("hull", craft_sim.kind_of(craft).id)["mesh"]
        stranger = models3d.present("hull", "unmarked")["mesh"]
        assert len(mine[0]) > len(hers[0]) > 0, (len(mine[0]), len(hers[0]))
        assert mine[0] != stranger[0] and hers[0] != stranger[0]
        # And an errand still reads as its errand.
        courier = models3d.present("hull", "courier")["mesh"]
        assert courier[0] != stranger[0] and courier[0] != hers[0]
        return (f"{game.ship.chassis.upper()} {len(mine[0])} vertices · "
                f"launch {len(hers[0])} · a stranger {len(stranger[0])}")

    @check("the sky it was built with holds still while the company moves")
    def _():
        game, craft, sortie, bridge = _away("static")
        before = list(getattr(bridge, "sky", ()) or ())
        first = sky_sim.refresh_company(game, bridge)[0].range_km
        for _n in range(6):
            craft_sim.beat(game, "forward", main=True, ticks=6)
        after = list(getattr(bridge, "sky", ()) or ())
        moved = sky_sim.refresh_company(game, bridge)[0].range_km
        assert [s.name for s in before] == [s.name for s in after]
        assert all(a.at == b.at for a, b in zip(before, after)), (
            "the static sky moved")
        assert moved > first * 2, (first, moved)
        assert getattr(bridge, "company", None), "nothing kept on the conn"
        return (f"the sky's {len(after)} sights held still; she went from "
                f"{first:,.0f} to {moved:,.0f} km")

    @check("orbit is the state a party goes down from, and the screen says so")
    def _():
        game = new_game("orbit-said")
        world = next((b for b in game.system.bodies
                      if BODY_KINDS[b.kind][2]), None)
        assert world is not None, "no landable body in this system"
        flight.hold_at(game, world)
        assert descent.in_orbit(game, world)
        assert descent.in_orbit(game) is world
        said = descent.says(game)
        assert world.name in said and "can take" in said, said
        # Off it, and the line says what to do about it.
        flight.stand_off(game)
        assert descent.in_orbit(game) is None
        adrift = descent.says(game)
        assert "Not in orbit" in adrift and "Helm" in adrift, adrift
        return f"“{said[:58]}…”; adrift: “{adrift[:44]}…”"
