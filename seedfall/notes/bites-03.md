# The parts that will bite you (3 of 5)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

  `moorings.boom_step` runs the arm and `moorings.captured` asks whether it has
  you — and had no way to say no.
- **Power the measurement before you encode it.** `ventures` measured 0.400
  against 0.500 over sixty trials and became a check pinning that gap; at two
  hundred trials it is 0.505 against 0.540, half a standard error. Noise
  written into a guard is worse than no guard, because it reads as evidence
  and the next person believes it. If a check asserts a difference, it owes a
  standard error.
- **A deterministic driver decides nothing about a stochastic tick.** The
  sweep's stateless generator makes `chance(p)` a threshold that clears in
  both runs or neither — so it flagged `approach` and `ventures` as per-call
  when both are identical in play. Ticks that draw randomness have to be
  judged by trials; only ticks that draw none can be judged by structure.
- **Lazily built state records when it was first asked for.** `exchequer.purse`
  is born carrying `settled = game.day`, so any comparison that advances the
  clock before the first call starts the two runs from different stored state.
  It had `exchequer` wrongly flagged in `test_ticks` for a cycle, and it made
  my own probe report a working fix as doing nothing. Give both sides an
  identical first step before letting them diverge.
- **A deterministic driver cannot see a probabilistic defect.** The tick sweep
  uses a stateless generator so only structure shows — which turns `chance(p)`
  into a threshold that clears in both runs or neither, and makes a genuinely
  per-call roll look like a rate. `ventures` needs 60 trials under a real
  generator to show 0.400 against 0.500. Two kinds of defect, two kinds of
  measurement.
- **A tolerance is part of the claim, not a weakening of it.** `test_ticks`
  first demanded two chopping of a span agree exactly, and that is
  unachievable for any tick applying two per-day rates in sequence — they do
  not commute, so interleaving them thirty times lands a fraction away from
  doing each once. The check is for finding ticks that are *materially*
  per-call; the residue is convergence and shrinks with the step.
- **Mutate every part of a fix, not the fix as a whole.** Three changes went
  into `loyalty` and only one was load-bearing: the dead-band I removed never
  fires, and linear-versus-compounding drift is 0.13 of a point. Both
  mutations came back green, which is the only reason I know. A fix described
  as three repairs when it is one is a docstring that will mislead the next
  person.
- **Validate the instrument before believing the measurement.** The tick sweep
  first reported all fourteen subsystems as per-call, which is not a credible
  result — a decay tick cannot be per-call. Two fresh games from one seed did
  not match, because `Ship.uid` and `Officer.id` climb across games from module
  counters. A verdict that indicts everything is a broken probe, and the
  control that would have caught it costs two lines.
- **A sensitivity control needs a change bigger than the resolution.** The same
  file's probe failed twice more: five days of memory decay is 0.27% against a
  print rounding to three places, and two hundred days is a no-op because a
  fresh game has no memories. Proving an instrument can see *something* wants
  the crudest possible change — a single credit.
- **A field read only by its gate is a fact nobody priced.** `Run.ly` was on
  every freight run and consulted solely by `reachable`, so the desk knew the
  distance to everything it recommended and discounted none of it. When a
  value is carried but only ever compared against a limit, ask what else
  should have been reading it.
- **When a fix disturbs five things, four of them are usually other bugs.**
  The clock took five attempts; each red check it produced was a separate
  defect it had merely been hiding — free repair, an artefact zero, a probe
  that would not sell, and a desk that never priced time. Fixing the thing
  that reveals defects last, not first, is what made it land unchanged.
- **A probe that fails is not the same as the thing it probes failing.**
  `test_stranded` reported a captain stalled with 51 credits; he was at a
  market with ten thousand credits of cargo aboard and the bot only ever sold
  survey data. Before recalibrating a check that goes red, ask whether the
  *measurement* took the move that was available.
- **Advice ages between the quote and the act.** The freight desk beats
  trading blind only while the market barely moves during the journey. Once it
  moves honestly, a named run's margin has closed by arrival — 47,910 on your
  own notes against 44,627 with the desk. Anything that recommends a distant
  action has to price the delay before the action.
