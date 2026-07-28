# INTERFACE.md — SEEDFALL navigation map

The top-level map of the game. Read this before opening any source file in
`seedfall/`.

## What this is

**SEEDFALL** is a native PyQt6 space exploration / trading / combat RPG built on
the GESTALT design programme in this repository — a modern Starflight with a
Civilization layer. You command a grown starship in the Verge, survey and trade,
fight or refuse to, research a fifty-eight-node tech tree, design hulls out of
grown organs and fabricated machinery, plant colonies, and deal with the Bloom.

The GESTALT documents supply one of the five technologies and all of the
physics: the grown hull classes from the Fleet Class Reference, the six-layer
hull from the Design Dossier, the phosphorus bottleneck and 9:1 ore ratio from
Metabolism, the wet/dry cyborg control stack from Nervous System, the cell types
from the Cell Atlas, and the reproduction-licence containment regime from the
Fleet Registry. The other four technologies exist so that the grown fleet has
something to be measured against.

**Combat is positional.** Ships carry a heading and a speed on a real plane.
The five range bands still exist — weapons are specified in them — but the band
is *derived* from an actual separation rather than stored, so closing is a
manoeuvre rather than a menu pick. Every mount has a firing arc (fore, broadside,
turret) and will refuse to fire outside it, which makes turning to bring a gun to
bear a real decision.

**And you can only sit in one seat.** Each turn you take one station personally —
Helm, Gunnery or Engineering — and your officers hold the other two at their own
level, which is competent and worse than you. Directed gunnery shoots markedly
better than automatic; engineering routes power, patches the outermost breach or
dumps heat; the helm decides what will bear next turn.

**The Bloom is an antagonist, not a timer.** Five named stages advanced by the
sector-wide burden: past Motile it keeps roaming instars in the field that prefer
your colonies to empty ground; past Adaptive it builds resistance (up to 55%) to
whatever weapon family you keep using, and forgets what you stop using. At
Kessel's Reach, found by surveying the origin system, is the First Instar — the
original husk with a Charter serial still on it. Containment requires the sector
clean *and* that husk dead, which takes about twenty burn passes from a
battleship.

**Diplomacy has two axes.** Your standing with each power, and how the powers
regard *each other* — a relations matrix that starts hostile in most pairs.
Tribute, intelligence and relief move the first; only brokering moves the second,
and brokering requires both parties to think well of you already. Concord needs
all four at Kin **and** all six pairs at peace, so it is a diplomatic achievement
rather than four grinds.

**Getting anywhere is a decision.** A jump drops you at the system edge, not
alongside anything. Bodies sit on real orbits that keep moving while you fly, so
the range to a target depends on when you leave. Four burn profiles trade
reaction mass against days — and *coasting is always free*, which is what stops
an empty tank from becoming a deadlock. Local work (survey, extract, dig, land)
flies the ship alongside first, so a player who never opens the helm still gets a
coherent transit; the helm is where you choose a better one.

**Two mini-games.** The **docking approach** is the control loop from the
nervous-system study — sense, compute, act, hold homeostasis — with three drifting
axes, one correction per pass, and readings blurred by how good your sensors are.
A clean approach earns standing; a botched one buys a tug. The **decoding bench**
takes a recording of something that was not speaking to you: four positions, a
hidden pattern, and feedback that tells you how many glyphs are exactly right and
how many are merely present, never which. Solving one is worth alien
understanding, and costs nothing but attempts.

**There is a game on the ground.** Landing a party opens a 7×7 zone map revealed
one tile at a time. Moving costs days of supply (known ground is cheap to
re-cross, which is what makes coming home survivable); terrain springs hazards
that officers' skills mitigate; site features offer choices resolved against a
named stat. Nothing is banked until the party is back on the lander, and running
out of supply in the field costs most of the haul. How much biomass you commit at
launch buys how long they can stay.

**Contracts are optional work with deadlines.** Six kinds, posted per port and
scaled by distance. They are checked on the clock and complete the moment their
terms are met rather than when you remember to hand them in. Nothing in the game
requires taking one — the five endings are open from turn one.

