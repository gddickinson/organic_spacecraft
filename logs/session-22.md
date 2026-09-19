# Session log, part 22 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

## 2026-07-28 — SEEDFALL: closing the crash class, and catching a signal

Last cycle a player segfaulted the game on a drop-down and I fixed the two
call sites that were missing a `defer`. That was the third time this rule has
cost a crash — a `Card`, a `QLineEdit` mid-keystroke, now a `QComboBox` — and
the third time the fix was one call site at a time, after a player found it.

- **The class is closed at the root.** `View.refresh` freed the old widgets
  synchronously, which is what let any handler destroy its own emitter. The
  outgoing widgets are now parked on the view and released on the next turn of
  the event loop, so whatever emitted outlives the event it emitted during
  whether or not the call site deferred. Measured no leak: 220 rebuilds, zero
  widgets still held.
- **A flaw in my own fix, caught by thinking about it rather than by a test.**
  Parking by assignment meant two rebuilds inside one event would drop the
  first batch synchronously — the same bug in a rarer hat. It extends now.
- **The suite can catch a segfault instead of being killed by one.** Every
  driver here chooses from a combo with `setCurrentIndex` or by emitting
  `activated`; neither opens a popup, and the crash lives entirely inside
  `QComboBoxPrivateContainer::eventFilter`. That is why five hundred checks
  missed it. `tests/popup_probe.py` sends real mouse events to the popup's
  viewport and runs out of process, so the failure mode is an exit code.
  Backing the fix out reports **exit -11**, which is the player's crash,
  reproduced.
- **The invariant, stated precisely.** The combo must be alive *at the instant
  Qt returns from delivering the click* — not afterwards. My first probe
  asserted aliveness after four `processEvents` and read False for a
  completely legitimate reason: the deferred rebuild had long since run. A
  check measuring the wrong moment would have condemned correct code.
- 526 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: somebody behind the counter, and a segfault from a combo box

**A crash first.** A player segfaulted the game choosing from a drop-down. The
stack named it exactly: `QComboBoxPrivateContainer::eventFilter` — the popup
was still delivering the mouse release that dismissed it when the handler
called `refresh()` and freed the combo underneath it. `widgets.defer` exists
for precisely this and `options_view` already used it; `diplomacy_view` and
`yard_view` did not. Both defer now.

525 checks had missed it because the driver sets `currentIndex`
programmatically, which never opens a popup and never takes that path. So the
new check tests the *invariant* rather than the path: **after emitting its own
signal, a control must still exist.** Writing it walked straight into the bug
under test — collecting the combos once and firing each in turn meant the
first deferred rebuild freed the rest, and the check itself died of a
use-after-delete. A fresh window per combo, the pattern `drive()` already used.

**And the cycle's feature: harbourmasters.** A quay was a bag of services with
nobody in it, while `memory.py` had supported a `port` mind since the day it
was written and never had one attached.

- **Derived identity, stored relationship.** Name, temper and the lever that
  could exist are seeded from the port; regard, memories, levers found and
  favours running live on the mind that persists.
- **Trading has a ceiling.** Squareness makes somebody helpful and stops. Past
  that you need what they want or what they fear — which is the whole point,
  because a relationship you can grind is not politics.
- **Leaning is a different transaction, not a cheaper one.** The first cut had
  it cheaper *and* unconditional, which made the lever strictly better than
  the relationship and deleted the decision. It now costs 1.6× asking, spends
  the lever, and permanently lowers the ceiling: 300 dealings afterwards reach
  36 where somebody who never leant reaches 48.
- **Every favour is read somewhere** — a search skipped, a board of 5 → 7 with
  better work on it, goods 12% inside the posted price. Checked against the
  systems they change rather than asserted.
- **A stranger read as "cold"** because `START_REGARD` sat inside the cold
  band. Somebody you have never met is not hostile; they are doing their job.
- **The `office` state was invisible to the save codec** — an attribute hung
  on a dataclass at runtime rather than a field, so every harbourmaster forgot
  you, your levers and your favours on reload. Found by the check, not by
  reading.
