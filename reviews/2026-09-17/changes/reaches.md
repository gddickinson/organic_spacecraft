# Innovation 1 — The Far Reaches: what changed

Spec: `reviews/2026-09-17/innovations/01-far-reaches.md`. For the map
maintainer: nothing here edits `INTERFACE.md`, `IMPROVEMENTS.md`, `README.md`
or `SESSION_LOG.md`; this file carries what they need.

## New modules

| File | What it holds |
|---|---|
| `data/regions.py` | `VERGE`; `RegionSpec` and `REGIONS` (Shoals 12, Hollow 10, Cradle 14 — frame, rim, spacing, `link` reach, region star tables); `RULES`/`NEUTRAL` (the per-region rule table `sim/regions.rule` reads); `ROGUE_SHARE`, `RUIN_SHARE`, `PRECURSOR_RUIN`; Cradle `DOSE_MORALE`, `DOSE_TECH`, `DOSE_TECH_CUT`, `HEAT_SHARE`; relight bill `DEEP_TECH`, `RELIGHT_CREDITS`, `RELIGHT_GOODS`, `RELIGHT_DAYS`, `READ_METHOD`; `HOLLOW_RINGS`, `ANCHOR_NAMES`; condensate `CONDENSATE`, `NATIVE_GLUT`, `CONDENSATE_BUYERS`. |
| `world/regions.py` | `Region` (registered); `anchors(galaxy)` (the three rim sites, memoised on seed + Verge count); `heart(systems)` (Kessel's Reach by the generator's rule); `region`, `systems_of`; `span(galaxy, a, b)` — light years *through the deep gates*, the one door for prices/lags across the rim; `generate(galaxy, rid, day)` (scatter + `_connect` + bodies + ports + entry + Hollow rings, appended with id == index, names from their own stream so open order does not matter); `open_buyers(galaxy)` (condensate lines on Concordat/Dry Choir markets, own seeds). Docstring says how the Kith should add gatherings to an existing Cradle. |
| `sim/regions.py` | The hook API: `region_of(system)`, `opened(game)`, `rule(game, system, key)`, `names(game)`. One function per rule: `sensor_scale`, `survey_scale`, `lawless`, `claimable` (Shoals / claims), `light`, `lit` (Hollow), `dose`, `irradiate` (Cradle). |
| `sim/relight.py` | The project: `anchor_of`, `region_at`, `is_open`, `is_read`, `note_survey` (called by `survey.perform`), `bloom_risk`, `preview`, `can_relight`, `relight`, `standing`. |
| `ui/reaches_chart.py` | Chart helpers: per-region frame and systems, the sealed silhouette of an unopened region, deep-anchor diamonds and Hollow rings, the anchor tooltip. |
| `ui/reaches_panel.py` | The relight panel (System screen, at an anchor), the through/back gate panels, `beyond` (chart: a star past the rim), `sealed` (chart side panel for a dark tab), `codex` rows. |
| `tests/test_reaches.py` | Suite `reaches` (14 checks, below). |

## New saved fields (all defaulted; old saves load)

- `System.region: str = "verge"` (`world/galaxy.py`)
- `Galaxy.regions: list = []` of `world/regions.Region(id, name, w, h, anchor_id, entry_id, opened_day, rings)`
- `Body.sunless: bool = False` (`world/planets.py`) — a Hollow rogue
- `WeaveState.read: list = []` (`sim/weave.py`) — anchors read by a deep survey
- `Commodity.native: str = ""` (data, not saved)

No `Game` field was added (`core/state.py` untouched — it sits at 499 lines).
No new id kind: regions are keyed by their string id.

## Suite `reaches` (`tests/test_reaches.py`)

1. regions generate deterministically (both open orders give the same sky), and opening each leaves every Verge system byte-identical (hashed before/after, minus the condensate line on buyer markets);
2. the ancient Weave (sites, rings, dawn chain) is unchanged after opening all three, recomputed from cold;
3. cross-region distance is infinite; a 10,000 ly drive reaches no region system; `jump_to` refuses;
4. relight preview equals the act — credits, each material, days — through a real deep survey;
5. deep-gate transit both ways, ₡0, lands at the entry; Hollow rings lit;
6. efficacy, seven levers (Shoals sensor via `detection` and `survey.reach`, Shoals survey quality, Shoals lawlessness, Hollow dark air, Cradle dose → morale, Cradle heat);
7. shielding and a melanised rind cut the dose (1.00 → 0.60 → 0.33);
8. condensate: made at the havens, bought dear by the two powers;
9. save with all three open round-trips through a fresh process;
10. an old save (no `regions`, `region`, `sunless`, `weave`) opens a region;
11. the Bloom crosses a lit deep link at the Weave's pace (0 on day 29, >0.02 on day 30, 0 with the link shut);
12. endings stay the Verge's (victory progress identical with the whole Cradle overgrown; heart unmoved);
13. the Cradle is unclaimed, unported, and not claimable by a power;
14. ms/day with 0 vs 3 regions open (≤ 1.6x).

