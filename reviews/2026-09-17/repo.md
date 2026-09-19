# Review 2026-09-17 — Repo, project docs and the small packages (#54–60)

Part of the [whole-project review](README.md).

## P2 — repo, docs-about-the-code and the small packages

54. **The navigation maps are longer than the rule they enforce.**
    - `seedfall/INTERFACE.md` is **6,383 lines**, and its "What this is"
      section alone runs 3,276. `seedfall/IMPROVEMENTS.md` is 1,098.
    - Your own rule is "every file under 500 lines" and "read INTERFACE.md
      first", and a 6k-line map defeats both.
    - **Fix:** keep INTERFACE.md to a ≤400-line map and move design history
      to `seedfall/notes/*.md`; split IMPROVEMENTS.md into `open.md` and
      `done-2026-08.md`. **M**

55. **The root `SESSION_LOG.md` is 747 KB and stale since 2026-08-02.**
    - `seedfall/SESSION_LOG.md` took over, so the root log no longer meets
      the "keep it updated" rule.
    - Its 271 committed revisions are most of the git history.
    - **Fix:** archive it by month under `logs/` and keep a short root
      index. **S**

56. **Git is 100 MB of loose objects and has never been packed.** A packed
    copy measures 11.9 MB, so `git gc` cuts about 88 MB. **S**

57. **Stale counts and descriptions.**
    - **README:** "55 suites, 458 checks" (199 / 1,482); "239 modules, every
      one under 500 lines" (567, at least 10 over); a broken
      `#the-ten-documents` anchor; "ten levels of zoom".
    - **Root INTERFACE.md:** says "eleven" documents in one place and
      "thirteen" in another, leaves out `viewer/models_page.py`, and claims
      "no third-party dependencies".
    - **Other docs:** the fleet doc says "six" documents and the compendium
      "seven".
    - **Screenshots:** `assets/seedfall/*.png` date from 28 July, before the
      flight deck; regenerate them with `python -m seedfall.tests.capture`.
    - **`deepen-roadmap.md`** (79 KB) belongs to a finished loop; archive
      it.
    - **Effort:** S.

58. **Viewer.**
    - The landing-page order differs from the in-document nav order (fleet
      before LICHEN; the class reference last).
    - Dossier and Earth Program share the 🌱 icon, and there are two
      "3D Models" cards, both 🛸.
    - `/models` loads model-viewer from unpkg, so the "offline" claim is
      false for that page.
    - The favicon isn't URL-encoded in the data URI.
    - There are no tests beyond `--check`, and nothing runs `--check`.
    - **Effort:** S.

59. **Root `sim/`: several "simulations" have their answers built in.**
    - `life_support` sets photosynthesis equal to respiration by
      construction.
    - The interior temperature is a constant 293 K.
    - `energy_budget` returns literals and ignores its `design` argument.
    - The "CO₂ ppm" curve is O₂ mass-ppm relabelled.
    - `params.py` disagrees with the documents: ARCA is 12 Gt (the docs say
      2–3 Gt), GRAVID has 6 cradles (the docs say 12–24), and `o2_fraction`
      is a mole fraction labelled as a mass fraction, which is why the O₂
      reserve comes out at 125 yr against 140.
    - **Fix:** label the illustrative ones as illustrative, or model them;
      add a params-vs-documents check. **S–M**

60. **Housekeeping.**
    - Two unrelated top-level packages are both called `sim` (root `sim/`
      and `seedfall/sim`).
    - `.gitignore` lacks `.coverage`, `htmlcov/`, `.pytest_cache/`, `.venv/`
      and `*.swp`.
    - Log grammar: "1 of the crew are dead", "cut back to a Outpost".
    - **Effort:** S.
