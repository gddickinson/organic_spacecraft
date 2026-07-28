# SESSION_LOG.md — GESTALT project

Running progress log. Newest first.

## 2026-07-28 — SEEDFALL: knowing where you are going

- **Discovery was one boolean.** A system was visited or it was not. It now
  climbs four rungs — **Catalogued** (a name and a position the registry will
  not stand behind), **Scanned** (read at range or bought as a chart),
  **Visited**, and **Charted** (every body surveyed). The map draws all four
  differently: an outline, a faded disc, a solid one, and a dotted ring around
  anything complete.
- **Charts can be bought, and surveys sold.** You can pay a broker for a scan
  rather than flying out to make your own, and a *complete* survey — every body
  in a system, not the interesting ones — sells once, to anybody. That is the
  reason to go back to somewhere you have already been.
- **Rumours point somewhere before you go.** Five kinds circulate at ports:
  buried relics, rich seams, unlicensed growth, lost hulls, and systems people
  are odd about. Pay to be told properly or just listen and risk them shutting
  up. Arriving settles the story either way.
- **A true rumour plants what it claims.** My first version tested the story
  against whatever the galaxy had already generated, and measured 0% true on
  the first three rolls — the conditions almost never held, which made the
  whole feature worthless. A true rumour now buries the relic, seeds the
  growth, enriches the seam. Measured over 90: 73% come good.
- **That fix created a much worse bug, which I caught before it shipped.**
  Planting inside the truth test meant `circulating()` mutated the sector — and
  it runs every time the port desk is drawn. Merely *looking* at a noticeboard
  seeded bloom and buried relics across the galaxy. Truth is now a pure dice
  roll; the planting happens in `take()`, when you have committed. The
  regression check runs thirty passes over the desk and demands the galaxy come
  back identical.
- **Two smaller things from the screenshots.** The map legend still described a
  two-state world, and a port offered "Nobody goes there" three times running,
  which reads like a broken generator rather than a rumour mill — one of each
  kind per port now.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, **8 exploration** (new), 23 interface — 107
  checks green. 104 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: work that leads somewhere

- **Contracts were a shopping list.** Independent jobs off a board — haul this,
  kill that, survey there — and nothing followed from finishing one.
  **Commissions** are four chains of three stages each, from the Charter, the
  Freeholds, the Dry Choir and the Concordat, where each stage escalates and
  the last one pays properly.
- **A stage is an ordinary contract.** `sim/chains.py` builds one through
  `contracts.shape()` — the same function the board uses — so deadlines, cargo,
  bounties and expeditions needed no changes at all. What makes it a chain is a
  `chain` field on the contract and what happens when it completes.
- **They close doors.** The Charter's assay office and the Freeholds' sluice
  are the same seam seen from two sides; taking either refuses the other, and
  the refusal holds at the rival's own port. Missing a deadline withdraws the
  commission for good rather than merely failing a job.
- **They land on the crew.** Finishing one raises loyalty for the officers
  whose convictions it served, so a career of Charter work and a career of
  Freehold work leave you with a different bridge.
- **Two bugs found by playing it.** A stage that asked for half the usual
  tonnage was titled with the *full* figure and completed at the halved one —
  "carry 62 t" that finished at 31 — because the scale was applied after the
  title was written. And a commission stage was sitting on the ordinary board,
  showing twice and eating one of the six contract slots; it is now held apart
  from both.
- **One refactor worth noting.** Pulling the per-kind contract shaping out of
  `generate()` so chains could reuse it was the whole reason this cycle stayed
  small. My first attempt at that extraction was a mechanical dedent that broke
  the file; doing it deliberately with the block in front of me took two
  minutes and worked. `port_view.py` crossed 500 lines on the way and the
  berths tab became `ui/berths_panel.py`.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, **7 missions** (new), 23 interface — 99 checks green.
  99 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a bridge with opinions

- **Officers were stat blocks with wages.** They modified rolls, gained levels,
  and never wanted anything or noticed anything. Each one now signs on with a
  **conviction** — believes in the licence, wants the Bloom burned, thinks it
  should be studied, Freehold to the bone, wants something left behind, in it
  for the money, loyal to the hull — and a **loyalty** that moves with what the
  ship actually does.
- **The same act reads differently from three seats.** Burning a Bloom system
  is a good day's work to a veteran of Kessel's Reach and a lost library to a
  xenologist; a treaty with the Charter costs you both Freeholders on the
  bridge. Measured across four convictions and four events, they end 38 points
  apart.
- **Loyalty is felt at the stations, not on a roster screen.** `officer_level()`
  — the number the helm, gunnery and engineering seats read — now returns the
  level an officer is *working* at: 1.2× when devoted, 0.72× when restless,
  0.45× when mutinous. It plugs straight into the crew stations built in the
  combat cycle.
- **A year of missed payroll costs you the bridge**, first walkout in month
  eleven. Paying properly and keeping the hull whole ends a year at mean
  loyalty 84. Two port actions push back: a bonus, and shore leave that costs
  you a week of the calendar.
