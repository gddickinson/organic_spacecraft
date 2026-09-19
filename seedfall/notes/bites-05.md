# The parts that will bite you (5 of 5)

Moved out of `seedfall/INTERFACE.md`, which is now only the map. Text unchanged.

  and 1.2% of a hull that heals itself. Nobody would ever have coasted — and
  its own blurb promised the radiators would complain. A burn now leaves heat
  in the hull (62% of cap on a hard burn), a hot hull is riskier to burn again
  in, and over the cap the radiators stop keeping up and the hull cooks. One
  hard burn from cold is free; a habit of them costs 11% of the hull.
- **Heat is no longer a one-way ratchet.** Nothing outside combat added it and
  nothing shed it, so a ship sat at thirty for twelve hundred days with vents
  rated at twenty-four a turn. `ship.cool()` runs on the clock. `REST_VENT` is
  not a physical ratio — it is the rate that makes heat a state you fly in
  rather than one that has gone by the time you arrive.
- **A rig stops when the hold is full.** `extract()` used to compute the whole
  spell's haul, take `min(raised, cargo_free)` and deplete the body for the
  full duration anyway. Measured: sixty days with an empty hold took 106.2 t
  and worked the body out by 0.384; with the hold 97% full it took 10.2 t and
  worked it out by the *identical* 0.384. Ninety-six tonnes raised and thrown
  away, a third of the body spent, and nothing said so. The working now ends
  when there is nowhere to put what it raises, and time and depletion both
  follow what was actually lifted.
- **A full hold must not be a stranding.** Refusing to work a body with
  nowhere to put the ore is right, and on its own it deadlocks: no room to mine
  ice for reaction mass, no mass to jump on, and the only way to dump anything
  was the contraband panel, which appears solely when carrying contraband at a
  hostile port. `trade.jettison()` is general now and the hold has a vent
  control. The project already holds that an empty tank must not be a deadlock;
  this is the same rule from the other side.
- **Everything that can refuse a working is checked before the ship flies out
  to it.** `flight.ensure_at()` came first, so a refusal cost twelve days of
  flying and gave nothing back. The regression check caught that, not me.
- **The panel forecasts the spell.** It quoted tonnes a day and offered "Work
  it — 30 days" with no notion of what that came to; now it says "25 t in 14
  days — the hold fills first".
- **The freight desk is an information tool with a floor under it.** Within a
  starting jump only 5% of lane/goods pairs show a positive spread, and the
  runs that do exist are invisible — finding one means visiting every
  neighbour first. The desk draws on two honest sources: your own register
  (real prices, going stale) and the harbourmaster, who names his own power's
  ports and what they are short of but will not quote their board.
- **A spread thinner than the drift is not a trade.** `tick_market` moves
  supply about 1.8% a day plus a random walk, so a thin margin is gone by the
  time the hull arrives. Flown and banded by spread, every band below a fifth
  loses money on average, so `MIN_SPREAD` is 0.20 and the desk will not
  recommend anything under it. Measured over two-year careers: 981 credits on
  your own notes, 33,069 following the desk.
- **What a run clears is the voyage, not the spread.** Ranking by margin per
  tonne is how a captain flies a four-credit spread nine light-years and pays
  for the reaction mass themselves.
- **Short-range legal arbitrage is thin by design and that is fine.** Ports of
  one power want the same things, so trading means crossing into somebody
  else's space. The contract board is the early game — every one of twelve
  openings has affordable work — and the desk comes into its own with range and
  a register.
- **A cargo contract is priced against what its cargo costs.** The reward was
  `amount * (base * 0.55 + rate * 0.4)`, and `base * 0.55` is the *floor* — what
  a market holding none of a good pays for it. Nobody sells at the floor, so the
  board priced its own work against a number that does not exist: 44% of cargo
  contracts paid less than sourcing their cargo, worst case fifty thousand
  credits down. `cargo_cost()` prices it properly and the board shows the
  arithmetic, because a fee on its own made a trap look like a living.
- **Distance pays haulage on cargo, not a share of the goods.** The old
  multiplicative premium turned an eighty-tonne silicon run into 130,000 clear.
  Freight is priced by mass and distance — a tonne is a tonne in the hold.