**Alien technology is a separate progression from research.** Four cultures —
the Abyssals, the Ossuary, the Weft and the Tessellate — left twelve
technologies scattered across the sector as buried sites. None can be reasoned
out. Understanding accumulates in study points from four sources: excavating a
site, taking relics apart in a laboratory, buying somebody's field notes at a
port, and seizing them off a hull you destroy. At full understanding the
technology is *incorporated* — its id is appended to `research.unlocked`, so the
shipyard and codex treat it like anything else you know, and it never appears in
the research tree because you could not have derived it.

**Thirty-five hulls and nineteen stations across five families:**

| Family | Hulls | Character |
|---|--:|---|
| Grown | 12 | Gestated from a seed. Heals; eats phosphate; takes months. |
| Fabricated | 13 | Concordat of Yards. Welded in weeks, dear, and never mends. |
| Hybrid | 4 | Freehold grafts. Both bills, both gifts. |
| Synthetic | 4 | Dry Choir. Crewless, superb instruments, no self-repair. |
| Xeno | 2 | Not ours. It mends, and nobody has explained how. |

Which parts graft to which frame is `ACCEPTS` in `data/hull_types.py`: a grown
hull refuses a fusion lance, a Yards hull refuses an intima, a hybrid takes
either, and a synthetic frame takes fabricated and Dry Choir work but nothing
alive.

## Running

```
python -m seedfall                  # title screen
python -m seedfall --new            # straight into a new chronicle
python -m seedfall --seed verge-7   # a specific sector
python -m seedfall.tests            # simulation + interface suites
python -m seedfall.tests sim        # one suite
```

Requires **PyQt6** (`pip install PyQt6`). Nothing else — no network, no server,
no browser. Saves live in `~/.seedfall/save.json`.

## Layout

