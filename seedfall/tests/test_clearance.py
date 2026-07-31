"""Being cleared to dock, and being turned away.

Berthing was something the *ship* worked out: `sim/moorings.py` read a table
of fittings, picked the nearest and flew at it. Nobody ever asked the quay
whether it would have you, so a hostile patrol and a Charter Fleet Hub offered
the same welcome — which is to say none, because neither was ever asked.

`sim/clearance.py` moves the authority to the structure. The claims:

- **A structure that will have you assigns a berth and sends the approach**:
  which fitting, where it is, how it is moving, where to hold, and the rate it
  may be crossed at.
- **A refusal is a real answer with a reason.** A hostile hull does not clear
  you; a Weave gate has nothing to tie up to; a world is orbited; and a port
  whose power has turned against you shuts the quay.
- **Ships clear you too**, so hull-to-hull docking is the same act.
- **The berth is the port's choice**, and the approach flies the one it was
  given rather than the one it fancied.
- **What it sends is what the geometry says**, so a clearance and the flying
  cannot disagree.
"""

from __future__ import annotations

import dataclasses
import math

from ..core.state import new_game
from ..sim import berthing as berth_sim
from ..sim import clearance as clearance_sim
from ..sim import flight
from ..sim import moorings
from ..sim import track as track_sim
from .harness import Suite


def _here(seed: str = "cleared"):
    game = new_game(seed)
    flight.travel_to(game, 0)
    return game


def run(suite: Suite) -> None:
    check = suite.check

    @check("a structure that will have you assigns a berth and says how")
    def _():
        game = _here()
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        said = clearance_sim.request(game, quay)
        assert said.granted, said.why
        assert said.berth, said
        assert said.station == quay.name
        # Everything an approach needs, and all of it non-trivial.
        assert said.hold_km > 0.0 and said.reach_km > 0.0, said
        assert said.max_closing > 0.0, said
        assert said.turn_seconds > 0.0 and said.berth_speed > 0.0, (
            "a turning structure cleared a hull without saying it turns")
        # And the words a screen shows carry the figures.
        line = clearance_sim.line(said)
        assert said.berth in line and "m/s" in line, line
        return (f"{said.station}: {said.berth}, hold "
                f"{said.hold_km * 1000:,.0f} m, {said.max_closing:.1f} m/s, "
                f"berth travelling {said.berth_speed:.2f} m/s")

    @check("a refusal is an answer, and says which kind of no it is")
    def _():
        game = _here()
        seen = {}
        body = next(c for c in track_sim.contacts(game) if c.kind == "body")
        seen["a world"] = clearance_sim.request(game, body)
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        seen["a hostile hull"] = clearance_sim.request(
            game, dataclasses.replace(hull, hostile=True))
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        seen["a gate"] = clearance_sim.request(
            game, dataclasses.replace(quay, berth="gate"))
        game.rep[quay.faction] = clearance_sim.WELCOME_AT - 40.0
        seen["a power that hates you"] = clearance_sim.request(game, quay)
        for why, said in seen.items():
            assert not said.granted, (why, said)
            assert len(said.why) > 20, (why, said.why)
        # Four different reasons, not one message four times.
        assert len({s.why for s in seen.values()}) == 4, seen
        # And the standing gate is a *gate*: put back in favour, cleared.
        game.rep[quay.faction] = 0.0
        assert clearance_sim.request(game, quay).granted
        return " · ".join(f"{why}: {said.why.split(':')[0][:38]}"
                          for why, said in seen.items())

    @check("a ship clears you for its collar")
    def _():
        game = _here()
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        said = clearance_sim.request(game, hull)
        assert said.granted, said.why
        assert said.sort == "collar", said.sort
        assert said.berth and said.hold_km > 0.0 and said.reach_km > 0.0, said
        # A hull is not a station: it does not turn, and it offers one point.
        assert said.turn_seconds == 0.0 and said.berth_speed == 0.0, said
        return (f"{said.station}: {said.berth}, hold "
                f"{said.hold_km * 1000:,.0f} m, reach "
                f"{said.reach_km * 1000:,.0f} m")

    @check("the approach flies the berth the port gave it")
    def _():
        # The point of moving the authority: the ship does not get to pick.
        game = _here()
        quay = next(c for c in track_sim.contacts(game)
                    if c.kind == "anchorage")
        conn, why = berth_sim.begin(game, quay)
        assert conn is not None, why
        assert conn.cleared is not None and conn.cleared.granted
        assert conn.berth == conn.cleared.berth, (conn.berth,
                                                  conn.cleared.berth)
        # And the geometry agrees with what was sent: the berth the clearance
        # named is where `moorings` puts it, to the metre.
        found = moorings.nearest(conn)
        assert found["name"] == conn.cleared.berth, (found, conn.cleared)
        assert math.dist(found["at"], conn.cleared.at) < 1e-9, (
            "the clearance and the geometry disagree about where the berth is")
        assert abs(found["reach_km"] - conn.cleared.reach_km) < 1e-9
        # The chronicle heard it.
        said = " ".join(line for _d, line, _k in game.log[-2:])
        assert conn.cleared.berth in said, said
        return (f"cleared for {conn.cleared.berth} and flying it, with the "
                "geometry agreeing to the metre")

    @check("an approach nobody cleared does not begin")
    def _():
        game = _here()
        hull = next(c for c in track_sim.contacts(game) if c.kind == "hull")
        conn, why = berth_sim.begin(game, dataclasses.replace(hull,
                                                              hostile=True))
        assert conn is None, "a hostile hull let a ship come alongside"
        assert "clearing you" in why or "does not answer" in why, why
        # A world, likewise: the conn is not how you arrive at a planet.
        body = next(c for c in track_sim.contacts(game) if c.kind == "body")
        conn2, why2 = berth_sim.begin(game, body)
        # A world *is* approachable — to orbit it — so this one is granted a
        # conn but refused a berth, and the refusal has to say which.
        said = clearance_sim.request(game, body)
        assert not said.granted and "orbit" in said.why, said.why
        return f"hostile: {why[:44]}… · world: {said.why[:44]}…"
