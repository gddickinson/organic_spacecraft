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

    @check("the tripwire's fast paths point at suites that exist and run")
    def _():
        """`KIN` is hand-written, and a stale entry fails silently.

        The tool runs a constant against its own neighbourhood first and only
        pays for the wide sweep if that passes. If an entry names a suite that
        no longer exists, `python -m seedfall.tests <name>` runs nothing and
        exits zero — so the fast stage "passes" every time and every constant
        quietly costs the full run instead of two seconds.

        Worse, an entry naming a suite that is in `SLOW` makes the answer
        depend on the map: a constant protected only by a slow suite reads as
        protected when its module has an entry and unprotected when it does
        not. The two stages have to agree on what counts.
        """
        from . import tripwire
        from .suites import ALL_SUITES

        known = set(ALL_SUITES)
        unknown = sorted(f"{mod}->{name}" for mod, near in tripwire.KIN.items()
                         for name in near if name not in known)
        assert not unknown, (
            f"fast paths naming a suite that does not exist, so the stage "
            f"passes without running anything: {unknown}")

        slow = sorted(f"{mod}->{name}" for mod, near in tripwire.KIN.items()
                      for name in near if name in tripwire.SLOW)
        assert not slow, (
            f"fast paths pointing at a suite the sweep itself excludes, so a "
            f"constant's verdict depends on having an entry: {slow}")

        # Every module holding constants either has a fast path or is named
        # here as having no suite that covers it. A new module with tuning in
        # it has to be a decision, not an omission.
        no_suite = {"llm", "loading", "responses", "telemetry", "voice",
                    "xenotech"}
        holding = {path.stem for path, _name, _value in tripwire.constants()}
        adrift = sorted(m for m in holding
                        if m not in tripwire.KIN and m not in no_suite)
        assert not adrift, (
            f"modules with tuning constants and no fast path: {adrift} — add "
            "one, or name them as having no suite")
        stale = sorted(m for m in no_suite if m in tripwire.KIN)
        assert not stale, f"{stale} now has a fast path and is still excused"
        # And each module appears once. A dict literal keeps the *last* value
        # for a repeated key and says nothing, so a second entry silently
        # replaces the first: six modules had two, and `stations` — three seats
        # and every constant they own — was being swept against `("gunnery",)`
        # alone because a narrower entry sat ninety lines below the real one.
        import ast
        import collections
        tree = ast.parse(pathlib.Path(tripwire.__file__).read_text())
        keys = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and \
                    getattr(node.targets[0], "id", "") == "KIN":
                keys = [k.value for k in node.value.keys]
        assert keys, "could not read the KIN table"
        twice = sorted(k for k, n in collections.Counter(keys).items() if n > 1)
        assert not twice, (
            f"{twice} appears more than once in the fast-path table; the later "
            "entry wins and the earlier one is dead")
        return (f"{len(tripwire.KIN)} fast paths, all live and each named once; "
                f"{len(no_suite)} modules named as having no suite")


    @check("a hang only counts as evidence where the run finishes clean")
    def _():
        # **The sweep's second stage has been voting with a stopwatch.**
        # `tripwire.SUITES` is 155 suites and takes about 25 minutes since
        # `core/clock.MAX_STEP` became 1; `LIMIT` is 60 seconds. So it timed
        # out on every constant, mutated or not — and `try_value` read a
        # timeout as "a hang is a very loud notice" and marked the constant
        # protected. Measured after the fix: of the eight negative constants
        # that had only ever "bitten" by hanging, seven fail no check at all.
        #
        # Driven through a stubbed `_run` rather than by running anything, so
        # this is deterministic and costs nothing.
        import subprocess
        from . import tripwire
        real_run, real_clean = tripwire._run, dict(tripwire._CLEAN)
        try:
            def always_hangs(suites):
                raise subprocess.TimeoutExpired("x", tripwire.LIMIT)

            tripwire._run = always_hangs
            tripwire._CLEAN.clear()
            # A set that cannot finish unmutated has nothing to say.
            assert tripwire.completes(("anything",)) is False
            assert tripwire.noticed(("anything",)) is False, (
                "a set that hangs unmutated was read as having objected")
            assert tripwire.suite_passes("nosuchmodule") is True, (
                "a stage that times out even unmutated was allowed to call a "
                "constant protected")

            # And where the set *does* finish clean, a hang is real evidence.
            tripwire._CLEAN.clear()
            tripwire._CLEAN[tuple(tripwire.SUITES)] = True
            calls = {"n": 0}

            def hangs_once(suites):
                calls["n"] += 1
                raise subprocess.TimeoutExpired("x", tripwire.LIMIT)

            tripwire._run = hangs_once
            assert tripwire.completes(tuple(tripwire.SUITES)) is True
            assert calls["n"] == 0, "a cached calibration was re-run"
        finally:
            tripwire._run = real_run
            tripwire._CLEAN.clear()
            tripwire._CLEAN.update(real_clean)
        return "a timed-out stage abstains; a clean one may still convict"
