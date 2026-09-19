# Session log, part 21 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

## 2026-07-28 — SEEDFALL: the helm, and the half of the fix I missed

Richer helm and flight simulation, the next standing priority. It turned into
finishing last cycle's job properly and then finding what a *general* question
catches that a specific one does not.

- **Last cycle bounded heat in the guns and left the helm wide open.** A hard
  burn adds heat on arrival; only `cool()` takes it away, at 0.84 a day
  against the ~32 a burn puts in. Bouncing between two bodies drove a hull to
  **5.4x its rated cap**, climbing linearly with nothing to stop it.
- **And it was worse than in combat, because it was quiet.** Ten hard burns
  then an engagement: the captain **routed on turn three at 51% hull while
  holding fire every single turn**. They lost to their own radiators without
  firing a shot. Now: driven off on turn 35 at 88% hull.
- **One rule, one place.** `HEAT_CEILING` and `cook()` moved to `sim/ship.py`
  beside `cool()`, because the hull owns its physics and both the guns and the
  helm put heat into it. `combat` re-exports them. A check asserts they are
  the *same objects*, because two copies of this rule drifted within a cycle.
- **Flying hot still costs.** Fourteen hard burns: 87 days at 68% hull against
  economy's 235 days at 100%, and double the incident rate. Bounded, not free.

**Then the general check earned its keep.** The burn board quotes a risk, and
that risk is the profile plus *three* surcharges. Two were charged silently:
the heat in the hull (a captain saw coast at 0.34 where its profile says 0.06)
and the star at your back (`_heat_risk` takes the nearer end of the leg, so a
hull parked at 0.40 AU paid on every departure, including one nine AU outward,
while the note only ever described arrivals).

I wrote a check asking the general question — *does anything cost more than
its profile without the screen saying why* — and it immediately found a
**third** surcharge I had not looked for: a distance term, up to +0.10, never
mentioned anywhere. All three are stated now, with their amounts.

**And the check was too weak at first, which I caught by mutation.** It asked
only whether *some* note existed. With the star warning deleted, the distance
note kept the quote looking explained and nothing failed. It now checks each
component separately, reconciles the components against the quoted total so a
fourth surcharge cannot appear unnamed, and caps what may go unsaid so the
noise threshold cannot be raised to hide something large.

Five checks in a new `test_helm` suite and four more in `test_thermal`, every
one proven to bite — including a mutation that raises the threshold to hide a
surcharge. 606 checks green.

## 2026-07-28 — SEEDFALL: a warship that can fire its own guns

Positional combat with crew stations, the next standing priority. Measure
first, as usual — but this time the measurement took several passes because
the first three readings were all my own errors.

- **False start one:** drove fights with a repeated order and got 0 wins and
  0 losses in 280 fights. INTERFACE.md already warns about this in writing —
  "driving a fight with one repeated order measures nothing, use
  `tests/captain_ai.py`" — and I had not read my own note.
- **False start two:** the test ship's magazine was empty, so the slug battery
  could never fire. Same class as the 9000 t of fuel in a 340 t hold.
- **False start three:** concluded heat was dead because a two-gun mining ship
  never overheats. It is not dead; that hull is simply not thermally limited.

**The real finding, once the measurements were sound.** Heat had no ceiling.
A Bastion firing the five heavy mounts it has slots for makes 74 heat a turn
against a rated cap of 50 and a vent of 6, so heat ran 68 → 132 → 187 → 243 →
279 and kept climbing. The overheat penalty is a share of how far over you
are, so it compounded — resolve fell 26, then 39, then 53, then 65 — and the
ship routed on turn five **at 93% hull**, beaten by its own radiators while
the enemy did almost nothing. There was no way back either: cooling from 279
at six a turn takes 38 turns, longer than the engagement, so `vent` could
never catch up and only cost you the gunnery seat.

So every thermal decision in the game was fake: salvo's "far more heat", the
aimed shot's "less heat", holding fire to cool, both power routings.

- **`combat.cook()` holds heat at twice the rated cap.** Measured over 40
  fights with the heavy battery: favourable outcomes 7/40 → 24/40, kills
  4 → 12. Recovery is back inside a fight — two turns of venting hard.
- **And salvo against aimed became a real choice**: salvo decisive and swingy
  (12 kills, 16 routs), aimed attritional (24 driven off, 2 kills).
- **The light explorer is untouched** — it peaks at 9% of its cap, so the
  ceiling is never consulted. This is a fix for a broken regime, not a
  rebalance.
- **One clamp, not two.** An end-of-turn clamp was tried and measured to
  change nothing (peak 2.32x either way), so it came out again.

