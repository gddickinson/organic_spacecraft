# Session log, part 26 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

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
