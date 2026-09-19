# Project review — 2026-09-17

A whole-project review of GESTALT and SEEDFALL. Five parallel reviewers each
took one area: engine code, Qt UI, tests and infrastructure, a gameplay
play-test, and the GESTALT documents. I reviewed the viewer, `sim/`,
`models3d/` and repo upkeep myself, then re-checked every **P0** item.

Every finding below was reproduced, measured or read in the source. Items
marked *(suspected)* were only read. Nothing in the repo was changed during
the review.

**Baseline.** The full suite passes: `python -m seedfall.tests` ran 199 suites
and 1,482 checks, exit 0, in 17 min 10 s on one core. The viewer check,
`models3d --check` and every README image link also pass.

**Verdict.** The engineering underneath is strong.
- Same seed, same sector under any `PYTHONHASHSEED`.
- No upward layer imports and no Qt in the engine.
- About 1 ms per game day.
- The suite is flake-free, and the document nav and anchors are clean.

The failures sit where the tests can't see:
- **Persistence breaks across a process boundary**, so Resume doesn't work
  in the shipped game.
- **Three degenerate moves beat every intended strategy.**
- **Honest play reaches no ending.**
- **The documents don't share one set of numbers.**
- **The project's own docs have outgrown the 500-line rule** they were
  written to enforce.


## Detail by area