**A costly mistake worth recording.** While measuring which clamp mattered I
used `git checkout seedfall/sim/combat.py` to undo a scratch mutation. That
restores from the index and threw away the entire cycle's uncommitted work on
that file. Rebuilt it, and the mutation harness now keeps the original bytes
in memory and writes them back in a `finally:`. Added to the traps list in
INTERFACE.md.

Eight checks in a new `test_thermal` suite, every one proven to bite.
597 checks green.

## 2026-07-28 — SEEDFALL: a gift is a public act

Diplomacy, the standing priority. Same method as the last three cycles —
measure the system for a dominant strategy before touching it.

- **The measurement.** A captain with money ended a chronicle at 92, 100, 100
  and 100 with all four powers, while the Concordat and the Freeholds sat at
  −67 with each other. The three gift overtures — tribute, intelligence,
  relief — added standing with their target and cost **nothing** anywhere
  else. So the relations matrix was scenery, there was never a side to take,
  and `broker`, the only action that moves that matrix, bought nothing you
  could not get by ignoring it entirely.
- **The fix used machinery that was already there.** `sim/allegiance.py` knows
  how much a rift is worth and was already wired to contracts, treaties and
  territory — including a `note()` for showing the price before you commit.
  Gifts go through it now. Nothing new was invented.
- **Measured after:** courting one side of an implacable feud reaches 100 with
  them and −100 with the other; courting both reaches 69 and 63, neither at
  Kin. Brokering the rift first drops the toll from 7.8 standing to 1.0. That
  is the purpose brokering never had, and the diplomacy screen has been
  telling players to broker for as long as it has existed.
- **The screen shows all of it.** The overture card now reads `Concordat +9
  standing · Freeholds −4 standing · Charter −1 standing` before you press
  anything, because `preview()` and `perform()` share the arithmetic.

**A real bug, found by playing.** With gifts now costing standing elsewhere I
went looking for whether a captain could recover from a wrecked relationship.
They could not: at −100, courting a power with unlimited credits for 120
sessions moved them *not one point*. Below −60 every overture is refused and
the only move left is `denounce`, which makes it worse. A one-way door, true
before this cycle and made far easier to fall through by it. `tribute` reaches
to −100 now — the crude one that works on people who cannot stand you, which
is exactly what its own blurb always said. Climbing back from the floor takes
555 days of steady tribute.

Eight checks in a new `test_courting` suite, each proven to bite. One mutation
did *not* bite and the reason is worth keeping: the "peaceful powers take no
offence" claim is held up by two independent guards, so removing either one
alone leaves the other standing. Defence in depth, not a hole — recorded in
the check so nobody chases it.

589 checks green.

## 2026-07-28 — SEEDFALL: a ship that shows what has happened to her

Following the standing request to keep improving the graphics, especially of
the ships. Two things were wrong: the model was lit badly, and it was silent.

- **A ship at 25% hull rendered pixel-for-pixel identically to one fresh out
  of the yard.** Every reading of the damage was a percentage in a side panel;
  the picture — the one thing always on the screen — said nothing at all.
  Damage now shows as blight spreading over the hull, following the outermost
  layer, which is the one damage lands on first and the one you could see.
- **The blight is patches, not static.** The first version hashed each face on
  its own and produced a checkerboard, which reads as a broken texture rather
  than as a wound. `speckle()` is coherent now: everything inside one `PATCH`
  cube shares a number, so neighbouring faces rot together. Measured, touching
  faces agree 79% of the time against 50% for face-by-face scatter.
- **It scatters without dice.** Drawing happens many times a second, so using
  `game.rng()` would mean two captains who looked at their ship a different
  number of times got different chronicles. A check exists solely for this.
- **Lighting: key, fill, rim and specular** instead of one lambert term. The
  rim is what separates the silhouette from the void; the specular is keyed to
  material, so a grown membrane (gloss 0.10) and a fabricated plate (0.55)
  stop looking like the same plastic in two colours. Faces also fade with
  distance, and the flat black backdrop is a graded well of light, so the hull
  has something to sit against.
- **The per-face outline is gone.** It existed to hide the hairline seams
  antialiasing leaves between polygons, but drawn darker than the face it drew
  a lat/long grid over a hull that is supposed to be grown. Same purpose, same
  colour as the face.
- **The caption names the skin.** "hull 93%" beside a visibly rotten ship read
  as a rendering fault; it now reads "hull 93% · sacrificial epidermis 45%".

Eight checks in a new `test_picture` suite, every one proven to bite by
reintroducing the bug it exists for — including the two that first did not.
The pixel check compares two renders rather than inspecting fields, because a
field on a dataclass proves nothing about what the captain can see.

