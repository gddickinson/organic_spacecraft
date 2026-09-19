"""The sky's day: bodies arriving and leaving, the forecast, and telling you.

Called once a day from `core/sectortime.economy` through `phenomena.tick`,
before the markets read their shocks, so a comet's glut is on the quays the
day it arrives. **It draws nothing from the day's luck**: everything here is
read off the schedule, which has its own keys, and the only writes are the
consequences — a body, a shock, a despatch, a line in the log.

What the day costs matters (`tests/test_phenomena` times it with every region
open): the schedule is built once a season for the whole sky and read from
a per-day table, so the day walks a few dozen events, not every star.
"""

from __future__ import annotations

from . import phenomena as sky_sim
from . import phenomena_bodies as bodies_sim
from . import phenomena_forecast as forecast_sim
from . import phenomena_nova as nova_sim


def tick(game, n: int) -> None:
    if n <= 0:
        return
    sky = sky_sim.state(game)
    nova_sim.tick(game, sky)
    live = sky_sim.live(game)
    _bodies(game, sky, live)
    _tell(game, sky, live)
    forecast_sim.issue(game, sky)
    if sky.lee is not None and sky.lee != game.orbit_body:
        sky.lee = None                  # she moved: the shadow is behind her


def _bodies(game, sky, live: dict) -> None:
    """Comets and rogues in, and out when their time is up."""
    running = {e.id: e for events in live.values() for e in events
               if e.spec.transient}
    for event_id in list(sky.transients):
        if event_id not in running:
            bodies_sim.leave(game, sky, event_id)
    for event_id, event in running.items():
        if event_id in sky.transients:
            continue
        body = bodies_sim.arrive(game, sky, event)
        system = game.galaxy.systems[event.system_id]
        if body is not None and (system.visited
                                 or event.system_id == game.location_id):
            game.add_log(f"{event.spec.name} at {system.name}: {body.name}. "
                         f"{event.spec.effect}", "good")


def _tell(game, sky, live: dict) -> None:
    """Say so when something is live where the hull is — once an event."""
    here = live.get(game.location_id, ())
    told = set(sky.told)
    for event in here:
        if event.id in told or event.spec.transient:
            continue
        sky.told.append(event.id)
        left = event.left(game.day)
        game.add_log(f"{event.spec.name} at {game.system.name}, {left} "
                     f"{'day' if left == 1 else 'days'} to run. "
                     f"{event.spec.effect}",
                     "warn" if event.kind in ("flare", "storm", "nova")
                     else "good")
    ids = {e.id for events in live.values() for e in events}
    sky.told[:] = [i for i in sky.told if i in ids]
