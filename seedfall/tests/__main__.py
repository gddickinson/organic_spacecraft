"""Run the SEEDFALL test suites: ``python -m seedfall.tests [suite …] [-j N]``.

    python -m seedfall.tests              # every suite, one process
    python -m seedfall.tests -j 8         # every suite, eight processes
    python -m seedfall.tests sim combat   # just these
    python -m seedfall.tests --list       # what there is, and how long each took
    python -m seedfall.tests --fast       # the cheap ones: what CI runs on a push
    python -m seedfall.tests --require-qt # CI: a suite skipped for Qt fails
    python -m seedfall.tests --coverage   # per-suite coverage, and who touches what

An unknown suite name is an error (exit 2), not a silent green run of
nothing, and a flag the runner does not know is refused rather than dropped —
`--help` used to start all 199 suites.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import time

from .runner import _load_times, child_main, run_here, run_parallel, summary
from .suites import ALL_SUITES, SUITES, SUITES_BY_KEY

__all__ = ["ALL_SUITES", "SUITES", "main"]


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m seedfall.tests",
        description="Run the SEEDFALL check suites.")
    ap.add_argument("suites", nargs="*", help="suite keys (default: all)")
    ap.add_argument("-j", "--jobs", type=int, default=1,
                    help="run suites in N processes (0 = one per core)")
    ap.add_argument("--list", action="store_true",
                    help="list the suites and their last recorded time")
    ap.add_argument("--timeout", type=float, default=1200.0,
                    help="seconds before a parallel suite is called hung")
    ap.add_argument("--slowest", type=int, default=10,
                    help="how many of the slowest suites to name at the end")
    ap.add_argument("--fast", action="store_true",
                    help="only the suites measured under 1.5 s alone (the "
                         "tripwire's broad stage): what CI runs on a push")
    ap.add_argument("--require-qt", action="store_true",
                    help="fail, rather than skip, anything that needs PyQt6")
    ap.add_argument("--coverage", nargs="?", const="", metavar="DIR",
                    help="record coverage per suite (needs `coverage`); "
                         "writes the combined data and a module→suite map "
                         "to DIR (default: a scratch directory)")
    ap.add_argument("--child", help=argparse.SUPPRESS)
    return ap


def main(argv: list[str] | None = None) -> int:
    """Run the wanted suites in the order `suites.SUITES` declares them."""
    args = _parser().parse_args(argv if argv is not None else sys.argv[1:])
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if args.child:
        return child_main(args.child, args.require_qt)
    if args.require_qt:
        from .harness import qt_missing
        if qt_missing():
            print("--require-qt: PyQt6 cannot be imported here, so every "
                  "interface suite would be skipped", file=sys.stderr)
            return 1
    if args.list:
        times = _load_times()
        for s in SUITES:
            t = times.get(s.key)
            print(f"  {s.key:16s} {s.label:44s} "
                  f"{'qt ' if s.optional else '   '}"
                  f"{f'{t:6.1f} s' if t is not None else ''}")
        return 0
    unknown = [k for k in args.suites if k not in SUITES_BY_KEY]
    if unknown:
        for k in unknown:
            near = difflib.get_close_matches(k, ALL_SUITES, n=3)
            hint = f" — did you mean {', '.join(near)}?" if near else ""
            print(f"no suite called {k!r}{hint}", file=sys.stderr)
        return 2
    wanted = set(args.suites or ALL_SUITES)
    if args.fast:
        # One list of what is cheap, not two: `tripwire.SLOW` is measured and
        # kept honest by the `harness` suite, so a push runs what it spares.
        from .tripwire import SUITES as CHEAP
        wanted &= set(CHEAP)
    specs = [s for s in SUITES if s.key in wanted]
    t0 = time.perf_counter()
    jobs = args.jobs if args.jobs > 0 else (os.cpu_count() or 2)
    cover = None
    if args.coverage is not None:
        from .coverage_map import Recorder
        cover = Recorder.start(args.coverage)
        if cover is None:
            return 2
    if cover is not None or (jobs > 1 and len(specs) > 1):
        # Coverage per suite needs a process per suite, even at -j 1.
        outcomes = run_parallel(specs, jobs, args.timeout, args.require_qt,
                                cover)
    else:
        outcomes = []
        for spec in specs:
            outcomes.append(run_here(spec, args.require_qt))
            _tidy()
    summary(outcomes, time.perf_counter() - t0, args.slowest)
    if cover is not None:
        cover.finish([o.key for o in outcomes])
    return 0 if all(o.good for o in outcomes) else 1


def _tidy() -> None:
    """Put down whatever a suite left standing, here rather than by luck.

    **A window outliving the suite that made it is how a run dies without
    failing.** The `chronicle` suite paints every screen a few hundred times
    over a decade, and its windows were still alive when Python got round to
    collecting them — somewhere in the middle of a *later* suite. Qt says
    "Cannot destroy paint device that is being painted" and the process goes
    down with exit 139, no traceback and nothing failing.

    So the widgets are put down at a suite boundary: closed, `deleteLater`
    honoured by draining DeferredDelete events (which `processEvents` alone
    does not deliver), and only then is the collector asked to run.
    """
    import gc
    try:
        from PyQt6.QtCore import QEvent
        from PyQt6.QtWidgets import QApplication
    except ImportError:
        gc.collect()
        return
    app = QApplication.instance()
    if app is None:
        gc.collect()
        return
    for widget in list(app.topLevelWidgets()):
        try:
            widget.close()
            widget.deleteLater()
        except RuntimeError:
            pass            # already gone, which is the outcome wanted
    for _pass in range(3):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()
    app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
