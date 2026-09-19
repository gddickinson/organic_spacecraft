# Session log, part 24 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

## 2026-07-28 — SEEDFALL: 3D ship plans (asked for)

- **Asked for 3D plans of the ship so a player can see what is going on with
  it — fittings, changes, storage, crew.** Everything on the ship screen was
  already true and none of it was a picture: you could read that a Polyp
  Laboratory was fitted and the ablative layer was at 41% and have no idea what
  you were flying.
- **A software renderer, not OpenGL.** `core/solid.py` is primitives, a
  painter's-algorithm depth sort and flat shading; `ui/plans_panel.py` fills the
  polygons with QPainter. No new dependency — and, the point, it renders
  identically offscreen, so the suite can look at the ship instead of taking its
  word. `models3d/` stays what it was: a trimesh export tool the game cannot
  import. The shape vocabulary is shared, so the two read as the same ship.
- `data/hullforms.py` gives each of the five families a silhouette, a faceting
  and a set of mounts; `sim/plans.py` assembles the model from the *actual*
  ship — chassis, every fitted part at its slot, the hold filled from the floor
  with what is really aboard, one berth per crewman lit if somebody is in it.
  Because the model is a function of the fitted list, the shipyard can hand it
  `design_fitted` and show the refit before you buy it.
- **The bug it shipped with, and how it was caught.** The ellipsoid was wound
  inside-out. Half the faces cull either way, so the count looked right and the
  ship drew as an x-ray of its own far wall with the cargo floating in front —
  which looked deliberate. Found by rendering it and looking, then pinned by two
  checks: normals on every primitive, and a box inside a sphere that the sphere
  must occlude. Both fail when the winding is put back.
- Two further defects found by looking: mounts written as a radius buried every
  fitting inside the beam (the hull is tapered, so where the skin is depends on
  height), and drawing every family at one resolution made them the same ship in
  different colours — a Yards hull is 6×8 facets now, welded plate against a
  gestated 16×24.
- `test_reachable` caught two helpers I wrote and never called. Deleted.
- Suites: 46 — 374 checks green. 196 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the chart now says what you can get to

- **The chart answered the wrong question.** It drew a dashed ring at the jump
  range and greyed one button to "Out of range" — which is "can I jump there in
  one hop". The question is "can I get there at all", by hopping, and often the
  answer is no. Flooding from the start at starting jump range reaches 2 to all
  42 systems depending on seed: median 13, a quarter of sectors under eight, one
  in eight at three or fewer. A captain handed a two-system pocket saw forty
  stars drawn no differently from the one next door.
- `sim/reach.py` computes the reachable component, what lies beyond the wall,
  and what each drive *this hull would actually accept* would open. The chart
  strikes through walled stars and prints the line: "2 of 42 systems are
  reachable at 8.9 ly — 40 lie beyond a gap no amount of hopping closes. A
  Foldrunner Coil would reach 13.7 ly and open 40 more, once researched."
- **Why the ladder is so steep, which the screen now admits.** `ion_cluster`,
  `plasma_drive` and `fusion_torch` are fabricated-family and a grown hull
  refuses them, so a NAVIS ladder is reaction organ 8.9, sail film 9.0,
  foldrunner 13.6. `opens()` lists only graftable drives, because naming the
  others would make one very expensive step look like a gentle climb.
- **Checked before concluding**: a shipyard is within reach in 80 of 80 seeds,
  so nobody is permanently stranded — the exit exists, it was just unsigned.
  `MAX_LANE` does not prevent this and never claimed to: it stops a *star*
  sitting alone, not a *cluster*.
- Fuel is deliberately not modelled in reachability: ice can be cut anywhere,
  so it paces a voyage rather than bounding it, and a wall that moved with the
  tank would be a worse lie than no wall.
- Suites: 45 — 366 checks green. 191 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: one chronicle, ten years, every screen

