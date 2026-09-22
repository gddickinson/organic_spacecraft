# INTERFACE.md — GESTALT project navigation map

The top-level map of this repository. Read it before opening source files.
Every package has its own map, linked below.

## What this project is

**GESTALT** is a conceptual design programme for living spacecraft and
habitats grown from a seed. The main deliverable is **thirteen**
self-contained, cross-linked HTML documents (published as claude.ai
artifacts), readable offline through a small Python viewer.

The documents' load-bearing numbers are recomputed in Python and checked
against the text: `calcs/` holds the calculations, and `python -m calcs
--check` compares 291 tagged numbers. Every claim is cited to real published
sources, with DOIs where one exists.

Alongside the documents:
- **`sim/`:** simulations of the main designs' systems, rendered as animated
  GIFs.
- **`models3d/`:** exportable 3D models of the designs.
- **SEEDFALL (`seedfall/`):** a playable PyQt6 space exploration, trading and
  combat RPG built on the documents. It is much the largest part of the
  repository, with about 840 modules.

## Layout

```
organic_spacecraft/
├── INTERFACE.md          ← you are here
├── README.md             how to run everything, and what each document is
├── SESSION_LOG.md        the running log (recent); history in logs/
├── play.py               starts the game from here: `python3 play.py [--new] [--help]`
├── pyproject.toml        packaging: `pip install -e ".[sim,models,dev]"`, pytest and ruff config
├── .github/workflows/    CI: ruff, the doc/model checks, the fast suites; the full suite nightly
├── docs/                 the thirteen documents (artifact fragments; see below)
├── calcs/                the documents' numbers, computed and checked   (calcs/INTERFACE.md)
├── sim/                  design simulations → animated GIFs              (sim/INTERFACE.md)
├── models3d/             3D models → glb / obj / stl                     (models3d/INTERFACE.md)
├── viewer/               zero-dependency local viewer for docs/ and the models
├── seedfall/             the game                                        (seedfall/INTERFACE.md)
├── assets/               figures (from the docs' SVGs), sim GIFs, model exports, game screenshots
├── reviews/2026-09-17/   the whole-project review, the plan, ten innovation designs,
│                         each work stream's merge notes (changes/), and STATUS.md
└── logs/                 the session log archive (31 parts) and the finished design loop
```

## The documents (`docs/`)

These files are **artifact fragments**, not complete HTML documents: they
begin at `<style>` and hold only head-and-body content. When they are
published, the host adds the `<!doctype html><head>…</head><body>` skeleton
and a minimal reset, and the viewer re-creates that skeleton offline.

Documents link to each other through `https://claude.ai/code/artifact/<id>`
URLs, which the viewer rewrites to local `/d/<slug>` routes. Every document
carries the same 13-entry programme nav, in the catalogue's order.

The fleet registry, dossier, drawings, habitat and compendium documents run
to 600–1,300 lines each. They are single-file published artifacts and are the
one deliberate exception to the 500-line rule.

## The viewer (`viewer/`)

Each module's job:
- **`catalog.py`** is the single source of truth: `Doc` records (slug, file,
  artifact id, title, kind, icon, blurb) in nav order. To add or rename a
  document, edit only this file.
- **`wrap.py`** turns a fragment into a standalone page and rewrites the
  artifact links.
- **`index.py`** is the landing page. **`models_page.py`** is the `/models`
  gallery; it needs a network connection for model-viewer, while the model
  files themselves are local.
- **`links.py`** audits every document: the nav is in catalogue order, every
  artifact id is known, and every `#anchor` exists.
- **`app.py`** is the HTTP server and CLI. `--check` loads every document and
  runs the link audit.

The data flows `app.Handler` → `catalog` → `docs/<file>` → `wrap.wrap()` →
the response.

```
python3 viewer/app.py            # http://127.0.0.1:8731   (--open, -p PORT)
python3 viewer/app.py --check    # every document loads, every link holds
python -m calcs --check          # every tagged number matches its calculation
python -m sim.run --check        # the simulations build; params match the docs
python -m models3d.run --check   # the models build and validate
```

The viewer is standard library only. `sim/` needs numpy, matplotlib and
Pillow; `models3d/` needs trimesh and scipy. The game needs PyQt6. Each set is an extra
in `pyproject.toml`.

## SEEDFALL (`seedfall/`)

The game is a separate desktop application, not part of the viewer. Start
with [`seedfall/INTERFACE.md`](seedfall/INTERFACE.md), which covers the
layers, the rules that bite, and a generated map for each package.

```
python3 play.py                      # play (or: python -m seedfall)
python3 play.py --help               # every option, and where the save lives
python -m seedfall.tests -j 8        # every suite, about 3 minutes
```

## Standing rules for this repository

- **Every source file is under 500 lines.** In the game, `tests/test_length`
  enforces this with no debts left. The published HTML documents are the one
  exception.
- **Maps are kept honest.** Root and per-package `INTERFACE.md` files are
  updated when structure changes. In the game they are generated
  (`python -m seedfall.tests.maps --write`) and checked by the `maps` suite.
- **`SESSION_LOG.md` is kept current.** Older entries go to `logs/`.
