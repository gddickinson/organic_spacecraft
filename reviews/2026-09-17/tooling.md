# Review 2026-09-17 — Tests and tooling (#36–43)

Part of the [whole-project review](README.md).

## P1 — tests and tooling

36. **17 minutes, serial, on one core of ten.** The top 4 suites (verbs,
    politics, pilotscreen, chronicle) take 37%. **Fix:** `-j N` with one
    subprocess per suite (per-pid saves already make that safe). Estimated
    about 2.5 min, and a segfault would then be pinned to one suite. **M**

37. **The test runner lies.**
    - An unknown suite name runs nothing and exits 0 (*re-checked*).
    - `--help` runs all 199 suites.
    - One exception in a suite's setup ends the whole run.
    - Output is block-buffered, so a hard crash loses finished results.
    - There are no per-suite timings or totals.
    - **Fix:** argparse, `--list`, try/except per suite, `flush=True`, and a
      timing table. **S**

38. **What is missing: bridge server tests and a real cross-process save
    test.**
    - `bridge` and `bridge2` both point to `test_bridge`, so it runs twice.
    - The protocol and socket tests from `785db99` were replaced; `server`,
      `client` and `attached` have 0% coverage.
    - **Fix:** restore them as `test_bridge_protocol.py`, and add a guard
      against a module being registered twice. **S**

39. **Weak checks.**
    - 86 checks whose only assertions sit inside a loop, so they pass on
      zero iterations.
    - `test_ui.py:198,214,266,418` contain no assertions at all.
    - `credits == credits` is used as a finiteness test.
    - Source-text matching in `test_sights`, `test_bridge_marks` and
      `test_flightdeck`.
    - `test_tuning` checks a range wide enough that doubling the value
      passes.
    - `tests/chronicle._study_here` passes approach ids to `set_project`, so
      **the decade-long chronicle never researches anything**.
    - **Effort:** S each.

40. **Order-dependent results, and optional dependencies.**
    - `test_controls.py:205` gives different counts in the full run than
      alone; per-process uid counters (#2) are the likely cause.
    - Without PyQt6, the `mesh` and `orders` suites crash the run instead of
      skipping.
    - **Effort:** S–M.

41. **Add a pytest shim rather than migrating.** A 20-line file
    parametrised over `SUITES` already works: selection by name,
    `--durations`, junit output, pytest-cov and xdist. Keep the `Suite`
    harness. **S**

42. **Coverage and duplicated setup.**
    - **Coverage:** 45% overall (sim 56%, ui 19%), and `core/llm.py` is 28%.
      The root `sim/`, `models3d/` and `viewer/` have no tests at all.
    - **Duplication:** `_app()` is defined 22 times and 89 files build their
      own `QApplication`; move that into `tests/qtkit.py`.
    - **Test files over 500 lines:** `test_robots` 624, `test_orbits` 567,
      `test_control` 560, `test_conn` 523, `test_industry` 520.
    - **Effort:** S–M.

43. **Nothing declares the dependencies or runs the checks.**
    - No `pyproject.toml`, requirements, CI or lint config.
    - The READMEs say only `pip install PyQt6`, but root `sim/` needs numpy,
      matplotlib and Pillow, and `models3d/` needs trimesh.
    - The interpreter in use is the borrowed `flika` conda env, which mixes
      PyQt5 and PyQt6.
    - The suites pass on Python 3.10–3.12.
    - **Fix:** a pyproject with `requires-python>=3.10` and `[sim]`,
      `[models]` and `[dev]` extras; a GitHub Actions workflow with a fast
      set per PR, the full suite nightly and `viewer/app.py --check`; ruff
      rules F, E9 and B. **M**