- **Turned last cycle's accident into a standing check.** The README
  screenshots found a shipped crash in minutes because they were one long-lived
  save touching every screen in sequence — the kind of play forty-three suites
  were not doing. `tests/chronicle.py` now flies a single captain for ten
  years: surveying whole systems, refitting, hiring, trading off the freight
  desk, mining, digging, landing parties, planting colonies, running works and
  moving the relations matrix. `test_chronicle.py` repaints every screen and
  every tab against that save as it accumulates, with `sys.excepthook` armed
  because Qt swallows what a slot raises.
- **It found a real one on its second run.** `Dig` held a `body_index` and no
  system, and `_fatigue` resolved it against `game.system` — whatever system
  the ship was in *now*. Fly away with an open trench and keep working it, and
  you read a different body's fatigue, or hit `IndexError` on a shorter body
  list. Digs are saved, so the wrong body outlived the session. `Dig.system_id`
  pins it, `site_of()`/`at_site()` resolve through it, `work()` refuses from
  elsewhere, and backfilling still works from anywhere — which is the one thing
  you must be able to do with a trench you have left. Old saves migrate.
  Verified by putting the bug back: the check fails, and the chronicle's screen
  check fails with the original `'int' object has no attribute 'sell'` when the
  register bug is reintroduced.
- **Most of the cycle went on the driver, and every correction was a
  measurement.** In order: `_move_on` mined ice and returned "moved", so a
  broke captain moved on 170 times and saw six systems; ranking the freight
  run above unexplored space shuttled one profitable lane 144 times; selling
  everything but volatiles sold the biomass and phosphate a seed bay is built
  from, so the bay never fitted and nothing was ever planted; a greedy refit
  loop bought every cheap part with a jump term and *lost* a light-year to
  fitted mass; surveying three bodies a round and leaving meant `scanned` never
  went true and a decade charted two systems; and exploring blind parked the
  captain in a pocket of portless systems for thirteen rounds on eleven tonnes
  of biomass. Each fix carries the number that justified it in a comment.
- **Two things the driver found that are the game's, not the driver's.**
  Every ground option that pays a field note wants comms or medicine, and the
  opening crew is science, nav and engineering — 168 notes offered in a decade,
  none takeable, until the captain visited the berths. Both specialists recruit
  at ordinary rates, so that is a station to fill rather than dead content, and
  the driver now hires. And flood-filling from the start at starting jump range
  reaches 3 to 18 of 42 systems depending on seed, median about 5 — logged as
  task #44 with the per-seed numbers rather than fixed blind.
- **The suite is honest about its one concession**: `play()` tops the purse up
  to a floor each round. Solvency is `test_play`'s question; this one is
  whether accumulated state breaks a screen. Every action is the real one, only
  the money is a gift, and `play`'s docstring says so.
- Painting every sixth round cost 3m45 for the same three verdicts; every
  twentieth costs 35s and still makes 387 paints plus a full reload pass.
- Suites: 44 — 360 checks green. 189 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a README, and the crash it found

- **Asked for a README with screenshots of every major feature.** Wrote
  `seedfall/tests/capture.py`, which builds one developed chronicle — a
  half-charted sector, colonies online, contracts in hand, a programme under
  way, a party on the ground — and renders fourteen screens offscreen. The game
  README is `seedfall/README.md`; the root programme README keeps its own shape
  and links to it.
- **Rendering them found a shipped crash.** `charts.stamp()` wrote each chart's
  completion day into `game.register` — which is the *price* register.
  `market.best_markets` walks every value in that dict and reads `.sell`, so
  charting any system and then opening a port raised `AttributeError` from
  inside a Qt slot, where Qt swallows the traceback and the freight desk simply
  fails to draw. It had been there since the charts cycle.
- **`test_verbs` never caught it** because its fixture does not survey a system
  to completion, so no chart was ever stamped. Chart dates have their own field
  now, with a migration for old saves, and a check asserts the price register
  contains nothing but quotes.
- **Worth naming: taking screenshots is a kind of play the suite was not
  doing** — one long-lived save touching every screen in sequence, rather than
  a fresh game per check. That is exactly the shape of state the collision
  needed.
