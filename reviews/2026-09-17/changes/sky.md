# Innovation 7: Stellar phenomena (a living sky)

Spec: `reviews/2026-09-17/innovations/07-phenomena.md`. Nothing here edits
`INTERFACE.md`, `IMPROVEMENTS.md`, `README.md` or `SESSION_LOG.md`. This file
carries what they need.

Six kinds of phenomena: stellar flare, comet passage, ion storm, rogue flyby,
aurora season, and the nova (once per chronicle, in the Cradle). All of them
are scheduled from `RNG(f"{seed}:sky:{system}:{season}")` with 90-day seasons.
None of them draws from the chronicle's luck. The Charter observatory forecasts
them on the despatch board, with an honest confidence. Each one can be
observed, which yields *phenomena* evidence, and the data sells to the Charter
and the Dry Choir.

## New files

| File | Lines | What it holds |
|---|---|---|
| `data/phenomena.py` | 303 | The `Kind` table (days, lead, share that come true, evidence, value, watch days, effect, blurb) and the rates by star and region. Also every effect's number, the transient bodies, the nova, the forecast, observing and selling, the bench `FEEDS`/`UPLIFT`, and the despatch words. |
| `sim/phenomena.py` | 457 | The front door. It holds the registered `SkyState`, `Observation` and `NovaState`, and the derived `Event`. It also holds the schedule (`planned`, `season_map`, `upcoming`, `active`, `live`) and one door per effect: `dose`/`irradiate`, `shelter`, `keep_lee`, `exposed`, `lane_closed`/`closed_systems`, `sensor_scale`, `survey_scale`, `comms_delay`, `aurora_yield`/`aurora_risk`, `transient_bodies`, `visible`, `forecasts`, `tick` and `progress`. |
| `sim/phenomena_tick.py` | 68 | The day: bodies in and out, telling the captain once per event, the forecast, clearing the lee. |
| `sim/phenomena_forecast.py` | 109 | `chorus`, `discrimination`, `lead_scale`/`lead_days`, `confidence`, `reported`, `pending` and `issue`, which sends the despatch. |
| `sim/phenomena_bodies.py` | 226 | Comets and rogues: `make`, `arrive`, `leave` and the clean-up (`can_leave`, `_clear`), plus `gluts`/`glut_on`, the comet glut derived as `market.Shock`s. |
| `sim/phenomena_shelter.py` | 152 | Shelter: a berth, the lee, the shadowed share of an orbit, or the umbra cone in free space. Also `lee_quote`, `keep_lee` and `spend_lee`. |
| `sim/phenomena_nova.py` | 217 | `ensure` (chooses the nova once the Cradle opens), `event`, `phase`, `fraction`, `dose_at`, `burst_visible`, `tick` and `burst`. The burst recasts the system through `data/remnants.NEUTRON`, evacuates the ports and settlers, scours holdings back to seed, and scours the hull if it is there. |
| `sim/phenomena_science.py` | 153 | `observe_quote`, `observe` (preview equals act), `price`, `sale_quote`, `sell` (through `wharfage.collect`). |
| `ui/sky_strip.py` | 208 | The System screen's Sky strip. It also holds the shelter row on the Pilot board, the Helm panel with its lee button, the codex's "Observed phenomena" and the sound hook. |
| `ui/sky_chart.py` | 60 | The chart overlay: a ring and glyph per visible phenomenon (dashed for a forecast), and the nova's dose radius. |
| `tests/test_phenomena.py` | 394 | Suite `phenomena`, 11 checks. |
| `tests/test_skybodies.py` | 176 | Suite `skybodies`, 3 checks: comet, rogue, nova. |
| `tests/test_phenomena_ui.py` | 176 | Suite `phenomenaui` (Qt), 4 checks. |
| `tests/phenomena_kit.py`, `tests/phenomena_levers.py` | 80, 244 | Scenes are found in the seed's own sky and never forced. There are 15 efficacy levers. |

## Saved state (all defaulted, and old saves load)

- `Game.sky: object | None = None`, appended last. It holds a
  `sim/phenomena.SkyState`: transients (event id → [system, body id]), told,
  forecast, observed (`Observation`s), lee, and nova (`NovaState`).
