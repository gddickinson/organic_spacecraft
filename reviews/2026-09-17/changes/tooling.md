# Stream D: tooling (review items #38 to #43)

What changed, how it was verified, and the text for the project maps and
READMEs, which this stream was not allowed to edit.

## Registry edits (`seedfall/tests/suites.py`)

| Key | Module | Change |
|---|---|---|
| `bridge` | `test_bridge_protocol` | Was `test_bridge`. Now the restored protocol and socket suite. |
| `bridgescreen` | `test_bridge` | Was `bridge2`. The duplicate row is gone. |
| `unattended` | `test_unattended` | New, split from `test_robots`. |
| `boats` | `test_boats` | New, split from `test_control`. |
| `plotting` | `test_plotting` | New, split from `test_conn`. |
| `orbitheight` | `test_orbit_height` | New, split from `test_orbits`. |
| `licences` | `test_licences` | New, split from `test_industry`. |

Also changed:
- `tripwire.py`: `bridge2` became `bridgescreen` in `SLOW`, and `licences` was added (2 s alone).
- `tripwire_kin.py`: the fast paths for `robots`, `telepresence`, `tug`, `conn`, `autopilot`, `track`, `orbits` and `industry` now also name the split suites.
- `test_length.ALLOWED`: the five `tests/*` rows are struck. Those files are now 434, 394, 466, 286 and 362 lines.

**At merge:** the harness guard's new check, "every check module runs exactly once", fails on any `test_*.py` that has no row. Register the other streams' new suites, or name them in `test_harness_guard.HELPERS`. Its second new check, "no check can pass by looking at nothing", also reads their files. Add a guard, or a row in `VACUOUS_OK` with a reason.

## #38 Bridge tests
- **Restored:** `tests/test_bridge_protocol.py`, from `785db99`, updated to today's 21 verbs. It has 12 checks:
  - every verb answers and serialises (both ways round against `VERBS`);
  - `describe`, `plain`, and a full session over a real socket;
  - the token is per bridge, and wrong, missing, foreign or upper-cased tokens are refused, including for the server-side verbs `seat`, `snapshot` and `verbs`;
  - junk lines get an answer and the line stays up;
  - an unserialisable reply costs one answer, not the socket;
  - the lock means only one command is inside the game at a time: 3 callers × 25 commands, measured at most 1 at once;
  - `bye` and `stop` close cleanly and release the port;
  - it binds loopback only;
  - `python -m seedfall.bridge` works across processes: a real wait, `--load` with no save is refused, and SIGINT exits 0;
  - **the attached bridge** runs every command on the Qt thread, checked by a probe verb.
- It does not fuzz arguments; that is `test_bridge_guard`.
- **Harness guard** (`test_harness_guard.py`): no module is registered twice, and every `test_*.py` is registered or listed in `HELPERS`. `test_controls` is listed there because `test_verbs` drives it. Both failure modes were demonstrated.

## #39 Weak checks
- **The scan** is in `tests/checkscan.py`, and runs as the harness check "no check can pass by looking at nothing". The naive count was 85:
  - 30 loop over a literal, cannot run empty, and are exempt by rule;
  - the other 55 got guards: `assert rows`, or a floor measured first;
  - `VACUOUS_OK` is empty.
- A check that delegates to a module helper which asserts counts as asserting.
- **`test_ui` 198, 214, 266 and 418** now have behavioural assertions:
  - picking a hull selects it and lights exactly one card;
  - at least 6 body kinds, and the detail panel is headed with the selected body;
  - the xeno tally goes 0 → 1 → 12 of 12;
  - all 15 screens render on a bare game, and the HUD reads ₡0.
- **Test bugs the guards exposed, now fixed:**
  - `test_surveys`: the coast path never ran (0 re-checks).
  - `test_reach`: returned early, claiming it had checked another seed.
  - `test_tuning`: the levy check called a `territory.levy_on` that never existed.
- **`x == x`:** `math.isfinite` is used in `test_sim` at 3 sites.
- **Source-text pinning replaced with watched paints:**
  - `test_sights`: each camera of a Conn screen is painted into a `QImage`, and the box `_target` returns must be the one `draw_sights` is told to keep off.
  - `test_bridge_marks`: the feed is painted and must hand over its own `sights`.
  - `test_flightdeck`: Engage is pressed. It must call `transit.begin` and never `travel_to`, open the transit screen and leave day and orbit unchanged.