- **A quote prices for the captain reading it; generation prices neutrally.** A
  contract's fee cannot depend on the standing of whoever happens to see the
  board, but what *you* will be charged does. Getting that backwards made the
  quote wrong by two per cent, which the check caught.
- **A field note is kept, not printed once.** Recovered lore lived in
  `expedition.lore`, was shown in the report dialog, and went out with the
  expedition object — never on the `Game`, never in the codex, and worth
  nothing, since `REWARD_SCALE["lore"]` was (0, 0). Three feature options
  existed to display a sentence and take it away. Notes now have identity
  (`data/fieldnotes.py`), are filed with the body, system and day they came
  from, and are evidence on an inquiry track, so going down and reading the
  room is worth doing.
- **A note is not cargo.** Stranding costs 60% of the haul; it does not cost
  what somebody already read and remembered. `test_notes.py` pins that.
- **No screen writes the ledger.** Seventeen sites across four view modules
  spent credits and moved standing directly — buying, selling, hiring, paying a
  bonus, repairing, buying a lead, commissioning bench time, scrapping a hull,
  tying up at a quay, and moving contraband off the books. Every one was a rule
  only a mouse could perform. They live in `sim/trade.py`, `sim/services.py`,
  `sim/crew.py`, `sim/shipyard.py`, `sim/customs.py` and `sim/minigames.py` now.
- **`test_layers.py` enforces the one-directional rule instead of stating it.**
  It matches ledger writes structurally — assignment to `.credits`, augmented
  assignment, `game.rep[…] = …`, any call to `adjust_rep` — and carries a
  self-check that plants all three shapes and fails if the matcher misses any,
  because a structural matcher that silently matches nothing would have passed
  on the day the defect was at its worst.
- **What a fight leaves behind belongs to the rules, not the screen.** Salvage,
  loot, cargo off the wreck, bounty progress, seized xenology, instar kills,
  consorts lost, loyalty and every standing change used to live in
  `ui/battle_view.py._finish()`; `sim/combat.py` held a loot dict and nothing
  else. Nothing headless could resolve an engagement, so every balance run that
  fought a battle collected no loot, no standing and no bounty credit. It is
  `sim/aftermath.resolve()` now, and the view reads what it returns.
- **`Battle.settled` makes the payout idempotent.** Both the screen and a
  headless driver can reach the end of a fight; neither may collect the salvage
  twice.
- **A kill is noted by everyone who dislikes the victim.** Destroying a hull
  moved its owner and nobody else, in a sector whose whole politics is a
  relations matrix. It now pays the owner's rivals a share scaled by the same
  severity ramp `sim/allegiance.py` uses, so a cordial sector gloats not at all
  and one at war gloats loudly. A Bloom kill pleases all four powers rather
  than the Charter alone, which is what it did — hardcoded, in a screen.
- **A chart is priced on what it says, not on how many bodies it has.**
  `survey_value()` was `460 + 210 * len(bodies)`, so a system with a buried
  Abyssal site and ore worth crossing the sector for fetched what five bare
  rocks fetched. Measured: charting the home system took 53 days and paid
  1,510 — 28 credits a day, against roughly 1,600 for smuggling. The whole
  42-system sector came to 55,014, about one contraband run.
- **The price list is scaled against the rest of the economy, not chosen.** The
  best contract in the game pays about 27,000 and the dearest hull 900,000. A
  first pass put a remarkable system's chart at 92,000 — over three times the
  best contract — which fixed exploration being worthless by making it the
  best-paying thing in the sector. The numbers in `data/charts.py` land a
  median chart near 26,000 and charting near 750 credits a day.
- **Who buys is a decision, because the powers want different things.** The Dry
  Choir pays over the odds for life and anomalies, the Yards for ore and sites,
  the Charter for anything alive or old or growing. Best and worst buyer differ
  by 1.6x on average and the best buyer varies by system, so a chart is
  something you carry to the right quay.