- **My first balance pass was wrong and the playtest showed it.** Loyalty drift
  toward ship morale was strong enough to flatten every officer onto the same
  number within a year — 76.4, 76.4, 76.4 — which threw the convictions away
  entirely. Drift is now a fifth as strong: what you did has to outweigh the
  ambient weather.
- **A check that greps the source found ten dead beliefs.** Convictions name
  the events they react to, and nothing was raising `xeno_study`,
  `xeno_incorporated`, `first_contact`, `bloom_cleansed`, `bloom_spread`,
  `colony_lost`, `crew_death`, `trade_profit` or `repair` — the xenologist's
  entire belief set among them. All now hooked at real sites.
- **Two smaller fixes.** The display bands were named on their own scale, so an
  officer reading "Mutinous" was mechanically merely restless; they now turn on
  the same constants the mechanics do. And the starting bridge drew names at
  random from a list of 27, which put two officers with the same first name on
  the same bridge about one game in ten — I got three Mareks on the first run.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, **7 crew** (new), 23 interface — 92 checks green. 94 modules, all
  under 500 lines.

## 2026-07-27 — SEEDFALL: colonies that keep growing

- **A colony was a purchase, not a place.** Plant it, wait out the gestation,
  and it emitted the same numbers forever; the only thing that could ever
  change was starving to death when upkeep went unpaid. Colonies now undertake
  **works** — commitments of material and time that change what the settlement
  *is*.
- **Eight works, one at a time, four to a colony.** Deepen the workings (ore
  ×1.7, and it costs more to run), raise a garrison, lay a slipway, erect a
  sensor mast, ring the habitat, build a xenology annex, open a free harbour,
  sink a lineage vault. Some are gated on family or research, some only offered
  to colonies that already produce the right thing. Material is charged up
  front, which is the point: it is the reason to fly ore somewhere rather than
  sell it.
- **Everything reads through one layer.** `sim/works.py` combines the class
  definition with the finished works, so ward, build sites, sensors, diplomacy
  and population all feel a work without anything else knowing works exist.
  Verified end to end: garrison 0.00 → 0.28 ward, slipway opens a build site,
  mast adds 2 ly of sensor.
- **A bug I predicted, then confirmed, then fixed.** The `port` effect was only
  read when a colony matured, so a harbour *built later* granted the effect and
  opened no market — the system stayed portless. Now handled where the work
  completes. The regression check fails without the fix.
- **A layout fault the screenshot caught.** Panels sit side by side and are
  given equal height; the shorter one had its rows dragged apart to fill the
  space. In the first render of the new empire screen the colony rows were
  spread over 600px of nothing. Panels now pack their contents to the top while
  the frame still matches its neighbour.
- **My first attempt to test that fault measured the wrong thing.** I asserted
  on the *gaps* between rows, and it passed with the fix disabled — because the
  spare height goes into stretching the row widgets themselves, not the space
  between them. Comparing each row against its own size hint shows it plainly:
  120px rows asking for 18–31px. Both new interface checks now fail without
  their fix and pass with it, verified in both directions.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  **6 empire** (new), 23 interface — 85 checks green. 91 modules, all under
  500 lines.

## 2026-07-27 — SEEDFALL: the fleet joins the fight

- **Escorts existed and did nothing.** `combat.py` contained no reference to
  `game.fleet` at all, so a second hull you had designed, paid for and fitted
  sat in a berth while you fought alone. Hulls can now be ordered to sail in
  company: they follow the flag, deploy onto the tactical plane, and fight.
- **A consort is a `Side`.** Subclassing the existing side means `_fire`, the
  layer model and every arc check work on one unmodified. What a consort adds
  is a standing order and a captain who follows it — you have one pair of hands
  and they stay on your own helm.
- **Three orders that are genuinely different bargains.** *Screen* spends the
  escort to keep you whole; *flank* spends patience getting behind something;
  *concentrate* spends everyone's safety to end it quickly. Measured over 24
  fights each: the flag took 50 damage alone and 12 with two screens, while
  flankers put out 34 to a screen's 3. Screening consorts also physically sit
  between you and the enemy, which weights the fire they draw.
- **Losses are permanent.** A consort below 22% hull breaks off; one that dies
  is struck from the fleet whatever the outcome, so bringing a hull to a fight
  is a real wager rather than free damage.
- **Two older bugs found while testing.** `_fire()` measured its range band
  between the flag and the enemy rather than between the two hulls actually
  shooting, which was invisible with two sides and wrong the moment a consort
  fired from a flank. And the Bloom's resisted-hit branch called an undefined
  `say()` — a `NameError` that crashed any late-game Bloom fight where a
  bearing mount hit tissue that had learned that weapon family. It needed
  stage 4, accumulated resistance, a mount in arc and a 25% roll, which is why
  nothing had tripped it.
