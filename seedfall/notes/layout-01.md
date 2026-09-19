# The module layout as of August 2026 (1 of 2)

The hand-written module map `seedfall/INTERFACE.md` carried until 2026-09, kept for its per-module notes. **Not current:** the generated maps (`<package>/INTERFACE.md`) are.


```
seedfall/
├── __main__.py         entry point: python -m seedfall
├── core/               engine primitives — no game rules, no Qt
│   ├── rng.py          seeded mulberry32 + pick/weighted/gauss/shuffle helpers
│   ├── util.py         formatting (credits, mass, stardate, duration) and clamp
│   ├── save.py         generic dataclass ⇄ JSON codec, @register, atomic write
│   ├── solid.py        a tiny 3D kit: primitives, projection, key/fill/rim
│   │                   lighting, specular and a depth term
│   ├── stars3d.py     the nine classes as nine pictures: colour, corona by
│   │                   luminosity, a binary as a pair, a black hole as an
│   │                   absence with a ring round it
│   ├── machineshop.py  build a machine, post it, scrap it — and the posting
│   │                   control quotes what it would be worth *there*
│   │                   before you send it
│   ├── robots_panel.py the machines you own, and what each is worth where
│   │                   it is standing — never its rating
│   ├── thumb3d.py     a catalogue portrait: one hull class, berth, world
│   │                   or star, on the renderer everything else uses
│   ├── surface.py     a cap on a sphere projected as an ellipse, from its
│   │                   own axes rather than from an orthographic guess —
│   │                   and `limb`, a world's true silhouette, clipped at
│   │                   the lens rather than abandoned there
│   ├── llm.py          optional language model, off by default, hard timeout
│   └── state.py        the Game object, advance_days(), new_game(), load_game()
├── data/               static content tables — pure data, no logic
│   ├── commodities.py  14 tradeable goods
│   ├── countermeasures.py  how loud a thing is to somebody else's sensors:
│   │                   transponding, running dark, shrouded, cloaked
│   ├── beginnings.py   stocks, origins and postings — who you are before day one
│   ├── personas.py     voices: register, tics, and offline sentence frames
│   ├── screens.py      the rail and the key for each screen — read by both layers
│   ├── help.py         the manual: prose, and which facts each topic generates
│   ├── lesson_types.py the shapes: a Lesson, and the Chapter it sits in
│   ├── lessons_early.py chapters I-V: finding your way, flying, money,
│   │                   science, distance
│   ├── lessons_late.py  chapters VI-X: working a system, fighting,
│   │                   holdings, powers, a career
│   ├── lessons.py      the curriculum: ten courses, twenty-nine lessons
│   ├── epochs.py       what the Verge becomes after each of the ten endings
│   ├── scenarios.py    40 situations an epoch puts in front of you
│   ├── chassis.py      the hull registry — assembles and re-exports the rest
│   ├── hull_types.py   layer stacks, the Chassis record, family rules (ACCEPTS)
│   ├── hulls_grown.py  the 12 GESTALT classes
│   ├── hulls_built.py  13 fabricated · 4 hybrid · 4 synthetic · 2 xeno
│   ├── part_types.py   Part / Weapon / Ability shapes, slots, range bands
│   ├── modules.py      drives, power, sensors, compute, utility organs
│   ├── armaments.py    weapons and defences
│   ├── parts.py        merged registry over modules + armaments
│   ├── tech.py         61-node research tree, 10 branches, 5 tiers
│   ├── colonies.py     19 colony and station classes, and `EFFECT_TEXT`:
│   │                   what each grant means, in words
│   ├── factions.py     6 powers + reputation bands
│   ├── exchequer.py    what a port yields, what it costs, what building costs
│   ├── wharfage.py     what a quay takes off the cargo crossing it, and
│   │                   what a treaty's berthing clause takes off that
│   ├── settlements.py  what the ground gives, and what settling it costs
│   ├── industry.py     processes: which technology makes which good, and
│   │                   what a licence to run it is worth
│   ├── lifeforms.py    xenobiology generation tables + anomalies
│   ├── strata.py       the four layers of a dig, 3 methods, finds and spoils
│   ├── contraband.py   who outlaws what, how hard they look, what they say
│   ├── territory.py    what a power says when its claim lands on your ground
│   ├── charts.py       what each power pays for a survey, and what for
│   ├── surveys.py      the four ways of looking, and what each cannot see
│   ├── approaches.py   the powers coming to you: what each wants, and why
│   ├── officials.py    harbourmasters: tempers, levers and favours
│   ├── dormancy.py     ways of sleeping a crossing, and what each risks
│   ├── lineages.py     what a crew member is made of: span, upkeep, ageing
│   ├── crossings.py    how hard to fly a jump, and which clock pays for it
│   ├── fieldnotes.py   the eight things the ground can tell you
│   ├── mounts.py       where an engine sits on a hull, and which way it pushes
│   ├── gates.py        the Weave's ancient anchors: tolls, rings and chords
│   ├── models3d.py     meshes at radius 1, and `present`: which mesh a thing
│   │                   in the sky gets, and the attitude it is held at
│   ├── berths3d.py     a quay, a Fleet Hub, a holding and a Weave gate —
│   │                   one silhouette each, where there was one shipyard
│   ├── ships3d.py      and other people's ships by what they are doing:
│   │                   courier, trader, prospector, patrol, no transponder
│   ├── parts3d.py      a fitting's picture: the slot is the silhouette, the
│   │                   yard the colour, the tonnage the bulk — and a barrel,
│   │                   an emitter or a housing for what it does
│   ├── life3d.py       a xenoform's body, from the three things it is made
│   │                   of: the plan is the silhouette, the metabolism the
│   │                   colour, a trait a feature you can see — and `marks`
│   │                   says which traits a portrait cannot show
│   ├── robots3d.py     a body per machine class, built from its own card:
│   │                   duties give it arms, a rig, a dish or a pack; the
│   │                   autonomy rung gives it a sensor head or a relay mast;
│   │                   tonnage gives it bulk and level a second pair of hands
│   ├── robots.py       20 classes of machine across the same five yards,
│   │                   each rated on the ECSS autonomy ladder (E1 teleoperated
│   │                   … E4 goal-directed) — the number that decides where a
│   │                   machine is worth putting
│   ├── works3d.py      your own holdings: one structure per colony class,
│   │                   built out of what the class *does* — roots, a bell,
│   │                   a dish, a cradle, a womb, a drum — plus its berths
│   │                   and its size in km, which is the one door for how
│   │                   big anything you come alongside is
│   ├── hulls3d.py      the five hull families as silhouettes, built from
│   │                   `hullforms`' own lengths, beams, tapers and facet
│   │                   counts — what the tactical plot draws
│   ├── starclasses.py  8 spectral classes with real radii and luminosities —
│   │                   a 12 km neutron star to an A-type at 1.8 solar
│   ├── worlds3d.py     worlds by latitude: caps, bands, and concentric rings
│   ├── surfaces.py     and by longitude: named features, and a lattice of
│   │                   ground texture sized to whatever the frame holds
│   │                   (starclasses also carries each class's mass, which is
│   │                   what decides how fast its worlds go round)
│   └── lore.py         intro, victories, endings, name pools, glossary
├── world/              generated content
│   ├── galaxy.py       sector generation, lane relaxation, distance/transit
│   ├── planets.py      bodies, biomes, resource grades, survey resolution
│   └── economy.py      per-port supply/demand, prices, market drift
├── sim/                game rules — never import Qt
│   ├── ship.py         Ship model, stats(), layer stack, cargo, repair
│   ├── shipyard.py     design validation, costing, build queue, refit
│   ├── combat.py       turn resolution, firing, damage, endings;
│   │                   `_run_seats` runs helm and engineering either way;
│   │                   `cook()` holds heat under `HEAT_CEILING`
│   ├── battle_state.py the Side and Battle shapes, shared by resolver/AI/UI;
│   │                   ENDINGS and `finish()` — the one door an engagement
│   │                   ends through, for combat, parley and prize alike
│   ├── prize.py        striking colours: a beaten crew gives up, and the
│   │                   captain decides once — prize crew, strip, or release
│   ├── tactical.py     the plane: positions, headings, firing arcs, bands
│   ├── stations.py     helm / gunnery / engineering: the seats and their acts
│   ├── turnplan.py     and the forecast of a turn that contains one — the
│   │                   seats you are not in included, since they run
│   │                   themselves, and the helm flown on a copy of the hull
│   ├── enemy_ai.py     how the other side fights — same geometry, no cheating
│   ├── abilities.py    defensive abilities, returning their own log lines
│   ├── colony.py       founding, daily yields, aggregate colony effects
│   ├── research.py     project selection and point accrual
│   ├── crew.py         officers, recruitment, experience, morale
│   ├── encounters.py   NPC generation and transit events
│   ├── threat.py       Bloom growth and spread, cleansing, victory checks
│   ├── xeno.py         study points, incorporation, alien passive bonuses
│   ├── biology.py      what your own biology explains on the ground
│   ├── bloom.py        stages, roaming instars, resistance, the First Instar
│   ├── contracts.py    generation, acceptance, progress, expiry
│   ├── diplomacy.py    standing, the relations matrix, treaties, brokering;
│   │                   every gift priced through `allegiance`
│   ├── expedition.py   the ground game: zone map, movement, attempts, hauls
│   │                   — `step_cost` is the one door for what a step spends
│   ├── reach.py        what you can get to at all, and what a drive would open
│   ├── plans.py        the ship as solids: hull, fittings, hold, berths;
│   │                   `scar()` marks the blight a hurt hull shows
│   ├── beginning.py    turning an opening choice into a chronicle
│   ├── legacy.py       life after an ending: epochs, pressure, situations
│   ├── telemetry.py    what the instrument windows read, band by band
│   ├── memory.py       minds: what everyone remembers about you
│   ├── grudge.py       what a power's memory costs you, and why
│   ├── voice.py        speech, written by the game or by a model
│   ├── manual.py       resolves the manual's facts from the tables themselves
│   ├── options.py      player settings, every one of which does something
│   ├── tutorial.py     the curriculum's state machine: which lesson, what
│   │                   has been stepped over, and jumping to a course
│   ├── tutorial_watch.py what it watches: the mark, every watcher, and
│   │                   `deed` — how a sim function records an act that
│   │                   leaves no state behind
│   ├── fieldwork.py    everything done off the ship — digs, analysis, landings
│   ├── assessment.py   reading an engagement: who wins, why, what to do
│   ├── chains.py       commissions: work that escalates and closes doors
│   ├── inquiry.py      evidence, approaches, setbacks and breakthroughs
│   ├── intel.py        how well a system is known, and what a chart is worth
│   ├── loading.py      fitted mass against what the hull is rated to shift
│   ├── orders.py       which standing orders apply — the discoverability index
│   ├── wayhome.py      the cheapest known walk back to the lander, in days of
│   │                   supply, and whether the party can afford it
│   ├── parley.py       breaking off and talking your way out: the odds, what
│   │                   each part of them is worth, the turn a refusal costs
│   │                   (a held flee strains and pays the same turn)
│   ├── transit.py      standing the watches of a crossing
│   ├── programmes.py   what the bench runs once a branch is exhausted, and
│   │                   what a finding buys: standing, money, or nothing
│   ├── conn.py         the last ten kilometres: a local frame, thrusters and
│   │                   the main drive, and what a contact costs. The pilot's
│   │                   side — the console and what a burn is allowed to do
│   ├── conn_open.py    opening one: `start` and `observe`, the only places
│   │                   that read the whole game — cargo for the tank, engines
│   │                   for the thrust, star for the light, system for the
│   │                   sky — and hand back a flight. Re-exported from conn.py
│   ├── telepresence.py the law of the delay: how far a machine is (`gap_au`),
│   │                  how much of its level survives the round trip
│   │                  (`grip`), the two multiplied (`effective`), and what a
│   │                  posted machine wards. A leaf — it takes the roster
│   │                  lazily, so `sim/robots` imports it and not the reverse
│   ├── hostiles.py     the hulls the captain has called enemies. Stored,
│   │                  because a Contact is rebuilt every call; read in one
│   │                  place, `traffic.in_system`, where the errand's answer
│   │                  and the captain's mark meet
│   ├── tug.py          the boats: whether a structure keeps them, whether they
│   │                  have a line on you, and what a tow costs (nothing).
│   │                  The other side of clearance — what a quay does for a
│   │                  hull it wants, where `control` is what it does about
│   │                  one it does not
│   ├── conn_step.py    the other side: one tick of time, how far it carries
│   │                   her and what she touches on the way. Only `apply`
│   │                   calls in, and only `step`
│   ├── outcome.py      whether an approach is over — alongside, in orbit,
│   │                   aground or adrift. An orbit is a shape rather than a
│   │                   distance, which is why it is not decided in conn.py
│   ├── law.py          the record: charges, judgment debts and warrants, in
│   │                   one saved object. Nothing else may hold a Charge
│   ├── governance.py   **the one front door** — the clock calls this and it
│   │                   owns the order the six modules below run in
│   ├── dockets.py      being seen and being charged, and the difference:
│   │                   `witness` is how far a power's arm actually reaches
│   ├── tribunal.py     the hearing. `case` states the whole price and
│   │                   `plead` spends exactly it
│   ├── debts.py        money owed to somebody who can do something about not
│   │                   being paid; distraint happens at the till
│   ├── warrants.py     what a power will do to you and how far it follows —
│   │                   the Charter's arm is the shortest, the Freeholds' the
│   │                   longest, and that is the truest thing here
│   ├── enforce.py      where the law touches the ship: berths, rings,
│   │                   counters, licences, hails and patrols
│   ├── clemency.py     the way out — pay, buy the paper back, buy a
│   │                   harbourmaster, or sign a treaty
│   ├── orbits.py       what counts as an orbit, its size and roundness, the
│   │                   ladder of heights you can ask to hold, and
│   │                   `ship_orbit_offset` — where in the orbit it holds the
│   │                   hull actually sits, which is why a range to the thing
│   │                   you are standing at is not zero
│   ├── autopilot.py    the flight computer: one control law, three modes
│   ├── collision.py    what is in the way, how long there is, and whether
│   │                   she can still be stopped — the guard the computer
│   │                   and the hand both read
│   ├── detection.py    how far this array sees, and how well: worlds are
│   │                   unmissable, hulls are not, and a poor fix is read
│   │                   pessimistically rather than trusted
│   ├── flightdeck.py   the computer's one front door: `computer` (the
│   │                   dispatcher every beat asks) and `can_arm` (the gate
│   │                   every autopilot button greys on)
│   ├── attitude.py     pointing the hull, and what the swing costs
│   ├── thrusters.py    mass, thrust and slew rate from what is actually fitted
│   ├── burnplan.py     a transfer as a sequence of burns
│   ├── berthing.py     what an approach charges the chronicle when it ends
│   ├── instruments.py  the conn's panel, judged against what it is trying to
│   │                   do; `drive_note` is the one door for the main-drive
│   │                   label the three flying windows all print
│   ├── preview.py      what a burn will do before you make it: a throwaway
│   │                   twin of the ship, flown and reported on
│   ├── pilot.py        what the console is set to — the throttle ladder, the
│   │                   coast, and the one door a burn's cost comes through
│   ├── gunnery.py      which mounts speak this turn: the volley, what it costs
│   │                   the hull in heat, and the best set that will not fault
│   ├── targets.py      a body or a quay as something with a mu and a radius
│   ├── weave.py        the ancient anchors, their rings, and lighting a chain
│   ├── gates.py        transit through the Weave, and what the toll is
│   ├── dig.py          working a site stratum by stratum, banking as you go
│   ├── customs.py      the contraband run: the unposted price and the search
│   ├── allegiance.py   what serving a power costs you with its enemies
│   ├── territory.py    claims against holdings: trespass, levy, defiance
│   ├── charts.py       pricing a survey by what is actually in the system
│   ├── aftermath.py    what an engagement leaves behind: salvage and standing
│   ├── notes.py        field notes: filed, looked up again, and worth something
│   ├── trade.py        buying and selling over a counter, and survey data
│   ├── services.py     repairs, a paid word, and a fortnight of bench time
│   ├── freight.py      the freight desk: what is worth loading, and where
│   ├── responses.py    provocation, the Bloom's answers, and studying a mass
│   ├── market.py       supply shocks, and the prices you wrote down
│   ├── ventures.py     what the powers do on their own account
│   ├── fleets.py       what a power fields, and where. Hulls sit on its
│   │                  holdings, and — at war — on what `war.spoils`
│   │                  says it is trying to take (`FRONT_WEIGHT` 0.6).
│   │                  That is the only way two flags share a system.
│   ├── armada.py       the fleet action at a contested system. Frames a
│   │                  skirmish, resolves nothing — `combat` still owns
│   │                  gunfire. `balance` feeds `ventures.odds`, and your
│   │                  own hull is in it when you are present AND have
│   │                  taken a side (`Venture.stance`).
│   ├── war.py          who is at war with whom, derived from the relation
│   │                  matrix (`WAR_AT` = -60); `spoils` is what a
│   │                  belligerent may take. Taking a system in war
│   │                  moves `port.faction` as well as `system.faction`;
│   │                  annexing empty ground moves only the register.
│   ├── exchequer.py    the public purse: income, upkeep, building,
│   │                   retrenchment, and the stake a venture costs
│   ├── wharfage.py     the due on the captain's own trade, and whose purse
│   │                   it lands in — one door for the rate and for the act
│   ├── accord.py       what a signed treaty is worth: mutual berthing off
│   │                   the wharfage at their quays, and their charts of
│   │                   their own space — quoted before you sign, and the
│   │                   same instrument through either door into signing
│   ├── settlement.py   the powers put people on the ground, and the local
│   │                   market starts hearing about it
│   ├── industry.py     licensing a process to a power: their treasury pays,
│   │                   their berths start making the thing, its price falls
│   ├── weather.py      the front overhead during a landing
│   ├── mining.py       seams, depth, and how hard you work a body
│   ├── rumours.py      leads that point somewhere before you have been,
│   │                   and what the place you heard one is worth
│   ├── consorts.py     escorts: ordering one out of its berth, standing
│   │                   orders, screening, who draws fire, what they eat
```