- **A tautological check of my own**, again: it asserted
  `after_cap == before_cap - CAP_PER_LEAN`, reading the very constant whose
  effect it claimed to test, and passed with that constant zeroed. Rewritten
  to compare two measured outcomes.
- Being boarded now costs you with the person who signed the order, not only
  with the power.
- 525 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the powers stop being a vending machine

Diplomacy was the top standing priority and I had spent three cycles on
piloting and combat, so: the board.

It ran one way. Six actions, all player→faction — send a tribute, share
intelligence, propose a treaty — and the four powers did exactly one thing
between them, `drift`, pulling their grievances back toward a baseline. You
put standing in and took tariffs out. Nobody ever knocked.

- **An approach has to be caused.** A power asks for silicon because its quays
  are short of silicon; it asks you to denounce the Freeholds because it is
  losing to the Freeholds; it warns you off a rival whose cargo you have been
  carrying; it offers terms because your standing passed 62; it levies ground
  you hold inside its space. The die only decides *when*, among reasons that
  already exist — pinned by a check that plays four hundred months with every
  trigger dead and demands zero envoys.
- **Three answers, all costed first**, and letting the window lapse costs
  exactly what refusing costs. An offer with a free deadline is a button that
  waits forever, not a decision.
- **Two bugs in my own new code, both the same shape as the ones this project
  keeps finding elsewhere.** `_shortage` read a `demand` mapping that `Market`
  does not have — it has `stock` — so `getattr(..., {})` returned empty every
  time and **requisitions could never fire at all**. Fixed, it then reported
  every power short of `wildseed`, which nothing stocks and no captain hauls:
  a shortage real in the data and meaningless as a request. Now restricted to
  tradeable goods actually in your hold, which is also what the flavour claims.
- **A dead wire I nearly shipped.** The clock hook was written against an
  eight-space indent, but `advance_days` had been dedented into `core/clock.py`
  two cycles ago, so the replacement silently did not apply. Measured before
  believing: eighty chronicle-years, zero approaches. With it wired, about
  eight per decade — one every fifteen months, which is a thing that happens
  to you rather than a weekly appointment.
- **Two of my mutation tests were inadequate rather than the checks weak.**
  Removing the "they are not talking to you" guard did not produce an uncaused
  envoy, because every other reason still required real state; and setting the
  quoted price to a constant kept preview and payment consistent, which is
  what the check actually verifies. Broken properly — reasons invented from
  nothing, and a payment 20% short of the quote — both bite.
- Ten years driven through the real window: 34 approaches, navigation held on
  every one, all answered by real button clicks.
- 514 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the plot finally shows what bears

The other half of #56. The tactical plot drew range rings and two triangles,
and never drew the one thing the whole geometry exists for.

- **Everything was already modelled and none of it shown.** The arc, the
  bearing, the range band, the magazine — all knowable before the turn, all
  reaching the player only afterwards as a log line saying the shot they had
  just spent a turn on did not happen.
- **`sim/firing.py` answers per mount, first**: bears or not, and if not
  exactly how far the bow must come round or how many bands to close. The plot
  draws one wedge per *arc* — one per mount stacked five identical broadsides
  on top of each other — lit when something in it bears, with the enemy's arcs
  faint, because sitting in a forward arc is a decision.
- **Three opinions about whether a gun can fire.** `combat._fire` refuses
  above 0.6; every selector picks only 0.5; `assessment.mounts` called
  anything above 0.5 out of range. **In practice the gap is empty** —
  `bears_at` steps 0.22 a band, so the reachable penalties are 0, 0.22, 0.44,
  0.66 and nothing lands between. A landmine, not a live bug, and saying
  otherwise would have been a better story than the true one. Both constants
  are named now, `assessment` delegates, and a check holds the gap shut.
- **The fire buttons tested range and nothing else.** A mount sixty degrees
  off the beam or with an empty magazine was offered, taken, and spent the
  turn on a log line explaining why it had not fired.
- **Two panels saying the same thing.** `assessment_panel` already listed
  mounts and bearings; the new picture supersedes it with the band, the
  magazine and the enemy's arcs, so the duplicate came out rather than being
  left to disagree.
