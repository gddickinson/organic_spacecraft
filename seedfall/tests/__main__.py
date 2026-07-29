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
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
