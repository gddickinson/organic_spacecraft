# CHANGES — innovation 2, the Kith

Spec: `reviews/2026-09-17/innovations/02-kith.md`. Nothing here edits
`INTERFACE.md`, `IMPROVEMENTS.md`, `README.md` or `SESSION_LOG.md`; this file
carries what the map maintainer needs.

A living people of the Cradle. Met on first entering it; learned through a
24-sign lexicon (listening, the decoding bench, exchanges, watching their
stars); dealt with by gift, not price; an accord unlocks their hulls and a
pilot. Every act states its misread odds, and those are the odds rolled.

## New files

| File | Lines | What |
|---|---|---|
| `seedfall/data/kith.py` | ~375 | the 24 signs (glyph, gloss) in 4 domains, 12 phrases, learning rates, the gates (0.4 / 0.5 / 0.7 + standing 40), misread odds, reactions and `WORTH`, `PRIORS` per good, `GENEROSITY`, debt/insult, songglass buyers, the three grafts (+ their adaptation pairs), gathering names, `KITH_PARTS` (grafts as `Part`s, family `"kith"`), `KITH_HULLS` (DRIFTER, CHOIR-COLONY, xeno family) |
| `seedfall/sim/kith.py` | ~475 | `KithState` (registered); first contact (`arrive`, `first_contact`); the lexicon (`comprehension`, `domain(s)`, `teach`); `misread_odds`, `can(act)`, `roll`, `fight`; listening (`listen_rate`, `listen_preview`, `listen`, `tick`); the bench (`phrases`, `bench_glyphs`, `begin_decode`, `decoded`); `observe`; hooks `refusal`, `synergy`, `grows`; **`progress(game) -> {met, comprehension, accord, exchanges}`** for a later renown system |
| `seedfall/sim/kith_acts.py` | ~385 | the gift economy: `preview_gift` / `offer` (one `_outcome`), `ask`, `belief`, `known`, `debt_at`, `come_due` (insults); `preview_ask`, `berth`, `passage`, `sign_accord`, `take_pilot` |
| `seedfall/sim/kith_world.py` | ~170 | placement: `chosen`, `place`, `ensure` (relight, load, clock), `gatherings`, `is_gathering`, `open_buyers` (songglass lines), `prefs` (hidden, derived from seed, not saved), `prior`, `graft_of` |
| `seedfall/ui/kith_panel.py` | ~290 | the gathering screen (replaces the market): lexicon glyph rows, listening + bench, the gift with its preview, what may be asked, history |
| `seedfall/ui/kith_codex.py` | ~100 | the Codex "The Kith" tab (entry + lexicon page + songs) and the chart's ring of lights round charted gatherings |
| `seedfall/tests/test_kith.py` | ~345 | suite `kith`, 11 checks |
| `seedfall/tests/test_kith_gift.py` | ~295 | suite `kithgift`, 11 checks |
| `seedfall/tests/kith_kit.py` | ~105 | scenes: an opened Cradle (through `relight.relight`), met, at a gathering; a bench solver |

## Saved state (all defaulted; old saves load)

- `Game.kith: object | None = None` — `sim/kith.KithState`: `met_day`,
  `met_at`, `lexicon`, `known_prefs` (gathering → good → [reaction,
  seen|told, odds]), `debts` (gathering → [owed, since, insulted]), `given`,
  `thanked`, `held`, `charted`, `accord`, `pilot`, `recordings`, `session`,
  counters (`acts`, `exchanges`, `misreads`, `decoded`), `history`.
- `Market.gift_economy: bool = False` (`world/economy.py`).
- Data only (not saved): `Commodity` `songglass` (`native="cradle"`),
  faction `kith` (hidden), lineage `kith`, part family `"kith"`.
- No new id kind. Gathering preferences are derived from their seed, never
  saved. Gatherings are `Port("gathering", name, 2, ("gathering",), "kith",
  independent=True)` on systems whose `faction` stays `None`.

## Placement and old saves