- `Body.transient_until: int | None = None`, in `world/planets.py`.
- The schedule itself is never stored. It is derived from the seed, and
  memoised per season.

## The design, in brief

- **Schedule.** Each kind draws the same 7 numbers per season whether it
  happens or not, and `KINDS` is append-only. A comet or rogue may start only
  one season in three per system, and only in its first 60 days. With comets
  lasting at most 200 days, a system never holds two transients, and the one
  it holds is always last in the list. A region's stars have no events before
  the day it opened.
- **Honest forecasts.** The schedule holds candidates, and `Kind.real` of them
  come true. The forecaster drops `discrimination` of the false alarms (from
  scan and a CHORUS Node) and states `real / (real + kept false alarms)`. The
  forecast is issued `lead × (1 + scan + 0.5·node)` days ahead, for stars
  within two jumps' range, and is sent from where the hull is.
- **Comet gluts are derived, not stored.** A stored glut took a
  `MAX_PER_SYSTEM` slot. That moved the market's onset roll, and so the luck
  of the whole chronicle: two idle years shifted a Concordat purse from
  45,500 to 20,900, and flipped three unrelated long fixtures. With derived
  gluts, an idle chronicle is byte-identical in its purses and politics to
  one with no sky at all (measured on 6 seeds over 2 and 10 years).
- **Transient clean-up.** When a transient leaves:
  - a hull in orbit stands off, with a log line;
  - a trench is backfilled;
  - a party is recalled;
  - survey postings are cut to the bodies that are left;
  - the knock, the lee and any landed conn are dropped.

  Holdings, settlers, landings and ground postings refuse transients outright.
  A flown conn, or a crossing under way to the body, makes it wait (settling
  either would advance the clock from inside the day). `flight.travel_to`
  refuses a flight that would arrive after the body has gone.

## Suites

- **`phenomena` (11 checks):**
  1. The sky is the seed's, every reader leaves the save byte-identical, and
     the tick leaves the chronicle's luck untouched.
  2. Forecasts arrive within their lead and never after the event starts.
     Stated confidence matches the observed rate: 83% stated, 87% came true,
     over 241 forecasts.
  3. Sensors and a node lengthen the lead and raise the confidence.
  4. Shelter works: a berth or a lee takes the whole dose, an orbit a share,
     and the lee burns its fuel. The umbra geometry is checked too.
  5. An unsheltered flare costs 1.5–3.0% of morale and no lives.
  6. The efficacy levers (15).
  7. A storm refuses the jump, reach, a freight line and a ring, with a
     reason, and then reopens.
  8. Observe equals its preview, and the price ladder follows rarity. The
     Choir pays more for burst data, the first of a kind earns a premium, and
     nothing sells twice.
  9. A save made mid-comet survives a fresh process, and an old save loads.
  10. The research uplift: +17% on the melanised rind, 0 on a node it does
      not feed.
  11. Performance with every region open.
- **`skybodies` (3 checks):**
  1. The comet: it is mined, gluts the quays, refuses a holding and a
     too-late flight, stands the hull off, and leaves no references behind.
  2. The rogue: its trench, a crossing to it and a live conn are all settled
     or waited on.
  3. The nova: it cannot happen before the Cradle opens, is forecast 286 days
     out, has a mounting dose, becomes a neutron star, evacuates the quay,
     gets observed brightening and as a burst, and there is only ever one.
- **`phenomenaui` (4 checks):**
  1. The strip and Observe, at both sizes.
  2. The chart overlay's pixels, with building five screens leaving the sky
     unchanged.
  3. The Helm panel and its lee button, and the Pilot showing "sheltered".
  4. The forecast despatch, the codex, and the flare and nova cues heard once
     each.

## Shared and other-owned files touched (one line per hunk)

- `core/state.py`: `sky` field appended after `assembly`.
- `core/sectortime.py`: import `phenomena as sky_sim`; one line
  `sky_sim.tick(game, n, r)` at the top of `economy`.
- `core/shiptime.py`: import; one line `sky_sim.irradiate(...)` after
  `regions_sim.irradiate`.
