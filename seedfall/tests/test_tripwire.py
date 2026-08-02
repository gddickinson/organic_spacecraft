"""The sweep that guards the constants had nothing guarding it.

`tests/tripwire.py` decides which constants in this game are protected, and its
`KIN` table — the fast path, one entry per module, saying which suites are
worth running for that module's constants — is hand-kept.

**This file said "nothing has ever checked the tool itself", and that was
wrong.** `tests/test_harness_guard` has checked the fast paths since long
before this existed, and checks them harder: that every named suite is real,
that every constant-holding module has an entry or is named as having no
suite, and that no module appears twice — a dict literal keeps the last value
for a repeated key and says nothing, which had silently swept `stations`
against one suite of five. Two of the checks written here duplicated the
weaker half of that and have been removed.

What was genuinely missing, and is all that remains here, is the *measured*
half: which suite has actually been watched to go red when a given constant
moves.

**A hand-kept table of what guards what goes wrong silently, and the verdict it
produces is confident either way.** "SURVIVES" from a sweep with a wrong fast
path does not mean *unprotected*; it means *not caught by the suites I chose to
run*. Measured, `bloom.HEART_HP = 2600.0` was reported as a survivor while
being pinned in `test_play` at half and at double.

**The entries cannot be got right by reading, which is the whole difficulty.**
`test_play` does not import `sim/bloom` or `data/bloom` at all — it plays the
game, and the heart is on the far end of that. `test_tuning` is the only suite
that imports the module and it does not catch the constant. Static analysis of
the imports gets this exactly backwards, so every entry here has to be earned
by mutating the constant and watching a suite go red.

What follows is the part of that which can be held cheaply: the entries stay
well-formed, and the guards that *have* been measured stay named.
"""

from __future__ import annotations

import pathlib

from .harness import Suite
from .sweepkit import constants
from .tripwire import KIN, SLOW

ROOT = pathlib.Path(__file__).resolve().parent.parent


#: Guards proved by mutation: module, constant, and the suite that went red.
#:
#: Every row was measured — the constant halved and doubled, one candidate
#: suite at a time, and this is the one that failed. They are here so a fast
#: path cannot quietly stop naming the only suite that protects a constant,
#: which is exactly what had happened to both of these.
MEASURED = [
    # `bloom` alone ran green; `tuning`, the only importer, ran green.
    ("bloom", "HEART_HP", "play"),
    # `envoy`, `approach`, `politics`, `play`, `sim`, `courting` and
    # `overtures` all ran green on this one.
    ("approaches", "ODDS_PER_DAY", "ticks"),
    # Both were sweep survivors with guards that only looked like guards:
    # `test_approach` built its fixture from `QUIET_DAYS` itself, and
    # `test_tuning` said in a comment that it pinned it and did not. Pinned
    # for real in `test_tuning` now, on the gap between two approaches and on
    # what a family forgets — measured, never read.
    ("approaches", "QUIET_DAYS", "tuning"),
    ("bloom", "RESIST_DECAY", "tuning"),
]



