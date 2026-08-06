"""Which suites speak for which module, for the tripwire's first stage.

Split out of `tests/tripwire.py` when that file reached the five-hundred-line
ceiling for the fourth time in a fortnight — and it was this table doing it
every time, because a table grows a row whenever the game grows a module
while the tool around it stays the size it was. `sweepkit` came out of the
same file for the same reason; this is the other half of the same seam: the
sweep is a *tool*, and which suite knows which module is *data*.
"""

from __future__ import annotations

#: Suites named after a module, so a constant is tried against its own
#: neighbourhood first. Two stages: the cheap one, then the wide one only on
#: the survivors. A single-stage sweep of everything is three hours.
#: One entry per module, and **exactly** one: six modules had two, and in a
#: dict literal the later wins silently. `stations` was the costly one — its
#: broad entry (routing, orderplan, seatwork) sat above a second entry reading
#: just `("gunnery",)`, so every constant the three seats own had been swept
#: against one suite that does not name them. `mounts` lost `lopsided` and
#: `rumours` lost `missions` the same way. `tests/test_harness_guard.py` now
#: refuses a duplicate, because this is not the sort of thing anyone sees by
#: reading a hundred-line table.
KIN = {
    "dormancy": ("dormancy",), "lineages": ("time",), "crossings": ("time",),
    "officials": ("counter", "officials"),
    # `ticks` caught `ODDS_PER_DAY` at double when `envoy`, `approach`,
    # `politics`, `play`, `sim`, `courting` and `overtures` all ran green.
    "approaches": ("envoy", "approach", "ticks", "tuning"),
    "approach": ("envoy", "approach"),
    "surveys": ("surveys",), "survey": ("charting", "surveys"),
    "anchorage": ("anchorage",),
    "doctrine": ("doctrine",), "firing": ("firing", "gunnery"),
    "tactical": ("gunnery", "combat"), "combat": ("seatwork", "combat", "gunnery"),
    "abilities": ("abilities", "combat"),
    "encounters": ("magazine", "readiness"),
    "impulse": ("impulse", "conn"),
    "knock": ("knock",),
    "moorings": ("moorings", "conn"),
    "clearance": ("clearance", "berthing"),
    "freeflight": ("freeflight", "freeframe", "conn", "pilotscreen"),
    "berths3d": ("standoff", "silhouettes"),
    "works3d": ("works3d",),
    "robots": ("robots",),
    # Split out of `robots` (#138). Earned: `robots` catches HALF_LIFE_S,
    # LIGHT_S_PER_AU and AU_PER_LY; `swarm` catches GUARD_DUTY.
    "telepresence": ("robots", "swarm"),
    "robots3d": ("robots3d",),
    "bays": ("bay", "berthing"),
    "control": ("control", "berthing"),
    "forcing": ("forcing", "control", "berthing"),
    # Split out of `control` (#138), constants and all. Measured: `control`
    # catches `TUG_FROM` at half. Speed, not safety — `control` is not in
    # `SLOW`, so the broad stage would catch it with or without this row.
    "tug": ("control", "clearance"),
    "landing": ("setdown", "landing"),
    "interdiction": ("interdiction",),
    "relics3d": ("relics3d",),
    "fleets": ("fleets", "control"),
    "armada": ("armada", "fleets"),
    "engage": ("engage", "combat", "pilotscreen", "firecontrol"),
    "war": ("war", "armada"),
    "piracy": ("piracy", "traffic", "fence"),
    "life3d": ("life3d",),
    "parts3d": ("parts3d",),
    "readiness": ("readiness",),
    "parley": ("parley", "combat"), "prize": ("prize",),
    "battle_state": ("prize", "combat"),
    "stations": ("routing", "orderplan", "seatwork", "turnplan", "gunnery"),
    "damage": ("thermal_doors", "combat"), "contraband": ("customs",),
    "customs": ("customs", "fence"),
    # `courtship` first: it is the real guard for the COURTSHIP_* family and
    # costs 1.4 s against `politics`'s 145.4 (#134).
    "diplomacy": ("courtship", "politics"),
    "grudge": ("grudges",), "colonies": ("works", "founding"),
    "works": ("works",), "mining": ("mining",), "research": ("bench",),
    "inquiry": ("evidence", "bench"), "flight": ("helm", "flight", "burns"),
    "path": ("helm", "flight", "burns"),   # split from `flight`, same pins
    "collision": ("collision", "detection", "byhand", "conn"),
    "elements": ("elements", "flight", "orrery"),
    "remnants": ("remnants", "geography"),
    "gate_traffic": ("gatetraffic", "gates"),
    "gatetraffic": ("gatetraffic", "gates"),
    "signals": ("comms",),
    "comms": ("comms", "gatetraffic"),
    "viewport_mark": ("bridgemarks", "sights"),
    "orbit_shapes": ("elements", "traffic", "flight"),
    "detection": ("detection", "collision"),
    "countermeasures": ("detection", "collision"),
    "contracts": ("postings", "missions", "cargo"), "chains": ("missions",),
    "expedition": ("landing", "ground", "wayhome"), "weather": ("ground",),
    "territory": ("territory", "levy"), "allegiance": ("allegiance",),
    "charts": ("provenance", "charting", "charts"),
    "notes": ("notes",),
    "freight": ("freight",),
    "market": ("trade",), "economy": ("trade", "solvency"),
    "commodities": ("trade",),
    "loyalty": ("conviction", "crew"), "convictions": ("conviction", "crew"),
    "crew": ("conviction", "crew"),
    "lifespan": ("time",), "upkeep": ("time",), "clock": ("time", "ticks"),
    # **`play` is here because a mutation put it here, not because it reads
    # right.** `test_play` imports nothing from `bloom`; it exercises the
    # heart by playing the game. Measured: `HEART_HP` halved and doubled runs
    # `bloom` green, `tuning` green — `tuning` is the only suite that imports
    # the module — and `play` red. A fast path written by reading the imports
    # would have missed the only suite that guards the constant.
    "bloom": ("bloom", "play", "tuning"),
    "threat": ("bloom",), "ventures": ("politics",),
    "intel": ("explore",), "transit": ("transit",), "shipyard": ("design",),

    # Modules that had no entry at all and so paid the wide run for every
    # constant they own — twenty-one of them, including `ship`, which holds
    # the thermal rule the whole game reads.
    "aftermath": ("aftermath",), "assessment": ("assessment",),
    "colony": ("grants", "founding", "swarm"),
    "minigames": ("approaching", "approach"),
    "plans": ("picture",), "ship": ("thermal_doors", "thermal", "feedstock"),
    "shocks": ("trade",), "tech": ("evidence", "bench"),
    "trade": ("counter", "trade"), "orders": ("orders",),
    "legacy": ("legacy",), "beginning": ("beginnings",),
    "watches": ("transit",),
    "services": ("trade",),

    # The law. `test_law` holds reach, filing and collection; `test_tribunal`
    # holds the hearing, the instruments and the way out — the same seam the
    # modules themselves split along.
    "offences": ("law",), "dockets": ("law",), "enforce": ("law",),
    "debts": ("law", "tribunal"),
    "tribunal": ("tribunal",), "warrants": ("tribunal", "law"),
    "clemency": ("tribunal",),

    # The conn and the plotting board. Both own a lot of tuning — thruster
    # impulses, the orbit band, the horizon — and all of it is answered by
    # the one suite, so neither should ever pay for the wide run.
    "conn": ("conn",), "autopilot": ("conn",), "track": ("conn",),
    "viewport": ("cameras",), "berthing": ("berthing", "conn", "pilotscreen"),
    "orbits": ("orbits", "conn", "berthing", "climbs"),
    "outcome": ("orbits", "conn", "berthing"), "targets": ("conn", "berthing"),
    "thrusters": ("thrusters",), "attitude": ("thrusters", "conn"),
    "weave": ("weave",), "gates": ("weave",),
    "instruments": ("conn",), "models3d": ("cameras",),
    "render3d": ("cameras",), "gunfire": ("gunfire",),
    "sky": ("cameras", "worlds"), "worlds3d": ("worlds",),
    "starclasses": ("worlds", "orbits"),
    "programmes": ("programmes",),
    "consorts": ("combat", "screening", "company"),
    "mounts": ("thrusters", "lopsided"),
    "pilot": ("pilot", "conn", "climbs"),
    "gunnery": ("volley", "gunboard", "gunnery"),
    "battle3d": ("gunfire",),
    "burnplan": ("thrusters", "helm"),
    "exchequer": ("exchequer", "industry", "politics"),
    "industry": ("industry", "exchequer"),
    # Measured constant by constant (#134): `exchequer` catches seven of its
    # thirteen in 3.5 s and `industry` catches two more in 7.5 — INDUSTRY_YIELD
    # and WAR_CHEST — which used to fall through to `politics` at 145.4 s a
    # variant. Cheapest first, dearest last.
    "rumours": ("provenance", "explore", "missions"),
    "memory": ("provenance", "grudges"),
    "options": ("options",),
    "traffic": ("traffic", "mesh", "hostiles"),
    "hostiles": ("hostiles",),
    "lifeforms": ("biology", "surveys"),
    "biology": ("biology",),
    "settlements": ("settlement", "exchequer"),
    "settlement": ("settlement",),
    "tutorial": ("tutorial",),
    "wharfage": ("wharfage", "counter", "accord"),
    "accord": ("accord", "wharfage"),
    "turnplan": ("turnplan", "orderplan"),
    "surfaces": ("surfaces", "worlds", "lighting"),
    "hulls3d": ("hullshapes", "combat"),
    "stars3d": ("starlight", "cameras"),
    "ships3d": ("silhouettes",),          # berths3d is above, with "standoff"
}