- **Fix the free lunch before tuning the meal.** #116 reverted once because an
  honest clock let repair erase the cost of a hard burn. The instinct was to
  re-tune burn heat; the actual cause was that repair was *free*, and once
  feedstock bound, the balance came right with no tuning at all — hard burning
  went from healing to 0.0000 over a month to costing 0.2413, seventeen times
  economy. Look for the missing constraint before reaching for a constant.
- **`min(what you have, what it costs)` is how a cost stops being one.**
  `repair_tick` computed the biomass a rebuild should eat, took the smaller of
  that and the hold, and healed the full amount either way — so a hull mended
  identically on 500 tonnes, on 20, and on none. The arithmetic was right and
  nothing downstream depended on it. Whenever a spend is written as a `min`
  against stock, ask what happens when the stock is zero.
- **A cost nobody can feel is not a cost.** Even made binding, the old rate put
  a whole hull back for 1.3 t of a 340 t hold. Sizing it against what the ship
  carries (20.5 t) rather than against nothing is what turned it into a
  decision.
- **When two things can never coincide, the link between them is a distance.**
  #118 wanted raider presence to feed the local black market, and raiders never
  work a system with a port while a market *is* a port — 28 raided systems
  across six sectors, none of them docked. The signal that works is how far a
  wharf is from where hulls are being taken (5.3 to 44.6, median 16.9), because
  stolen cargo travels. Check whether the two populations overlap before
  designing a local reading.
- **Measure through the door the game uses, not the one underneath it.**
  "Founding is free" survived a whole task description because it was measured
  by calling `exchequer.found()` directly. The game never does: `_invest` pays
  `p.credits -= cost`, and at a 40,000 cost against a 12,000 reserve a power
  opening with 30,000 cannot found at all. The raw operation and the act are
  different questions.
- **A design decision nothing checks is a design decision waiting to be
  undone.** `exchequer.payback`'s docstring explains at length why the sort is
  by payback and not by price — the upkeep curve is quadratic and the yield
  linear, so the cheap works are the ones that never pay — and nothing in the
  suite asked whether either half was still true. A paragraph is not a guard.
- **A threshold of `> 0.0` is a bug waiting for a continuous input.**
  `control` and `interdiction` both asked `ward_at(...) > 0.0`, which was
  correct while a ward could only be a built work worth 0.28 — and became
  wrong the instant machines contributed, because a teleoperated guard nine AU
  from its supervisor is worth 1e-7 and that is greater than zero. When a
  quantity stops being chunky, every test against zero has to be re-read.
- **Check the scale a law works at before building on it.** #112 was scoped as
  light-lag deciding gunfights; halving a teleoperated hand takes 599,585 km
  and the tactical arena is 1,400 units across, so at combat range an E1 hand
  keeps 99.77% of itself. The law was right and the arena was wrong — the same
  mechanism moved to colony postings gives a 1,800-credit guard that stops
  working the moment you leave orbit and a 9,000-credit one that does not.
- **A gate over thin traffic produces nothing.** Replacing the raider gate
  with a lawlessness threshold dropped piracy from 26 systems to 9 — because
  the least policed places are the portless ones and they carry about one hull
  each, so a yes/no test had almost nothing to act on. A *slope* inside the
  gate put it back to 28. When a rule fires on a population, look at how big
  that population is before deciding the rule is right.
- **Correlation that comes from a shared input is not a relationship.**
  Raiders already avoided squadrons — 17% at nothing on station against 0–2%
  elsewhere — and it meant nothing: `traffic.hostile_ok` and `fleets` both read
  `port`. Two numbers agreeing because they read the same field is the shape a
  one-door violation makes when you look at its output instead of its source.
- **Two constants the data can never separate are one constant.**
  `fleets.CAPITAL_WEIGHT` tripled a capital's share of a fleet, and every
  capital in the game is level 3 while no ordinary port ever is — so it and
  `LEVEL_WEIGHT` were never distinguishable, and flattening it changed no
  verdict anywhere. Deleted, not pinned. A knob a check cannot bite is a knob
  the model does not have.
