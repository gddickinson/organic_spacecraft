"""Run the SEEDFALL test suites: ``python -m seedfall.tests [sim|ui|…]``."""

from __future__ import annotations

import sys

from .harness import Suite


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    wanted = [a for a in argv if not a.startswith("-")] or ["sim", "xeno", "play", "combat", "flight", "ui"]
    ok = True

    if "sim" in wanted:
        from . import test_sim
        suite = Suite("simulation")
        test_sim.run(suite)
        ok &= suite.report()

    if "xeno" in wanted:
        from . import test_xeno
        suite = Suite("xenotech")
        test_xeno.run(suite)
        ok &= suite.report()

    if "play" in wanted:
        from . import test_play
        suite = Suite("playability")
        test_play.run(suite)
        ok &= suite.report()

    if "combat" in wanted:
        from . import test_combat
        suite = Suite("tactical")
        test_combat.run(suite)
        ok &= suite.report()

    if "flight" in wanted:
        from . import test_flight
        suite = Suite("flight")
        test_flight.run(suite)
        ok &= suite.report()

    if "ui" in wanted:
        try:
            from . import test_ui
        except ImportError as err:
            print(f"── interface ───\n  skipped: {err}\n")
        else:
            suite = Suite("interface")
            if test_ui.run(suite):
                ok &= suite.report()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
