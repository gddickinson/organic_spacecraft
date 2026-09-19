# The module layout as of August 2026 (2 of 2)

The hand-written module map `seedfall/INTERFACE.md` carried until 2026-09, kept for its per-module notes. **Not current:** the generated maps (`<package>/INTERFACE.md`) are.

```
│   ├── loyalty.py      what the bridge thinks of how you run the ship
│   ├── control.py      approach control: who holds each berth (derived from
│   │                   the traffic), what the structure told you, the quiet
│   │                   refusal, the hail→warn→ward→repel ladder, and a
│   │                   station that simply leaves
│   ├── bays.py         what a hull can actually strike — a bounding radius is
│   │                   not a hull — and the structures you fly *into*: the
│   │                   aperture, the corridor through it, and the rim
│   ├── robots.py       machines you own: the roster, where each is posted,
│   │                   and `grip` — how much of a machine's rating survives
│   │                   the light-lag to whoever is supervising it. The one
│   │                   law the whole robot design turns on
│   ├── works.py        colony development: what a settlement becomes
│   ├── clearance.py    being cleared to dock: which berth the structure
│   │                   assigns, and everything the approach needs
│   ├── freeflight.py   taking the conn on nothing in particular: flying the
│   ├── engage.py       the seam from flying to fighting. Decides whether a
│   │                  pilot may open fire and **at what band the fight
│   │                  starts**, from how far `conn.pos` has been flown, then
│   │                  hands both to `combat.start`. Resolves nothing itself.
│   │                   ship for its own sake, and having it move the hull
│   ├── moorings.py     berths: where a ship ties up on a structure, and
│   │                   where an approach is actually flying
│   ├── knock.py        what being shoved off station comes to, and how
│   │                   long it takes to get back on it
│   ├── impulse.py      momentum: masses, inelastic contact, and what two
│   │                   things do to each other — both of them
│   ├── readiness.py    what the ship brings to a fight nobody has started:
│   │                   a rehearsal through `combat.start`, thrown away
│   ├── flight.py       the helm: orbits, intercepts, routing, transfer burns.
│   │                   `ship_position` is the one door for where the hull is
│   │                   **now** — the recorded place plus the flight in hand;
│   │                   `base_position` is the recorded place alone, which is
│   │                   what `freeflight.where` flies from. `hold_at` and
│   │                   `stand_off` are the only two writers, and both spend
│   │                   the flight into the place they write
│   ├── path.py         where a leg actually runs: the arc bent round the
│   │                   star, the heat of working close in, and the risk —
│   │                   split from `flight`, which imports it to quote
│   ├── survey.py       what a way of looking costs, finds, and is blind to
│   ├── approach.py     a power's envoy: caused, costed, and answerable;
│   │                   a treaty signed here costs what one you propose costs
│   ├── officials.py    who runs the quay, what they think, what you know
│   ├── anchorage.py    quays, hubs and holdings — places you can put in
│   ├── traffic.py      other hulls: where they are, what they are doing,
│   │                   and which systems the picket mesh reports from
│   ├── doctrine.py     the battle computer: what unattended seats decide
│   ├── firing.py       which mounts bear, and what would fix the rest
│   ├── damage.py       a hit: which layer takes it, what breaches, the words
│   ├── dormancy.py     who is under, what it saves, and who wakes up
│   ├── lifespan.py     ageing, decline, and the end of a career
│   ├── upkeep.py       what each lineage eats, and what going short costs
│   ├── minigames.py    the docking control loop and the decoding bench
│   └── actions.py      player actions spanning modules (jump/survey/mine/dive)
├── ui/                 PyQt6 presentation — never mutates state directly
│   ├── theme.py        palette, fonts, the global stylesheet
│   ├── widgets.py      Panel, Card, Bar, Pill, TabBar and the View base class
│   ├── window.py       MainWindow: hud, nav rail, view stack, log; refuses
│   │                   an unknown screen before touching anything, saves on
│   │                   close
│   ├── window_dialogs.py  toast/dialog/confirm, bound as methods the way
│   │                   flight_clock's are; None from a dialog is a refusal,
│   │                   never a choice
│   ├── title.py        title screen and the opening briefing; cancelling it
│   │                   returns to a live chronicle rather than closing
│   ├── app.py          QApplication bootstrap
│   ├── map_view.py     custom-painted sector chart and jump control
│   ├── system_view.py  bodies, survey, extraction, diving, colonising
│   ├── survey_panel.py the four methods as cards, each stating its blind spot
│   ├── crossing_panel.py  the four ways to fly it, costed on both clocks
│   ├── anchorage_panel.py where you can put in, and how to get back to it
│   ├── traffic_panel.py   who else is out here, and which of them runs dark
│   ├── life_panel.py      the life catalogue, grouped by biochemistry
│   ├── mesh_panel.py      what the picket mesh hears in systems you are
│   │                   not in, and what the chart marks because of it
│   ├── doctrine_panel.py  what the seats you are not in intend this turn
│   ├── firing_panel.py    mount by mount: ready, or exactly what is stopping it
│   ├── approach_plot.py   the docking approach, drawn instead of counted
│   ├── envoy_view.py      a power's proposition, with all three answers costed
│   ├── official_panel.py  the desk: who is there, and both ways of asking
│   ├── dormancy_panel.py  the long sleep, costed in years, tonnes and lives
│   ├── tactical_plot.py   the engagement from above, arcs included
│   ├── port_view.py    market, services, recruitment
│   ├── board_panel.py  the contract board, split out of port_view
│   ├── ship_view.py    layer stack, fittings, crew, hold
│   ├── plans_panel.py  the ship drawn: materials, rim light, blight
│   ├── yard_view.py    hull designer, build queue, fleet management
│   ├── tech_view.py    research tree
│   ├── empire_view.py  colonies, depot, victory progress, waiting
│   ├── codex_view.py   class reference, powers, glossary, about
│   ├── xeno_view.py    the xenology desk (hosted as a Research tab)
│   ├── expedition_view.py  the landing zone: fogged map, party, field log
│   ├── diplomacy_view.py   relations matrix and the overture desk
│   ├── helm_view.py    the helm screen: burn planner, where to put in
│   ├── fire_panel.py  the fire control: what is in reach, what firing would
│   │                  mean at that range, and the trigger. Refusals print;
│   │                  the battle `engage` built is handed over, not rebuilt
│   ├── painting.py    one door for painting on a widget: `Painted` owns the
│   │                  painter's lifetime so a paint that cannot begin (or
│   │                  dies mid-frame) is recorded in `MISSES` rather than
│   │                  killing the process from inside `paintEvent`
│   ├── viewport_mark.py the ring and name on whatever the course is laid on.
│   │                  A free flight has no `conn.target`, so the window drew
│   │                  nothing and every contact looked alike
│   ├── viewport_math.py where a direction lands on the screen: `project`,
│   │                  `_unit`, `HALF_FOV`. Pure geometry, no Qt
│   ├── pilot_panels.py the bridge's two columns and the boards in the right
│   │                  one. The screen was 1,444 px tall in a 782 px view
│   │                  until it was measured on a *shown* window
│   ├── pilot_view.py   the Pilot screen: the view out, six cameras, the six
│   │                  axes, a course you can lay on anything in view, and
│   │                  drive and throttle. The armed state it shows is the
│   │                  flight's own (`Conn.auto`/`arm_main`/`clock_on`).
│   ├── flight_clock.py the one clock that flies `game.conn`: set_conn_clock,
│   │                  fly_beat and beat_refresh, bound as MainWindow methods
│   ├── conn_moves.py  the acts that swap the conn's flight — retarget,
│   │                  reopen, fly free — each billing the flight it replaces
│   ├── conn_panel.py  the conn's side panel: `content` says what it shows,
│   │                  `apply` updates in place and rebuilds only when the
│   │                  set of things said changes
│   ├── flying_keys.py the six axes on keys (W/A/S/D, R/F), through the same
│   │                  hold-to-burn doors the buttons wire
│   ├── autopilot_bar.py the one autopilot bar every flying screen shows:
│   │                  the modes, Manual, and the computer-dock button
│   ├── viewport_hud.py heads-up aids in every camera: the predicted path,
│   │                  prograde/retrograde, the aim point, a bay's mouth
│   ├── orbit_chart.py the orrery widget — paints bodies, quays, traffic
│   │                  and the leg you are about to fly; answers clicks.
│   │                  One door for label placement (`_room_for`) and one
│   │                  for a quay's mark (`place_mark`, painter + hit test)
│   ├── minigame_view.py    docking approach and decoding bench
│   ├── dig_view.py     the trench: the stratum you are on and how to take it
│   ├── blackmarket_panel.py  the quiet word on the quay, and the tip-off
│   ├── freight_panel.py  what is worth loading here, and what it clears
│   ├── demand_view.py  answering a power that has annexed ground you hold
│   ├── despatch_view.py the inbox `sim/comms` kept with no UI, plus the
│   │                  full chronicle with a kind filter; every action a
│   │                  comms door
│   ├── battle_text.py  the battle screen's words — parley forecasts and
│   │                  the aftermath card, priced by `sim`, drawn by the view
│   └── battle_view.py  combat screen and post-engagement resolution,
│                      including the prize choice on a struck hull
└── tests/              python -m seedfall.tests
    ├── harness.py      a tiny check runner (no pytest dependency)
    ├── test_sim.py     27 simulation checks
    ├── test_xeno.py    5 alien-technology checks
    ├── test_play.py    14 playability checks — can the game be won and lost
    ├── test_combat.py  5 tactical checks — arcs, stations, consorts
    ├── captain_ai.py   a competent test pilot: steers until its arcs bear
    ├── test_empire.py  6 colony checks — works, effects, costs, persistence
    ├── test_crew.py    7 crew checks — convictions, loyalty, consequences
    ├── test_missions.py 7 commission checks — escalation, blocking, lapsing
    ├── test_settlement.py 8 checks — people on the ground, and the local
    │                   price of what they dig
    ├── test_biology.py 7 checks — what you can make sense of on the ground
    ├── test_mesh.py    5 checks — what a CHORUS Node lets you see
    ├── test_options.py 8 checks — every setting does something
    ├── test_provenance.py 9 checks — a rumour's source, and whether
    │                   the buyer of a chart knows yours
    ├── test_explore.py 8 exploration checks — the intel ladder, rumours
    ├── test_mining.py  7 mining checks — seams, methods, wear, exhaustion
    ├── test_research.py 8 research checks — evidence, approaches, setbacks
    ├── test_trade.py   8 trade checks — shocks, the register, staleness
    ├── test_ground.py  7 ground checks — weather, sight, being pinned
    ├── test_politics.py 8 politics checks — ventures, sides, the Concord
    ├── test_design.py  6 design checks — loading, overloading, stranding
    ├── test_orders.py  8 orders checks — reachability, urgency, unread state
    ├── test_assessment.py 6 read checks — honesty, arcs, robustness
    ├── test_balance.py 8 balance checks — measured by playing the fights
    ├── test_bloom_arc.py 7 Bloom checks — provocation, answers, study
    ├── test_transit.py 6 crossing checks — watches, aborting, tension
    ├── test_watches.py 5 checks — every option a real trade, every risk priced
    ├── test_courtship.py 7 checks — diminishing returns on goodwill
    ├── test_routing.py 5 checks — power routing lands the turn it is ordered
    ├── test_magazine.py 6 checks — the other side can actually fight
    ├── test_stranded.py 6 checks — the way out of a dead end is real
    ├── test_geography.py 5 checks — a port stays the kind of port it is
    ├── test_grants.py  8 checks — every colony effect is read, and does something
    ├── test_prospect.py 5 checks — a ground option's prize is the officer's prize
    ├── test_gates.py   4 checks — every "may I?" agrees with the act it guards
    ├── test_beginnings.py 11 checks — the opening card is the chronicle you get
    ├── test_docking.py 5 checks — the approach instrument can be believed
    ├── test_fog.py     6 checks — the chart shows only what you can see
    ├── test_customs.py 9 contraband checks — the premium, the search, heat
    ├── test_allegiance.py 8 checks — taking sides, and brokering out of it
    ├── test_territory.py 8 checks — annexation, levy, defiance, seizure
    ├── test_charts.py  9 chart checks — contents, buyers, staleness, rate
    ├── test_aftermath.py 7 checks — salvage, standing, and who is glad
    ├── test_notes.py   8 field-note checks — filed, counted, kept, reachable
    ├── test_layers.py  5 layer checks — no Qt below, no ledger above
    ├── test_cargo.py   6 cargo-contract checks — the board offers no traps
    ├── test_freight.py 9 freight checks — the desk, its floor, its stock,
    │                   and a career
    ├── test_workings.py 7 mining checks — the rig stops when the hold is full
    ├── test_burns.py   7 burn checks — heat, cooking, and a real profile choice
    ├── test_bench.py   5 bench checks — the draw matches what the screen says
    ├── test_works.py   5 works checks — nothing gated behind a phantom tech
    ├── test_overtures.py 5 checks — the preview is what the overture does
    ├── test_seats.py   6 seat checks — what taking a station is worth
    ├── test_founding.py 5 checks — the seed dialog says what will grow
    ├── test_attempts.py 6 checks — the odds shown are the odds rolled
    ├── test_reach.py   6 reach checks — the chart's wall is a real wall
    ├── test_plans.py   8 plan checks — the model is the ship, and it is solid
    ├── test_picture.py 8 checks — the picture shows the ship's condition
    ├── test_courting.py 8 checks — a gift is seen by the recipient's enemies
    ├── test_thermal.py 12 checks — guns and helm both bounded
    ├── test_helm.py    5 checks — every number on the burn board is accounted
    ├── test_grants.py  5 checks — every colony grant is read, and explained
    ├── test_postings.py 5 checks — the board only offers work you can reach
    ├── test_counter.py 6 checks — the board's price is the counter's
    │                   price, on the screen as well as in the helper
    ├── test_landing.py 6 checks — walking home beats stranding
    ├── test_charting.py 5 checks — a chart is dated, and goes off
    ├── test_conviction.py 6 checks — every event an officer cares about fires
    ├── test_bench_kinds.py 5 checks — evidence names are real, tech is reachable
    ├── test_envoy.py   7 checks — the preview is the answer, both doors alike
    ├── test_seatwork.py 5 checks — the crew hold their seats either way
    ├── test_thermal_doors.py 5 checks — every heat door goes through one gate
    ├── test_ventures.py 6 checks — both sides of a venture are costed
    ├── test_exchequer.py 10 checks — the powers' purses: income,
    │                   upkeep, building, retrenchment, the venture stake
    ├── test_climbs.py  5 checks — the conn sells no climb the tank cannot
    │                   make, and prices the ones it refuses
    ├── test_company.py 6 checks — who may be ordered to sail in company,
    │                   and what feeding them costs
    ├── test_parley.py  6 checks — the odds on talking your way out, stated
    │                   and then measured by hailing four hundred times
    ├── test_wayhome.py 8 checks — the walk back to the lander, priced against
    │                   what walking it spends
    ├── test_abilities.py 6 checks — every bridge ability fires, is bounded,
    │                   and says what it will do
    ├── test_levy.py    5 checks — the levy on a holding: taken, received,
    │                   and said out loud
    ├── test_fog.py     10 checks — what the chart shows about a star nobody
    │                   of yours has looked at, the body count included
    ├── test_wharfage.py 10 checks — the due on your own trade: conserved,
    │                   named on the board, waived at a free port, priced by
    │                   standing and by the size of the berth
    ├── test_accord.py  10 checks — a treaty's two clauses are real: the
    │                   relief lands at their quays and nobody else's, the
    │                   charts are priced at what a broker would take, the
    │                   desk quotes both before signing, and proposing one
    │                   and accepting one deliver the same instrument
    ├── test_industry.py 10 checks — a licensed process changes a market
    ├── test_orderplan.py 6 checks — every order says what it will do
    ├── test_turnplan.py 8 checks — and says it about the *turn*: the figure
    │                   on the button is where the hull ends up, played over
    │                   2,000 turns, with the gunner you left behind named
    ├── ground_ai.py    a party leader good enough to measure the ground with
    ├── suites.py       the suite table `__main__` dispatches from
    ├── test_beginnings.py 9 checks — the commission you pick is the one you get
    ├── test_legacy.py  12 aftermath checks — an ending is a turn, not a stop;
    │                   no epoch unfailable, absence decided, the calendar runs
    ├── test_solvency.py 7 checks — money cannot be conjured: scrap, raw
    │                   prices, contraband markets, promotion, the Cartel
    ├── test_prize.py   7 checks — striking colours, the prize choice,
    │                   nonlethal meaning it, struck priced between outcomes
    ├── test_despatch.py 5 checks — the despatch board, courier lag, sweep
    │                   aging, digit keys on their rail positions
    ├── chronicle_fights.py the decade driver's combat half — seeking
    │                   trouble and taking the engagement (split at the
    │                   ratchet; `chronicle.py` sits under the limit now)
    ├── test_instruments.py 5 checks — a gauge agrees with the ship and itself
    ├── test_lopsided.py 9 checks — what one missing engine of a pair costs
    ├── test_pilot.py   9 checks — a throttle and a coast the pilot can reach
    ├── test_volley.py  7 checks — the gunner's middle: fire some of them
    ├── test_gunboard.py 3 checks — the board, pressed and read off screen
    ├── test_revived.py 5 checks — what the revived dead fields now do
    ├── test_voices.py  8 checks — the game speaks with no model reachable
    ├── test_grudges.py 9 checks — memory reaches the price and the board
    ├── test_gunnery.py 5 checks — what a weapon delivers is what the bridge said
    ├── test_controls.py 4 checks — every control that is not a button
    ├── interact.py     plays by pressing what is on the screen, not by calling sim
    ├── test_bridge.py  6 checks — the protocol answers, always, and stays local
    ├── test_manual.py  13 checks — the manual cannot go stale, options cannot lie
    ├── test_tutorial.py 12 checks — it will not take your word for it
    ├── chronicle.py    one captain, one save, a decade of doing everything
    ├── test_chronicle.py 3 checks — that decade, through every screen
    ├── capture.py      renders every screen offscreen, for the README
    ├── captain_bot.py  the long-game captain the playability checks fly
    ├── probes.py       the newer efficacy probes, split out of levers.py
    ├── test_dig.py     7 dig checks — strata, methods, banking, backfilling
    ├── test_resume.py  5 resume checks — anything half-done survives a save
    ├── efficacy.py     the harness: neutralise a feature, measure the world
    ├── levers.py       one entry per claim the game makes about a number
    ├── test_efficacy.py 31 checks — every feature has to move something
    ├── test_reachable.py 4 reachability checks — nothing written and uncalled
    ├── test_verbs.py   10 verb checks — every control in the game, clicked
    ├── test_flight.py  5 helm checks — determinism, intercepts, routing
    ├── test_flightdeck.py 9 checks — one armed state, one clock, one bill:
    │                   every window reads the flight, and no path replaces
    │                   a live conn without paying for it
    └── test_ui.py      24 interface checks, rendered on Qt's offscreen platform
```