- **Three of my own checks were wrong, in three different ways**, and only
  trying to break them showed it:
  - the closing-rate check excused `|rate| < 1` as agreement, which forgives
    precisely the failure of always returning zero — and once fixed it failed
    against the real code, because the rate is instantaneous and the hulls
    steer before advancing. The honest fix was to test it against its own
    definition and document what it is;
  - the assessment check compared one band, where "bears" and "worth firing"
    coincide, and passed with the two rules forked wide open. It sweeps every
    band now, and the fit carries a `lixiviant` on purpose so a mount can be
    in arc and genuinely unusable;
  - the marginal-mount check asserted a state the game cannot reach, which is
    how the landmine was discovered.
- `combat.py` crossed 500 lines, so a hit and its narration moved to
  `sim/damage.py`; the plot moved to `ui/tactical_plot.py`.
- 505 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the seats you leave stop being stupid

Task #56, the half about automatic piloting and battle systems. The gap turned
out to be sharper than "add an autopilot":

    if not directed:
        order_id = side.helm_order or "hold"     # repeat, forever

An unattended helm repeated your last order until you came back to it, and an
unattended gunner salvoed every turn whatever the heat and whatever bore. Order
*close* and walk to gunnery, and the helm flies you down the enemy's throat for
the rest of the engagement. That is a punishment for looking away, not a
decision about where to spend attention.

- **A battle computer chooses.** `sim/doctrine.py` reads band, aspect, heat,
  hull and what bears, and picks an order for every seat nobody is in.
- **It says so first.** The battle screen names the order and the reasoning
  before the turn resolves — a system that acts on your behalf without stating
  its intent is this project's signature defect wearing a uniform.
- **It is not free and not better than you.** `doctrine` comes off the compute
  fitting, 0.15 for the core you launch with to 1.00 for a Cold Ledger, and
  below 0.30 there is no computer at all — so the hull you start with behaves
  exactly as it always did, which is what the other 490 checks assume. A seat
  run by the machine works at the officer's rate: measured, it vents 90% of
  what you vent sitting in it. Measured effect over 24 fights: 12.1% of the
  enemy hull removed with no computer, 16.9% with an excellent one.
- **A bug that gave confident bad advice.** `_bearing_count` read
  `side.weapons`; the mounts hang off `side.st.weapons`. It returned an empty
  list every time, so every count was zero, gunnery always concluded "nothing
  bears", and the helm came about forever chasing an arc it was already in.
  Nothing raised. It simply advised badly, with complete confidence — the
  worst failure mode an advisory system has.
- **Doctrine was coupled to a Battle it never had.** The first cut took the
  range band off `battle.range_units`, but `run_helm` is handed two sides and
  nothing else. The two bodies already know how far apart they are.
- **A check that demanded variety where correctness implies constancy.** My
  first version asserted the computer's helm order *changed* over a fight — but
  a hull already in its preferred band should say "hold" every turn and be
  right to. It was failing the computer for being correct. Rewritten to the
  actual claim: does it *depart from what it was last told*, and does it adapt
  across situations rather than parroting one answer? 10/10 engagements depart.
- 498 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: the sector stops being empty, and the chart starts predicting

Follow-on from the helm complaint. Quays got positions last cycle; ships had
none at all — encounters were rolled the instant you arrived and thrown away,
consorts followed you implicitly, ventures were a number in a ledger.

- **Traffic has somewhere to be.** A handful of hulls per system — traders,
  patrols, prospectors, couriers and the occasional unmarked hull — each with
  a name, a faction, an errand and a position that moves along its leg with
  the clock. Busyness follows the port: a capital works five, unclaimed space
  one, a bloomed system fewer than either, because the traffic left.
- **Derived, not stored**, like anchorages. Persistent identity with no
  migration, at the price that derivation must never touch `game.rng()` —
  that advances with the save, so a reload would hand you a different sector.
- **The chart predicts now, which is the whole point.** `roll_encounter`
  weighs who is actually present, so the hull that turns onto you is one you
  could have plotted first, by name. Measured: 18% of arrivals contested where
  something runs dark against 6% where nothing does — same system, same day.
