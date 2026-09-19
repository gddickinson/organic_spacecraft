# Innovation 3 — Nemeses and the hunt: changes for the merge

Spec: `reviews/2026-09-17/innovations/03-nemeses.md`. This file stands in for
the INTERFACE / SESSION_LOG edits (the maps were not touched).

## New files (all owned by this innovation)

| File | Lines | What it holds |
|---|---|---|
| `seedfall/data/nemeses.py` | ~240 | Archetypes (five, with `edge`, `pursuit`, `aggression`, `ally`, `buy_off`, `wanted`), seven traits, `ENDINGS` (every battle result id → a rival's word, no new ids), names, taunts, the two shroud parts, `trophy_part` |
| `seedfall/sim/nemeses.py` | ~455 | `Nemesis` and `HuntState` (both `@register`), `state`, rise (+ caps, `RISE_GAP`), the triggers the calendar sees (hunt warrants, the cartel ledger via `undercut`), the daily `tick` (roam, hear, mend, rumours, returns), sightings and confidence decay, memory + despatch taunts |
| `seedfall/sim/rivals.py` | ~320 | Difficulty, the persistent hull (`refit`: new at a rise, re-armed and never worse on a return), `meet` (the encounter hook), `encounter`, `header`, `opening` (first volley, the grateful ally as a consort) |
| `seedfall/sim/rival_ends.py` | ~230 | `settle` — called by `aftermath.resolve`: every ending mapped, bounty/trophy/standing, wounded→return, spared→ally or betrayal, plunder on a loss, rises from ordinary fights, `ashore` for a prize-taken rival |
| `seedfall/sim/hunts.py` | ~470 | The board (rivals + raiders where `piracy` says raiders work, in reach, only what the issuer's purse can pay), `take`, `search_odds`/`search`, persistent raider hulls, `collect` (full for destroyed/struck, half for driven-off), `pay` (out of the issuer's purse), buy-off, trophy terms/mount/sell |
| `seedfall/sim/running_dark.py` | ~120 | The switch: `dark`, `signature`, `exposure`, `suspicion`, `caught`, `set_dark` (logs itself), `tradeoff` (tooltip text) |
| `seedfall/ui/hunts_panel.py` | ~290 | The Hunts tab (dossiers with `thumb3d` portraits, search with stated odds, board, trophies), `rival_lines` for the aftermath card |
| `seedfall/ui/hunt_marks.py` | ~125 | HUD chip, Ship-screen row, chart sighting rings, battle header |
| `seedfall/tests/test_nemeses.py` | ~405 | Suite `nemeses` (18 checks, with `nemesis_hunts`) |
| `seedfall/tests/nemesis_hunts.py` | ~170 | The hunt's checks, run by `test_nemeses` (split at the length rule) |
| `seedfall/tests/nemesis_kit.py` | ~170 | Fixtures: mid-game warfit, a rival at level N, fights, win rates |
| `seedfall/tests/test_nemeses_ui.py` | ~160 | Suite `nemesesui` (4 Qt checks, optional) |

## Hooks in shared / other-owned files (one line per hunk)

- `core/state.py` — `hunt: object | None = None` appended after `crew_leaving`, the innovation named in a trailing comment (the file is at 499 lines; a separate comment line would break the 500 rule — see deviations).
- `core/ids.py` — `"nemesis": ("Nemesis", "id")` added to `KINDS`.
- `core/sectortime.py` — import line; `nemeses_sim.tick(game, n, r)` after `memory_sim.tick` in `reckoning` (draws nothing from `r`).
- `sim/encounters.py` — 7 lines at the top of `roll_encounter` (`rivals.meet` first, `seen = running_dark.exposure`); `HUNTER_ODDS * seen`; `min(0.7, danger) * seen`. Lit, `seen` is 1.0 and the draw sequence is unchanged.
- `sim/aftermath.py` — import; `out["nemesis"] = rival_ends.settle(game, battle, out)` before the loss returns.
- `sim/customs.py` — `odds += running_dark.suspicion(game)` in `chance`.
- `sim/enforce.py` — `watchers` counts a dark hull as a patrol's business; `tick` multiplies stop odds by `exposure` and appends `running_dark.caught` lines.
- `sim/trade.py` — `nemeses_sim.undercut(game, system, brought * price)` after a sale (the cartel's ledger).
- `data/parts.py` — imports `SHROUDS`, appends it to `PARTS`.
- `data/help.py` — topic `hunts` appended.
- `ui/law_view.py` — import; `if hunts_panel.tabbed(self): return` after the heading.
- `ui/ship_view.py` — import; one `dark_row` widget after the fitted/crew row.
- `ui/hud.py` — import; the chip added after the clock pill; `sync_chip` in `refresh`.
- `ui/star_chart.py` — import; `hunt_marks.draw_sightings(p, self, g)` after `_draw_names`.
- `ui/battle_view.py` — import ×2; `band=encounter.get("band") or 3` in `combat.start`; `rivals_sim.opening(...)` after it; `hunt_marks.battle_header(...)` under the title.
- `ui/battle_text.py` — `rival_lines` appended to `aftermath_lines`.
- `tests/suites.py` — rows `nemeses`, `nemesesui`.
- `tests/tripwire_kin.py` — fast paths for the five new sim modules.

## Measurements

- Win rate, warfit NAVIS on day 540, 200 seeded fights across all five archetypes, rivals risen at level 1 and refitted up: **level 1 70%, level 5 37%** (target 60–75 / 30–45).
- Run dark, 5,040 seeded arrivals per seed: **34 / 45 / 46% fewer** encounters (verge-7, s5, alpha-1); shrouded 46 / 54 / 55%. Customs odds docked dark at a Concordat quay: **10% → 35%**.
- Search: stated 84% over 3 days, found 85% of 300 (hunter, lit); dark quarry 43%.
- Careers, 3 seeds × 3 years (`scratch-nemeses/campaign/hunter.py`): hunter **+28.7 / +24.8 / −12.3 cr/day** (mean 13.7); explorer +37.9 / +3.1 / +34.8 (mean 25.3); the old fighter bot ≈ −16 (dead or broke on all three). Hunting net of repairs and guns: +35k / +5k / +6k per career; 11, 1 and 10 prices collected (s5's opening pocket holds one raider).

## Deviations

- **`Game.hunt` (a `HuntState`) instead of `Game.nemeses` + `Game.dark`.** `core/state.py` was at 499 lines against the 500 limit; one field is all it can take.
- **Level 5 "does not retreat" is the `feral` style (no breaking off on a broken hull), not extra nerve.** A 2× last stand and 2.5× relentless nerve measured level 5 at 3% (87 of 200 fights to stalemate).
- **Nerve grows 5 a level plus a tenth of the grudge; the 0.4 a level goes into hull and fit.** Charged to nerve at 27 a threat point, level 5 won 27%.
- **Per-archetype `edge` on the threat** (ace −0.6, hunter −0.3, husk +0.6): measured spread was ace 38% / husk 97% at level 1.
- **Swarm escorts are hull and nerve on the rival's own `Side`**: the battle has one enemy side.
- **Duellist accuracy is +0.08 on the rival's stats, all bands**; the enemy's stats are rebuilt only on a disable.
- **Coward** is 0.6× nerve and the `cautious` style rather than a 50%-hull threshold, which would need an `enemy_ai` edit.
- **Posted raiders** stand where `piracy.raider_chance > 0` even when `traffic` rolled no raider there ("heard of, never plotted"). Traffic alone put no raider inside the opening pocket of two of three sectors.
- **A driven-off raider pays half** (`DRIVEN_SHARE`); only destroyed or struck pays in full. Raiders broke off in 20 of 27 meetings, and without this the hunter netted −16/day.
- **Bounties come out of the issuer's exchequer purse**, and a board posts only what the purse can pay.
- **Rise from "cartel undercutting"** = 60,000 credits of goods sold at Freehold counters (hook in `trade.sell`).
- **Hunter income is below the explorer's on average (13.7 against 25.3)**: in band on two seeds, and negative on alpha-1, where the hunter lost too many fights with the opening hull.
