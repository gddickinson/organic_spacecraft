# IMPROVEMENTS.md — the live backlog

What could be better, honestly sized, kept current. The done column stays,
because a list that forgets what it cost is a list that re-estimates badly.
History and reasoning live in `INTERFACE.md` ("One flight deck", "The second
pass") and `SESSION_LOG.md`; this file is only the state of play.

## Done — the flight-deck campaign (commits `a6393aa`, `c9335eb`, 2026-08-03)

The player report that drove it: pilot/conn/flight/gunnery not integrated,
sluggish, contradictory displays, engine activity unrelated to speed,
autopilot disjointed and wrongly displayed.

- One armed state on the flight (`Conn.auto` / `arm_main` / `clock_on` /
  `mark`); every window reads it. One clock (`ui/flight_clock.py`).
- Autosave no longer writes the sector on every repaint (~30 ms under every
  button — most of the "sluggish").
- Flight-controls window reads `game.conn` (was blind without the Conn
  window); approach window likewise.
- Hand-over from alongside opens clear of the structure, carries the adrift
  baseline, and goes to the nearest thing in reach of where she actually is.
- Every path that replaces a live flight bills it first; a clearance refusal
  keeps the flight and says why (`ui/conn_moves.py`).
- Reaction mass billed as it burns, settled exactly (#148, #149);
  `berthing.secure_underway` settles a live conn before any transfer.
- Approach-control ladder and point defence run per tick, not per substep
  (was 120× harsher at worlds).
- "Look fore" cameras, one name per autopilot mode, objectNames throughout
  (#153). Run bill quoted on the ship board before a run drains the tank.
- Transit applies the heat and risk its own forecast quotes; the orrery
  walks the hull along the leg while a crossing is stood.
- The computer flies into bays (mouth-axis corridor, go-around; 0/6 → 16/16
  at a gestation shell) and refuses a hull target with the reason.
- The descent order (`Put her down` / `Belay the descent`) on the conn
  console; `sim/landing.py` reachable in play.
- Conn side panel syncs in place (18–21 ms a beat → 2.8 ms).
- `engage.REACH_KM` decoupled from the free-flight advisory.
- The two ship masses documented as two deliberate laws (handling vs
  registry, up to 10⁶ apart) — **do not unify**; see `thrusters.mass_tonnes`.

## Done — the third pass (2026-08-03): held engines, one clock, the HUD

The player's report: manual engine control worked in steps with
instantaneous responses; burns should build velocity over time, be visible
on the flight-control visualization, and the clock should be universal
across pilot, helm and flight control.

- **Hold-to-burn** — the pads and the new keys (W/A/S/D, R/F) are
  press-and-hold through `flight_clock.start_burn`/`end_burn`: a standing
  order the beat consumes, so speed ramps and the plumes stay lit for the
  burn's real duration; a quick click keeps the precise one-tick press.
- **Universal clock** — screen changes no longer stop it; HUD chip on every
  screen; helm Run/Stop; battle stops it at once; time compression
  ×1/×4/×16 in the one beat.
- **Heads-up aids in every camera** (`ui/viewport_hud.py`) — predicted path
  under the current control state, prograde/retrograde, the approach's aim
  point, a bay's mouth ring; the bridge mark carries the engagement band.
- Brake-to-zero mode; one-button computer docking from the helm; a ninth
  tutorial lesson teaching the conn (watched through billed conn time).

## Done — the fourth pass (2026-08-03): one computer, the same bar everywhere

- `sim/flightdeck.py`: the flight computer's one front door (`computer`,
  `can_arm`); no screen owns a private dispatcher.
- `ui/autopilot_bar.py` on Pilot, Helm, Conn, Flight controls and Approach:
  all modes + Manual, same labels, same toggle, through
  `flight_clock.arm_mode`.
- "Depart" mode — moving away is a verb of the same computer.
- Computer docking beside the hand-flown mini-game on the system screen;
  the helm's dock button is the same door.
- One interplanetary executor: the plotting board flies the helm's watched
  crossing instead of the instant `travel_to`.

## Done — the fifth pass (2026-08-03): flown rigorously

Played every goal from every window, by hand and by computer. Three real
defects, all hidden by one coverage gap — no suite had ever pressed a
control in a *pop-out* window.

- **A body conn opened already finished** (8 of 11 seeds): the pad and every
  mode dead before a control could be touched. `Conn.opened_orbiting` +
  `outcome.resolve`; `autopilot.fly` writes the mode it flies.
- **"Move away" flew the ship into the planet**: a radial demand in a
  gravity well cancels the orbit. Departing a world climbs the ladder now,
  or refuses with the reason.
- **A held burn could outlive the hand holding it** (rebuild, screen change,
  window close): every door closes the order via `end_burn(quiet=True)`.
- `tests/test_flightops.py`: every control in all six flying windows, on a
  flight of every kind — plus the goal checks (body conn, depart, descent
  order, heads-up aids).

## Done — the sixth pass (2026-08-03): the tutorial becomes a curriculum

Play-tested the non-flying half and the seams between the halves, then built
the teaching layer the game was missing.

- **29 lessons in 10 courses** — each course a scenario a beginner can take
  on its own (`data/lessons_early.py`, `lessons_late.py`).
- **`sim/tutorial_watch.py`** — every watcher reads the world against a mark;
  the six acts that leave no state behind are recorded by the sim function
  that performs them (`deed`), never by a button.
- **`ui/academy_panel.py`** — the Academy tab: courses, progress, and
  "Teach me this", which steps over what you can already fly.
- **Four manual pages on playing well** — first hour, money, flying,
  fighting.
- **A process-killing paint bug**: thirteen widgets painted without
  `ui/painting.py`'s guard, and one of them aborted the suite (exit 134, zero
  failures). `painting.alive` + `@painting.safe_paint` now cover them all.
- **Integration fixes**: local work secures a live hand-flight first; the
  flight clock is held off the flight deck (and says so) so shopping cannot
  quietly cost days.

## Done — the eighth pass (2026-08-03): what the instruments actually see

**"How far are ship systems able to detect objects?"** — the honest answer
was *infinitely far, perfectly*, and that was a defect. The collision guard
read `Conn.sky` straight: a noiseless list of everything in the system, so
the cheapest array got a VESPER Organ's warnings and a raider running dark
was tracked as precisely as a lit quay.

- **`data/countermeasures.py`** — a signature is a share of a lit hull:
  transponding 1.00, running dark 0.28, shrouded 0.10, cloaked 0.035. Which
  one a hull runs comes from its errand and a stable hash of its id, so it
  never drifts from the traffic that generates it and two screens agree.
- **`sim/detection.py`** — 4,000 km of reach per light year of array. Worlds,
  stars and quays are unmissable by construction; hulls are the question.
  `Track.quality` falls off as `1 − (km/reach)²`, and past the edge the
  contact is simply *not on the plot*.
- **A poor fix is read pessimistically.** The guard inflates a closing rate
  it cannot trust and shaves the room it thinks it has — 200.0 m/s on a
  superb array reads 257.9 m/s on one barely holding the contact — so a bad
  sensor warns early rather than late, and the board says *estimated*.
- **The emergent rule: a cloak beats your brakes before it beats your eyes.**
  On the opening hull, lit contacts show at 16,800 km and cloaked at 588,
  against 1,019 km of stopping distance at 300 m/s. Everything else is seen
  with room to spare; the cloaked one is on you.
- **The array is stamped on the flight** (`Conn.array`), not read from the
  game. `sim/instruments.readout` holds a Conn and no Game, so a guard that
  asked the Game would have had the panel using a default 2.0 ly array while
  the computer used the ship's real one — two screens disagreeing about what
  is out there, which is the fault this whole campaign was about.
- The `Collision` row names what is hiding and whether the fix is a guess; a
  `Contacts` row appears when something out there is not squawking; and a
  manual topic ("What you can see, and what can hide") quotes *your* ranges
  from *your* array. `tests/test_detection.py` holds the six claims.
- **Found by playing: the sky was different every session.** The first draft
  rolled a raider's countermeasure off the builtin `hash`, which Python salts
  per process — so a hull came up cloaked in one session and dark in the
  next, and a reloaded chronicle was a different sky. Invisible inside a
  single run, which is why the claim that catches it spawns three
  interpreters. It rolls off `core/rng.hash_seed` now, the same way
  `sim/traffic` already keyed its own hulls, and the roll moved from `data/`
  to `sim/` where deciding belongs. Measured across five galaxies: 417 hulls,
  25 raiders, 4 of them cloaked — meeting one is an event.
- **The curriculum learned the last two passes.** A new lesson in *The
  wheel* — "Find out what is in the way" — has the captain throw the
  safeties switch off and back on, and explains in one place what the guard
  does, that contact is allowed when you mean it, and that a hull running
  dark is close before it exists. Thirty lessons now.
- **One door for the safeties switch.** The conn console and the flight panel
  each flipped `conn.safeties` themselves and each carried its own copy of
  the sentence to say about it. `collision.toggle_safeties` is the one door;
  it also records the deed, which is what the new lesson watches.
- **A length debt paid, not recorded**: `sim/conn.py` went over the ceiling,
  so the two flight builders moved to `sim/conn_open.py` (424 + 113 lines).
  The seam is real — opening a flight reads the whole game, flying one does
  not — and PEP 562 keeps `conn.start` working for every caller.
  `tests/test_tutorial.py` went the same way for the same reason: how a
  lesson is *performed* moved to `tests/tutorial_acts.py`, leaving the suite
  to hold the claims (402 + 122 lines).

**Known limitation, unchanged by this pass**: `Conn.sky` is a snapshot taken
when the approach opens, so a hull sits where it was then. A dark raider
cannot yet *close* on you during a flight — it can only be somewhere you did
not see. Giving a sighting a persistent, ageing position is item 3 below.

## Done — the ninth pass (2026-08-03): orbits with a shape and a tilt

**"Every object in the system is orbiting the sun in the same way."** True,
and not a drawing fault: `flight.position` had one element to read.

- **`data/orbit_shapes.py` + `sim/elements.py`** — six Keplerian elements,
  derived from the body's identity and kind, never stored, so old chronicles
  gain real orbits on load. Every bound quoted against a real Solar System
  body so it can be argued with rather than merely preferred.
- **Three dimensions everywhere a position goes** — `separation`,
  `distance_to`, `route` (which bends round the star unchanged, because the
  geometry was already dimension-agnostic), `track.at`, `traffic.position`,
  the conn's sky, both charts.
- **The plotting board finally shows what it was built for.** Its `to_screen`
  has taken a `z` and tilted since the day it was written, and its docstring
  said the orbits were flat but the tracks needed somewhere to stand up. Now
  the orbits stand up too, and a steeply inclined path is drawn a shade
  brighter because an overhead view cannot otherwise say so.
- **Two limitation docstrings retired**: `freeflight.where` and
  `freeflight.toward` both dropped `z` "because the sector is a plane".
- **Hulls hold a circuit, not a spot**, at their own tilt and direction. The
  first draft used a real orbital period and broke rendezvous — five km/s
  against a conn that closes at tens of m/s. Station-keeping is powered; the
  constant says so.
- **A shove can push out of the plane** (`knock.pitch`), because a collision
  has no reason to respect an orbital plane.
- **The sector talks to you now, and a gate is a machine.** `sim/comms.py`
  and `data/signals.py` give the game an inbox: a sender, a body, sometimes a
  question, and a *delay*. Nothing is broadcast through a ring — a gate moves
  mass — so a despatch is carried by a courier that waits for a slot,
  transits and rebroadcasts. Four regimes, and a chronicle uses all of them:
  same system (a radio call), carried on the lit Weave (hours), shipped
  aboard ordinary hulls where there is no anchor (11 d/ly), and light where
  no hull can reach at all. Measured on one chronicle: 8 shipped, 33 light.
  `sim/gatetraffic.py` gives rings a bore (a size, not a toll) and a cycle,
  with queues read off the port's level and the hulls already in the system.
- **Still to build: enforcement at a gate.** Slots nobody polices are a
  suggestion. A warded anchor should be run, slipped past under
  `data/countermeasures` (which is where a cloak finally earns a use beyond
  the collision guard), or talked past with a forged despatch priority — and
  an unwarded ring in a lawless system should have no picket at all, which
  is what would make the Weave's geography political.
- **The exit-139 segfault: found, and it was never what it looked like.**
  `tests/test_verbs.py` drives every control on every screen by building a
  window per control, clicking, pumping the loop and calling `close()`.
  **`close()` is not a delete.** A closed widget is still a live paint device
  with events queued against it; the reference then fell out of scope, the
  collector took the C++ object at some unrelated later moment, and a queued
  paint landed on a device that no longer existed — which is why
  `painter.setBrush` appeared to fail on a good colour (the painter was fine,
  its *device* was gone) and why the crash always surfaced in a suite well
  after the one that caused it. Closing *and* destroying each window takes it
  from 1–2 in 4 to **0 in 8**.
  - It was characterised wrongly three times first — concurrency, then widget
    teardown at suite boundaries, then out-of-range projected coordinates —
    because it was reasoned about from symptoms. `python -X faulthandler`
    settled it in one run and should have been the first move.
  - Two fixes made while wrong are kept because they are real: `render3d`
    now bounds a projected vertex (one a hair in front of the lens genuinely
    projects to billions and genuinely can kill a rasteriser), and the
    harness puts windows down at suite boundaries.
  - **Exit 139 with zero failures is the worst shape a failure takes.** Grade
    a run on its exit code, never on a count of FAIL lines.
- **A dead star now leaves what a dead star leaves.** Three of the nine
  classes are corpses and all three generated systems from the living table —
  a supernova remnant could hold an ocean world with lifeforms in it.
  `data/remnants.py`: a white dwarf engulfed its inner system and shed the
  rest wide and cold, rubble-rich; a neutron star's planets are second
  generation, condensed from fallback debris, metal and sterile; a black hole
  keeps almost nothing. Measured over ten galaxies: 47% rubble round a corpse
  against 32% round a living star, 0 lifeforms against 975, innermost body
  1.78 AU against 0.40, 3.1 bodies against 3.8.
- **The generator's RNG stream is a compatibility surface, and I learned it
  the hard way.** The first version of the above chose a remnant's bodies
  with `rng.weighted`, which takes a different count of numbers out of the
  sector generator — so every seed in the game grew a *different sector* and
  **thirty-five checks failed in places with nothing to do with dead stars**.
  A galaxy is grown once and stored, so what a generator draws is as much an
  interface as what it returns. Remnants are recast **after the fact** now,
  derived from each body's own identity and touching `rng` not at all;
  disabling the feature and re-running was what proved the churn was mine.
- **`gate_body` enforced a rule it had only stated.** "Deliberately not the
  one the quay is built over" was left to the assumption that the outermost
  body is never the largest — true in a system of six, false in the two-to-
  four-body systems remnants keep, so a Weave anchor came out standing on a
  port. Single-body systems are exempt because there is nowhere else.
- **A survey quote cannot bill luck, and the check now says so.** It demanded
  the spend equal the forecast exactly; a burn incident ("the correction
  costs reaction mass nobody budgeted") took 6 t on top of a 3 t burn. The
  claim is the real one now: the quote is exact and anything past it was
  *announced* — a silent overspend still fails.
- **The orrery's seat fan is built rather than waited for.** It required some
  seed to happen to grow two quays at one body; after the remnant tables no
  seed in 160 did, so the case the fan exists for went untested while the
  check passed.
- **One order now docks her.** A run stopped 50 km short and handed the conn
  back; `flightdeck.berth_from_here` carries it on into the berth through the
  hand-over, the clearance and the boats. 18 of 18 chronicles run from open
  space to a named fitting.
- **The harbour's own boats were flying a course no captain would be allowed.**
  A tow ran straight at the berth from wherever it caught the hull and went
  through the structure — a collision at nought m/s, 579 m short of mast 4.
  `tug._walk` swings her round the keep-out sphere instead. Two traps found
  by checks, not by thinking: a guard that excluded the destination froze a
  tow for 2,100 beats, and the far-side case is exactly anti-parallel, where
  falling back to a straight line towed her through the middle.
- **Reported by the player: a quay was at the centre of its own planet.**
  An anchorage's position was its body's, so the range to it from that world
  was zero — the autopilot said it had arrived and would not move, and a
  target at zero range fills every camera at once. `anchorage.berth_orbit`
  gives it a place of its own; Fleet Hub stands 2,067 km off and running for
  it costs 606 beats and 8.7 t.
- **Found by playing the GUI: "Ahead" could not point up.** `Conn.heading`
  is one angle about the vertical and `freeflight.steer` discarded the third
  number, so a course laid on a contact above the plane left the nose under
  it — 5,952 km closed to 1,514 and sailed past. `Conn.pitch` fixes it; the
  same run closes to 14 km. The check that caught it was already there and
  had been passing for the wrong reason: everything used to be coplanar.
- **A second exit-134, and the same lesson twice.** One chart still unpacked
  a route leg as two numbers. `painting.safe_paint` caught `RuntimeError` and
  `TypeError` — the two a dying painter had raised *so far* — so `ValueError`
  walked out of `paintEvent` and killed the process, with 151 of 186 suites
  green and **nothing failing**. The list was the accident; what belongs
  there is "a picture that did not happen". It now catches the six that mean
  that, and the leg is unpacked whole.
- **Two silent short ranges.** `survey.reach_to` and `anchorage.reach_to`
  worked their distance in x and y only. Nothing crashed; they just read
  short for any body off the plane, which is most of them now.
- **Every world was lit from above**, whatever it was doing.
  `targets.starlight` returned a fixed `-0.25` third component, so the light
  fell the same way on a body above the plane as below it. It follows the
  body's own position now — this is what gives a world a terminator on the
  correct side, and it was only ever right by accident while everything sat
  in one plane.
- **Six cameras leave blind cones**, which one plane hid. A mark 35.7° out of
  the plane was ringed in none of the six windows; an off-picture chevron
  points at it now (`viewport_mark`).
- Found while converting: a bridge check asserted the computer burns "ahead"
  and then "astern", which was a fact about a flat sector — measured, it
  opened the torch 340 times on *down*, *left* and *back* and never once on
  ahead. The narration was right and the claim was wrong; it now checks the
  words against `conn.fired_*`, which is the thing it was really about.
- Found while converting: the free-flight rendezvous check was really testing
  the *fuel budget*, not the control law — every one of those runs is
  marginal on a new hull's 20 t and `run_quote` says `afford: False` for all
  three. It is given the mass now, and the bill is claimed where the bill
  belongs.

## Done — the tenth pass (2026-08-04): the review's worst, fixed

The same day as the review below, in its value order. Every fix carries a
played claim; the suites named held green through the pass.

- **The crash and the two data-loss shapes.** `go()` refuses an unknown
  screen before anything is hidden or reassigned; the two manual topics
  point at real screens; the manual's "go to" button only offers rail
  screens and calls them by their rail names. Escape at the ending returns
  to the game instead of falling into `clear_save()`; `begin_again` and the
  ending path no longer clear the save before the title dialog can still be
  cancelled, and cancelling it returns to a live chronicle. `closeEvent`
  saves; buy, sell and vent save the way `learn_about` always did.
  (`tests/test_ui.py` ×4, `ui/window_dialogs.py` split out — `ui/window.py`
  was at 507.)
- **The same counter never pays more than it asks.** The floor is stated at
  both layers — `world/economy.sell_price` clamps under what *this* captain
  would pay, `sim/market.quote_sell` clamps under `quote_buy` — so every
  modifier present and future is covered. The office rate keeps both its
  directions up to that ceiling. Swept: 532 quotes, cold and warm, every
  port; 40 played round trips lose money. (`tests/test_counter.py` ×3.)
- **A prospect is fed by bringing material in.** Tonnes bought over the
  issuing counter are remembered against the posting
  (`Contract.bought_here`, written by `trade.buy`) and do not complete it;
  the board's blurb says so. A delivery completes from the hold, not the
  location-free depot. (`tests/test_cargo.py` ×2.)
- **A worked-out board fills again.** `contracts.board_for` owns the board
  in `sim/`, stamped and turned over on the harbour's clock (faster at
  bigger ports); an old save's bare list is adopted, not thrown away.
  (`tests/test_postings.py`.)
- **The Bloom shows up for the fight.** The stage rides what it has
  *answered* as well as the burden (`data/bloom.STAGE_BY_ANSWERS`) — played,
  an engaged captain reaches Adaptive in 7 burns instead of never. The two
  no-op responses do their thing: answering advances the stage before the
  effects land, "everywhere at once" adapts against the family that has
  actually hurt it (`BloomState.hurt`, fed by combat *and* by `cleanse`,
  which fires the same fitted guns), and a cleaned sector still detaches
  instars from the living heart. A refused heart-strike no longer provokes;
  an instar never retargets the system it stands in; the heart is pinned to
  the generated origin, not a live `max()`. (`tests/test_bloom_arc.py` ×3.)
- **Combat is decided on the plot again.** Sensory interference saturates
  (`DAZZLE_CAP`) — the flash organ is a support tool now (hull kept 0.43 vs
  0.21), not a 10%→62% win button. The enemy plays a real seat a turn:
  engineering when cooking or holed, the helm when the geometry is wrong,
  gunnery otherwise — and its guns work every turn through the same
  `turnplan.bearing_set` arc test as every player selector, undirected
  unless gunnery is the seat, exactly the player's price. Damage control
  patches the outermost *breached* layer (it skipped `hp <= 0`, the one
  case its blurb advertises, and walked the list inward-first). The idle
  gunner fires on the ability and brace paths too. The legacy `move` order
  moves. `seal`'s armour lives on the side and survives the stat rebuilds
  that erased it every turn (`abilities.armour_of`, read by `combat` and
  `assessment`). `broke` can no longer be referenced unbound; the enemy's
  brace clears.
- **The log can tell good news from bad** — `"good"` and `"bad"` (61 call
  sites) are in `theme.TINTS`.
- **Diplomatic ground is worked once, whoever asks.** Two-party cooldowns
  key on the pair (broker) or the target (denounce), not the seat the order
  came from; denounce's appreciation runs through `courtship` like every
  other gain, and the preview quotes the tapered number.
  (`tests/test_overtures.py` ×2.)

## Done — the eleventh pass (2026-08-04): the sector answers back

The top of the reassessed list, in order. Every one carries a played claim.

- **A wait stands down on news worth a hand** (`core/clock.wait_days`,
  `Game.wait_days`). Found by playing: a year alongside a Fleet Hub starved
  three crew one at a time, with credits in the purse and biomass on sale a
  berth away, while the log said "it is starting to tell" five times and
  nothing paused. `advance_days` stays exact — work that bills its own days
  bills all of them — and *waiting* is the different verb. Stops on `bad`
  **and `warn`** (`STAND_DOWN_KINDS`: the starving crew is warned three
  times and only `bad` once everyone is dead, so stopping on `bad` alone
  stops exactly too late), always for a question the window would lock on,
  and reports a digest — days, treasury, what was said — with "wait the
  remaining N days" on the dialog. Measured on a provisioned captain:
  9–90-day stretches, so waiting is still waiting.
- **The Bloom is felt in the treasuries that fund everything**
  (`exchequer.BLOOM_YIELD_LOSS`). Nothing holding money read `system.bloom`
  before: a fully overgrown sector now takes a power from 724 to 109 credits
  a day, which shrinks its fleets, its ventures and its promotions through
  machinery that already existed.
- **The powers fight it** (`containment`, `data/ventures.py` +
  `ventures._apply`). Six venture kinds and none was about the thing eating
  the sector; nothing in the game but the captain had ever reduced
  `system.bloom`. A flotilla is fitted out for the worst system anybody can
  see, cuts 0.22 off it, and provokes the Bloom the way a captain's burn
  does. Backing or opposing it runs through the existing preview pipeline.
- **Ruin is outlived, not waited out** (`threat._stood_through_it`), and
  **the loss can be reached** (`threat.harbours_left`). Ruin asked only for
  a drowned sector and a live hull, which passivity satisfies ~180 days
  before the loss could fire — and victory is checked first, so a living
  captain could not lose to the Bloom at all. Ruin now wants something of
  yours still standing or a record of having fought; the loss fires when
  every *harbour* is drowned, which happens sooner and can be watched
  closing.
- **An empire is not free to administer** (`works.admin_total`,
  `data/works.ADMIN_STEP`). Each holding past the first makes every holding
  dearer: the marginal worth of one more falls from +359/day at five to
  +65 at thirty, so colony spam has a ceiling, and the credit line goes
  negative at scale — a large empire must *trade* to pay its bill, which is
  the late-game sink the game lacked. The seed card quotes it before you
  commit.
- Found while doing it: the bridge's `extract` verb advertised "tonnes" and
  its parameter was *days* of rig time — asking for 30 t ran a 30-day
  working that raised 99 t.
- **Fifteen failures the pipe had been hiding, all traced before fixing.**
  Four were real regressions of mine: the heart-fallback that fixed the
  no-op responses had let the *routine* top-up reach the origin, making it
  a permanent re-infestation engine that put Containment out of reach
  (`_spawn_instar(from_heart=...)` — a wave is an event, the top-up is a
  standing condition); and a competent enemy proved worth about a
  difficulty step, so a light patrol beat an armed hull three times in ten
  until enemy nerve was re-pitched (`encounters.RESOLVE_BASE`, measured
  82/33/15 across the scale against 71/33/15). Six were checks encoding
  rules deliberately changed — Ruin's new gate, hold-only delivery,
  `abilities.armour_of`, the moved ledger, and two fixtures that assumed a
  port can never close (a power poor enough to retrench now gives one up,
  which is the Bloom's economic bite working). **Five were checks measuring
  badly**, and would have failed on any later change: the provoked-growth
  check ran three years into saturation where both arms pin at the ceiling
  and read equal to the decimal — below it the effect is ×2.20 and ahead in
  20 sectors of 20, against the ×1.085 and 15-of-20 it used to report; the
  warfit and smuggling checks judged 32- and 12-sample statistics against
  thresholds finer than their noise, and smuggling used a *mean* where one
  seizure swamps the distribution (median: bare +33k, kitted +292k); and
  the `offer_gain` one-door check counted a *comment* as a reading.
- **Four length violations, and the measurement that hid them.** The tenth
  pass was reported green on a run whose exit code was read through a pipe
  (`... | tail; echo $?` is *tail's* status, always 0), so `tests/test_ui.py`
  at 530 lines rode into commit `0c98798` over the ceiling. Paid off along
  real seams: `tests/test_window.py` (the window as an application —
  navigation refusal, save on quit, dismissed dialogs, the unstubbed
  briefing), `ui/seed_dialog.py` (offering, pricing and planting a colony),
  and `sim/exchequer_ledger.py` (the screen queries), which took
  `sim/exchequer.py` under the limit and **off the debt list** — ten files
  and 517 lines of debt now, down from eleven and 525. `tests/test_play.py`
  went the same way afterwards, along the seam its own docstring names:
  `tests/test_endgame.py` holds the Bloom's escalation, its adaptation and
  the climax at Kessel's Reach.
- **A check whose control was somebody else's ports.**
  `test_industry`'s "cheaper than other powers' berths" inverted by one
  credit (156 against 155) the moment infestation began moving power
  economies — the same shape as the 1.15 ratio that check already records
  recalibrating once. Replaced with the like-for-like control (the same
  berths, the same year, without the licence), which no tuning of the
  sector's economy can shift. **A control that is not the thing you changed
  is not a control.**

## Done — the twelfth pass (2026-08-04): played again, five things found

A fresh play-through of the committed tree, over the bridge and on screen.
Everything here was found by playing rather than by reading.

- **The ship's log became an unreadable smear.** By day 226 the sidebar —
  the game's only notification channel — was a column of two-pixel slivers.
  The same fault `widgets.View._sync_scroll` exists for, in the one panel
  that fix never reached: rebuilding a column of wrapping labels inside a
  scroll area does not tell the inner widget its contents grew, so sixty
  entries were flattened into one screenful instead of scrolling. Now
  2,062 px of log in a scroller, and the good/bad tints from the tenth pass
  finally do their job.
- **A recurring warning turned a long wait into a wall.** Standing down on
  every bad line meant a hold short of biomass stopped the wait eight times
  in fourteen days with the same sentence. `wait_days(..., ignoring=)` and
  a digest that hands back what it showed: **"carry on" now means "I have
  read that"**, and only genuinely new news stops the next spell. Measured:
  three stand-downs for three distinct developments, then a full 120-day
  spell.
- **A driven session deadlocked on an envoy.** An envoy or a territorial
  demand stops the clock and locks the window, and the protocol could
  neither see nor answer one — so every wait returned nought days for ever.
  `waiting` and `reply` verbs (`bridge/protocol.py`).
- **The containment bar said "nearly won" to a captain who had done
  nothing.** It measured systems-not-yet-infested, so an untouched sector
  on day 227 read 38 of 42. The husk is half the condition and is now half
  the measure: 46% untouched, 50% with the sector clean, 100% only with the
  origin dead.
- **"Five of them"** over ten endings, counted now rather than stated; and
  `HEART_HP` read from `data/bloom` in both views instead of a hardcoded
  2600 in each.

## Done — the thirteenth pass (2026-08-05): the flight deck, photographed

A deep play-test driven through the real interface — a hull flown to a quay
by hand and then by computer, every flying window opened, every instrument
photographed and *looked at*. Five defects, none of which stopped anything
working, which is why pressing every control had never found them.

- **Opening the conn threw away a finished approach.** Berthed at Fleet Hub,
  moored, `anchorage.docked_at` naming the berth — and opening the Conn
  window began a fresh approach at the arrival range, so the instruments
  read 12,000 m from a quay the ship was tied to. Securing sets `landed`,
  and the window read that as "no live flight". Exactly the fault that
  window's own note says it exists to prevent: one flight, whichever window
  you look through. Taking the conn again is a control the pilot presses.
- **Two controls in one grid cell.** The conn console put "Cut in" and the
  100% throttle in the same place — four throttle steps running into a
  button at column 3 — drawn over each other into an unreadable smear, both
  clickable. The throttle and coast runs have a row of their own now and
  their columns are derived, so neither collides if either list grows.
- **An instrument value cut off mid-word.** "Computer — off — she flies as
  you fly her" was drawn unwrapped in a fixed-width column: the pilot read
  "she flies as you f". Values wrap now.
- **A ladder of overlapping labels.** Every tick on the predicted course
  carried its time, and on a slow approach the whole hour landed inside
  forty pixels — "6m120m…560m" in one smear. One label per `LABEL_GAP`.
- **Four names in one place on the plotting board.** At the default zoom the
  inner system is a few pixels across, so the star, its worlds, the quay and
  the ship all wrote their names on the same spot. Names give way to each
  other (`NAME_GAP`); marks never do, and a chosen mark is always named.

`tests/test_flightpix.py` holds the four claims — a suite that asks whether
the flying windows can be *read*, beside `test_flightops`, which asks
whether their controls work.

## Done — the fourteenth pass (2026-08-05): the fog, and two stolen flights

The Holdings fog leak, then a forty-six shot sweep of every screen with a
flight photographed at five stages, an orbit, a free flight and all six
cameras.

- **The Holdings panel counted the whole sector.** `intel.sees_bloom` covers
  the chart and this went round it: every infested system counted and the
  sector-wide burden printed, above a picket whose `watch` is sold on
  telling you what happens where you are not. `threat.known_bloom` is the
  one door — the census is what is *known*, and it says how many systems
  nothing of yours has looked at rather than folding them in silently.
  `victory_progress(seen_only=True)` fogs the containment bar for display;
  **the achieved flag is never fogged**, or a captain could take Containment
  by keeping their eyes shut.
- **Opening the conn stole a live orbit.** Established at 299 km under the
  computer, opening the Conn window switched the target to a quay and began
  a fresh approach — photographed as "Conn — Fleet Hub, approach begun,
  12.0 km" over a hull circling a world. Two causes, both now fixed: the
  window asked `default_target` instead of the flight it already had, and
  **a `Target`'s id is not a `Contact`'s id** — a quay is `quay:port-14` on
  both sides but a body is `body:0` as a contact and `0` as a target, so
  "am I already flying to this?" answered *no* for every world in the game.
  `conn_targets.same_place` asks the question through
  `targets.target_from_contact`, so both sides are the same kind of thing.
- The same fix retired the `landed` half of the test: `landed` means
  *arrived* — secured at a quay, established in an orbit, set down on a
  surface — and all three are still flights whose target the window should
  be showing.

- **A ship in orbit is no longer at the planet's core.**
  `flight.ship_position` returned the body's exact position when alongside
  one, so the Pilot screen listed a world 6,772 km in radius at `0 km` and
  every range to the thing you were standing at came out nought. This is
  the third defect of that shape the project has fixed, after
  `anchorage.berth_orbit` for a quay at its planet's centre and
  `traffic.STATION_KM` for a hull sharing a body — and it is fixed the same
  way, by giving the thing a place of its own.
  `flight.ship_orbit_offset` holds the radius the flight actually flies
  (`Game.orbit_alt_km`, or the standard rung when nobody has chosen), on an
  orbit derived from the body's identity and the calendar and never stored,
  so an old chronicle gains the place without a migration. Measured: the
  world that read 0 km now reads 7,449 km, which is its standard orbit
  radius, and the conn's altitude and this agree because both ask
  `orbits.height_km`. Two position claims that asserted the hull sat at the
  body's exact centre now assert the stronger thing — that it rides *with*
  the body without being buried in it — and a new sweep holds that nothing
  a captain is standing at ever reads zero (61 ranges, 6 chronicles).

## Done — the fifteenth pass (2026-08-05): one way in to everything

**Reported by a player: "I can fly up to a Weave anchor, but how do I use
it?"** They were right to be stuck. An anchor is a place in the system with
no services, the panel that rides a ring lives on the sector chart, and the
anchorage card's fall-through for anything that is not a quay offered *Open
holdings*. So the game invited them to fly to a thing and then said nothing
at it.

- **The anchor explains itself, at the anchor.** Standing at one now says
  what a Weave anchor is, whether it is lit, what it is joined to, and — if
  dark — exactly what waking it wants, which is the Weavecraft technology
  before anything else. With a button to the chart where the ring is ridden.
- **A manual topic**, "The Weave, and how to ride one", with a generated
  fact that reads *this* chronicle: how many anchors are burning, what the
  one here is doing, and what a step from where you stand would cost.
- **`sim/hail.py` and `ui/comms_window.py` — the general fix.** One door
  that opens on anything `sim/track` can put a cursor on: who they are,
  what they say in their own voice (`sim/voice`), and a menu of what can be
  done, every entry either available or greyed *with the reason*. A quay
  lists its services and its harbourmaster; a gate lists its transits or
  what it needs; a world lists survey, rig and landing; a hull lists hail,
  mark and the guns. Reachable from the Pilot screen's contact rows and
  from every place on the helm's put-in list.
  It decides nothing — every option is a door that already existed
  (`berthing`, `gates`, `hostiles`, the port screen), which is what stops a
  menu promising what the game would refuse. `tests/test_hail.py` holds
  that: what the menu offers is what `berthing.can_conn` answers, and every
  refusal names a reason.

## Done — the sixteenth pass (2026-08-05): played long, and losing exists

Fifty-odd chronicles driven headlessly across the economy, four long games
pressed through the real GUI to day 2,280–2,666, and the option-space behind
every dialog (colonies, research, the ground, digs, the shipyard) driven
directly. The GUI play found nothing; the long economy runs found eight
things, and two of them were load-bearing.

- **The game had no loss by neglect.** Three modules agreed a chronicle ends
  when the crew is gone, no officer is active and no machine keeps watch —
  and the test sat inside the branch `upkeep.tick` only reaches when
  something the crew *needs* is missing. Nothing is missing once nobody is
  aboard to need it, so the branch was unreachable: five do-nothing
  chronicles all emptied (seed `dn-a` at day 1516) and not one ended.
  `upkeep.unmanned` is asked every tick now; doing nothing ends it at 1517.
- **Idling out-researched playing by about forty per cent.** `research.tick`
  poured `banked` in raw while the day's own points were throttled by what
  the bench is supplied with, so *not choosing* beat choosing and a saved
  lump cascaded through node after node. Banked points go through the same
  gate now: always-on 12 techs against bank-then-dump 13, was 16–17.
- **Standing was purchasable at about 350 credits a point.** Survey data is
  an ordinary stocked commodity, so the sets could be bought over the very
  counter they were handed back to, and the hand-in granted `min(6, n*0.4)`
  with no cooldown — nought to the +100 cap in 19 to 26 hand-ins.
  `SURVEY_REP_CAP` puts it at the same rate as any other sale, and the
  hand-in finally goes through `wharfage.collect`, which its own docstring
  calls "the only place money moves" — 50 sets moved 20,650 credits with the
  quay seeing none of its 519.
- **A prospect is gated on the voyage, not on a tally.** The `bought_here`
  count added in the twelfth pass never came down, so a captain who
  *refuelled* at the issuing port — volatiles and biomass are both wanted
  goods — had an honest mined cargo refused for tonnes long since burned.
  `Contract.travelled` is the thing the rule was always reaching for, and a
  purchase cannot poison it.
- **A starving holding said so every day for ever** — 770 lines in 800 days,
  which wiped the 300-line log inside four months and stood a long wait down
  daily. Once when it starts, once a year after that, and once when it is
  fed again.
- **A hold worth selling is a way out.** `is_stranded` priced escape against
  the purse alone, so a captain at a market with 15,000 credits of silicon
  aboard was called stranded — and the tow charged them standing to be
  dragged away from the counter that would have fixed it.
- Two smaller ones: a discarded docstring in `colony.bloom_attack` (two
  string literals, the informative one a no-op), and the harness captain in
  `tests/captain_bot.py`, which bought fuel and never food and then had no
  income once the bodies in reach ran out. **Three times now this file has
  recorded the same lesson: that is not the game dead-ending, it is the
  probe failing to take the move in front of it.**

## Done — the seventeenth pass (2026-08-05): one ship, one place, one drive

Three things reported from play, all of them the same shape — a fact with
more than one door.

- **The ship's position did not follow a flight.** `flight.ship_position`
  returned the *recorded* place, and the recorded place is not written again
  until `berthing.commit` — so the helm's system map, the plotting board and
  the tactical list all held the hull at the quay it left while the conn
  beside them counted the range down. Reported as four windows disagreeing
  with a fifth; it was one window telling the truth. `base_position` is the
  recorded place now (what `freeflight.where` flies from) and
  `ship_position` adds `Conn.flown_km` on top, so every screen that already
  asked the one door follows the flight without being told there was one.
  - The subtlety that cost a rewrite: **`conn.pos` is not an offset from the
    ship.** An approach's frame is anchored on its *target* and
    `conn_open.start` opens it at a canned arrival range, so `conn.pos` is
    already kilometres the instant a conn is taken — adding it teleported
    the hull every time a window opened. `Conn.start_pos` and the
    `flown_km` it feeds are zero at that instant and exactly the kilometres
    flown after it, which is true in an approach frame and a free one alike.
  - The sector chart is at light-year scale and a flight inside a system
    does not change which system you are in. There is nothing there to
    follow, and the check says so, so a later cycle does not "fix" it.
- **The engine button said "off" while the computer was burning.** Three
  windows formatted that label themselves and only the flight panel had
  learned to say FIRING. `instruments.drive_note` is the one door;
  `conn_controls`, `flight_window` and `pilot_panels` all ask it.
- **Speed was there under two names.** `instruments.readout` called it
  "Speed" in a free flight and "Relative" when orbiting and when coming
  alongside. One quantity, three windows, two words — which reads as a
  missing instrument, and was reported as one. It is "Speed" everywhere; the
  orbit panel keeps "Circular here" beside it, because that is a different
  number.

**And one thing the new fixes caught in an old check.** Giving the game loss
by neglect (16th pass) silently shortened every long headless fixture: a
do-nothing chronicle now ends at about day 1,360, and `advance_days`
early-returns after that — so `test_war`'s "3,600 days" loop was really
running about 1,400 and measuring the sector a third of the way through its
decade. It reported 1 war over six sectors and no quay changing hands, against
6 and 2 when the calendar actually elapses. The fixture provisions the hull
now (food and wages, the only things `upkeep.demand` asks for — not a
suppressed death, so a regression in the rule itself would still show), and
the check reports the span each sector actually got so the truncation cannot
go quiet again. Surveyed the rest: `test_geography._fed` already had the
pattern and its docstring says why; every other long fixture stops under
1,400 days. **Any new fixture that means to run past ~1,400 days must
provision, or it is measuring less calendar than it asks for.**

Played rather than argued: `test_window` opens the real `OrbitChart` and
`PlotCanvas`, flies the hull 19,539 km from the flight deck and asks each
widget where it is drawing her; `test_position` holds the recorded place
still mid-flight and checks securing does not count the flight twice;
`test_instruments` drives all four target kinds for the speed row and walks
the drive label through off → armed → FIRING with the pad switched *off*,
which is the reported case.

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

## Open — the 2026-08-04 review: the systems layers

A four-agent review (combat, economy, strategic layer, player experience)
plus a live play-through over the bridge, looking everywhere the flight-deck
campaigns did not. The verdict: the flight deck holds and the systems layers
do not — not one item below was on this list before, and every number was
measured by driving the sim, not by reading it. In rough value order.
(The worst of it — the session-brick, the data loss, the same-counter
arbitrage, the contract exploits, the dead board, the unreachable Bloom,
the flash organ, the diplomacy exploits — was fixed the same day; see the
tenth pass above.)

*(Most of this list was closed by the nineteenth pass above — the scrap
exploit, the raw prices, the contraband market, the promotion arithmetic,
the robots, SOL-FORGE, the Cartel ledger, threat scaling, surrender/prize,
`nonlethal`, the brace button, the Charter's warships, the comms UI and the
keyboard sweep. What follows is only what remains open.)*

- **Mining is the worst-paid thing in the game** at 129 cr/day median, and
  it is the one with hull wear and mishap risk. Now that colonies have a
  ceiling (eleventh pass) the comparison is fairer, but a rig should still
  beat sitting still.
- **Lawlessness still has one moment to bite** — `sim/piracy.py`'s
  five-term model is read only at the jump exit. The nineteenth pass added
  a second interception moment (warrant hunters), but that reads the law's
  ledger, not the lawlessness model; the two never meet.
- **No sound. Not one byte** — no audio asset, no QtMultimedia import in
  the tree. Four cues would carry more than any HUD addition: thruster loop
  on the held burn, proximity tone off the collision guard, berth-secured
  chime, a distinct bad-news alert. `QSoundEffect` behind a no-op façade,
  the same shape as the optional-LLM path.
- One save slot, no geometry persistence; buttons at 2.02:1 border contrast
  against WCAG's 3:1, `chloro`/`osteo` luminance-identical for a
  deuteranope, 8–9 px type with no scale setting; the Bloom absent from the
  HUD (the despatch counter is there now; a burden chip off
  `threat.harbours_left` is not); the header clips the ship name unelided;
  the yard's "After refit" numbers clip at the default window size;
  forced-answer screens lock navigation while their own fiction offers days
  to decide.
- `comms.tick` still watches exactly one fact (the standing band) against a
  docstring promising a sector that speaks. Colony losses and epoch turns
  now write to the board from their own sites; wars, port closures and
  harbour losses are the remaining material (`sim/threat.py` log tuples).

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

## Open — defects and debts, in rough value order

1. **Tuning constants without a guard.** The tripwire's last clean sweep
   read 60 of 131 unprotected (`INTERFACE.md`, "Which numbers are actually
   held in place"); a few have been pinned since, and new constants
   (`path.py`, `engage.REACH_KM`, `freeflight.RUN_MARGIN`) joined the pool.
   Each pin is its own small piece of work: drive the sim to the bar,
   bracket with absolute values. Re-run the sweep before choosing targets.
3. **Nine recorded length debts, 504 lines over** (`tests/test_length.ALLOWED`),
   `data/works3d.py` at 635 the worst. Each is a real seam to find, roughly
   a cycle apiece; the ratchet stops them growing meanwhile.
   (`sim/exchequer.py` was struck off in the eleventh pass;
   `tests/chronicle.py` in the nineteenth — its fights are
   `tests/chronicle_fights.py`, and the file sits at 471.)
3. **Other ships are not plotted on the helm chart.** Nothing gives a known
   hull a persistent position a chart could draw — honestly a design piece
   (where does a sighting live, how stale may it go), not a marker to add.
4. **The engine light lives one beat.** `fired_*` is truthfully "the burn
   that happened this tick", so at 250 ms the light flickers under an
   autopilot that corrects intermittently. A short UI-side latch (or a
   "last burn" row) would read better without lying about the record.
5. **The docking mini-game and the conn share a gate by accident.**
   `berthing.can_conn` refuses while `game.docking` (the mini-game) runs —
   two systems both named "approach" meeting in one check. Works, but the
   naming invites the next bug; worth a rename or a comment at the gate.
6. **The descent order is only on the conn console.** The flight window —
   the panel you'd actually fly a descent from — doesn't carry it.
7. **Run bill on the button as well as the board.** The ship board quotes
   it every beat; the `Run for X` button label could carry it too (stale
   between rebuilds — needs the label refreshed in `sync`).

## Ideas — not defects; would make it more fun or easier to pick up

(The first five ideas — dock-for-me, keyboard flying, the conn tutorial
lesson, time compression, brake-to-zero — shipped in the third pass.)

- **More HUD, now the layer exists** (`viewport_hud`): a ladder of tick
  marks on the predicted path (time-to labels), the corridor hold point
  drawn as a gate rather than a chevron, closing-rate colour on the mark,
  weapon-arc cones in the tactical plot's first-person view.
- **Throttle on the digit keys** beside the six axis keys.
- **A combat HUD in the battle screen's own viewport** — the band ring and
  arcs are on the tactical plot; the first-person cameras go dark in a
  fight today.
- **An orbit you fly is still flat.** `autopilot.across` shapes an orbit in
  the conn's *local* x/y plane and returns a tangent with `z` zero — a
  deliberate simplification, and untouched by this pass because the conn's
  frame is not the system's. Now that a heliocentric orbit has a tilt, the
  obvious next question is a polar or inclined orbit round a world, which is
  a real thing to want and would need the tangent, the rungs and the orbit
  test to agree about which plane is being held.
- **Dead imports across `data/`.** `flake8 --select=F401` finds a couple of
  dozen (`dataclasses.field` in eight files, `models3d` helpers in three).
  Three were cleared where this pass was already rewriting the imports; the
  rest is a tidy-up nobody has done.
- **Let the captain hide too.** `data/countermeasures.py` describes the
  signature of *anything*, and only the sky reads it — the player's hull is
  always loud. A "run dark" switch (drop the transponder, bank the drive)
  that lowered piracy's encounter odds and raised customs' suspicion, with a
  shroud as a fitting you buy, would put the same table on both sides of the
  glass. The sim reads it already; what it needs is the cost side.
- **Sightings that age.** `Conn.sky` is a snapshot taken when the approach
  opens, so a dark raider can only be somewhere you did not look — it cannot
  *close* on you during a flight. This is the same missing piece as "other
  ships are not plotted on the helm chart" (defect 3): a sighting needs a
  home, a position and a staleness before either can be built.
- **The height picker's refusal could say which gate refused it.** A rung
  can be unsold because the tank is too small *or* because `orbits.quotable`
  says the price cannot be believed on these thrusters; the tooltip blames
  the tank either way, and `flightdeck.can_arm` has to point at the picker
  rather than repeat the gate. One reason string, asked of `orbits`, would
  let both screens say the true one.
