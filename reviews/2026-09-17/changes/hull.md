# CHANGES — innovation 4, the living hull

Spec: `reviews/2026-09-17/innovations/04-living-hull.md`.

Grown, hybrid and xeno hulls remember what is done with them on nine stress
channels, and at thresholds an adaptation emerges: a small permanent change
with a gain and a cost, which the captain can encourage (growth material,
sets in within 20 days), suppress (fades; the channel is starved back), or
ignore (sets in by itself after 60 days). Fabricated and synthetic hulls
never adapt, and the Ship screen says so.

## New files

| File | Lines | What |
|---|---|---|
| `seedfall/data/adaptations.py` | 259 | channels, family rates, budget steps, costs, the 16-row table with GESTALT-grounded text |
| `seedfall/sim/adaptation.py` | 390 | `record`, `fleet_record`, `sky`, `tick`, `encourage/suppress/prune` + `_quote`s, `fx`, `apply`, `dose_multiplier`, `reading` |
| `seedfall/ui/body_panel.py` | 191 | the Body tab: channel bars, the emergence with both answers costed, what has set in with Prune |
| `seedfall/tests/test_adaptation.py` | 457 | suite `adaptation`, 14 checks |
| `seedfall/tests/adaptation_kit.py` | 117 | scenes the checks stand a ship in (dim star, Fleet Hub, fight, ocean) |

## The table

| Adaptation | Channel ≥ | Gain | Cost | Families |
|---|---|---|---|---|
| Callused rind | impact 240 hp | armour +1 | sublight −3% | grown, hybrid |
| Scar lattice | impact 600 hp | regrowth +15% | evasion −0.02 | all three |
| Radiator fronds | heat 250 heat-days | vent +20% | conceal −0.10 | all three |
| Heat-shock chaperones | heat 900 | heat cap +15% | regrowth −5% | all three |
| Long-haul metabolism | crossing 130 ly | jump +0.4 ly | morale −0.10 | all three |
| Torpor reflex | crossing 480 ly | air reserve +25% | sublight −2% | all three |
| Melanised rind | dark 40 days | air reserve +30%, crew dose ×0.80 | vent −10% | grown, hybrid |
| Night-adapted eyes | dark 120 days | sensor reach +12% | survey quality −0.03 | all three |
| Glare mantle | glare 60 days | crew guard +0.05, crew dose ×0.75 | sensor reach −8% | all three |
| Sun-fed intima | glare 150 days | regrowth +10% | heat cap −5% | grown, hybrid |
| Mineral gut hypertrophy | gut 250 t | ore rate +15%, phosphate rate +10% | hold −3% | grown, hybrid |
| Concentrator root | gut 900 t | phosphate rate +30% | ore rate −5% | grown, hybrid |
| Acute opsins | eyes 14 looks | survey quality +0.05 | sensor reach −5% | all three |
| Magnetite antenna | eyes 40 looks | sensor reach +10% | sublight −2% | all three |
| Pressure bone | depth 3 dives | armour +1, crew guard +0.04 | sublight −3% | grown, hybrid |
| Motile trim | burn 5 hard crossings | sublight +5% | heat cap −5% | all three |

Rates: grown 1×, hybrid 0.5×, xeno 1.5× (xeno draws what it grows at random
from its open set, seeded from chronicle+hull+day, not from `game.rng`).
Budget by chassis hull points: <300 → 1 (SPORE), <1000 → 2, <2000 → 3
(NAVIS), <5000 → 4 (TESTUDO, TARDIGRADE), else 5 (LEVIATHAN); hybrids one
fewer, floor 1. Encourage: 4 t phosphate + 12 t biomass × hull/1400, through
`sim/stores`. Prune: 3,000 cr × hull/1400 and 8 days, alongside a `gestation`
anchorage. Suppress and prune leave the channel one threshold *below* zero.

## Recording sites (one line each)

impact `sim/damage._apply_to_layers` · heat `core/shiptime.hull` (cooling
result ÷ `COOK` = heat-days) · crossing and burn `sim/actions.jump_to` (flag +
escorts) · dark/glare inside `adaptation.tick` (flag + escorts; `System.heat`
< 0.25 / ≥ 0.9) · gut `actions.extract` · eyes `survey.perform` and
`actions.survey` (only a look that yielded research) · depth `actions.dive`.

## Measured against the balance targets

Bots from `scratchpad/campaign` (explorer, fighter, colonist, trader × seeds
s1–s3, five years, NAVIS), scripts in `scratchpad/scratch-hull/`.

- **Channel fill, 5 y, nothing emerging:** crossing 260–1,046 ly; eyes
  66–97 (explorer, colonist), 0 (trader, fighter); glare 6–116 d; dark 0–48 d;
  gut 100–677 t; impact 0–2,457 hp. Heat, burn and depth: 0 in every bot
  career (none runs hot, flies hard crossings or dives). Six back-to-back hard
  transfers: 1,125 heat-days; a week over the cap is ~500.
