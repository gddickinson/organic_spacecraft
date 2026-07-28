"""Run the SEEDFALL test suites: ``python -m seedfall.tests [sim|ui|…]``."""

from __future__ import annotations

import sys

from .harness import Suite


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    wanted = [a for a in argv if not a.startswith("-")] or ["sim", "xeno", "play", "combat", "flight", "empire", "crew",
                                       "missions", "explore", "mining", "research", "trade",
                                       "ground", "politics", "design", "orders",
                                       "assessment", "balance", "bloom", "verbs", "ui"]
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

    if "empire" in wanted:
        from . import test_empire
        suite = Suite("empire")
        test_empire.run(suite)
        ok &= suite.report()

    if "crew" in wanted:
        from . import test_crew
        suite = Suite("crew")
        test_crew.run(suite)
        ok &= suite.report()

    if "missions" in wanted:
        from . import test_missions
        suite = Suite("missions")
        test_missions.run(suite)
        ok &= suite.report()

    if "explore" in wanted:
        from . import test_explore
        suite = Suite("exploration")
        test_explore.run(suite)
        ok &= suite.report()

    if "mining" in wanted:
        from . import test_mining
        suite = Suite("mining")
        test_mining.run(suite)
        ok &= suite.report()

    if "research" in wanted:
        from . import test_research
        suite = Suite("research")
        test_research.run(suite)
        ok &= suite.report()

    if "trade" in wanted:
        from . import test_trade
        suite = Suite("trade")
        test_trade.run(suite)
        ok &= suite.report()

    if "ground" in wanted:
        from . import test_ground
        suite = Suite("ground")
        test_ground.run(suite)
        ok &= suite.report()

    if "politics" in wanted:
        from . import test_politics
        suite = Suite("politics")
        test_politics.run(suite)
        ok &= suite.report()

    if "design" in wanted:
        from . import test_design
        suite = Suite("design")
        test_design.run(suite)
        ok &= suite.report()

    if "orders" in wanted:
        from . import test_orders
        suite = Suite("orders")
        test_orders.run(suite)
        ok &= suite.report()

    if "assessment" in wanted:
        from . import test_assessment
        suite = Suite("assessment")
        test_assessment.run(suite)
        ok &= suite.report()

    if "balance" in wanted:
        from . import test_balance
        suite = Suite("balance")
        test_balance.run(suite)
        ok &= suite.report()

    if "bloom" in wanted:
        from . import test_bloom_arc
        suite = Suite("bloom")
        test_bloom_arc.run(suite)
        ok &= suite.report()

    if "verbs" in wanted:
        try:
            from . import test_verbs
        except ImportError as err:
            print(f"── verbs ───\n  skipped: {err}\n")
        else:
            suite = Suite("verbs")
            if test_verbs.run(suite):
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
