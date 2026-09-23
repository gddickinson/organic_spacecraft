"""PyQt6 presentation layer. Views never mutate state directly — they call into
sim/ and then ask the window to refresh.

Contents (178 modules; one line each in `INTERFACE.md`):

The window: app, window, window_dialogs, view_registry, menubar, hud,
    log_panel, crash, popout, monitors, title, chronicle_picker,
    seed_dialog, beginning_view, tutorial_bar, focus, flow, view_base,
    widgets, theme, painting, layer_row, endings.
The chart and the system: map_view, star_chart, reaches_chart, sky_chart,
    system_view, survey_panel, crossing_panel, anchorage_panel,
    traffic_panel, life_panel, mesh_panel, orbit_chart, reaches_panel,
    sky_strip, weave_panel, spheres, surface.
Flying: helm_view, pilot_view, pilot_panels, pilot_acts, conn_window,
    conn_controls, conn_panel, conn_moves, conn_targets, flight_window,
    flight_clock, flying_keys, autopilot_bar, approach_window,
    approach_plot, viewport, viewport_hud, viewport_mark, viewport_math,
    viewport_target, sights, mount_sight, thrust_pad, gauges, plot_canvas,
    plot3d_window, render3d, stars3d, thumb3d, effects, effect_paint,
    effect_marks, effect_clock.
Fighting: battle_view, battle_orders, battle_text, battle3d, tactical_plot,
    tactical_board, tactical_window, gunner_window, fire_panel,
    firing_panel, doctrine_panel, assessment_panel, hunts_panel, hunt_marks,
    gunnery_view, turret_window, turret_view, turret_scene, turret_hud,
    turret_panels, turret_controls.
Port, trade and the yard: port_view, market_grid, board_panel,
    commissions_panel, freight_panel, register_panel, blackmarket_panel,
    berths_panel, official_panel, rumours_panel, yard_view, shipdiagram,
    machineshop, robots_panel, concourse_panel.
The ship: ship_view, plans_panel, body_panel, arc_panel, dormancy_panel,
    mining_panel.
The crew: crew_view, crew_roster, crew_sheet, crew_ops, portrait,
    portrait_paint, body_plan.
The concourse: concourse_view, concourse_shops, concourse_body,
    concourse_night, concourse_law, concourse_hire, place_scene.
Afoot: afoot_view, afoot_canvas, afoot_panels, afoot_talk_panel,
    afoot_start.
Holdings, the house and the Voyage: empire_view, works_panel,
    industry_panel, exchequer_panel, house_panel, house_dialog,
    voyage_panel, counsel_card, renown_chip, programmes_panel,
    ventures_panel.
The powers and the law: diplomacy_view, assembly_panel, envoy_view,
    demand_view, law_view.
Research, the ground and the Kith: tech_view, tech_tree, inquiry_panel,
    xeno_view, expedition_view, dig_view, minigame_view, kith_panel,
    kith_codex.
News, help and the rest: despatch_view, comms_window, codex_view, help_view,
    academy_panel, legacy_view, memoir_panel, orders_panel, transit_view,
    options_view.
Sound: audio, synth, soundmap.
Everything else: afoot_marks, craft_panel, craft_window, craft_yard,
    worldmap_view, zone_canvas."""
