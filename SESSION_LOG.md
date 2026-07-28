# SESSION_LOG.md — GESTALT project

Running progress log. Newest first.

## 2026-07-28 — SEEDFALL: ten endings, and a game that carries on past them

- **Asked for a wider range of endings, and for the game to continue after any
  of them with more play afterwards.** There were five victories, one loss and
  death, and reaching one showed a dialog and called `clear_save()`.
- **Five more endings**, each measured off machinery that already existed:
  **Lineage** (four grown hulls of your own gestation, signed for), **Xenarchy**
  (all twelve alien technologies incorporated), **The Cartel** (most of the
  sector's prices in your register, and a purse), **Apostasy** (a synthetic hull
  with nobody aboard, at Kin with the Choir), and **Ruin** — outliving the
  sector, which required checking endings *before* letting the Bloom kill you,
  since the old order set `dead` first and Ruin could never fire.
- **Every ending now opens an epoch.** `data/epochs.py` rewrites the world once
  and starts a new clock in place of the Bloom: containment leaves four powers
  with no common enemy and a cleared sector to divide; concord leaves a unified
  Verge with something on a heading toward it; dominion makes you a power, with
  secession. Forty situations across the ten, each a choice whose answers state
  what they do — and `legacy.apply` reads the same dict the card was rendered
  from. An epoch closes badly at full pressure or well after four years held,
  and the next one can follow; the chronicle keeps all of them.
- A situation waiting on an answer is a field on the `Game` with an `.over`
  flag, like a battle or an open trench, so the navigation guard diverts to it
  and it survives a save.
- **The checks found two things.** The Cartel ending was unreachable by
  construction — 25 systems' prices demanded, 17 to 24 markets in a sector,
  which is the same defect as a work gated behind a technology that does not
  exist; it is a share of what exists now. And `test_play`'s standing "every
  ending can actually fire" check caught that five new endings had been added
  without extending it.
- Two of my own measurement errors, caught before they became findings:
  measuring a card that buys time while the gauge sat at its floor of zero
  ("said −9, moved 0"), and a fixture that priced the first thirty systems
  rather than the twenty that have markets.
- Suites: 48 — 391 checks green. 203 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: an opening worth choosing (asked for)

- **Asked for more choices at the start: ship, crew, starting place, race and
  background.** Every chronicle used to open the same way — a NAVIS called
  *Patient Increment*, three officers, five technologies, the Charter capital —
  and every one of those was already a real axis in the simulation that was not
  the player's to pick.
- `data/beginnings.py` adds three **stocks** (substrate, not ancestry: Wet
  crews breathe, Dry Choir ones do not and nothing they fly ever mends, Grafted
  pay both bills), six **origins** (Charter Surveyor, Yards Journeyman, Freehold
  Grafter, Choir Cantor, Bloom Survivor, Registry Fugitive), a **hull** from
  those the stock will crew, and five **postings**. Each carries what it gives
  *and* what it costs, and the screen's fourth column is the chronicle you would
  actually open — pinned by a check that opens it and compares.
- **The invariant that mattered most**: `new_game()` with no choices is exactly
  the game as it shipped. Three hundred and eighty checks are written against
  that opening; a default that quietly differed would leave all of them passing
  while measuring a different game. The canonical origin's deltas are all zero
  and a check compares hull, outfit, purse, standing, crew and start across
  three seeds.
- **It found a live soft-lock in the shipped game.** The NAVIS launches with a
  Reaction-Mass Organ, a Radiator Bloom and a Mining Root whose technologies
  were not in `STARTING_TECH`, and the Refit tab offers Remove on every fitted
  part. Pull the drive on day one and `parts_available("drive", …)` returns an
  empty list: the slot can never be filled again, jump falls to the bare
  chassis, and nothing tells you. Fixed structurally — whatever `new_game`
  fits, it grants the technology for — so no future hull can reintroduce it.
  Verified by putting the old constant back.
- **A second defect, from the same checks**: the stock's effects were stored on
  the Game and never folded into `bonuses`, so "superb instruments" was a
  sentence the simulation did not read. `test_orders` caught it as a field
  written and never read.
- Suites: 47 — 383 checks green. 199 modules, all under 500 lines.

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

## 2026-07-28 — SEEDFALL: somewhere to take a cargo

- **Took the task I deferred last cycle**, and the measuring went four rounds
  before it told me the truth.
- **First finding: the runs exist and are invisible.** Within a starting jump
  only 5% of lane/goods pairs show a positive spread — but there are about
  twenty per sector, worth up to 1,400 a tonne, and the rate climbs to 16% as
  the drive improves. Finding one meant visiting every neighbour and writing
  down prices first. So: an information problem, and I built a freight desk
  with two honest sources — your own register, and the harbourmaster, who names
  his own power's ports and what they are short of without quoting their board.
- **Then a bug of mine, found by flying it.** Zero runs at Halcyon Wake, every
  time. `COLD` was −8, the floor of the Neutral band — and the Dry Choir
  *starts* at −10. A new captain standing on a Dry Choir quay was locked out of
  the whole mechanic on day one for no reason of their own. Set against the
  standing bands now, at Distrusted.
- **Then the careers still lost money, with 35 runs made.** Traced one:
  the desk said the port paid 590, it paid 530 by the time the hull got there,
  and the margin had been 14. The desk was recommending spreads smaller than
  the noise — `tick_market` moves supply about 1.8% a day with a random walk on
  top.
- **Then I nearly tuned my way out of it.** I had confidence discounting the
  *takings*, which says you only receive three quarters of the price; removing
  it made things worse, because the wrong model had accidentally been filtering
  bad runs. Rather than keep adjusting the knob I flew 120 openings and banded
  the outcome by advertised spread: every band under a fifth loses money on
  average. `MIN_SPREAD` is 0.20, derived, with the table in the source.
- **Result: 981 credits on your own notes, 33,069 following the desk**, over
  two-year careers — and the desk now refuses to name a run rather than name a
  bad one.
- **The efficacy harness caught my probe measuring the wrong scenario.** It
  noted every port in the sector first, and for a captain whose register holds
  everything the harbourmaster has nothing to add — so the lever read as inert,
  correctly. Rewritten for a captain who has not been there yet, which is the
  case the feature is actually for.
- **Honest about the limit.** Short-range legal arbitrage is thin because
  ports of one power want the same things; trading means crossing into
  somebody else's space. I checked the early game is not stranded by it: all
  twelve openings have affordable work on the contracts board, which last
  cycle's fix made pay properly.