- [seedfall.md](seedfall.md) — gameplay (#9–20), interface (#21–29), engine code health (#30–35)
- [tooling.md](tooling.md) — test suite, runner, packaging and CI (#36–43)
- [documents.md](documents.md) — the 13 GESTALT documents' content (#44–53)
- [repo.md](repo.md) — maps and logs, git, README, viewer, root `sim/` (#54–60)

---

## P0 — fix first (lost saves, crashes, a broken core flow)

1. **Resume fails for every save in a freshly launched game.** *Re-checked.*
   - **Where:** `core/save.py:69-89`.
   - **Cause:** `_REGISTRY` is filled only as a side effect of imports. After
     `import seedfall.ui.app` (all that `__main__` loads), 28 of 56
     `@register` classes are missing: `Choices`, `Envoy`, `Signal`, `Law`,
     `Settlement`, and others.
   - **Re-checked:** a 30-day save failed in a fresh process with
     `unknown type 'Envoy'`. **A scratchpad copy of the real
     `~/.seedfall/save.json` (5 Aug) failed with `unknown type 'Choices'`.**
   - **Data-loss risk:** the title screen's other two buttons (`_new`,
     `_compose`) both call `clear_save()`, so the next click deletes the
     save.
   - **Why no test caught it:** every test that loads a game does so in the
     process that wrote the save.
   - **Fix:** in `load_game`, import every `seedfall.sim` module via
     `pkgutil`, or keep an explicit registry. Make `encode` refuse
     unregistered dataclasses. Add a check that saves in one subprocess and
     resumes in another. **S**

2. **Id counters live in the process, not the save.**
   - **Where:** 15 modules hold `_uid = itertools.count(1)`
     (`sim/ship.py:22`, `colony.py:19`, `contracts.py:23`, …).
   - **Effect:** after a reload, a new hull gets uid 1, the same as the
     flagship. Switch flag, save and load, and the fleet became
     `[('Second Hull',1),('Second Hull',1)]`: **the original flagship was
     gone** (relink at `core/state.py:427-430`).
   - **Also seen:** duplicate contract, settlement and memory ids after two
     years.
   - **Fix:** a saved `Game.next_ids` plus `game.next_id(kind)`, or reseed to
     max+1 on load. **M**

3. **Attributes set at runtime are silently dropped by the save.**
   - **Examples:** `Game.short_days` (hunger debt), `Game.conn_seconds` (a
     tutorial lesson), `Game.crew_leaving`, `DiplomaticState.approached`
     (the envoy quiet period), `Officer._warned`.
   - **Effect:** two runs, one reloaded, diverge within 1–30 days.
   - **Fix:** declare them as fields. Use `slots=True` on registered
     dataclasses, or assert in `encode` that `__dict__` holds no undeclared
     keys. **S**

4. **A clock step shorter than a day runs the whole daily tick.**
   - **Where:** `clock._one_step`. `berthing.charge_flown` calls
     `advance_days(owed/86400)` on every 250 ms flight beat.
   - **Starvation is forgiven:** colonies starving for 392–456 days reset to
     0 after one 30-second step (`colony.tick` finds `owed = 0` affordable).
   - **Patrol stops multiply:** `enforce.py:299` floors the span at 0.2 days,
     so 5,000 slices totalling 0.0005 days gave 10 Charter stops.
   - **Cost:** 1,000 slices a day ran 30 days in 21.7 s, against 0.04 s for
     whole days.
   - **Fix:** carry the fraction, and return before `rng("tick")` when no
     whole day has passed. **S**

5. **Any exception in a slot kills the shipped game without saving.**
   - **Cause:** `ui/app.py` never installs `sys.excepthook`. Only the tests
     do.
   - **Trigger found:** two keys queued in the Help search (fast typing)
     abort with exit 134 (`help_view.py:72`: a deferred `setFocus` on a
     deleted `QLineEdit`).
   - **Fix:** install a hook that saves, shows a toast and writes a crash
     log, and look the box up again inside the deferred call. **S**

6. **All 15 screen shortcut keys do nothing.** *Re-checked.*
   - **Cause:** `ui/window.py:158` (rail button) and `ui/menubar.py:49`
     (Screens menu) bind the same key, and Qt reports "Ambiguous shortcut
     overload".
   - **Measured:** 0 of 15 keys work. With the rail shortcuts removed, 15 of
     15 work.
   - **Fix:** keep the menu binding only, and add a test that sends real key
     events. **S**

7. **The `tripwire` suite rewrites real source files on every run.**
   *Re-checked.*
   - **Where:** `tests/test_tripwire.py:148-302`.
   - **Files rewritten:** `sim/exchequer.py`, `data/bloom.py`, `sim/tug.py`,
     `data/gates.py`. After this review's run, **`data/bloom.py`,
     `data/gates.py`, `sim/tug.py` and `data/exchequer.py` were left mode 600
     instead of 644** (restored by hand; git does not track the difference).
   - **Other problems:** the `tug.py` check has no `finally` restore, and
     overlapping runs ("the normal case", per `tests/__init__.py`) can import
     a constant while it is mutated.
   - **Fix:** mutate a temp copy of the package (parameterise
     `sweepkit.ROOT`). **S–M**

8. **Damaged or older saves crash or vanish.**
   - **Crashes:** `save.read` catches only `OSError`, `ValueError` and
     `KeyError`. A missing required field raises `TypeError` (143 required
     fields in 40 classes, so adding one breaks every older save), and a list
     payload raises `AttributeError`.
   - **Silent loss:** a save with `version != 1` returns `None` with no
     message.
   - **Missing safeguards:** no migration table, no invariant check, no
     `fsync`, and a fixed `save.tmp`.
   - **Fix:** catch everything and move a bad file aside as `.bad`; add
     migrations keyed by version; keep golden old saves under
     `tests/fixtures/`. **M**

---

## Suggested order

1. **Saves (#1–4, #8).** One focused pass with a cross-process test. This is
   the only item where players are losing their game today.
2. **Crash and input (#5, #6, #30) and test safety (#7, #37).** Mostly
   one-line fixes.
3. **The three exploits (#9–11).** Then re-measure #12, because the endings'
   pacing can only be judged once the shortcuts are closed.
4. **Tooling (#36, #41, #43).** Parallel runner, pyproject and CI, so the
   rest of this list is cheap to verify.
5. **Documents (#44–46).** The three corrections a careful reader would find
   first.
6. **Maps and logs (#54–57).** Bring them back under the 500-line rule.