def run(suite: Suite) -> None:
    check = suite.check

    @check("the fast path stops at the first suite that objects")
    def _():
        # **Measured on `exchequer`**, whose fast path is
        # `("exchequer", "politics")`: `exchequer` answers in 3.6 s,
        # `politics` takes 145.4 s — the most expensive suite in the project —
        # and handing both to one run cost 148.0 s a variant. The set of
        # suites consulted is unchanged; asking them one at a time and
        # stopping at the first objection is the whole saving.
        from . import tripwire

        asked = []

        def stub(suites):
            asked.append(tuple(suites))
            # The first suite any module names objects. Nothing after it
            # should ever be run.
            return "exchequer" not in suites and "bloom" not in suites

        real_run, real_clean = tripwire._run, dict(tripwire._CLEAN)
        target = ROOT / "sim" / "exchequer.py"
        before = target.read_text()
        try:
            tripwire._run = stub
            tripwire._CLEAN.clear()
            import contextlib
            import io
            with contextlib.redirect_stdout(io.StringIO()):
                code = tripwire.main(["--fast", "exchequer"])
        finally:
            tripwire._run = real_run
            tripwire._CLEAN.clear()
            tripwire._CLEAN.update(real_clean)
            target.write_text(before)

        assert code == 0, code
        assert asked, "the sweep never ran a suite"
        # Every ask is a single suite, and `politics` is never among them:
        # `exchequer` objected first and the expensive neighbour was spared.
        assert all(len(a) == 1 for a in asked), (
            f"the fast path still hands several suites to one run: "
            f"{[a for a in asked if len(a) != 1][:3]}")
        assert all("politics" not in a for a in asked), (
            "politics was run even though exchequer had already objected")
        return (f"{len(asked)} runs, one suite each, and the 145 s neighbour "
                f"never asked")

    @check("the fast sweep never pays for the broad set")
    def _():
        # `--fast` exists because the two stages cost wildly different
        # amounts: `piracy`'s ten constants, all caught by their own suites,
        # swept in 20 seconds; `exchequer`'s thirteen were still going after
        # thirty minutes. What it produces is a shortlist, not a verdict, and
        # it must say so.
        from . import tripwire

        asked = []
        real_run, real_clean = tripwire._run, dict(tripwire._CLEAN)
        target = ROOT / "data" / "bloom.py"
        before = target.read_text()
        try:
            tripwire._run = lambda suites: asked.append(tuple(suites)) or True
            tripwire._CLEAN.clear()
            import contextlib
            import io
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = tripwire.main(["--fast", "bloom"])
        finally:
            tripwire._run = real_run
            tripwire._CLEAN.clear()
            tripwire._CLEAN.update(real_clean)
            target.write_text(before)

        assert code == 0, code
        wide = [a for a in asked if len(a) > 3]
        assert not wide, (
            f"--fast ran the broad set of {len(wide[0])} suites; stage two is "
            f"exactly what it exists to skip")
        said = out.getvalue()
        assert "shortlist" in said, (
            "the fast sweep called its findings something other than a "
            f"shortlist: {said[-200:]}")
        assert "unprotected" not in said, (
            "the fast sweep called a constant unprotected, which is a verdict "
            "it cannot reach — only its own suites declined to object")
        return f"{len(asked)} runs, none of them the broad set, and it says so"

    @check("the sweep runs, and puts every file back exactly as it was")
    def _():
        # **`main` had no check of any kind, and it was dead at HEAD.** A local
        # `noticed = False` in `main` shadowed the module-level `noticed()` for
        # the whole function including its closure, so the first constant it
        # tried called `False(suites)` and the tool died with "'bool' object is
        # not callable". Nothing noticed, because nothing ever ran it — #134's
        # re-sweep had been waiting on a tool that could not start.
        #
        # The suites are stubbed out: what is under test is the sweep's own
        # loop, not whether the game passes. `_run` returning False means the
        # run failed, which is what `noticed` calls an objection — so every
        # candidate is caught, the survivor list is empty, and the sweep says
        # nothing on the way past.
        from . import sweepkit, tripwire

        target = ROOT / "sim" / "tug.py"
        before = target.read_text()
        import contextlib
        import io
        out = io.StringIO()
        real_run, real_clean = tripwire._run, dict(tripwire._CLEAN)
        try:
            tripwire._run = lambda suites: False
            tripwire._CLEAN.clear()
            with contextlib.redirect_stdout(out):
                code = tripwire.main(["tug"])
        finally:
            tripwire._run = real_run
            tripwire._CLEAN.clear()
            tripwire._CLEAN.update(real_clean)

        assert code == 0, f"the sweep exited {code}"
        said = out.getvalue()
        assert "0 of 5 constants are unprotected" in said, said[-300:]
        after = target.read_text()
        assert after == before, (
            "the sweep did not put sim/tug.py back the way it found it — "
            f"{len(before)} bytes before, {len(after)} after")
        # And it had something to sweep, or the run proves nothing.
        found = [n for p, n, _v in sweepkit.constants("tug")]
        assert len(found) >= 4, f"only {found} to sweep in tug"
        return f"swept {len(found)} constants and restored the file byte for byte"

    @check("a negative constant is not invisible, and a rewrite round-trips")
    def _():
        # Two traps `sweepkit` exists to remember. A negative literal parses as
        # `UnaryOp(USub, Constant(...))`, not `ast.Constant`, and for as long
        # as the finder matched only the latter, 14 of 436 constants were
        # invisible — among them whether two powers are at war. And a rewrite
        # that does not restore exactly is how a probe once left
        # `data/industry.py` at zero bytes.
        from . import sweepkit

        every = sweepkit.constants()
        negatives = [(p.stem, n, v) for p, n, v in every if v < 0]
        assert negatives, (
            f"{len(every)} constants found and not one negative — the finder "
            f"is matching ast.Constant only and cannot see -60.0")
        assert len(every) > 400, len(every)

        # **Restore from the snapshot, never from what `rewrite` handed
        # back.** Proving this check bites means breaking `rewrite`, and the
        # first version's cleanup wrote back `rewrite`'s own return value — so
        # the mutation that broke restoring also broke the undo, and left
        # `data/gates.py` sitting on disk with `TOLL_REFUSED_BELOW = 0`. A
        # check that cleans up through the thing it is testing has no cleanup.
        path, name, value = negatives[0]
        target = ROOT / f"{'data' if (ROOT / 'data' / f'{path}.py').exists() else 'sim'}" / f"{path}.py"
        before = target.read_text()
        try:
            original = sweepkit.rewrite(target, name, 0)
            assert original == before, "rewrite did not hand back the original"
            now = target.read_text()
            assert now != before, f"{path}.{name} was not actually changed"
            assert f"{name} = 0" in now, f"{name} not set in {path}"
        finally:
            target.write_text(before)
        assert target.read_text() == before, "the file was not put back"
        return (f"{len(every)} constants, {len(negatives)} negative; "
                f"{path}.{name} = {value} rewritten and restored")

    @check("a fast path still names the suite measured to guard its constant")
    def _():
        # The defect this file exists for. Both rows were sweep survivors that
        # were in fact pinned, because the fast path did not name the suite
        # doing the pinning and the broad stage does not run it either — so
        # neither stage ran the only check that would have gone red.
        held = {}
        for module, name, guard in MEASURED:
            named = KIN.get(module)
            assert named, f"{module} has no fast path at all"
            assert guard in named, (
                f"{module}.{name} is guarded by the {guard!r} suite, measured, "
                f"and its fast path is {named} — a sweep would report it "
                f"unprotected while a check sits there holding it")
            assert guard in SLOW, (
                f"{guard!r} is not in SLOW, so the broad stage would have "
                f"caught {module}.{name} anyway and this row proves nothing")
            held[f"{module}.{name}"] = guard
        # And the constants are still there to be guarded.
        have = {(p.stem, n) for p, n, _v in constants()}
        for module, name, _guard in MEASURED:
            assert (module, name) in have, (
                f"{module}.{name} is named here and the sweep cannot see it")
        return " · ".join(f"{k} by {v}" for k, v in held.items())
