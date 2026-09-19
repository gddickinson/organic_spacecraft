# The parts that will bite you (4 of 5)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

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
- **`responses.growth_multiplier()` is read in `threat.tick`, and that is the
  only thing making provocation matter.** It was computed and read by nothing
  at all on the first pass — the same shape as the levy counter that
  incremented and changed nothing. If a new Bloom response adds an effect, find
  the place that consumes it before believing it works.
- **Studying a mass and burning it are exclusive on the same mass.** Study
  yields xenolith and readings scaled by how much growth is present and feeds
  it a little; burning removes the thing you would have studied. That conflict
  is the setting's central tension and `STUDY_FLOOR` is what keeps a burnt-out
  system from paying twice.
- **A public function nobody calls is a feature that does not exist.**
  `test_reachable.py` walks the tree and fails on any public module-level
  function called from nowhere at all. Be clear about its limit: it will not
  catch one that is called only from a readout or only by the suite. The
  Bloom's growth multiplier was consumed by `summary()` from the day it was
  written while contributing nothing to the simulation, and this check would
  have passed on it. Reachability is a floor, not a guarantee.
- **`return None` is not a result.** Counting it made the analysis flag every
  early-exit function; the self-check caught that on its first run, which is
  the argument for the self-check existing.
- **A feature is not finished until a lever in `tests/levers.py` proves it
  moves the world.** Reachability only shows a function is called;
  `test_efficacy.py` switches each claimed effect off and demands the same
  seeded scenario come out different. Disconnect the Bloom growth multiplier
  and reachability still reports "every one reachable" while efficacy fails.
- **Levers patch a module attribute, not an imported name.** The codebase calls
  across modules as `module.function(...)`, so the lookup happens at call time
  and every caller sees the substitution. A lever aimed at something imported
  by name would silently do nothing, so the suite checks each substitution
  actually changes its measurement before trusting the comparison.
- **Watch for a probe that saturates or starts already satisfied.** The first
  Bloom lever ran long enough for every system to pin at its 1.0 ceiling, so a
  Bloom growing half again as fast reached exactly the same total; the first
  research lever stocked the bench full in *both* runs. Both read as inert
  features when the features were fine.
- **A crossing charges as it goes, not up front.** `transit.begin()` takes
  nothing; each watch spends its share. That is what makes cutting the burn a
  real decision — you keep what you have not yet spent and lose what you have.
- **`intel.sees_bloom` is the one door for what the chart may show about a
  star's infestation.** The sector chart has a careful knowledge system —
  `intel.level` ranks 0..3 and the marker and port ring both respect it — and
  the Bloom was exempt from all of it: a red halo sized by `system.bloom` on
  every star however unknown, and a side panel printing "Bloom mass: 77%" one
  line above "Knowledge: name only". It also quietly undid the picket, whose
  `watch` effect exists to report what happens where you are not. You see a
  system's Bloom if you have been there, can see it from where you stand,
  watch it, or hold a colony in it. **A registry entry is not eyes.**
- **The aggregate stays public.** Holdings still reports how many systems
  carry growth and what share of the sector by mass, so scouting is a cost
  rather than a wall: how bad is published, where is earned.
- **`Docking.shown` is the instrument; `d.error` is the truth, and screens
  never touch it.** The readout was rolled fresh inside `reading()` on every
  call, and the panel called it from `game.rng("readout")` — which advances
  the save's seed — so an untouched axis read −44, −49, −42, −47, −49 in five
  consecutive paints. The panel then took its *colour* from `d.error` while
  printing the blur, and every button's forecast quoted `d.error` outright.
  The reading is taken once per pass now and the panel, the colours and
  `forecast` all use it. **If you add a docking readout, read `shown`.**
- **`NOISE_CEILING` must stay above `TOLERANCE` or the sensor rating is
  inert.** It was 5 against a tolerance of 6, so nulling the reading put you
  inside tolerance whatever your instruments: flying on the instrument alone,
  every noise from 0 to 5 docked 100% of the time in 3.2–3.5 passes. At 9 a
  bare hull (sensor 2) reads ±7 and pays about a pass; a well-found one reads
  ±3 and does not.
