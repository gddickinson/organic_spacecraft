"""Game rules: ships, shipyards, combat, colonies, research, crew, encounters,
the Bloom, and the player actions that span them. Never touches Qt.

Contents (244 modules; one line each in `INTERFACE.md`):

The ship and its fittings: ship, plans, loading, thrusters, shipyard,
    stores, services, abilities, damage, adaptation, readiness.
Flying: the conn and the flight deck: conn, conn_open, conn_step,
    flightdeck, freeflight, autopilot, attitude, pilot, preview,
    instruments, outcome, collision, detection, track, targets, bays,
    moorings, moorings_steer, knock, impulse, tug, control, clearance,
    telemetry, sheer, forcing, berthing, anchorage, orbits, orbit_heights,
    elements, shock.
Getting anywhere: actions, flight, heliocentric, burnplan, burn_incidents,
    path, reach, transit, dormancy, passage, wayhome, gates, weave,
    gatetraffic, regions, relight.
Fighting: combat, battle_state, tactical, stations, turnplan, enemy_ai,
    doctrine, gunnery, firing, gunfire, shooting, assessment, parley, prize,
    aftermath, engage, consorts, turret, gunsight, foes, skirmish, drills,
    manning.
Rivals and the hunt: nemeses, rivals, rival_ends, hunts, running_dark,
    hostiles.
Trade, freight and money: trade, market, profile, shore, freight,
    freightlines, linetrips, lineroute, lineforecast, lineledger, haulers,
    masters, wharfage, customs, exchequer, exchequer_ledger,
    exchequer_payback, industry, commitments, contracts, chains.
Surveying, mining and the ground: survey, mining, charts, intel, rumours,
    notes, fieldwork, expedition, expedition_gen, landing, weather, biology,
    dig, xeno, programmes.
Research: research, inquiry.
Holdings: colony, works, settlement, robots, telepresence, territory,
    interdiction.
The powers, the law and the Assembly: diplomacy, diplomacy_acts, accord,
    allegiance, approach, ventures, war, armada, fleets, grudge, officials,
    law, governance, dockets, tribunal, debts, warrants, enforce, clemency,
    piracy, assembly, assembly_session, assembly_vote, assembly_lobby.
The crew and their stories: crew, roster, loyalty, lifespan, upkeep, arcs,
    arc_beats, arc_places, lifepath, checks, person.
Places and the concourse: places, clinic, authority, kindred.
Afoot: walking a deck: afoot, afoot_begin, afoot_state, afoot_sites,
    afoot_map, afoot_people, afoot_cast, afoot_incidents, afoot_fight,
    afoot_ai, afoot_acts, afoot_deeds, afoot_talk, afoot_said, afoot_ends.
Afoot: deck plans drawn to shape: afoot_plans, afoot_program,
    afoot_placeprog, afoot_hullplan, afoot_latticeplan, afoot_loops,
    afoot_stationplan, afoot_worksplan, afoot_groundplan, afoot_blocks,
    afoot_gen, afoot_furnish.
The Bloom and the endings: threat, bloom, responses, legacy.
The Kith and the sky: kith, kith_acts, kith_world, phenomena,
    phenomena_tick, phenomena_forecast, phenomena_bodies, phenomena_shelter,
    phenomena_nova, phenomena_science, sky.
Voices, news and memory: comms, hail, voice, memory, traffic, encounters.
Renown, counsel and the memoir: renown, renown_facts, renown_perks, counsel,
    counsel_sources, counsel_doors, counsel_kit, memoir.
Starting, teaching and settings: beginning, tutorial, tutorial_watch,
    manual, options, orders, minigames.
Everything else: afoot_fire, afoot_holdings, afoot_kith, afoot_ringplan,
    afoot_trouble, afoot_ways, craft, crossing, establishments."""
