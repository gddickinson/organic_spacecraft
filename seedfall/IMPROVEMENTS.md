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

- **"Dock for me" on the helm/anchorage panel**: one button that takes the
  conn on the quay and arms `close`, for the player who never opens the
  pilot screen. All the pieces exist (`open_conn(win, contact)` + `_auto`).
- **Keyboard flying**: the six axes on keys (and the throttle on digits) on
  the Pilot screen; the pad is mouse-only today.
- **A tutorial lesson for the conn**: the tutorial watches real acts; none
  of its eight steps teaches taking the conn, laying a course, or running
  the clock — the systems this campaign fixed are the ones a new player
  meets blind.
- **Time compression on the beat** (×1/×4/×16): a long run for a distant
  mark is minutes of real time watching the range fall; the one-clock
  design makes a multiplier safe to add in exactly one place
  (`flight_clock.fly_beat` ticks per beat).
- **A "brake to zero" convenience** beside the fly-at buttons (arm `null`,
  stop when still, disarm) — the pieces exist; it is three presses today.
