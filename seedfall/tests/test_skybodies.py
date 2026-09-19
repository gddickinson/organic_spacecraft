"""Bodies that come and go, and the star that goes: comets, rogues, the nova.

The delicate part of the living sky (`sim/phenomena_bodies.py`), split from
`test_phenomena` for length:

- **A comet appears, can be mined, gluts the quays, and leaves cleanly** —
  the hull holding at it stands off with a log line, nothing permanent could
  be put on it, a flight that would arrive after it has gone is not begun,
  and no structured reference to it survives in the save.
- **A rogue's trench, a crossing to it and a live conn** are settled when it
  goes, and it waits for the two that cannot be settled inside the clock.
- **The nova**: once, only in the Cradle and only once it is open, forecast
  months ahead, a dose that mounts, then the burst — a neutron star by the
  remnant table, the quay evacuated, burst data taken from a neighbour.
"""

from __future__ import annotations

import json

from ..core import save as save_mod
from ..core.state import new_game
from ..data import phenomena as data
from ..sim import actions, flight
from ..sim import phenomena_bodies as bodies_sim
from ..sim import phenomena as sky_sim
from ..sim import phenomena_nova as nova_sim
from ..sim import phenomena_science as science
from . import phenomena_kit as kit
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("a comet arrives, is mined, gluts the quays, and leaves cleanly")
    def _():
        game, comet = kit.find("sky-comet", "comet", _mineable)
        kit.put(game, comet.system_id)
        kit.on_day(game, comet.start - 1)
        count = len(game.system.bodies)
        kit.on_day(game, comet.start)
        body = game.system.bodies[-1]
        assert len(game.system.bodies) == count + 1
        assert body.transient_until == comet.end and body.kind == "comet"
        glutted = [sid for sid, shocks in bodies_sim.gluts(game).items()
                   if any(s.until == comet.end for s in shocks)]
        assert glutted, "no quay heard about the comet"
        game.ship.cargo = {"volatiles": 100}
        index = len(game.system.bodies) - 1
        got = actions.extract(game, index, 10)
        assert got["ok"], got
        assert got["got"].get("volatiles", 0) > 0 and \
            got["got"].get("phosphate", 0) > 0, got["got"]
        assert game.orbit_body == body.id
        from ..sim import colony as colony_sim, landing
        assert not landing.kind_allows(body)
        refused = colony_sim.can_found(game, game.system, body, "medusa_still")
        assert not refused[0] and "passing" in refused[1], refused
        flight.stand_off(game)
        game.day = comet.end - 1               # too late to fly out to it
        late = flight.travel_to(game, index, "coast")
        assert not late["ok"] and "gone before" in late["why"], late
        flight.hold_at(game, body)
        kit.on_day(game, comet.end)
        assert body not in game.system.bodies and len(game.system.bodies) == count
        assert game.orbit_body is None, "the hull went with the comet"
        told = [t for _d, t, _k in game.log[-6:] if "stands off" in t]
        assert told, "the helm stood off without a word"
        _no_ghost(game, body)
        return (f"{body.name}: {got['got'].get('volatiles', 0):.0f} t "
                f"volatiles, {got['got'].get('phosphate', 0):.1f} t phosphate "
                f"in 10 days; {len(glutted)} quays glutted; gone on day "
                f"{comet.end}, the hull stood off")

    @check("a rogue's trench, a crossing to it and a live conn are all "
           "settled when it goes")
    def _():
        from ..sim import dig as dig_sim, transit as transit_sim
        game, rogue = kit.find("sky-rogue", "rogue", seasons=90)
        kit.at(game, rogue)
        body = game.system.bodies[-1]
        index = len(game.system.bodies) - 1
        assert body.transient_until == rogue.end and body.sunless
        from ..data.xenotech import XENOTECH
        body.relic, body.relic_found = XENOTECH[0].id, True
        game.dig = dig_sim.Dig(id=1, body_index=index, body_name=body.name,
                               tech_id=body.relic, system_id=game.location_id)
        game.transit = transit_sim.Transit(id=1, body_index=index,
                                           body_name=body.name,
                                           burn="standard", watches=4)
        game.sky.lee = body.id

        class Flying:                           # a conn in the air
            landed = False
        game.conn = Flying()
        kit.on_day(game, rogue.end)
        assert body in game.system.bodies, "left from under a live conn"
        game.conn.landed = True
        game.advance_days(1)
        assert body in game.system.bodies, "left from under a crossing"
        game.transit.over = True                # she arrived
        game.advance_days(1)
        assert body not in game.system.bodies
        assert game.dig.over and game.conn is None and game.sky.lee is None
        _no_ghost(game, body)
        return (f"{body.name} waited out the conn and the crossing, then "
                f"left: trench {game.dig.outcome}")

    @check("the nova: once, in the Cradle, forecast months ahead, and it "
           "scours what it touches")
    def _():
        game = new_game("sky-nova")
        sky = sky_sim.state(game)
        game.advance_days(3)
        assert sky.nova is None, "a nova without a Cradle"
        kit.open_cradle(game)
        game.advance_days(1)
        nova = sky.nova
        assert nova is not None and nova.begins - game.day >= data.NOVA_DELAY[0] - 1
        star = game.galaxy.systems[nova.system_id]
        assert star.region == "cradle" and star.star != data.NOVA_REMNANT
        from ..world.galaxy import Port
        star.port = Port("outpost", "Test Quay", 1, ("market",), "charter")
        kit.put(game, nova.system_id)
        kit.on_day(game, nova.begins)
        heard = [s for s in game.signals if "nova" in s.subject]
        assert heard and nova.bursts - nova.begins >= 120
        early = sky_sim.dose(game)
        game.day = nova.bursts - 20
        late = sky_sim.dose(game)
        assert 0 <= early < late, (early, late)
        said = science.observe(game)
        assert said["ok"] and said["stage"] == "brightening", said
        neighbour = min((s for s in game.galaxy.systems
                         if s.region == "cradle" and s.id != star.id),
                        key=lambda s: _ly(s, star))
        kit.put(game, neighbour.id)
        kit.on_day(game, nova.bursts)
        assert nova.burst and star.star == data.NOVA_REMNANT
        assert star.port is None and star.market is None
        assert all(not b.lifeforms and not b.surveyed for b in star.bodies)
        from ..data.remnants import NEUTRON
        kinds = {k for _w, k in NEUTRON.weights}
        assert all(b.kind in kinds for b in star.bodies), star.bodies
        burst = science.observe(game)
        assert burst["ok"] and burst["stage"] == "burst", burst
        game.galaxy.regions[-1].opened_day += 1
        nova_sim.ensure(game, sky)
        assert sky.nova is nova, "a second nova"
        assert sky_sim.progress(game)["nova"] == "watched"
        return (f"{star.name}: forecast {nova.bursts - nova.begins} days out, "
                f"dose {early:.2f} → {late:.2f}; now a neutron star, quay "
                f"evacuated, burst watched from {neighbour.name}")


def _ly(a, b) -> float:
    from ..world.galaxy import distance
    return distance(a, b)


def _mineable(game, event) -> bool:
    system = game.galaxy.systems[event.system_id]
    return bool(system.port) and event.end - event.start >= 40


def _no_ghost(game, body) -> None:
    """No structured reference to a departed body anywhere in the save."""
    raw = save_mod.encode({"game": game})["game"]
    raw.pop("log", None)
    raw.pop("signals", None)
    sky = raw.get("sky") or {}
    sky.pop("observed", None)
    blob = json.dumps(raw, default=str)
    assert f'"{body.id}"' not in blob, "a departed body is still referenced"
    assert game.orbit_body != body.id
