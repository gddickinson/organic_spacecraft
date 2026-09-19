"""Fixtures for `test_renown`: facts held where a check puts them, a set of
seeded game states for the counsel, and a Hall in a folder of its own.

Not a suite.
"""

from __future__ import annotations

import contextlib
import copy
import os
import tempfile
from pathlib import Path

from ..core.rng import RNG
from ..core.state import new_game
from ..sim import renown, renown_facts


@contextlib.contextmanager
def facts(values: dict):
    """Every fact reads from `values` (0 when absent) while inside."""
    real = renown_facts.fact
    renown_facts.fact = lambda _g, key: float(values.get(key, 0.0))
    try:
        yield values
    finally:
        renown_facts.fact = real


@contextlib.contextmanager
def perk_off(key: str):
    """One perk switched off, the rest as the rank says."""
    real = renown.perk
    renown.perk = lambda g, k: False if k == key else real(g, k)
    try:
        yield
    finally:
        renown.perk = real


def ranked(game, rank_id: str) -> None:
    """Give the captain the renown a rank needs (and nothing else)."""
    st = renown.ensure(game)
    st.score = next(need for rid, _n, need in renown.RANKS if rid == rank_id)


@contextlib.contextmanager
def hall_folder():
    """A save — and so a Hall — in a folder of its own for the check."""
    from ..core import save as save_mod
    before = os.environ.get(save_mod.SAVE_ENV)
    with tempfile.TemporaryDirectory() as where:
        os.environ[save_mod.SAVE_ENV] = str(Path(where) / save_mod.SAVE_NAME)
        try:
            yield Path(where)
        finally:
            if before is None:
                os.environ.pop(save_mod.SAVE_ENV, None)
            else:
                os.environ[save_mod.SAVE_ENV] = before


def _mutate(game, rng) -> None:
    """Knock a state about: what urgent counsel exists to catch."""
    from ..sim.ship import apply_damage
    roll = rng.int(0, 5)
    if roll == 0:
        game.ship.cargo["volatiles"] = rng.int(0, 11)
    elif roll == 1:
        apply_damage(game.ship, rng.int(200, 700))
    elif roll == 2:
        game.credits = rng.int(0, 3000)
    elif roll == 3:
        game.credits += rng.int(20_000, 80_000)
    elif roll == 4:
        game.ship.crew = max(1, game.ship.crew // 3)
    for cid in ("biomass",):
        if rng.chance(0.3):
            game.ship.cargo[cid] = 0.0


def states(count: int = 200) -> list:
    """`count` game states: five sectors played by the careful captain to
    several depths, each copy knocked about differently."""
    from . import careful_captain as cc
    out = []
    bases = []
    for seed in ("counsel-a", "counsel-b", "counsel-c", "counsel-d",
                 "counsel-e"):
        g = new_game(seed)
        rng = RNG(f"counsel-{seed}")
        plan: dict = {}
        for stop in (5, 60, 200, 420):
            while g.day < stop and not g.dead and not g.victory:
                day = g.day
                cc.turn(g, rng, plan)
                if g.day == day:
                    g.advance_days(1)
            if not g.dead:
                bases.append(copy.deepcopy(g))
    rng = RNG("counsel-states")
    while len(out) < count:
        base = bases[len(out) % len(bases)]
        game = copy.deepcopy(base)
        _mutate(game, rng)
        game.recompute()
        out.append(game)
    return out
