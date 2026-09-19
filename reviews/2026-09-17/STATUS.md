# Status: where each review item was fixed

This file maps each of the 60 findings in this folder, plus the ten
innovations, to the module that fixed it and the suite that pins it. Each
work stream's own merge notes are in [`changes/`](changes/) (engine, ui,
rules, tooling, docs, sound, nemeses, lines, hull, reaches, assembly, …).
Item numbers are the review's own.

## P0: saves, crashes, a broken core flow (fixed directly in Phase 0)

| # | Finding | Fixed in | Pinned by |
|---|---|---|---|
| 1 | Resume failed in every fresh process | `core/save.ensure_registry` imports every saved type before a read; `encode` refuses an unregistered dataclass | `persistence` (resume across two process boundaries) |
| 2 | Id counters lived in the process | `core/ids.py`: each chronicle has its own book (`Game.ids`), bound on new/load/advance and restored to at least max+1 on load | `persistence` (fresh id, same seed after another chronicle) |
| 3 | Runtime attributes dropped on save | Six are now declared fields. `save.STRICT` under test refuses undeclared attributes. They were found by tracing `__setattr__` over the whole suite | every suite (STRICT), `persistence` |
| 4 | Sub-day clock steps ran the daily tick | `core/clock._one_step` carries the fraction and returns before any tick or luck; only contracts settle | `persistence` (2,000 slices; a starving colony is not forgiven) |
| 5 | A slot exception killed the game | `ui/crash.py` (crash log, recovery save, message); `help_view._refocus` | `persistence`, `window` |
| 6 | All 15 screen keys dead | the rail no longer binds keys; the menu owns them | `screenkeys` (real key presses) |
| 7 | The tripwire rewrote source files | `sweepkit.sandbox()` works on a copy; `put` keeps file modes | `tripwire` (tree mtimes unchanged) |
| 8 | Damaged or old saves crashed or vanished | `save.read` never raises and moves bad files to `.bad`; version migrations; `core/loading.validate`; fsync; `.bak` | `persistence` |
| — | **Found while fixing:** a headless probe overwrote the player's save | `save.save_path()` sends offscreen and minimal processes to a temp file | `persistence`, `savefile` |

## Phase 1: the review in five streams

**Rules (A):**

| # | Fixed in | Pinned by |
|---|---|---|
| 9 Lineage on day 21 | `Ship.launched_on`, `threat.line_of`, `LINEAGE_AGE`; licence checked in `start_build` | `exploits` (earliest day 515) |
| 10 Re-sweeps paid forever | `Body.survey_q`/`surveyed_on`; survey sales go through `apply_sale` | `exploits` (441 → 4 cr/day) |
| 11 Standing for sale | `Market.yours`, `trade.imported` | `exploits` (40 → 40 after 79 round trips) |
| 12 Back-loaded Bloom | a monthly allowance of new infestations shared by throws, instars and the Weave | `rulebook`, `endgame`, `bloom` |
| 13 Death only in the window | `aftermath.resolve` calls `game.die` | `rulebook`; seeking a fight is covered by innovation 3 |
| 14 Envoys from day 1 | `approach.GRACE_DAYS`, `set_aside`, `holds` | `rulebook`, `envoy` |
| 15 Boxed-in starts | `sim/passage.py` charted lanes | `rulebook` (40 seeds: 0 boxed in) |
| 16 Small rule bugs | licence in `can_found`; `Contract.taken_on`; `Quote.shocked`; `research.shortage_news` | `rulebook` |
| 17 Text contradicting the game | counts computed from data | `rulebook`, `manual` |
| 18 Take-command overfill | `consorts.take_command(_terms)` | `exploits` |
| 19 Screens changed the future | per-key RNG in `contracts.board_for`; recruit and rumour boards (B) | `exploits`, `uirules` |
| 20 Stores spent in opposite orders | `sim/stores.py`, the one door | `rulebook`, `solvency` |

**Interface (B):**

