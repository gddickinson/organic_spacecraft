# Session log, part 20 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-29; undated entries keep their original place.

## 2026-07-29 — SEEDFALL: four more doors into the same hull

Priority four: richer helm and flight. Two cycles went into bounding heat, and
this is the one that found out how incomplete that was.

- **`INTERFACE.md` said there were exactly two places heat is added.** There
  were six. A crossing watch in `transit`, a flight incident in `flight`, an
  action's own effects in `actions` and taking a hit in `damage` all put heat
  into a hull without ever consulting the ceiling.
- **A single fault took a hull sitting at the ceiling to 2.36x its cap** —
  the incident fires *after* `travel_to` clamps, so it lands on top. That is
  precisely the compounding the ceiling exists to stop, since every penalty
  for running hot scales with how far over you are.
- **The fix is not another `cook()` call.** `ship.add_heat` is now the only
  way to put heat into a hull, and it clamps on the way in. Asking six callers
  to remember is what four of them did not do. Measured after: eight hard
  burns with faults land at exactly 2.00x, never past it.
- **A smaller thing in the same function.** A fuel fault rolled two to eight
  tonnes, took as much as the tank actually held, and reported the *roll*.
  One in five told a captain with three tonnes aboard that eight had gone.

**On the guard, and on redundant guards.** The check that would have found all
four is a static one: nothing outside `sim/ship.py` may write `\.heat +=`. It
needs one deliberate exception noted in the file — `sim/customs.py` has its own
`add_heat`, which is scrutiny from the revenue and shares nothing with the
thermal system.

One mutation missed: removing `add_heat`'s own `max(0.0, ...)` changed
nothing, because `cook` already floors at zero. That is a redundant guard
rather than a hole in the check, so I removed the redundancy instead of
excusing it — one floor, in one place — and pointed the mutation at the floor
that is actually load-bearing. It bites.

Five checks in a new `test_thermal_doors` suite, every one proven to bite.
660 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a turn where nobody flew the ship

Priority three: positional combat with crew stations. Two doors again, and
this time the older one switched the whole system off.

- **`take_turn` takes two shapes of action.** `{"type": "station", "order":
  ...}` runs the crew stations — your seat takes your order, officers hold the
  other two. The older `{"type": "fire", "weapon_id": ...}` family never
  called `_run_stations` at all.
- **The battle screen still sends the older shape** for the firing picture's
  per-mount buttons and for abilities. So a captain who picked a mount instead
  of ordering a salvo lost their crew for that turn: nobody flew the ship,
  nobody stood in the engineering section. Measured on a hull at 30 heat, the
  turn ended at 24.0 through the old door against 19.44 through the new, and
  `helm_order` was still `None` afterwards.
- **Only `move` had ever been migrated**, which is how it stayed hidden. The
  obvious comparison — salvo against salvo — agrees whatever you do: on a
  light hull the seats have nothing to show, and on a heavy one the heat
  ceiling erases the difference before it can be read. It only appears below
  the ceiling, on a hull carrying heat.
- **`_run_seats` is called from both paths now.** All 650 existing checks
  stayed green, and outcomes over thirty seeds are identical either way.

**Four of my six mutations missed on the first run, and two of those were my
checks' fault.** The brace check asserted an upper bound — "sheds no more than
three vents" — which a skipped section and an unattended one both satisfy. It
asserts the exact three now: the brace, the section standing *attended*
because that is where the captain is, and the end of the turn. The other two
misses were bad mutations that left the calls in place and only discarded
their return values, which changes nothing.

Worth knowing rather than fixing: the helm runs before the guns, so a mount
that bears when you press the button may not bear when the shot goes. That was
already true of the station path; it is now true of the named-mount buttons
too, which is the point of the change rather than a side effect.

Five checks in a new `test_seatwork` suite, every one proven to bite.
655 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a treaty that was free if you waited to be asked

Every area of the breadth list has now had a cycle, so back to the top of the
priority list: diplomacy. Last time was the overtures you make; this is the
half where the powers come to you.

`approach.answer` carries the comment "everything here must match `preview`
exactly". Four things did not.

