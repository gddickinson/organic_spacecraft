# Session log, part 31 of 31

Archived from the root `SESSION_LOG.md`. Dated entries here span undated to undated; undated entries keep their original place.

## conn_window comes under the line, and the Pilot screen's last blocker goes

`ui/conn_window.py` 508 → **466**, and off the ratchet. Fifteen files remain
named.

The seam is a real one rather than a convenient one: **which contact the conn
should open on** is a policy question, and the window around it is plumbing.
`ui/conn_targets.py` holds `default_target` and the `DEFAULT_ORDER` it reads —
and the Pilot screen (#137) needs the same answer for what to show and what to
offer, so this is a door two screens share rather than a private helper of one.
`conn_window` re-exports the name, because two checks import it from there and
moving a name is not the point of a split.

### Wrong turns worth keeping

- **The split broke five checks twice, for the same reason each time:** a moved
  function needs what it reads moved with it. First `berth_sim`, which
  `default_target` calls and the new module did not import. Then
  `DEFAULT_ORDER`, the constant it ranks contacts by, still sitting in
  `conn_window`. Both were invisible until the suite ran — the module imported
  cleanly either way, because the names are only touched inside the function.
  A split is not done when it parses.
- The comment block above `DEFAULT_ORDER` went with it. A constant whose
  reasoning stays behind in another file is a constant nobody will understand
  the next time it is questioned.

## One flight deck: the armed state moved onto the flight (2026-08-02)

The player's report was structural and it measured true: the pilot window,
the flight controls, the conn and the approach plot were four views holding
four private copies of the armed state. What was done, in one session:

- **`Conn.auto` / `arm_main` / `clock_on` / `mark`** — the armed mode, the
  drive selection, the clock and the laid course live on the flight now;
  every window reads them through properties, as `game.conn` itself is read.
- **One clock** — `ui/flight_clock.py`, `MainWindow.flight_timer` at 250 ms;
  `fly_beat` steers, flies, bills (`charge_flown`) and refuses to beat under
  a battle. Two open windows used to fly the ship at double time.
- **The autosave gate** was saving the whole sector on *every repaint*
  (`0 >= 0` at the default cadence) — ~30 ms under every button. Most of
  the reported sluggishness.
- **`win._flight_conn`** was read and never written: the Flight-controls
  window was blind unless the Conn window happened to be open.
- **`hand_over` at 0.000 km** — a moored hull's hand-over opened inside the
  structure and the first press "struck" it. It keeps the opening range
  inside radius + alongside.
- **Retargeting refunded the flight** — every swap now bills first
  (`ui/conn_moves.py`); a refusal keeps the old flight and says why.
- **#148/#149 closed** — mass billed as it burns (`charged_rcs`), commit
  exact; `berthing.secure_underway` settles a live conn before any transfer.
- **The control ladder ran per substep** — point defence bit up to 120x
  harder at a world than a quay. Per tick now.
- **#153 closed** — cameras say "Look …", one mode name per mode across the
  three windows, objectNames on every flight control.
- **`sim/flight.py`'s length debt paid** — `sim/path.py` took the arc, the
  heat and the risk. `tests/test_flightdeck.py` (9 checks) pins the lot.

## The second pass: the deck's own backlog (2026-08-03)

- **Transit parity** — `transit.finish` applies the arrival heat and rolls
  the risk the helm quoted (stored at commit; a recompute at arrival prices
  a zero-length leg). The orrery walks the hull along the leg by watches
  stood instead of parking it at the origin.
- **Bays flown** — `bays.approach_aim`: mouth-axis hold point, corridor as
  the phase test (not a distance race that flip-flopped a 40 t tank dry),
  and a go-around when the chord would cut the core. 0/6 → 16/16 alongside
  at a gestation shell/drum, on 1–2 t. `close` on a hull refused honestly.
- **The descent order** — Put her down / Belay the descent on the conn
  console; `sim/landing.py` finally reachable in play.
- **Conn panel sync** — `ui/conn_panel.py`, 18–21 ms a beat down to 2.8.
- **`engage.REACH_KM`** decoupled from `freeflight.far_km()`.
- **The two masses documented as two laws** (handling vs registry; up to
  six orders of magnitude apart across the fleet) rather than "fixed" into
  one number that would break either flying or ramming.

## The third pass: held engines, one clock, the HUD (2026-08-03)

- **Hold-to-burn** — a press was one instantaneous impulse; the pads and
  the new W/A/S/D, R/F keys are press-and-hold through one pair of doors
  (`flight_clock.start_burn`/`end_burn`), a standing order the beat
  consumes minute after minute. Speed builds; plumes stay lit; a quick
  click keeps the precise one-tick press and its quote.
- **Universal clock** — leaving a screen no longer stops it; HUD chip
  everywhere; helm Run/Stop; battle stops it immediately through both
  doors; time compression ×1/×4/×16 inside the one beat.
- **`ui/viewport_hud.py`** — predicted path (the approach window's dry run,
  in first person), prograde/retrograde, the aim point, a bay's mouth ring;
  the bridge mark carries the engagement band.
- Brake-to-zero; helm one-button computer docking; ninth tutorial lesson
  ("Take the ship's wheel", watched through billed `game.conn_seconds`).

## The fourth pass: one computer, the same bar everywhere (2026-08-03)

- **`sim/flightdeck.py`** — the computer's one front door (`computer`,
  `can_arm`), cut out of `freeflight` (which had also quietly doubled three
  functions from a backwards slice — deduplicated). The law stays in
  `sim/autopilot`.