```
seedfall/
├── __main__.py         entry point: python -m seedfall
├── core/               engine primitives — no game rules, no Qt
│   ├── rng.py          seeded mulberry32 + pick/weighted/gauss/shuffle helpers
│   ├── util.py         formatting (credits, mass, stardate, duration) and clamp
│   ├── save.py         generic dataclass ⇄ JSON codec, @register, atomic write
│   └── state.py        the Game object, advance_days(), new_game(), load_game()
├── data/               static content tables — pure data, no logic
│   ├── commodities.py  14 tradeable goods
│   ├── chassis.py      the hull registry — assembles and re-exports the rest
│   ├── hull_types.py   layer stacks, the Chassis record, family rules (ACCEPTS)
│   ├── hulls_grown.py  the 12 GESTALT classes
│   ├── hulls_built.py  13 fabricated · 4 hybrid · 4 synthetic · 2 xeno
│   ├── part_types.py   Part / Weapon / Ability shapes, slots, range bands
│   ├── modules.py      drives, power, sensors, compute, utility organs
│   ├── armaments.py    weapons and defences
│   ├── parts.py        merged registry over modules + armaments
│   ├── tech.py         61-node research tree, 10 branches, 5 tiers
│   ├── colonies.py     19 colony and station classes
│   ├── factions.py     6 powers + reputation bands
│   ├── lifeforms.py    xenobiology generation tables + anomalies
│   └── lore.py         intro, victories, endings, name pools, glossary
├── world/              generated content
│   ├── galaxy.py       sector generation, lane relaxation, distance/transit
│   ├── planets.py      bodies, biomes, resource grades, survey resolution
│   └── economy.py      per-port supply/demand, prices, market drift
├── sim/                game rules — never import Qt
│   ├── ship.py         Ship model, stats(), layer stack, cargo, repair
│   ├── shipyard.py     design validation, costing, build queue, refit
│   ├── combat.py       turn resolution, firing, damage, endings
│   ├── battle_state.py the Side and Battle shapes, shared by resolver/AI/UI
│   ├── tactical.py     the plane: positions, headings, firing arcs, bands
│   ├── stations.py     helm / gunnery / engineering orders
│   ├── enemy_ai.py     how the other side fights — same geometry, no cheating
│   ├── abilities.py    defensive abilities, returning their own log lines
│   ├── colony.py       founding, daily yields, aggregate colony effects
│   ├── research.py     project selection and point accrual
│   ├── crew.py         officers, recruitment, experience, morale
│   ├── encounters.py   NPC generation and transit events
│   ├── threat.py       Bloom growth and spread, cleansing, victory checks
│   ├── xeno.py         study points, incorporation, alien passive bonuses
│   ├── bloom.py        stages, roaming instars, resistance, the First Instar
│   ├── contracts.py    generation, acceptance, progress, expiry
│   ├── diplomacy.py    standing, the relations matrix, treaties, brokering
│   ├── expedition.py   the ground game: zone map, movement, attempts, hauls
│   ├── fieldwork.py    everything done off the ship — digs, analysis, landings
│   ├── assessment.py   reading an engagement: who wins, why, what to do
│   ├── chains.py       commissions: work that escalates and closes doors
│   ├── inquiry.py      evidence, approaches, setbacks and breakthroughs
│   ├── intel.py        how well a system is known, and what a chart is worth
│   ├── loading.py      fitted mass against what the hull is rated to shift
│   ├── orders.py       which standing orders apply — the discoverability index
│   ├── parley.py       breaking off and talking your way out
│   ├── market.py       supply shocks, and the prices you wrote down
│   ├── ventures.py     what the powers do on their own account
│   ├── weather.py      the front overhead during a landing
│   ├── mining.py       seams, depth, and how hard you work a body
│   ├── rumours.py      leads that point somewhere before you have been
│   ├── consorts.py     escorts: standing orders, screening, who draws fire
│   ├── loyalty.py      what the bridge thinks of how you run the ship
│   ├── works.py        colony development: what a settlement becomes
│   ├── flight.py       the helm: orbits, intercepts, routing, transfer burns
│   ├── minigames.py    the docking control loop and the decoding bench
│   └── actions.py      player actions spanning modules (jump/survey/mine/dive)
├── ui/                 PyQt6 presentation — never mutates state directly
│   ├── theme.py        palette, fonts, the global stylesheet
│   ├── widgets.py      Panel, Card, Bar, Pill, TabBar and the View base class
│   ├── window.py       MainWindow: hud, nav rail, view stack, log, dialogs
│   ├── title.py        title screen and the opening briefing
│   ├── app.py          QApplication bootstrap
│   ├── map_view.py     custom-painted sector chart and jump control
│   ├── system_view.py  bodies, survey, extraction, diving, colonising
│   ├── port_view.py    market, services, recruitment
│   ├── ship_view.py    layer stack, fittings, crew, hold
│   ├── yard_view.py    hull designer, build queue, fleet management
│   ├── tech_view.py    research tree
│   ├── empire_view.py  colonies, depot, victory progress, waiting
│   ├── codex_view.py   class reference, powers, glossary, about
│   ├── xeno_view.py    the xenology desk (hosted as a Research tab)
│   ├── expedition_view.py  the landing zone: fogged map, party, field log
│   ├── diplomacy_view.py   relations matrix and the overture desk
│   ├── helm_view.py    orbit chart and burn planner
│   ├── minigame_view.py    docking approach and decoding bench
│   └── battle_view.py  combat screen and post-engagement resolution
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
    ├── test_explore.py 8 exploration checks — the intel ladder, rumours
    ├── test_mining.py  7 mining checks — seams, methods, wear, exhaustion
    ├── test_research.py 8 research checks — evidence, approaches, setbacks
    ├── test_trade.py   8 trade checks — shocks, the register, staleness
    ├── test_ground.py  7 ground checks — weather, sight, being pinned
    ├── test_politics.py 8 politics checks — ventures, sides, the Concord
    ├── test_design.py  6 design checks — loading, overloading, stranding
    ├── test_orders.py  8 orders checks — reachability, urgency, unread state
    ├── test_assessment.py 6 read checks — honesty, arcs, robustness
    ├── test_balance.py 7 balance checks — measured by playing the fights
    ├── test_verbs.py   7 verb checks — every control in the game, clicked
    ├── test_flight.py  5 helm checks — determinism, intercepts, routing
    └── test_ui.py      22 interface checks, rendered on Qt's offscreen platform
```

## How the layers connect

The dependency rule is one-directional and worth preserving:

```
data/  ──►  world/  ──►  sim/  ──►  ui/  ──►  __main__
                    core/ is available to everything
```

- **`core/state.Game` owns time.** `advance_days(n)` is the only clock: it ticks
  research, colonies, build slips, hull regrowth, every market, payroll, air,
  morale and the Bloom, then checks for victory. Nothing else advances a day.
- **`sim/` never imports Qt.** It takes a `game` and returns plain data. That is
  why the simulation suite can run headless and why the whole rules layer is
  testable without a display.