- **Check the claim the numbers support, not the one you wanted.** At fleets of
  four to eight spread over three to six holdings, largest-remainder rounding
  is bigger than the level weighting: only one power in six sectors shows a gap
  of two. The true and pinnable claim was the *ordering* — 22 of 24 pairs put
  more at the developed holding and none put fewer.
- **Step the clock in a check, never jump it.** `advance_days` runs each
  subsystem's tick once with `n` as an argument, so a per-day decision fires
  once for a 900-day jump. Same seed, same span: one jump leaves every power
  insolvent (−79 to −252) and ninety steps of ten leaves them all thriving
  (+198 to +515). Anything measured across a long jump is measured on a game
  that does not exist.
- **A cache keyed by id will draw the wrong thing.** `relics3d.mesh_for` looked
  an object up by its id and returned the cached mesh, so a relic whose fields
  had been changed still drew the canonical one — and a check comparing a relic
  with and without its bonus compared one picture with itself and passed on a
  mark that was never drawn. Handed an object, draw that object; the cache is a
  fast path for ids only.
- **One shape's gaps are not evidence about the others.** The mark check probed
  a single relic and passed with the mark buried at the centre, because that
  maker's prism stack leaks light between its tiers. A claim about every member
  of a family has to be measured on every member.
- **Silhouettes in one frame trade against each other.** Widening the
  tessellate relic to separate it from abyssal (52%→43%) pushed it into weft
  (62%→70%), so the worst pair got worse. Tune against the worst pair, never
  against the pair in front of you.
- **A guard's fallback is where its blind spot lives.** `test_reachable`
  resolved 1,319 of 1,329 calls precisely and fell back to bare-name matching
  for the rest — and the fallback credited every module with a function of
  that name, which is how `control.provoked` sat unread for weeks behind a
  local variable in `sim/threat.py`. The precise part of a check is not the
  part to audit.
- **A rule that reports nothing new can still be wrong.** Excluding names
  bound anywhere in the tree gave 0 new orphans, same as the correct per-file
  rule — and would have silently stopped counting callbacks. Agreeing with the
  right answer on today's data is not evidence; what separated them was asking
  what each would do to a genuine bare-name reference.
- **A new authority should be one branch, not a second ladder.** Giving worlds
  the right to object needed `control.welcome` to learn a single rule — *a
  world minds the descent, not the orbit* — and every rung, the patience, the
  ward, the grievance and the aftermath came free. The temptation was a
  parallel `interdiction.step`, which would have been a second copy of five
  tuned constants.
- **Measure a threshold against the distribution it will meet.** "Somebody
  will defend a seam worth 0.35" made 93% of the sector armed, because every
  home system has a claimant and the median best seam is 0.72. The fix was not
  a better number but a *gradient* — what the seam is worth decides whether
  they shoot or only talk — checked against the generator's own quartiles.
- **A thing that hides must hide from the readout too.** `interdiction.line`
  warns about settled and worked worlds and says nothing about a quiet site.
  A screen that named it would give away what the sim is keeping, which is the
  same fault as a forecast that quotes a figure the act cannot produce.
- **When the obvious fix would be a lie, measure first.** The body-contact
  branch had no speed test, so every arrival on a world was a crash. The
  obvious repair is a rate threshold — and the drive delivers 0.071 m/s²
  against a rocky world's 10.371, so no threshold produces a landing. The
  right change was to name three endings and let the arithmetic say which is
  reachable where, not to invent a number that makes the nice one possible.
- **Two fields called `kind` in the same call chain.** `Target.kind` is what a
  thing is to an approach (`"body"`); `Body.kind` is what sort of world it is
  (`"rocky"`). `targets.target_from_body` carries the second through as
  `look`. Reading the wrong one reported that every world in the sector had no
  surface, and it looked like a data fault rather than a naming one.
- **A memory nobody weighs is a memory nobody feels.** `forcing.grievance`
  recorded a power's reaction to being broken into with kinds `approach` and
  `forced`, and moved that power's opinion by exactly 0.00 — neither kind is in
  `memory.WEIGHT`, which is the table that turns a note into a feeling. Same
  shape as "declared and unconsumed", one level up: the record was written, and
  the thing that reads records did not recognise it.