- **Signing a treaty was free through one door.** `diplomacy.perform` charges
  the signatory's enemies when you propose one; `approach.answer` appended
  the treaty and charged nobody. Measured with all four powers at −70 with
  each other: proposing cost −6 with each of the other three, accepting the
  identical instrument cost **nothing at all**. A treaty is the most public
  act in the game, and there was a door through which it was invisible —
  which is precisely what the last diplomacy cycle set out to end.
  `TREATY_WEIGHT` now lives in `data/diplomacy.py` and both doors read it.
- **Haggling claimed the treasury.** The envoy screen printed "Treasury:
  +794" for a push. Pushing raises what is *on the table*; nothing is paid
  until you accept. `preview` reports `offer` separately from `credits` now,
  and the card reads "What is on the table: +794 credits".
- **Two silences**: accepting a denunciation drives the two powers a further
  six apart, and refusing a levy is filed as a grievance. Both happened, and
  neither appeared in the preview the screen is built from. Both do now.

**A detail worth keeping.** The existing check `pushing moves the price once
and only once` compared the movement of the offer against `preview["credits"]`
— and was right about the semantics all along. The screen read the same field
as the treasury. One number, two readings, and the screen had the wrong one; a
check can be correct and still leave a defect standing if something else reads
its subject differently.

The envoy triggers themselves measured clean: all five kinds reachable once
their preconditions are built, and my first sweep only missed two because the
driver never raised standing or planted a colony — the same confounding as the
combat cycle, caught by constructing the conditions instead.

Seven checks in a new `test_envoy` suite, every one proven to bite.
650 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a bench that was never fully stocked

Research, the last area of the breadth list this run had not touched. The
technology tree measured clean — all 61 reachable, no dangling prerequisites,
all eight bonus keys consumed. The defect was in the suite that measures it.

- **`test_provisional` hand-typed its evidence kinds and got three of them
  wrong.** It stocked `survey`, `specimen`, `field`, `relic`, `trade`,
  `hardware`. There are four kinds: `survey`, `specimen`, `hardware`,
  `reading`. So three names did nothing — `inquiry.add` returns 0.0 for a name
  it does not know, silently — and `reading`, which is real, was never stocked
  at all.
- **Six of the ten branch mixes ask for `reading`.** Cognition wants 35% of
  it, xenology 65%. So every programme in those branches was being measured on
  a bench starved of a quarter to a third of its input, in the suite that
  decides whether any research approach dominates. Measured: cognition
  unlocks in 165 days on a full bench and 214 without it; xenology 170 against
  215.
- **The conclusion survived, but the numbers moved a long way.** With the
  bench correct, `push` is now the *slowest* route to sound technology at 420
  days where it had been the fastest. "No approach is best at everything"
  still holds, and now holds against a measurement that is true.
- **The screen was right all along** — the research panel has always shown
  "Xenolith readings · 140 held · 33 wanted". Only the fixture was wrong.

**The guard, and the first version of it that did not work.** I wrote a check
that scans call sites for evidence-kind literals. It passed the mutation that
restored the bad tuple — because `test_provisional` passes a *variable*, so no
search of call sites could ever have seen the bug it was written for. It now
also walks the AST for any `*KINDS` constant that is a plain list of strings,
under the rule that a list naming any real kind must name only real ones —
which catches the hand-typed six and leaves `test_cargo`'s `CARGO_KINDS`,
about contracts and mentioning no evidence, alone.

Five checks in a new `test_bench_kinds` suite, every one proven to bite.
643 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: five things the bridge never noticed

Political machinations — the convictions officers hold and what moves them.
The audit that found the dead colony effect, asked here: does every event an
officer has an opinion about ever actually happen? Five did not.