`kith_world.place` picks 4–6 Cradle systems (never the entry) from
`RNG(f"{seed}:kith:gatherings")`; names, preferences and grafts from
`{seed}:kith:{system id}:…` — as the `world/regions` docstring asks, never the
region's stream and never re-running `generate`. It runs at the relight
(`sim/relight`), on load (`core/loading`, for a Cradle opened before the Kith
existed), and from `kith.arrive`/`kith.tick`. Idempotent. Songglass buyer
lines go on Charter and Dry Choir markets from `{seed}:songglass:{id}`.

## Suites

`kith` (11): first contact once (via the deep gate, despatch, re-entry);
gatherings from their own seeds, off the entry, unclaimed, all three grafts
grown; listening preview == act, cap 0.55, lever; the bench teaches exactly
its phrase, a loss nothing, lever; an exchange teaches exactly its spoken
signs + stars teach Place (lever via `survey.perform`); gates bracketed
0.39/0.40, 0.49/0.50, 14/15, 0.69/0.70, 39/40 with reasons; misread odds
shown == odds passed to the roll == 4,000-roll frequency (3.5σ); the listen
rate formula, the throat and a quarter-rate idle day, absolute; old save
gets its gatherings on load (same ids/names, songglass lines back);
cross-process save; the screen (Ask first, Offer, Listen pressed; Codex tab).