| # | Fixed in | Pinned by |
|---|---|---|
| 21 Clipping | `view_base.Pane`, `WrapRow`, horizontal scroll as needed, the log folds below 1300 px | `fit` (0 of 15 screens overflow at 1040×680) |
| 22 Battle below the fold | `battle_orders.py`, pinned panes | `fit` (20/20 orders in view at 1360×880) |
| 23 Whole-screen rebuilds | `log_panel` (incremental), `tech_tree`, `market_grid`, `View.keep` | `fit` (Tech refresh 325 → 28 ms) |
| 24 Cameras re-simulated per paint | `viewport_hud.world` cache | `flightsame` (143 → 64 ms a beat) |
| 25 Keyboard and focus | focusable `Card`, `focus.py`, `PickList` beside the chart, accessible names | `keyboard` |
| 26 Visual fixes | the theme (flat ≠ disabled, transparent panels), 2×2 HUD, log glyphs, ground legend, layer pills, legend swatches, chart layout | `fit` |
| 27 Pop-outs never freed | `popout.py` (`WA_DeleteOnClose`) | `popouts` |
| 28 Rules in `ui/` | the sim acts log themselves; `sim/commitments.py` | `uirules` (AST allow-lists) |
| 29 Inconsistencies | `util.reaction_mass`, `thrust_pad.py`, one Computer row | `fit`, `flightpix` |
| — | One save slot (backlog) | `core/slots.py`, `chronicle_picker.py`, "Save as…" | `slots` |

**Engine (C):**

| # | Fixed in | Pinned by |
|---|---|---|
| 30 Bridge validation | `bridge/checks.py`; NaN refused at parse; `shot` limited to a basename; line cap; ambushes fought | `bridgeguard` (378 hostile calls) |
| 31 The LLM blocked the UI thread | a deadline and circuit breaker in `core/llm.py`; comms runs off-thread | `llmguard` |
| 32 Imports and dead code | re-entrancy guard; `xeno.__all__`; dead functions removed | `engineguard`. Tree-wide pyflakes: see Phase 3 |
| 33 Broad excepts | `core/guard.swallowed` | the full suite runs with the guard raising |
| 34 Performance | `exchequer.income` memo; `tick_market` | 0.86 → 0.79 ms/day, state hashes identical |
| 35 Long files | 8 sim/data splits; `clock` into `shiptime`/`sectortime`; 4 ui; 5 tests; `core/loading`; `data/help_more` | `length` (**no debts left**) |

**Tooling (D):**

| # | Fixed in | Pinned by |
|---|---|---|
| 36–37 Serial runner; a CLI that lied | `tests/runner.py` (`-j`, `--fast`, `--list`, `--require-qt`, `--coverage`); unknown suite exits 2 | 17 min → about 3 min |
| 38 Bridge tests lost | `test_bridge_protocol`; duplicate guard | `bridge`, `harness` |
| 39 Weak checks | `checkscan.py` (55 guarded); the chronicle now researches | `harness` |
| 40 Order dependence; optional Qt | per-chronicle ids; lazy Qt | `harness` |
| 41 pytest | `tests/pytest_shim.py`, `pyproject.toml` | `pytest -k …` |
| 42 Coverage; duplicated setup | `tests/qtkit.py`; `--coverage` (74% on the fast set) | — |
| 43 No packaging, CI or lint | `pyproject.toml`, `.github/workflows/ci.yml`, ruff config | CI, green on 3.10–3.12 (the first runs found scipy missing from `models`, eleven lint errors, a hard-coded home path and a CPU budget in seconds) |

**Documents (E):** items 44–53 and 59.
- NAVIS is one body everywhere.
- The Grün flux is fixed.
- The metabolism energy gap is admitted and named as a bet.
- ARCA's shield and hoop load are fixed.
- Cross-document conflicts are resolved.
- The growth arithmetic follows the model.
- Citations are checked, with 96 DOIs.
- Accessibility (AA contrast, `data-theme`, captions, headings) is fixed.
- The small fixes are done.