- **`promoted`, +5 to every officer aboard**, because it sits in `UNIVERSAL`
  and applies whatever they believe. `crew.grant_xp` returns the list of
  people it has just promoted — the return value exists for this — and **all
  eight call sites threw it away**. So a career built over a decade moved
  nobody, and was not even written in the log. It now reports itself: the ship
  feels the event, the officer promoted gets `PROMOTION_OWN` on top (+14
  against a bystander's +5), and the log reads "Feodor Sarkis is made Science
  Officer 4."
- **`licence_served` and `free_served`, +11 each** — the largest single thing
  either conviction believes in, and never delivered. A Charter partisan could
  run Charter commissions for ten years and feel it only as the
  `commission_done` everybody else felt. `loyalty.served` fires when a
  commission is paid, and only for partisans of the power that issued it.
- **`burner_served` and `xeno_served`** were unreachable — their convictions
  have no aligned power — and duplicated `bloom_cleansed` and
  `xeno_incorporated`, which do fire. Removed, rather than left in the data
  claiming something untrue.
- **Loyalty still bites**, checked deliberately so none of this makes it
  toothless: an unpaid bridge goes restless around month eight and is empty by
  month twelve.

**Two of my own checks were too weak and mutation caught both.**
- "Finishing a commission delivers it" asserted only that loyalty moved. But
  `_pay` also adjusts standing, and `loyalty.align` drags partisans along at a
  quarter rate — about +1.25, enough to pass with `served` deleted entirely.
  It now asserts the partisan moves by at least what the conviction declares.
- Both promotion checks asserted that officers were *reported* promoted and
  never that their level rose. Deleting `o.level += 1` passed everything.

Six checks in a new `test_conviction` suite, every one proven to bite.
638 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a chart that never went off

Exploration and mapping, which had not had a cycle. Surveys measured clean —
the forecast matches the days actually spent, including on a dry tank; all
four find categories are consumed; all four methods are reachable, `sweep`
included once you are parked in-system rather than out at the arrival radius.
Charts were where it was.

- **`charts.freshness` says "a chart made long ago is worth less. The sector
  moves." It was never once true.** Dating a finished chart lived in
  `actions.survey`, the single-method call the four survey methods replaced.
  The screen calls `survey.perform`, which did not date it. So no chart a
  player ever made was stamped, freshness returned 1.0 for ever, and
  `FRESH_DAYS` and `STALE_FLOOR` decided nothing at all.
- **The survey office had been written for this the whole time**, carrying an
  "Age of the survey" row behind `if fresh < 0.95` that could not fire. It now
  reads "62% of fresh" in amber beside a price that has fallen with it.
- **Measured after:** ₡14,794 fresh, ₡10,726 at a year, ₡6,657 at the floor.
  Selling a chart while it is current is a decision again.

**Why nothing caught it, which is the part worth keeping.** Surveying a body
has two doors: `actions.survey`, used by the remote bridge and by every test
driver in the suite, and `survey.perform`, used by the screen. They did
different things — and every driver went through the door that worked, so the
suite saw a system behaving correctly while no player ever could. The first
check in the new suite asks the general question directly: do both doors leave
the same state behind.

**And I wrote a tautology, and mutation caught it.** The ageing check measured
freshness at `FRESH_DAYS // 2`, `FRESH_DAYS` and `FRESH_DAYS * 3` — so
widening the window to ten thousand years passed cleanly, because the check
simply waited ten thousand years. It moves the ruler with the thing it
measures. The ages are plain numbers now: 360 days, 730, 2200.

Five checks in a new `test_charting` suite, every one proven to bite.
632 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a penalty that paid better than the reward

Surface expeditions, which had not had a cycle.

- **Stranding was the best way to play the ground.** `haul_kept` applied the
  carrying limit when the party walked home and **skipped it entirely when
  they stranded**, returning 40% of everything ever picked up, uncapped. Five
  hundred tonnes collected came home as **200 t stranded against 60 t
  returned**. Measured end to end: a leader who never turned back kept 933 t,
  one who always walked home kept 41 t. Twenty-three times better to fail.
- **It also contradicted its own ending**, which says everything not on their
  backs stays where it fell.
- **The order is the fix**: what they can carry, and *then* what stranding
  costs. Now 500 t is 60 t home and 24 t stranded, and walking home wins.
- **The turn-back margin is a real decision again**, with a peak in the
  middle: 29 t at margin 0, 35 t at 4, 23 t at 14. Too little strands the
  party; too much spends the expedition walking.
- **Supply could go to −1**, because a crossing costing two could be paid out
  of one. Floored, so no screen has to print it.
- **The screen says what the lander will lift.** "Carrying 140 / 60" in amber
  left the captain to infer that eighty tonnes would cease to exist, and said
  nothing about stranding. It now reads "Comes up 60 t — 80 t stays" and "If
  they strand 24 t", both off `landing_forecast`, which is `haul_kept` — so
  the forecast and the outcome cannot drift.

**`tests/ground_ai.py`, because there was no way to measure this.** The same
gap combat had before `captain_ai`: a driver that wanders and grabs never goes
back to the lander, so every party strands and every policy scores identically.
The one decision the ground poses is how much supply to keep for the walk home,
and it was invisible to a driver that never walked home.

**On thresholds.** The peak-in-the-middle check first failed at 40 seeds a
margin — the gap to margin 0 wobbles between 1.12x and 1.21x there. Rather
than loosen the threshold to whatever passed, I measured at 120 (three seconds
for six hundred expeditions) and asserted below what that showed. The claim
that held at every sample size is the structural one: the best margin is
inside the range rather than at an end of it.

Six checks in a new `test_landing` suite, every one proven to bite.
627 checks green, nothing over 500 lines.

## 2026-07-29 — SEEDFALL: a favour that was never granted

Trading, which had not had a cycle. `market.quote_buy`'s own docstring names
the invariant worth checking — "a screen that quotes one number and charges
another is the defect this project keeps finding" — so I checked it.

- **The office rate was applied at the till.** With it running the board
  showed 36/t and the counter charged 31.68; the board said the port paid 29
  and it paid 32.95. Exactly the split that helper exists to prevent.
- **Except it never ran.** `Favour.lasts` is a window in days, a quiet price
  is granted "this once", so it carries `lasts=0` — and `ask()` recorded
  favours under `if favour.lasts:`. A zero-day favour fell straight through.
  Measured by playing: asking cost **12.7 regard**, stored nothing, and the
  purchase that followed was charged the full posted price. One of the five
  favours the game advertises as "read somewhere real" bought nothing at all.
- **Fixed both ways.** A one-shot is held in its own list until used, and the
  rate lives in `quote_buy`/`quote_sell` so board and counter cannot disagree.
  The desk says "good once, next time you deal here"; the market board
  explains why its numbers are not the posted ones.

**The check that should have caught it, and why it did not.** `test_officials`
had "every favour is read somewhere in the game", and for the quiet price it
wrote the favour straight into the dated `favours` dict by hand. That state is
unreachable — `ask` could never produce it — so the check proved the price
code worked given something the game cannot do, and read as coverage. It now
grants through `ask`, and reintroducing the bug fails it.

That is three cycles running where the lesson was the same: a whitelist of
known keys, a coverage run pinned to one lucky seed, and now a fixture that
sets up a state the game cannot reach.

**Two files were over five hundred lines and are not now.**
- `ui/port_view.py` hit 509. The contract board came out into
  `ui/board_panel.py`. I extracted it mechanically and then ran a static
  undefined-name scan, which found three names — `Panel`, `spacer`,
  `FACTIONS_BY_ID` — that had travelled without their imports, and fourteen
  left orphaned behind. Worth doing *before* the suite, not after.
- `tests/__main__.py` hit 525, because every cycle added another five-line
  `if "name" in wanted:` block. Seventy-eight of them, all the same block. It
  is a table in `tests/suites.py` now and the dispatch is 50 lines. The
  hand-kept `ALL_SUITES` beside it had already drifted from the real dispatch
  order at index 46, which is what a second copy always does.

Five checks in a new `test_counter` suite, every one proven to bite, plus the
repaired `test_officials` check. 621 checks green, and nothing over 500 lines.

## 2026-07-28 — SEEDFALL: a board that offers work you can reach

Missions, which had not had a cycle. The general question again: is every
posting on the contract board actually doable?

- **65% of targeted postings named a system outside the reachable component.**
  `_pick_target`'s docstring said "reachable in principle" and its whole test
  was `bloom < 0.4`. Reachability is transitive and nothing checked it. At the
  opening drive 15 of 42 systems can be flown to; deliver ran 69% unreachable,
  survey 63%, expedition 57%. Letting one lapse costs standing with the issuer.
- **And the card never said where the work was** — reward, deadline, standing,
  cargo cost, allegiance cost, and no destination at all.
- **Both halves fixed.** The generator asks `reach.component`. `reach.route_to`
  gives fewest hops and the days they cost, checked against `jump_quote` for
  single hops. The card reads "Nine's Rise — 3 jump(s), about 20 days each
  way", and says so in warn colour if the deadline will not cover it.
- **Feasibility is judged one way, not round trip.** `check()` completes a
  delivery, a survey and a ground contract on *arrival*. Judging round-trip
  flagged three postings that are perfectly doable — a warning nobody needs
  teaches captains to ignore warnings.

**Then the full suite caught a regression, and it was not the one it looked
like.** `test_chronicle`'s "the chronicle does everything it claims" started
failing on `planted a colony`. My change had shifted the driver's path — but
sweeping seeds showed colonies were planted by **1 seed in 24 under the old
targeting too**. The check was pinned to the single seed that happened to work.

The real cause was a driver bug of some age. `chronicle._refit_here` still
tested "the system has a port", which stopped being the rule when
`shipyard.can_refit_here` tightened to "alongside a yard" — so the driver
called `apply_refit` from wherever it was, got "you are not alongside a yard"
back, and dropped it. Measured: 822 of 1506 founding refusals were "no seed
bay fitted". Teaching it to put in at a yard first took that to 100, and
planting from 1 seed in 24 to 6 in 48. The original check seed passes again on
its own merits, and the first chronicle check went from 0 colonies to 5.

I have recorded the measured rarity in the check itself, because a capability
only one seed in twenty-four exercises is not being covered, it is being got
away with.

Five checks in a new `test_postings` suite, every one proven to bite —
including one that needed a deliberately impossible deadline, because with
every real posting comfortably in time, "always says yes" and "is right" look
identical. 616 checks green.

## 2026-07-28 — SEEDFALL: a grant that does nothing, and a card that says nothing

Empire-building, which had not had a cycle. Measured the nineteen colony
classes for payback first — that turned up nothing damning (pomona_grove pays
back in 45 days, the negative-income classes justify themselves on effects) —
so I asked instead whether the effects they advertise are read at all.

- **`megastructure` was declared by the ARCA Habitat and read by nothing.**
  400,000 credits, 2,600 tonnes of ore, 900 days, a million people, and the
  one property that made it an ARCA Habitat rather than a very good mine was
  consulted by no line of the game. A five-by-ten-kilometre drum of spun rock
  was overgrown by the Bloom on exactly the same roll as a lichen farm.
- **It now means what it should.** `bloom_attack` already had the machinery —
  a colony's own `ward` halves its chance of being taken — so a megastructure
  guards at 0.85. Measured: a farm is taken in 29% of attacks, the drum in 4%.
  Not immunity; `bloom_attack`'s own comment promises the Bloom gets
  everything unattended eventually, and a check holds it to that.
- **The founding screen printed the internal keys.** `"Grants: " + ", ".join
  (effects)` — so a captain weighing nine hundred days read "Grants:
  megastructure" and could not find out what it meant, which was just as well.
  `EFFECT_TEXT` gives all fourteen a sentence and the cards print those.

**What actually found it.** Not a whitelist. Two suites already listed
`megastructure` in a `KNOWN_EFFECTS` set — but that only asserts nobody
declares an *unknown* key, never that a declared one is consumed. It read like
coverage and was not. The new check asks the general question instead — *is
every declared effect read by something* — and on its first run found a
**second** dead key I had not looked for: `drydock`.

**And `drydock` turned out not to be the bug it looked like.** Its card says
"refits and repairs here, without flying to a yard", and I nearly reported it
as a broken promise. Playing it showed refitting at an Orbital Drydock works
fine — because every class granting `drydock` also grants `build_here`, which
`_colony_services` does read. So the promise was kept by a second flag
happening to be set. `drydock` now reads alongside `build_here`: nothing
currently plantable changes, and a dock that is only a dock works as its card
reads instead of silently granting nothing.

My own error worth keeping: I first "found" that a lichen dome lets you refit.
It does not — I had parked the ship on the body the Fleet Hub orbits, so
`docked_at` returned the Hub, which has a yard. Checked before reporting.

`ui/system_view.py` is at 494 lines. The next thing added to it should split
it first.

Five checks in a new `test_grants` suite, every one proven to bite.
611 checks green.