`kithgift` (11): preview honest (unknown = prior; seen = act to the tonne;
prior's likeliest answer 68% of 240 draws); debt → insult on day 90 not 89,
−10, next gift pays first; trade gate at a gathering; songglass nowhere in
the Verge before, 8 buyers after, sold through `trade.sell`; graft fits only
grown (all 37 classes) + synergy lever; accord unlocks DRIFTER/CHOIR-COLONY
at a gathering only + the pilot; Concord unchanged with Kith at ±100, 400
arrivals at −100 meet no Kith, a misread fight does; misread −4, 30% fights
(400 misreads); gift standing cap 3 / 10-day / offence −3; graft at 15,000,
debt-cleared +1; berth 5 days mends, passage charts all, history cap 60.

Tripwire sweep (`python3 -m seedfall.tests.tripwire kith --fast`, the 32
constants in `data/kith` and `sim/kith*`): the first pass left 14 survivors
(passive share, science worth, both throat factors, misread standing, fight
share, the three gift-standing numbers, debt-cleared, graft threshold, berth
days, pilot level, history cap). The checks added for them leave **0 of 32**.

## Measurements (scripts in `scratchpad/scratch-kith/`)

- **Contact**: on the deep-gate crossing itself — 0 days after the relight's
  crossing, in all runs; once only.
- **Comprehension over time** (`kithbot.py`, 3 seeds, one gathering, every
  recording solved, gifts from day ~40): Kin 0.39 / 0.59 / 0.72 / 0.80 / 0.88
  at days 39 / 69 / 99 / 129 / 159 (kb1). Trade gate day 39–54; accord day
  168–184 — standing (40) is the binding bar. Listening alone: trade gate at
  118–129 days, the cap 0.55 never passed.
- **Exchange vs Verge trade** (`measure.py`, 4 seeds, every gathering, 20
  gifts of 10 t with the debt repaid in kind, songglass at the best Verge
  buyer ₡1,651): prized 1.02–1.45× the best Verge counter for the same good,
  welcome 0.78–1.36×, plain 0.41–0.68×, offended 0.
- **Misreadings**: stated 24.5 / 17.0 / 10.9 / 6.1 / 1.5% at Exchange
  0.40 / 0.50 / 0.60 / 0.70 / 0.85 rolled 24.8 / 17.8 / 11.7 / 7.8 / 1.7%
  (600 each); in play 3–5 of 59–68 acts, 0–2 fights.
- **Verge unchanged**: the four campaign bots × 3 seeds × 3 years give the
  same day, credits, techs and standing as the untouched tree (12/12); with
  the Cradle open and the Kith placed, 8 two-year runs, no error, strict save.

## The FACTIONS audit

| Site | Effect of a hidden `kith` row |
|---|---|
| `core/state.new_game` rep init | `rep["kith"] = 0.0` — the Kith standing, on purpose. Old saves read `.get(…, 0)`. |
| `world/galaxy` owners | excludes hidden: no Verge port is the Kith's |
| `data/factions.THE_POWERS`, `sim/diplomacy.POWERS` | unchanged, four |
| `sim/beginning` origins, `sim/manual` powers, `ui/map_view` legend, `ui/port_view` Standing, `sim/allegiance`, `sim/programmes`, `sim/territory` | all skip hidden |
| `ui/codex_view` Powers | **edited**: the Kith show once met (their own flag), the Abyssals as before |
| `sim/encounters.roll_encounter` | candidates hard-coded to three powers: the Kith never; only `kith.fight` (a misreading) makes one |
| `sim/legacy` Concord epoch | **edited**: it raised every rep but the Bloom's to 60, which would have handed the Kith's accord standing to the Concord |
| `sim/tutorial_watch._best_standing` | max over all reps, Abyssals already included; the Kith move only after contact, long after the tutorial. Left. |
| `bridge/protocol` rep | reports `kith` too. Left. |
| `sim/assembly_vote` short-name map | names only. Left. |

## Shared and other-owned files touched (one line per hunk)

- `core/state.py` — `kith` field appended after `assembly`.
- `core/sectortime.py` — import; one line in `reckoning` (`kith_sim.tick`).
- `core/loading.py` — 3 lines after `recompute`: `kith_world.ensure(game)`.
- `data/factions.py` — `kith` Faction appended (hidden).
- `data/commodities.py` — `songglass` appended (`native="cradle"`).
- `data/parts.py` — import + `*KITH_PARTS` in `PARTS`.
- `data/chassis.py` — import + `*KITH_HULLS` in `CHASSIS`.
- `data/hull_types.py` — `ACCEPTS["grown"]` += `"kith"`.
- `data/lineages.py` — `kith` lineage appended (`common=False`).
- `data/help_more.py` — topic `kith` appended.
- `world/economy.py` — `Market.gift_economy` field.
- `sim/flight.py` — `arrive_in_system`: 2 lines, `kith.arrive(game)`.
- `sim/relight.py` — import; one line after `generate`: `kith_world.ensure`.
- `sim/enforce.py` — `may_trade`: 4 lines, the gift-economy refusal first.
- `sim/minigames.py` — `finish_decoding`: 4 lines routing a `kith:` tag.
- `sim/adaptation.py` — `fx`: 5 lines folding `kith.synergy(ship)` (the one door).
- `sim/shipyard.py` — `can_build_here` xenoyard branch: `or kith.grows(…)`.
- `sim/survey.py` — import; one line after `note_survey`: `kith_sim.observe`.
- `sim/legacy.py` — Concord epoch skips `kith`.
- `sim/manual.py` — `@fact("kith")` appended.
- `ui/port_view.py` — import; 3 lines hosting `kith_panel.build`.
- `ui/codex_view.py` — import; tab list +1 conditional tab; dispatch +1; Powers reveal.
- `ui/star_chart.py` — import; one line `kith_codex.draw` after `hunt_marks`.
- `ui/minigame_view.py` — `_glyphs` (6 lines); 2 glyph lookups; `_finish` goes `res["back"]`.
- `tests/suites.py` — 2 rows. `tests/tripwire_kin.py` — 3 keys.
- `tests/test_sim.py` — part/chassis gates also accept `data/kith.GATES`
  (import folded into an existing line; the file stays at 500).
- `tests/test_works.py` — `KNOWN_TECH` also holds `data/kith.GATES`.
- `tests/test_reaches.py` — "unported" check now "its only quays are the Kith's".

## Deviations

- **Grafts are unlocked, not handed over fitted**: a gathering's gift is the
  growing of the graft (its gate joins `research.unlocked`, as incorporated
  xenotech does); any nursery grafts it to a grown hull at the yard.
- **Graft family `"kith"`**, accepted by grown hulls only (not hybrid, not
  the Kith's own xeno hulls) — the spec's "grown hulls only", exactly.
- **The Kith pilot comes with the accord**, not "occasionally".
- **Phenomena** (innovation 7) do not exist in this tree: a survey in the
  Cradle that sees something stands in (`kith.observe`, callable by 7).
- **Passage** charts every gathering (and adds it to `discovered`); it does
  not move the ship. **Berth** mends the hull and the crew in 5 days.
- Not done: Kith traffic on the chart, a gathering sound cue.