- **State the price, not the refusal.** Two claims about forcing a capital port
  were wrong, and flying each one said so: it *can* be cut into (half an hour,
  243 hull), and a starting hull *does* live through it (93 of 336, on its last
  two layers, inside a port it has just broken into). Nothing in a defence
  system should refuse an act outright when arithmetic will do it — and the
  arithmetic must come from one number, `control.means`, which buys the guns
  and the time they have to fire together.
- **Carry the state, leave the record.** The rule `preview._copy` took nine
  fields to make sayable. `boom` and `tug` are how far a structure's equipment
  has come out and decide what the next tick does, so a forecast's twin carries
  them. `sheered` and `towed` are how far the station moved away or walked the
  hull in — a trial run may not credit or bill a station for something it has
  not done, the same reasoning that keeps `struck_damage` out.
- **Measure the saving on the right segment.** Tugs that caught a hull at the
  hold point saved 0.04 t of a 0.98 t approach, and being more generous about
  the catch took it to 0.08 — because nearly all the mass goes into *reaching*
  the corridor rather than into the last five hundred metres. No amount of
  tuning the catch could fix a figure measured on the wrong leg. Boats that
  come out to the opening range make it 1.41 t against nothing, at the price of
  2.7 hours, which is a decision.
- **A promise in the sales text is a claim the game has to meet.** A treaty was
  sold as "mutual berthing, shared charts, and a clause about the Bloom that
  nobody expects to be honoured" for 30,000 credits. The third is a joke; the
  other two were as well. Signing appended a faction id to a list read by
  `treaty_bonus` (+3% on the trade stat, on no screen) and by the matrix's
  "treaty" pill. Measured at Vesper Bight: wharfage 1.714% before and 1.552%
  after — and *all* of that fall was the standing the treaty granted, which
  tribute at a third of the price buys as well. Charts known: 0 before, 0
  after. `sim/accord.py` is the two clauses, and the lesson generalises past
  this one instrument: **read what a thing tells the player it does, then go and
  measure each promise separately.** A benefit that is real but invisible
  (`treaty_bonus`) and a benefit that is named but absent (berthing, charts)
  fail the same way at the desk.
- **Isolate the lever you claim to be measuring.** The first pass at checking
  the berthing clause let `perform` grant its standing, and standing is *also*
  an input to `wharfage.rate` — so the check would have passed on a treaty that
  did nothing but flatter you. `tests/test_accord.py::_sign` restores `game.rep`
  after signing for exactly this reason, and the two-doors check restores it on
  the envoy path too, where `accept_rep` lands instead.
- **Count both doors into the same act.** `treaty` can be proposed at the
  diplomacy desk or accepted from an envoy, and `data/diplomacy.py` already
  records what happened when they disagreed about `TREATY_WEIGHT` — waiting to
  be asked was the way to sign for free. Adding the charts clause to the
  proposing door alone would have been that bug in reverse; `accord.hand_over`
  is the one delivery both call.
- **A posting has to name somewhere the hull can get to.** `_pick_target` was
  documented as choosing a system "reachable in principle" and tested only
  `bloom < 0.4`; reachability is transitive and nothing checked it, so **65%
  of targeted postings named a system outside the reachable component** (15 of
  42 systems fly at the opening drive). Ask `reach.component`, which is the
  same answer the chart gives. `reach.route_to` costs the flight, and the card
  states it.
- **A coverage check pinned to one seed is a check you are getting away with.**
  `test_chronicle`'s "does everything it claims" ran on a fixed seed by
  design, but only **1 seed in 24** ever planted a colony — so it was pinned
  to the one that worked and any change anywhere would break it. The cause was
  a driver bug, not luck: `chronicle._refit_here` still tested "the system has
  a port" after `shipyard.can_refit_here` tightened to "alongside a yard", so
  `apply_refit` returned "you are not alongside a yard" and the driver dropped
  it. Putting in at a yard first took planting to 6 seeds in 48.
- **A vocabulary whitelist is not coverage.** Two suites listed
  `megastructure` in a `KNOWN_EFFECTS` set, which asserts only that nobody
  declares an *unknown* key — never that a declared one is consumed. It read
  like coverage for a flag no line of the game consulted: the ARCA Habitat
  cost 400,000 credits, 2,600 tonnes of ore and 900 days, and its one
  distinguishing property did nothing. `test_grants.py` asks the general
  question instead — *is every declared effect read by something* — and found
  a second dead key (`drydock`) on its first run.