- **`CREW_CHOICES` holds station ids, and `make_officer` refuses one it does
  not know.** Two of the six used to be *stat* names — "engineering" and
  "medicine" against the roles "engineer" and "medic" — and `make_officer`
  answered an unrecognised id by picking a role at random. Nothing exercised
  it, because no screen ever set `Choices.crew`; the moment the opening grew
  a bridge picker, choosing the engineer would have seated somebody else.
  `role_id=None` still means "anybody"; a name is now either known or an
  error.
- **`CREW_SLOTS` is the opening complement, not a ceiling.** The berths board
  is explicit that in play "you may keep as many as you can pay", and six
  roles exist to be filled — so `can_hire` deliberately does not consult it.
  `beginning.apply` trims to it, which is what makes a dry stack sail with
  two, as its card has always said.
- **Every gate must agree with the act it guards, and the act should call the
  gate.** The sim has seventeen `can_*`/`is_*` functions; a screen asks the
  gate whether to offer a button and the act asks its own conditions when the
  button is pressed. Two real bugs came from that gap before it was asked on
  purpose (`is_stranded` against `extract`, `quote` against `check`), and
  `test_gates` found a third: `crew.hire` refused a station that was already
  crewed and the berths board did not know — **49% of candidates over sixty
  ports could not be signed**, every one under a live button.
- **An agreement check cannot guard a shared gate, and must not pretend to.**
  Once `hire` calls `can_hire` and `start_build` calls `can_build_here`,
  changing the gate moves both answers together and they agree all the way
  down — which is the architecture you want. The *rule* then needs a separate
  check measured by outcome. Making `can_build_here` answer yes everywhere
  passed every check in the project until one was written for it.
- **`contracts.CARGO_KINDS` is the one list of kinds completed by carrying
  something.** It was written out three times — in `quote`, in `shape`, and
  again in `test_cargo` — and all three said `("deliver", "prospect")` while
  `check` completed a `relic` in the *same branch* as a prospect. So relic was
  the one cargo contract neither priced on the board nor floored against what
  its goods cost: measured over 271 of them, median net **−402** and **62%
  losing money**, against 0% for the two that were covered. A check that
  shares the code's whitelist can only confirm what the code already assumed —
  `test_cargo` derives the set by playing now, handing each kind its
  completion state with an empty hold and then a full one.
- **A ground option's prize depends on who you send, and the card must say
  so.** `attempt` multiplies a success by `1 + margin * MARGIN_BONUS`, but
  `odds_for` quoted the bare `REWARD_SCALE` band — so the card read the same
  at every officer level while the payout did not. Measured on "Cut a sample",
  800 attempts a level: quoted 8–26 ore throughout, paid up to 32.2 green and
  47.8 at level five, with 28 of 42 option-and-level pairs over their ceiling.
  Skill moved the odds on screen and the prize in secret. The quote is
  conditioned on the officer now — the smallest and largest margin they can
  roll on a success, carried through — so a seam reads 8–32 green and 9–45 at
  level four. **The tuning constants live in `data/expedition.py`**; a bare
  0.12 inside `attempt` is what made the forecast unable to quote it.
- **A dead aggregate is where a dead effect hides.** `test_grants` asks the
  general question — is every effect a colony grants read by something? — and
  two slipped past it anyway. `colony.effects()` copied `watch` into a
  `watch_systems` set and `fabricate` into a `has_fabricator` flag that **no
  other line in the game ever opened**, and the check counted those copies as
  consumers. A mention inside a function whose own output nobody reads is not
  a consumer. The check excludes the aggregator's body now, and follows one
  hop through it (`vault` reaches `state.py` via `has_vault`, and must still
  pass). A second check holds the aggregate itself to publishing only keys
  something opens — it was carrying six dead ones, including a `research`
  that was always 0.0 while two callers added it to the bench rate.
- **`colony.watching()` and `colony.fabricating()` are direct queries**, not
  aggregate lookups. A picket gates whether you hear about unlicensed growth
  in a system you are not in — the sector used to report every infestation
  anywhere, which is exactly why the effect bought nothing. A fabricator takes
  `FABRICATED_OFF` off the *credits* of fabricated fittings built or refitted
  in its system; the metal is charged either way, and grown fittings are
  untouched. `cost_of` and `refit_cost` both take the flag, and `yard_view`
  passes it so the screen quotes what the yard charges.
