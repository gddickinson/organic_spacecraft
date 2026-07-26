# GESTALT — Grown Spacecraft & Habitats

A conceptual design program for **living, grown-from-a-seed spacecraft and
habitats**: biocomposite hulls, photosynthesizing interiors, and a gated,
mostly-fundable ground program to find out — cheaply and honestly — whether any
of it can actually be built.

Everything here is a **concept study**, not flight hardware. Where the science
is real it is marked and cited; where it is a bet, the bet is named. Every
quantitative claim is grounded in a Python calculation and, increasingly, tied
to a real published source.

## The documents

Ten cross-linked documents live in [`docs/`](docs/), each carrying the same
navigation bar linking the whole set:

| Document | What it is |
|---|---|
| **Design Dossier** (`gestalt.html`) | The living starship: anatomy, closed-loop metabolism, defenses, growth curve, bioengineering roadmap — with 18 real citations. |
| **Starship Drawings** (`gestalt-drawings.html`) | Architectural drawing set of the 120 m grown vessel (elevation, sections A/B/C). |
| **Habitat · ARCA** (`gestalt-habitat.html`) | The million-person habitat drum: sections, layered anatomy, biome map, life-support budget. |
| **LICHEN** (`gestalt-lichen.html`) | A settlement grown into Moon/Mars regolith: dome anatomy, pressure-balanced over-blanket, perchlorate → O₂ chemistry. |
| **GRAVID** (`gestalt-gravid.html`) | The nursery organism that gestates the fleet from seeds. |
| **Fleet Registry** (`gestalt-fleet.html`) | Vehicle classes, a readiness scorecard mapped to the Earth-Program phases, and the containment regime. |
| **Fleet Class Reference** (`gestalt-classref.html`) | A detailed profile of every one of the 18 grown-vehicle classes: role, spec, seed-to-vessel growth protocol, hardest challenge, plus a master comparison table. |
| **Compendium** (`gestalt-compendium.html`) | The deep technical reference (organisms, circuits, materials, metabolism, defenses, biomining) — with 20+ real citations. |
| **Earth Program** (`gestalt-earthprogram.html`) | The ground R&D/testing/prototyping roadmap: TRL ladder, six work packages, a 40-year Gantt with budget, gated go/no-go. |
| **3D Models** (`gestalt-3d.html`) | Interactive, rotatable/zoomable 3D solid models of all seven main forms, rendered by a self-contained software engine — with a live scale bar, labelled hotspots, and cutaway views that reveal the interior components. |

## Viewing them

A zero-dependency Python viewer serves all documents locally, re-creating the
web-artifact skeleton and rewriting the cross-document links to local routes so
navigation works offline:

```bash
python3 viewer/app.py --open
```

then browse <http://127.0.0.1:8731/>. Other options:

```bash
python3 viewer/app.py            # serve without opening a browser
python3 viewer/app.py -p 9000    # choose a port
python3 viewer/app.py --check    # validate every document loads, then exit
```

Requires only Python 3 (standard library). See [`INTERFACE.md`](INTERFACE.md)
for the project map and how the viewer modules fit together.

## Note on the source files

The files in `docs/` are **artifact fragments** — they begin at `<style>` and
omit the outer `<!doctype html><head><body>` skeleton, which the publishing host
(and this viewer) supply. Open them through the viewer rather than directly.