- Suites: 44 — 356 checks green. 187 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the odds on the ground

- **The expedition screen said "(science, difficulty 3)" and stopped.**
  Resolution is `1d6 + officer level >= difficulty + 2`, so that exact string
  is a one-in-three attempt with a green officer and a five-in-six with a
  level-three one — the same nine characters either way. The reward was
  unpacked into a variable named `_reward` and discarded, so the player was
  never told what success paid. And a failure springs a hazard 40% of the time,
  costing supply, the rover and sometimes an officer, which was also unstated.
- **The ground game is nothing but a sequence of these choices**, which is what
  made this the one worth doing: every tile with a feature on it is a decision
  between two or three options and the screen gave a stat name and a number
  with no scale attached to it.
- **`expedition.odds_for()` gives the chance, the officer who would take it,
  the prize and the risk**, and the panel reads "83% — Marek Nazari on
  engineering · 900–3,400 credits · If it goes wrong: 7% chance of springing
  something". Reading a flight recorder with nobody on comms is 33% with a 27%
  chance of springing something; stripping the salvage next to it is 83%. That
  is the decision, and it was invisible.
- **The check rolls each option six hundred times** and fails unless the
  empirical rate matches the quote, because the resolution lives in `attempt`
  and the quote in `odds_for` and the whole point is that they cannot drift.
  Worst discrepancy across nine options: 3.0%. Dropping the `+2` from the quote
  makes it report "said 67% rolled 32%".
- **Eighth cycle running where the defect was a readout.** Seven of the eight
  now have a preview or forecast function in the sim with a check pinning it to
  what actually happens: contracts, freight, mining, the bench, overtures,
  seats, colonies, and now ground options.
- Suites: 44, **6 attempts** (new) among them — 355 checks green. 186 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what will grow there

- **Seventh cycle running the defect is a readout, and this time I went looking
  for it deliberately** rather than stumbling on it. The plant-a-seed dialog
  was the obvious remaining candidate: founding is the core empire decision,
  months long and tens of thousands of credits, and the screen gave a price and
  a gestation time and nothing else.
- **Measured on a single rocky body: fourteen classes on offer**, yielding
  anything from 2.6 tonnes of ore a day (RADIX Mine, 12,000 credits) to 260
  credits a day (Free Port, 74,000) to 4.2 research a day (Reactivated Array,
  96,000). Three of the nineteen classes yield nothing at all and buy effects
  instead — a GRAVID Nursery at 60,000 credits produces not one tonne of
  anything, which is legitimate and needs saying.
- **`colony.forecast()` gives yield, upkeep, effects and a rough payback**, and
  the card shows them: "2.6 ore/day, 0.11 phosphate/day · Upkeep: 0.1
  biomass/day · Pays for itself in about 0.3 year(s) once it is up." Payback
  ranges from 0.1 years to 3.6 across the classes, which is the comparison the
  dialog existed to support and could not.
- **Priced at a flat table rather than a market**, deliberately: a payback that
  swings with whichever port you happen to be standing in is not something
  anybody can compare classes with.
- **The check plants all fourteen classes a body will take**, matures each, and
  fails unless yield, upkeep, effects and gestation are what was forecast.
  Forecasting nothing makes four of the five checks fail, the first reporting
  "radix_mine: forecast {}, yields {'ore': 2.6, 'phosphate': 0.11}".
- **One fixture error of my own**, caught immediately: I stocked a guessed list
  of commodities and the check died on spidroin, for a class it was not
  testing. It stocks the whole commodity table now.
- Suites: 43, **5 founding** (new) among them — 348 checks green. 185 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what a seat is worth

- **Measured the crew stations, and the combat sim is sound.** Directed gunnery
  really does shoot markedly better than automatic: +0.10 against −0.12 + 0.02 a
  tactical level. An unattended helm repeats its last order at 0.7 + 0.06 a nav
  level of the turn rate. An unattended engineering section sheds a fraction of
  its vent and can do nothing else — no venting hard, no routing power, no
  damage control. All three claims hold.
