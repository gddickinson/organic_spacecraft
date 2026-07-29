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

        from .suites import ALL_SUITES, SUITES, SUITES_BY_KEY

        # The dispatch used to be seventy-eight hand-written blocks and this
        # check read the source for them. It is a table now, so the question
        # is asked of the table directly — which is stronger: a row that names
        # a module that cannot be imported, or has no `run`, fails here rather
        # than the moment somebody asks for that suite.
        assert ALL_SUITES == [s.key for s in SUITES], (
            "ALL_SUITES has drifted from the table it is derived from")
        assert len(SUITES_BY_KEY) == len(SUITES), (
            "two suites share a key, so one of them can never be asked for")

        checked = 0
        for spec in SUITES:
            module = importlib.import_module(f"seedfall.tests.{spec.module}")
            assert hasattr(module, "run"), (
                f"{spec.key} dispatches to {spec.module}, which has no `run`")
            assert spec.label, spec.key
            checked += 1
        assert checked > 60, checked
        return f"{checked} suites, every one dispatching to a real module"