- **`ui/` never mutates state directly** — a view calls a `sim/` function, then
  `win.refresh()`, which recomputes derived values and redraws.
- **`ship.stats()` is the single source of derived numbers.** Chassis base +
  fitted parts + research bonuses + officer skills, with a power-brownout
  multiplier. Anything asking "how far can this ship jump" asks `stats()`.
- **Views subclass `ui.widgets.View`** and implement `build()`; the base class
  clears and rebuilds the column on every refresh. Simple and fast enough — a
  full screen is a few hundred widgets.

## The parts that will bite you

- **`HULL_SCALE` in `sim/ship.py`** converts the descriptive `hull` figures in
  `data/chassis.py` into combat hit points. Chassis numbers are written to read
  sensibly against each other; this constant tunes fight length. Change it and
  every engagement in the game changes.
- **`MAX_LANE` in `world/galaxy.py`** guarantees no star sits further from its
  nearest neighbour than a starting hull can jump. Without the relaxation pass
  that enforces it, some seeds strand the player on turn one.
- **`GRIND_TURN` / `MAX_TURNS` in `sim/combat.py`** stop two well-armoured hulls
  grinding forever. Armour is also floored at 15% damage leak-through for the
  same reason.
- **Driving a fight with one repeated order measures nothing.** Combat is
  positional: a hull whose mounts are all on the beam never fires while it
  steers straight at the enemy, so a test that only ever says "salvo" reports
  zero damage and looks like a balance problem. Use `tests/captain_ai.py`,
  which picks the helm order that suits the arcs the ship actually carries.
- **A consort is a `Side`.** `sim/consorts.py` subclasses it, so `_fire`,
  `_apply_to_layers` and the arc checks work on one without changes. What that
  buys is also the constraint: anything that assumes a battle has exactly two
  sides — `_who()` did — has to learn otherwise.
- **Save identity**: `game.ship` must be the same object as its entry in
  `game.fleet`. `load_game()` re-links them after decoding; damage would
  otherwise apply to a copy.
- **Transient fields**: anything on a dataclass marked
  `metadata={"transient": True}` is skipped by the save codec. `Game.ship_stats`
  holds references to the content tables and must never be written to a save.
- **Qt mnemonics**: an `&` in a button label becomes an accelerator underscore.
  Write "and".
- **Never derive anything persistent from `hash()`.** Python randomises string
  hashing per process, so a value derived from it changes on every launch.
  Orbital phases did exactly this, and a saved game reloaded with every planet
  somewhere new. Use `core.rng.hash_seed`.
- **`View._sync_scroll()` is why screens paint correctly on the first frame.**
  Rebuilding a view's column does not tell its `QScrollArea` that the contents
  changed size, and the layout's true minimum is not known until the new
  widgets are polished — so it measures once immediately and once more after
  the event loop settles. Qt recovered on its own by the second turn, which
  made the fault invisible in play and very visible in a screenshot.
- **Adding a hull family** means touching six places: `LAYER_SETS`, `ACCEPTS`,
  `FAMILY_LABEL`/`FAMILY_TINT`/`FAMILY_NOTE`, `BASE_POWER`, `BUILD_NEED`, and
  `NO_REGEN` if it cannot heal — all of them in `data/hull_types.py`. The test
  suite checks every family for all six, and that its layer weights sum to one.
- **Xenotech ids live in `research.unlocked` alongside real technologies.**
  Anything walking that list must tolerate ids that are not in `TECH_BY_ID` —
  `tech.bonuses()` already skips them, and the gate check in `test_sim.py`
  accepts either vocabulary. Alien passive bonuses are folded in separately by
  `Game.recompute()`.
- **Study banked past a prerequisite is kept, not lost.** You can dig up the
  Phase Loom before you understand the Null Seam; `xeno.settle()` runs on the
  clock and incorporates anything whose moment has arrived.
- **A colony's numbers come from `sim/works.py`, not its class.** `yields_of`,
  `upkeep_of`, `effects_of` and `pop_ceiling` combine the class definition with
  whatever the settlement has since built. Read `col.definition.yields`
  directly and you will report what the colony produced the day it was planted.