- **The orders panel stated none of it.** It printed the station name, the
  officer's level and a blurb. So a captain could not tell that gunnery is
  worth +0.22 with a green officer and only +0.10 with a veteran — that *who
  you have* decides *where you should sit*, which is the entire point of the
  one-seat rule.
- **`stations.seat_value()` says what each seat buys**, given the officers
  aboard, and the bridge draws it: "turn at full rate instead of 82%", "+22% to
  hit over the officer", "vent 72 heat instead of 25, or route power, or patch
  a breach". Sixth cycle running where the defect was a readout rather than a
  rule.
- **The checks drive the claims through `run_helm` and `run_engineering`**
  rather than re-deriving their formulas, so changing the sim and not the
  quoted figure is caught. Halving the unattended turn rate makes it report
  "said an officer turns at 70% and it turned at 50%".
- **Three of my own measurement errors this cycle, all caught before they were
  written down as findings.** My first driver set `action["station"]`, which
  the sim ignores — the station is derived from the order — so four
  configurations produced identical results and looked like proof the choice
  did not matter. Then `hull_pct` rounding 99.3% to 100% read as the player
  taking no damage at all. Then the fixture promoted "the tactical officer" on
  a crew that has none, so a green bridge was compared with itself.
- Suites: 42, **6 seats** (new) among them — 342 checks green. 184 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: what an overture buys

- **Measured the six diplomatic overtures.** They all work and they are
  properly differentiated: tribute 12,000 credits for +9 standing, intelligence
  6 survey sets for +7, relief 40 t of biomass for +11, treaty 30,000 for +14
  and a signature, denounce free but −14 with the target, broker 20,000 to move
  the relations matrix +28. Only brokering repairs the matrix and only
  denouncing tears it, which is exactly as designed.
- **The screen showed the price and never the benefit.** Relief is about six
  times better per credit than tribute (193 a point against 1,333) and three
  times better than intelligence, and a player had no way to see any of it —
  three overtures, three costs, no numbers on the other side.
- **And a treaty had a cost stated nowhere at all.** Beyond its 30,000 it
  charges standing with the signatory's enemies through `allegiance`. You
  signed, and two other powers thought less of you for a reason the game never
  mentioned. In a sector at war it is six points with each of the other three.
- **`dip.preview()` is a pure function** returning what an overture will move —
  the target, third parties, and the matrix — and the screen draws it under
  each one, with the cooldown. A treaty now reads "Charter +14, Freeholds −2,
  Concordat −1" before you commit rather than after.
- **The check that matters is the honesty one:** perform every overture and
  fail unless standing and matrix move exactly as previewed. Hiding the
  treaty's rivals again makes it report "said {charter: 14}, did {charter: 14,
  concordat: −1, freeholds: −2.2}". There is a second check that previewing
  moves nothing, because a preview that quietly performs is worse than none.
- **Nothing was wrong with the diplomacy sim itself** and I have not touched
  it. This cycle is entirely about the screen telling the truth about what it
  offers — the fifth time that has been the defect, after the contract fee, the
  freight spread, the mining rate and the research bench.
- Suites: 41, **5 overtures** (new) among them — 335 checks green. 183 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a work nobody could build

- **Measured colony works for the first time, and got it wrong twice before
  getting it right.** First pass compared each work across a *different* seed,
  so I was comparing different colonies on different bodies. Second pass fixed
  the seed and still showed four works with large negative yields — building a
  garrison apparently cutting output 29%. That was market drift: I was pricing
  the yield in credits at a market whose prices move over the 70–140 days of
  construction. Measured in tonnes, every work does exactly what its table
  says. Sixth measurement artefact of this project; caught before it became a
  finding.
- **Then a real one, and it took a third correction to see.** `annex` was
  offered by no colony. My first reachability sweep had not unlocked the tech
  it wants, so `available()` returned it as *not ok* and my filter dropped it —
  seventh artefact. Unlocking everything in the game and running it again:
  **buildable by 0 of 19 classes.**
