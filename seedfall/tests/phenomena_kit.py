"""Scenes the sky's checks stand a hull in. Not a suite.

The sky is scheduled from the seed, so a scene is *found*, not forced: walk
a chronicle's seasons for the first real event of a kind that suits, then
put the hull there on the right day. Nothing here patches the schedule —
a check that forced a storm would be testing the fixture.
"""

from __future__ import annotations

from ..core.state import new_game
from ..sim import flight
from ..sim import phenomena as sky_sim


def find(seed: str, kind: str, ok=None, seasons: int = 60, game=None):
    """(game, event): the first real `kind` in `seed`'s sky that `ok` likes."""
    game = game if game is not None else new_game(seed)
    for season in range(seasons):
        for events in sky_sim.season_map(game, season).values():
            for event in events:
                if (event.kind == kind and event.real and event.start > 2
                        and (ok is None or ok(game, event))):
                    return game, event
    raise LookupError(f"no {kind} in {seed}'s first {seasons} seasons")


def put(game, system_id: int) -> None:
    """Stand the hull in a system, off everything."""
    game.location_id = system_id
    flight.arrive_in_system(game)


def on_day(game, day: int) -> None:
    """Move the calendar to `day - 1` and live the last day through the clock,
    so the sky's tick runs on `day` exactly as it would in play."""
    game.day = day - 1
    game.advance_days(1)


def at(game, event, offset: int = 0) -> None:
    """The hull in the event's system on its start day (plus `offset`)."""
    put(game, event.system_id)
    on_day(game, event.start + offset)


def berth_body(game):
    """The body the quay here stands over, or None."""
    from ..sim import anchorage
    body, _index = anchorage.anchor_body(game.system)
    return body if game.system.port else None


def open_cradle(game) -> None:
    """The Cradle, generated and open as of today."""
    from ..world import regions as world_regions
    world_regions.generate(game.galaxy, "cradle", game.day)


class Recorder:
    """Stands in for a game's luck and writes down the odds it is asked."""

    def __init__(self):
        self.asked: list = []

    def chance(self, p: float) -> bool:
        self.asked.append(float(p))
        return False

    def int(self, lo, _hi):
        return lo

    def float(self, lo=0.0, _hi=1.0):
        return lo

    def pick(self, items):
        return items[0]

    def next(self) -> float:
        return 0.5
