# Session log, part 23 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span 2026-07-28 to 2026-07-28; undated entries keep their original place.

## 2026-07-28 — SEEDFALL: driving the real window, and the clock it broke

- **Asked to play the game through its GUI as a watched systems test.** The
  bridge existed but held its own headless game, which is useless for
  watching. `bridge/attached.py` puts the same protocol in front of the
  *running* `MainWindow`, with `python -m seedfall --bridge`, and adds the
  verbs a watcher needs — `go`, `tab`, `screen`, `shot`.
- **What makes it safe is marshalling.** The socket runs on its own thread and
  the whole interface reads the `Game` from Qt's; mutating from one while the
  other paints is a data race. Every command is posted to the Qt event loop
  and the socket thread waits for the answer.
- **The test found a live crash within four minutes.** Putting the rig on a
  body killed the heading bar: `stardate` formats the day with `:03d`, and
  `advance_days` — annotated `n: int` and never coercing — had let a
  fractional transit turn `game.day` into a float. Everything downstream
  assumes whole days. The clock now carries the fraction rather than dropping
  it, with an epsilon, because a hundred tenth-days sum to 9.999999999999998
  and would otherwise lose a day every ten.
- **Two more, from reading what the game said aloud.** The ship's computer
  reported "before any of this, *they* were refused a berth" — a captain's
  backstory, because the bridge verb could not say what kind of thing was
  speaking. And the harbourmaster introduced himself as "Harbourmaster Vell,
  harbourmaster", a frame prefixing a title onto a name that already had one.
  Both pinned: every speaker must draw on its own kind of past, and no persona
  may say its own title twice in a greeting.
- The rest of the tour was clean: twelve screens, every tab, survey, trade,
  mine, jump, sixty days of clock, diplomacy, the 3D plans, and a voice.
- Suites: 55 — 456 checks green. 238 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: the rest of the controls, and a second segfault

- **Generalised last cycle's crash rather than waiting for the next one.** A
  player hit an abort clicking a card, and the reason it survived 450 checks
  was that `test_verbs` drives `QPushButton`s — which Qt emits safely after the
  press — and nothing else. So I counted what else a player can touch: 135
  buttons and 98 cards covered, and **14 line edits, 13 spin boxes and 5 combo
  boxes that nothing had ever driven**.
- **The first one I drove segfaulted the process.** Typing a single character
  into the manual's search field killed the game — signal 11, not a catchable
  exception. `textChanged` fires *during* the keystroke, the handler rebuilt
  the view, `View.refresh` freed the field being typed into, and Qt returned
  into it. Two more connections on the options page had the same hazard.
- The rule now lives in one place: `widgets.defer()` runs a handler after the
  current event has finished being delivered, and `View.refresh_later()` uses
  it. Anything that rebuilds the widget which emitted the signal goes through
  it.
- **Fixing the crash was not enough to make the field work.** Deferred, it
  stopped dying and still accepted only one character, because the rebuild
  replaced the box and focus went nowhere. It restores focus and the cursor
  now — and the check types a whole word one key at a time into whatever holds
  focus, which is the only way to notice.
- Verified by putting each fault back: the card crash fails its check, and the
  search segfault takes the whole suite down with exit 139, which the "only
  commit if green" rule catches.
- `test_verbs` crossed 500 lines; the non-button controls moved to
  `test_controls.py`, driven from the same offscreen app.
- Suites: 55 — 453 checks green. 237 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a fight with one outcome, and a crash on every card

- **The task list was clear, so I went looking by playing.** The chronicle
  suite claimed to do everything and had never fired a shot: encounters were
  rolled on arrival and thrown away. Wiring combat into it produced thirty
  engagements in a decade — and every single one ended the same way.
- **Combat had exactly one outcome.** Measured over 360 engagements with the
  test captain: 100% "driven-off", both hulls at 100%, median 34 turns. No
  kills, no routs, no parleys, no damage at all.
