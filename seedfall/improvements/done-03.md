# SEEDFALL backlog — done, part 03 of 03

Moved out of `seedfall/IMPROVEMENTS.md`, which keeps only what is open. Order and wording are unchanged.

## Done — the nineteenth pass (2026-08-05): the reviews' residue, closed

Four sub-passes in value order, working the two review lists above the line.
Every fix carries a played claim; three new suites (`solvency`, `prize`,
`despatch`) hold them beside additions to eight existing ones.

**The economy cannot be conjured** (`tests/test_solvency.py`, 7 checks):

- **Scrapping never profits.** `scrap_value` prices the bill *as if the
  fabricator discount was taken* (Ship records no provenance, so the breaker
  assumes the cheapest build) and values returned matter as itself
  (`data/parts.material_value` — was a flat 60/t: ore at 143% of base,
  silicon at 7%). Swept 44 hulls: scrap pays 45% of the cheapest bill, never
  more. The +146,470/cycle exploit is dead.
- **Nothing outside the counter quotes the raw prices.** Five live call
  sites switched to `market.quote_*` (the freight desk's buy card and
  hearsay card, its fuel line, the port screen's bunkering button, the
  bridge's `market` verb, `is_stranded`'s escape price) and a source-scan
  check pins the rule with the two documented exceptions (`contracts`
  neutral generation, `industry`'s market twin).
- **A tonne of contraband no longer conjures a market.** `apply_sale` leaves
  a `base == 0, supply == 0` stock where it is — the tonnes land on the
  quay; the 14,300 cr/t scarcity-capped market the next tick used to adopt
  does not appear. 400 played days confirm.
- **Promotion happens.** `exchequer.would_yield` is one arithmetic for the
  ledger *and* the forecast — `payback` used to re-derive the curve bare
  (no capital bonus, no industries) and read "never pays" at every port in
  the sector. Played: a capital with three industries promotes at a 450-day
  payback, and a rich purse actually buys it. Bare berths still never
  promote, which is the deliberate half.
- Robots can no longer drive the treasury underwater (unpaid is starved,
  and a starved machine wears ×2); SOL-FORGE sites on sunward rock instead
  of a body kind no generator produces; the Cartel ending counts only
  living quotes at open ports (`market.confidence`, not a filing cabinet).

**The endgame arc holds** (`test_legacy` +4, `test_bloom_arc` +3):

- **Ruin is the captain's or nobody's.** `BloomState.fought` records only
  the player's own provocation (`provoke(npc=True)` for the powers'
  flotillas), and `_stood_through_it` reads it — `advance_days` alone used
  to take the ending on day 2,338.
- **The hunt never re-seeds the ground you stand on** (the `hunt` response
  wrote `location_id` over `_retarget`'s no-self-target rule at the exact
  moment `infested == 0` was earned), **`hunting()` is transient** (ends
  when the provocation decays) **and `_retarget` finally reads it** — a
  hunting Bloom's masses actually come for the hull now.