- **Charts go stale.** A survey is dated when it is finished and decays to 45%
  over two years, which makes a survey circuit a living rather than a one-off
  sweep of the sector.
- **Claims and holdings have to be able to collide.** `ventures._claimable()`
  used to exclude any system the player held a colony in, and `can_found()`
  never looked at `system.faction` — so the powers declined to contest your
  ground and you could squat on theirs, and territory was never once disputed.
  Both directions are live now, through `sim/territory.py`.
- **A demand is something you are in the middle of**, so `Demand` is a field on
  the `Game` with an `.over` flag and `window.go()` diverts to it. `test_resume`
  picked it up as the sixth guarded activity with no prompting — which is the
  whole point of writing that check as a rule rather than a list.
- **Every answer to a demand costs something different.** Paying the levy keeps
  the holding and gives up 30% of what it makes; ceding loses it and reads
  best with them; refusing keeps it, costs standing, and means somebody comes
  for it — measured at 12 of 12 defiant holdings seized within eight years. A
  claim that lapses cancels the standoff rather than leaving it hanging.
- **Work for a power is a position, not an errand.** Completing a contract
  charges you standing with everyone that power is at odds with, scaled by how
  bad the rift is (`sim/allegiance.py`). `contracts.py` did not import
  `diplomacy` at all, so you could be the Charter's courier, the Concordat's
  bounty hunter and the Freeholds' prospector in the same week while all three
  were at war, and every one of them thought better of you for it.
- **The penalty is not the point; the escape is.** Severity ramps from zero at
  −15 to full at −70, so brokering a rift *part* of the way down is worth doing.
  Measured: the same 28 jobs return 108 total standing in a hostile sector and
  170 in a brokered one. That is what finally gives the relations matrix a job
  in ordinary play rather than only at the Concord ending.
- **Contraband needs both halves or it is not a trade.** A good that is
  outlawed somewhere has no posted price there and therefore a much better
  unposted one (`customs.premium`), and the same power opens your hold at the
  dock (`customs.inspect`). Shipping only the search would be a tax nobody
  would choose to pay; shipping only the premium is what the game already had,
  and measurement said it beat honest trade outright.
- **Scrutiny is the brake.** Selling into a black market and being cleared both
  raise a per-faction heat that thins what they will pay, thickens the search,
  and decays on the clock. Without it one dock is an unlimited money printer.
  `COOLING` was tuned by playing careers, not chosen: at the first value a run
  put on more heat than a month shed, so every career ended down.
- **Mitigations multiply, they do not subtract.** Standing, a clean approach and
  a concealed hold each take a share off the odds. Subtracting them let a
  fitted-out hull with good standing drive the risk under the floor and stop
  being a smuggler at all.
- **A part that is kit for a trade is marked `civilian`** and NPC loadouts skip
  it. Adding two smuggling parts put them straight into the enemy outfit pool
  and broke the combat-assessment check — a feature about trade silently
  re-tuning every encounter in the game.
- **A dig banks per layer, not at the end.** `dig.work()` credits understanding
  as each stratum comes out, so a trench abandoned after the casing is worth the
  casing. That is the whole reason backfilling is a choice rather than a way of
  throwing the dig away, and it is what `test_dig.py` pins: restoring
  bank-at-the-end passes every other dig check and fails that one alone.
- **Anything you can be in the middle of belongs on the `Game`.** The window
  exposes `transit`, `docking`, `decoding`, `dig` and `decoding_tech` as properties
  over game fields; holding them on the window loses them over a save, which
  docking and decoding did unnoticed for many cycles. `test_resume.py` reads
  the guard in `window.go()`, takes every activity with an `.over` flag, and
  fails on any that is not a field on the `Game`.
- **A `Battle` stays on the window on purpose**, recorded in `battle_state` and
  in `TRANSIENT` in `test_resume.py`: combat resolves in one sitting and no
  clock runs during it. Anything else added to that allowlist needs its reason
  written down beside it.
- **Colony effects are a closed vocabulary.** `test_sim.py` asserts that every
  key in a `ColonyClass.effects` is one the game actually reads, so a typo in a
  station definition fails the suite instead of silently doing nothing.