- **Anything a work grants that needs an action, not just a number, has to be
  triggered where the work completes.** Opening a harbour was read only at
  maturation, so a colony that built one afterwards had the `port` effect and
  no market.
- **A conviction that reacts to an event nothing raises is dead flavour.**
  `data/convictions.py` names events; something in `sim/` or `ui/` has to call
  `loyalty.record()` with that exact string or the belief never fires. A check
  in `test_crew.py` greps the tree and fails on any event that is never raised
  — it caught ten of them on the day the system was written, including every
  belief the xenologist held.
- **Loyalty bands and loyalty mechanics share their edges.** `BANDS` in
  `data/convictions.py` turns on `WALKOUT` and `RESTLESS`, the same constants
  `effective_level()` uses, so the pill on the roster is a statement about what
  the officer will actually do. Move one and move the other.
- **A commission stage is an ordinary contract.** `sim/chains.py` builds one
  through `contracts.shape()`, the same function the board uses, so deadlines,
  cargo, bounties and expeditions all work untouched. What makes it a chain is
  `Contract.chain` and what happens in `chains.on_contract_done()`.
- **`contracts.active()` is board work only.** Commission stages are excluded
  from it and from the `MAX_ACTIVE` cap, because they are not work you chose to
  juggle. Use `contracts.all_open()` when you genuinely mean everything live.
- **`shape()` takes its scale before it writes the title.** A stage that asked
  for half the usual tonnage used to be titled with the full figure and
  complete at the halved one — a posting nobody could plan a hold around.
- **`rumours.circulating()` must stay pure.** It runs every time the port desk
  is drawn. Deciding truth used to plant what the story claimed, which seeded
  bloom and buried relics across the sector merely because somebody looked at a
  noticeboard. Truth is now a dice roll at circulation; `plant()` runs in
  `take()`, when you have actually committed to the lead.
- **Intel levels are derived, never stored.** `intel.level()` reads
  `body.surveyed`, `system.visited` and the bought-chart list, so nothing has
  to be kept in step. Add a way to learn about a system and it belongs in that
  function.
- **Volatiles are never buried below an open cut, and neither is whatever a
  body is advertised as.** `mining._depth_of()` enforces both. Fuel at depth
  two strands a captain with no bore and no reaction mass — the same deadlock
  the mining root's `drink` was added to prevent — and a rock listed as
  ore-bearing that needs a shaft is a survey that lied.
- **Seams are derived from `body.resources`, never stored.** Depth comes from
  `hash_seed` of the body and resource, so every existing save has seams
  without a migration and the same rock always hides the same thing in the same
  place. Never use `hash()` here; see the note above about orbits.
- **`STARVED_FLOOR` is why a new captain is not stuck.** A programme runs at
  that fraction with nothing on the bench; evidence buys the rest. Set it to
  zero and a captain who picks a project on turn one and flies makes no
  progress at all, which reads as a broken game rather than a hungry one.
- **A programme's evidence mix comes from its branch**, in
  `data/inquiry.BRANCH_MIX`, not from each of the sixty-one technologies. A new
  technology needs no work there; a new *branch* does, and `test_research.py`
  fails if one is missing.
- **An evidence kind nothing grants is an empty locker.** The same greping
  check as the convictions: every kind in `EVIDENCE` must appear as a literal
  in a `sim/` or `ui/` call to `inquiry.add`.
- **`Stock.shock` is kept apart from `Stock.supply` on purpose.** The daily
  drift pulls supply toward equilibrium; if a blight were folded into supply
  the drift would quietly erase it, and expiring it could never restore the
  original price. `market.apply_to_markets()` recomputes every row from the
  live shocks wholesale rather than adjusting, so an expired shock lifts
  cleanly and two overlapping ones cannot drift out of step.
- **The register is memory, not observation.** `market.note_prices()` writes
  down what a port pays only while you are standing in it, and
  `market.confidence()` decays what you wrote. Nothing should ever read a
  distant market directly — that is the whole mechanic.
- **A weather condition gated on a biome that does not exist is unreachable.**
  `data/weather.py` gates whiteouts and downpours on biome ids, and those must
  be real ones from `world/planets` — the first draft invented "ice" and
  "ocean" and silently lost two of its seven conditions. `test_ground.py`
  checks every gate against a real galaxy.
