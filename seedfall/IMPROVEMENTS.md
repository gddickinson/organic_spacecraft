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

## Open — defects and debts, in rough value order

1. **Tuning constants without a guard.** The tripwire's last clean sweep
   read 60 of 131 unprotected (`INTERFACE.md`, "Which numbers are actually
   held in place"); a few have been pinned since, and new constants
   (`path.py`, `engage.REACH_KM`, `freeflight.RUN_MARGIN`) joined the pool.
   Each pin is its own small piece of work: drive the sim to the bar,
   bracket with absolute values. Re-run the sweep before choosing targets.
2. **Eleven recorded length debts, 525 lines** (`tests/test_length.ALLOWED`),
   `data/works3d.py` at 635 the worst. Each is a real seam to find, roughly
   a cycle apiece; the ratchet stops them growing meanwhile.
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