- The cause was one rule with two implementations. `_fire` floors damage at
  `max(dmg * 0.15, dmg - armour)` — the comment says "something always gets
  through, or two well-armoured hulls would shoot at each other until the sun
  went out" — and `_apply_to_layers` then ran `while left > 0.5`, discarding
  anything smaller. For a three-damage weapon the floor is 0.45, so it was
  swallowed entirely: **the Photic Flash Organ, the only armament a new
  captain starts with, dealt exactly nothing to any armoured hull**, forever,
  while the log said "hits for 0" and the read panel correctly reported 0.45 a
  turn. The honest number was on screen; the ledger delivered none of it.
- Fixed the guard to an epsilon, and stopped the bridge reporting a landed hit
  as zero — thirty turns of "hits for 0" reads exactly like a broken weapon.
  A check now compares what the read panel says a shot lands against what the
  guns actually deliver.
- **Then a player hit a hard crash and sent it.** Clicking any card — a body on
  the System screen, a node on Research — aborted the process:
  `Card.mousePressEvent` emitted `clicked` inline, the handler rebuilt the
  screen, `View.refresh` unparented the old widgets and freed them, and the
  next statement called `super().mousePressEvent(ev)` on a deleted object.
  The emit is deferred by one turn of the event loop now.
- **Why nothing caught it**: `test_verbs` drives every `QPushButton` on every
  screen, and Qt emits those safely after the press completes. Cards have a
  hand-written `mousePressEvent`, and nothing had ever clicked one. There is a
  check that does now, and it fails when the inline emit is put back.
- Suites: 55 — 451 checks green. 236 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: costing the way out of a pocket

- **Task #44, and the measurement changed what I built.** A quarter of sectors
  open with fewer than eight of 42 systems reachable and one in eight with
  three or fewer, which looked like a generation defect. Before touching
  generation I played a two-system pocket for twenty-five years: evidence still
  accumulates in the hundreds, both its markets sell magnetite, the whole
  fourteen-technology chain to the Foldrunner is open from inside, and one
  pocket earned 71,000 of the 78,000 credits needed in under seven years.
  **The wall is a gate, not a lock.** Changing generation would have been
  fixing the wrong thing.
- **The actual defect was the project's signature one**: the chart named a way
  out — "a Foldrunner Coil would open 40 more, once researched" — and stopped
  there, which is the same shape as a contract fee with no cargo cost beside
  it. Measured, that way out is twelve technologies, 4,990 research points,
  78,000 credits and 20 tonnes of magnetite. A project, not a purchase.
- `reach.plan()` costs it and the chart prints it: what is still to research
  and for how many points, the credits and how far short you are, and **each
  material with the reachable ports that stock it** — because whether the
  pocket can supply its own way out is the thing that decides whether you are
  working toward something or waiting for nothing.
- The check that carries the finding asks it continuously rather than once: 24
  walled sectors, the smallest two systems, every one able to supply its own
  exit. Making one material unobtainable fails it, so if generation ever
  produces a real trap the decision not to change generation gets revisited.
- Suites: 54 — 445 checks green. 235 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: grudges that cost something, and can say why

- **Task #53, and the loop's stated first priority.** Memory existed but only
  coloured what an envoy said. Measured before starting: a decade of play left
  exactly *one* mind holding anything — the Charter, from contracts — so
  grudges would have been dead content for three powers out of four.
- `sim/grudge.py` turns memory into behaviour. A quay **prices you by what it
  remembers** (bounded at 18% either way, so memory is felt without replacing
  the market); a power that holds enough against you **stops posting work**,
  which is a harder wall than a poor price; and feeling **travels** between
  powers close on the relations matrix, which is what makes that matrix
  something to think about rather than a readout.
- The rule that keeps it honest: `because()` names the memories responsible for
  whatever `feeling()` returns, with dates, and the diplomacy screen prints
  them. Nothing in this game may dislike you for a reason it cannot state.
