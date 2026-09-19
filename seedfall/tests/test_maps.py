"""The package maps name every module, and nothing that is gone.

Each `seedfall/<package>/INTERFACE.md` is generated (`tests/maps.py`) because
the hand-written map grew to 6,383 lines and still went stale. This is the
ratchet that keeps the generated ones honest: add a module and the map must be
regenerated (`python -m seedfall.tests.maps --write`), or this fails.
"""

from __future__ import annotations

from . import maps
from .harness import Suite


def run(suite: Suite) -> None:
    @suite.check("every package map names every module, and nothing gone")
    def _():
        bad = maps.stale()
        assert not bad, (f"regenerate with `python -m seedfall.tests.maps "
                         f"--write`: {bad}")
        counts = {p: len(maps.modules(p)) for p in maps.PACKAGES}
        assert sum(counts.values()) > 600, counts
        return " · ".join(f"{p} {n}" for p, n in counts.items())

    @suite.check("every map stays under five hundred lines")
    def _():
        sizes = {p: len((maps.ROOT / p / "INTERFACE.md").read_text().splitlines())
                 for p in maps.PACKAGES}
        over = {p: n for p, n in sizes.items() if n >= 500}
        assert not over, over
        return f"largest {max(sizes, key=sizes.get)} at {max(sizes.values())} lines"
