"""Test suites for SEEDFALL. Run with ``python -m seedfall.tests``.

**Importing this package moves the save file out of the player's way**, and it
has to happen here rather than in `__main__` because a check module can be
imported on its own — probes do it constantly — and importing
`seedfall.tests.test_ui` imports this package first either way.

Fourteen check files call `save_mod.write({"game": game})` with no path. Until
`core.save.save_path` existed, that meant `~/.seedfall/save.json`: measured
after a run, the player's save held 192,514 bytes of a game seeded `lab8` — a
fixture invented for the orrery checks — at day 0 with 18,000 credits. And two
runs at once raced each other's `save.tmp`, which produced five phantom
failures in one session (`anchorage`, `traffic`, `tutorial`, `grudges`,
`territory`), none of them real.

The pid is in the name so concurrent runs cannot collide, which matters because
the full suite takes about 25 minutes against a cron that fires every 10.
`setdefault` so a caller who has already chosen a path keeps it.
"""

from __future__ import annotations

import atexit
import os
import tempfile
from pathlib import Path

from ..core import save as _save_mod
from ..core.save import SAVE_ENV

_SAVE = Path(tempfile.gettempdir()) / f"seedfall-test-{os.getpid()}.json"
#: Only a path this package chose is this package's to delete. The tidy-up
#: used to remove whatever `SEEDFALL_SAVE` named, so a probe that pointed it
#: at a file it meant to keep — or at the player's save — lost it, and its
#: `.bak`, on exit (a play-test's three run saves, 2026-09-18).
_OURS = SAVE_ENV not in os.environ
os.environ.setdefault(SAVE_ENV, str(_SAVE))

#: Under test, a saved object carrying an attribute that is not one of its
#: fields fails the write instead of being silently dropped. Six such
#: attributes lived in the game until 2026-09, and every one of them was
#: lost on every reload.
_save_mod.STRICT = True


@atexit.register
def _tidy_up() -> None:
    """Take the run's save away with it, and the staging file beside it."""
    if not _OURS:
        return
    here = _SAVE
    staged = list(here.parent.glob(here.name + ".*.tmp"))
    for leftover in [here, here.with_suffix(".tmp"),
                     here.with_name(here.name + ".bak"), *staged,
                     here.with_name(here.stem + ".hall.json"),  # sim/memoir
                     *here.parent.glob(here.stem + ".*.bad")]:
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            pass