The new `calcs/` package checks the numbers: `python -m calcs --check` holds 291 tagged numbers against 173 keys. Root `sim/` is honest, and its params are checked against the documents. **All 13 documents need republishing.**

## Wave A and Wave B: ten innovations

| # | Innovation | Main modules | Suites |
|---|---|---|---|
| 1 | The Far Reaches | `world/regions`, `sim/regions`, `sim/relight`, `ui/reaches_*` | `reaches` |
| 3 | Nemeses and the hunt | `sim/nemeses`, `rivals`, `rival_ends`, `hunts`, `running_dark`, `ui/hunts_panel` | `nemeses`, `nemesesui` |
| 4 | The living hull | `data/adaptations`, `sim/adaptation`, `ui/body_panel` | `adaptation` |
| 5 | Freight lines | `sim/freightlines`, `linetrips`, `lineroute`, `lineforecast`, `lineledger`, `haulers`, `masters`, `ui/house_*` | `freightlines` |
| 6 | The Assembly | `data/assembly`, `sim/assembly*`, `ui/assembly_panel` | `assembly` |
| 10 | Soundscape | `data/sounds`, `ui/synth`, `ui/audio`, `ui/soundmap` | `audio`, `soundmap` |
| 2 | The Kith | `data/kith`, `sim/kith`, `kith_acts`, `kith_world`, `ui/kith_panel`, `ui/kith_codex` | `kith` |
| 7 | Stellar phenomena | `data/phenomena`, `sim/phenomena*` (eight modules), `ui/sky_strip`, `ui/sky_chart` | `phenomena`, `skybodies`, `phenomenaui` |
| 8 | Officer arcs | `data/arcs`, `sim/arcs`, `arc_beats`, `arc_places`, `ui/arc_panel` | `arcs` |
| 9 | Renown and the Voyage | `data/milestones`, `sim/renown*`, `counsel*`, `memoir`, `ui/voyage_panel`, `counsel_card`, `renown_chip`, `memoir_panel` | `renown`, `renownui` |

## Phase 3: upkeep

| # | Item | Done |
|---|---|---|
| 54 | Maps too long | `seedfall/INTERFACE.md` went from 6,383 to 182 lines; its history is in `seedfall/notes/`. Each package map is generated (`python -m seedfall.tests.maps --write`), as are the `__init__` docstrings, and the `maps` suite fails on a missing module. `IMPROVEMENTS.md` went from 1,098 to 133 lines; the done history is in `seedfall/improvements/`. |
| 55 | Session log | Archived to `logs/` (31 parts, verbatim); both logs are current. |
| 56 | git gc | Done: 111 MiB of loose objects packed into 17.9 MiB. It was a default `git gc`, and unreachable objects are kept in a cruft pack. |
| 57 | Stale counts and screenshots | The README and INTERFACE counts are computed or checked. There are 20 screenshots, six of them new systems, regenerated by `tests/capture.py`. That script now clears a held screen after each setup, because an envoy had turned shots 12–20 into one screen. `deepen-roadmap.md` is in `logs/`. |
| 58 | Viewer | Nav order, icons and favicon encoding. `viewer/links.py` audits every link in `--check`. |
| 60 | Housekeeping | `.gitignore`, log grammar. The two `sim` packages keep their names, because renaming the root one would break the documents' and README's commands. |
| 32 | Tree-wide dead imports | A ruff F401 sweep. It removed six re-exports that callers read as `alias.name`; they are restored with `# noqa: F401` on their own lines, and the new `exports` suite finds the same shape statically. |
| — | **Found in Phase 3:** the renown chip was an empty box | A menu-bar corner re-lays out only when the corner widget itself shows. `renown_chip._relayout` sends the bar a resize. | `renownui` (the chip is as wide as its text; the speaker is inside the window) |
| — | **Found in Phase 3:** wrapped text clipped on a screen's first frame | `view_base.Pane._need` measures the column by height-for-width at the viewport's width. | `fit` (15 screens whole on the first frame; this fails on the old measure) |