- **The varied opening aspect was unreachable.** `tac.initial_layout()`, built
  last cycle to vary how an engagement starts, was never used in play: the
  battle screen called `combat.start()` without an rng, so every fight in the
  game began with the enemy dead ahead at band 3. Now seeded from the game's
  own stream. Measured across 40 fights, outcomes are unchanged — it buys
  variety, not difficulty.
- **My test captain was the problem, twice.** Driving fights with a repeated
  "salvo" reported the player dealing *zero* damage, which looked like combat
  was broken; the ship's mounts were all broadside and the order never turned
  it beam-on. Fixing that to steer toward the target still failed, because
  closing puts the target at 0° — outside a broadside arc entirely. Combat was
  behaving correctly the whole time. The arc-aware pilot now lives in
  `tests/captain_ai.py` so the next change to combat is measured against a
  captain that can actually fight.
- Suites: 27 simulation, 5 xenotech, 14 playability, **5 tactical**, 5 flight,
  22 interface — 78 checks green. 87 modules, all under 500 lines.

## 2026-07-27 — SEEDFALL: the helm learns to lead a moving target

- **Transfers now aim where the body will be.** The helm panel told the player
  "bodies move while you fly", and the code did not do it: every quote was
  measured against where the target sat *today*, and arrival teleported you to
  wherever it had drifted. `flight.intercept()` solves the lead as a fixed
  point — guess a flight time, look up where the body will be then, re-time the
  leg, repeat. It settles in at most two passes across 380 solves, and a flown
  transfer now arrives on the predicted day with the aim point 0.0000 AU from
  the body.
- **Courses route around the star.** With the aim point drawn on the chart it
  was immediately obvious that a target on the far side produced a straight line
  passing 0.03 AU from the star. `flight.route()` bends the course around a hot
  radius and charges the detour in distance and days, so an opposite conjunction
  is expensive rather than lethal. The clearance never closes tighter than the
  destination, so the innermost rock is still reachable — and still hot.
- **The chart shows the plan.** The orbit chart draws the routed course as a
  polyline, a crosshair at the aim point, an amber arc for the ground the target
  covers while you are under way, and the star's heat zone when the leg runs
  near it. A burn selector re-plots without committing. The chart also now
  scales to the outermost body, having previously cropped comets off the plot.
- **`hash()` was moving every planet on every launch.** Orbital phase was
  derived from `hash((body.name, body.id))`, and Python randomises string
  hashing per process — so the same seed grew the same galaxy and then scattered
  its orbits differently every time the game started, including between saving
  and loading. Now derived from `core.rng.hash_seed`. A regression check runs
  three subprocesses under different `PYTHONHASHSEED` values and demands one
  answer.
- **A first-frame layout fault, honestly scoped.** Rebuilding a view's column
  did not tell its `QScrollArea` the contents had changed size, so a screen
  taller than the viewport painted once squashed. My first reading of this was
  far more dramatic — nine of ten screens "unable to scroll" — and it was wrong:
  measuring how many event-loop turns the unfixed code needed showed Qt
  recovering by the second turn, so a running app was never broken. What the
  fault really cost was one frame of reflow, and trustworthy screenshots. Since
  reviewing these screens by rendering them offscreen is how this loop works,
  that second thing matters: the bug fooled me before it could fool a player.
- **Two of my own regression checks did not bite, and I caught both.** The
  first asserted a course never dips inside its tighter endpoint — geometrically
  impossible, since a chord between two points at similar radii always sags. The
  second passed with the fix deliberately disabled, because every earlier check
  had already called `grab()` on those views and forced the layout. Rewritten to
  build its own window and measure exactly one event-loop turn, it now fails
  without the fix and passes with it — verified in both directions.
- Suites: 27 simulation, 5 xenotech, 14 playability, 2 tactical, **5 flight**
  (new), 22 interface — 75 checks green. 84 modules, all under 500 lines.

## 2026-07-27 — SEEDFALL: combat becomes positional, with crew stations

- **A real plane.** Ships now carry a position, heading and speed. The five range
  bands survive — every weapon is specified in them — but the band is *derived*
  from an actual separation rather than stored, so all the existing band logic
  kept working while closing became a manoeuvre instead of a menu pick.
- **Firing arcs.** Every mount fires through fore, broadside or turret, derived
  from what it is: fixed lances look forward, point defence and anything
  self-guiding traverses. A mount outside its arc refuses to fire and says how
  many degrees off it is, so turning to bring a gun to bear is a decision worth a
  turn.
- **Three crew stations, one of you.** Each turn you take Helm, Gunnery or
  Engineering personally; your officers hold the other two at their own level.
  Directed gunnery shoots markedly better than automatic. Engineering routes
  power to the mounts or the drive, patches the outermost breach, or dumps heat.
  Twelve orders across the three.
- **The enemy uses the same geometry** — it steers for the range its mounts want
  and comes about when its fixed arcs are pointing the wrong way. It does not
  cheat the plot.