- **`ui/autopilot_bar.py`** — Hold station · Brake to zero · Close and
  berth · Make orbit · Move away · Run for <mark> · Manual, identical on
  the Pilot, Helm, Conn, Flight-controls and Approach screens, all through
  `flight_clock.arm_mode`. Manual lit when nothing is armed.
- **"Depart" mode** — the same computer moves her away past the corridor,
  stops, and hands back. The system screen offers computer docking beside
  the hand-flown mini-game; the helm's dock button is the same door.
- **One transfer executor** — the plotting board's Engage flies the same
  watched crossing as the helm (was `travel_to`, the instant one).
- test_flightdeck grew to 14 checks; full suite green.

## The fifth pass: flown rigorously, three defects (2026-08-03)

Played every goal from every window, by hand and by computer. The coverage
gap that hid all three: `test_verbs` sweeps the 13 standing screens and had
never pressed a control in a *pop-out*. `test_flightops` sweeps all six.

- **A body conn opened already finished** — 8 of 11 seeds. `Conn.opened_orbiting`
  + `outcome.resolve`: an outcome is what a flight achieves, not its start.
  `autopilot.fly` writes the mode it flies onto `Conn.auto`.
- **"Move away" flew into the planet** — a radial demand in a gravity well
  asks the drive to cancel 2,779 m/s of orbit. Depart now climbs the ladder
  (or refuses with the reason and points at the picker/helm).
- **A held burn could outlive the hand** — no `released` reaches a destroyed
  widget. Rebuild, screen change and window close all call
  `flight_clock.end_burn(quiet=True)`.
- Verified sound: computer berthing from 5 surfaces, hand berthing from 3
  pads, orbit + rungs, run-alongside, depart from a structure, crossings
  from helm and plotting board (with arrival heat), berth→port disembark,
  landing once surveyed, engage from the bridge with the clock stopping and
  the gunner/tactical stations painting through the fight.

## The sixth pass: the tutorial becomes a curriculum (2026-08-03)

- **29 lessons in 10 chapters** (`data/lesson_types.py`, `lessons_early.py`,
  `lessons_late.py`, assembled by `lessons.py`), each course a scenario.
- **`sim/tutorial_watch.py`** — the mark, every watcher, and `deed`: the six
  acts that leave no state (computer flew, watch stood, seam worked, trench
  opened, party landed, fire opened) are recorded by the *sim function that
  performs them*, never by a button.
- **`ui/academy_panel.py`** — the Academy tab under Help: every course, what
  it teaches, progress, and "Teach me this" (`tutorial.jump_to`, which steps
  over what you can already fly).
- **Four manual pages on playing well**: your first hour, making money,
  flying her well, fighting and not fighting.
- Broad play-test also fixed: local work (survey/extract/dig/land) now
  secures a live hand-flight first, and the flight clock is held off the
  flight deck so shopping does not quietly cost days.

- **The crash only a full run could find**: exit 134, zero failures. Thirteen
  widgets build a raw `QPainter` and never had `ui/painting.py`'s guard; the
  approach view's painter died mid-frame and the TypeError escaped
  `paintEvent`. `painting.alive` (never began) + `@painting.safe_paint`
  (dies part-way) now cover all thirteen.

## The seventh pass: collision guard (2026-08-03)

- **`sim/collision.py`** — scan the target *and the sky*, measure room to the
  solid part, and answer "can she still be stopped" (`v²/2a`). Levels:
  clear · watch · brake · imminent. Measured at 60/30/20 km on a 40 m/s
  approach: clear, watch, imminent.
- **The computer brakes** — `flightdeck.computer` overrides whatever mode is
  armed when the room is running out (measured: burns −0.97 along the hazard
  bearing instead of the mode's own burn).
- **`Conn.safeties`** — one flag, a button on the conn console and the flight
  panel. Off: nothing brakes, nothing is refused. Deliberate orders (ditch,
  cut, a bay corridor) are silent without touching it.
- **The hand keeps its rope** — only a burn that worsens an *unstoppable*
  closure is refused, with the reason and the switch named.
- Warnings: a `Collision` panel row, a ringed box in the camera view, a log
  line. `tests/test_collision.py`, 5 checks.