## The final play-test (2026-09-18)

An independent agent played the first hour over the bridge (at 1360×880 and
1040×680) and ran three strategies for two years each. Each new system
worked where it was reached, with two caveats. No bot could afford a
relight (about ₡60k) in two years, so the Far Reaches and the Kith were
tested on a save given ₡150k by hand. And the house's one reachable line had
no profitable trade, so it never ran. The previews it compared all matched:
Assembly, Kith, relight and arcs. It found eleven defects; the fixes:

| # | Defect | Fixed in | Pinned by |
|---|---|---|---|
| 1 | Envoy deals minted and burned money (a denunciation paid +₡3,810 with no purse moving) | `approach._changes_hands`: out of the power's purse, capped at what it holds; a levy goes in; logged | `envoy` (the captain and every purse together are conserved; a thin purse pays 500 and the preview says so) |
| 11 | Importing `seedfall.tests` deleted the save its caller named, and the `.bak` | `tests/__init__._OURS`: only a path the package chose is tidied | `persistence` |
| 5 | Sky-data sale paid less than its button (wharfage unmentioned); no purse paid | `phenomena_science.sale_quote` states the due and the net, and the buyer's purse pays | `phenomena` |
| 2 | The berth lesson stuck when opened alongside | `berthing.commit` counts berths; `tutorial_watch._berthed` accepts a new one | `tutorial` |
| 3 | Sector chart stretched to 437×1,461 and blank after a list pick | `StarChart.heightForWidth`, top-aligned in its row (`WrapRow.add(align=)`) | `fit` |
| 7 | Helm burn board fell 2,000 px down after a pick | burn tabs two to a row; the crossing rows stacked (`Panel.add_stacked`) | `fit` (five bodies, side by side) |
| 4 | Academy wider than the window; "twenty-nine" over a count of 30 | stacked lesson rows; the count computed | `fit` (whole screens), by eye |
| 8 | "All 42 systems" under the Hollow's tab; the relight never said the Hollow wants 12 ly | the reach note names its region; `relight.preview["lanes"]` | by eye |
| 9 | "Younger by 25" was the new mean; signing on wrote no log line | `lifespan.sign_on` logs and returns `was` | `hands` |
| 10 | Raw `**` in Help; "A The Tessellate site"; raw floats in the Port | the data; "a site of the …"; rounded | `manual` (no raw markers in 370 paragraphs) |
| 6 | Where you may trade from (anywhere in the system) disagrees with the yard and the berth lesson | **Open**: a design pass (`IMPROVEMENTS.md`) | — |

## The final gate (2026-09-18)

- **Full suite:** 235 suites, 1,763 checks, 0 failed, 0 skipped, 201 s at
  `-j 8`, exit 0.
- **Viewer:** every document loads and every link holds. **calcs:** 291
  tagged numbers, 0 problems. **sim:** 19 parameter checks, 0 mismatches.
  **models3d:** every model builds and validates.
- **Resume across processes:** a two-year careful-captain chronicle is saved
  in one process and loaded in another, with the same state hash. After 60
  more days both processes still hash the same. A copy of the player's 5
  August save loads and plays on. The real save is untouched (sha1
  `d2dac2fd…`).
- **Honest play:** the careful captain reaches Genesis on 7 of 10 seeds within
  five years, with 0 deaths. A day costs about 1.4 ms with everything on (1.6×
  the pre-work baseline; the budget was 2×).
- **Can an honest captain afford the Far Reaches?** The careful captain
  (seeds s1–s3, three years) held ₡12k–27k between days 365 and 730, against
  a relight's ₡10k in cash. The money is there in the first two years for a
  captain who aims at it. It never relights because it follows Genesis and
  never researches Deep Weave, so an honest end-to-end relight is **not yet
  measured**.
- **Known gaps:**
  - honest trader income is still thin;
  - hunter income is below the explorer's;
  - only Genesis has been measured for honest endings;
  - the nightly full-suite job has not yet run on GitHub (push CI is green).
