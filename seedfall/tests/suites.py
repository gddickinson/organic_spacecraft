"""Every suite in the harness, and the module that holds it.

`__main__.py` carried a five-line `if "name" in wanted:` block per suite, and
grew by one every time a cycle added a check file — past five hundred lines,
which is the point at which this project splits a file. The blocks were all
the same block, so they are a table now: adding a suite is one row.

`optional` marks the four that need PyQt. They are skipped with a note rather
than failing the run, so the suite is usable on a machine without it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuiteSpec:
    key: str          # what you type on the command line
    module: str       # the module under `seedfall.tests`
    label: str        # what the report calls it
    optional: bool = False   # skip, with a note, if PyQt is missing


SUITES: list[SuiteSpec] = [
    SuiteSpec("sim", "test_sim", "simulation"),
    SuiteSpec("xeno", "test_xeno", "xenotech"),
    SuiteSpec("play", "test_play", "playability"),
    SuiteSpec("combat", "test_combat", "tactical"),
    SuiteSpec("flight", "test_flight", "flight"),
    SuiteSpec("empire", "test_empire", "empire"),
    SuiteSpec("crew", "test_crew", "crew"),
    SuiteSpec("missions", "test_missions", "missions"),
    SuiteSpec("explore", "test_explore", "exploration"),
    SuiteSpec("mining", "test_mining", "mining"),
    SuiteSpec("research", "test_research", "research"),
    SuiteSpec("trade", "test_trade", "trade"),
    SuiteSpec("ground", "test_ground", "ground"),
    SuiteSpec("politics", "test_politics", "politics"),
    SuiteSpec("design", "test_design", "design"),
    SuiteSpec("orders", "test_orders", "orders"),
    SuiteSpec("assessment", "test_assessment", "assessment"),
    SuiteSpec("balance", "test_balance", "balance"),
    SuiteSpec("bloom", "test_bloom_arc", "bloom"),
    SuiteSpec("reachable", "test_reachable", "reachable"),
    SuiteSpec("efficacy", "test_efficacy", "efficacy"),
    SuiteSpec("transit", "test_transit", "transit"),
    SuiteSpec("watches", "test_watches", "watches"),
    SuiteSpec("courtship", "test_courtship", "courtship"),
    SuiteSpec("routing", "test_routing", "routing"),
    SuiteSpec("magazine", "test_magazine", "magazine"),
    SuiteSpec("stranded", "test_stranded", "stranded"),
    SuiteSpec("geography", "test_geography", "geography"),
    SuiteSpec("prospect", "test_prospect", "prospect"),
    SuiteSpec("gates", "test_gates", "gates"),
    SuiteSpec("docking", "test_docking", "docking"),
    SuiteSpec("fog", "test_fog", "fog"),
    SuiteSpec("customs", "test_customs", "customs"),
    SuiteSpec("allegiance", "test_allegiance", "allegiance"),
    SuiteSpec("territory", "test_territory", "territory"),
    SuiteSpec("charts", "test_charts", "charts"),
    SuiteSpec("aftermath", "test_aftermath", "aftermath"),
    SuiteSpec("notes", "test_notes", "notes"),
    SuiteSpec("layers", "test_layers", "layers"),
    SuiteSpec("cargo", "test_cargo", "cargo"),
    SuiteSpec("freight", "test_freight", "freight"),
    SuiteSpec("workings", "test_workings", "workings"),
    SuiteSpec("burns", "test_burns", "burns"),
    SuiteSpec("bench", "test_bench", "bench"),
    SuiteSpec("works", "test_works", "works"),
    SuiteSpec("overtures", "test_overtures", "overtures"),
    SuiteSpec("seats", "test_seats", "seats"),
    SuiteSpec("founding", "test_founding", "founding"),
    SuiteSpec("attempts", "test_attempts", "attempts"),
    SuiteSpec("reach", "test_reach", "reach"),
    SuiteSpec("plans", "test_plans", "plans"),
    SuiteSpec("beginnings", "test_beginnings", "beginnings"),
    SuiteSpec("legacy", "test_legacy", "legacy"),
    SuiteSpec("instruments", "test_instruments", "instruments"),
    SuiteSpec("voices", "test_voices", "voices"),
    SuiteSpec("bridge", "test_bridge", "bridge"),
    SuiteSpec("time", "test_time", "time"),
    SuiteSpec("anchorage", "test_anchorage", "anchorage"),
    SuiteSpec("traffic", "test_traffic", "traffic"),
    SuiteSpec("doctrine", "test_doctrine", "doctrine"),
    SuiteSpec("firing", "test_firing", "firing"),
    SuiteSpec("approach", "test_approach", "approach"),
    SuiteSpec("officials", "test_officials", "officials"),
    SuiteSpec("dormancy", "test_dormancy", "dormancy"),
    SuiteSpec("tuning", "test_tuning", "tuning"),
    SuiteSpec("hands", "test_hands", "hands"),
    SuiteSpec("approaching", "test_approach_game", "approaching"),
    SuiteSpec("harness", "test_harness_guard", "harness"),
    SuiteSpec("salvage", "test_salvage", "salvage"),
    SuiteSpec("provisional", "test_provisional", "provisional"),
    SuiteSpec("counter", "test_counter", "counter"),
    SuiteSpec("landing", "test_landing", "landing"),
    SuiteSpec("charting", "test_charting", "charting"),
    SuiteSpec("conviction", "test_conviction", "conviction"),
    SuiteSpec("evidence", "test_bench_kinds", "evidence"),
    SuiteSpec("envoy", "test_envoy", "envoy"),
    SuiteSpec("seatwork", "test_seatwork", "seatwork"),
    SuiteSpec("thermal_doors", "test_thermal_doors", "thermal doors"),
    SuiteSpec("ventures", "test_ventures", "ventures"),
    SuiteSpec("orderplan", "test_orderplan", "order plan"),
    SuiteSpec("postings", "test_postings", "postings"),
    SuiteSpec("grants", "test_grants", "grants"),
    SuiteSpec("helm", "test_helm", "helm"),
    SuiteSpec("thermal", "test_thermal", "thermal"),
    SuiteSpec("courting", "test_courting", "courting"),
    SuiteSpec("picture", "test_picture", "picture"),
    SuiteSpec("seams", "test_seams", "seams"),
    SuiteSpec("manual", "test_manual", "manual"),
    SuiteSpec("tutorial", "test_tutorial", "tutorial"),
    SuiteSpec("grudges", "test_grudges", "grudges"),
    SuiteSpec("gunnery", "test_gunnery", "gunnery"),
    SuiteSpec("surveys", "test_surveys", "surveys"),
    SuiteSpec("chronicle", "test_chronicle", "chronicle", True),
    SuiteSpec("dig", "test_dig", "dig"),
    SuiteSpec("resume", "test_resume", "resume", True),
    SuiteSpec("verbs", "test_verbs", "verbs", True),
    SuiteSpec("ui", "test_ui", "interface", True),
]

SUITES_BY_KEY = {s.key: s for s in SUITES}

#: Order matters: this is the order a full run reports in.
ALL_SUITES = [s.key for s in SUITES]