- **A quoted burn's risk is the profile plus three surcharges** — distance,
  the star at either end of the leg, and the heat already in the hull — and
  `path_note` must account for all of them. Two were silent, and the third was
  found only because a check asked the *general* question ("does anything cost
  more than its profile without the screen saying why") rather than testing
  the two known cases. That check verifies each component separately: an
  earlier version asked only whether *some* note existed, and a surviving note
  masked a deleted one.
- **Never `git checkout <path>` to undo a scratch mutation.** Mutation testing
  wants the file back exactly as it was, and `git checkout` restores it from
  the *index* — which silently throws away the uncommitted work the cycle is
  about. It cost this file its whole change once. Read the bytes into memory
  first and write them back in a `finally:`; `tests/` mutation harnesses do.
- **Driving a fight with one repeated order measures nothing.** Combat is
  positional: a hull whose mounts are all on the beam never fires while it
  steers straight at the enemy, so a test that only ever says "salvo" reports
  zero damage and looks like a balance problem. Use `tests/captain_ai.py`,
  which picks the helm order that suits the arcs the ship actually carries.
- **The ground's one piece of arithmetic is `sim/wayhome.py`.** A step spends a
  day on ground already crossed and up to three on fresh, times the weather;
  reach the pad and the haul comes up capped at what four people can lift; run
  out first and 40% of it comes home. The screen showed "Supply · 7 days" and
  **never said how far away the lander was**, so 60% of a hold rode on a
  subtraction nobody was shown. `expedition.step_cost` is the one door for what a
  step costs and `wayhome` adds it up over the cheapest *known* route, so the
  quote and the walk cannot drift.
  Two things it must keep doing: count the days a party is **pinned** (a
  katabatic gale stops all movement, and the first version quoted "4 days home, 3
  to spare" to a party that could not take a step — a trap, found by the check
  that walks the quoted route and was refused at the first one); and refuse to
  plan over tiles nobody has seen, which needs a *tempting* unseen shortcut to
  test, since avoiding dear unseen ground costs nothing either way.
- **The long chronicle never brought a party home.** Measured over ten years: 50
  landings stranded, 32 aborted, **0 returned** — so `lift_off`, `can_lift` and
  the whole banked-haul path were never driven by a played game. It walks back on
  a costed two days' spare now: 31 returned, 14 stranded. And knowing the price
  is worth something — at the same margin, a leader reading the costed walk
  returned 15 parties of 24 and stranded 5, where one counting tiles returned 9
  and stranded 11.
- **A levy reaches the power that claimed the ground, and the captain hears about
  it.** `territory.collect_tithe` skimmed thirty per cent off a holding's output
  and `colony.tick` **threw its return away**: measured on a RADIX Mine turning out
  2.6 t of ore a day, thirty days produced 78 t, the captain received 54.6, and the
  Charter's purse moved by **nothing**. No log line, nobody the richer. It credits
  `Purse.levies` now and the clock writes "Charter took the levy off RADIX Mine —
  35.1 t ore, 1.5 t phosphate, worth about 1,089". Both halves are rules the game
  applies elsewhere: `wharfage.collect` moves both sides in one function, and #100
  exists so a deduction is never silent.
  The demand screen has always quoted "a levy would cost X a year" off a bare 0.55
  inside `yearly_worth` — with nothing receiving the levy there was no act for that
  forecast to be wrong against. `territory.value_of` is the one door now and the
  quote is exact: **8,829 a year against a year that took 8,829**.
- **A commission's reward has to exist, and there are two tech namespaces.**
  `chains.Chain.reward_tech` promised the Reliquary's captain `xenolinguistics`,
  which is in **neither** the research tree nor `data/xenotech.py`, and
  `chains._finish` appended the string to `research.unlocked` regardless — a
  reward granting no bonus and opening no node, on the one commission in four
  that hands over a whole node of a fifty-eight-node tree, advertised on no
  screen. Task #38's shape exactly. It grants `firstcontact` (First Contact
  Protocol, tier 4, 1,100 points — which is what the Reliquary is *about*),
  `chains.reward_tech_of` is the door the desk reads, and the desk says "1,100
  points of research you do not have to do".
  **The guard has to know about both namespaces.** A first sweep checked the tree
  alone and reported thirty-seven phantoms — twelve xeno parts naming ids that
  live in `data/xenotech.py` and are perfectly real, gated behind studied alien
  work rather than the bench. A check that cried wolf about those would have been
  deleted inside a month. It also refuses a *xenotech* id as a commission reward,
  because `_finish` grants by appending to `research.unlocked` and only a tree
  node can go there — caught by mutation, since `vent_symbiosis` exists.