- **`levers.py` crossed 500 lines** as the list grew; the newer probes moved to
  `probes.py`, split by age rather than theme, because a cargo probe belongs to
  `customs`, `trade` and `contracts` equally.
- Suites: 36, **7 freight** (new) among them — 301 checks green. 177 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a board that was half traps

- **Used last cycle's extraction to measure trading for the first time.**
  Moving buy and sell into `sim/trade.py` made an honest trading career
  something a script can fly. So I flew ten of them, and every one lost money.
- **The driver was not the problem this time — but the first finding was
  still not the real one.** Honest arbitrage is close to dead: only 10–14% of
  lane/goods combinations are profitable anywhere in a sector, 1–9% within a
  starting jump, and **six of twelve openings offer no profitable legal run at
  all** from the first port. The spread is 20%, so a destination has to price
  25% above the source, and your neighbours are usually your own power's ports
  with the same supply skews.
- **Which made the contract board the intended answer, so I checked it — and
  it was a trap.** `shape()` priced a cargo contract at
  `amount * (base * 0.55 + rate * 0.4)`. `base * 0.55` is the *floor* price:
  what a market holding none of a good will pay for it. Nobody sells at the
  floor; a counter with stock charges about `base * 1.1`. So the board priced
  its own work against a number that does not exist. Measured: **44% of cargo
  contracts paid less than buying their cargo cost at the port that posted
  them**, worst case −50,151 credits on a silicon prospecting job.
- **The inversion was cruel in the right way to go unnoticed.** Cheap goods
  survived because the flat rate term carried them; it was silicon, magnetite
  and trehalose — exactly the cargoes worth carrying — that were guaranteed
  losses. And the card showed a fee and nothing else, so a trap looked
  identical to a living.
- **Priced against real cost now**, with distance paying *haulage* per tonne
  per light-year rather than multiplying the value of the goods — the old
  multiplicative premium turned an eighty-tonne silicon run into 130,000 clear.
  Worst contract now clears +989, median +12,311. And the board shows the
  arithmetic: "Cargo costs about ₡39,060 here — clears ₡27,975".
- **A bug in my own fix, caught by the equivalence check.** The quote priced at
  rep 0 with no trade bonus while the player pays their own price, so it was
  wrong by two per cent. Generation must price neutrally — a fee cannot depend
  on who reads the board — but a quote must price for the captain standing
  there. Both, now.
- **And a check of mine that measured the wrong thing.** My haulage check
  asserted reward/cost < 4 and failed at 11.7x — on ore hauled a long way. That
  is not a fault: freight is priced by mass and distance, so a tonne is a tonne
  in the hold and the ratio to a cheap good's value says nothing. Rewritten to
  measure net and net-per-tonne, with the reasoning written down so the next
  person does not re-tighten it.
- **The arbitrage finding is queued, not acted on** — fixing the contract board
  and redesigning the trade economy in one cycle would have been two things.
- Suites: 35, **6 cargo** (new) among them — 293 checks green. 173 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: no screen writes the ledger

- **The debt I flagged twice, paid.** Seventeen sites across four view modules
  spent credits and moved standing directly. Buying, selling, signing an officer
  on, paying the bridge a bonus, repairing a hull, paying for a lead,
  commissioning bench time, breaking a hull up, tying up at a quay, and moving
  contraband off the books — every one of them a rule that only a mouse could
  perform and no headless run could measure. Same defect as last cycle's
  engagement aftermath, spread thinner across more files.
- **Eleven operations moved down**, into `sim/trade.py` and `sim/services.py`
  (new) and into `crew.py`, `shipyard.py`, `customs.py` and `minigames.py`
  where they belonged. `port_view.py` went from 484 lines to 427 and the views
  now call and draw rather than decide.
- **The rule is enforced now, not stated.** `test_layers.py` matches ledger
  writes structurally — assignment to `.credits`, augmented assignment,
  `game.rep[…] = …`, any call to `adjust_rep` — across every module under
  `ui/`. Putting one line back names the file and the line number.
- **It carries a self-check, and that was not paranoia.** A structural matcher
  that silently matches nothing would have passed on the day the defect was at
  its worst — which is precisely the failure mode this project has hit before,
  twice, with regression checks that passed with the fix removed. The check
  plants all three shapes of write and fails if it recognises fewer than three.
- **And an equivalence check**, the same discipline the aftermath got: buy
  twelve tonnes and sell five, once through `sim/trade.py` and once by clicking
  the port screen, and fail unless credits, standing and hold come out
  identical.
- **The Qt check moved** out of `test_aftermath.py` into `test_layers.py`,
  where somebody looking for the layer rule will actually find it. Neither
  breach the project suffered was an import pointing the wrong way; both were
  rules written upward, so the Qt half was never going to be enough on its own.
- Suites: 34, **5 layers** (new) among them — 286 checks green. 172 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: what the ground told you

- **Three wrong measurements before one right one.** Setting out to check
  whether an expedition pays, my first driver stranded 40 parties out of 40 and
  reported the ground game as worthless. It was the driver: it never went home.
  Second version budgeted one supply per step when rough ground costs two, and
  still stranded 26 of 40. Third version returned 28 of 40 but priced the haul
  through `sell_price(market, "credits")`, which returns None — so the single
  largest reward in the ground game, 900–3,400 credits a find, counted as zero.
  Only the fourth attempt measured the thing I meant to measure. I have made
  this exact mistake before, on the combat balance harness, and changed real
  numbers on false evidence; this time I checked the driver first.
- **The honest number: 1,438 credits, 8.8 research and 7.3 study for 37
  party-days** — about 39 credits a day against ~750 for charting. Low, but
  the ground clock and the ship clock are not the same thing, so I have written
  it down rather than acted on it.
- **What the measuring actually found was better than a balance problem.**
  Recovered lore lived in `expedition.lore`, was read out once in the report
  dialog, and went out with the expedition object when recovery set
  `game.expedition = None`. It never reached the `Game`, never appeared in the
  codex, and `REWARD_SCALE["lore"]` was (0, 0) — so finding one granted nothing
  whatever. Three feature options across two features existed purely to print a
  sentence and take it away, and eight written discoveries sat in the data under
  a comment calling them "the reason anyone reads an expedition report twice",
  which you could not do.
- **Notes have identity now** and are filed against the game with the body, the
  system and the day. There is a Field notes tab in the codex, and each one is
  evidence on an inquiry track — 206 points across three tracks, so a party that
  reads the room is doing something no other activity in the sector does.
- **A note is not cargo.** Stranding costs 60% of the haul; it does not cost
  what somebody already read and remembered. That is a check, not an opinion.