- **A closed epoch turns the age or rests.** `data/epochs` sequels
  (containment's triumph *is* concord's opening; exodus's failure *is*
  ruin's) open through the same `begin`; with no sequel the chronicle
  *rests* — `legacy.rested` suppresses re-detection and the calendar runs
  on. Measured before: 2,000 requested days moved the calendar 13 → 13.
- **No epoch is unfailable, and none untriumphable** — concord (ceiling
  0.884) and xenarch (0.838) re-pitched, and an arithmetic sweep in
  `test_legacy` holds all ten epochs' floors and ceilings against the
  break. **An unanswered situation is decided in absence** at its worst
  answer after 120 days — never answering used to collapse the ceiling to
  pure drift.
- **No sector is inert.** A Bloom stalled with no clean ground in seeding
  range makes one forced throw after ~3 stalled years (`threat.STALL_TICKS`)
  — deterministic on purpose: a live chance at 0.35 re-paced every slow
  sector and a naive five-year captain starved in a sector 37/42 drowned.
  90 of 500 sectors used to generate a Bloom that could never leave home.
- Combat's no-turn orders: straining against a grapple now costs the turn
  (it was an infinite loop for a driver — `grappled` only counts down in
  the end-of-turn the free return skipped); the silent unknown-station
  refusal speaks. **A capped overture is refused before it is paid**, and
  `offer_gain` caps at the room the ledger has left so the quoted rise is
  the delivered one (tribute at rep 100 used to charge 12,000, deliver
  +0.00, and still anger the signatory's rivals).

**Combat's arc around the fighting** (`tests/test_prize.py`, 7 checks;
`test_balance` +3):

- **Threat scales.** `encounters.draw_threat` is the one door for the
  difficulty number, reading the calendar and the hull actually flown —
  day one in the opening hull draws the old U(1, 3) untouched; day 1,200
  in a heavy hull draws a median 2.88 against 1.86. `engage.open_fire`
  draws from the same door (the default-1.0 spawn was the easiest fight in
  the game).
- **A hunt warrant is a hull with your name on it.** `warrants.bites`
  always documented that "encounters asks for hunt" and encounters never
  asked; `enforce`'s `law_hunted_by` flag was written and read by nothing.
  A stop that chose the hunt summons the hunter at the next arrival; a
  posted warrant finds you at 0.25 per arrival where the paper reaches.
- **Striking colours** sits between "kill it" and "let it go": a broken,
  spent crew strikes (`enemy_ai`, on the same resolve the fight runs on;
  the Bloom never does), and the captain decides once — prize crew
  (`sim/prize.py`; the hull joins the fleet through the consort machinery
  with a fresh uid), strip her holds (priced), or let them limp home
  (remembered kindly). Standing: driven-off 4 < struck 6 < destroyed 14,
  struck-and-taken 14. Endings moved to `battle_state` (one door for the
  resolver, `parley` and `prize`).
- **`nonlethal` means it** — the Photic Flash Organ's breach vents nobody,
  as the glossary always claimed. **Recovered tonnage is priced**
  (`aftermath.worth_of`) on the aftermath card — it was 1.5–10× the credit
  loot and invisible. **Brace has a button.** A mute enemy's Hail button is
  off, with the reason. **The Charter fields no armed vessel**, as its own
  book says — out of the encounter table, and pinned against its lore.

**The sector speaks, and the player can hear it** (`tests/test_despatch.py`,
5 checks):

- **`ui/despatch_view.py`** — the inbox `sim/comms.py` kept for six passes
  with zero UI callers: despatches with channel, staleness note and reply
  buttons (every action a `comms` door), plus a Chronicle tab over the full
  300-line log with a kind filter (the sidebar shows sixty; the rest were
  unreachable anywhere). HUD carries an unread counter that is a button.
  Bridge verbs `despatches`/`answer_signal` (deliberately *not* in
  `waiting`/`reply` — a bulletin must never deadlock a driven session).
- **Word travels.** A lost colony's bulletin rides couriers from the system
  that lost it (427 days from the far side, measured); an epoch's turning
  writes to the board. Bulletins unread for a year are swept as litter —
  the store grew without bound before — and an open question is never swept.
- **The keyboard means what it looks like.** A digit key is the rail
  position it opens (`4` opened the fifth entry, and two off by the end);
  W/A/S/D work wherever the flight clock runs (`DECK_SCREENS`, not
  `pilot` alone); "Keys 1–8" over fifteen screens, "Eight things" over
  thirty lessons and "Five endings" over ten are all counted now; the two
  channel tints that were not `theme.TINTS` keys are.

**Found on the way:** the suite's two speech checks assumed no live model
answers and failed on a machine running Ollama — the claim is about the
game when nothing answers, so they arrange it (a dead local port) instead
of assuming it. The seven law modules got their tripwire fast paths. And
`test_play`'s five-year solvency floor had been passing on an artifact —
the bot froze at day 1500 and a frozen captain cannot die; un-frozen, one
seed's sector legitimately drowns in year 4.8, so the check now owns the
*economy* (nobody starves, nobody in debt) and lets the sector's own
ending be the one thing that stops a run.

## Closed by the nineteenth pass — the 2026-08-05 endgame sweep

5,640 engagements across 5 factions × 9 hulls × difficulty 0.5–4.0 found
**no defects at all** in the fighting itself. Every arc defect it found is
now fixed and pinned: the refused brokerage (same day), Ruin-by-passivity,
the `hunt` self-seed, the frozen calendar after a closed epoch, the two
unfailable epochs, the inert-Bloom sectors, the dead `hunting()` read, the
no-turn orders and the capped overture. See the nineteenth pass above for
what each fix measured.

## Done — the eighteenth pass (2026-08-05): four powers, four laws

The governance survey's answer was "there is no law" — every legal act in the
game was one of four mechanics in a legal costume: a reputation delta, a
memory entry, a percentage skimmed at a till, or an escalation ladder bolted
to a berth. There is a law now, and the design decision that shaped all of it
was **not to build a police force.** `data/factions.py` says the Charter
"fields no armed vessel anywhere", and a sector-wide constabulary is exactly
the "single authority that could weaponise the reproduction licence" the
programme's own charter was written to prevent. So instead: four powers, four
legal cultures, each only as long as that power's arm.

**The spine.** An act → a charge → a judgment → a sanction → enforcement that
can actually reach you → a way back. Seven modules, one front door
(`sim/governance.tick`, which the clock calls once and which owns the order
the six others run in).

- `data/offences.py` — eleven offences, and **which powers recognise each**.
  Trespass offends everyone because everyone keeps a register; unlicensed
  germination is the Charter's alone, because the Freeholds post a price for
  unlicensed seed on the open market and a power cannot charge you with the
  thing it sells.
- `data/forums.py` — the four legal cultures, drawn from what each faction
  already was. The Charter: administrative, decides on paper, and its entire
  armoury is the word *no* — no clearance, no licence, no gate. The Concordat:
  arbitration over property, with hulls to collect it. The Freeholds: **no
  forum at all** — a claim becomes a price on your hull, posted openly and
  sold on. The Dry Choir: attainder by computation, no hearing, nowhere to
  stand, and what comes out is anathema.
- `sim/law.py` the record · `sim/dockets.py` witness and filing ·
  `sim/tribunal.py` the hearing · `sim/debts.py` money owed ·
  `sim/warrants.py` instruments · `sim/enforce.py` where it bites ·
  `sim/clemency.py` the way out · `ui/law_view.py` the docket screen.

**Being seen is not being charged**, and that is the load-bearing idea.
`dockets.witness` asks what a power actually has in a system — its quay, its
register, its hulls, or a friend with one of those — and returns 0 for a power
with nothing there, so nothing is recorded at all. Working the frontier is not
innocence; it is being unobserved, and it is allowed to feel different.

**Every dead reader from the survey is now wired to a live one.** Smuggling
risk was opt-in (`customs.inspect` had one call site while three buttons
docked you around it); `BURNED = 1.0` — "they are waiting for you" — was a
label no code read; patrols were furniture with `hostile=False`;
`grudge.hostile_open` was called only by its own test; the two purchasable
favours "a berth regardless" and "a word before it happens" bought nothing —
and the second's blurb literally reads *a levy, a search, **a claim** — you
hear about it first*; `may_engage` had no political gate, so you could open
fire inside a capital's approaches and the station would not react; the
Charter's licence was a tradeable commodity with no issuing authority and no
revocation. All of them do something now.

**Two faults found by playing it, both caught before they shipped:**

- **The law re-entered itself.** A patrol that stopped you charged two days
  with `advance_days`, which runs the clock, which runs the law, which stops
  you. It surfaced as a `RecursionError` in `settlement.maturity`, three
  modules from the cause — which is what re-entrancy always looks like from
  outside. There is a guard flag now and no clock inside the clock.
- **The layer generated its own work, geometrically.** A default charge
  decided in absence produced a default charge; its debt went unpaid and
  produced arrears; that was decided in absence too. Measured from a single
  contraband bust: **61,820 charges and ₡498 million owed inside eight
  years** — a save file that does not load rather than a game. A power now
  has *one* "you are not answering us" at a time and escalates the instrument
  instead of the paperwork: the same decade now ends at 3 charges and ₡45,000.

Nineteen played checks across `tests/test_law.py` and `tests/test_tribunal.py`,
including the two that matter most: **a captain who does nothing wrong is
never charged with anything** (three chronicles to day ~2,400, exposure 0.00),
and **the same act in front of the four forums produces four different
afternoons** — licence suspended, bond against the hull, a price on your hull,
and removal from the record.

## Closed by the eighteenth pass — the governance survey

Asked how debts are collected, laws enforced and crimes punished. The honest
answer is that **none of those systems exist as systems**. Every "legal" act
in the game is one of four mechanics in a legal costume: a reputation delta,
a memory entry, a percentage skimmed at a point of sale, or an escalation
ladder attached to a berth. That is a defensible design — justice in the
Verge is a relationship with a harbourmaster — but several pieces promise
more than they deliver, and those are the gaps worth closing:

- **Smuggling risk is opt-in.** `customs.inspect` has exactly one caller —
  the docking minigame — while `ui/system_view.py:135`, `ui/map_view.py:467`
  and `ui/anchorage_panel.py:88` all dock directly, one of them captioned
  "Skip the approach and dock directly". A whole risk/reward system is
  bypassed by a button.
- **`BURNED = 1.0` — "they are waiting for you" — is a label with nothing
  behind it.** No code path reads `heat >= BURNED`. The cheapest place in the
  game to put a picket at the jump exit or a pre-emptive board.
- **No debt exists at all**, and the one unguarded outflow (`robots.py:351`,
  the only `credits -=` without an affordability check) can put the treasury
  underwater with nothing in the game responding. A yard that impounds the
  hull is the missing half of an economy that already has wharfage, tolls,
  levies, admin overheads and payroll.
- **Two purchasable favours buy nothing.** `Favour("berth")` and
  `Favour("warning")` cost regard and are read by no code; `clearance.py`
  never asks `officials`.
- **`grudge.hostile_open` is dead** — the game's own definition of "this
  power shoots you on sight", called only from a test.
- **The embargo venture inspects nobody**, though its prose says it is
  "inspecting anything that smells of" a rival's cargo and `sim/customs.py`
  already has the machinery.
- **Patrols are furniture** — `hostile=False`, parked at the quay body,
  never intercepting, while `piracy.lawlessness` gives them the largest term
  in its model and the only moment that model can bite is the jump exit.
- **`engage.may_engage` has no political gate.** You may open fire inside a
  capital's approaches; the ladder only escalates on unauthorised *closing*.
- **The censure venture is the game's only trial and the player cannot
  testify.** A censure aimed at the player, assembled from the memories
  `grudge.because()` already names by date, would be a tribunal built almost
  entirely out of parts that exist.
