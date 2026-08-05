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

### The economy, measured

- **Mining is the worst-paid thing in the game** at 129 cr/day median, and
  it is the one with hull wear and mishap risk. Now that colonies have a
  ceiling (eleventh pass) the comparison is fairer, but a rig should still
  beat sitting still.
- **Scrapping a self-built hull profits.** `scrap_value` recomputes the cost
  without the fabricator discount the build was given
  (`sim/shipyard.py:293-298`): +146,470 credits per THRESHOLD cycle. It also
  values every returned tonne at a flat 60 — ore above market, silicon at
  7% of it.
- **The freight desk still has the bug `cargo_cost` documents fixing.**
  `sim/freight.py:150`, `:203`, `:258` call `buy_price`/`sell_price` raw
  instead of `market.quote_buy`/`quote_sell`, so the board quotes a price
  the counter will not honour. `trade.sell_survey_data` (`sim/trade.py:129`)
  the same. Worth a claim that nothing outside `sim/market` imports the raw
  prices.
- **One tonne of contraband opens a market the port was built without**
  (`world/economy.py:149-170` — `apply_sale` writes a supply into a
  zero-base stock and the next tick adopts a baseline at the scarcity cap).
  Verified: 14,300 cr/t at a port `make_market` refused to give the good.
- **A power's port can never be promoted, by arithmetic.**
  `YIELD_PER_LEVEL × L − UPKEEP_COEFF × L²` (`data/exchequer.py:31,36`)
  makes the marginal gain of level 2 exactly zero and level 3 negative;
  `payback` returns `inf` for both, and 2,000 played days produced no
  retrenchment and purses that only grew. The docstring's "any shock pushes
  a power into deficit" does not happen.
- Smaller: SOL-FORGE requires a `"star"` site no generator can produce
  (`data/colonies.py:112` — 0 in 1,223 bodies over 8 sectors); robot upkeep
  drives the account negative silently (`sim/robots.py:~351`); the exchequer
  `payback` re-derives a curve `yield_of` does not follow
  (`sim/exchequer.py:264`); the Cartel ending counts twenty-year-old price
  quotes (`sim/threat.py:195`).

### The Bloom, what remains

*(Reachability was fixed in the tenth pass; the economic bite, the
`containment` venture and the Ruin/loss separation in the eleventh.)*

- The Holdings panel and the containment bar leak the fog
  (`ui/empire_view.py`, `sim/threat.py` — no `intel.sees_bloom` filter), so
  a picket's `watch` still buys nothing. (The "Five of them" line and the
  hardcoded `HEART_HP` beside it were fixed in the twelfth pass.)

### Combat, what remains

*(The flash organ, the one-seat enemy, and the four silent deletions were
fixed in the tenth pass.)*

- **Threat never scales.** Day 1 and day 900 draw the same 1.0–3.0 spread
  (`sim/encounters.py:166`), and `engage.py:145` spawns the conn's target at
  the *default* difficulty — opening fire yourself buys the easiest fight in
  the game.
- **Nothing sits between "kill it" and "let it go".** No surrender, no
  prize (though `consorts.sail` already flies a second hull under your
  flag); `driven-off` pays 10 research; fleeing is ~0.61 odds per turn,
  retryable, and `fleeable` is never set False by any caller. The aftermath
  prints recovered tonnage without valuing it — the cargo is ~5× the credit
  loot and the player cannot see the reason to fight.
- Smaller: `brace` vents three times and has no button; `nonlethal` is
  read by nothing (`damage._breach` kills crew whatever opened the hull);
  lawlessness can only ever bite at the jump exit (`sim/piracy.py` builds a
  five-term model with one moment to use it); the Charter fields armed
  warships against its own lore (`encounters._outfit` arms any chassis).

### The world talks and the player cannot hear it

- **`sim/comms.py` is a complete, ticking, saved inbox with zero UI.**
  Five channels, couriers, lag — grep `ui/` for `comms`, `unread`,
  `asking(`: nothing. Signals accumulate unbounded in the save because
  nothing ever calls `read`. A Captain's Log screen — full scrollback over
  the 300 stored lines (the sidebar shows 60, the rest are unreachable),
  a kind filter, a despatches tab, an unread pill on the HUD — is the
  highest-value UX item on the table. `comms.tick` also watches exactly one
  fact (your standing band) against a docstring promising a sector that
  speaks; the log tuples in `sim/threat.py:66-116` are the material.
- **No sound. Not one byte** — no audio asset, no QtMultimedia import in
  the tree. Four cues would carry more than any HUD addition: thruster loop
  on the held burn, proximity tone off the collision guard, berth-secured
  chime, a distinct bad-news alert. `QSoundEffect` behind a no-op façade,
  the same shape as the optional-LLM path.
- One save slot, no geometry persistence; number keys don't match rail
  order (`4` opens the fifth entry — `data/screens.py:16-30`); W/A/S/D
  documented only inside one lesson and dead on the Helm though the clock
  runs there (`ui/window.py:363` vs `flight_clock.DECK_SCREENS`); buttons at
  2.02:1 border contrast against WCAG's 3:1, `chloro`/`osteo`
  luminance-identical for a deuteranope, 8–9 px type with no scale setting;
  "Twenty-nine things" over 30 lessons (`ui/academy_panel.py:31`), "Eight
  things to try" (`ui/title.py:136`), "Keys 1–8" over 13 screens (`:160`);
  the Bloom absent from the HUD; the
  header clips the ship name unelided; the yard's "After refit" numbers
  clip at the default window size; forced-answer screens lock navigation
  while their own fiction offers days to decide.

### What would hold it in place

Almost none of the above is catchable by the suite as written, because it
is about *reachability and balance* — code that works and is never reached,
numbers individually pinned and jointly exploitable. The tripwire's natural
sequel is a set of played economic claims: a same-port round trip loses
money at every trade × bias combination; a 2,000-day sector produces at
least one port promotion and one retrenchment; an engaged captain reaches
Bloom stage 2; no cargo contract nets positive without leaving the system.

## Open — defects and debts, in rough value order

1. **Tuning constants without a guard.** The tripwire's last clean sweep
   read 60 of 131 unprotected (`INTERFACE.md`, "Which numbers are actually
   held in place"); a few have been pinned since, and new constants
   (`path.py`, `engage.REACH_KM`, `freeflight.RUN_MARGIN`) joined the pool.
   Each pin is its own small piece of work: drive the sim to the bar,
   bracket with absolute values. Re-run the sweep before choosing targets.
3. **Ten recorded length debts, 517 lines** (`tests/test_length.ALLOWED`),
   `data/works3d.py` at 635 the worst. Each is a real seam to find, roughly
   a cycle apiece; the ratchet stops them growing meanwhile.
   (`sim/exchequer.py` was struck off in the eleventh pass — its screen
   queries are `sim/exchequer_ledger.py`.)
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
