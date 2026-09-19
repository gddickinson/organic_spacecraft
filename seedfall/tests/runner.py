"""Running suites — in this process, or one process per suite, in parallel.

**Why a process per suite.** A full run in one process took 17 minutes on
one core of ten, and a segfault anywhere in it (the suite has recorded exit
134 and 139 more than once) took every later suite down with it and named
none of them. A child per suite runs on every core and pins a crash to the
suite that crashed.

**Why the result line.** A child reports through its exit code *and* a
last line of JSON, because the exit code alone cannot say how many checks
ran — and a suite that ran nothing must not read as green.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path

from .harness import Suite, needs_qt

RESULT = "@@SEEDFALL-RESULT "
#: Where the last run's per-suite timings are kept, so the next parallel run
#: can start the longest suites first. A scratch file, never committed.
TIMINGS = Path(tempfile.gettempdir()) / "seedfall-suite-times.json"


@dataclass
class Outcome:
    key: str
    label: str
    status: str            # ok · fail · skip · crash · error
    passed: int = 0
    failed: int = 0
    seconds: float = 0.0
    output: str = ""
    skipped: int = 0       # checks skipped for want of PyQt6

    @property
    def good(self) -> bool:
        return self.status in ("ok", "skip")


def run_here(spec, require_qt: bool = False) -> Outcome:
    """Run one suite in this process and print its report as it goes."""
    out = _run_here(spec)
    if require_qt and (out.status == "skip" or out.skipped):
        # CI has Qt. A skip there is an interface suite that never ran and a
        # green line that says nothing about it, so it is refused.
        print(f"  FAIL --require-qt: {spec.label} skipped "
              f"{out.skipped or 'all its'} check(s) for want of PyQt6\n",
              flush=True)
        out.status, out.failed = "fail", out.failed + max(out.skipped, 1)
    return out


def _run_here(spec) -> Outcome:
    t0 = time.perf_counter()
    try:
        module = import_module(f"seedfall.tests.{spec.module}")
    except ImportError as err:
        if not needs_qt(err):
            # Optional or not, an import that fails for any reason but a
            # missing PyQt6 is a broken module, not a missing dependency.
            print(f"── {spec.label} ───\n  ERROR importing: {err}\n", flush=True)
            return Outcome(spec.key, spec.label, "error",
                           seconds=time.perf_counter() - t0)
        # PyQt is not installed. Say so and carry on rather than failing a
        # run that has nothing to do with the interface.
        print(f"── {spec.label} ───\n  skipped: {err}\n", flush=True)
        return Outcome(spec.key, spec.label, "skip")
    suite = Suite(spec.label)
    try:
        ran = module.run(suite)
    except Exception as err:                                  # noqa: BLE001
        if needs_qt(err):
            print(f"── {spec.label} ───\n  skipped: {err}\n", flush=True)
            return Outcome(spec.key, spec.label, "skip",
                           seconds=time.perf_counter() - t0)
        # A suite whose *setup* raises used to end the whole run, taking
        # every later suite with it. It is one failure, and says where.
        tail = traceback.format_exc().strip().splitlines()[-6:]
        suite.failed.append("  FAIL (suite raised outside a check)\n       "
                            f"{err!r}\n       " + "\n       ".join(tail))
        ran = True
    seconds = time.perf_counter() - t0
    if spec.optional and not ran and not suite.failed:
        return Outcome(spec.key, spec.label, "skip", seconds=seconds)
    ok = suite.report()
    sys.stdout.flush()
    counts = dict(passed=len(suite.passed), failed=len(suite.failed),
                  seconds=seconds, skipped=len(suite.skipped))
    if ok and not suite.passed:
        if suite.skipped:
            return Outcome(spec.key, spec.label, "skip", **counts)
        # **A suite that ran no checks is not a pass.** It is the shape a
        # broken import or a loop over nothing takes.
        print(f"  ERROR: {spec.label} ran no checks\n", flush=True)
        return Outcome(spec.key, spec.label, "error", seconds=seconds)
    return Outcome(spec.key, spec.label, "ok" if ok else "fail", **counts)


def child_main(key: str, require_qt: bool = False) -> int:
    """`--child KEY`: run one suite and end with a machine-readable line."""
    from .suites import SUITES_BY_KEY
    from .__main__ import _tidy
    spec = SUITES_BY_KEY[key]
    out = run_here(spec, require_qt)
    _tidy()
    print(RESULT + json.dumps({"status": out.status, "passed": out.passed,
                               "failed": out.failed, "skipped": out.skipped,
                               "seconds": round(out.seconds, 2)}), flush=True)
    return 0 if out.good else 1


def _child(spec, env: dict, timeout: float, flags: tuple = (),
           wrap: tuple = ()) -> Outcome:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, *wrap, "-m", "seedfall.tests", "--child",
             spec.key, *flags],
            capture_output=True, text=True, env=env, timeout=timeout,
            cwd=str(Path(__file__).resolve().parents[2]))
    except subprocess.TimeoutExpired as err:
        text = (err.stdout or "") if isinstance(err.stdout, str) else ""
        return Outcome(spec.key, spec.label, "crash",
                       seconds=time.perf_counter() - t0,
                       output=text + f"\n  CRASH: timed out after {timeout:.0f} s\n")
    seconds = time.perf_counter() - t0
    body, result = [], None
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT):
            result = json.loads(line[len(RESULT):])
        else:
            body.append(line)
    text = "\n".join(body).rstrip() + "\n"
    if result is None:
        tail = "\n".join(proc.stderr.strip().splitlines()[-12:])
        return Outcome(spec.key, spec.label, "crash", seconds=seconds,
                       output=f"── {spec.label} ───\n{text}\n  CRASH: exit "
                              f"{proc.returncode}, no result line\n{tail}\n")
    return Outcome(spec.key, spec.label, result["status"], result["passed"],
                   result["failed"], seconds, text, result.get("skipped", 0))


def _load_times() -> dict:
    try:
        return json.loads(TIMINGS.read_text())
    except (OSError, ValueError):
        return {}


def _save_times(outcomes: list[Outcome]) -> None:
    times = _load_times()
    times.update({o.key: round(o.seconds, 2) for o in outcomes
                  if o.status in ("ok", "fail")})
    try:
        TIMINGS.write_text(json.dumps(times, indent=0, sort_keys=True))
    except OSError:
        pass


def child_env() -> dict:
    """The environment a suite's own process runs in."""
    from ..core.save import SAVE_ENV
    env = dict(os.environ)
    # The parent's own save path was set on import; each child must choose
    # its own (per pid) or they would all write one file.
    env.pop(SAVE_ENV, None)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["PYTHONUNBUFFERED"] = "1"
    return env