- **A tactical plot** on the battle screen: range rings, both hulls drawn as
  headings, the line of sight labelled with the range, your forward arc sketched,
  and a per-mount readout saying "bears", "60° off arc" or "out of range".
- Modules split to stay under the line limit: `tactical`, `stations`,
  `battle_state`, `enemy_ai` and `abilities` came out of `combat`. Two interface
  bugs fixed on the way — a nav hint reading "keys 1–90", and a salvo control
  duplicated between the fire row and the gunnery station.
- Suites: 27 simulation, 5 xenotech, 14 playability, 2 tactical, 21 interface.

## 2026-07-27 — SEEDFALL: diplomacy with two axes

- **A relations matrix between the powers.** Standing with a faction was a number
  that went up when you sold them charts. There is now a second axis: how the
  four powers regard *each other*, starting hostile in four of six pairs (the
  Concordat and the Freeholds at -45 over stolen frames; the Charter and the
  Freeholds at -35 over forged licences).
- **Six overtures**, each with a cooldown and a standing floor: tribute,
  intelligence, relief supplies, treaties, denouncement (which buys you standing
  with everyone who dislikes your target) and **brokering**, the only action that
  moves faction-to-faction relations at all — and it requires both parties to
  think well of you first.
- **Faction agendas**: each power is chronically short of something (the Charter
  of phosphate, the Yards of ore, the Dry Choir of recordings) and pays extra
  standing for it.
- **Concord is now a diplomatic achievement**: all four powers at Kin *and* all
  six pairs at peace, rather than four separate grinds against one meter.
- **Two balance defects found by playing.** The naive survey-and-sell strategy
  was sitting on exactly zero credits after five years — in-system flight costs
  had quietly made it unviable — which also made the solvency check flaky. Fixed
  by moving the jump arrival point inside the system rather than beyond its outer
  orbit, and repricing survey data from 300 to 460; the check now asserts a floor
  rather than merely "not in debt". Also: ten nav destinations were binding a
  shortcut to a nonexistent "10" key.

## 2026-07-27 — SEEDFALL: the Bloom becomes an antagonist

- **The problem, measured first**: a BASTION with five mounts cleared the whole
  sector inside one in-game year, and the Bloom opened on only 2.8 of 42 systems.
  The game's central threat was frightening while you were poor and irrelevant
  the moment you could afford a warship.
- **Five named growth stages** — Latent, Vegetative, Motile, Adaptive, Sovereign —
  advanced by the sector-wide burden, each raising growth and spread and each
  announced in the log. A test seed runs Latent → Vegetative (yr 2) → Motile
  (yr 5) → Adaptive (yr 6) → Sovereign (yr 7), so there are years of grace before
  it starts hunting.
- **Motile instars**: once past stage 2 it keeps masses in the field that travel
  between systems, preferring *your* colonies, and take them.
- **Adaptation**: from stage 3 it builds resistance to whatever weapon family you
  keep using — up to 55% — and forgets what you stop using. Vary the loadout or
  watch your guns stop working. Verified: 200 fabricated hits gives 55%
  resistance to fabricated and none to grown.
- **The First Instar** at Kessel's Reach: the original husk, Charter serial still
  legible, found by surveying the origin system. Containment now requires the
  sector clean *and* the heart dead — 21 burn passes from a battleship, each
  costing days and taking backlash. Clearing the map is no longer enough.

## 2026-07-27 — SEEDFALL: the helm, and two games inside the game

- **The helm — in-system spaceflight.** A jump now drops you at the system edge
  rather than alongside whatever you came to see. Bodies sit on real orbits with
  Keplerian periods and keep moving while you fly, so the range to a target
  depends on when you leave. Four burn profiles trade reaction mass against days,
  each with its own risk of dust, debris, a radiator flutter or an attitude fault.
  **Coasting is always free**, which is deliberate: without it an empty tank could
  not reach the ice that would refill it, which would have re-introduced the
  deadlock fixed the day before. Local work flies the ship alongside on the
  standard profile, so nobody is forced through the helm to survey a rock.
- **Docking, as the nervous-system study describes it.** Sense with the wet
  organs, compute on the dry core, act with the muscles, hold homeostasis
  meanwhile. Three axes drift; you correct one per pass; the readout is blurred
  in proportion to how poor your sensors are and the correction is as precise as
  your navigator and compute allow. A clean approach earns standing, a botched
  one buys a tug.
- **A decoding bench** for alien emissions: four positions, a hidden pattern, and
  a response saying how many glyphs are exactly right and how many are present
  but misplaced — never which. Worth real study points toward whichever
  technology you are working on, and it costs nothing but attempts, so it is the
  poor captain's route into xenotechnology.
- **A real bug the playability suite caught**: a transit event where a Freehold
  skiff sells you volatiles subtracted credits without checking you could afford
  them, so a poor captain went into debt. You now buy what you can pay for and
  the goods scale to match.
