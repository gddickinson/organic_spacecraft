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
    "approaches": ("envoy", "approach", "ticks", "tuning", "rulebook"),
    "approach": ("envoy", "approach", "rulebook"),
    "surveys": ("surveys",), "survey": ("charting", "surveys", "exploits"),
    "passage": ("rulebook",),
    "anchorage": ("anchorage",),
    "doctrine": ("doctrine",), "firing": ("firing", "gunnery"),
    "tactical": ("gunnery", "combat"), "combat": ("seatwork", "combat", "gunnery"),
    # Split out of `combat` (#35): one shot and one salvo, DAZZLE_CAP with them.
    "shooting": ("seatwork", "combat", "gunnery"),
    "abilities": ("abilities", "combat"),
    "encounters": ("magazine", "readiness"),
    "impulse": ("impulse", "conn"),
    "knock": ("knock",),
    "shock": ("shock", "conn"),
    "profile": ("uwp", "trade"), "uwp": ("uwp",),
    "checks": ("lifepath",), "lifepath": ("lifepath", "crew"),
    "careers": ("lifepath",), "person": ("shore",), "shore": ("shore",),
    "kit": ("shore",), "venues": ("shore",), "backgrounds": ("shore",),
    "roster": ("muster", "crew"),
    "places": ("concourse", "bodywork", "shore"),
    "clinic": ("bodywork",), "venues_aboard": ("bodywork",),
    "kindred": ("kindred", "crew"),
    "authority": ("concourse", "rulebook"),
    "careers_civil": ("lifepath",), "career_types": ("lifepath",),
    "treatments": ("bodywork",), "venue_types": ("concourse", "shore"),
    "venues_trade": ("shore",), "venues_body": ("concourse",),
    "venues_night": ("shore",),
    "turret": ("turret",), "gunsight": ("turret",), "foes": ("turret",),
    "skirmish": ("turret",), "drills": ("turret",), "manning": ("turret",),
    "moorings": ("moorings", "conn"),
    "moorings_steer": ("moorings", "byhand", "conn"),
    "clearance": ("clearance", "berthing"),
    "freeflight": ("freeflight", "freeframe", "conn", "pilotscreen"),
    "berths3d": ("standoff", "silhouettes"),
    "works3d": ("works3d",),
    # Split out of `works3d` (#35) with the geometry its parts share.
    "works3d_parts": ("works3d", "bay"),
    "robots": ("robots", "unattended"),
    # Split out of `robots` (#138). Earned: `robots` catches HALF_LIFE_S,
    # LIGHT_S_PER_AU and AU_PER_LY; `swarm` catches GUARD_DUTY.
    "telepresence": ("robots", "unattended", "swarm"),
    "robots3d": ("robots3d",),
    "bays": ("bay", "berthing"),
    "control": ("control", "berthing"),
    # Split out of `control` (#35): standing off, constants and all.
    "sheer": ("control", "berthing"),
    "forcing": ("forcing", "control", "berthing"),
    # Split out of `control` (#138), constants and all. Measured: `control`
    # catches `TUG_FROM` at half. Speed, not safety — `control` is not in
    # `SLOW`, so the broad stage would catch it with or without this row.
    "tug": ("boats", "control", "clearance"),
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
    # Split out of `flight` (#35): the orbits every quote asks about.
    "heliocentric": ("helm", "flight", "burns"),
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
    # Split out of `contracts` at 500 lines: the margin, the haulage rate and
    # what a card quotes.
    "contract_price": ("cargo", "postings", "quayside"),
    "expedition": ("landing", "ground", "wayhome"), "weather": ("ground",),
    # Split out of `expedition` (#35): generation and the haul home.
    "expedition_gen": ("landing", "ground", "wayhome"),
    "territory": ("territory", "levy"), "allegiance": ("allegiance",),
    "charts": ("provenance", "charting", "charts"),
    "notes": ("notes",),
    "freight": ("freight",),
    "market": ("trade", "rulebook"), "economy": ("trade", "solvency"),
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
    "bloom": ("bloom", "play", "tuning", "rulebook"),
    "threat": ("bloom", "rulebook", "exploits"), "ventures": ("politics",),
    "intel": ("explore",), "transit": ("transit",), "shipyard": ("design",),

    # Modules that had no entry at all and so paid the wide run for every
    # constant they own — twenty-one of them, including `ship`, which holds
    # the thermal rule the whole game reads.
    "aftermath": ("aftermath",), "assessment": ("assessment",),
    "colony": ("grants", "founding", "swarm"),
    "minigames": ("approaching", "approach"),
    "plans": ("picture",), "ship": ("thermal_doors", "thermal", "feedstock"),
    "shocks": ("trade",), "tech": ("evidence", "bench"),
    "trade": ("counter", "trade", "exploits"), "orders": ("orders",),
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
    "conn": ("conn", "plotting"), "autopilot": ("conn", "plotting"),
    "track": ("conn", "plotting"),
    "viewport": ("cameras",), "berthing": ("berthing", "conn", "pilotscreen"),
    "orbits": ("orbits", "orbitheight", "conn", "berthing", "climbs"),
    # Split out of `orbits` (#35): the height ladder, constants and all.
    "orbit_heights": ("orbits", "orbitheight", "conn", "berthing", "climbs"),
    "outcome": ("orbits", "conn", "berthing"), "targets": ("conn", "berthing"),
    "thrusters": ("thrusters",), "attitude": ("thrusters", "conn"),
    "weave": ("weave",), "gates": ("weave",),
    "instruments": ("conn",), "models3d": ("cameras",),
    "render3d": ("cameras",), "gunfire": ("gunfire",),
    "sky": ("cameras", "worlds", "skycompany"), "worlds3d": ("worlds",),
    "starclasses": ("worlds", "orbits"),
    "programmes": ("programmes",),
    "consorts": ("combat", "screening", "company"),
    "mounts": ("thrusters", "lopsided"),
    "pilot": ("pilot", "conn", "climbs"),
    "gunnery": ("volley", "gunboard", "gunnery"),
    "battle3d": ("gunfire",),
    "burnplan": ("thrusters", "helm"),
    "exchequer": ("exchequer", "industry", "politics"),
    "industry": ("industry", "licences", "exchequer"),
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
    # `core/slots.py`: its name limit and the head it reads a summary from
    # are what the named-chronicle checks pin.
    "slots": ("slots",),
    # `data/sounds.py`: the loop rate. Halved, a loop asks for more than its
    # file can hold; doubled, the cache passes its budget (`test_audio`).
    "sounds": ("audio",),
    # Innovation 3: the rivals, the hunt and the switch — one suite knows them
    # all, and it plays their constants (win rates, odds, the dark cut).
    "nemeses": ("nemeses",), "rivals": ("nemeses",),
    "rival_ends": ("nemeses",), "hunts": ("nemeses",),
    "running_dark": ("nemeses",),
    # Innovation 5, freight lines: the house's tables (data and sim share the
    # stem), the hulls it buys and the masters it hires.
    "freightlines": ("freightlines",), "haulers": ("freightlines",),
    "masters": ("freightlines",),
    # The living hull: a sweep of its eleven found every one caught here.
    "adaptations": ("adaptation",),
    # `data/regions.py`: the Far Reaches' rules, relight bill and condensate.
    "regions": ("reaches",),
    # Innovation 6: `data/assembly` and `sim/assembly` share the stem.
    "assembly": ("assembly",), "assembly_lobby": ("assembly",),
    "assembly_session": ("assembly",), "assembly_vote": ("assembly",),
    # Innovation 2: `data/kith` and `sim/kith` share the stem; the gift
    # economy and the placement are theirs too.
    "kith": ("kith", "kithgift"), "kith_acts": ("kithgift", "kith"),
    "kith_world": ("kith", "kithgift"),
    # Innovation 8, officer arcs: `data/arcs` and `sim/arcs` share the stem;
    # `arc_places` holds the race's distances.
    "arcs": ("arcs",), "arc_places": ("arcs",),
    # Innovation 9: the ranks and rewards (data), the check, the facts, the
    # counsel's thresholds and the Hall — one suite plays them all.
    "milestones": ("renown",), "renown": ("renown",),
    "renown_facts": ("renown",), "counsel": ("renown",),
    "counsel_sources": ("renown",), "counsel_doors": ("renown", "afootcareer"),
    "memoir": ("renown",),
    # Innovation 7: `data/phenomena` and `sim/phenomena` share the stem.
    "phenomena": ("phenomena",),
    # Afoot (2026-09-21): the rules suite pins the numbers, the play suite
    # the endings and the incidents that spend them.
    "afoot": ("afoot", "afootplay"), "afoot_acts": ("afoot", "afootplay"),
    "afoot_ai": ("afootplay",), "afoot_arms": ("afoot", "afootfire"),
    "afoot_cast": ("afootplay", "afoot"), "afoot_deeds": ("afootplay",),
    "afoot_derelicts": ("afootplay", "afoot"), "afoot_ends": ("afootplay",),
    "afoot_fight": ("afoot", "afootplay", "afootweight", "afootfire"),
    "afoot_gen": ("afoot",),
    "afoot_incidents": ("afootplay", "afootcareer"), "afoot_map": ("afoot",),
    "afoot_people": ("afoot", "afootplay", "afootcareer"),
    "afoot_plans": ("afootshapes", "afoot"),
    # The deck plans drawn to shape: hulls, loops, stations, holdings, ground.
    "afoot_programs": ("afootshapes",), "afoot_program": ("afootshapes",),
    "afoot_placeprog": ("afootshapes",), "afoot_hullplan": ("afootshapes",),
    "afoot_latticeplan": ("afootshapes",), "afoot_loops": ("afootshapes",),
    "afoot_stationplan": ("afootshapes",),
    "afoot_worksplan": ("afootshapes",),
    "afoot_groundplan": ("afootshapes",),
    "afoot_blocks": ("afootshapes", "afoot"),
    "afoot_ways": ("afootfair", "afootplay"),
    "afoot_ringplan": ("afootweight", "afootshapes"),
    "establishments": ("establishments", "concourse"),
    "afoot_talk": ("afoot", "afootplay"), "afoot_begin": ("afootplay",),
    # The open items closed (2026-09-22): fire, the Kith's exchange, trouble
    # aboard and ashore, and your own works.
    "afoot_fire": ("afootfire",), "afoot_kith": ("afootcareer",),
    "afoot_trouble": ("afootcareer", "afootplay"),
    "afoot_holdings": ("afootcareer",),
    # Made fast, or across (2026-09-22): the berth and the ways over.
    "crossing": ("crossing", "concourse", "afoot"),
    # Single-seat craft (2026-09-22): the cradle, the ticket, the sortie.
    "craft": ("craft", "craftbattle"),
    # Split out of `craft` at 500 lines: the run and the look.
    "craft_errands": ("craft", "craftui"),
    # And in an engagement (2026-09-22): the run, the answer, the cradle.
    "craft_battle": ("craftbattle",),
    # The hangar deck (2026-09-22): cradles, buying, mending, selling.
    "hangar": ("hangar", "craft"),
    # Where you may deal from (2026-09-22): the counter and the lighterage.
    "quayside": ("quayside", "trade", "wharfage"),
    # Down to the ground (2026-09-22): the lander and the world's own pull.
    "descent": ("descent", "ground", "craft"),
    # And flown rather than charged (2026-09-22).
    "descent_flight": ("descentflight", "descent", "craft"),
    # What a party crosses ground in (2026-09-22).
    "vehicles": ("vehicles", "ground", "wayhome"),
    "camps": ("camps", "ground", "vehicles"),
    # A world as a map, and what is on it (2026-09-22).
    "worldmap": ("worldmap",), "worldsites": ("worldmap",),
    "zone_canvas": ("ground", "keyboard"),
    "developments": ("worldmap",),
    # The yard side of what rides down, split out of `hangar` at 500 lines.
    "garage": ("vehicles", "camps", "hangar"),
}
