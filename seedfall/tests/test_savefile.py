"""Where the chronicle is kept, and whose chronicle a test run is allowed to touch.

This suite exists because the answer used to be "the player's", and nothing
noticed. `core/save` spent `SAVE_PATH` as a *default argument* on `write`,
`read`, `exists` and `clear`; a default binds when the function is defined, so
the path could not be redirected by a test, by a second process, or by
assigning to the constant afterwards.

Measured, not supposed. After a full suite run, `~/.seedfall/save.json` held
192,514 bytes of a game seeded `lab8` — a fixture invented three cycles earlier
for the orrery checks — sitting at day 0 with 18,000 credits. Fourteen check
files call `save_mod.write({"game": game})` with no path, and every one of them
was writing over whatever the player had.

The same binding caused the phantom failures the cycle prompt warns about: two
runs at once race each other through `save.tmp`, and one session lost five
checks that way (`anchorage`, `traffic`, `tutorial`, `grudges`, `territory`),
none of them a real defect.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..core import save as save_mod
from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("a test run keeps its chronicle somewhere that is not the player's")
    def _():
        here = save_mod.save_path()
        theirs = save_mod.SAVE_DIR / save_mod.SAVE_NAME
        assert os.environ.get(save_mod.SAVE_ENV), (
            f"{save_mod.SAVE_ENV} is unset, so this run is writing to "
            f"{here} — importing `seedfall.tests` is supposed to set it")
        assert here != theirs, f"the run is saving straight to {theirs}"
        assert str(os.getpid()) in here.name, (
            f"{here.name} does not carry the pid, so two runs at once would "
            "share a save file and race each other through save.tmp")
        return f"{here.name}, not {theirs}"

    @check("saving with no path named does not touch the player's save")
    def _():
        # The defect exactly, and the only check here that would have caught
        # it: every caller below passes no path, which is what the fourteen
        # check files do.
        theirs = save_mod.SAVE_DIR / save_mod.SAVE_NAME
        before = (theirs.exists(),
                  theirs.stat().st_mtime_ns if theirs.exists() else 0,
                  theirs.stat().st_size if theirs.exists() else 0)

        # Refuse *before* writing, not after. The first draft wrote and then
        # compared, which meant that when it failed it had already done the
        # damage — running it against the reverted code to prove it bites put
        # a 52-byte marker over the player's save. A check that destroys what
        # it is guarding is not a guard.
        assert save_mod.save_path() != theirs, (
            f"a pathless write would land on the player's save at {theirs}; "
            "refusing to make the point by doing it")

        assert save_mod.write({"marker": "test-savefile"}), "save returned False"
        got = save_mod.read()
        assert got and got.get("marker") == "test-savefile", (
            f"wrote with no path and read back {got!r}")
        assert save_mod.exists(), "exists() cannot see what write() just made"

        after = (theirs.exists(),
                 theirs.stat().st_mtime_ns if theirs.exists() else 0,
                 theirs.stat().st_size if theirs.exists() else 0)
        assert before == after, (
            f"a pathless write moved the player's save at {theirs}: "
            f"{before} -> {after}")
        return (f"wrote, read and cleared {save_mod.save_path().name}; "
                f"{theirs} untouched")

    @check("the environment is the one door, and it is asked every time")
    def _():
        # A *call-time* resolution, not a default argument. Proved by moving
        # the variable underneath the module and watching the answer follow —
        # which is precisely what could not happen before.
        was = os.environ.get(save_mod.SAVE_ENV)
        moved = Path(os.environ["TMPDIR"] if "TMPDIR" in os.environ else "/tmp")
        moved = moved / f"seedfall-door-{os.getpid()}.json"
        try:
            os.environ[save_mod.SAVE_ENV] = str(moved)
            assert save_mod.save_path() == moved, (
                f"moved {save_mod.SAVE_ENV} to {moved} and save_path() still "
                f"answers {save_mod.save_path()}")
            assert save_mod.write({"marker": "moved"}), "save returned False"
            assert moved.is_file(), f"{moved} was not written"
            os.environ.pop(save_mod.SAVE_ENV)
            assert save_mod.save_path() == \
                save_mod.SAVE_DIR / save_mod.SAVE_NAME, (
                "with the variable unset it should fall back to the player's")
        finally:
            if was is None:
                os.environ.pop(save_mod.SAVE_ENV, None)
            else:
                os.environ[save_mod.SAVE_ENV] = was
            moved.unlink(missing_ok=True)
        return f"followed {save_mod.SAVE_ENV} to {moved.name} and back"