**My own error worth recording:** the first coherence check asked whether a
marked face had a marked neighbour. With half the hull marked that is true by
chance — per-face static scored 99% on it. The metric had to become neighbour
*agreement* against the chance baseline before it could tell the two apart.

581 checks green.

## 2026-07-28 — SEEDFALL: a seam that can actually be worked out

Same method as last cycle — measure a system for a dominant strategy before
touching it — this time on mining.

- **A body never ended.** It capped at 95% depleted and went on paying 1.1 t a
  session without limit: measured at trip 20 and still paying at trip 199. So
  "this seam is finished, move on" was never an event, and the gentle methods
  bought nothing, because the cap arrived whatever you did.
- **Now it refuses the rig**, and the four methods pull apart properly. From
  one body: `bore` 2.45 t/day for 202 t total; `leach` 1.01 t/day for 407.
  Rate against lifetime — a real decision, and one that depends on whether
  bodies are plentiful or scarce.
- **The panel states both**, because neither figure can be worked out from the
  other.
- **The forecast is calibrated against the thing it forecasts.** My midpoint
  estimate read 15% high, consistently, for every method — including `skim`,
  which has no mishap risk, so it was arithmetic and not collapses. Rather
  than ship a flattering forecast I measured the gap and named it
  `WORKING_LOSS`; `test_seams` re-measures it, and it now lands within 2%.
- **An existing check had encoded the old behaviour** — "a worked-out body
  still pays, but less" — and broke when the body started refusing outright.
  Updated to the stronger claim rather than softened.
- And my first two attempts to measure any of this failed on my own driver: I
  filled a 340-tonne hold with 9000 tonnes of fuel and then read "no room in
  the hold" as a mining bug.
- 573 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: pushing a programme finally costs something

Research, untouched until now. It looked deep — evidence types, four
approaches, setbacks and breakthroughs — so I measured it before touching it,
and found that `push` was simply the correct answer: 76 days to unlock against
`careful`'s 132, with its 28%-a-season setback already priced into that
number, because a setback costs progress and progress is exactly what the
measurement counts. Four ways to run a programme and one of them right.

- **A pushed result is provisional.** The blurb had said so all along — "build
  on results nobody has replicated" — and nothing read it. The technology
  unlocks and delivers 55% of its bonuses until somebody checks the work,
  which costs bench time and no evidence.
- **Measured after**: to two *sound* technologies, `parallel` wins with a full
  bench, `copy` with a thin one, and `push` — still fastest to raw capability
  — is now the slowest of the four to soundness. The screen states the
  unreplicated rate beside the pace, and the debt has its own panel.

**Four measurement errors of my own, all caught by looking twice.**

- I "found" that evidence scarcity did nothing — identical times whether the
  bench was flooded or starved. It was my trickle: the tech wanted `hardware`,
  which I never supplied, and even my "starved" rate of 8 a month exceeded the
  real requirement of 5–7. A genuinely empty bench takes 2.4× as long.
- I asserted confirming costs no credits. Days pass and wages are paid; that
  is the clock's business, not the bench's.
- I looked for a bonus-granting technology among the *starting* ones. None of
  them grants a passive bonus, so `next()` raised `StopIteration` and the
  harness reported an empty failure message.
- And I twice wrote a test file with a `def _();` stub in it, which is a
  syntax error, not a placeholder.
- 568 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: a near miss on the ground finally pays

Breadth, and a lead from the tripwire: `expedition.SPOILED` was a constant
sitting at its own degenerate value — `0.0`, commented "what a spoiled attempt
is worth, as a share", and read by nothing at all.

- **Every attempt on the ground was all-or-nothing.** Missing by one and
  fumbling by five were the same outcome: zero, plus a 40% chance of springing
  a hazard. An officer's level was a cliff rather than a slope, and the ground
  screen — which states the odds, the prize and the hazard — had nothing to
  say about failure at all.
- **A near miss now pays a tapering share.** Measured: 645 credits for missing
  by one against 351 for missing by two, nothing beyond the window, and
  12–36% of a clean attempt across every reward type.
- **The screen says so first**: "17% of the time, about 30% of the prize still
  comes back."
- **A guard for last cycle's lesson** — a suite that does not exist looks
  exactly like a suite that passes. `tests/test_harness_guard.py` asserts
  every name in `ALL_SUITES` dispatches to a real module with a `run`. Written
  as a subprocess first, which recursed until it timed out because it lives
  inside a suite.

**Four of my own checks were too weak, and trying to break them proved it.**