- **A port reverts to `Stock.base`, not to 1.0.** `make_market` builds real
  economic geography — an ore-rich system's port gets up to 1.75x supply, a
  faction's exports 1.55x, what it is short of 0.62x — and `tick_market` used
  to drag every commodity at every port toward
  `1 + volatility * trend * 12`, a number with nothing to do with the port.
  The geography was gone inside a year: the spread in ore supply across ports
  fell 0.431 → 0.117, and from year one **the best arbitrage in the entire
  sector was zero or negative on every commodity, for ever**. The module
  docstring had always said "its own equilibrium"; the arithmetic said 1.0.
  `base` defaults to 0 and is adopted from current supply on first tick, so
  saves written before it keep their character instead of being flattened.
- **A 4-sample threshold is not a check.** `test_politics`' Concord broker ran
  four seeds and demanded three. Measured over seventy-two games the true rate
  is 56–68%, so that assertion had about an even chance of failing on any
  given day and had been passing on luck. It went red for an economy change
  that a fixed-length control proved had no political effect at all — same 322
  ventures, standing and relations within noise — and the apparent
  53%-against-75% gap vanished (21/36 against 22/36) on a fresh range of
  seeds. Twenty games and a floor at 35% now. **When a check on a stochastic
  outcome fails, measure the rate on a fresh seed range before believing it.**
- **`is_stranded` must ask whoever grants each way out, not guess.** It is
  the gate on `distress_call`, the game's only answer to being out of fuel and
  money at once, and it carried two guesses. The ice test read
  `resources["volatiles"] > 0.05` — how *rich* a body is — while whether a rig
  will go on it is `mining.worked_out`, which reads how much has been *taken*.
  Different quantities, so a rich body worked to exhaustion counted as fuel
  for ever: a captain at Amber Anchorage, a one-body system, with 0 credits
  and 2.3 tonnes, was refused a tow with "you can still move". The port test
  fell back to `or 40` when `buy_price` returned None, which is exactly what
  it returns when the shelf is empty. **If you add a fourth way out, ask its
  owner.**
- **A fresh sector is not the state the bug lives in.** No port in 417 is out
  of reaction mass at generation, which is why the empty-shelf branch went
  unseen for so long. Played sectors get there. Construct the state.
- **`captain_bot` is the deadlock check and it has to reach the end.** Its own
  docstring says a stall means a hole a player would fall into, and nothing
  was asserting it ran its full five years — two of six stopped short, one on
  day 1406 of 1825, while the solvency check beside it passed on the *mean*
  treasury of all six.
- **An NPC's magazine is sized to its own mounts, not to salvage.**
  `make_enemy` gave every hull a flat 4–20 t of ore, alloy and biomass —
  stores meant for the wreck — and those were quietly doubling as ammunition
  nobody had sized against a fight. Measured: a mean of 12 rounds against a
  31-turn fight, dry on turn 11, **unarmed for 63% of every engagement**, and
  the player taking no damage at all in 13 of 20 fights. `ROUNDS_MIN/MAX`
  stock each ammo-hungry mount separately now.
- **A warship needs a gun that can hurt you, not just a gun.**
  `_weapon_pool` raised the tier until *some* weapon existed, and for a
  fabricated hull the first to appear is the point-defence cannon — so **40%
  of NPC hulls arrived armed with nothing but flak**, Concordat warships at
  difficulty two included. `MAIN_GUN_DAMAGE` (12, against a median mount of
  30) is the bar. Specialists are still fitted alongside a battery, which is
  what they are for.
- **The difficulty curve was a cliff, and `_rack` is what gave it a bottom.**
  Scales 0.5, 1 and 2 all came out at 8–16 points of throw because every one
  of them carried flak, and scale 3 jumped to 85. Requiring a main gun fixed
  the flat bottom and created a new fault in its place: a fabricated hull's
  first main gun is tier three, and tier three holds the breach torpedo, so a
  light patrol drew from a battleship's rack. `_rack` widens the pool with
  difficulty. Now 27 · 28 · 45 · 88.