- Suites: 27 simulation, 5 xenotech, 9 playability, 19 interface.

## 2026-07-27 — SEEDFALL: playability audit, then the ground game

- **Playability audit first, and it found two showstoppers.** `exodus_launched`
  was read by the victory check and set by nothing, so one of the five endings
  could never fire. And a captain could deadlock: broke, no fuel, ore in the hold
  and no way to convert one into the other away from a port. Both fixed — there
  is now a `launch_exodus` action, the mining root cracks ice for reaction mass
  (which is its third ingest route in the metabolism document anyway), and a
  distress beacon will get you towed for standing and money if there is genuinely
  no ice either.
- **A new `playability` suite** exists so neither class of defect returns: every
  ending must fire from conditions a player can actually reach, twelve destitute
  starts must all be recoverable, and a plain survey-and-sell run must stay
  solvent for five years.
- **Ground expeditions — a game within the game.** A lander puts a party on a 7×7
  zone revealed one tile at a time. Supply is the clock; terrain costs days and
  springs hazards; site features (worked stone, downed hulls, vents, sealed
  caches, standing arrays) offer choices resolved against an officer's stat.
  Nothing is banked until the party walks back to the lander. Known ground costs
  one day to re-cross, which is the difference between tension and a death trap —
  the first cut had seven expeditions in eight stranding, and now it is one.
- **Contracts.** Six kinds — delivery, prospecting, survey commission, bounty,
  antiquities, ground contract — posted per port, priced by distance, checked on
  the clock so they close the moment their terms are met. Failing one costs
  standing. Nothing requires taking any of them.
- Two real bugs caught by rendering the screens: a zone map cached on the view was
  destroyed with its container on every refresh, and the research card grid sized
  its columns to content so the third column was clipped.
- Suites: 27 simulation, 5 xenotech, 7 playability, 17 interface.

## 2026-07-27 — SEEDFALL: alien technology as its own progression

- **Four alien cultures, twelve technologies, found rather than researched.** The
  Abyssals (still living, under the ice), the Ossuary (a lineage that spent its
  last centuries preparing to be found), the Weft (matter worked at nanometre
  pitch, no bodies and no writing) and the Tessellate (crystalline, and fond of
  standing waves that do not decay). Their remains are seeded as buried sites on
  body kinds that suit them, and every technology is guaranteed at least one site
  so no chronicle is unwinnable.
- **Discover, trade, steal, incorporate** — all four verbs the brief asked for.
  Understanding accrues in study points from excavating a site (which wears out
  as you return to it), analysing relics in a polyp lab, buying field notes at a
  port (the Dry Choir has the best and knows it), or seizing them off a hull you
  destroy. At full understanding the technology is *incorporated*: its id joins
  `research.unlocked`, unlocking one of twelve new parts — most of them family
  `any`, because the point of alien work is bolting it to the hull you already
  fly. Study banked past a prerequisite is kept and settles later.
- **A xenology desk** on the Research screen shows each culture, what has been
  recovered, what remains "an unrecovered technology", and the analyse controls.
- **Three UI bugs fixed on the way, two of them long-standing.** A dozen research
  tabs forced a minimum width wider than the view, clipping everything beside it
  — tabs now wrap onto fixed rows. The card grid sized columns to content, so the
  third column of the research tree, the codex and the hull picker was cut off —
  columns now share the width equally. And an over-clever height-for-width flow
  layout, tried first, collapsed the whole column inside the scroll area; it was
  replaced with something deterministic, which is the lesson.
- Suites split and grown: 27 simulation, 5 xenotech, 17 interface.

## 2026-07-27 — SEEDFALL: five technologies, not one

- **Hull roster 21 → 35, stations 12 → 19**, across five technology families
  rather than three. The GESTALT grown fleet is now one option among several
  instead of the only real choice.
- **Two new families.** *Synthetic* — Dry Choir vessels (CANTOR, LATTICE,
  ORDINAL, THEOREM): crewless, no atmosphere plant, a photonic skin over a
  spaceframe wrapped around a substrate vault, superb instruments and no
  self-repair whatsoever. *Xeno* — REVENANT and ANTIPHON, laid down to a plan
  nobody in the Verge wrote; they mend like a grown hull and ring audibly when
  something large moves nearby.
- **Seven new fabricated hulls** filling the gaps the Yards line had — TENDER
  (tug), AWL (smuggler), KILN (mobile refinery), CARAVEL (passenger liner),
  SPINDLE (deep survey), PORTCULLIS (system monitor), HAMMERFALL (siege) — plus
  the MIDDEN hybrid ship-breaker.
- **Eight new stations spanning the technologies**: Orbital Drydock, Refinery
  Platform, Monitor Station and Helium Skimmer (fabricated), Free Port (hybrid),
  Relay Choir (synthetic) and Reactivated Array (xeno).