- **Widened what writes memory**, which is what made the feature reach real
  play: every overture, a denunciation (which lands on the power denounced),
  and each of the three answers to a territorial demand. A played decade now
  leaves all four powers holding specific, dated, legible reasons.
- **A defect I created and the suite caught the same run**: `contracts.
  cargo_cost` priced the board's quote with the raw `buy_price` while the till
  went through the new helper — nearly nine hundred credits apart on one
  cargo. Both read `market.quote_buy` now.
- **A defect found by playing rather than by checking**: brokering the same
  pair eight times wrote eight identical memories and pinned the power at the
  +100 cap, so the readout could not say which of them mattered. Repeating
  something now reinforces one memory with diminishing returns and moves its
  date forward, which is both truer and legible: "you sat us down with
  Concordat +37.7 · relief +31.0 · tribute +25.9".
- An efficacy lever switches the price bias off; the harness reports it inert
  when it is.
- Suites: 54 — 442 checks green. 235 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a tutorial that will not take your word for it

- **Asked for an optional tutorial at the start.** Eight lessons — survey
  something, look at a market, sell what you learned, buy reaction mass, go
  somewhere, take on work, look at what you are flying, see who is who — shown
  as a strip along the top rather than as dialogs.
- **The design point is that it watches rather than trusts.** A step that
  advances because Next was pressed teaches nobody anything and will march a
  confused player through eight screens of congratulation. So every lesson
  names a watcher, and every watcher is a function of game state compared
  against a **mark taken when the lesson opened** — "survey a body" means one
  more than you had, not "a body is surveyed", so a captain who surveyed
  something before starting is not waved through.
- **It never blocks anything.** The window's guard diverts for a battle, an
  open trench and an aftermath question; the tutorial is deliberately not among
  them, in a game whose premise is that there is no track. A check walks all
  twelve screens with a lesson open.
- It lives on the `Game` with an `.over` flag like everything else you can be
  part-way through, so it survives a save — including mid-explanation, which a
  check reloads and carries on from. Skipping is final until it is started
  again from the Help screen, and the `tutorial` option is back on the options
  page now that something reads it.
- **Three of my own errors, caught by the checks rather than shipped**: a
  fixture that added cargo and then sold it, so the hold returned to the mark
  and the watcher correctly saw nothing; a starting system with only two
  bodies, which the survey fixture assumed away; and a "does it block
  navigation" check that read `go()` for the word "tutorial" and tripped over
  the import line — it walks the screens now.
- Found by looking: `deleteLater()` alone leaves the previous lesson's text
  painted under the new one until the event loop catches up.
- Suites: 53 — 432 checks green. 233 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a menu bar, and options you can actually set

- **Asked for an options page reachable from a menu bar, including the LLM
  choices.** There was no menu bar at all — the theme had styled `QMenuBar`
  since the beginning and nothing ever built one.
- `ui/menubar.py` builds it from the same tables as everything else: screens
  and their keys from `data/screens.py`, instruments from `monitors.SHAPES`, so
  a screen or an instrument added tomorrow appears without anybody editing a
  list. Four menus — Chronicle (save, options, begin again, quit), Screens,
  Instruments, Help.
- `ui/options_view.py` is **one** options page, shown either in its own window
  from the menu or embedded in the Help screen. Two options pages is two places
  for the bounds to disagree.
- **The LLM is settable from the game now, not only from the environment.**
  `core/llm.py` gained `configure()`; the player picks the provider from what
  is on the machine and names a model, and `options.apply()` pushes it down. A
  fresh process still starts off and no check ever turns it on. The page probes
  only when you press *Look for models*, and *Say something* prints a line so
  "a model is answering" is a claim you can check.