- **Two hulls with the same name.** The pools hold four or five names each and
  a capital works five hulls, so the chart showed *Long Consent* twice — which
  makes "the hull you plotted" meaningless exactly when it starts to matter.
- **`position()` defaulted to the wrong system.** It fell back to
  `game.system`, so asking about traffic anywhere else indexed one system's
  body list with another's indices and raised `IndexError` — on the very call
  `hostiles()` makes to sort. A hull carries its own system id now.
- **Labels piled into a smear** where traffic converges on the quay. A hull is
  named on the chart only where there is room; the panel names them all.
- **Three of my own checks were weaker than they read**, and only trying to
  break them showed it:
  - "what is on the chart is what stops you" verified a linked id and nothing
    else — it passed with the name assignment deleted. It now asserts the ship
    you meet *is* the hull you plotted.
  - "running dark makes a system more dangerous" measured a **confound**:
    unmarked hulls appear in portless and bloomed systems, which were already
    the dangerous ones, so it passed with my contribution set to zero.
    Rewritten to hold the system fixed and vary only the traffic.
  - "hulls move" looked at one system whose hulls all held station, measured
    nothing, and passed. It scans fourteen systems now.
  - And one mutation of mine was inadequate rather than the check being wrong:
    running dark has two effects and zeroing the danger term left the
    guaranteed-encounter path, so the check was right to survive it.
- `HULL_NAMES` moved from `sim/encounters.py` to `data/lore.py` — encounters
  asks traffic who is present, so traffic cannot import encounters.
- 491 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: a quay is a place, not a screen you switch to

A player at the helm: *"the map only shows the sun and planets. What about
other known ships or stations, the fleet hub and other shipyards? I think the
game starts at a shipyard but it is hard to tell... How would I navigate back
to a shipyard if it is not on the map?"*

They were right, and the reason was worse than a missing marker.

- **A `Port` had no position at all.** No body, no orbit, no coordinates — it
  hung off a `System` as a bag of services. The quay you were standing on was
  nowhere in space, and docking was a screen you switched to from the chart.
  So the one view you actually fly from could not show you the one place you
  most need to fly back to. That is why nothing was drawn: there was nothing
  to draw.
- **An anchorage is now anchored to a body**, so it inherits a real orbit that
  moves with the clock — and every intercept, burn profile and transfer quote
  works on it unchanged, because flying to a quay *is* flying to the body it
  orbits. No special case anywhere in `sim/flight`.
- **Derived, never stored**, like `ship.stats()`. One source of truth, no save
  migration, and no way for a stored quay to disagree with its port.
- **The helm answers the question now.** Quays, capitals and your own holdings
  are drawn and labelled; the header says *"In orbit of Loam Span I, alongside
  Fleet Hub"* rather than a bare body name; and a panel lists everywhere you
  can put in with a course and a fuel bill. `offering(game, "shipyard")` is
  the literal answer to "how do I get back to a shipyard".
- **The confusion was real and measurable.** A fresh chronicle starts in a
  system *with* a Fleet Hub but 4.26 AU off it, not at it — which is exactly
  why the player could not tell whether they had started at a shipyard.
- **Two layout defects caught by rendering it.** Three columns fitted a wide
  desktop and silently dropped the third at any ordinary window size, so the
  new panel was invisible at 1400px; it is stacked under the chart now. And
  the sector chart named a port without saying what it offers, which makes
  "which of these has a yard" unanswerable.
- **A tautological check, caught by trying to break it.** The stability check
  passed with the anchor deliberately broken, because my mutation was still
  deterministic — the property could not fail given the function's signature.
  Rewritten to something that genuinely can: the berth must survive time, RNG
  draws *and* a save/reload, which is the real risk for derived state. It now
  fails against a truly wandering anchor.
- **Not done, and not pretended:** known hulls are still not plotted. Nothing
  in the game gives another ship a persistent position, so that is a separate
  piece of work rather than a marker.
- 484 checks green, every file under 500 lines.