- **Proved it bites** by restoring the throw-away: three of eight checks fail,
  including the save one, which reports "nothing to save".
- Suites: 33, **8 notes** (new) among them — 282 checks green. 169 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: what a fight leaves behind

- **I said last cycle I would take the `test_reachable` task next unless a
  bigger hole turned up, so I measured it first.** Across 473 public functions
  the bare-name matcher currently masks *zero* real orphans — the five
  candidates are my own scratch matcher's false positives (aliased imports,
  re-exports, decorators, callables passed as arguments). So that task would
  prevent a future defect rather than fix a live one, and it lost again to
  something that was actually broken. Worth saying plainly rather than quietly
  reordering.
- **Every consequence of an engagement lived in `ui/battle_view.py`.** The
  salvage, the loot, the cargo pulled off the wreck, bounty progress, seized
  xenology files, instar kills, consorts lost, loyalty, and every standing
  change that follows from shooting at somebody. `sim/combat.py` held a loot
  dict and nothing else. That breaks the one-directional rule the project is
  built on, and it meant nothing headless could resolve a fight: every balance
  run that fought a battle collected no loot, no standing, no bounty credit.
- **It is `sim/aftermath.resolve()` now** and the view reads what it returns.
  `battle_view.py` went from 468 lines to 425 and stopped importing six sim
  modules it no longer needs.
- **A kill told only its victim.** Destroying a Concordat hull was −14 with the
  Concordat and nothing to anybody else, in a sector whose entire politics is a
  relations matrix. It now pays the victim's rivals a share on the same
  severity ramp `allegiance` uses: measured, a Concordat kill gives the
  Freeholds +3.4 (they are at −45) and the Charter +0.6 (at −20), and leaves
  the Dry Choir cold (+5). At peace nobody gloats at all.
- **A Bloom kill used to please the Charter alone, hardcoded, in a screen.**
  All four powers approve of one less instar now.
- **The check the project never had:** no module under `sim/`, `data/`,
  `world/` or `core/` may import Qt. 93 modules, clean — but it was never
  verified, and the rule it protects had just been broken in spirit for the
  whole life of the combat screen.
- **And the sharper one:** the same engagement is played out twice, once
  through the sim and once through the view, and the credits, standing and
  research must come out identical. Paying a 250-credit bonus from the screen
  fails it and prints both ledgers side by side.
- **Found and did not fix:** 17 more sites across four view modules still write
  `game.credits` and `game.rep` directly. Same defect, spread thinner. That is
  a four-file refactor and would have meant starting a second thing, so it is
  queued rather than half-done.
- Suites: 32, **8 aftermath** (new) among them — 273 checks green. 166 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a chart worth the flying

- **Exploring was the worst-paying thing in the game by about fifty to one.**
  Measured before writing anything: charting the five-body home system takes 53
  days and the chart sold for 1,510 credits — 28 a day, against roughly 1,600
  for a smuggling run. Charting the *entire* 42-system sector and selling every
  chart came to 55,014, which is about one run of unlicensed seed. Meanwhile
  `intel.py`'s own docstring called the Charted level "the only one worth
  anything to a buyer, and the reason to go back to somewhere you have already
  been". The code said one thing and the arithmetic said another.
- **`survey_value()` priced a chart by weight** — `460 + 210 * len(bodies)`.
  A system with a buried Abyssal site, nine catalogued organisms and ground
  worth crossing the sector for fetched exactly what five bare rocks fetched.
- **A chart is information, so it is now worth what it says.** Relics,
  anomalies, life, ore grade, somewhere to tie up, Bloom, and how far it is
  from the buyer's nearest holding. Dearest chart in a sector is about 10x the
  cheapest, so which system you go and chart is a decision.
- **And it is worth that to somebody in particular.** The Dry Choir pays over
  the odds for wet cognition and anything unaccounted for; the Yards want rock
  and somewhere to stand a hull; the Charter wants anything alive, anything old
  and early warning. Best and worst buyer differ by 1.6x on average, and the
  best buyer varies by system — so a chart is something you carry to the right
  quay rather than sell where you happen to be standing.
- **Charts go stale**, decaying to 45% over two years, which makes a survey
  circuit a living rather than one sweep of the sector.
- **I overshot on the first pass and the measurement caught it.** The initial
  price list made a remarkable system's chart worth 92,000 — over three times
  the best contract in the game — and charting worth 1,137 credits a day. That
  fixes exploration being worthless by making it the best-paying thing in the
  sector. Rescaled against the actual economy (best contract ~27,000, dearest
  hull 900,000) to a median chart near 26,000 and about 750 a day.
- **A second measurement error, in my own check.** The "charting is a living"
  check first read 1,127 credits a day off a single seed. Across ten seeds the
  median is 763 and the range 630–837 — the seed I happened to pick was half
  again the median. The check now averages six sectors, so the band is set by
  the distribution rather than by luck.
- **Proved it bites** by restoring the flat rate: four of eight checks fail,
  the last reporting "charting still pays 35 credits a day".
- Suites: 31, **8 charts** (new) among them — 264 checks green. 164 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: contested ground

- **The sector had claims and it had holdings and they never touched.**
  `ventures._claimable()` explicitly excluded any system the player held a
  colony in — the powers politely stepped around your ground — and
  `colony.can_found()` never looked at `system.faction`, so you could plant
  inside somebody's declared space and nobody said a word. An empire game where
  territory is never contested has the empire taken out of it.
- **Both directions are live now.** Planting on a power's register costs
  standing with them (and pleases their enemies, via last cycle's allegiance
  module), and at Distrusted they simply will not have you. The cost is shown
  in the plant-a-seed dialog, before you commit, rather than in the log after.
- **A power will annex ground you hold**, and that is a question rather than a
  news item. Three answers, all measured to be genuinely different: pay the
  levy and keep it, giving up 30% of what it makes; hand it over and read best
  with them; or refuse — which keeps it, costs 18 standing, and means somebody
  comes for it eventually. 12 of 12 defiant holdings were seized within eight
  years. If the claim later lapses, the standoff ends with it.
- **The demand lives on the `Game`**, because it is something you can be in the
  middle of. `test_resume` picked it up as the sixth guarded activity without
  being told — which is exactly why that check was written as a rule about
  `window.go()` rather than a list of activities.
- **A bug in my own test helper, found by a seed that disagreed with me.** One
  of twelve trials failed with an empty assertion message. The cause: a holding
  can mature *and* be overgrown by the Bloom inside the same `advance_days`
  call, so `colony.online` was True on an object already removed from
  `game.colonies`. The helper now asserts membership rather than a flag, and
  keeps the Bloom out of the system so the check measures territory and not
  luck.
