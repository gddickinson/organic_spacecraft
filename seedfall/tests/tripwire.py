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

import ast
import os
import pathlib
import subprocess
import sys

#: Suites that are fast and do not need Qt. Enough coverage to catch a real
#: change; cheap enough to run a hundred times.
SUITES = ("sim combat flight crew mining research trade politics bloom time "
          "dormancy officials approach doctrine firing surveys anchorage "
          "traffic empire explore missions ground design orders assessment "
          "customs allegiance territory charts aftermath notes cargo freight "
          "workings burns bench works overtures seats founding attempts reach "
          "beginnings legacy grudges gunnery transit").split()

#: Constants that are deliberately structural rather than tuning — changing
#: them is a different kind of edit and the sweep only adds noise.
SKIP = {"MASK", "SAVE_VERSION", "KEEP", "MAX_BAND", "ARENA"}

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def constants(only: str = "") -> list:
    """Every module-level numeric constant, as (path, name, value)."""
    out = []
    for folder in ("data", "sim", "core"):
        for path in sorted((ROOT / "seedfall" / folder).glob("*.py")):
            if only and only not in path.stem:
                continue
            tree = ast.parse(path.read_text())
            for node in tree.body:
                if not isinstance(node, ast.Assign) or len(node.targets) != 1:
                    continue
                target = node.targets[0]
                if not isinstance(target, ast.Name) or not target.id.isupper():
                    continue
                if target.id in SKIP:
                    continue
                value = node.value
                if isinstance(value, ast.Constant) and \
                        isinstance(value.value, (int, float)) and \
                        not isinstance(value.value, bool):
                    out.append((path, target.id, value.value))
    return out


def variants(value):
    """Degenerate values worth trying, most disruptive first."""
    tries = []
    if value != 0:
        tries.append(0 if isinstance(value, int) else 0.0)
    tries.append(value * 2 if value else 1)
    if value:
        tries.append(value / 2 if isinstance(value, float) else max(1, value // 2))
    return tries


def rewrite(path: pathlib.Path, name: str, new) -> str:
    """Set a constant, returning the original text for restoring."""
    original = path.read_text()
    out, done = [], False
    for line in original.splitlines(keepends=True):
        stripped = line.lstrip()
        if not done and stripped.startswith(f"{name} ") and "=" in line:
            indent = line[:len(line) - len(stripped)]
            out.append(f"{indent}{name} = {new!r}\n")
            done = True
        else:
            out.append(line)
    if not done:
        return ""
    path.write_text("".join(out))
    return original


#: A clean run of the subset takes about ten seconds. Sixty is generous, and
#: bounded: a mutated constant can send the sim into a very slow path — an
#: unreachable loop bound, a zero step — and a generous timeout turns one bad
#: value into a quarter of an hour of nothing.
LIMIT = 60


#: Suites named after a module, so a constant is tried against its own
#: neighbourhood first. Two stages, because the broad set costs thirty-six
#: seconds and most constants are caught by their own suite in two: run the
#: cheap one, and only pay for the wide one on the survivors. A single-stage
#: sweep of everything is three hours and finds the same answer.
KIN = {
    "dormancy": ("dormancy",), "lineages": ("time",), "crossings": ("time",),
    "officials": ("officials",), "approaches": ("approach",),
    "approach": ("approach",), "surveys": ("surveys",), "survey": ("surveys",),
    "traffic": ("traffic",), "anchorage": ("anchorage",),
    "doctrine": ("doctrine",), "firing": ("firing", "gunnery"),
    "tactical": ("gunnery", "combat"), "combat": ("combat", "gunnery"),
    "damage": ("combat", "gunnery"), "contraband": ("customs",),
    "customs": ("customs",), "diplomacy": ("politics",),
    "grudge": ("grudges",), "colonies": ("works", "founding"),
    "works": ("works",), "mining": ("mining",), "research": ("bench",),
    "inquiry": ("bench",), "flight": ("flight", "burns"),
    "contracts": ("missions", "cargo"), "chains": ("missions",),
    "expedition": ("ground",), "weather": ("ground",),
    "territory": ("territory",), "allegiance": ("allegiance",),
    "charts": ("charts",), "notes": ("notes",), "freight": ("freight",),
    "market": ("trade",), "economy": ("trade",), "commodities": ("trade",),
    "loyalty": ("crew",), "convictions": ("crew",), "crew": ("crew",),
    "lifespan": ("time",), "upkeep": ("time",), "clock": ("time",),
    "stations": ("gunnery",), "consorts": ("combat",), "bloom": ("bloom",),
    "threat": ("bloom",), "ventures": ("politics",), "memory": ("voices",),
    "intel": ("explore",), "transit": ("transit",), "shipyard": ("design",),
}


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
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        [sys.executable, "-B", "-m", "seedfall.tests", *suites],
        capture_output=True, text=True, cwd=ROOT, timeout=LIMIT, env=env)
    return done.returncode == 0


def suite_passes(module: str = "") -> bool:
    """True if nothing noticed. A hang counts as noticed — loudly."""
    near = KIN.get(module)
    if near and _run(near) is False:
        return False
    return _run(SUITES)


def main(argv: list) -> int:
    """Sweep, restoring the tree whatever happens.

    A killed sweep used to leave the constant it was holding mutated — I
    stopped one mid-trial and left `QUIET_DAYS = 0` sitting in the working
    tree. A tool that edits source has to put it back on the way out, not
    only on the happy path.
    """
    only = argv[0] if argv else ""
    found = constants(only)
    # Any bytecode left over from an earlier run may have been compiled from
    # a mutated source. Start clean.
    for cache in ROOT.rglob("__pycache__"):
        for stale in cache.glob("*.pyc"):
            stale.unlink(missing_ok=True)

    print(f"sweeping {len(found)} constants "
          f"({'module ' + only if only else 'every module'})\n", flush=True)

    import atexit
    import signal
    holding: dict = {}

    def restore(*_args):
        for where, text in list(holding.items()):
            pathlib.Path(where).write_text(text)
        holding.clear()

    atexit.register(restore)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_a: (restore(), sys.exit(130)))

    survived = []
    for index, (path, name, value) in enumerate(found, 1):
        print(f".. [{index:3d}/{len(found)}] {path.stem}.{name}", flush=True)
        noticed = False

        def try_value(candidate, suites) -> bool:
            """Set the constant, run those suites, always put it back."""
            original = rewrite(path, name, candidate)
            if not original:
                return False
            holding[str(path)] = original
            try:
                return not _run(suites)
            except subprocess.TimeoutExpired:
                return True             # a hang is a very loud notice
            finally:
                path.write_text(original)
                holding.pop(str(path), None)

        # Stage one: every variant against the constant's own neighbourhood.
        # Two seconds a go, and it catches most of them.
        near = KIN.get(path.stem)
        if near:
            for candidate in variants(value):
                if try_value(candidate, near):
                    noticed = True
                    break

        # Stage two, only for survivors: the wide set, and only the single
        # most disruptive value. Thirty-six seconds is worth paying once to
        # confirm a finding; it is not worth paying three times to reconfirm.
        if not noticed:
            noticed = try_value(variants(value)[0], SUITES)

        flag = "  " if noticed else "??"
        print(f"{flag} [{index:3d}/{len(found)}] {path.stem}.{name} = {value!r}"
              + ("" if noticed else "   — nothing noticed"), flush=True)
        if not noticed:
            survived.append((path.stem, name, value))

    print(f"\n{len(survived)} of {len(found)} constants are unprotected:")
    for module, name, value in survived:
        print(f"    {module}.{name} = {value!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
