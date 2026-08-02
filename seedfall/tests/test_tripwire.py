"""The sweep that guards the constants had nothing guarding it.

`tests/tripwire.py` decides which constants in this game are protected. A
dozen check files cite its verdicts in their comments, and several checks exist
*because* it reported something unpinned. Nothing has ever checked the tool
itself, and its `KIN` table — the fast path, one entry per module, saying which
suites are worth running for that module's constants — is hand-kept.

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
from .suites import ALL_SUITES
from .tripwire import KIN, SLOW, constants

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
]


def _modules() -> set:
    out = set()
    for folder in ("data", "sim", "core", "world", "ui"):
        for path in (ROOT / folder).glob("*.py"):
            out.add(path.stem)
    return out


def run(suite: Suite) -> None:
    check = suite.check

    @check("every fast path names suites that exist")
    def _():
        # A misspelt suite key does not raise — the sweep runs the ones it
        # recognises and the entry silently protects less than it says. There
        # is no other way to notice.
        real = set(ALL_SUITES)
        wrong = {mod: [s for s in named if s not in real]
                 for mod, named in KIN.items()}
        wrong = {m: v for m, v in wrong.items() if v}
        assert not wrong, f"fast paths naming no such suite: {wrong}"
        return f"{len(KIN)} fast paths, {sum(len(v) for v in KIN.values())} " \
               f"suite names, all real"

    @check("every fast path names a module that exists")
    def _():
        # Measured when this went in: `declared` had an entry and there is no
        # `declared` module anywhere in the package — a row that could never
        # be consulted, carried along as if it were doing something.
        mods = _modules()
        ghosts = sorted(m for m in KIN if m not in mods)
        assert not ghosts, (
            f"fast paths for modules that do not exist: {ghosts}")
        return f"{len(KIN)} fast paths, every one a real module"

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
