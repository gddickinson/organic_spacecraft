# CHANGES — innovation 9, Renown and the Voyage

Spec: `reviews/2026-09-17/innovations/09-renown.md`. This file stands in for
the INTERFACE / IMPROVEMENTS / SESSION_LOG edits; the maps were not touched.

**The headline.** An honest captain who follows the first officer's counsel
and chooses a road reaches **Genesis within five years on 9 of 10 seeds**
(s1–s10), with no deaths; with the rewards withheld, 0 of 5 (s1–s5). The
simple strategy bots still reach nothing (they ignore counsel and never sign
on hands; 15 of 20 die of an empty mess deck).

## New files

| File | Lines | What it holds |
|---|---|---|
| `data/milestones.py` | 334 | `Reward`, `Milestone`, `M()`; `RANKS` (Master 0, Captain 80, Commodore 250, Admiral of the Verge 550, Legend 1000); `PERKS` (six keys, rank, words); `STANDING_FLOOR`, `RECRUIT_FLOOR`, `TABLE_EVERY`; `CAREER` (66 milestones across 14 topics); `TOPICS`. Docstring: the one-line way to add a milestone (and the Wave B ones). |
| `data/milestone_tracks.py` | 183 | `TRACKS`: three rungs on each of the ten endings (Ruin's pays nothing); `ROADS` (the technology at the end of each ending's road); `RUNG_TECH`; `TRACK_ORDER`. |
| `sim/renown.py` | 388 | `RenownState` (@register); `ensure`, `note` (counts acts that leave no state), `rank`, `perks`, **`perk(game, key)`** (the one door every perk is read through), **`reward_terms`** (the one price), `check` (fires, pays, promotes; backdates an old save), `tick` (daily, logs itself, holds the standing floor), `hold`, `seen`, counsel dismiss/recall, `ladder`/`tracks`/`leading`/`follow`/`focus`/`next_step`, `recent`, `by_topic`. |
| `sim/renown_facts.py` | 353 | `FACTS`: ~60 named numbers read from existing state; `fact(game, key)`; `wave_b(game, "module:key")` — reads `sim/<module>.progress(game)` behind an import guard; `COUNTED`. |
| `sim/renown_perks.py` | 133 | The two perks that are acts: `motions`/`table_terms`/`table`/`motion` (the Assembly tables one motion a year for an Admiral), `name_of`/`name_terms`/`name_system` (Legend). |
| `sim/counsel.py` | 164 | `moves`, `advise(game, 3)`, `act(game, suggestion)` — dispatches `verb` to the sim door the matching button calls. |
| `sim/counsel_sources.py` | 203 | urgent (fuel, food, hull, hands), answers (envoy, demand, situation), bench, freight desk, contracts, surveys. |
| `sim/counsel_doors.py` | 232 | the next rung (promoted when the road is chosen), the Reaches, the Assembly, a house/line, a bounty, the living hull, arcs (guarded), survey data to sell, "choose a road". |
| `sim/counsel_kit.py` | 121 | `S`, `in_market`, `buyable` (trade.buy's gates), `nearest`, `hop_to` (the next jump, with jump_to's exact refusal), `road`, `road_tech`. |
| `sim/memoir.py` | 159 | `compose`, `record` (once per ending; Hall entry keyed per chronicle), `settle` (clock door), `page_of`; the Hall: `hall_path`, `hall`. |
| `ui/voyage_panel.py` | 195 | The Voyage tab: rank and progress, perks (with the motion and naming pickers when held), the ten ladders with "Follow", recent milestones. |
| `ui/counsel_card.py` | 84 | "First officer suggests…" on the Sector Chart; `take(win, move)` opens the screen/tab/star; `recall`. |
| `ui/renown_chip.py` | 65 | The fresh-milestone chip (menu-bar corner, beside the mute chip). |
| `ui/memoir_panel.py` | 79 | The memoir on the Aftermath; the Hall line on the title and its window. |
| `tests/test_renown.py` (+ `renown_perks_checks.py`, `renown_career_checks.py`, `renown_kit.py`, `careful_captain.py`) | 229/232/186/109/279 | Suite `renown`, 15 checks. |
| `tests/test_renown_ui.py` | 197 | Suite `renownui`, 5 Qt checks. |

**Saved state:** `Game.renown: object | None = None` → `RenownState(achieved,
score, ranks, counts, titles, paid, fresh, since, motion, named, quiet_until,
course, memoir)`, all defaulted. A save without it loads; the first check
credits what the old chronicle already shows (renown only, no purse pays,
one log line). Acts counted only since renown existed (`COUNTED`: sales,
fights, dives, cleansed…) wait for the next time they are done.

## Ranks and perks (each read at one line)

| Rank | Renown | Perk | Read at |
|---|---|---|---|
| Captain | 80 | Priority berthing: a full quay offers its first berth | `control.free` |
| Captain | 80 | The trading-house charter fee waived (₡6–9k, forgone by the issuer) | `freightlines.charter_terms` |
| Commodore | 250 | Recruits +1 level floor | `crew.pool_at` → `recruit_pool(floor=)` |
| Admiral of the Verge | 550 | No power's standing below Neutral (−8) | `renown.tick` → `hold` |
| Admiral of the Verge | 550 | The Assembly tables one motion a year you name | `assembly_session.announce` → `renown_perks.motion` |
| Legend | 1000 | A system renamed «⟨ship⟩'s Reach» | `renown_perks.name_system` |

## Milestones