- `world/planets.py`: `Body.transient_until` (4 lines with its comment).
- `sim/regions.py`: `dose` now calls a new `shield(game, stats)` (the same
  guard, rind and `dose_multiplier` arithmetic, extracted so a flare shares
  the one door).
- `sim/actions.py`: import; `jump_quote` gains a `closed` key; `jump_to`
  refuses on it; `extract` refuses a stale index (a departed comet); the
  aurora yield in `take`; the aurora risk in `dive`.
- `sim/reach.py`: import; `component` and `routes_from` skip storm-shut
  systems (2 hunks each). `lineroute` inherits this through `routes_from`.
- `sim/gates.py`: `quote` refuses a hop with a storm at either end, and that
  reason comes first.
- `sim/survey.py`: import; storm `survey_scale` in `preview` and `perform`;
  `system.scanned` ignores a passing body.
- `sim/detection.py`: `sensor_of` × `sky_sim.sensor_scale`.
- `sim/telemetry.py`: `scope` reach × `sky_sim.sensor_scale`.
- `sim/comms.py`: `send` adds `sky_sim.comms_delay`.
- `sim/market.py`: import; `factor`, `apply_to_markets` and `note_prices`
  read the derived comet gluts.
- `sim/inquiry.py`: `draw` × `_uplift`, a new private function reading
  `data/phenomena.FEEDS`.
- `sim/flight.py`: `travel_to` refuses a flight that arrives after a
  transient body leaves.
- `sim/anchorage.py`: `anchor_body` ranks transients last; `gate_body` never
  picks one.
- `sim/colony.py`: `can_found` refuses a transient body.
- `sim/settlement.py`: `sites_for` skips a transient body.
- `sim/landing.py`: `kind_allows` refuses a transient body.
- `data/inquiry.py`: `Evidence("phenomena")` appended. It is in no branch mix:
  it is a bonus, never a requirement.
- `data/shocks.py`: `COMET_GLUT` appended, outside `SHOCKS` and added to
  `SHOCKS_BY_ID`.
- `data/sounds.py`: two cues appended, `flare` and `nova`.
- `data/help_more.py`: topic `phenomena` appended.
- `ui/soundmap.py`: in `hud`, a lazy import and `sky_strip.sound(win, ear)`.
  The import is lazy because a top-level one is circular through
  `widgets`.
- `ui/star_chart.py`: import `sky_chart`; one line after
  `hunt_marks.draw_sightings`.
- `ui/system_view.py`: four lines hosting `sky_strip.build` after the
  reaches panel.
- `ui/helm_view.py`: four lines hosting `sky_strip.shelter` under the head.
- `ui/pilot_panels.py`: import; one `sky_strip.shelter_row` line in
  `ship_board`.
- `ui/codex_view.py`: two lines in `_sky`, after the Far Reaches grid.
- `tests/suites.py`: three rows appended (`phenomena`, `skybodies`,
  `phenomenaui`).
- `tests/tripwire_kin.py`: row `"phenomena": ("phenomena",)`.
- `tests/captain_bot.py`: the naive captain waits out an ion storm instead of
  breaking on the refused jump. Its stall check failed once at day 74 before
  this change.

## Measured against the balance targets

The bots are in `scratchpad/scratch-sky/campaign/skybots.py`: the four
strategy bots plus a phenomena chaser, each for 3 years on s1, s2 and s3,
with integrity checked after every turn.

- **Notable phenomena within 2 jumps.** On the bots' own paths the median gap
  is 23.8 days (15 careers; 18.6–33 days, and 72 days in one short fighter
  career). Measured statically from every system: a median of 30–39 days.
  The target is 20–40 days. Two changes got here: aurora was eased from
  0.25 to 0.18 (it was 21 days), and comets from 0.30 to 0.12 per slot.
- **Flare cost.** Unsheltered: a mean of 1.1% of morale per flare in play
  (n = 48, max 3.0%). Measured by twins in the suite: 1.5–3.0%. Sheltered
  (a berth or the lee): 0. No flare ever cost a life. The lee costs 0.4 t of
  reaction mass a day.