- **The fog covers the body count, and a chart's price no longer gives it away.**
  `intel.LEVELS[0]` calls a registry entry "a body count the registry will not
  stand behind" and `LEVELS[1]`, which is what a chart buys, promises "the bodies
  are real" — and the map panel printed `len(sys.bodies)` at every rank, sized the
  marker by it, **and priced the chart at `900 + 260 a body`**. Measured across a
  sector: forty-one unknown systems, thirteen distinct prices, the count inverting
  exactly (1,160 → one body, 1,420 → two, 1,680 → three). The one fact a chart
  exists to sell was written on its tag. `intel.body_count` is the door; the price
  is `CHART_BASE + CHART_PER_LY × distance` — the trip somebody made, which is
  what a broker can honestly charge for — and its correlation with the body count
  is **0.02 against the old formula's 1.00**. `map_view.marker_radius` is a
  function rather than an expression because a mutation putting the old radius
  back left every check green.
- **`abilities.preview` is the door, and `seal` is bounded.** Six abilities are
  granted by seven fitted parts, and a played decade of seventy engagements fired
  **none of them**, so nothing had driven the module end to end. Reading it for
  that reason found `seal` doing `st.armour += 4` on a four-turn cooldown with no
  other rule: **2 armour to 34 over eight firings**, 43 over a long engagement,
  unbounded — on a part the opening NAVIS carries. Its own sentence says it "gives
  up the breached compartment", which presupposes a breach and is finite, so it
  now needs a holed layer, spends it, and never touches the pressure vessel: five
  compartments of six for +20 and then nothing. `use_ability` asks `preview` and
  **only spends the cooldown if it fires** — it used to set the cooldown before
  deciding anything, so an ability that could do nothing still went out of action
  for four turns and returned quietly.
- **A consort is a `Side`.** `sim/consorts.py` subclasses it, so `_fire`,
  `_apply_to_layers` and the arc checks work on one without changes. What that
  buys is also the constraint: anything that assumes a battle has exactly two
  sides — `_who()` did — has to learn otherwise.
- **Ordering a hull to sail in company is `consorts.sail`, not a screen.** It was
  a screen: `yard_view._set_escort` wrote `ship.escort` and `ship.docked_at`
  itself, so the rule about which hulls may be ordered out lived in whether the
  button had been drawn, and the first headless caller ordered out a hull that
  was not in the fleet. `can_sail` is the rule — yours, not the flag, not a wreck,
  somebody aboard, berthed *here*, not already out — and `data/orders.py`'s escort
  card reads the same function, having previously nagged about hulls six systems
  away.
- **A hull in company eats out of your hold.** `upkeep.complement(game,
  company=True)` counts its crew; `demand` asks with them and `draw`/`breathers`
  ask without, because stores come out of the shared hold while air and power are
  per hull. Before this a fleet was free to keep — measured, a thirty-crew escort
  moved the day's demand, the power draw and the wage bill by exactly nothing.
  `consorts.keep` is what the yard quotes, unrounded, so the figure on the panel
  is the figure `upkeep.tick` takes.
- **Counting which mechanics a played decade ever reaches is worth doing
  directly.** Wrapping the doors and playing ten years found that **seventy
  engagements deployed a consort in none of them** — `escorts_of` was empty every
  time because a chronicle never lays down a second hull, so orders, screening and
  interception had never been driven end to end by a game. `test_company` now
  drives them: four engagements, four consorts deployed, 73 turns with one
  interposed between the flag and the enemy.
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