- **Two new station mechanics.** A **Free Port** opens a market in a system that
  had none, which is worth considerably more than its docking fees. A **Monitor
  Station** wards its system: it slows the Bloom, burns back what it can reach,
  and — since it is the thing with the guns — defends itself far better than the
  farm next door. Averaged over eight trials, two unattended years take a system
  from 0.24 to 0.75 infestation; watched, it falls to 0.20.
- **Three new technologies** (Autonomous Munitions, Synthetic Cognition, Xenolith
  Metallurgy) and ten new parts, including a smelter bay that turns ore into
  alloy in the hold on the way home.
- **Structural change**: hulls moved out of `data/chassis.py` into
  `hull_types.py` (layer stacks and the family rules), `hulls_grown.py` and
  `hulls_built.py`, with `chassis.py` reduced to the registry. Every import site
  in the game was left untouched, and no file crossed 500 lines.
- **Six new checks** covering the new ground: every family complete and coherent
  (layer weights summing to one, a critical layer, a build requirement, a tint);
  the graft rules that let a hybrid take an intima and refuse a coherent beam;
  only the mechanical families refusing to heal; every station's effect keys
  drawn from a closed vocabulary; the Free Port opening a real market; and the
  monitor ward. That last one caught two real bugs — the station was being eaten
  by the Bloom before its ward could apply, and the hull picker kept editing a
  SPORE while showing you synthetic hull cards. Suite now 27 simulation + 15
  interface checks.

## 2026-07-27 — SEEDFALL: the programme as a playable RPG (PyQt6)

- **New `seedfall/` package**: a native desktop space exploration / trading /
  combat RPG — a modern Starflight with a Civilization layer — built entirely on
  the thirteen documents. PyQt6, 53 modules, every file under the 500-line limit,
  no server and no build step. `python -m seedfall`.
- **The documents are the mechanics, not the flavour.** The Class Reference
  becomes 21 hull chassis; the Dossier's six-layer hull becomes the damage model
  (shots ablate epidermis → rind → mycelium → osteoid, and the crew only starts
  dying when the pneumostat opens); Metabolism becomes the economy, with
  phosphorus scarce because chondrite is 0.1% P; the Cell Atlas becomes the
  fittings; the Nervous System becomes a cognition branch where you must *buy*
  silicon because nobody can grow a processor; the Compendium becomes a 58-node,
  ten-branch tech tree; and the Registry's six named containment failures become
  the six factions — including the Bloom, a lineage with its Hayflick counter cut
  out, which simply grows.
- **Design intent — many paths.** Grown / fabricated / hybrid hull families with
  real trade-offs (grown heals but gestates for months and eats phosphate;
  fabricated is instant, expensive and never repairs itself). Combat on a
  five-band range track where destruction is only one win condition: resolve lets
  a TESTUDO with no weapons at all win by outlasting, which is the programme's
  actual doctrine. Five simultaneous victory conditions (Containment, Exodus,
  Concord, Genesis, Dominion).
- **Built first as a browser build, then ported to PyQt6 and the web build
  retired**, so there is exactly one implementation of the rules and no chance of
  the two drifting apart. The `/game` viewer route was removed with it.
- **Tested headlessly, and it mattered.** `python -m seedfall.tests` runs 21
  simulation checks and 15 interface checks; the interface suite builds the real
  `MainWindow` on Qt's `offscreen` platform and paints every screen and tab,
  including a live engagement. Between the two builds the suites caught nine real
  defects, several of them unplayable: sector generation that could **strand the
  player with nothing in jump range** (fixed with a lane-relaxation pass
  guaranteeing every star has a neighbour within a starting jump); combat that
  **never terminated** because armour could fully null a weapon (armour now floors
  at 15% leak-through, plus late-onset resolve attrition and a turn cap); weapon
  mounts beyond the first doing nothing (added the full-salvo order); hulls so
  large relative to damage that an escape pod drove off a battleship (hull scale
  retuned — fights now run ~18 turns and span destroyed / driven-off / lost);
  derived ship stats being written into save files; a negative ice-harvest rate
  from the reaction organ's fuel draw; and a clipped HUD caption.
- `seedfall/INTERFACE.md` documents the module map, the one-directional layer
  rule (`data → world → sim → ui`), and the constants that will bite anyone
  retuning it. Root `INTERFACE.md` and `README.md` updated.

## 2026-07-26 — Working 3D models (glTF/OBJ/STL) + an interactive viewer

- **New `models3d/` package**: builds solid, colour-coded 3D meshes of the
  seven main designs (trimesh) and exports each to **three working formats** —
  `.glb` (glTF, coloured), `.obj`, and `.stl` (printing) — into
  `assets/models3d/`, plus a preview PNG. Modular: `build.py` (per-design mesh
  builders), `render.py` (matplotlib preview), `run.py` (CLI
  `python -m models3d.run [--check]`). `dome_half` is hand-triangulated so it
  needs no external triangulation engine; each GLB is round-trip-validated.
