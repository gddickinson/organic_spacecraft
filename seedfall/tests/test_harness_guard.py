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

        # **This used to forbid a fast path naming a suite in `SLOW`**, on the
        # grounds that a constant's verdict would then depend on having an
        # entry. That was right while `SLOW` held seventeen suites that mostly
        # needed a window. It is wrong now: the two stages have different jobs.
        # The fast path is *the suite that knows this module* and running one
        # expensive suite for the one constant it speaks for is exactly what it
        # is for; the broad stage is *did anything at all notice* and has to be
        # cheap enough to finish, or it abstains and guards nothing. Measured,
        # 118 of the fast paths now name a suite the broad set excludes, and
        # every one of them is the right suite for its module.
        #
        # What still has to hold is that a fast path names a suite that exists
        # — checked above — and that it is named once, checked below.

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

        # And every key names a module that exists. A row for something that
        # was renamed or deleted can never be consulted and quietly makes the
        # table look bigger than it is — `declared` sat here for cycles with
        # no `declared` module anywhere in the package. Measured when this
        # moved in: dropping the assertion let a ghost entry back through
        # every other check in the project.
        here = {path.stem
                for folder in ("data", "sim", "core", "world", "ui")
                for path in (pathlib.Path(tripwire.__file__).resolve()
                             .parent.parent / folder).glob("*.py")}
        ghosts = sorted(m for m in tripwire.KIN if m not in here)
        assert not ghosts, (
            f"fast paths for modules that do not exist: {ghosts}")
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

    @check("every suite measured over budget is out of the broad stage")
    def _():
        # **The guard for the defect behind #131.** `tripwire` runs a
        # constant's own suites and then a broad set, and a timeout in either
        # used to count as proof it noticed. The broad set cost 36 seconds when
        # written and about thirteen minutes once `core/clock.MAX_STEP` became
        # 1, so it timed out on everything and handed every constant a pass
        # mark earned by a stopwatch. `completes` makes an unfinishable stage
        # abstain, which is honest but leaves those constants unguarded —
        # measured, 9 survivors in the first 18 swept.
        #
        # So the broad set has to stay affordable. Timed individually: 155
        # suites, 761 s in total, `politics` alone 145. These are the ones over
        # 1.5 s; excluding them leaves 71 suites and about 30 s.
        #
        # This is deliberately a *static* check. Asking whether the stage
        # really finishes means running 71 suites inside a suite run, and
        # measured that way it exceeds `LIMIT` on a loaded machine — it would
        # be timing the hardware, not the design. Re-time with the script in
        # the task notes when suites change speed, and update this list.
        from . import tripwire
        over_budget = {
        "aftermath", "anchorage", "approaching", "bench", "bloom",
        "burns", "byhand", "cameras", "cargo", "charting",
        "climbs", "conn", "connwindow", "counter", "courting",
        "customs", "declared", "docking", "dormancy", "drawbudget",
        "empire", "evidence", "exchequer", "fence", "fleets",
        "fog", "freight", "gates", "geography", "grants",
        "grudges", "hands", "helm", "industry", "landing",
        "levy", "life3d", "lopsided", "mining", "notes",
        "officials", "options", "orbits", "orders", "orrery",
        "parley", "picture", "pilot", "politics", "postings",
        "programmes", "provisional", "public", "readiness", "research",
        "reticle", "revived", "robots", "robots3d", "salvage",
        "seams", "seatwork", "settlement", "showflying", "sim",
        "stranded", "territory", "thermal", "thermal_doors", "thrusters",
        "ticks", "time", "trade", "traffic", "transit",
        "turnplan", "tutorial", "ventures", "war", "watches",
        "wayhome", "weave", "wharfage", "works3d",
        }
        adrift = sorted(over_budget - tripwire.SLOW)
        assert not adrift, (
            f"measured over 1.5 s and still in the broad stage: {adrift} — "
            "the stage will stop finishing inside LIMIT, abstain, and leave "
            "every constant its own fast path misses unguarded")
        assert len(tripwire.SUITES) >= 60, (
            f"the broad stage is down to {len(tripwire.SUITES)} suites; it is "
            "meant to be a wide net, not a second fast path")
        return (f"{len(over_budget)} suites over budget, all excluded; "
                f"{len(tripwire.SUITES)} left in the net")

    # **The five-hundred-line rule used to be checked here too, with a debt
    # list of its own.** `tests/test_length.py` grew a second one, and within
    # two cycles they had drifted: this copy still carried `sim/conn.py` at
    # 612 and `sim/control.py` at 602 after both had been split and struck off
    # the other, and the two disagreed about `ui/viewport.py` — 535 against
    # 533. Two lists of what is too long is the exact fault this file exists
    # to catch, wearing a checker's coat.
    #
    # `tests/test_length.py` is the one door now: it holds the ceilings, and
    # it refuses a row for a debt that has been paid, which is what would have
    # caught the drift had there been only one list to drift from.
