"""Scenes the Kith checks stand a ship in: an opened Cradle, a gathering,
a solved recording. Not a suite — `tests/test_kith.py` reads it.

The Cradle is opened through the real door (`sim/relight.relight`), with the
anchor's reading taken as done: `test_reaches` drives the deep survey itself,
and doing it again here would measure the survey, not the Kith.
"""

from __future__ import annotations

import copy
import itertools

from ..core.state import new_game
from ..data import kith as data
from ..data.regions import DEEP_TECH, RELIGHT_GOODS
from ..sim import flight, gates, kith, kith_world, relight, weave
from ..sim import minigames as mg

_OPENED: dict = {}


def put(game, sid: int) -> None:
    game.location_id = sid
    flight.arrive_in_system(game)


def opened(seed: str):
    """A chronicle with the Cradle relit, standing at the anchor, not met.

    Built once per seed and handed out as a deep copy: every check starts
    from the same day with nobody else's acts in it.
    """
    hit = _OPENED.get(seed)
    if hit is None:
        game = new_game(seed)
        game.credits = 400_000
        game.research.unlocked.append(DEEP_TECH)
        for cid, need in RELIGHT_GOODS.items():
            game.stores[cid] = need * 2
        game.ship.cargo["volatiles"] = 120
        game.recompute()
        sid = relight.anchor_of(game, "cradle")
        put(game, sid)
        weave.ensure(game).read.append(sid)
        out = relight.relight(game, "cradle")
        assert out["ok"], out
        hit = _OPENED[seed] = game
    return copy.deepcopy(hit)


def entry(game):
    from ..world import regions as world_regions
    return world_regions.region(game.galaxy, "cradle").entry_id


def met(seed: str):
    """Through the deep gate: the Kith are met at the Cradle's entry."""
    game = opened(seed)
    assert gates.use(game, entry(game))["ok"]
    return game


def at_gathering(seed: str, index: int = 0):
    """Met, and alongside the `index`th gathering."""
    game = met(seed)
    put(game, kith_world.gatherings(game.galaxy)[index].id)
    return game


def fluent(game, value: float, domains=None) -> None:
    """Set every sign (of these domains) to `value`."""
    state = kith.ensure(game)
    for sign in data.SIGNS:
        if domains is None or sign.domain in domains:
            state.lexicon[sign.id] = value


def solve(game, lose: bool = False) -> dict:
    """Play the bench out: a consistent-guess solver, or throw every try."""
    bench = game.decoding
    pool = list(itertools.product(range(bench.palette),
                                  repeat=mg.CODE_LENGTH))
    while not bench.over:
        guess = list(pool[0])
        if lose:
            guess = [(bench.secret[0] + 1) % bench.palette] * mg.CODE_LENGTH
        said = mg.guess(bench, guess)
        pool = [c for c in pool if mg.score(list(c), guess)
                == (said["exact"], said["near"])] or pool
    return mg.finish_decoding(game)


def truth(game, cid: str) -> str:
    """What the gathering here really thinks of a good."""
    return kith_world.prefs(game.galaxy, game.system)[cid]


def good_taken_as(game, reactions) -> str | None:
    """A good this gathering takes in one of `reactions`, if any."""
    prefs = kith_world.prefs(game.galaxy, game.system)
    return next((cid for cid in ("condensate", "volatiles", "phosphate",
                                 "magnetite", "ore", "spidroin", "trehalose",
                                 "survey", "alloy")
                 if prefs[cid] in reactions), None)