- **Anything that stops the party moving must leave something it can do.**
  A katabatic gale refuses movement, so `expedition.shelter()` is always
  available and always costs a day of supply. Without it a pinned party can
  neither progress nor die and the expedition simply stops.
- **`diplomacy.drift()` is what stops the sector ratcheting shut.** Every
  blockade and censure is a debit; with nothing pulling the other way a decade
  of background politics drove every pair far below `CONCORD_RELATION` and left
  an ending unreachable through no fault of the player. Grievances fade toward
  `INITIAL_RELATIONS`. Any new faction behaviour that moves relations needs to
  be weighed against it.
- **Ventures never annex a system you hold a colony in.** `_claimable()`
  excludes them. Losing a settlement to a registry filing would be good drama
  and would also silently break the colony that is still pointing at it.
- **Never size anything against `chassis.mass_t`.** Structural mass runs from a
  sixty-tonne SPORE to a twelve-billion-tonne LEVIATHAN, so any threshold built
  on it is meaningless for most of the range. `sim/loading.py` sizes capacity
  from slot count and hold rating, which are on the same scale as the parts and
  cargo that fill them.
- **Loading affects jump range at 45% strength, deliberately.** A full hold
  costing speed is a trade; a full hold leaving a captain unable to reach the
  nearest system is the stranding deadlock this project has hit twice.
  `test_design.py` checks the laden jump against the nearest neighbour.
- **A new system is not finished until `data/orders.py` can point at it.**
  Fifteen cycles each added something perfectly discoverable to whoever had
  just built it; a new captain saw a chart, one log line, and no sign any of it
  existed. Every entry there needs a predicate of the same id in
  `sim/orders.py`, and `test_orders.py` fails on either half being missing.
- **Anything persistent on `Game` needs a reader.** `test_orders.py` walks the
  dataclass fields and fails on any that nothing loads — it caught a levy
  counter that incremented and changed nothing, and a death reason the game
  recorded and never showed.
- **Never compare combatants by raw hull and raw damage.** Enemy hull is a
  chassis lottery that does not track difficulty at all — `make_enemy` picks
  from a faction pool and scales hull only 10% per difficulty point — while
  armament and armour both track it cleanly. `assessment.weight()` compares
  turns-to-break after armour, and its thresholds are calibrated against 320
  measured fights rather than guessed.
- **Most fights end when somebody's nerve goes, not their hull.** Any model of
  who is winning that ignores resolve reads far bleaker than the game plays,
  which is why the thresholds sit where they do rather than at the obvious 1.0.
- **Build a fresh hull for every fight in a balance measurement.** Reusing one
  ship across a run silently starts every fight after the first with a wreck.
  It reads as "encounters are brutally hard" and sent an entire afternoon's
  tuning the wrong way before the artefact was spotted.
- **Nerve is driven by the fight, not the clock.** `_end_of_turn` once drained
  resolve purely on the turn counter, and the enemy lost it twice as fast as
  the player, so an unarmed hull drove off a battleship three times in four by
  waiting. It now turns on damage taken, being behind on damage, and futility —
  that last term is what keeps endurance a real strategy for a hull built to be
  hit.
- **Every low-tier weapon in the game is grown-family.** A fabricated hull at
  tier one can mount none of them, which is why faction warships used to arrive
  unarmed. `encounters._weapon_pool` raises the tier until something fits.
- **Qt swallows exceptions raised inside a slot.** It prints a traceback to
  stderr and carries on, so `button.click()` returns perfectly happily and a
  test that only clicks sees nothing wrong. This is why fleeing and hailing
  could be broken for a whole cycle while `test_ui.py` rendered every screen
  and passed. `test_verbs.py` installs a `sys.excepthook` to catch them; if
  that trap ever stops working every verb check goes quietly green, so there is
  a check for the trap itself.
- **Rendering a screen does not press its buttons.** `test_ui.py` proves the
  screens draw; `test_verbs.py` proves the verbs run. They are different
  claims and a refactor can break the second without touching the first.
- **Colony effects are a closed vocabulary.** `test_sim.py` asserts that every
  key in a `ColonyClass.effects` is one the game actually reads, so a typo in a
  station definition fails the suite instead of silently doing nothing.

## Tests

`python -m seedfall.tests` — no dependencies beyond PyQt6 itself.