- **The seats run engineering first, then the helm, then the guns.** That
  order is load-bearing, not incidental. Engineering is what sets
  `side.route`, and its two consumers sit either side of it: the guns read it
  when they fire (after both seats) and the helm reads it while steering. With
  the helm running first, `route_guns` landed on the turn it was given and
  `route_engines` landed a turn late — ordering "power to the drive" left the
  ship at a dead stop, and it leapt to 74.9 on the following turn, the turn
  the captain had ordered *hold station*. If you add a seat, put whatever
  allocates a resource before whatever spends it.
- **The best seat depends on the hull, and that is working as intended.**
  Measured over 40 engagements apiece: a beam-armed navis leaves the enemy at
  46% hull with the captain at the helm and 92% with the captain at the guns;
  a heavy bastion reverses it, 66% at the helm against 30% at the guns.
  Taking the gunnery seat costs you the helm, which repeats its last order at
  seven-tenths turn rate — for a ship that has to keep its beam on, that costs
  more than the accuracy is worth. Do not "fix" this.
- **`offer_gain` is the only thing that decides what an overture buys.**
  `preview` and `perform` each carried their own copy of
  `action.gain * (1 + diplomacy)`, which is the arrangement that produced a
  free treaty, an ungranted favour and a phantom haggle payment in this same
  file. One function now, and `test_courtship` greps the source to keep it
  that way — `.gain` may appear exactly once in `sim/diplomacy.py`.
- **Goodwill is cheapest from people who barely know you.** `courtship()`
  tapers an overture's worth above 25 standing, squared, to a floor of 0.30.
  Without it nothing in diplomacy had a diminishing return at all: the same
  forty tonnes moved a power at 95 exactly as far as one at 0, and the
  Concord — the sector's whole political condition — arrived on day 855 for a
  captain who never left port. It is 3.2 years now, and the powers finish
  sitting *at* Kin (70–73) rather than pinned at 100.
  **The floor must not go below about 0.30.** Standing erodes on its own — the
  churn takes a power at 90 down to 83 inside two years — so an ally has to
  stay worth courting. At 0.08 and 0.15 the determined broker in
  `test_politics` reached the Concord in only two games of four: an ending
  made unreachable is a worse fault than one made too cheap.
- **A penalty is a share of the gain, never a flat amount.**
  `allegiance.price` had `max(1.0, ...)` under it — invisible while every act
  was worth five or more, and a trap the moment `courtship` made a gift worth
  0.88: the floored penalty of 1.0 with each of two rivals turned relief at
  high standing into a button that cost forty tonnes to leave you 1.12 worse
  off. The floor also flattened the severity ramp this module exists to
  create. Keep costs strictly proportional to `weight`.
- **A movement of "−0" is a rounding artefact, not a number.** Courtship made
  the small end of the standing range real, and a penalty of a tenth of a
  point formatted as "−0 standing" — which reads as nothing and looks like a
  bug. `diplomacy_view.standing_figure` decides it; note that
  `abs(delta) < 0.5` is *not* the right test, because Python rounds a half to
  even and exactly −0.5 formats as "−0" too. Ask what it rounds to.
- **The hull regrows and the calendar does not.** About 2.3 a day when badly
  hurt, and faster near full. So *hull damage is a cheap cost and days are an
  expensive one*, and an option that charges both can cancel itself out:
  `contact/hold` was first retuned to ten off the hull plus two days, and the
  two days healed the ten exactly. Never price a watch option — or judge one —
  on declared damage alone; `test_watches.py` measures what is still missing
  after the option's own days have passed.
- **Every watch option must be a trade nobody can dismiss.** `data/watches.py`
  states the rule in its own docstring — "there is no option that is simply
  best" — and four options broke it. The check is *domination*: does any
  option cost no more on every axis and pay at least as much? That single
  question found all four, across two watches, and it catches four of the five
  regressions in the mutation sweep. Testing the options that worked would
  have found none of them.
- **A declared risk has to cost something when it fires.** `contact/hold`
  carried the largest risk in the table, 45%, and `risk_damage=0`: it printed
  "They were not nobody." and nothing happened. `risk_days` exists because a
  risk could previously only cost hull, and being stopped and searched costs
  time — without it the option could not be priced at all.
- **The price register holds price quotes and nothing else.** Chart completion
  dates used to be stashed in `game.register` beside them, and
  `market.best_markets` walks every value in it and reads `.sell` — so charting
  anything and then opening a port raised `AttributeError` inside a Qt slot,
  where Qt swallows it and the panel simply fails to draw. Chart dates live in
  `game.charts_made` now, with a migration for old saves. Found by rendering
  the screens for the README, which is a kind of play the suite was not doing.
