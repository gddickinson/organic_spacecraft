"""Run the SEEDFALL test suites: ``python -m seedfall.tests [sim|ui|…]``."""

from __future__ import annotations

import sys
from importlib import import_module

from .harness import Suite
from .suites import ALL_SUITES, SUITES

__all__ = ["ALL_SUITES", "SUITES", "main"]


def main(argv: list[str] | None = None) -> int:
    """Run the wanted suites in the order `suites.SUITES` declares them.

    This was seventy-eight copies of the same five-line block, one per suite,
    and it grew by one every cycle until the file went past five hundred
    lines. The order here is now the only order — the hand-kept `ALL_SUITES`
    beside it had already drifted from the dispatch at index 46.
    """
    argv = argv if argv is not None else sys.argv[1:]
    wanted = [a for a in argv if not a.startswith("-")] or list(ALL_SUITES)
    ok = True

    for spec in SUITES:
        if spec.key not in wanted:
            continue
        try:
            module = import_module(f"seedfall.tests.{spec.module}")
        except ImportError as err:
            if not spec.optional:
                raise
            # PyQt is not installed. Say so and carry on rather than failing
            # a run that has nothing to do with the interface.
            print(f"── {spec.label} ───\n  skipped: {err}\n")
            continue
        suite = Suite(spec.label)
        # An optional suite reports only if it says it actually ran.
        if spec.optional:
            if module.run(suite):
                ok &= suite.report()
        else:
            module.run(suite)
            ok &= suite.report()
        _tidy()
    return 0 if ok else 1


def _tidy() -> None:
    """Put down whatever a suite left standing, here rather than by luck.

    **A window outliving the suite that made it is how a run dies without
    failing.** Measured, repeatedly, and always in the same place: the
    `chronicle` suite paints every screen a few hundred times over a decade,
    and its windows were still alive when Python got round to collecting
    them — somewhere in the middle of a *later* suite. Qt says "Cannot
    destroy paint device that is being painted" and the process goes down
    with **exit 139, no traceback and nothing failing**, which is the worst
    shape a failure can take: a run that looks green by every measure except
    the one that counts.

    So the widgets are put down at a suite boundary, where nothing is
    painting, instead of at whatever moment the collector chooses. Closing
    is not enough — a closed widget is still a live paint device until it is
    deleted, so it is closed, `deleteLater` is honoured by draining the event
    loop, and only then is the collector asked to run.
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
    # **`deleteLater` is a promise, not a deletion.** It posts a
    # DeferredDelete event, and `processEvents` does not deliver that one —
    # it is held for the event loop proper, which a suite run never enters.
    # Without this the widgets stayed alive exactly as before and the tidy
    # was a comment: measured, the same crash two runs in three.
    for _pass in range(3):
        app.processEvents()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()
    app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
