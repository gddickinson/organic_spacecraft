"""Run the SEEDFALL test suites: ``python -m seedfall.tests [sim|ui|…]``."""

from __future__ import annotations

import sys

from .harness import Suite


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    wanted = [a for a in argv if not a.startswith("-")] or ["sim", "xeno", "play", "combat", "flight", "empire", "crew",
                                       "missions", "explore", "mining", "research", "trade",
                                       "ground", "politics", "design", "orders",
                                       "assessment", "balance", "bloom", "reachable",
                                       "efficacy", "transit", "customs", "allegiance", "territory", "charts", "aftermath", "notes", "layers", "cargo", "freight", "workings", "dig",
                                       "resume", "verbs", "ui"]
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

    if "reachable" in wanted:
        from . import test_reachable
        suite = Suite("reachable")
        test_reachable.run(suite)
        ok &= suite.report()

    if "efficacy" in wanted:
        from . import test_efficacy
        suite = Suite("efficacy")
        test_efficacy.run(suite)
        ok &= suite.report()

    if "transit" in wanted:
        from . import test_transit
        suite = Suite("transit")
        test_transit.run(suite)
        ok &= suite.report()

    if "customs" in wanted:
        from . import test_customs
        suite = Suite("customs")
        test_customs.run(suite)
        ok &= suite.report()

    if "allegiance" in wanted:
        from . import test_allegiance
        suite = Suite("allegiance")
        test_allegiance.run(suite)
        ok &= suite.report()

    if "territory" in wanted:
        from . import test_territory
        suite = Suite("territory")
        test_territory.run(suite)
        ok &= suite.report()

    if "charts" in wanted:
        from . import test_charts
        suite = Suite("charts")
        test_charts.run(suite)
        ok &= suite.report()

    if "aftermath" in wanted:
        from . import test_aftermath
        suite = Suite("aftermath")
        test_aftermath.run(suite)
        ok &= suite.report()

    if "notes" in wanted:
        from . import test_notes
        suite = Suite("notes")
        test_notes.run(suite)
        ok &= suite.report()

    if "layers" in wanted:
        from . import test_layers
        suite = Suite("layers")
        test_layers.run(suite)
        ok &= suite.report()

    if "cargo" in wanted:
        from . import test_cargo
        suite = Suite("cargo")
        test_cargo.run(suite)
        ok &= suite.report()

    if "freight" in wanted:
        from . import test_freight
        suite = Suite("freight")
        test_freight.run(suite)
        ok &= suite.report()

    if "workings" in wanted:
        from . import test_workings
        suite = Suite("workings")
        test_workings.run(suite)
        ok &= suite.report()

    if "dig" in wanted:
        from . import test_dig
        suite = Suite("dig")
        test_dig.run(suite)
        ok &= suite.report()

    if "resume" in wanted:
        try:
            from . import test_resume
        except ImportError as err:
            print(f"── resume ───\n  skipped: {err}\n")
        else:
            suite = Suite("resume")
            if test_resume.run(suite):
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