- **`WITHDRAW_AT`:** pinned by what a deployed consort does. It stays in the line at 26% hull and breaks off at 18% (measured: 22%). Mutated in memory, ×2, ×0.5, ×1.25 and ×0.8 all fail.
- **`test_works3d`:** the expectations are now pairs, so the chorus-node dish is checked.
- **`test_lighting`:** imports `render3d` for its message.
- **Chronicle:**
  - `_study_here` now walks `research.researchable`. A decade now researches 21 technologies, where it was 0. `play()` reports `researched`, and `test_chronicle` asserts at least 10.
  - Research changed the path of the `wayhome` seed. It stalled for 5 years between two ports that had shunned the captain. `_move_on` now seeks a quay where `enforce.may_trade` is true.

## #40 Order dependence and optional Qt
- **`test_controls` "long session":** re-measured, it still differed: 153 days alone, 151 after the verbs checks. The cause is `core/ids._NEXT`, which `new_game` never resets; ids feed the dice (`game.rng(f"instar-{id}")`). The check now clears the counters first, and gives 153 both ways.
- **`mesh` and `orders`:**
  - `orders` takes `NAV` from `data.screens`;
  - `mesh` imports `ui.mesh_panel` inside the two checks that need it.
- **The harness now skips Qt checks** when PyQt6 is really absent, by name and count, and fails as before where Qt exists. Measured with PyQt6 blocked by a `sitecustomize`: before, 84 suites were red on 174 checks, every one the same missing import. After: `201 suites · 1231 checks · 0 failed · 22 skipped (+174 checks skipped for want of PyQt6)`, exit 0.
- **`--require-qt`** turns every skip into a failure, and refuses to start where Qt cannot import (exit 1).

## #41 pytest shim
- `tests/pytest_shim.py` gives one test per suite, each run through the runner's `--child` in its own process.
  - `SEEDFALL_INPROCESS=1` runs in-process instead, which `pytest --cov` needs.
  - `SEEDFALL_REQUIRE_QT=1` is the pytest form of `--require-qt`.
- `pyproject.toml` sets `python_files = ["pytest_shim.py"]`, `testpaths`, and `-p no:pytestqt`.
- It was renamed from `pytest_suites.py`, because `-k ui` matched "s**ui**te" and selected all 201 suites.
- Verified:
  - `pytest --collect-only` finds 206 tests;
  - `-k "combat or window"` selects 3;
  - `--durations` and junit work (3 tests, 0 failures);
  - pytest-cov works in-process;
  - with no Qt: 179 passed, 22 skipped.

## #42 Shared Qt set-up, duplicate runs, long files
- **`tests/qtkit.py`** provides:
  - `use_offscreen()`;
  - `app()`, which holds the application;
  - `overlap()`;
  - `redirect_save()`, which asserts that the save path is not `~/.seedfall/save.json`;
  - `main_window(game)`, which redirects the save first, then stubs dialogs, confirm and toast.
- **Migrated:** all 18 `_app` copies (11 identical, 7 variants) and 4 `_overlap` copies. `test_ui._use_offscreen` is now an alias, because 69 files import it.
- **Not migrated:** the 89 inline `QApplication.instance() or QApplication([])` sites. They were left alone to avoid churn.
- **The six five-year bot runs** go through `captain_bot.five_year_runs()`, memoised per process. That is about 10 s saved when `play` and `stranded` share a process.
- **Files split:**

  | Original | Before → after | New file |
  |---|---|---|
  | `test_robots` | 624 → 434 | `test_unattended` (214) |
  | `test_control` | 560 → 466 | `test_boats` (119) |
  | `test_conn` | 523 → 286 | `test_plotting` (269) |
  | `test_orbits` | 567 → 394 | `test_orbit_height` (199) |
  | `test_industry` | 520 → 362 | `test_licences` (186) |

  Check totals are preserved (75 across the ten suites plus `length` and `harness`).

## #43 Infrastructure
- **`pyproject.toml`:**
  - project `gestalt-seedfall`, version read from `seedfall.__version__`;
  - `requires-python >= 3.10`, `PyQt6>=6.4`;
  - extras `[sim]`, `[models]` and `[dev]`;
  - console script `seedfall`;
  - config for pytest, coverage and ruff.
- **`pip install -e ".[dev]"`** was tested in a scratch venv with a network connection. It installed PyQt6 6.11, pytest 9.1 and ruff 0.16.8. From that venv, outside the tree:
  - the `seedfall` entry point resolves;
  - 7 suites under `--require-qt` are green;
  - pytest and ruff pass.
- **ruff** was installed only in a scratch venv. It runs `F`, `E9` and `B` at 99 columns, and the tree passes.
  - Temporary global ignores, counted: F401 198, B905 124, B007 37, F841 21.
  - Temporary per-file ignores cover the 39 rarer findings, one row per file.
- **`.github/workflows/ci.yml`:**
  - ruff;
  - a 3.10/3.11/3.12 matrix with the Qt libraries and `SEEDFALL_SAVE` in `$RUNNER_TEMP`;
  - `viewer/app.py --check` and `models3d.run --check`;
  - `--fast --require-qt -j 4` on push and PR;
  - the full suite nightly, with `--coverage` on 3.12 and the map uploaded.
  - The YAML parses. It has not been run on GitHub.
