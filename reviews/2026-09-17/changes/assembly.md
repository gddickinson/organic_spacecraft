# CHANGES — innovation 6, the Assembly

Spec: `reviews/2026-09-17/innovations/06-assembly.md`. For the Phase 3 fold
into `seedfall/INTERFACE.md`, `IMPROVEMENTS.md` and `SESSION_LOG.md`.

## New files

| File | What it holds |
|---|---|
| `data/assembly.py` | Cadence (90 ±10 days, 30 days' notice, 180-day term, 2–3 motions, seat order), the closed effect vocabulary `EFFECTS` (key, combine rule, default, reader), and the 15 `RESOLUTIONS` with per-power creed stances and their reasons. The docstring says how to add a resolution. |
| `sim/assembly.py` | The door. `AssemblyState`, `Tabled`, `Active` (all `@register`ed). `ensure`, **`effect(game, key, default)`** (refuses a key outside the vocabulary), `effects` (memoised per day), `enact` (the only writer of `active`), `in_force`, `pair_key`; the readers that need more than a number: `embargoed`, `tax_salvage`, `founding_rebate`, `local_power`; `hold` (the Choir floor, daily); `tick`. Imports nothing from `sim/` at module level, so eleven consumers can import it without cycles. |
| `sim/assembly_session.py` | Seat rotation (`seat`, `seat_system`, `present`), `schedule`, `draw` (the agenda from `luck(game, session, tag)`, never `game.rng`), `announce` (a despatch from the seat), `sit` (count, move the matrix, enact, one-off extras, report), `expire`, `lost_last`, `tick`. |
| `sim/assembly_vote.py` | `interest` (named reasons), `score`, `speech`, `forecast`, `tally`, `vote_of`, `moves` (the relation outcome), `title`/`words`. |
| `sim/assembly_lobby.py` | `position`, `preview`, `lobby` (does exactly `preview`), `speech`, `intelligence`. |
| `ui/assembly_panel.py` | The "The Assembly" tab: next sitting with a countdown and a set-a-course button, each motion with its effect in plain words, the forecast per power with reasons, your stance, the speech swing, and the lobby acts with previews; what is in force; the last sittings. |
| `tests/test_assembly.py` | Suite `assembly`, 11 checks. |
| `tests/assembly_probes.py` | One efficacy probe per effect key (`READERS`). |

## Resolutions and where each key is read

| Resolution | Key(s) | Read at (one line) |
|---|---|---|
| Bloom Levy | `tithe` 5% · `containment` +0.15 · `wharfage` ×1.05 | `exchequer._books` · `ventures.odds` · `wharfage.rate` |
| Open Quays | `wharfage` ×0.5 | `wharfage.rate` |
| Licence Amnesty | `amnesty` | `enforce.may_seed`, `customs.aboard` |
| Embargo on ⟨power⟩ | `embargo` (its exports refused at the other powers' counters) | `trade.sell` via `assembly.embargoed` |
| Ceasefire ⟨A, B⟩ | `ceasefire` (+ relation lifted to −40 on passing) | `war.at_war` (so `armada`, `ventures` and `fleets` too) |
| Research Commons | `commons` 4 survey evidence a set | `trade.sell_survey_data` → `inquiry.add` |
| Salvage Law | `salvage_tax` 30% of credits + `worth_of(cargo)` | `aftermath._salvage` via `assembly.tax_salvage` |
| Charter Recognition of the Choir | `choir_floor` −10 (+15 Charter–Choir on passing) | `assembly.hold` (daily tick) |
| Convoy Escort Mandate | `lawless` ×0.75 on capital-lane systems | `piracy.lawlessness` |
| Privateer Licences | `lawless` ×1.25 on unclaimed systems | `piracy.lawlessness` |
| Colony Charter | `founding` 20% of the credit price, paid from the four purses | `colony.found` via `assembly.founding_rebate` |
| Harbour Dues Reform | `repairs` ×0.85 | `services.repair_quote` |
| Border Treaty ⟨A, B⟩ | `border` | `war.spoils` (so `ventures` annexation) |
| Contraband Accord | `search` ×1.5 | `customs.chance` |
| Free Passage | `tolls` ×0.5 | `gates.toll` |

Hooks for later: **Bounty Compact** (key `bounty`, read where `sim/contracts`
prices a bounty) and **Deep Gate Moratorium** (`deep_gates`, read where a deep
gate is lit). Adding one = a `RESOLUTIONS` row + an `EFFECTS` row + one reader
line + a `tests/assembly_probes.READERS` row; the suite fails a key without a
probe.

## Balance, as measured (scratchpad bots, 5 seeds × 5 years unless stated)

- Sector with nobody lobbying (10 seeds): mean pair relation **+3.7**, **49%** of motions pass (spread −26 to +30).
- Idle explorer bot: +10.2, 49% pass. Same with a 150 cr/day stipend: −12.4, 33% pass.
- Broker, explorer income only: +14.0, aim met 75%. Broker with the stipend: **+36.6** (23.5–47.7), aim met **84%**, 70% pass, about 33 lobby acts in five years.
- Concord: the funded broker reaches 3–4 of 6 pairs at peace (idle 1–2); **no power reaches Kin**, because the career's standing collapses in both bots.

## Shared / other-owned files touched (one line per hunk)

- `core/state.py`: `Game.assembly` field, last saved field, one line.
- `core/sectortime.py`: import; `assembly_sim.tick(game, n)` after `dip.drift` in `economy`.
- `data/help.py`: topic `assembly` appended.
- `tests/suites.py`: row `assembly` appended.
- `ui/diplomacy_view.py`: import; `self.tab`; the Desk/Assembly `TabBar` in `build`; `_page`.
- `sim/wharfage.py`: import; `share *= effect("wharfage")` in `rate`.
- `sim/exchequer.py`: import merged into the `diplomacy` line; the tithe on the `_books` accrual line (still 499 lines).
- `sim/ventures.py`: import; containment odds in `odds`.
- `sim/enforce.py`: import; amnesty early-return in `may_seed`.
- `sim/customs.py`: import; amnesty in `aboard`; the Contraband Accord in `chance`.
- `sim/trade.py`: two imports; the embargo refusal in `sell`; the commons in `sell_survey_data`.
- `sim/war.py`: import; the ceasefire in `at_war`; the border in `spoils`.
- `sim/aftermath.py`: import; `tax_salvage` at the end of `_salvage`.
- `sim/piracy.py`: local import; the `lawless` line in `lawlessness`.
- `sim/colony.py`: import; `founding_rebate` after `stores.spend` in `found`.
- `sim/services.py`: import; the repairs line in `repair_quote`.
- `sim/gates.py`: import; the tolls line in `toll`.
- `tests/tripwire_kin.py`: four `KIN` rows appended (`assembly*` → suite `assembly`); `harness` requires a fast path for any module holding constants.
- `tests/test_politics.py` ("the powers act without being prompted"): runs the seeds "acting" and "acting-2" instead of "acting" alone. With the Assembly, "acting" resolved 10 ventures and all 10 succeeded. Over eight other seeds, 7.0 failures each (8.9 without the Assembly).
- `tests/test_geography.py` ("a port keeps the character…"): the berth guard is now at least 5 open per seed and a mean of at least 8 across the four seeds, where it was at least 8 per seed. Over 12 seeds: 11.8 open on average with the Assembly, 11.5 without; the worst seed is 5 either way. "geo1" alone moved from 9 to 6.

Both are single-seed trajectories that the Assembly diverts by moving the matrix; it draws nothing from `game.rng`. Blinding `tithe`, `wharfage` or `containment` did not change either result.

The play-test bots (not in the repo) are `scratch-assembly/campaign/broker.py`, with modes broker, brokerfunded, idle and idlefunded.
