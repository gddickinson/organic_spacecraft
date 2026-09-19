# INTERFACE.md — `sim/` (GESTALT design simulations)

Small, dependency-light Python package that models the **major systems** of the
main GESTALT designs and renders them as **animated 3D visualisations** (GIFs).
Document numbers come from the root `calcs/` package (which checks them against
the documents), and `doccheck.py` compares every remaining parameter with the
documents, so the simulations cannot drift from the rest of the project.

## Layout

```
sim/
├── params.py      Canonical parameters per design (single source of truth) + palette
├── systems.py     System dynamics — pure functions returning time-series arrays
├── geometry.py    3D mesh / point generators (spheroid, drum, dome, cradles, crew)
├── animate.py     Builders: geometry + systems -> a 3D scene + gauges -> animated GIF
├── doccheck.py    Parameters and outputs vs the documents' numbers (via calcs)
├── run.py         CLI entry point
└── INTERFACE.md   this file
```

## What each design demonstrates

| Design | 3D scene | Systems shown |
|---|---|---|
| **NAVIS** | a green spheroid (100 × 50 m body) **growing** from a seed, mining root reaching to a rock, day/night intima glow | the Dossier growth model (→ 24,000 t in ~5 yr), deposition rate (→ 16 t/day ceiling), the metabolism ledger from `calcs` |
| **ARCA** | a **spinning** drum with crew on the inner surface, glowing axial sun-cord, a Coriolis drop path | spin gravity g(r) → 1 g at the rim; O₂/CO₂ driven by light- and CO₂-limited photosynthesis against crew respiration (RQ 0.92) — the ~142-yr O₂ reserve drifts ~1.8 points/century without carbonate make-up |
| **LICHEN** | a dome on regolith with a sun crossing the sky | day/night surface swing; interior as a thermal RC circuit (τ ≈ 0.5 yr, steady ≈ 280 K with 1 MW of people inside) |
| **GRAVID** | 12 cradles budding off a feedstock spine, embryos **gestating** (amber → green), one hatching | staggered ~3.5-yr gestation cycles, per-cradle throughput |

## How the modules connect

- **`params.py`** defines the `Design` dataclass and the `DESIGNS` dict. Every
  other module reads its numbers from here; to retune a design, edit only this file.
- **`systems.py`** holds one function per system (`growth`, `life_support`,
  `spin_gravity`, `thermal`, `energy_budget`, `gestation`). Each takes a `Design`
  and returns a dict of numpy arrays — no plotting, so they are easy to test.
- **`geometry.py`** returns matplotlib-ready meshes (`X, Y, Z`) and point clouds.
- **`animate.py`** has one builder per design (`navis`, `arca`, `lichen`,
  `gravid`) in `BUILDERS`. Each composes a figure (a 3D axis + gauge subplots),
  defines a per-frame `update`, and saves a GIF via `PillowWriter`.
- **`run.py`** is the CLI: it calls the builders and writes GIFs (+ a middle-frame
  preview PNG) to `assets/sim/`.

## Running

```bash
python -m sim.run              # render every design -> assets/sim/sim-<key>.gif
python -m sim.run navis arca   # a subset
python -m sim.run --fast       # few frames — a quick smoke test
python -m sim.run --check      # run every model, check params vs documents and calcs --check
```

Requires `numpy` + `matplotlib` + `Pillow` (all standard scientific-Python).
All modules are kept under 500 lines. Outputs land in `assets/sim/`.