## 2026-07-28 — SEEDFALL: two clocks, and four kinds of person to feel them

The player asked for time to matter — ageing over long crossings, hibernation,
lifespans, and different needs for wet crew, cyborgs and synthetics — then
added the thing that reframes it: *"Don't forget that time is relative."*

- **A lineage is a substrate.** Everyone aboard used to be the same thing:
  immortal, breathing, eating nothing. Four lineages now, differing in span
  (96 to 900 years), ageing rate (1.00× to 0.07×), what they consume, and
  whether the atmosphere plant matters to them at all.
- **The Choir stops suffocating.** The opening screen sells a Dry Choir
  lineage on "no air to run out of", and the daily tick killed recordings by
  asphyxiation on exactly the same schedule as a wet crew. The purest form of
  the defect this project keeps finding: a screen promising a consequence the
  simulation never read. A wet crew now dies in 120 airless days; a Choir crew
  does not notice.
- **Two clocks.** `Game.day` is the Verge's and drives every deadline, market,
  colony and faction. `Game.ship_day` is proper time and drives ageing,
  upkeep, repair, refining, wages and the research bench. `advance_days(n,
  dilation)` writes both. The split is what stops a hard burn being free: at
  dilation 6 a year of clock ages the crew 0.14 years instead of 1.0 and eats
  a sixth of the food — and banks 320 fewer research points.
- **Four ways to fly a crossing**, from a long coast (1.55× days, 0.45× fuel,
  clocks agree) to a relativistic run (11× dilation, 5× fuel). The map states
  all four costs before you commit: days out here, days lived aboard, reaction
  mass, what the crew eats and what it does to their span.
- **Provisioning follows the crew.** A hull launches with 220 days of what
  *its own* lineage eats, so a Choir captain is not punished on day one for a
  choice made on the character screen.