- **Ignore (the bots' default):** first emergence day **135–250** in all 12
  careers (target 60–250); **3 emergences in 5 years in all 12** (target
  3–6; the NAVIS budget). Before retuning, impact 150 and glare 40 gave a
  fighter day 26 and a colonist starting under an A-star day 40.
- **Suppress everything:** 2–9 emergences in 5 years at `DRAW_DOWN = -1.0`;
  it was 7–29 at 0.4, 4–16 at 0, 2–12 at −0.5.
- **Hybrid (PALIMPSEST):** first 261–424, 2 in 5 years. **Xeno (REVENANT):**
  first 90–104, 3.
- **Worth:** no gain beats the best tier ≤ 2 fitting on its stat; nearest is
  scar lattice at 90% of `regrowth_surge` (checked in the suite).
- **Not badly behind:** the twelve held sets move single stats by at most
  armour +1 (25% of a NAVIS's 4), scan +0.05, air +30%; costs 2–8%. Bot
  deaths with adaptations 5/12, with them switched off 5/12 — the
  differences are chaotic divergence (trader s2 was at 24 credits by day 301
  in both).

## Suite `adaptation` (14 checks, ~5 s)

1. every channel fills from its act, driven through the act (fight, hard
   burns, jumps, a dim and a glaring star, a working, a survey, a dive); the
   star lines bracketed at 0.18/0.32 and 0.86/1.00
2. a threshold makes an emergence and logs it; 129 ly does not; cap 600
3. left alone it sets in on day 60, not 59, and `ship_stats` moves
4. encourage costs exactly its quote (4 t + 12 t), sets in on day 20, refused
   short of phosphate
5. suppress leaves exactly the quoted −130 and nothing re-emerges
6. every effect of every adaptation moves its stat, measured with `fx`
   switched off through `efficacy.Lever` (34 effects)
7. no gain beats a tier-2 fitting
8. all 17 fabricated/synthetic hulls: nothing recorded, emerged or set in
9. budget by body: spore 1, navis 3, testudo 4, leviathan 5, graft 1,
   threshold 3, revenant 3
10. hybrid 0.5×, xeno 1.5× and a random draw that spends its trigger
11. prune equals its quote (3,000 cr, 8 days) and only at a Fleet Hub
12. every tech + extra fittings + all 16 at once stay inside `BOUNDS`
13. cross-process save/load, and a save without the fields loads
14. the Body tab: Encourage, Suppress and Prune pressed; welded hull says so

A tripwire-style sweep of all 11 constants in `data/adaptations.py` against
this suite: every variant caught (the one "survivor" is `1 // 2 → 1`, the
same value).

## Deviations, each with its reason

- **Night-adapted eyes** are sensor +12% everywhere at scan −0.03, not
  "+12% in dim systems": `stats()` is a pure function of the ship and is
  recomputed on events, not on arrival, so a location-conditional stat would
  be stale. The cost is the real trade of dark adaptation (rod convergence:
  sensitivity for acuity).
- **Pressure bone** costs sublight −3%, not mass +2%: `Stats.mass` has no
  reader (grep), so a mass cost would be decorative. Dive safety comes through
  armour, which is what `actions.dive` reads (risk 0.28 − 0.01 × armour).
- **Callused rind** armour +1 flat, not +8%: a NAVIS has armour 4, so 8% is
  0.32 of soak. **Scar lattice** evade −0.02 flat (−10% of 0.20), not −4%.
  **Long-haul** morale −0.10, not −0.02: the morale fx enters the target at
  ×0.4, so −0.02 moved it 0.008.
- **Costs added** where the spec named none: chaperones (regrowth −5%),
  melanised rind (vent −10%), glare mantle (sensor −8%). Glare mantle also
  gets crew guard +0.05 so it moves a stat before the Cradle's dose exists.
- **Eyes** counts only a survey that yielded research — the farmer bot's daily
  re-sweep of one body would otherwise fill it.
- **Depth** counts ocean dives only: there is no atmospheric-dive act in the
  game (`sim/landing.py` is explicit that a ship cannot enter a world).
- **Burn** counts interstellar hard/relativistic crossings, not in-system
  hard transfers (spec: "hard-burn crossings").
- A crossing's days count under the destination's star (`jump_to` sets the
  location before the clock runs).
- An adaptation's effects are fields `gives`/`takes`, not `gain`/`cost`:
  `test_courtship` holds any `.gain` read outside `sim/diplomacy` to be a
  second door onto the courtship curve, and the first full run said so.
- **Not done:** the optional plans-picture tint.

## Shared / other-owned files touched

- `sim/ship.py` — 3 fields appended at the end of `Ship` under a comment;
  `stats()` returns `adaptation.apply(s, ship)` (lazy import, 2 lines).
- `sim/damage.py` — import; one `record(to.ship, "impact", total)`.
- `sim/actions.py` — import; `jump_to` 2 lines (crossing, burn); `survey` 1;
  `extract` 1; `dive` 1.
- `sim/survey.py` — import; 1 record line in `perform`.
- `core/shiptime.py` — import; `COOK` added to an import; `hull` phase: 1
  heat record line + the 2-line `tick` loop.
- `ui/ship_view.py` — import; a third tab; 3-line branch to `body_panel`.
- `data/help.py` — topic `adaptation` appended.
- `sim/manual.py` — fact `body` appended (4 lines, calls `adaptation.reading`).
- `tests/suites.py` — row `adaptation` appended.
- `tests/tripwire_kin.py` — row `adaptations` appended.

## For the maps (not edited here)

`seedfall/INTERFACE.md` Layout rows: `data/adaptations.py` (the living hull's
table), `sim/adaptation.py` (record/tick/answers/apply — the one door for
what the body does to the numbers), `ui/body_panel.py` (Ship → Body tab),
`tests/test_adaptation.py` (14 checks), `tests/adaptation_kit.py`.