- The taper check compared two noisy means with a bare `>`, which passes about
  half the time with the taper deleted. It requires a 1.25× margin now.
- The fumble check counted empty-handed failures, but `lore` options never
  salvage, so deleting the near-miss window entirely still left plenty of
  empty hands. Then, corrected for that, it *still* passed — because the taper
  goes negative at a wide miss and zeroes small prizes on its own, so the two
  rules overlap. The precise claim is simply that nothing beyond the window
  ever pays, and that is what it asserts.
- The "missing by more" check originally asserted the constants existed and
  returned. That is not a measurement.
- And I read a "325 unit average salvage" as a bug when it was arithmetic
  nonsense of my own: averaging credits (900–3400) with ore (8–26). Compared
  per reward type it was 12–36% throughout.
- 562 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the approach, drawn and flyable

The last of the piloting request. The docking mini-game modelled an error and
a drift per axis, a blurred readout and a hull-set precision, and delivered
all of it as three integers and six buttons — with the drift not delivered at
all.

- **It is drawn now.** Range and attitude as a position against the collar,
  roll as the hull's tilt, the tolerance box at the centre, and a ghost of
  where the next correction lands with the drift counted. A roll error is not
  a position, so it is not drawn as one — that would be a prettier lie than
  the numbers were.
- **Every burn says what it leaves**, and which axes it lets slip while you
  make it. That was the invisible rule: firing on one axis walks the other
  two, and nothing ever said so.
- **A drive computer**, on the same `doctrine` stat as the battle computer. It
  weighs how far an axis is out against where its drift is taking it, and
  cannot fire harder than the hull allows.
- **And it is priced.** First measurement: the autopilot docked 59.5% of the
  time against a careful hand's 58.5% — identical, free, and therefore an
  argument for never flying an approach again. A computer-flown dock is graded
  as a bare clean one now: 68% at grade 1.00 against 68% at grade 2.39 by
  hand. The machine brings you alongside; it does not bring you alongside
  well.
- **A guard for last cycle's lesson.** A suite that does not exist looks
  exactly like a suite that passes — running a missing one prints nothing and
  exits zero. `tests/test_harness_guard.py` asserts every name in
  `ALL_SUITES` is dispatched to a real module with a `run`. Proven by removing
  a registration: it names the missing suite. Written as a subprocess first,
  which recursed until it timed out, because it lives inside a suite.
- **And the derived-state trap again**, in my own hands: I set
  `ship_stats.doctrine` for a screenshot and `recompute()` threw it away, so
  the screen reported no computer fitted. Third time; `stock_fx` is the input,
  `ship_stats` is the output.
- 557 checks green, every file under 500 lines — `test_sim` crossed it, so the
  harness checks moved out.

## 2026-07-28 — SEEDFALL: the hands get older, and can finally be replaced

A player asked why hands have no ages. Because `ship.crew` was an integer.

- **A mean and a spread on the hull**, aged by proper time at the lineage's
  rate. Still a mass — the game treats the hands as a headcount on purpose —
  but a mass that gets older. Measured: a fed crew goes from 29 to 98 over
  seventy years and falls from 34 aboard to 6.
- **The spread makes it a slope.** Forty hands started four years short of the
  span leave over seven years in six separate losses, not one cliff.
- **They can be signed on.** `ship.crew` only ever fell before — combat,
  hunger, a sleep somebody did not wake from — and there was no way to take
  anybody on at all. A crew that can only shrink is an unfixable loss rather
  than something you manage. Within the berths that exist, for a fee, and a
  young intake pulls an old deck from 80 back to 49.
- **Dormancy now reaches them**, which closes the loop on last cycle: a
  sleeping mess deck ages 0.21 years where an awake one ages 1.00. That saving
  was previously real and unmeasurable, which is precisely why the
  `put_under` bug hid.

**Three faults of my own, two of them found by the tool I built last cycle.**

- The tripwire immediately reported four of my *new* constants unprotected —
  including `SIGNING_FEE`, whose check asserted `spent == SIGNING_FEE * 8`.
  That is the tautology again, on brand-new code, caught before it shipped
  rather than three cycles later. It asserts a range written in the check now.
- It also reported them unprotected for a second, different reason: the
  tripwire kept its **own copy of the suite list**, which went stale the
  moment a suite was added, so the `hands` suite was never run and the
  constants it protects looked unguarded. `ALL_SUITES` is published from
  `tests/__main__` now and the tool derives from it.
- And a `git checkout` I ran to undo a bad edit quietly reverted this cycle's
  suite registration, so `python3 -m seedfall.tests hands` printed nothing at
  all and exited zero. A suite that does not exist looks exactly like a suite
  that passes.