- **A live bug, mine, from last cycle.** Three call sites used `win.save()` and
  `MainWindow` had no such method: carrying on past an ending, answering an
  aftermath situation, and changing a setting. Every one raised inside a Qt
  slot, where it is swallowed. The aftermath checks drove `sim/legacy.py`
  directly and never pressed the button. There is now a check that answers a
  situation *through the view*, and one that fires all 25 menu actions with
  `sys.excepthook` armed. Both fail when `save()` is removed.
- **A second, subtler one, found by the suite after splitting `window.py`:**
  `credits` is a Python builtin. Calling it by mistake does not raise
  `NameError` — it calls the interpreter's `_Printer` and fails two suites
  away with a message about positional arguments.
- `window.py` crossed 500 lines; the heading bar moved to `ui/hud.py`.
- **My own check was wrong first**: "every option does something" scanned for
  the setting's name elsewhere in the package, which cannot see a setting that
  `options.apply()` *forwards* into `core/llm.py`. It reported two live
  settings as dead. It now moves each unnamed setting and watches for an
  observable change.
- Suites: 52 — 424 checks green. 229 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a manual that cannot go stale, and options that bite

- **Asked for an extensive help system and an options screen.** Nineteen
  topics ordered the way a captain meets them, a search, contextual help from
  every screen, a Keys page, and five settings.
- **The manual counts rather than restates.** A page that says "thirty-five
  hulls" is wrong the day somebody adds one and nothing would notice, so
  `data/help.py` holds prose and `sim/manual.py` generates every countable
  claim from the table it describes — the ten endings and the epoch each opens,
  the burn profiles with this hull's heat, what this sector can actually reach,
  the powers and how each regards you now. A check fails if a topic names a
  fact nothing can resolve, and it caught a dangling cross-reference (`trade`
  pointed at a `customs` topic that did not exist — smuggling has its own page
  now).
- **Every option does something, and the screen says so.** `sim/options.py`
  holds the settings and their bounds; a check reads the whole package and
  fails if a setting is not consumed outside the module that defines it. That
  discipline cost two entries: a tutorial toggle and a seen-endings list, both
  taken off the screen until the thing they configure exists. Model speech
  needs *two* switches — the machine's and the player's — and the panel names
  which one is missing rather than offering a toggle that silently fails.
- **A real defect, found while documenting it.** The rail derived shortcuts as
  "1–9, then 0 for the rest", so when an eleventh screen was added the Codex
  and the Aftermath both bound `0` and the Aftermath had no key at all. Keys
  now live in `data/screens.py`, read by the window and by `sim/manual.py` —
  which is across the layer rule, so the Keys page is built from the same table
  as the rail.
- Also found by looking: generated facts can be any length, and an unwrapped
  label forces a minimum width wider than the view, which pushed the whole
  manual off the right edge.
- Suites: 52 — 420 checks green. 226 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: a bridge, so the game can be driven from outside

- **Asked for a way to drive the game remotely, for a chatbot to play
  characters, and as a route to multiplayer with autonomous seats.** `bridge/`
  is that: seventeen verbs over a running `Game`, a loopback JSON-lines
  transport, and a seat mechanism.
- **The protocol is separate from the transport on purpose.** Verbs are plain
  functions over a `Game` with no Qt and no socket, so the suite drives all of
  them in-process and the transport is a detail that could be swapped. No verb
  reimplements anything: each calls the same `sim/` function the window does.
- **Local only.** It binds 127.0.0.1, mints a token per session, and refuses
  anything untokenised. No discovery, no broadcast, nothing routable.
- A **seat** is a named role an outside caller speaks for — how a second
  captain joins and how an agent holds a rival. Claiming one is a declaration
  rather than a lock, which is what makes somebody stepping away survivable.
- **The bug it shipped with, found over a real socket.** `survey` returns a
  `Lifeform` object among its results; the reply was merged straight into the
  envelope and `json.dumps` raised *inside the connection thread*. The socket
  died silently and the caller read an empty line with nothing to go on. Fixed
  by making the boundary total — `plain()` flattens anything, the writer never
  lets a bad reply kill a connection, and a check hands the dispatcher eleven
  kinds of rubbish and requires a polite answer to each.