- **Interactive gallery in the local viewer**: added a `/models` route
  (`viewer/models_page.py`) that shows the models lit, rotatable and AR-capable
  via `<model-viewer>`, with download links, plus static serving of the
  glb/obj/stl at `/models/<file>` (path-traversal guarded) and a "Working 3D
  Models" card on the landing page.
- README gains a "Working 3D models" section with the seven previews. Verified
  every mesh by eye from a rendered frame (fixed the preview's cross-part depth
  sorting so the LICHEN/TESTUDO domes show).

## 2026-07-26 — Nervous System (13th document): sensing, cognition, comms

- **New 13th document — Nervous System** (`gestalt-nervous.html`): how a grown
  vessel senses, thinks, controls and communicates. Its thesis: a km-scale ship
  needs both a **grown "wet" nervous system** (real sensory organs, bioelectric
  signalling, grown neural computation — DishBrain-style) for sensing,
  homeostasis, reflex and learning, and a **fabricated "dry" silicon core** (fast
  deterministic compute, navigation, comms, the human digital interface) —
  because biology can't grow a fast transistor or a radio, and silicon can't
  self-repair or sense. The two are joined by a real bio-electronic **interface**
  (OECTs, microelectrode arrays, electrogenetics, optogenetics, conductive
  nanowires). It is, honestly, a cyborg. Covers senses, the signalling
  speed-limit, the four kinds of organic computation, the silicon side & the
  interface, communication (crew + fleet), and a worked docking control loop.
  Three house-style figures (control stack, bio-electronic interface, docking
  loop), 14 citations. Registered in the catalog (slug `nervous`); canonical nav
  regenerated to **thirteen** entries across every document; all thirteen
  artifacts republished.

## 2026-07-26 — Python simulations of the designs' major systems (animated 3D)

- **New `sim/` package**: dependency-light Python (numpy + matplotlib) that
  models the major systems of the four main designs and renders them as
  **animated 3D GIFs** (`assets/sim/`). Modular — `params.py` (canonical
  numbers, single source of truth), `systems.py` (grounded dynamics: growth,
  life support, spin gravity, thermal, gestation), `geometry.py` (3D meshes),
  `animate.py` (per-design 3D-scene-plus-gauge builders), `run.py` (CLI:
  `python -m sim.run [design] [--fast] [--check]`).
- **Four simulations**, each a 3D scene + live gauges: **NAVIS** grows from a
  seed to ~24,000 t on the mining-limited curve with day/night intima glow;
  **ARCA** spins to 1 g at the rim with crew on the inner surface, a Coriolis
  drop, and a stable ~125-yr O₂ reserve; **LICHEN** swings ~160–265 K on the
  Martian surface while the interior holds 293 K; **GRAVID** gestates vessels in
  staggered cradle cycles. Each verified by eye from a rendered frame.
- Added `sim/INTERFACE.md`, a README "Simulations" section (the four GIFs), the
  project INTERFACE tree, and a gitignore for the preview frames.

## 2026-07-26 — Metabolism (12th document): ingest → digest → metabolise → excrete

- **New 12th document — Metabolism** (`gestalt-metabolism.html`): the nutrition-
  and-waste physiology of a grown vessel across four acts. Python-grounded
  mass-and-energy budget yields the document's thesis: photosynthesis on the hull
  makes only ~0.45 t/day of biomass (matching 13 t/day growth would need 29× the
  hull area), so the intima only makes the crew's **air** — the **body** is grown
  by *eating the rock* (digesting a carbonaceous asteroid's reduced organic
  carbon, ~1.4 MW, and oxidising its minerals), which is why growth is
  mining-limited. Covers the two mouths, the mineral gut (bioleaching →
  separation → refinery → organics → absorption), the two-sap bloodstream, and
  the four waste streams (only heat truly leaves; ~100 t/day tailings re-used as
  shielding; C/H₂O/N closed). Five house-style figures (whole-body flow,
  ingestion, digestive tract, energy budget, excretion streams), 13 citations.
  Registered in the catalog (slug `metabolism`); canonical nav regenerated to
  **twelve** entries across every document and all twelve artifacts republished.
  (Recovered mid-build from a botched in-place figure swap by rebuilding the doc
  from source and re-injecting figures cleanly.)

## 2026-07-26 — Cell Atlas (11th document) + richer 3D interiors

- **New 11th document — the Cell Atlas** (`gestalt-cells.html`): a cell-level
  cytology of a grown vessel. Grounds the census in Python (~10¹⁹ cells per
  hull; ~42 distinct types across 8 functional classes) and catalogues every
  type — role, survival, chassis, metabolism, life-cycle, coordination and
  distribution — plus the internal ecosystem/trophic web, and how each type is
  engineered, grown and tested (cross-linked to the Compendium and Earth
  Program). Three new house-style figures (lineage tree, trophic web, hull
  cell-distribution map), 19 citations, honest `gap:` flags on the three big
  integration bets. Registered in the viewer catalog (slug `cells`); the
  canonical nav is regenerated to **eleven** entries across every document and
  all eleven artifacts republished.