Also: `tests/suites.py` +1 row; `tests/tripwire_kin.py` +1 row (`"regions": ("reaches",)`).

## The audit: every iteration over `galaxy.systems`

"Include" = the Reaches take part. "Local" = the caller's own region (what
`distance` already allows; mostly to avoid walking the far side or mixing
coordinate frames). "Verge" = `galaxy.verge()`.

| Site | Decision | Why |
|---|---|---|
| `core/sectortime.economy` market tick | Include | Region markets tick; appended last, so Verge draws in the loop are unchanged. |
| `core/state._pick_start`, `validate` | Include (n/a) | Runs before any region exists; bound check is on the full list. |
| `bridge/protocol.neighbours`, `checks.index` | Include | Infinite distance filters itself. |
| `sim/beginning.start_system` | Include (n/a) | New game, Verge only by construction. |
| `sim/reach.component`, `routes_from` | **Local** | Same answer (nothing hops the rim), half the walk. |
| `sim/reach.walled`, `horizon` | **Local** | "N of M reachable" is out of this region's stars. |
| `sim/reach.sold_within`, `requirements.yards` | Include | Filtered by the (local) component. |
| `sim/intel.sellable` | Include | Region charts sell. |
| `sim/intel.summary` | Include (+ `systems=` arg) | Chart header passes the tab's systems. |
| `sim/intel.chart_price` | Include, **span** | Was `int(inf)` for a region chart bought in the Verge. |
| `sim/intel.in_sensor_range` | Include (+ Shoals scale) | |
| `sim/tutorial_watch` (4 sites) | Include | Deltas of surveyed bodies. |
| `sim/telepresence.gap_au` | Include, **span** | Was an infinite light-lag ("inf days round trip"). |
| `sim/legacy._rewrite` containment/exodus | Include | The Bloom is beaten everywhere. |
| `sim/legacy._rewrite` ruin | **Verge** | Ruin is the Verge's ending; the Reaches are not overgrown by it. |
| `sim/comms.lag_days` | Include, **span** past the rim | Was `due_day = inf`: news never arrived. |
| `sim/charts._reach` | Include, **span** | `WORTH["route"] * inf` was an infinite price. |
| `sim/passage.chart`, `lanes` | Include (n/a) | Filed at new game in the Verge. |
| `sim/enforce._system_by_id`, `gatetraffic.demand` | Include | Lookups. |
| `sim/ventures._claimable` | **Not past the rim** (`regions.claimable`) | Powers' reach is the Verge's; the Cradle is left for the Kith. |
| `sim/ventures._infested` | **Verge** | Flotillas burn the Verge's fire; a region's growth is lost ground. |
| `sim/ventures` blockade target | Include | First matching market (a Verge one first). |
| `sim/memory` prior memories | **Verge** | Pre-chronicle history; nobody had crossed the rim. |
| `sim/market.tick` shocks, `apply_to_markets` | Include | |
| `sim/accord.space`, `quays` | Include | |
| `sim/exchequer.holdings`, `_inputs`, `outlay`, `due` | Include | Region havens are independent, so the purses do not move. |
| `sim/settlement.sites_for` | Include | |
| `sim/actions.is_stranded` (`in_range`) | Include | Infinite distance filters itself. |
| `sim/actions.distress_call` (`nearest_port`) | Include, tie broken by **span** | A Cradle hull used to be towed to list-order's first port. |
| `sim/actions.jump_quote`, `jump_to` | Refuse past the rim | `transit_days(inf)` raised `OverflowError` (the chart's info panel called it). |
| `sim/weave.sites`, `_ring_order`, `_key` | **Verge**, keyed on Verge count | Opening a region must not re-sample the ancient gates. |
| `sim/telemetry` scope | Include (+ Shoals scale) | |
| `sim/freight.from_desk` | **Local** | A desk names its own power's quays this side of the rim. |
| `sim/freight.from_register` ly | Include, **span** | `round(inf)` crash once a region price was written down; `reachable` refuses a cross-rim run. |
| `sim/exchequer_ledger.summary`, `approach._shortage` | Include | |
| `sim/traffic.watched`, `armada.actions`, `war.spoils`, `biology.catalogue` | Include | |
| `sim/contracts._target` | Include (via local component) | |
| `sim/contracts._remember_done` | Include | Index lookup. |
| `sim/threat.bloom_systems`, `known_bloom`, `bloom_burden` | **Verge** | Containment / Ruin / stage pacing. |
| `sim/threat.tick` growth, carry, throws | Include | Throws are distance-bound; the stall "spear" refuses an infinite pair. |
| `sim/threat.tick` quarter/half beats, overgrown | **Verge** | "Sector lost" means the Verge. |
| `sim/threat.harbours_left` | **Verge** | |
| `sim/threat.victory_progress` (total, markets, register, drowned) | **Verge** | Endings are the Verge's. |
| `sim/piracy._reach` | **Local** | Raw `math.dist` across two frames; a region has no capital → lawless. |
| `sim/piracy.fence_pull` | **Local** | Same. |
| `sim/rumours.circulating` | **Local** | Provenance is a light-year count. |
| `sim/bloom.ensure` heart | **Verge** (`world/regions.heart`) | A region's frame could out-rank the far corner. |
| `sim/bloom._spawn_instar` | **Verge** | Instars are the Verge's Bloom. |
| `sim/bloom._retarget` | **Local** | A mass targeting across the rim was under way for ever. |
| `ui/star_chart` (3 sites) | Tab's region | |
| `ui/map_view._destinations` | Tab's region | |
| `ui/empire_view` Bloom census | **Verge** | Matches `known_bloom`. |

## Shared and other-owned files touched (one line per hunk)

- `core/shiptime.py`: import `regions_sim`; one line in `hull` (`irradiate`); `aboard`'s `air_ok` also asks `regions_sim.lit`.
- `sim/survey.py`: two imports; `reach` × `sensor_scale`; `preview` and `perform` quality × `survey_scale`; one line in `perform` (`relight_sim.note_survey`).
- `sim/detection.py`: `sensor_of` × `sensor_scale`.
- `sim/conn_open.py`: import; the two `array=` stamps × `sensor_scale`.
- `sim/piracy.py`: `_reach` local; `lawlessness` + `regions_sim.lawless`; `fence_pull` local.
- `sim/threat.py`: `import math`, `verge` import; `bloom_systems`, `known_bloom`, `bloom_burden` Verge; spear finite; beats Verge; overgrown Verge; `harbours_left` Verge; `victory_progress` Verge (3 hunks).
- `sim/bloom.py`: `import math`; `ensure` heart; `_spawn_instar` Verge; `_retarget` local.
- `sim/reach.py`: import; `component`, `routes_from`, `walled`, `horizon` local.
- `sim/intel.py`: `in_sensor_range` scale; `chart_price` span; `summary(game, systems=None)`.
- `sim/comms.py`: `lag_days` span past the rim.
- `sim/charts.py`: `_reach` span.
- `sim/memory.py`: prior memories Verge.
- `sim/ventures.py`: `_claimable` claimable; `_infested` Verge.
- `sim/actions.py`: `jump_quote` beyond-the-rim quote; `jump_to` refusal; `distress_call` passes the galaxy.
- `sim/freight.py`: import `span`; `from_register` ly by span; `from_desk` local; `reachable` refuses cross-rim.
- `sim/rumours.py`: `circulating` local.
- `sim/legacy.py`: Ruin rewrite Verge.
- `sim/telepresence.py`: `gap_au` span.
- `sim/telemetry.py`: scope reach × scale.
- `sim/inquiry.py`: import `TECH_MIX`; `mix_for` reads it first.
- `sim/manual.py`: one `@fact("reaches")` block before "reading a topic".
- `data/tech.py`: one node, `deepweave` (xenology tier 3, reqs xenobiology + mea, 560).
- `data/inquiry.py`: `TECH_MIX` after `DEFAULT_MIX`.
- `data/help.py`: two topics appended (`reaches`, `deep-gates`).
- `data/starclasses.py`: `T`, `BG`, `O` appended to the dict.
- `data/commodities.py`: `Commodity.native` field; `condensate` appended.
- `data/gates.py`: `deep` and `inner` appended to `GATE_KINDS`.
- `world/economy.py`: `NATIVE_GLUT` import; `make_market` skips a non-native good before any draw; `add_line`.
- `world/planets.py`: `Body.sunless`.
- `world/galaxy.py`: import; `System.region`; `Galaxy.regions`; `distance`; `verge`; `local`; `nearest_port(…, galaxy=None)`.
- `sim/weave.py`, `sim/gates.py`: owned (deep gates in `network`, `anchor_at`, `deep_gates`, `deep_links`; free toll, span, `bloom_links`).
- `ui/star_chart.py`: import; `region` attr; `_projection` frame; `_pick`; tooltip in `mouseMoveEvent`; paint: sealed early-out, tab's systems, **one line** `reaches_chart.draw_deep(self, p, g)` after `self._draw_weave(p, g)`; `_draw_weave` Verge only. The paint is otherwise the shape it was — the nemeses overlay can go next to `draw_deep`.
- `ui/map_view.py`: imports; `region`/`_aboard` state; `_show`, `_tabs`; header per tab; sealed side panel; destinations per tab; `_step` follows the region; `_info` beyond-the-rim panel; legend entry.
- `ui/system_view.py`: 4 lines hosting `reaches_panel.build`.
- `ui/weave_panel.py`: `anchor_at` instead of `gate_at`.
- `ui/codex_view.py`: star-count note computed; a "The Far Reaches" grid on the sky tab.
- `ui/empire_view.py`: Bloom census total from `known_bloom`.
- `tests/suites.py`: +1 row. `tests/tripwire_kin.py`: +1 row.

## Measurements

See the report (and `scratch-reaches/campaign/` for the bots).