- **"Build a xenology annex" was gated on a technology that does not exist.**
  A hundred days, eleven thousand credits and twenty-two alloy, granting half a
  research point a day and four points of diplomacy, behind
  `tech="xenolinguistics"` — which is in neither the sixty-one-node research
  tree nor the twelve xenotechnologies. Nobody could ever build it.
- **It is the only broken gate in the whole content set.** Works, colonies,
  parts, chassis and every tech prerequisite: 131 gated entries, one wrong.
  Pointed at `xenobiology`, and there is now a check over all of them.
- **A test fixture was part of why it hid.** `test_verbs` appended the phantom
  id to `research.unlocked`, so the sweep that clicks every control in the game
  saw a work no real chronicle could reach. A fixture that invents content is a
  fixture that stops the suite noticing content is missing — that is fixed too.
- Suites: 40, **5 works** (new) among them — 329 checks green. 182 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a bench that eats what it says

- **Measured the research bench for the first time.** Most of it is sound: the
  approaches are a real decision (careful 112 days, parallel 75, push 58 with
  setbacks), a starved bench crawls at 180 days but is never a dead end, and
  evidence saturates per project at about 160 units — which is correct, because
  it is *consumed*, so across 61 techs you need some ten thousand of it.
- **But the readout was out by a factor of two.** `needs()` is documented as
  "how much of each kind a programme will consume end to end" and the screen
  prints it as "26 wanted". `draw()` then spent `total / 60` a day, while a
  careful programme runs about 128 days — so the bench ate **2.1x** what it
  advertised, on every track, for every technology. The sixty was a duration
  nobody had checked against the real one.
- **And it ignored the approach.** Running parallel tracks costs, in its own
  blurb, "three benches' worth of material" — and the shelves were read against
  the careful figure. The screen now quotes ×1.9 for parallel because that is
  what parallel takes.
- **Fixed by pacing the draw over the programme's actual expected length**
  rather than a constant. Wanted and used now agree within 7%, and the panel
  reads "Hardware 40 held · 64 wanted" in amber when you are short.
- **A false alarm of my own, checked before it became a finding.** A test
  showed the bench *gaining* survey evidence during a run — 400 stocked, 28
  spent, 426 left — which looked like something generating evidence out of
  nothing. It was my arithmetic: a chronicle opens with 55 survey and 25
  specimen already on the shelves, so `stock=400` starts at 455. Idle time
  generates nothing, as it should.
- **And one stale lever.** Adding a `rate` argument to `draw()` broke the
  existing `research-evidence` lever, whose patch was a three-argument lambda.
  The efficacy harness reported it as a signature error rather than silently
  passing, which is the whole reason it checks its own substitutions.
- Suites: 39, **5 bench** (new) among them — 323 checks green. 181 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a hard burn that costs something

- **Set out to build a launch-window planner, and the measurement killed it.**
  A leg's cost varies 1.9x on average and up to 5x as the bodies move, which
  looked like the missing decision in piloting. Then I measured the orbital
  periods: **1,486 to 9,855 days**. The windows are four to twenty-seven years
  apart, and waiting 1,400 days to save 3 t of volatiles — about 120 credits —
  is not a trade anyone would take. I had `window()` and `hold()` written and
  deleted them rather than ship a feature nobody would use. A decorative
  feature is exactly what the efficacy harness exists to catch, and I would
  rather catch it before writing the screen.
- **What the measuring found instead.** Flying a system end to end took 55 days
  coasting and 10 on hard burns. The hard burn cost about three hundred credits
  of reaction mass and 1.2% of a hull that heals itself, so the four profiles
  collapsed to "always hard burn". Its own blurb promised that "the crew will
  feel it and the radiators will complain", and a burn never touched heat.
- **Heat was a one-way ratchet.** Nothing outside combat added it and nothing
  shed it: a ship sat at thirty for twelve hundred days with radiators rated at
  twenty-four a turn. The only thing that ever generated heat outside a fight
  was one flight incident, and it followed you around for ever.