- **`test_sim.py`** drives the rules headlessly: sector generation and
  determinism, every chassis and part, tech-tree reachability, trade, colonies,
  building, combat outcome distributions, Bloom pacing, save round-trip.
- **`test_combat.py`** covers arcs and crew stations, and holds the consorts to
  the bargain their orders describe: screening must measurably pull fire off
  the flag, and flankers must shoot markedly more than screens do.
- **`test_empire.py`** plants a colony, matures it and develops it: that a
  finished work changes production, that its effects reach ward, build sites
  and sensors, that material is charged up front, and that works survive a
  save.
- **`test_crew.py`** checks that the same act pulls a bridge apart rather than
  together, that loyalty is felt at the crew stations and not only on a roster,
  and that a year of missed payroll actually costs you officers.
- **`test_missions.py`** runs a commission to its end, and checks the three
  things that make one different from a posting: that stages escalate, that
  taking one is refused at its rival's own port, and that a missed deadline
  withdraws it permanently.
- **`test_explore.py`** climbs the intel ladder rung by rung, checks a chart
  cannot be bought twice or a survey sold twice, and — the important one —
  proves that thirty passes over the rumour desk leave the galaxy byte for byte
  unchanged.
- **`test_mining.py`** measures the four methods against each other over
  twenty runs apiece and asserts they are actually different bargains — a bore
  must out-yield an open cut by a third and cost more hull and more of the body
  doing it — then works a body out and checks it stops paying.
- **`test_research.py`** measures a captain who surveys against one who does
  not — the second must reach the first technology in well under three quarters
  the time, or the evidence model is decoration — and checks that a captain who
  picks a project on turn one and does nothing else still gets there.
- **`test_trade.py`** puts a shock on a market, checks the price moves, then
  expires it and checks the price comes back — the failure mode being a sector
  that accumulates permanent distortions over a long game. It also formats
  every shock's text to catch an unfilled field, which would otherwise crash a
  port screen months into somebody's game.
- **`test_ground.py`** pins a party under a gale and shelters until the
  expedition ends, which is the check that a stuck state cannot exist. It also
  measures tiles crossed with and without weather, so a condition that costs
  nothing fails.
- **`test_politics.py`** checks that a determined broker can still reach the
  Concord against twenty-five years of background churn, and — because the
  emergent numbers plateau against the -100 floor either way and make a weak
  signal — tests the fading mechanism directly by pushing a relation down and
  watching it come back.
- **`test_design.py`** builds every chassis at a sensible fit and fails if any
  is penalised for it, then maxes one out and fails if it is not. It also
  checks that a fully laden starting hull can still reach its nearest
  neighbour.
- **`test_orders.py`** builds ten game states and demands every standing order
  fire in at least one of them, calls every predicate unguarded so a broken one
  cannot hide behind the panel's exception guard, and checks that acting on an
  order makes it go quiet.
- **`test_assessment.py`** plays out forty fights across two hulls and four
  difficulties and fails if a worse-sounding verdict wins more often than a
  better-sounding one — the read is worth nothing if it is not honest. It fails
  against the raw-hull comparison the first draft used.
- **`test_balance.py`** plays out every assertion it makes. It checks no
  faction fields an unarmed warship, that heavier threats arrive in heavier
  hulls, that the win rate falls with difficulty and rises with a better ship,
  that waiting is not a way to beat a battleship, and that fleeing and hailing
  both actually run — the last because splitting them into `parley.py` left
  them calling names that no longer existed and nothing drove either path.
- **`test_verbs.py`** clicks every enabled control in the game — 210 of them
  across the standing screens, an engagement, an expedition, all four port
  tabs and both mini-games — each on a fresh game, and again with a wrecked
  hull that has no money, no crew and no air. It fails against last cycle's
  parley regression, which is what it was written for.
- **`test_flight.py`** holds the helm to its promises: that a seed grows one
  fixed set of orbits *in every process*, that a transfer aims where a body
  will be rather than where it is, that the intercept solve converges, and that
  no course is plotted through a star.
- **`test_ui.py`** builds the real `MainWindow` on Qt's `offscreen` platform and
  paints every screen and every tab, including a live engagement. It stubs
  `win.dialog` because `QDialog.exec()` would block. One check builds its own
  window: grabbing a widget forces a layout pass, so a check for first-frame
  layout cannot reuse one every earlier check has already painted.
