# INTERFACE.md — `sim/` (GESTALT design simulations)

Small, dependency-light Python package that models the **major systems** of the
main GESTALT designs and renders them as **animated 3D visualisations** (GIFs).
Every number is grounded in the program documents (via `params.py`), so the
simulations stay consistent with the rest of the project.

## Layout

```
sim/
├── params.py      Canonical parameters per design (single source of truth) + palette
├── systems.py     System dynamics — pure functions returning time-series arrays
├── geometry.py    3D mesh / point generators (spheroid, drum, dome, cradles, crew)
├── animate.py     Builders: geometry + systems -> a 3D scene + gauges -> animated GIF
├── run.py         CLI entry point
└── INTERFACE.md   this file
```

## What each design demonstrates

| Design | 3D scene | Systems shown |
|---|---|---|
| **NAVIS** | a green spheroid **growing** from a seed, mining root reaching to a rock, day/night intima glow | growth curve (→ ~24,000 t), deposition rate (→ mining ceiling), photosynthesis-vs-mining metabolism |
| **ARCA** | a **spinning** drum with crew on the inner surface, glowing axial sun-cord, a Coriolis drop path | spin gravity g(r) → 1 g at the rim, day/night, the ~125-yr O₂ reserve staying stable |
| **LICHEN** | a dome on regolith with a sun crossing the sky | day/night surface temperature swing vs a stable 293 K interior, pressure balance |
| **GRAVID** | cradles budding off a feedstock spine, embryos **gestating** (amber → green), one hatching | staggered gestation cycles, per-cradle throughput |

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
python -m sim.run --check      # run every model once, render nothing (fast validation)
```

Requires `numpy` + `matplotlib` + `Pillow` (all standard scientific-Python).
All modules are kept under 500 lines. Outputs land in `assets/sim/`.