96 in all: 66 career milestones (looking 16, money 9, the bench 5, holdings
4, fighting 4, rivals 5, the law 2, the powers 3, the Weave/Reaches 5,
freight lines 3, the Assembly 3, the living hull 2, the people 2, a life 3)
and 30 ending-track rungs. Rewards on 27 rungs; every credit names its payer
and comes out of that power's purse through `hunts.pay` (a purse pays what
it holds; `short` says the rest). Examples: Genesis — Piezolyte researched
₡15,000 (Charter), first dive +400 research, contact +600 research and
«Speaker to the Deep»; Lineage — first hull ₡8,000, second ₡15,000 (Charter);
Cartel — ₡5,000 (Freeholds), ₡12,000 (Concordat); Concord — +3 then +5 with
all four. **Adding a Wave B milestone is one row** (the fact is read already):
`M("kith_contact", "First words with the Kith", 40, "kith:contact", 1, "kith", "…")`
— `sim/<module>.progress(game)` must return a dict with that key.

## Hooks in shared / other-owned files (one line per hunk)

- `core/state.py`: `renown` field appended after `assembly` (1 line).
- `core/state.py`: `Game.die` calls `memoir_sim.record(self)` after the death is set (2 lines, local import).
- `core/sectortime.py`: imports `memoir as memoir_sim`, `renown as renown_sim`.
- `core/sectortime.py`: `renown_sim.tick(game)` in `reckoning`, before the endings check.
- `core/sectortime.py`: `memoir_sim.settle(game)` after the overgrown check.
- `sim/threat.py`: import; `renown_sim.note(game, "cleansed")` in `cleanse` when a system is cleared.
- `sim/actions.py`: import; `renown_sim.note(game, "dives")` in `dive`.
- `sim/aftermath.py`: import; `renown_sim.note(game, f"battle:{result}")` in `resolve`.
- `sim/trade.py`: import; `note("sales", brought > 0)` in `sell`; `note("survey_sales", …)` in `sell_survey_data`.
- `sim/control.py`: import; `free` offers the first berth of a full quay under the "berth" perk (4 lines).
- `sim/crew.py`: import `RECRUIT_FLOOR`; `recruit_pool(…, floor=0)`; `pool_at` passes the perk's floor.
- `sim/freightlines.py`: import; the fee is 0 under the "charter" perk (2 lines).
- `sim/assembly_session.py`: import `renown_perks`; `announce` appends the captain's motion (1 line).
- `ui/empire_view.py`: a third tab ("Voyage") and its dispatch; the "Ways this ends" list moved to the Voyage — `_victories` is now `_bloom` (the census, unchanged, plus a "The Voyage" button); unused imports dropped.
- `ui/map_view.py`: import; `counsel_card.build(self, g)` under the heading.
- `ui/hud.py`: import; the menu-bar corner is `renown_chip.corner(win, soundmap.chip(win))`; `renown_chip.sync(win)` in `refresh`.
- `ui/menubar.py`: import; Help → "The first officer's counsel".
- `ui/legacy_view.py`: import; the memoir panel on the Aftermath (both branches).
- `ui/title.py`: import; `memoir_panel.hall(self)` under the picker.
- `data/help_more.py`: topic `renown` appended.
- `tests/suites.py`: rows `renown`, `renownui`.
- `tests/tripwire_kin.py`: rows `milestones`, `renown`, `renown_facts`, `counsel`, `counsel_sources`, `counsel_doors`, `memoir` → `renown`.
- `tests/__init__.py`: `_tidy_up` also removes `<stem>.hall.json`.

## Measurements (scripts: `scratchpad/scratch-renown/campaign/`)

- **Careful captain** (`tests/careful_captain.py`, follows Genesis), 5 years:
  s1 1,234 · s2 1,442 · s3 1,472 · s4 1,294 · s5 contact made, protocol
  unfinished; s6 1,647 · s7 1,388 · s8 1,260 · s9 1,741 · s10 1,157. No deaths.
- **Rewards withheld**, same bot, s1–s5: no ending (s4 overgrown on day
  1,590). **Counsel steering by the leading track, no road chosen**: no ending
  (hence "Choose a road" in counsel). Scratch bot, 2×2: counsel+rewards 5/5,
  counsel only 0/5, rewards only 2/5, neither 1/5.
- **First milestone** day 1 on every seed; **Captain** days 45–76 on s1–s5
  (98 and 108 on s6, s10); Commodore 421–686; Admiral on 3 of 10; Legend none.
- **Rewards paid** per career ₡12,000–32,000 (median ₡27,000); a purse was
  short on 4 of 10 careers (the Charter's, empty when Genesis' first rung fired
  on s1 and s10). Median purse at the third year-end: ₡5,468 with the rewards,
  ₡9 without (s1–s5).
- **Counsel**: 200 seeded states in the suite — 942 moves of 15 kinds, every
  top move actionable, the blocked ones refused with exactly the words shown;
  244 simple-bot states (scratch) — 1,183 moves, 0 failures; 3 ms per
  `advise`. The daily check costs 86 µs (a day is ~1 ms).

## Deviations

- The renown chip sits in the menu bar's corner, not on the heading bar: on
  the bar at 1,040 px it pushed the meters' captions under their bars.
- No "unique fitting" rewards: credits, standing, bench work and titles only.
- A captain **chooses** a road (`renown.follow`, the Voyage's "Follow"); the
  next rung on a chosen road outranks the desk's freight run in counsel.
- No ending requirement was retuned (`sim/threat.py` untouched but for the
  counter): Genesis became reachable through counsel, research toward the
  next rung's technology first, and the track's rewards.
- Counsel's bounty rule is the hunter bot's measured threshold (guns ≥ 15,
  hull ≥ 75%), not a simulated fight.