- 550 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: auditing the tests instead of trusting them

Last cycle I said the tautological-check habit was mine and I would watch for
it. Watching is not a method, so: a tool that changes every tuning constant in
the game and reports the ones nothing notices.

- **`tests/tripwire.py`.** Zero, double or halve each of 131 module-level
  constants; run the suites; report the survivors. A survivor is dead code,
  a tautologically-checked number, or a genuinely unpinned one.
- **60 of 131 are unprotected.** The worst is `approaches.ODDS_PER_DAY` —
  zero it and no envoy ever arrives again, retiring the whole diplomacy
  feature I shipped two cycles ago, with 535 checks still green.
- **The tool poisoned itself first, and I nearly believed it.** Its first run
  said sixteen. It was rewriting source between runs while Python served
  `.pyc` files compiled from the *mutated* text, so restores did not reliably
  take — I found it when a check crashed with `PER_LOSS` reading 0.0 at
  runtime and 9.0 on disk. Bytecode is disabled in the children now, and the
  caches are cleared at the start. A tool that audits the tests has to be
  audited too, and the honest number is nearly four times the flattering one.
- **`tests/test_tuning.py`** pins the eight worst, every one against a figure
  written in the check rather than against the constant it guards. 52 remain,
  listed in the task queue.
- **A killed sweep left mutated source in the tree.** It restores on SIGINT,
  SIGTERM and exit now — a tool that edits source has to put it back on the
  way out, not only on the happy path.

**And two player questions, both of which found real holes.**

*"Why don't hands have ages?"* Because `ship.crew` is an integer. The 34 hands
are a headcount with nothing to hang an age on, so "your crew ages on a long
crossing" is true for 3 of 37 people — and it is exactly why last cycle's
dormancy bug hid so well. Queued with a design: a mean and a spread on the
ship, not 34 records.

*"Why can a ship refit when not docked at a shipyard?"* Because the rule was
in the button and not the simulation. `apply_refit` checked the design and the
cost and nothing else, so the remote bridge could strip a hull in deep space —
and the button's own rule tested "this system has a port", which is neither
being alongside nor being at a yard. `shipyard.can_refit_here` now expresses
it through the anchorages, and two existing checks that had been quietly
relying on the loophole had to be docked first.

- 543 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: sleeping through it, and a sugar that finally does something

The half of the player's time request I left undone. Ageing, lineages and
upkeep shipped; the counter-measures did not, so a long crossing had exactly
one answer — fly harder, pay in reaction mass. An engineering answer to a
biological problem.

- **`trehalose` finally does something.** It has been in the commodity tables
  from the beginning, described as vitrified sugar with CAHS proteins that
  replaces the water in a cell and holds it unbreathing — the sugar real
  tardigrades use — and nothing had ever consumed a gram of it.
- **Three methods and a null.** Cold sleep, trehalose vitrification, and
  low-power idle, which only a Dry Choir lineage can do because it is not
  sleep. Measured over 600 days: a sleeper ages 0.07 years against the watch's
  1.64 and eats 13 tonnes against 61.
- **It does not stack free with dilation.** Both cost the ship's own work, so
  doing both costs it twice: 712 research over a year awake at rest, 154
  asleep, 123 at dilation 4, 30 doing both.
- **A bug that made the headline benefit unreal.** `put_under` slept the hands
  first and the officers last, so with 34 hands and 30 sleepers *no officer
  ever went under* — and officers are the only people in the game who have an
  age. The saving the screen advertised was arithmetically invisible. Sleepers
  are drawn proportionally now, with at least one officer always on the
  bridge, and the measured ageing moved from 1.64 → 1.64 → 1.64 across all
  three methods to 1.64 → 0.58 → 0.07.
- **Ninety-nine tonnes of sugar.** The first vitrification rate put a third of
  the hold and sixty thousand credits into one crossing, which is not an
  expensive option but a closed door. Cut to 32 tonnes.
- **The screen quoted arithmetic about a crew that was not aboard** — the
  Dry-Choir-only method showed ageing and ration savings computed from *this*
  hull's wet lineage while being disabled. It states its case in words now.
- **Another tautological check of mine**, the third in as many cycles: the
  watch floor asserted `total - room >= round(total * MIN_WATCH)`, which reads
  the constant whose effect it tests and passes with it zeroed, because
  `max(1, …)` leaves one person awake and the arithmetic agrees. One person is
  not a watch on a thirty-seven-hand hull. It asserts an absolute floor now.
- 535 checks green, every file under 500 lines.