- **So: a burn leaves heat, and heat is a state you fly in.** Hard burn arrives
  at 62% of cap; a hot hull is riskier to burn again in; over the cap the
  radiators stop keeping up and the hull cooks. Measured over a four-leg tour
  plus a month sitting: coast 89 days and no hull, economy 59 days for 6 t,
  hard 41 days for 24 t and **11% of the hull**. One hard burn from cold is
  still free — it arrives under the cap. It is the habit that costs.
- **`REST_VENT` is written down as what it is:** not a physical ratio but the
  rate that makes heat a state you fly in rather than one that has gone by the
  time you arrive. At 0.5 a hard burn cleared in four days and never stacked;
  at 0.14 it takes a fortnight.
- **The efficacy harness rejected my first lever**, correctly: it patched the
  `BURNS` list, which `travel_to` never reads (it goes through `BURNS_BY_ID`),
  and it demanded a callable target. Routing the heat through `burn_heat()`
  fixed both and is better code.
- Suites: 38, **7 burns** (new) among them — 317 checks green. 180 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: a rig that knows when to stop

- **Mining, measured for the first time.** It pays 11–104 credits a day and the
  four methods are a real decision: boring lifts most and takes 0.81 of a body,
  bioleach lifts nearly as much per day for 0.13. Over a body's life, leaching
  wins. That part was already right.
- **The fifth measurement artefact of this project nearly became a finding.**
  I measured the panel's quoted rate against the actual haul and got 36–54% —
  "the screen lies". It does not: my probe had loaded 300 t of volatiles to
  fund the bore's upkeep, leaving 40 t of hold. With room, quoted matches
  actual at 101%. Checked before claiming, which is the only reason it did not
  go in the log as a bug.
- **But it led straight to a real one.** Working a body for sixty days with an
  empty hold takes 106.2 t and works it out by 0.384. With the hold 97% full it
  takes 10.2 t — and works the body out by the **identical 0.384**. Ninety-six
  tonnes raised and thrown away, a third of a body spent to recover a tenth of
  what the rig lifted, sixty days gone, and nothing anywhere said so.
- **The working stops when there is nowhere to put what it raises.** Time and
  depletion both follow what was actually lifted: 10 t in 3 days for 0.019 of
  the body instead of 60 days for 0.384. Ten seconds of arithmetic on the panel
  now says "25 t in 14 days — the hold fills first".
- **A second bug, found by the regression check rather than by me.** Everything
  that can refuse a working ran *after* `flight.ensure_at()`, so being told
  there was no room cost twelve days of flying out to the body first. The check
  asserted no time passes on a refusal and reported "12 days spent on a refused
  working".
- **And a vacuous check of mine, caught the same way.** The proportionality
  check picked a hold fill fraction blind, and on that seed the body raised
  less than the hold anyway, so no capping happened and it passed measuring
  nothing. It now computes the room to leave from the haul the spell would
  actually raise, and asserts capping occurred before drawing any conclusion
  from it.
- **And then my own fix deadlocked the game, which the playability bot caught
  by hanging.** Refusing to work a body with a full hold is correct — but it
  left a captain with a full hold and an empty tank unable to mine ice for
  reaction mass, unable to jump, and with no way to dump anything: the only
  jettison in the game was on the contraband panel, which appears solely when
  carrying contraband at a hostile port. The bot span forever because `extract`
  refused without advancing the clock, so the five-year limit never arrived.
  The full suite went from five minutes to never finishing, which is how I
  found it.
- **`trade.jettison()` is general now** and the hold has a vent control, so the
  affordance the bot needed is one a player has too. The project already holds
  that an empty tank must not be a deadlock; this is the same rule from the
  other side, and there is a check for it.
- **`test_play.py` crossed 500 lines**, so the long-game captain moved to
  `captain_bot.py` — it is the thing that catches deadlocks and deserves to be
  findable.
- Suites: 37, **7 workings** (new) among them — 309 checks green. 179 modules,
  all under 500 lines.