def run_child(spec, timeout: float = 1200.0, require_qt: bool = False
              ) -> Outcome:
    """One suite in a process of its own, as `-j` runs it. For the pytest
    shim, which wants the isolation without the pool."""
    return _child(spec, child_env(), timeout,
                  ("--require-qt",) if require_qt else ())


def run_parallel(specs: list, jobs: int, timeout: float,
                 require_qt: bool = False, cover=None) -> list[Outcome]:
    """Run each suite in its own process, `jobs` at a time, longest first.

    `cover` (a `coverage_map.Recorder`) wraps each child in `coverage run`
    with a data file of its own, which is what makes a module→suite map
    possible: one combined file cannot say which suite touched what.
    """
    env = child_env()
    times = _load_times()
    order = sorted(specs, key=lambda s: -times.get(s.key, 30.0))
    outcomes: list[Outcome] = []
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        flags = ("--require-qt",) if require_qt else ()
        futures = [pool.submit(_child, s, env, timeout, flags,
                               cover.wrap(s.key) if cover else ())
                   for s in order]
        for fut in as_completed(futures):
            out = fut.result()
            print(out.output, end="", flush=True)
            outcomes.append(out)
    if cover is None:
        # A suite under `coverage run` takes about twice as long; its time
        # would reorder the next plain run and misstate `--list`.
        _save_times(outcomes)
    rank = {s.key: i for i, s in enumerate(specs)}
    return sorted(outcomes, key=lambda o: rank[o.key])


def summary(outcomes: list[Outcome], wall: float, slowest: int = 10) -> None:
    """The totals a run never printed: counts, time, and what went wrong."""
    checks = sum(o.passed + o.failed for o in outcomes)
    failed = [o for o in outcomes if not o.good]
    skipped = [o for o in outcomes if o.status == "skip"]
    cpu = sum(o.seconds for o in outcomes)
    print("═" * 60)
    unrun = sum(o.skipped for o in outcomes)
    print(f"  {len(outcomes)} suites · {checks} checks · "
          f"{sum(o.failed for o in outcomes)} failed checks · "
          f"{len(skipped)} skipped"
          + (f" (+{unrun} checks skipped for want of PyQt6)" if unrun else "")
          + f" · wall {wall:.0f} s · suite time {cpu:.0f} s")
    if slowest:
        print("  slowest: " + ", ".join(
            f"{o.key} {o.seconds:.0f}s"
            for o in sorted(outcomes, key=lambda o: -o.seconds)[:slowest]))
    if failed:
        print("  NOT GREEN: " + ", ".join(f"{o.key} ({o.status})" for o in failed))
    else:
        print("  all green")
    print("═" * 60, flush=True)
