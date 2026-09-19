"""Loading the chronicle from disk, checking it, and clearing it.

Split out of `core/state.py` when it reached five hundred lines, along a real
seam: `state` says what a chronicle *is*; this says whether the one on disk
can be played. Everything here is re-exported from `state`, so
`state.load_game` is still the one door.
"""

from __future__ import annotations

from . import ids as ids_mod
from . import save as save_mod


def load_game(path=None):
    """The chronicle at `path` or in play, or None; `load_problem()` says why."""
    global _load_problem
    _load_problem = None
    data = save_mod.read(path)
    if not data:
        _load_problem = save_mod.last_error()
        return None
    from .state import Game
    game = data.get("game")
    if not isinstance(game, Game):
        _load_problem = "the save holds no chronicle"
        return None
    problems = validate(game)
    if problems:
        _load_problem = "; ".join(problems)
        print(f"[seedfall] save refused: {_load_problem}")
        save_mod.quarantine(path or save_mod.save_path())
        return None
    game.ids = ids_mod.bind(ids_mod.restore(game.ids, game))
    # The active ship must be the same object as its entry in the fleet, or
    # damage would apply to a copy.
    for i, f in enumerate(game.fleet):
        if f.uid == game.ship.uid:
            game.fleet[i] = game.ship
            break
    # A chronicle saved before there were two clocks has lived every day the
    # Verge has. Left at zero, a twenty-year captain's crew would be younger
    # than the chronicle and their whole span would come back.
    if not game.ship_day and game.day:
        game.ship_day = game.day
    game.recompute()
    # A Cradle opened before the Kith existed is given its gatherings, from
    # their own seeds, the moment it is read (`sim/kith_world.ensure`).
    from ..sim import kith_world
    kith_world.ensure(game)
    return game


_load_problem: str | None = None


def load_problem() -> str | None:
    """Why the last `load_game` came back empty, in words."""
    return _load_problem


def validate(game) -> list[str]:
    """What would make this chronicle unplayable, if anything. Checked on
    load, because a save that decodes is not yet a game that runs."""
    import math
    out = []
    if not game.fleet:
        out.append("the fleet is empty")
    elif not any(f.uid == game.ship.uid for f in game.fleet):
        out.append("the flagship is not in the fleet")
    uids = [f.uid for f in game.fleet]
    if len(uids) != len(set(uids)):
        out.append("two hulls share an identity")
    if not 0 <= game.location_id < len(game.galaxy.systems):
        out.append(f"the ship is at system {game.location_id}, which is not in "
                   f"the sector")
    if not isinstance(game.credits, (int, float)) or not math.isfinite(game.credits):
        out.append(f"the purse holds {game.credits!r}")
    return out


def has_save() -> bool:
    return save_mod.exists()


def clear_save() -> None:
    save_mod.clear()
