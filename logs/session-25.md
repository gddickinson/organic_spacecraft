# Session log, part 25 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

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
