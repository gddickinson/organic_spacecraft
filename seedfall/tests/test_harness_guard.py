"""Whether the harness itself is telling the truth.

A suite that does not exist looks exactly like a suite that passes. Running a
missing one prints nothing and exits zero, so a lost registration, a typo, or
a renamed module is indistinguishable from success — which cost an hour when
a `git checkout` quietly reverted one.

Split out of `test_sim` when that file crossed five hundred lines. Checks
about the tests belong together anyway.
"""

from __future__ import annotations

import pathlib

from .harness import Suite


def run(suite: Suite) -> None:
    check = suite.check

    @check("every suite that is registered actually runs")
    def _():
        """A suite that does not exist looks exactly like a suite that passes.

        `python3 -m seedfall.tests hands` printed nothing and exited zero for
        an hour last cycle, because a `git checkout` had quietly reverted its
        registration. The runner skips names it does not recognise in silence,
        so a lost `if "x" in wanted:` block, a typo, or a missing import is
        indistinguishable from success.

        Checked statically rather than by running them: this lives *in* a
        suite, so shelling out to run one recursed until it timed out.
        """
        import importlib
        import re

        from .__main__ import ALL_SUITES

        root = pathlib.Path(__file__).resolve().parent.parent.parent
        source = (root / "seedfall" / "tests" / "__main__.py").read_text()

        missing = [name for name in ALL_SUITES
                   if f'if "{name}" in wanted' not in source]
        assert not missing, (
            "listed in ALL_SUITES and dispatched by nothing — running them "
            f"prints nothing and exits zero: {missing}")

        # And whatever each block imports has to be importable and have a
        # `run`, or the dispatch raises the moment somebody asks for it.
        checked = 0
        for name in ALL_SUITES:
            block = source.split(f'if "{name}" in wanted:', 1)[1][:400]
            found = re.search(r"from \. import (\w+)", block)
            assert found, f"{name} is dispatched but imports nothing"
            module = importlib.import_module(f"seedfall.tests.{found.group(1)}")
            assert hasattr(module, "run"), (
                f"{name} dispatches to {found.group(1)}, which has no `run`")
            checked += 1
        return f"{checked} suites, every one dispatched to a real module"