- **`--fast`** runs the suites `tripwire` treats as cheap: 100 suites, 30 s at `-j 4`.
- **`.gitignore`** additions: `.coverage*`, `htmlcov/`, `coverage-out/`, `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `.venv/`, `build/`, `dist/`, `*.swp`.

## Coverage (`--coverage [DIR]`, `tests/coverage_map.py`)
- Each suite's child runs under `coverage run` with its own data file. The runner writes:
  - the per-suite files;
  - the combined `.coverage`;
  - `coverage-map.json`: module → the suites that execute it, per-package totals, and the modules nothing executes.
- Measured on `--fast` (100 suites): **74.0%**.

  | Package | Coverage |
  |---|---|
  | sim | 79% |
  | ui | 62% |
  | core | 80% |
  | data | 98% |
  | world | 95% |
  | bridge | 23% (`bridge` is a slow suite) |

  12 modules are executed by nothing in that set. `bridge/attached.py` is one of them; so are `ui/crash.py` and `ui/options_view.py`.
- On `sim`, `bridge` and `harness`: 40.8% overall, and bridge 78%.

## Game bugs found, not fixed
1. **`ui/yard_view.py`:** the shipyard's "All (N)" hull tab snaps back to the first family. `_hull_picker` resets any family that is not real, and "all" is not one. It shows 5 of the 11 hulls.
2. **`sim/xeno.py`:** `__all__` names `known`, which does not exist, so `from seedfall.sim.xeno import *` raises AttributeError (ruff F822).
3. **`core/ids`:** `new_game` does not reset the id counters, and ids seed dice. The same seed plays differently in a fresh process and after "Begin again" in the same one.
4. **`bridge/client.py`:** `Client.send` raises `ConnectionResetError` when the far end has closed, instead of answering `{"ok": False, ...}`. Seen under `--coverage` timing.
5. **`bridge/server.py`:**
   - `_talk` lets a client reset escape its thread as an uncaught exception, which pytest reports as a thread warning;
   - the token is compared with `!=`, not `secrets.compare_digest`. This is minor, since the server is loopback only.

## README text to paste

Add to the root README, under "Run the viewer" or a new "Install" section:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .              # the game: `seedfall`, or python -m seedfall
pip install -e ".[sim]"       # + numpy, matplotlib, Pillow for the root sim/
pip install -e ".[models]"    # + trimesh for models3d/
pip install -e ".[dev]"       # + pytest, pytest-cov, coverage, ruff
```

Add to the SEEDFALL README, under running the checks:

```bash
python -m seedfall.tests -j 8             # every suite, a process each
python -m seedfall.tests --fast -j 4      # the ~100 cheap suites (what CI runs on a push)
python -m seedfall.tests sim combat       # just these; --list shows them all
python -m seedfall.tests --require-qt     # a suite skipped for want of PyQt6 fails
python -m seedfall.tests --coverage out/  # per-suite coverage + out/coverage-map.json
pytest -k "combat or window" --durations=10 --junitxml=out.xml   # the same suites via pytest
ruff check .                              # F, E9, B; config in pyproject.toml
```

Checks write their saves to a per-process scratch file, never to `~/.seedfall`.
Set `SEEDFALL_SAVE=/some/path.json` to choose where.

Suggested CI badge and paragraph: "CI (`.github/workflows/ci.yml`) runs ruff, the document and model checks, and the fast suites on Python 3.10, 3.11 and 3.12 for every push and pull request. It runs every suite nightly, recording per-suite coverage on 3.12."

## INTERFACE.md rows to add under `seedfall/tests/`
- `qtkit.py`: shared Qt set-up (`app`, `use_offscreen`, `overlap`, `redirect_save`, `main_window`). Not a suite.
- `checkscan.py`: static scan for checks that pass on an empty loop or assert nothing. Used by `harness`.
- `coverage_map.py`: the runner's `--coverage`, per-suite data and the module→suite map.
- `pytest_shim.py`: the only file pytest collects; one pytest test per suite.
- `test_bridge_protocol.py` (`bridge`): the protocol, loopback server, client, token and attached bridge.
- `test_unattended.py`, `test_boats.py`, `test_plotting.py`, `test_orbit_height.py`, `test_licences.py`: the splits listed above.
- `captain_bot.five_year_runs()`: the six memoised five-year runs.

## Full suite, final
`python -m seedfall.tests -j 4` exited 0:
`206 suites · 1505 checks · 0 failed checks · 0 skipped · wall 333 s · suite time 1333 s`.
The baseline before this stream was 201 suites and 1,497 checks.
