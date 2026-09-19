# Stream A · rules — module-level changes for the maps

For folding into `INTERFACE.md`, `seedfall/INTERFACE.md` and `SESSION_LOG.md`.
Review items #9–#20 (`reviews/2026-09-17/seedfall.md`).

## New modules

- **`sim/stores.py`** (#20) — the one door for "what the captain has to hand":
  `held(game, key)` (credits, or depot + hold), `lacking(game, cost)` →
  `[(key, need, have)]`, `take(game, key, amount, hold_first=False)` → shortfall,
  `spend(game, cost)`. **Materials come out of the depot first**; only the
  crew's eating (`upkeep`) and a carried delivery (`contracts`) pass
  `hold_first=True`. Replaces the copies in colony, shipyard (`pay` removed;
  `affordable` now wraps `lacking`), works, gates, diplomacy, dormancy, mining,
  robots, survey, reach, upkeep and contracts (`_take_cargo` removed).
- **`sim/passage.py`** (#15) — a boxed-in opening's way out. `chart(game)` is
  called once by `core/state.new_game`; while the start pocket holds fewer than
  `MIN_POCKET` (8) systems or `MIN_POWERS` (2) powers' ports it files a
  *charted lane* across the shortest gap (both ends' `System.lanes`), and logs
  it. `joined(a, b)`, `lanes(game)`, `note(game)`. Read by `reach.component`,
  `reach.routes_from`, `reach.note` and `actions.jump_quote` (a lane is in range
  at any drive). Galaxy generation is untouched; wide openings get nothing.

## New saved fields (all defaulted; old saves load)

| Class | Field | Meaning |
|---|---|---|
| `sim/ship.Ship` | `launched_on: int \| None = None` | day a slip/cradle of yours launched her (`shipyard.tick_builds`) |
| `world/planets.Body` | `survey_q: float = 0.0` | best survey quality achieved |
| `world/planets.Body` | `surveyed_on: int = -1` | day last surveyed |
| `world/galaxy.System` | `lanes: list = []` | charted-lane partners (`sim/passage`) |
| `world/economy.Market` | `yours: dict = {}` | cid → [tonnes bought here lately, day] (`sim/trade`) |
| `sim/market.Quote` | `shocked: dict = {}` | cid → day the shock that moved it ends |
| `sim/contracts.Contract` | `taken_on: int = -1` | day accepted (also set by `chains`) |
| `sim/approach.Envoy` | `aside_until: int = -1` | day a set-aside envoy asks again |
| `sim/research.Research` | `starve_said: list = []` | the shortage the log was last told |

Non-saved: `freight.Run.shocked` (flag) and `voyage()["shocked"]`;
`survey.preview()["charts"]` (whether a look would chart anything).

## Changed rules, by item

- **#9 Lineage** — `threat.line_of(game)`: grown, `launched_on` set, not in
  `LINEAGE_EXCLUDES` (`spore`), flown `LINEAGE_AGE` (365) days. Victory reads it.
  `shipyard.start_build` asks `enforce.may_seed` for gestated families. Goal text
  in `data/lore` updated. Earliest Lineage: day 21 → day 515 (unlimited money).
- **#10 Re-sweeps** — `world/planets.survey_body(..., day=None)`: a charted body
  pays only for new finds plus the base chart pro rata to a gain of at least
  `SHARPER_BY` (0.05); stamps `survey_q`/`surveyed_on`. `survey.perform` grants
  science XP only when something was learned. `trade.sell_survey_data` calls
  `apply_sale`.
- **#11 Standing** — `trade.BOUGHT_MEMORY` (60 d), `trade.imported(...)`:
  standing, `trade_profit` loyalty, survey-sale standing and bench research are
  granted only on tonnes this counter did not sell you lately.
- **#12 Bloom** — `threat.tick`: a sector pace (`THROW_RATE` 0.30 footholds a
  month × √stage spread × provocation) shared by throws, instars and the Weave;
  instars now move *before* the throws; `THROW_AT` 0.35. `data/bloom` stages
  keep 0/0/1/2/3 instars (were 0/0/2/3/5); new beat `quarter_the_verge`.
  `threat._harbour_lost` sends a "Sector bulletin" despatch when a quay drowns.
- **#13** — `aftermath.resolve` calls `game.die` on "lost" (returns `died`);
  `ui/battle_view._finish` no longer kills.
- **#14** — `data/approaches.GRACE_DAYS` (60), `SET_ASIDE_DAYS` (10);
  `approach.holds(game)`, `set_aside(game, envoy)`, `set_aside_terms(...)`.
  `window.go()`'s envoy branch and `clock._awaiting_answer` ask `holds`.
- **#16** — `colony.can_found` asks the licence; survey commissions count
  `surveyed_on >= taken_on`; `market.SHOCK_SPENT` (0.25), `shock_discount(...)`
  and `best_markets` row `shock_until`; `freight.from_register` discounts a
  quote whose shock ends before arrival; `research.shortage_news(res, done)`
  (the bench's shortage is logged once per spell, and `clock` no longer draws
  a quarter-chance for it).
- **#17** — `core/util.spelled(n)`; `data/factions.THE_POWERS`, `KIN`; tutorial
  and ending text compute counts; lesson "sell" asks for the hold, not survey
  data; Apostasy fires at Kin (70, was 75); Concord's card names the six pairs.
- **#18** — `consorts.can_take_command`, `take_command_terms`, `take_command`:
  what fits crosses (food, then reaction mass, then dearest per tonne); the rest
  stays aboard the old hull. `ui/yard_view._switch_ship` calls it.
- **#19** — `contracts.board_for` seeds each board from
  `RNG(f"{seed}:board:{sid}:{day // turnover}")`, never `game.rng`.

## New suites (`tests/suites.py`)

- `exploits` → `tests/test_exploits.py` (10 checks, ~1 s).
- `rulebook` → `tests/test_rulebook.py` (8 checks, ~5 s).
- `tests/tripwire_kin.py`: `passage` → rulebook; rulebook/exploits added to
  approaches, approach, survey, market, bloom, threat, trade.

## Checks updated because a change intentionally moved what they pinned

`test_play` and `test_legacy` (Lineage fixtures stamp `launched_on`),
`test_sim` (lifts a licence suspension before the build check), `test_missions`
(stamps `surveyed_on`), `test_ticks` (envoy sweep starts after the grace),
`test_time` and `test_war` (harbours held open so a career/a war decade is
measured, not the Bloom), `test_exchequer` (growth check over four sectors),
`tests/captain_bot` (a broke captain flies to a counter),
`tests/chronicle_fights` (the patron refloats the chronicle after a lost fight),
`test_ui` ("every screen survives a developed game" waits until its colony is
online instead of a fixed 200 days, by which the Bloom now takes that system).

## Merge note — `core/clock.py`

Two hunks, both to be carried into stream C's phase modules by hand:
1. `_awaiting_answer`: the envoy is asked through `approach_sim.holds(game)`
   (a set-aside envoy does not stop a wait); `demand`/`situation` unchanged.
2. The bench block in `_one_step`: the `if starved ... if r.chance(0.25):
   add_log(...)` lines become `short = research_sim.shortage_news(game.research,
   done)` / `if short: game.add_log(...)`. This removes one draw from the
   step's `rng("tick")` stream, which is intended.

## For other streams

- **Interface**: `survey.preview()["charts"]` can grey or relabel a repeat
  sweep; `freight` rows carry `shocked`; `approach.set_aside_terms` is on the
  envoy screen. The chart could draw `passage.lanes(game)`.
- **Engine**: `bridge/protocol.waiting` still reports a set-aside envoy as
  blocking (use `approach.holds`), and `neighbours` filters by raw distance, so
  lanes are not listed there (use `actions.jump_quote(...)["in_range"]`).