- **Proved the central check bites** by restoring the one-line exclusion that
  made territory uncontestable: exactly one check fails, and it says "the
  powers still step around anywhere the player holds".
- Suites: 30, **8 territory** (new) among them — 255 checks green. 161 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: whose work you take

- **`contracts.py` did not import `diplomacy`.** Six powers, a relations matrix
  that starts hostile in most pairs, and the thing a player actually does all
  day touched none of it. You could run the Charter's deliveries, collect a
  Concordat bounty and take Freehold prospecting money in the same week while
  all three were at each other's throats, and every one of them thought better
  of you for it. Standing was accumulation with no tension anywhere in it.
- **Serving a power now costs you with its enemies**, in proportion to how bad
  the rift actually is. The precedent was already in the game and inconsistent:
  diplomacy actions offended rivals (crudely — a flat −4 that ignored the
  severity), ventures offended a named other party, and contracts, by far the
  most frequent faction interaction, offended nobody. One module now does it
  for all three, and the flat −4 is gone.
- **The penalty is not the point. The escape is.** Severity ramps from nothing
  at −15 to full at −70, so dragging a pair from implacable to merely bad is
  worth doing. Measured across the same 28 jobs: 108 total standing in a
  hostile sector, 170 in a brokered one — and the per-power split goes from
  62/18/8/25 to 80/40/35/25. The relations matrix finally has a job in ordinary
  play instead of only at the Concord ending.
- **It enforces an order rather than closing a door.** Serve one power
  exclusively and you end up its partisan: Charter +100, Concordat −30,
  Freeholds −42. Make peace first and you can still work all four to Kin, so
  the Concord is reachable — you just cannot get there by being everyone's
  courier. Verified both directions, since a penalty that quietly foreclosed an
  ending would be a worse bug than the one I set out to fix.
- **The Dry Choir falls out as the neutral employer** — nobody is at odds with
  them at the opening, so their work costs nothing. That was not designed; it
  is what the opening relations happen to say, and it gives the map a safe
  harbour worth knowing about.