- **Two promises I broke and fixed.** Provisioning by lineage made the opening
  screen's forecast wrong twice — first the biomass (the screen quoted the
  chassis's fifty berths against the thirty-four that actually sail; `crew =
  34` was a bare literal inside `new_game` that the screen had no way to read)
  and then the alloy (routing `new_game` through the same helper double-counted
  the origin's stores, which `apply` already adds). Both are now one function
  with one caller each, which is the only durable fix for that class.
- **A ten-minute hang, from my own new control.** The suite stopped dead on
  `system/'Close pass'` against a wrecked hull: the survey flies seventeen days,
  the crew dies, the ending dialog returns nothing, and the fall-through starts
  a *new* chronicle — which opens the opening dialog and waits forever for an
  answer nobody was going to give. `interact.py` had already learned this from
  the shipyard's name prompt; `test_verbs` now neutralises modals too.
- **A dead promise, wired up.** Three colony classes advertise sensor reach and
  `colony.effects` had tallied it per system since the day they were written —
  nothing ever read the tally. Surveys gave the number teeth, so a relay node
  now doubles what you can sweep from where you are.
- **My own measurement errors, twice.** A check that overrode `ship_stats` and
  another that overrode `colony_fx`: both are *derived*, both are rebuilt by
  `recompute`, and both threw the override away mid-check — so the check
  measured a sharp instrument for the forecast and a blunt one for the survey,
  then blamed the forecast. And an airless-crew check that advanced 120 days in
  one call, letting `repair_tick` heal the life layer so the air came back.
- All four new time checks proven to bite by reintroducing the bug. 477 checks
  green. `core/state.py` crossed 500 lines the day time stopped being uniform,
  so the daily tick moved to `core/clock.py`.

## 2026-07-28 — SEEDFALL: four ways to look at a world, and three that never paid

Answering a question from the player: *"how are surveys carried out? They seem
to have no cost and are all the same."* They were. One button, three days, no
cost, no risk, and the same kind of answer for a comet as for an ocean world —
while thirteen sensor fittings and a drone technology existed only to nudge a
single `scan` float.

- **Four methods, deliberately not a ladder.** A long-range sweep is not a worse
  close pass; it is a different question. It costs no travel and no stores, and
  it cannot see anything that moves or anything buried. A probe swarm goes where
  the hull will not, needs `dronework` and eats silicon and alloy every time. A
  deep survey is the only thing that reliably finds a buried site, and it wants
  nine days, reaction mass for the charges and a real sensor suite. Each names
  what it `finds`, and `world/planets.survey_body` is filtered by that list, so
  a method that says it cannot see lifeforms genuinely cannot.
- **The panel states the whole bill before you commit** — days, stores, what it
  will find and, the part that makes it a decision, *what it will be blind to.*
- **A forecast that lied by nine days.** `flight.ensure_at` quietly drops to a
  coast when there is not enough reaction mass for a standard burn, and a coast
  is slower. The preview always quoted the standard burn, so on a dry tank it
  promised seven days for a trip that took sixteen. Fixed by forecasting the
  profile that will actually be used.
- **A bill that hid most of itself.** The deep survey quoted four tonnes of
  charges and spent seven: flying the hull alongside burns reaction mass on top,
  and the card never mentioned it. `full_cost()` now folds the flight in.
- **Three colony works that paid nothing.** Vigil viva, a CHORUS node and a
  reactivated array all advertise sensor reach, and `colony.effects` has tallied
  it per system since the day they were written — and *nothing ever read the
  tally.* `stats()` also dropped any `sensor` bonus on the floor, summing only
  fittings. Both were invisible because until surveys the number decided
  nothing; now it gates the free method. A relay node takes reach from 4.00 to
  8.00 AU. It stays per-system rather than folded into `ship_stats`: a dish
  spread across one system should not help you three jumps away.
- **Two of my own measurement errors, caught before they became findings.**
  I "fixed" a forecast mismatch that was really my check poking `ship_stats`,
  which `advance_days` rebuilds from the hull and throws away — the check
  measured a sharp instrument for the forecast and a blunt one for the survey,
  then blamed the forecast. Same lesson a second time with `colony_fx`. Derived
  state cannot be overridden by a test that moves the clock; the fixture now
  goes through real inputs and plants a real colony.
- **Proving the checks bite.** Reintroduced all four bugs. Three failed
  immediately; the coast-forecast one **passed**, because the fixture always had
  fuel for a standard burn — so the fix was unproven and the path untested.
  Added a dry-tank case: it now fails with "said 7 days, took 16".
- 466 checks green, every file under 500 lines. `system_view.py` had crossed the
  limit at 505, so the survey report moved to `ui/survey_panel.py`, where it
  belonged anyway.

## 2026-07-28 — SEEDFALL: playing by pressing, and a helm warning that said nothing

- **Measured the gap first.** A six-year chronicle makes **zero** fractional
  day advances, which is why nothing in the suite could reach the crash a
  player hit in four minutes. The chronicle plays by calling `sim` with the
  ship already in place; a player presses *Open cut*, and the handler flies
  the ship first. `tests/interact.py` plays by pressing instead — 132 presses
  of 107 distinct controls over 651 days in the committed check.
- **Two things had to be neutralised before a session could run at all.**
  `QDialog.exec` blocks, and so does `QInputDialog.getText`, which is static
  and does not go through it — the shipyard uses it to ask a hull's name, and
  a session that pressed *Lay down* hung for ten minutes waiting.
- **A player found the helm lying.** Every body in the system reported "you
  will be working 0.40 AU from the star", including one nine AU out. The note
  took the *minimum* of the ship's distance and the target's, so a hull parked
  close in reported its own position whatever you clicked. It is the
  destination's distance now, and a check requires the notes across a system
  to tell the destinations apart.
- **A watcher saw a pop-up, not the game.** `--new --bridge` ran the opening
  briefing, which is modal; the bridge's queued commands executed *behind* it,
  so the game was played invisibly. `--bridge` skips the modal opening now,
  and `blocked`/`dismiss` let a caller see and clear anything in the way.
- **Said plainly**: the session driver does *not* reproduce the fractional-day
  path, and I could not find which caller produces one — five seeds give no
  fractional flight quote. The calendar check pins the behaviour directly
  instead, which is the honest guard.
- Suites: 55 — 458 checks green. 239 modules, all under 500 lines.
