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

from ..core.save import SAVE_ENV

_SAVE = Path(tempfile.gettempdir()) / f"seedfall-test-{os.getpid()}.json"
os.environ.setdefault(SAVE_ENV, str(_SAVE))


@atexit.register
def _tidy_up() -> None:
    """Take the run's save away with it, and the staging file beside it."""
    here = Path(os.environ[SAVE_ENV])
    for leftover in (here, here.with_suffix(".tmp")):
        try:
            leftover.unlink(missing_ok=True)
        except OSError:
            pass
