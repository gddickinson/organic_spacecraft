"""Which tuning constants are actually protected by a check, and which are not.

Three cycles running I have written a check that reads the very constant whose
effect it claims to test — `after_cap == before_cap - CAP_PER_LEAN`,
`total - room >= round(total * MIN_WATCH)` — and then watched it pass with
that constant set to zero. Each time I caught it by hand, by trying to break
the thing on purpose. Each time I said I would watch for it.

Relying on remembering is not a method. This is: **change a constant and see
whether anything notices.**

A constant that can be doubled, halved or zeroed without a single check
failing is in one of three states, and all three are worth knowing about:

- **Dead.** Nothing reads it. The game has had several of these — a colony's
  sensor bonus that no code path consumed, a `demand` mapping that did not
  exist on the object it was read from.
- **Tautologically checked.** Something reads it, and so does the assertion,
  so they move together and the check cannot fail. My habit.
- **Genuinely unpinned.** Real, load-bearing, and nothing holds it in place —
  so the next person to tune it finds out from a player.

This is slow — a suite run per constant — so it is a tool rather than a check.
Run it directly:

    python3 -m seedfall.tests.tripwire            # everything
    python3 -m seedfall.tests.tripwire dormancy   # one module

It reports only what survives, because that is the list worth acting on.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

#: Suites the sweep does not run in its broad stage, because they cost too
#: much to run once per constant.
#:
#: **Measured, not judged.** All 155 suites timed: 761 s in total and wildly
#: lopsided — `politics` alone is 145 s (19%), `byhand` 52, `provisional` 34.
#: Excluding everything over 1.5 s leaves **71 suites in 47 seconds**, inside
#: `LIMIT`, where the whole set is nearly thirteen minutes.
#:
#: That number is the point. `completes(SUITES)` calibrates whether the broad
#: stage finishes clean; while it did not, the stage abstained and every
#: constant its own fast path missed went unguarded — 9 survivors in the
#: first 18 swept. The stage votes again now.
#:
#: The old list was hand-kept and calibrated before `core/clock.MAX_STEP`
#: became 1. None of `politics`, `byhand`, `provisional` or `orders` was in it;
#: all four had grown past half a minute. A hand-kept list of what is expensive
#: goes stale the moment the thing it describes changes speed, which is why
#: these figures are written down beside it.
#:
#: The entries here for needing a window or being a whole chronicle are kept:
#: `ui`, `bridge`, `instruments`, `chronicle`, `play` and the rest. `tutorial`
#: was once excluded for building a window and lost its fast path over it — it
#: sets the offscreen platform itself, so being expensive is the only reason
#: to skip a suite, and at 5.1 s it now is one.
SLOW = {
    "aftermath", "anchorage", "approaching", "balance",
    "bench", "bloom", "bridge", "burns",
    "byhand", "cameras", "cargo", "charting",
    "chronicle", "climbs", "conn", "connwindow",
    "counter", "courting", "customs", "declared",
    "dig", "docking", "dormancy", "drawbudget",
    "efficacy", "empire", "evidence", "exchequer",
    "fence", "fleets", "fog", "freight",
    "gates", "geography", "grants", "grudges",
    "hands", "helm", "industry", "instruments",
    "landing", "layers", "levy", "life3d",
    "lopsided", "manual", "mining", "notes",
    "officials", "options", "orbits", "orders",
    "orrery", "parley", "picture", "pilot",
    "pilotscreen", "firecontrol", "bridge2", "sights",
    "plans", "play", "politics", "postings",
    "programmes", "provisional", "public", "reachable",
    "readiness", "research", "resume", "reticle",
    "revived", "robots", "robots3d", "salvage",
    "seams", "seatwork", "settlement", "showflying",
    "sim", "stranded", "territory", "thermal",
    "thermal_doors", "thrusters", "ticks", "time",
    "trade", "traffic", "transit", "tuning",
    "turnplan", "tutorial", "ui", "ventures",
    "verbs", "voices", "war", "watches",
    "wayhome", "weave", "wharfage", "works3d",
    "xeno",
}


def _suites() -> list:
    from .__main__ import ALL_SUITES
    return [name for name in ALL_SUITES if name not in SLOW]


SUITES = _suites()

# **How to find a constant and how to change it lives in `sweepkit`**, split
# out when this file hit five hundred lines exactly. This file is the other
# half: which suites speak for which module, and what a sweep concluded.
from .sweepkit import ROOT, constants, put, rewrite, variants  # noqa: E402


#: A clean run of the subset takes about ten seconds. Sixty is generous, and
#: bounded: a mutated constant can send the sim into a very slow path — an
#: unreachable loop bound, a zero step — and a generous timeout turns one bad
#: value into a quarter of an hour of nothing.
LIMIT = 60


# **Which suite speaks for which module lives in `tripwire_kin`**,
# split out when this file hit the ceiling for the fourth time. It is
# a table and this is a tool; only the table grows with the game.
from .tripwire_kin import KIN  # noqa: E402



def _run(suites) -> bool:
    """Run these suites in a child that never writes or reads stale bytecode.

    Without `PYTHONDONTWRITEBYTECODE` this tool silently poisons itself. It
    rewrites a constant, Python compiles a `.pyc` from the mutated source, the
    constant is restored — and the next process is still served the cached
    bytecode, because the restore does not always move the mtime far enough to
    invalidate it. I found this the way it deserved to be found: a check
    crashed with `PER_LOSS` reading 0.0 at runtime and 9.0 on disk.

    Every result from a sweep without this is worthless in both directions —
    a mutation that outlived its restore, or a restore that never took.
    """
    # A child gets its **own** save file. `tests/__init__` sets `SEEDFALL_SAVE`
    # per pid and `setdefault` means a child would otherwise inherit the
    # parent's and write over the run that spawned it — harmless while this was
    # only ever a command-line tool, and not harmless now that a check calls
    # `completes` during a suite run.
    from ..core.save import SAVE_ENV
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop(SAVE_ENV, None)
    done = subprocess.run(
        [sys.executable, "-B", "-m", "seedfall.tests", *suites],
        capture_output=True, text=True, cwd=ROOT, timeout=LIMIT, env=env)
    return done.returncode == 0


_CLEAN: dict = {}


def completes(suites) -> bool:
    """Does this set finish inside `LIMIT` with **nothing** mutated?

    **A hang only means something if the same run does not hang anyway**, and
    for the broad set it does. Measured: `SUITES` is 155 suites and takes about
    25 minutes since `core/clock.MAX_STEP` became 1 — the note on `KIN` saying
    "the broad set costs thirty-six seconds" was written before that. So the
    second stage has been timing out on every constant, mutated or not, since
    #116 landed.

    That would be merely useless if a timeout were treated as no information.
    It was treated as *proof*: "a hang is a very loud notice". So every
    constant its own suite failed to catch has been reported protected on the
    strength of a stopwatch. Calibrated once per set and cached, because the
    answer cannot change inside a run.
    """
    key = tuple(suites)
    if key not in _CLEAN:
        try:
            _run(suites)
            _CLEAN[key] = True
        except subprocess.TimeoutExpired:
            _CLEAN[key] = False
    return _CLEAN[key]


def noticed(suites) -> bool:
    """Did any of these object to what is on disk right now?

    **The one door for that question**, and there were two: `suite_passes` and
    the `try_value` closure inside `main` each had their own `try/except`
    around `_run`, and only one of them could be reached by a check. A
    mutation restoring the old "a hang is a very loud notice" in the other
    left every check green.
    """
    try:
        return not _run(suites)
    except subprocess.TimeoutExpired:
        return completes(suites)


def suite_passes(module: str = "") -> bool:
    """True if nothing noticed.

    A hang counts as noticed only where `completes` says the set finishes when
    unmutated — otherwise the stopwatch is measuring the suite, not the
    constant, and a stage that cannot finish clean does not get a vote.
    """
    near = KIN.get(module)
    if near and noticed(near):
        return False
    if not completes(SUITES):
        return True                     # the broad stage abstains
    return not noticed(SUITES)


def main(argv: list) -> int:
    """Sweep, restoring the tree whatever happens.

    A killed sweep used to leave the constant it was holding mutated — I
    stopped one mid-trial and left `QUIET_DAYS = 0` sitting in the working
    tree. A tool that edits source has to put it back on the way out, not
    only on the happy path.
    """
    # **`--fast` skips stage two, and the measurement says why.** The two
    # stages cost wildly different amounts now that the fast paths are right:
    # `piracy`'s ten constants were all caught by their own suites and the
    # module swept in **20 seconds**. `exchequer`'s thirteen were still going
    # after **thirty minutes**, because every constant its own suites miss
    # pays for the broad set — 74 suites — and so does the one calibration
    # run before them. So both stages over everything is an overnight job,
    # and stage one alone is about a quarter of an hour.
    # The shortlist that produces is not a verdict — it is *not caught by the
    # suite that knows this module*, which is the right question to ask 439
    # times and the wrong one to stop at. Confirm a shortlist with a full run
    # of those constants alone.
    fast = "--fast" in argv
    argv = [a for a in argv if a != "--fast"]
    only = argv[0] if argv else ""
    found = constants(only)
    # Any bytecode left over from an earlier run may have been compiled from
    # a mutated source. Start clean.
    for cache in ROOT.rglob("__pycache__"):
        for stale in cache.glob("*.pyc"):
            stale.unlink(missing_ok=True)

    print(f"sweeping {len(found)} constants "
          f"({'module ' + only if only else 'every module'})"
          + ("  — fast path only, so a survivor here is a shortlist entry "
             "and not a verdict" if fast else "") + "\n", flush=True)

    import atexit
    import signal
    holding: dict = {}

    def restore(*_args):
        for where, text in list(holding.items()):
            put(pathlib.Path(where), text)
        holding.clear()

    atexit.register(restore)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_a: (restore(), sys.exit(130)))

    survived, distant = [], []
    for index, (path, name, value) in enumerate(found, 1):
        print(f".. [{index:3d}/{len(found)}] {path.stem}.{name}", flush=True)
        # **Not `noticed`.** A local of that name shadows the module-level
        # `noticed()` for the whole of `main`, including the closure below —
        # so `try_value` called `False(suites)` and the sweep died on its
        # first constant with "'bool' object is not callable". It had been
        # dead at HEAD, which is why #134's re-run never started.
        caught = False

        def try_value(candidate, suites) -> bool:
            """Set the constant, run those suites, always put it back."""
            # **Snapshot first, and restore from the snapshot.** The undo
            # used to be `rewrite`'s own return value, which means the sweep
            # cleaned up through the very thing it would be blamed for: break
            # `rewrite` and you break the restore with it, and the run leaves
            # mutated constants sitting on disk. Found by mutating `rewrite`
            # on purpose and watching `data/gates.py` come out of it holding
            # `TOLL_REFUSED_BELOW = 0`.
            before = path.read_text()
            original = rewrite(path, name, candidate)
            if not original:
                return False
            holding[str(path)] = before
            try:
                # Through `noticed`, the one door for "did anything object".
                # This carried its own copy of the try/except, and no check
                # could reach it — so a mutation restoring "a hang is a very
                # loud notice" here left the whole suite green.
                return noticed(suites)
            finally:
                put(path, before)
                holding.pop(str(path), None)

        # Stage one: every variant against the constant's own neighbourhood.
        # Two seconds a go, and it catches most of them.
        # **One suite at a time, stopping at the first objection.** The fast
        # path used to hand the whole tuple to a single run, so a constant
        # paid for every suite its module names even when the first of them
        # answered. Measured on `exchequer`, whose fast path is
        # `("exchequer", "politics")`:
        #
        #     exchequer            3.6 s
        #     politics           145.4 s
        #     both together      148.0 s
        #
        # `politics` is the most expensive suite in the project — 19% of a
        # whole run — and every one of `exchequer`'s thirteen constants was
        # paying 148 s a variant to ask a question `exchequer` answers in
        # under four. The set consulted is unchanged and so is every verdict;
        # only the order and the early exit are new. Entries are written with
        # the module's own suite first, which is both the cheapest and the
        # likeliest to object.
        near = KIN.get(path.stem)
        caught_by = ""
        if near:
            for candidate in variants(value):
                for one in near:
                    if try_value(candidate, (one,)):
                        caught, caught_by = True, one
                        break
                if caught:
                    break

        # Stage two, only for survivors: the wide set, and only the single
        # most disruptive value. Thirty-six seconds is worth paying once to
        # confirm a finding; it is not worth paying three times to reconfirm.
        if not caught and not fast:
            caught = try_value(variants(value)[0], SUITES)
            if caught:
                caught_by = "the wide set only"

        flag = "  " if caught else "??"
        print(f"{flag} [{index:3d}/{len(found)}] {path.stem}.{name} = {value!r}"
              + (f"   — {caught_by}" if caught else "   — nothing noticed"),
              flush=True)
        if not caught:
            survived.append((path.stem, name, value))
        elif not near or caught_by == "the wide set only":
            # Protected, but by nothing that names its subject. Worth knowing:
            # it is held up by a suite that happened to walk past, which is a
            # thinner thread than a check written for it.
            distant.append((path.stem, name, value))

    # **The word matters.** "Unprotected" is a verdict and the fast stage
    # cannot reach one: all it knows is that the suite which names the module
    # did not object. Saying more than that is how a pinned constant ends up
    # on a survivor list, which is the fault this whole apparatus was built
    # after (`bloom.HEART_HP`, reported a survivor while `test_play` held it).
    print(f"\n{len(survived)} of {len(found)} constants "
          + ("were not caught by their own suites — a shortlist to confirm "
             "with a full run:" if fast else "are unprotected:"))
    for module, name, value in survived:
        print(f"    {module}.{name} = {value!r}")
    if distant:
        print(f"\n{len(distant)} are protected only by a suite that does not "
              "name their subject:")
        for module, name, value in distant:
            print(f"    {module}.{name} = {value!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