- **Proved all three checks bite** by reintroducing each defect: a flat
  threshold instead of the ramp fails exactly the gradient check and nothing
  else, and dropping the charge fails both integration checks — the second
  naming the discrepancy outright ("quoted charter −2.4 and actually moved
  −0.0").
- Suites: 29, **8 allegiance** (new) among them — 245 checks green. 157 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a run worth making

- **Contraband was free money and nobody had noticed.** Unlicensed seed was the
  dearest good in the table and flagged illegal, and neither fact did anything.
  The Freeholds both sold it and bought it, so a hold full of it never had to
  cross anybody else's space; nobody ever looked in the hold; and the standing
  penalty for selling it did not apply at the ports where you sold it. Measured
  across six sectors before writing a line: +971 to +2,118 the tonne against
  +997 to +1,680 for the best legal arbitrage anywhere in the sector.
- **The Charter's entire identity is the licensing regime**, and you could fly
  a hold of unlicensed seed through their space unexamined. Both halves are in
  now: a power that outlaws a good has no posted price for it and a much better
  unposted one, and that same power opens your hold at the dock.
- **Neither half is worth having alone.** A premium nobody can seize is what
  the game already had. A search with nothing worth carrying through it is a
  tax nobody would choose to pay. The run now goes Freeholds → Charter space,
  which is the one direction it never went before.
- **The first cut was a trap and playing it said so.** Both careers — bare hull
  and fully fitted out — ended down: heat went on faster than it came off, so
  the premium fell under the buy price and the odds pinned at the ceiling.
  Retuned the cooling rate and the fine against measured careers rather than
  taste. Now: bare hull +188k over eight runs, fitted out +402k with half the
  seizures. Committing to the trade roughly doubles it.
- **Mitigations multiply rather than subtract.** My first version subtracted
  them, so a void hold plus a manifest loom plus Trusted standing drove the
  odds under the floor — a smuggler who could not be caught. They now take a
  share each: 21% bare down to 9% fully fitted out, and never zero.
- **The screens found a bug I had written myself.** Rendering the quiet word on
  a Concordat quay showed the posted market *also* still listing Unlicensed
  Seed with a live Sell button — you could hand contraband over the desk at the
  station whose boarding party exists to stop you. The market now reads "seized
  on sight" with no counter, and the check that pins it names the defect
  exactly when I put the button back.
- **And one I caused elsewhere.** Two new parts went straight into the NPC
  outfit pool, so enemy warships started rolling smugglers' false manifests and
  the combat-assessment check went red — a feature about trade silently
  re-tuning every encounter. Parts that are kit for a trade are now marked
  `civilian` and NPC loadouts skip them. The guard checks both directions:
  never on a warship, still fittable by the player.
- **`test_verbs` could not see the quiet quay**, the same blind spot the trench
  was in last cycle. Added it: 21 controls with a hold full of contraband, all
  clean.
- Suites: 28, **9 customs** (new) among them — 236 checks green. 155 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a dig you work

- **Excavating was one call.** Press the button, lose twelve days, receive a
  number of points, and occasionally read that the face collapsed. Everything
  the setting says about Abyssal sites — that they are layered, that they are
  fragile, that the interesting part is always under the part that is easy to
  reach — was written in the codex and present nowhere in the game.
- **A site now has four strata**: spoil and overburden, the casing, the works,
  and whatever it was for. Each holds more of the site's understanding than the
  one above it and each is more fragile, so the value and the risk both climb
  together as you go down.
- **Three ways to take a layer**, and the choice is real rather than a difficulty
  slider. Working properly takes a fortnight and loses almost nothing; cutting
  straight down takes four days, spoils most of what is in a deep layer, and can
  bring the face in on the party. Measured over sixty digs: careful 138 points in
  56 days, brisk 121 in 28, cut 47 in 16.
- **That produces an actual strategy** rather than a dominant option: cut through
  the overburden, which holds 8% of the value and spoils at 5%, then work the
  deep strata properly, where cutting spoils at the 85% cap. The screen shows all
  three numbers side by side, so the decision is legible before you commit.
- **Understanding banks per layer, not at the end** — which is the whole point.
  A trench abandoned after the casing is worth the casing, so backfilling is a
  choice rather than a way of throwing the dig away. Restoring bank-at-the-end
  passes every other dig check and fails that one alone; I verified that by
  putting the old behaviour back and watching exactly one check go red.
- **A dig lives on the `Game`**, so last cycle's rule held on its first new
  case — `test_resume` picked it up as a guarded activity with no prompting.
- **`test_verbs` could not see the trench**, since it is only reachable with a
  dig open. Added it: four controls, all clean. That is the same blind spot the
  flee-and-hail NameError lived in.
- **Found a hole in `test_reachable` by falling into it.** I wrote a `summary()`
  in `dig.py` that nothing calls, and the check passed — it matches bare names,
  so any other module's `summary` covers for it. Measured the blast radius
  before reacting: across 433 public functions it currently masks exactly that
  one, and resolving calls to their defining module throws five false alarms
  unless aliased imports and re-exports are followed properly. So: deleted the
  dead function, wrote the limitation into the check's own docstring, and queued
  the real fix rather than bolting it on mid-cycle.
- Suites: 26, **6 dig** (new) among them — 223 checks green. 151 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: put it down and pick it up again

- **A save taken mid-approach lost the approach.** `docking`, `decoding` and
  `decoding_tech` lived on the window rather than the game, so reloading
  silently dropped them: the guard that had been holding you in the docking
  screen simply stopped, and the passes you had spent were gone. It had been
  that way for many cycles and nothing noticed. Last cycle's transit work
  exposed it by fixing only itself.
- **All three are on the `Game` now**, with `Docking` and `Decoding` registered
  with the save codec, and the window exposing them as properties over game
  fields so nothing else had to change.
- **The sharper half is the decoding secret.** Had the code been regenerated on
  load rather than persisted, a player could save, guess, reload and guess
  again against a fresh code until it fell out. The check asserts the secret
  itself survives, not merely that an exchange exists.
- **A `Battle` deliberately stays on the window**, which `battle_state` has
  said since it was written: combat resolves in one sitting and no clock runs
  during it. It is in the check's allowlist with that reason attached.
- **The general check is the one worth having.** It reads `window.go()`, takes
  every activity the guard will divert you into — recognised by its `.over`
  flag — and fails on any that is not a field on the `Game`. Put docking back
  on the window and it reports it by name. A new mode that guards navigation
  and keeps its state on the window now fails the suite rather than quietly
  losing a player's evening.
- **My first version of that check flagged five things that were never state**
  — `self.views`, `self.current`, `self.toast` and friends — because it matched
  every `self.X` in the method rather than the ones with a finished state.
- Suites: 25, **5 resume** (new) among them — 215 checks green. 147 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: a crossing you fly

- **Travel was a wait.** Pick a destination, pay the reaction mass, watch the
  calendar move, occasionally read a line about something that had already
  happened to you. The helm could plot an intercept and route around a star and
  then had nothing to do for eleven days.
- **A crossing now runs in watches.** Two to four of them depending on the leg,
  and a watch may bring something that wants an answer: debris across the
  course, a radiator lobe that will not seat, a bad slug of reaction mass, a
  hull adrift with no beacon, a flare off the star, the intima fruiting, a
  contact on the same lane. Seven of them, twenty options, and every option
  spends one of the three things a crossing has — time, mass, or the hull.
- **The tension is measurable, which is the test.** Flying the same crossings
  hurried against careful: 7.4 days and 0.6% of the hull, against 8.5 days and
  none of it. Neither policy is better on both axes, which is what makes the
  watch a decision rather than a formality.
- **Nothing is charged up front**, so cutting the burn halfway is a real
  option: you keep the mass you have not yet burned and lose what you have,
  and you are where you started.
- **Two things I got wrong and caught by playing it.** The last watch of every
  crossing could never bring anything, because I rolled for events only when
  not yet at the destination — the final leg, when a captain is most tired and
  least stocked, was always the quiet one. And I first held the crossing on the
  window rather than on the `Game`, which loses it over a save exactly as
  docking and decoding state still does.
- **A lever for it in the efficacy harness**, so the watches have to keep
  earning their place: switch them off and a crossing takes 6.5 days instead of
  7.5.
- Suites: 24, **6 transit** (new) and a fourteenth lever among them — 223
  checks green. 146 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: every feature has to move something

- **Reachability was a floor, and I said so at the time.** A function called
  only from a readout passes it: the Bloom's growth multiplier was consumed by
  `summary()` from the day it was written while contributing nothing whatever
  to the simulation. This cycle closes that gap.
- **Ten levers, one per claim the game makes about a number.** Each names a
  feature, a way to switch it off, and a measurement of the world. Neutralise
  the lever, run the same seeded scenario, and the measurement has to move.
  Provocation, hull loading, consort screening, relation drift, ground weather,
  colony works, crew loyalty, market shocks, mining method, research evidence —
  all ten prove themselves, several emphatically: screening cuts damage to the
  flag from 54 to 9, a deep bore doubles what comes off a body.
- **The demonstration that matters**: disconnect the Bloom multiplier again and
  reachability still reports "416 public functions, every one reachable" while
  efficacy fails with "11.45 with the feature, 11.45 without".
- **Two of my probes were wrong before any feature was.** The Bloom one ran
  long enough that every system pinned at its ceiling of 1.0, so a Bloom
  growing half again as fast reached exactly the same total; the research one
  stocked the bench full in *both* runs and compared full against full. Both
  read as inert features when the features were fine — a saturating or
  already-satisfied probe is the failure mode to watch for here.
- **And I got the sign convention backwards on every lever at once**, which was
  at least an efficient mistake. The field is now named for what happens when
  the feature is *removed* rather than what it does when present.
- **The harness carries two checks on itself**: that a deliberately decorative
  feature fails it, and that every lever's substitution actually changes its
  number rather than quietly missing its target. A harness that cannot fail is
  worse than none.
- Suites: 23, **13 efficacy** (new) among them — 203 checks green. 142 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: nothing written and never called

- **Three cycles running, a feature shipped a number the game never read** — a
  levy counter, a death reason, a Bloom growth multiplier. The `Game`-fields
  check catches persistent state; this is the other half. `test_reachable.py`
  walks the package and fails on any public function called from nowhere at
  all.
- **It found three real holes, not just dead code.**
  - **Treaties bought nothing.** `treaty_bonus()` promised that signing made
    everyone easier to trade with and was called by nobody, so a treaty cost
    goods, paid standing, and added a label. It is folded into the trade bonus
    now: four treaties move it 0.00 → 0.12.
  - **Instars could not be killed.** `kill_instar()` was called from nowhere,
    so roaming masses seeded systems and ate colonies with no counterplay
    whatever — and the provocation table paid seventy for a kill nobody could
    make. A mass in your system is now announced and can be intercepted.
  - **Convictions never felt your standing.** `loyalty.align()` — a
    Charter-raised officer taking your Charter standing personally — existed
    from the day convictions were written and was called by nothing. It runs
    from `adjust_rep` now.
- **And fourteen genuinely dead functions removed**, including
  `planets.extraction_rate`, orphaned when mining was rewritten.
- **Two things the check taught me about itself.** `return None` is not a
  result — counting it flagged every early-exit function, and the self-check
  caught that on its first run. And restricting the scan to value-returning
  functions missed `kill_instar` entirely, which mutates and returns nothing;
  widening it to every public function added exactly one more finding and no
  noise at all.
- **What it does not catch, stated in the check itself.** A function called
  only from a readout, or only by the suite, passes. The Bloom's growth
  multiplier was consumed by `summary()` from the day it was written while
  contributing nothing to the simulation — I verified this check would have
  passed on it. Reachability is a floor, not a guarantee.
- Suites: 22 of them, **4 reachable** (new) among them — 190 checks green.
  139 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the Bloom starts paying attention

- **The arc had two ends and nothing between them.** Growth is detected, it
  spreads on a timer, and eventually you burn into the heart. Five stages,
  roaming instars and weapon-family resistance were all in place, and none of
  it responded to *you*.
- **Provocation is the middle.** Burning a system, clearing one, killing an
  instar and striking the heart all cost it something, and it keeps count.
  Past each threshold it answers: it grows harder, then it hardens
  specifically against whatever family you have been using, then it detaches a
  seeding wave, and finally it starts sending masses after your hull across
  nine light years without stopping at the colonies on the way. Provocation
  bleeds away if you leave it alone, so this is a response to a campaign rather
  than a doom counter.
- **Study or burn, not both.** Nine days alongside a living mass yields
  xenolith and readings scaled by how much of it there is — and it grows while
  you watch. Burning it removes exactly the thing you would have studied. The
  setting has always described that tension and the game had never once made
  you feel it; the system screen now offers both buttons side by side with what
  each is worth.
- **I nearly shipped the levy bug again.** `growth_multiplier()` was computed
  from the responses and read by nothing whatever — the Bloom would have
  "answered" by printing a line and changing nothing at all. It is now consumed
  in `threat.tick`, and the check measures actual spread with and without,
  because a multiplier nobody reads looks exactly like one that works. It fails
  against the unwired version: "spread 35.0 against 35.0".
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, 7 balance,
  **7 bloom** (new), 7 verbs, 23 interface — 186 checks green. 138 modules, all
  under 500 lines.

## 2026-07-28 — SEEDFALL: every verb in the game, driven once

- **Rendering a screen does not press its buttons.** Splitting `combat.py` last
  cycle left fleeing and hailing calling names that no longer existed, and
  nothing noticed — `test_ui.py` draws every screen and passed throughout. The
  new suite clicks **210 enabled controls**: the ten standing screens, an
  engagement in progress, a party on the ground, all four port tabs, and both
  mini-games, each on a fresh game because clicking one control can end the
  fight or spend the money the next one needs.
- **The trap that made the bug invisible is worth stating.** Qt *swallows*
  exceptions raised inside a slot — it prints a traceback to stderr and carries
  on, so `button.click()` returns perfectly happily and the obvious version of
  this check sees nothing at all. Catching them needs a `sys.excepthook`. I
  verified the whole thing by reintroducing last cycle's bug: it reports
  `battle/'Hail them': NameError name 'is_destroyed' is not defined`.
- **And a check for the trap itself**, because if the hook ever stops working
  every verb check goes quietly green whatever is broken.
- **Also driven on a wreck**: the same controls with no money, no crew, no air
  and a hull open to space — 78 of them stay enabled in states their handlers
  were never written for. All clean, which is a genuinely reassuring answer
  rather than a vacuous one.
- **What it did not find is worth saying too.** No new bugs: 210 controls in
  five contexts, plus 78 on a wrecked ship, all ran without raising. The value
  this cycle is the check, not a fix.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, 7 balance,
  **7 verbs** (new), 23 interface — 179 checks green in about seventy seconds.
  135 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: difficulty that means something

- **Encounter difficulty was very nearly decorative**, and three separate
  things were wrong. Every weapon below tier two is grown-family, so a
  *fabricated* warship at low difficulty could mount none of them and arrived
  unable to fire a shot — 100% of scale-one Concordat hulls were unarmed. The
  chassis was drawn uniformly from the faction's whole list, so a scale-four
  patrol could turn up in a scout. And `tier = round(difficulty)` is a step, so
  everything from 1.5 to 2.4 drew identical parts.
- **All three are fixed**: armament is fitted separately and the tier rises
  until something fits, hulls are drawn weighted toward the threat, and a
  fractional difficulty rolls between the tiers either side of it. The curve
  now descends smoothly across eight steps instead of falling off a cliff
  between 2 and 3.
- **The real culprit was nerve.** Resolve drained on `(turn - 9) × 0.45`,
  purely on the clock, and the enemy lost it *twice as fast as the player*. A
  hull with no armament at all drove off a scale-four battleship 75% of the
  time by sitting there. Nerve now turns on damage taken, being behind on
  damage, and futility — an unarmed hull wins 6% at scale four, while a TESTUDO
  built to be hit still wins by outlasting, which the game has always said it
  should.
- **I spent an afternoon tuning against a measurement artefact.** My harness
  reused one ship object across every fight, so the second fight onward started
  with a wreck. That read as "encounters are brutally hard", and on that basis
  I changed armour from subtractive to diminishing and tripled enemy hull —
  both reverted once a fresh hull per fight showed the player was in fact
  winning almost everything. The note is now in `INTERFACE.md` and at the top
  of the balance suite.
- **Splitting `combat.py` at 504 lines broke fleeing and hailing**, and nothing
  in the suite drove either path — every attempt to break off would have raised
  `NameError` in a live game. There is a check for both now.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, 6 assessment, **7 balance** (new),
  23 interface — 172 checks green. 134 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a defeat that teaches something

- **You could lose a NAVIS in two turns and be told nothing.** Combat had arcs,
  bands, crew stations, consorts and abilities, and a scrolling list of damage
  lines. Playing a losing fight, the one actionable line — "nothing will bear
  at this range" — was buried among fourteen hits, and nothing before the first
  shot suggested a scale-3 battleship would end it inside a minute.
- **The read** now sits beside the plot: who breaks whom first, what the enemy
  is armed for and doing, whether you can outrun it, which of your mounts are
  bearing and by how many degrees the rest are off, and two or three things
  worth doing about it. Against that battleship it opens with "outmatched",
  "they break you in 3 turns", "can you outrun them: no", and "breaking off
  costs you very little; this does not."
- **My first model was worse than useless — it was not even monotonic.** I
  compared raw hull and raw damage, and measured it: a scale-0.5 scout read as
  a *harder* fight than a scale-2 warship. Enemy hull turns out to be a chassis
  lottery that ignores difficulty entirely, while armament (0 damage at scale
  1, 121 at scale 3) and armour both track it. Comparing turns-to-break after
  armour fixed the direction.
- **Then the thresholds were wrong, and only measurement found it.** A ratio of
  0.19 was reading "outmatched" in fights the player won 70% of the time,
  because most wins come from the enemy breaking off rather than dying — a pure
  damage race reads far bleaker than the game plays. The bands are now set from
  320 fights across two hulls and eight difficulties, and the reasoning is
  recorded beside the constants.
- **The check that matters** plays forty fights and fails if a worse-sounding
  verdict wins more often than a better-sounding one. Against the raw-hull
  model it fails exactly as it should: outmatched 31%, lighter hull 37%, a real
  fight 25%, heavier hull 39%.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, 8 orders, **6 assessment** (new), 23
  interface — 165 checks green. 132 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: an audit, not a sixteenth system

- **The seam was discoverability.** Fifteen cycles each added a system that was
  perfectly obvious to whoever had just built it. A first-time captain got a
  sector chart, one line of log — "The Patient Increment is under way" — and no
  indication that commissions, consorts, colony works, the research bench or
  the register existed. Checking every screen on turn one for a trace of each
  system found three entirely invisible and several behind tabs nobody had a
  reason to open.
- **Standing orders** are the fix: twenty conditions worth acting on, each with
  a predicate and a screen it points at, the four most pressing shown above the
  chart. A brand-new captain is now told that a commission is on offer, nothing
  is on the bench, nothing here has been surveyed and there is word going
  round. Ten years into a game the same panel leads with the Bloom.
- **Placement was the whole point and I got it wrong first.** The panel went in
  below the chart and the system detail, where a first-time player would never
  scroll to find it — the exact problem it was written to solve. It reads
  compactly now and sits directly under the heading.
- **A check for state written but never read found two more seams.** A levy
  venture incremented a counter that nothing anywhere consulted: the venture
  succeeded, the save grew a number, and the sector was exactly as before.
  Levies now make everything that power tries next easier, which is visible on
  the diplomacy desk. And `death_reason` had been recorded on every death since
  the game was written and never shown — the game always knew why you died and
  simply never said.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, 6 design, **8 orders** (new), 23 interface — 159 checks
  green. 129 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: mass is the price of everything

- **Fitted mass was free.** A NAVIS carrying 267 tonnes of armour and reactors
  flew exactly as fast as one carrying 52, and jumped *further*, because
  nothing anywhere read the tonnage. Every design was therefore the same
  design: the heaviest, best part in every slot. Loading now sets speed,
  evasion and (dampened) jump range.
- **The trade is legible.** A maxed NAVIS with a full hold reads "overloaded"
  at 1.32 of its capacity and pays 18% of its loading factor; a stripped one
  reads "light" and gains 14%. The design sheet shows fitted mass, loading
  against capacity, and what it is costing — beside the existing power deficit,
  so two tensions now argue with each other on the same screen.
- **Heavy is not simply worse.** A second drive adds 210 tonnes and buys 6.9 ly
  of jump range. That is the design question: what do you want the hull to be
  good at.
- **I calibrated it wrong twice, and the play-testing caught both.** First I
  sized capacity against `chassis.mass_t` — which runs from a sixty-tonne SPORE
  to a twelve-billion-tonne LEVIATHAN, so every hull read as "light" and the
  penalty never engaged. Rebasing on slot count and hold rating put it on the
  right scale, and then I calibrated against fully-maxed fits and found every
  chassis pinned at the floor: a realistic design fills two-thirds of its
  slots, not all of them with the heaviest thing available. The check now
  builds all thirty-five hulls at a sensible fit and fails if any is penalised
  for it.
- **The stranding trap was live again.** Loading cuts jump range as well as
  speed, and a captain who fills the hold and cannot reach the nearest system
  is the deadlock this project has hit twice before. Jump takes the loading
  effect at 45% strength, and the check measures a fully laden starting hull
  against its nearest neighbour: 98% of empty range, 2.7 ly of margin.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, 8 politics, **6 design** (new), 23 interface — 151 checks green.
  125 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the powers start doing things

- **Diplomacy waited for the player.** Four factions tracked how they regarded
  you and each other, and nothing they wanted ever made them act. They now run
  **ventures** on their own account: annexing an unclaimed system, embargoing a
  rival, courting one, raising a levy, letting a concession, or assembling a
  censure. Each runs a season or two and resolves whether or not you were
  involved.
- **You can back one, work against it, or let it happen.** Backing costs
  credits and buys standing with the sponsor at the expense of its target;
  opposing costs standing and needs only nerve. Either moves the odds by 30
  points. Letting it happen is a choice too — over twelve years the powers
  annexed five systems between them without asking.
- **The first version quietly broke a victory condition.** Every blockade and
  censure is a permanent debit to a pair of relations, and nothing ever pushed
  the other way: the worst pair slid from -45 to -94.5 within a decade and kept
  going. Concord needs *every* pair at +15, so a long game was foreclosing an
  ending the player is entitled to reach, through pure background churn.
  Grievances now fade toward where the sector rests; relations reach
  equilibrium around year ten instead of sliding, and a determined broker
  reaches Concord in 4/4 test games.
- **My first attempt to measure that was wrong twice.** I advanced twenty years
  in a single `advance_days` call and saw nothing move at all — the tick does
  not iterate, so four ventures were created and none resolved. Then, having
  fixed the measurement, my regression check *passed with the fix removed*,
  because relations plateau against the -100 floor either way and the emergent
  numbers barely differ. It now tests the mechanism directly: push a relation
  down 40 points, leave it alone for twenty years, and it must come back.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  7 ground, **8 politics** (new), 23 interface — 145 checks green. 123 modules,
  all under 500 lines.

## 2026-07-28 — SEEDFALL: weather on the ground

- **Terrain was fixed and the sky was empty.** An expedition already had
  supply, a rover, hazards and injuries, but nothing about the surface changed
  while you were on it. Seven **weather** conditions now roll in and out over
  the days you are down there: dust storms, whiteouts, radiation squalls,
  downpours, ground tremors and katabatic gales, with clear weather about 57%
  of the time.
- **It bites on all three axes.** A gale takes a two-day crossing to five,
  multiplies the hazard chance by 2.6, and cuts sight to one tile. Measured
  over 24 expeditions, a party covers 13.8 tiles in enforced fair weather and
  11.1 with real weather — the walk home is longer than the walk out, which is
  the whole point.
- **A gale pins the party entirely**, so *Sit out the weather* is always
  available and always costs a day of supply. That is not a convenience: a
  party that can neither move nor die is an expedition that stops, and the
  first version had exactly that hole — the existing playability check spun its
  driver 150 times and failed with "expedition never terminated".
- **Two of my seven conditions were dead on arrival.** I gated whiteouts on
  biomes called "ice" and "frozen" and downpours on "ocean" and "temperate",
  none of which the generator produces — it makes `cryo`, `subsurface`,
  `verdant`, `microbial`, `sulfuric` and three others. Both conditions were
  unreachable. The check now validates every gate against a real galaxy, and
  fails if a condition can never occur.
- **One thing that looked like a bug and was not.** Two direction buttons
  showed no movement cost in the screenshot; I read that as a rendering fault,
  and it was the party standing in the bottom-right corner with two of its four
  neighbours off the grid. Worth confirming from the data before fixing the
  wrong thing.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research, 8 trade,
  **7 ground** (new), 23 interface — 137 checks green. 119 modules, all under
  500 lines.

## 2026-07-28 — SEEDFALL: a market with news in it

- **Prices drifted and nothing ever happened.** Markets already responded to
  what you personally bought and sold, but no event ever struck one. Seven
  kinds of **shock** now do: a blight through the growing stacks, the yards
  downing tools, a convoy that never arrived, a seam coming in, the Concordat
  dumping a stockpile, a quarantine, somebody quietly rearming. Each names
  itself, moves local supply hard, and lifts after a season or two.
- **Shocks are kept apart from supply on purpose.** The daily drift pulls
  supply back toward equilibrium, so folding a blight into it would let the
  drift quietly erase the blight — and expiring it could never restore the
  original price. `Stock.shock` is a separate multiplier, recomputed wholesale
  from the live shocks each tick.
- **The register makes information worth having.** You write down what a port
  pays only while standing in it, and what you wrote goes stale: full
  confidence today, half at two hundred days, worthless at four hundred. The
  market screen now tells you where your own notes say to take what is in your
  hold, how far it is, and how old the note is. Nothing reads a distant market
  directly — that is the entire mechanic.
- **News only reaches you from places you know.** A shock at a system you have
  never visited and hold no colony in happens silently.
- **The regression check that mattered most** puts a shock on a market, checks
  the price moves, then expires it and checks the price comes *back*. Written
  the obvious way — adjust the multiplier when a shock is live — an expired
  shock never lifts, and a long game accumulates permanent distortions across
  the sector. I verified the check fails against that version.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, 8 research,
  **8 trade** (new), 23 interface — 130 checks green. 116 modules, all under
  500 lines.

## 2026-07-28 — SEEDFALL: research grows inputs

- **Research was one pool.** Everything you did anywhere fed a single number
  and a single bar, so nothing you chose to do changed what you could learn. A
  programme now consumes **evidence** of four kinds, each from a different part
  of the game: survey data from charting, specimens from landing parties and
  dives, hardware off hulls you take apart, xenolith readings from digs. A
  propulsion programme cannot be fed by botany.
- **The mix is derived from a technology's branch**, not written out for each
  of sixty-one entries, so the whole tech tree got inputs without being
  touched. Adding a technology needs no work; adding a *branch* does, and the
  suite fails if one is missing a mix.
- **Four approaches, four bargains.** Measured over 24 runs each: careful 120
  days and never a setback; parallel tracks 90 days for nearly twice the
  material; push it 60 days with a 28% chance a season of going backwards;
  reverse-engineer 90 days and cheap, but only if you hold alien work or
  salvaged hardware to take apart.
- **It measurably pays to go and look.** A captain who surveys as he goes
  reaches his first technology in 52 days against 225 for one who simply flies.
- **I bricked the opening and the playtest caught it.** Gating all progress on
  evidence meant a fresh captain who set a project and flew made *literally
  zero* progress — 0.0/150 at twelve months. A bench with nothing on it now
  still runs at 35%: reading, arguing and going over old results. Evidence buys
  the other two thirds. The regression check sets a project on turn one, does
  nothing else, and demands the technology arrive.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, 7 mining, **8 research** (new),
  23 interface — 122 checks green. 112 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: mining becomes a decision

- **Extraction was a rate.** Park in orbit, pick 30 or 90 days, tonnage
  appears. It was the last pillar with no choice in it. A body now has
  **seams** at three depths, and you choose **how** to work it.
- **Four methods, four bargains.** Measured over twenty 60-day runs each:
  *skim* 26 t with no wear and a tenth of the depletion; *open cut* 149 t at
  0.9% hull and 38% worked out; *deep bore* 244 t at 3.2% hull and 81% worked
  out, with mishaps three times as often; *bioleach* 140 t, no wear, 13%
  depletion, but it burns biomass and needs a harvest tendril. A bore reaches
  seams nothing else can, which is often the whole reason to fit one.
- **Depth is derived, not stored.** `hash_seed` of the body and resource, so
  every existing save has seams without a migration and the same rock always
  hides the same thing in the same place.
- **The first version reintroduced a deadlock the game had already fixed.**
  Burying volatiles at depth two meant a captain with no bore and no reaction
  mass had no way to make fuel — exactly the trap the mining root's `drink`
  was added to prevent two cycles into this project. The existing playability
  check caught it on the first run. Fuel now never sits below an open cut, and
  neither does whatever a body is advertised as: a rock listed as ore-bearing
  that needs a shaft is a survey that lied.
- **Two readout bugs from the screenshots.** "Wear on the hull 13.5% a month"
  was quoting damage to the *outermost layer* as if it were overall integrity —
  five times worse than the truth. And a 0.02-grade trace seam listed as
  "0.0 t volatiles/day" made the panel look broken.
- **My own measurement was wrong first.** The initial method comparison
  reported zero tonnes for all four, which looked like the feature was dead.
  I had loaded 400 t of fuel into a 340 t hold, so there was nowhere to put
  the ore.
- Suites: 27 simulation, 5 xenotech, 14 playability, 5 tactical, 5 flight,
  6 empire, 7 crew, 7 missions, 8 exploration, **7 mining** (new), 23 interface
  — 114 checks green. 108 modules, all under 500 lines.

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