- **3D models — richer cutaway interiors**: multi-level decks, habitation
  compartments, vascular cores, ARCA terraces/settlements/sun-cord nodes,
  LICHEN floors + taproot, GRAVID embryos at two growth stages with umbilicals,
  and SPORE/LEVIATHAN/TESTUDO occupants. All 14 builds node-verified.

## 2026-07-26 — Detailed illustrated README (+ a broken figure found & fixed)

- **Rewrote `README.md`** into a detailed, illustrated guide: hero, a mermaid program
  map + closed-loop-metabolism diagram, a per-document tour with real figures, a
  "by the numbers" table (python-verified), the honesty conventions, and run/structure
  sections.
- **Extracted 13 figures** straight from the documents' own inline SVGs into
  `assets/figures/` as PNGs. Each figure is made self-contained (the docs' CSS
  variables are resolved to literal dark-theme values, since librsvg does not evaluate
  `var()`; stray `&` escaped; a dark ground added) and rasterised with `rsvg-convert`,
  then eyeballed. Class-styled drawing sheets (Starship/Habitat/GRAVID/LICHEN) carry
  their doc's class rules so they render faithfully.
- **Found and fixed a real defect:** the Compendium's *defence-in-depth* cancer-control
  figure was an unfilled `{fig}` placeholder in the published doc. Rebuilt it from
  scratch as a python-grounded waterfall (10¹² → 0.1 uncontrolled tumour lineages
  across seven layered controls, ~10¹³× suppression, below the 1-per-lifetime
  threshold) and republished the Compendium.

## 2026-07-26 — Two new documents, consistency pass + GitHub

- **Grew to ten documents.** Added the **Fleet Class Reference**
  (`gestalt-classref.html`, 9th) — a detailed profile of all 18 grown-vehicle
  classes with a master comparison table — and **3D Models** (`gestalt-3d.html`,
  10th) — interactive, rotatable/zoomable solid models of all seven main forms,
  drawn by a self-contained (WebGL-free) software renderer with cutaway views,
  interior components, a live scale bar and labelled hotspots.
- **Consistency pass across all 10 docs.** The per-document navigation bars had
  drifted (each listed a different 5–8 subset of the set). Regenerated every
  `prog-nav` to one canonical 10-entry bar so all documents cross-link the whole
  program; verified 9 links + 1 current marker and balanced tags in each.
  Re-published all ten artifacts to their canonical URLs. Updated `README.md`,
  `INTERFACE.md`, and `viewer/catalog.py` to reflect ten documents.
- **Published the project to GitHub** (`git init` + first commit).

## 2026-07-26 — Persisted to project folder + Python viewer

- Copied all eight published documents from the (session-only) scratchpad into
  `docs/`, plus the design-loop state file `deepen-roadmap.md`.
- Built a zero-dependency **Python viewer** (`viewer/`, stdlib only):
  - `catalog.py` — document registry (source of truth).
  - `wrap.py` — wraps each artifact fragment into standalone HTML and rewrites
    cross-document `claude.ai/code/artifact/<id>` links to local `/d/<slug>`
    routes (preserving `#anchors`).
  - `index.py` — themed landing page (document grid, GESTALT identity, light/dark).
  - `app.py` — `http.server` app + CLI (`--check`, `--open`, `-p`).
  - Verified: `--check` passes for all 8 docs + index; live server returns 200 for
    `/` and `/d/<slug>`, 404 for unknown slugs; 0 residual external artifact links
    after rewriting.
- Added `INTERFACE.md`, `README.md`, and this log.

## Program state (design loop)

The documents are produced and refined by a recurring "deepening" design loop
whose full round-by-round history and queue live in `deepen-roadmap.md`.

- **Phase A** (rounds 1–20): deepen each document element; ground every figure
  in Python. Complete.
- **Phase B** (rounds 21–30): build the Earth Program (ground R&D roadmap) —
  six work packages, integration ladder, Gantt + budget, gated go/no-go. Complete.
- **Phase C** (rounds 31–44): cross-link all documents bidirectionally; audit and
  reconcile every figure against the Compendium §08 canonical-parameters table.
  Caught and fixed several real errors (ARCA atmosphere 828→113 Mt and its O₂-buffer
  cascade; LICHEN membrane 6.5→7.4 MN/m; the pressure-wall 6.5 cm→6.5 mm; the O₂
  buffer 160→140 yr to match the canonical 34% O₂; stale cross-doc phrasing).
- **Phase D**: upgrade all figures to professional architectural-diagram
  standard, and add real citations throughout (~108 references across the set).
- **Phase E** (user-directed): subsystem deep-dives (light delivery, healing &
  regeneration, sustainability) documented as chat answers + python-grounded
  figures; the **Fleet Class Reference** and interactive **3D Models** documents;
  and a whole-program consistency + cross-linking pass. Program now ten documents.
