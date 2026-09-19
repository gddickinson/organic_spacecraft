# Innovation 7 — Stellar phenomena (a living sky)

## Why

The sky is static:
- stars never change;
- the only time-varying events are market shocks, ventures and the Bloom.

Exploration has nothing to *come back for* once a system is surveyed, which is
part of the mid-game stall the play-test measured. The GESTALT documents make
the space environment a design driver (flares, radiation, micrometeoroids,
thermal cycling); the game should too.

## What the player gets

**Timed, forecast events on systems.** Each changes what a place is for a
while, and each is **observable science**.

| Phenomenon | Where | Duration | Effect | Opportunity |
|---|---|---|---|---|
| **Stellar flare** | M/K dwarfs mostly, any star | 1–5 days | crew radiation dose unless sheltered (in the shadow of a body, or at a berth); sensors +; comms delay (despatches slow) | observe: evidence; the Charter buys the data |
| **Comet passage** | any system with an outer body | 60–200 days, rising then passing | a new transient body: an ice-rich comet you can mine for volatiles and phosphate; a volatile glut at nearby markets (a shock) | a mining window |
| **Ion storm** | the Shoals mostly, the Verge rarely | 3–15 days | lanes into and out of the system are closed (jump refused, with a reason); survey resolution down | ride it out; observe |
| **Nova** | the Cradle, rare; a single slow event per chronicle | 120–300 days of brightening, then the burst | a mounting dose within a radius, then the burst: the system is scoured (bodies stripped, ports evacuated) and a remnant is left (`data/remnants.py`) | observers early are paid in unique evidence; the Choir pays a fortune for burst data taken from a safe distance |
| **Rogue flyby** | any; the Hollow more | 30–90 days | a sunless body passes through: new survey targets, rare relics | a transient survey and relic target |
| **Aurora season** | gas giants and magnetised worlds | 20–60 days | atmosphere dives are safer and yield more | a diving window |

- **Forecast honestly.** Most phenomena are announced on the despatch board
  before they begin, with lead time and confidence ("the Charter observatory
  at X forecasts a flare at Y within 6 days, 70%"). Better sensors and a CHORUS
  node give longer and better forecasts.
- **Observe** is a new act at a live phenomenon. It spends days and gives
  **phenomena** evidence, a new evidence kind for the research bench
  (`data/inquiry.py` kinds). It feeds relevant tech nodes (sensors, radiation
  shielding, Deep Weave) and is sellable as data to the Charter and the Dry
  Choir, priced by rarity.
- **Shelter** during a flare: stand behind a body (the ship's position against
  the star) or be at a berth, and the dose is avoided. The Helm/Pilot
  screens show a shadow indicator.

## Design

- **Content:** `data/phenomena.py` holds the kinds, their rates by star class
  and region, durations, effects and evidence yields.
- **Rules:** `sim/phenomena.py` covers:
  - scheduling: a per-system, per-season deterministic RNG key, so the sky is
    the same whoever looks, and viewing never changes it;
  - the forecast (to comms);
  - start and end;
  - `active(game, system)`;
  - effects, one door each: `dose(game)`, `lane_closed(game, a, b)`,
    `transient_bodies(system)`;
  - `observe(game)` with a preview;
  - the data sale price.
- **State:** `Game.sky: object | None = None` holds a registered `SkyState`:
  active and forecast phenomena, observed ones (for the codex), and nova
  progress.
- **Transient bodies:** comets and rogues are added to a system's body list
  with a `transient_until` field. `Body` gets a defaulted
  `transient_until: int | None = None`. They are removed when they pass, and
  anything referencing them is cleaned up: rigs, orbits, contracts. That is
  the delicate part. Test that the ship in orbit around a departing comet is
  moved to stand off with a log line.
- **Readers:** the dose goes to crew health through `lifespan`/`upkeep` or
  morale, in one place. Lane closure goes in `actions.jump_to` and the quote,
  plus `reach`. Survey resolution goes in the survey module. Market gluts
  reuse `market.Shock`. Sensor bonuses go in `detection`/`telemetry`.
- **Clock:** `phenomena.tick(game, n, r)` in sector time.
- **Regions:** read `System.region` (innovation 1) for regional rates: ion
  storms in the Shoals, the nova in the Cradle, rogues in the Hollow.

## UI

- **The Sector Chart** marks active and forecast phenomena with an icon and a
  ring coloured by kind.
- **The System screen** gets a "Sky" strip: the active phenomenon, its time
  left, its effect in words, and Observe with a preview.
- **The Pilot/Helm** get a flare shelter indicator.
- **Despatches** carry forecasts.
- **Codex:** "Observed phenomena".

## Balance targets

- About one notable phenomenon per 20–40 days somewhere within 2 jumps.
- A flare unsheltered costs a crew about 1–3% of a hand's health or a morale
  hit, never a sudden death.
- The nova is a chronicle-scale set piece: at most one per game, forecast at
  least 60 days ahead.
- Observation evidence helps research without trivialising the tree:
  about +10–20% on relevant nodes for a captain who chases phenomena.

## Tests (new suite `test_phenomena`)

- Schedules are deterministic, and opening the chart doesn't change them.
- Forecasts precede events with the stated lead.
- Each effect moves its number (efficacy).
- Sheltering avoids the dose.
- Lane closure refuses the jump with a reason, and reopens.
- A comet appears, can be mined, and leaves cleanly (rig and orbit cleanup).
- A nova builds and bursts, the remnant is right, ports are evacuated, and
  there are no dangling references.
- Observe equals its preview.
- The data sale is priced by rarity.
- Cross-process save during an active phenomenon.
- Performance: the tick cost with all regions open.

## Notes from Wave A (read before building)

- Regions exist: `System.region` in {"verge","shoals","hollow","cradle"};
  `sim/regions.region_of/opened/rule`. Regional rates key off these.
  Unopened regions have no systems yet — phenomena there begin when opened.
- The Cradle already applies a dose and a heat floor (`sim/regions.irradiate`,
  called from `core/shiptime.hull`). A flare dose should go through the same
  door or sit beside it, and **must multiply by `adaptation.dose_multiplier`**
  (the living hull's melanised rind / glare mantle). Flares should feed the
  living hull's `glare` channel (`adaptation.record(ship, "glare", days)`).
- Sound: add cues for a flare warning and a nova (rows in `data/sounds.py`,
  a hook in `ui/soundmap.py`) if cheap; the façade is `ui/audio.py`.
- Market gluts reuse `sim/market.Shock`; lane closure must also be honoured
  by freight lines' routing (`sim/lineroute.py`) and the deep gates
  (`sim/gates.py`).