- **Comet mining.** In 24 chaser sessions of 20 days on an opening NAVIS:
  17.4 t of volatiles (max 23) and 0.69 t of phosphate (max 1.85) each. The
  NAVIS's phosphate rig is 0.1; a passing comet grades 0.30–0.60 in
  phosphate, against 0–0.10 for a resident one.
- **The chaser's research uplift.** A time-weighted multiplier of 1.122–1.147
  on the feeding programmes (+12–15%), with all five sensor and shielding
  nodes it reached unlocked. It made 8–15 observations and sold ₡0, ₡28,639
  and ₡21,068 of data (s1 had no buyer port in reach). The suite's direct
  measure: +17% on the melanised rind, and 0 on nodes the sky does not feed.
- **Cost of the day.** With all three regions open (78 systems): 0.97 ms
  against 0.83 ms with the whole sky switched off (1.17x). Verge only: 0.86
  against 0.74 (1.16x). The suite bound is 1.3x; it measured 1.21x under
  `-j 4`.
- **Integrity.** 0 exceptions and 0 integrity violations across 15 careers
  (at most one transient per system and always last; no orbit, colony, dig or
  contract pointing at a missing body; every transient recorded). 436
  transients arrived, 400 left and none was deferred. The rest were still
  passing at the end.
- **Idle chronicles are unchanged.** With the sky on, powers' purses after 2
  idle years and worst relations after 10 are identical to the sky switched
  off.
- **The sky against the baseline in play.** Deaths and purses fall within
  seed noise: fighters died in 3 of 3 runs either way, traders ended broke
  either way, and explorers ended on 77k/79k/58k against 75k/78k/50k.

## Deviations, each with its reason

- **Aurora.** The game has no atmospheric dive (the living-hull stream found
  the same). An aurora season raises extraction at gas giants and magnetised
  worlds (×1.35) and halves the risk of the one dive there is. Both are
  measured by levers.
- **A flare costs morale, not a hand's health.** Crew are a count, and
  officers have no health. This is the spec's "or a morale hit".
- **Forecasts are sent from where the hull is**, so they arrive at once
  (plus a flare's delay). Sent from the star by the comms law, at 11 days a
  light year, a 3-day flare warning would arrive weeks late.
- **Comet gluts are derived, not appended to `Game.shocks`**, for the
  measured reason given above. They are still `market.Shock`s through
  `market.factor`, and the register marks them.
- **Freight lines honour storms through `reach.routes_from`**, which
  `lineroute.path` walks. `lineroute.py` itself is not edited, and the suite
  checks `lineroute.path` returns None.
- **Transients: prevention first.** Landings, ground postings, holdings and
  settlers are refused on a transient rather than cleaned up afterwards (a
  party already down is still recalled). A live conn or a crossing makes the
  body wait, and `travel_to` refuses a flight that would be too late.
- **The nova's holdings are scoured back to seed, not deleted**, so no
  colony id dangles. Founding a holding in a brightening system is not
  refused (not done). The Cradle has no ports by construction, but any port
  there is evacuated (tested by planting one).
- **Observe and the sale live in `sim/phenomena_science.py`**, not behind
  wrappers in `sim/phenomena.py`, which is at 457 lines.
- **Not done:**
  - a legend entry for the chart's rings;
  - naming the phenomenon in the picked-star panel on the Sector Chart;
  - the Choir's premium applies to burst data only.
- **Pre-existing, not mine.** At 1040×680 the despatch board clips a
  two-line body after the window has visited other screens. It reproduces
  with the sky off and plain despatches
  (`scratch-sky/shots/baseline-despatch2-1040x680.png`).

## For the maps (not edited here)

- **Layout rows:**
  - `data/phenomena.py`: the living sky's table.
  - `sim/phenomena*.py`: the schedule and one door per effect, the tick, the
    forecast, transient bodies, shelter, the nova, observing and selling.
  - `ui/sky_strip.py` and `ui/sky_chart.py`.
  - Tests: `test_phenomena` (11), `test_skybodies` (3), `test_phenomena_ui`
    (4), `phenomena_kit`, `phenomena_levers`.
- **For renown:** `phenomena.progress(game)` returns `{"observed", "kinds_seen",
  "nova"}`. The nova is one of "unknown", "brightening", "burst" or
  "watched".