- **A watch option states what going wrong costs, not just its odds.** The
  panel rendered "Might go wrong: 30%" and stopped, so holding through debris
  (30% of thirty off the hull) and running a bad slug (35% of twenty-four)
  read as the same gamble. `risk_text` and `risk_damage` existed in the data
  and were read by `sim/transit.py` alone — the screen referenced neither.
- **A ground option states its odds, its prize and its risk.** The screen
  listed "(science, difficulty 3)" and nothing else. Resolution is
  `1d6 + officer level >= difficulty + 2`, so that same string is a
  one-in-three with a green officer and five-in-six with a level-three one; the
  reward was unpacked into a discarded variable; and a failure springs a hazard
  40% of the time, unstated. `expedition.odds_for()` gives all four, and the
  ground game is nothing but a sequence of these choices.
- **The seed dialog says what will grow.** It showed each class's cost and
  gestation and never its yield — the one thing that separates them. Measured
  on one rocky body: fourteen classes from 2.6 t of ore a day (RADIX Mine,
  12,000) to 260 credits a day (Free Port, 74,000) to 4.2 research a day
  (Reactivated Array, 96,000), and three that yield nothing and buy effects
  instead. `colony.forecast()` gives yield, upkeep, effects and a rough
  payback, and the card shows them.
- **A colony forecast prices at a flat table, not at a market.** A payback that
  swings with whichever port you are standing in is not something a player can
  compare classes with.
- **A seat says what taking it is worth, not just who is holding it.** The
  orders panel printed each station's officer level and never the consequence.
  Measured from the sim: gunnery is +0.22 to hit with a green officer and +0.10
  with a veteran; an unattended helm repeats its last order at 0.7 + 0.06 a nav
  level of the turn rate; an unattended engineering section sheds a fraction of
  its vent and can do nothing else. `stations.seat_value()` states each, so who
  you have decides where you should be sitting.
- **An overture says what it buys, not only what it costs.** The diplomacy
  screen listed a name, a blurb and a price and never a benefit: tribute at
  12,000 credits for +9 standing read the same as relief at 40 t of biomass
  for +11, which is about six times better per credit. `dip.preview()` is a
  pure function returning what will move — the target, third parties, and the
  relations matrix — and the screen draws it.
- **A treaty's cost with the signatory's enemies is now stated.** It charges
  standing through `allegiance` and said so nowhere: you signed, and two other
  powers thought less of you for a reason the game never mentioned. In a sector
  at war that is six points with each of the other three.
- **Nothing is gated behind a technology that does not exist.** "Build a
  xenology annex" — 100 days, 11,000 credits, +0.5 research a day and +0.04
  diplomacy — was gated on `tech="xenolinguistics"`, which is in neither the
  research tree nor the xenotechnologies. It was buildable by 0 of 19 colony
  classes with everything in the game unlocked. One entry in the whole content
  set was wrong; `test_works.py` now checks all 131 gated entries across works,
  colonies, parts and chassis, plus every tech prerequisite.
- **A test fixture was part of why it hid.** `test_verbs` appended the phantom
  id to `research.unlocked`, so the sweep that clicks every control saw a work
  no real chronicle could reach. A fixture that invents content is a fixture
  that stops the suite noticing content is missing.
- **What the bench says a programme will eat is what it eats.** `needs()` is
  documented as the end-to-end total and the screen prints it as "26 wanted";
  `draw()` then spent `total / 60` a day while a careful programme runs about
  128 days, so the bench ate 2.1x the advertised figure on every track. The
  sixty was a duration nobody had checked. The draw is paced over
  `span_of()` — the programme's real expected length at the current rate — so
  the two agree.
- **A quote is priced for the approach in hand.** Running parallel tracks costs
  "three benches' worth of material" by its own blurb, and the readout quoted
  the careful number. `needs()` takes the `Research` and applies the approach's
  draw, so the shelves are read against what this programme will actually take.
- **The four burn profiles are a decision because a hard burn arrives hot.**
  Measured: a system flown end to end took 55 days coasting and 10 on hard
  burns, and the hard burn cost about three hundred credits of reaction mass
