# Stream C · engine — map changes for INTERFACE.md

Review 2026-09-17, items #30–#35. What the project maps need to learn; the
maps themselves were not edited.

## New modules

| Module | What it holds | Split from / why |
|---|---|---|
| `core/shiptime.py` | `bench`, `hull`, `aboard`, `crew` — the day's phases on the ship's clock | `core/clock._one_step` (260 lines), #35 |
| `core/sectortime.py` | `holdings`, `economy`, `reckoning`, `settle_contracts` — the phases on the sector's clock | `core/clock._one_step`, #35 |
| `core/guard.py` | `swallowed(where, err)` — what a broad `except` does with what it was not for: re-raise under test, one stderr line in play | #33 |
| `data/works3d_parts.py` | the shared geometry constants, the part builders `_keel`…`_gantry`, `PARTS`, the berth points and `_berths` | `data/works3d.py` (635), #35 |
| `sim/expedition_gen.py` | `generate` (landing zone) and the haul: `haul_kept`, `landing_forecast`, `study_kept`, `STRANDED_SHARE` | `sim/expedition.py` (499), #35 |
| `sim/moorings_steer.py` | `aim`, `lead`, `where_at`, `berth_velocity`, `rates`, `steer` | `sim/moorings.py` (499), #35 |
| `sim/heliocentric.py` | `semi_major`, `period_days`, `elements_of`, `position`, `distance_from_star`, `separation`, `R_INNER/R_OUTER/YEAR_AT_1AU` | `sim/flight.py` (498), #35 |
| `sim/burn_incidents.py` | `_INCIDENTS`, `_incident` | `sim/flight.py`, #35 |
| `sim/diplomacy_acts.py` | `available`, `preview`, `refusal`, `perform`, `_spend`, `_work_key`, `_merged`, `_remember` | `sim/diplomacy.py` (500), #35 |
| `sim/sheer.py` | `SHEER_RATE`, `SHEER_FROM`, `sheers`, `sheer_step`, `sheer_line` | `sim/control.py` (487), #35 |
| `sim/orbit_heights.py` | the height ladder: `ORBIT_HEIGHTS`, `height_km`, `heights`, `heights_for`, `climb_dv`, `holdable`, `quotable`, `QUOTABLE`, `CLIMB_MARGIN`, `HEIGHT_TOLERANCE`, … | `sim/orbits.py` (485), #35 |
| `sim/shooting.py` | `_fire`, `_salvo`, `VARIANCE`, `DAZZLE_CAP` | `sim/combat.py` (482), #35 |
| `bridge/checks.py` | `Refused`, `whole`, `index`, `amount`, `words`, `ended`, `MAX_LINE` — argument validation at the protocol boundary | #30 |
| `bridge/battle.py` | the bridge's engagement: `begin`, `current`, verbs `fight` and `prize` | #30 (`jump` dropped its ambush) |

**Every moved name is re-exported from its old module**, so `works3d.DRUM_R`,
`exp_sim.generate`, `moorings.aim`, `flight.position`, `dip.perform`,
`control.sheer_step`, `orbits.heights_for` and `combat._fire` all still
answer. Where the new module needs something back from the old one it
imports it *inside the function* (the old module imports the new one to
re-export it, so the other direction at module scope is a cycle whichever
loads first); each new module's docstring says so.

Current sizes: `works3d` 239, `expedition` 393, `moorings` 333, `flight` 398,
`diplomacy` 177, `control` 420, `orbits` 221, `combat` 329, `clock` 274.

## Changed behaviour worth a line in the map

- `core/clock.advance_days` **raises `ClockReentered`** if called while the
  same game's day is running, and **`ValueError`** for a span that is not a
  finite number ≥ 0. No caller in the game nests (the full suite runs with it).
- `core/llm`: `complete()` never raises; a total `DEADLINE` (12 s); a
  circuit breaker (`COOL_OFF` 60 s doubling to 600 s; `cooling()`);
  `permitted()` — no socket without `SEEDFALL_LLM` set; `may_ask()` — the
  no-network test a window uses.
- `sim/voice.speak(..., wait=False)` returns the written line plus an `Ask`;
  `voice.model_line(ask)` is the thread-safe half. `sim/hail.opening()` is
  `greeting` for a caller that will not wait. `ui/comms_window` asks the model
  on a worker thread and swaps the line in when it arrives.
- `sim/exchequer.income` is memoised per input fingerprint (`_inputs`);
  `Exchequer.memo` is a transient field (never saved).
- The bridge: every verb's arguments validated (`bridge/checks.py`); verbs
  marked `acts=True` are refused once the chronicle has ended and while an
  engagement is open; `jump` opens an engagement that `fight`/`prize` finish;
  `waiting` reports it as `battle`; `shot` takes a bare `.png` name and saves
  into the temp folder only (`attached.shot_name`); a line is at most 64 KiB
  (an over-long one is drained and refused); `NaN`/`Infinity` refused at parse.
- `sim/` never imports `core.state` or `core.clock` at import time (checked:
  233 data/world/sim modules, one interpreter) — now pinned by
  `test_engine_guard`.
- Deleted as unreferenced: `Game.system_by_id`, `autopilot._against`,
  `solid._quad`. `xeno.__all__` no longer names the missing `known`.
  `telemetry.crew()["morale"]` reads `game.ship.morale` (it read a `Game`
  attribute that never existed, so always 1.0).

## New suites

| Key | Module | Checks |
|---|---|---|
| `bridgeguard` | `tests/test_bridge_guard.py` | fuzz of every verb × argument × hostile value (378 calls); the review's named cases; nothing acts after the end; an ambush is fought; line length and NaN at parse; `shot` names (Qt) |
| `llmguard` | `tests/test_llm_guard.py` | no request without `SEEDFALL_LLM`; 15 malformed replies over loopback; a hung endpoint costs one deadline then nothing; a mute socket; the comms window opens in ms against a hung model and takes the late line (Qt half skips without PyQt6) |
| `engineguard` | `tests/test_engine_guard.py` | re-entrancy refused and recovered; non-finite spans refused; income memo vs fresh sum through seven kinds of change; no sim→core.state/clock import; `guard.swallowed` loud/quiet; `__all__` names exist; crew gauge morale |

## Tripwire fast paths added (`tests/tripwire_kin.py`)

`works3d_parts`, `expedition_gen`, `heliocentric`, `sheer`, `orbit_heights`,
`shooting` — each the old module's suites, because each carries numeric
constants that moved (`test_harness_guard` requires a row).