- Suites: 51 — 410 checks green. 220 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: minds that remember, and voices (asked for)

- **Asked for LLM-driven speech for ships, crew, other captains and anything
  that communicates, with personalities, and persistent characters whose
  memories update from interactions and from what happens in the universe.**
  This is the foundation: providers, personas, minds, and the speaking layer.
- **The binding constraint, taken seriously**: the game ships with no network
  and the suite is hermetic. So `core/llm.py` is **off by default**, gated on
  `SEEDFALL_LLM`, hard-timeout, and `complete()` returns `None` whenever there
  is nothing there — which is the ordinary case, not an error, because every
  speaking path had to work offline anyway. `test_voices.py` replaces
  `llm.complete` with something that *raises*, so a check that reaches for a
  model fails loudly; what the suite measures is the written voice.
- Providers detected from whatever is on the machine: Ollama on localhost, an
  Anthropic key, an OpenAI-compatible endpoint.
- `data/personas.py` makes personality data rather than prompt strings: eight
  voices — the ship's computer, an officer, a harbourmaster, another captain, a
  raider, a faction envoy, a Dry Choir lineage, and plain — each with a
  register, tics, a temperature and **sentence frames for seven moods**, which
  is what the offline path speaks with. It is the default, so it has to be
  worth reading; a check holds all fifty-six combinations to being distinct and
  slot-free.
- `sim/memory.py` gives officers, captains, ships, factions and ports a `Mind`:
  memories with a day, a kind, a salience and tags, from three sources —
  direct, heard (sector news), and prior (a past generated before you ever meet
  them). Salience decays; recall is by fit to the situation rather than
  recency, so a customs desk raises the seizure and a counter raises the cargo.
  An impression is derived from what is held, and `grudge()` names the
  memories responsible for it.
- **It is wired to real events, not a system beside the game**: a kill, a
  parley, a rout, a seizure at customs and a finished contract each write a
  memory, and losing a colony or turning the sector over into an epoch is
  broadcast as news that every power and quay hears.
- **The mood is decided by the game, never by the model.** A model is told how
  a character feels and asked only for the prose; its answer is validated for
  length, leaked instructions and line count before use, and falls back
  silently. Speech reads state and never writes it, which is what makes the
  whole feature removable.
- Two phrasing defects found by reading the output rather than the code: leads
  ending on a pronoun produced "I have not forgotten that you you left…", and
  unweighted backstory made every greeting open with two pieces of somebody's
  childhood.
- Suites: 50 — 404 checks green. 210 modules, all under 500 lines.

## 2026-07-28 — SEEDFALL: pop-out instruments (asked for)

- **Asked for pop-up windows for monitoring ship systems and sensors, with
  good graphics.** Six of them — power, heat, integrity, hold, crew and a
  scope — each in its own window, staying on top, re-reading the live game
  every nine-tenths of a second. Windows rather than another tab on purpose:
  the point is watching heat while you fly, and a tab cannot do that.
- Painted, not assembled from labels: `ui/gauges.py` draws a 240° dial with
  ticks and a needle, a segmented stack for the hull and the hold, and a scope
  with a sweep, range rings, bodies on the inner third and stars in sensor
  range on the outer. All QPainter, so it renders identically offscreen and the
  suite can look at it.
- `sim/telemetry.py` holds the readings so the layer rule stands and the checks
  can ask what an instrument *says* without painting it. Each reading carries
  its own band — good, watch, bad — from the sim's thresholds rather than the
  panel's opinion.
- **The defect, found by looking**: the crew dial drew a needle over "0/0 d"
  while its own caption on the same face read "124 days of air", because `Dial`
  paints `now`/`cap` and the crew reading supplied neither. Every dial-able
  reading carries them now, and a check holds all three to agreeing with
  themselves.
- Suites: 49 — 396 checks green. 206 modules, all under 500 lines.

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
