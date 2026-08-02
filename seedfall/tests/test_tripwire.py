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

from .harness import Suite
from .tripwire import KIN, SLOW, constants


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
