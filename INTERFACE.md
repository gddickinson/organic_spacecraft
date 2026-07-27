# INTERFACE.md — GESTALT project navigation map

The top-level map of this project. Read this before opening source files.

## What this project is

**GESTALT** is a conceptual design program for living, grown-from-a-seed
spacecraft and habitats. The deliverables are twelve self-contained, cross-linked
HTML documents (published as web artifacts) plus a small Python viewer for
reading them offline. Every quantitative claim in the documents is grounded in
Python calculations and cited to real published sources.

## Layout

```
organic_spacecraft/
├── INTERFACE.md          ← you are here (navigation map)
├── README.md             ← how to run the viewer, what each doc is
├── SESSION_LOG.md        ← running progress log
├── deepen-roadmap.md     ← the design-loop state file + round-by-round history
├── docs/                 ← the eleven published documents (HTML fragments)
│   ├── gestalt.html            Design Dossier (starship)
│   ├── gestalt-drawings.html   Starship architectural drawing set
│   ├── gestalt-habitat.html    ARCA million-person habitat drawings
│   ├── gestalt-lichen.html     LICHEN surface-dome settlement
│   ├── gestalt-gravid.html     GRAVID nursery organism
│   ├── gestalt-fleet.html      Fleet registry + readiness + governance
│   ├── gestalt-classref.html   Fleet Class Reference (all 18 classes, detailed)
│   ├── gestalt-compendium.html Engineering & Biology Compendium (deep reference)
│   ├── gestalt-cells.html      Cell Atlas (all ~42 cell types, cytology reference)
│   ├── gestalt-metabolism.html Metabolism (ingest/digest/metabolise/excrete + budget)
│   ├── gestalt-earthprogram.html  Earth Program (ground R&D roadmap)
│   └── gestalt-3d.html         Interactive 3D models (self-contained WebGL-free engine)
├── assets/figures/       ← figures for the README, rendered from the docs' own SVGs
│                            (see viewer note; each is extracted + var-resolved to PNG)
├── assets/sim/           ← animated-GIF outputs of the design simulations
├── sim/                  ← Python simulations of the designs' major systems (see sim/INTERFACE.md)
│   ├── params.py         canonical parameters per design (single source of truth)
│   ├── systems.py        system dynamics (growth, life support, spin, thermal, gestation)
│   ├── geometry.py       3D mesh / point generators
│   ├── animate.py        builders: geometry + systems -> animated-GIF 3D scenes
│   └── run.py            CLI entry point (`python -m sim.run`)
└── viewer/               ← zero-dependency local web viewer (stdlib only)
    ├── catalog.py        Document registry (source of truth)
    ├── wrap.py           Fragment → standalone HTML + link rewriting
    ├── index.py          Landing-page (index) HTML builder
    └── app.py            HTTP server + CLI entry point
```

## The documents (`docs/`)

These files are **artifact fragments**, not complete HTML documents: they begin
at `<style>` and contain only head-and-body content. When published as artifacts
the host injects the `<!doctype html><head>…</head><body>` skeleton and a minimal
CSS reset. The viewer re-creates that skeleton for offline reading (see
`viewer/wrap.py`). Documents link to each other via
`https://claude.ai/code/artifact/<id>` URLs; the viewer rewrites these to local
`/d/<slug>` routes.

## The viewer (`viewer/`) — how the modules connect

- **`catalog.py`** — the single source of truth. Defines the `Doc` dataclass and
  the `DOCS` list (slug, filename, artifact id, title, kind, favicon, blurb).
  Exposes `BY_SLUG`, `BY_ARTIFACT_ID`, and `artifact_id_to_slug()`. Everything
  else imports from here; to add or rename a document, edit only this file.
- **`wrap.py`** — `wrap(fragment, title, favicon, id_to_slug)` returns a complete
  HTML document. `rewrite_links(fragment, id_to_slug)` swaps artifact URLs for
  `/d/<slug>` routes (preserving `#anchors`). Holds the `SKELETON` template and
  the `RESET` CSS that mirror the artifact host.
- **`index.py`** — `render()` returns the themed landing page (a grid of document
  cards) in the GESTALT dark-field visual identity, theme-aware (light/dark).
- **`app.py`** — the entry point. `Handler` (a `BaseHTTPRequestHandler`) routes
  `/` → `index.render()` and `/d/<slug>` → `load_document(slug)`. `load_document`
  reads the fragment from `docs/` and wraps it. `check()` validates every
  document loads. `main()` parses CLI args and runs a `ThreadingHTTPServer`.

Data flow: `app.Handler` → `catalog` (which doc) → read `docs/<file>` →
`wrap.wrap()` (skeleton + link rewrite) → HTTP response.

## Running

```
python3 viewer/app.py            # serve at http://127.0.0.1:8731
python3 viewer/app.py --open     # and open a browser
python3 viewer/app.py --check    # validate all docs load, then exit
python3 viewer/app.py -p 9000    # choose a port
```

No third-party dependencies; standard library only. All viewer modules are kept
under 500 lines.
