# INTERFACE.md — `models3d/` (working 3D models)

Builds solid, colour-coded 3D meshes of the main GESTALT designs and exports
them as **working interchange files** that open in any 3D tool:

- **`.glb`** — glTF binary, coloured; opens in web viewers, Blender, game
  engines, Windows 3D Viewer, and (converted) macOS AR Quick Look.
- **`.obj`** (+ `.mtl`) — Wavefront OBJ, universal.
- **`.stl`** — a single solid, for 3D printing.

plus a `-preview.png` for the docs. Outputs land in `assets/models3d/`.

## Layout

```
models3d/
├── build.py     Mesh builders per design (trimesh primitives) -> trimesh.Scene of coloured parts
├── render.py    Static matplotlib preview of a scene (no GPU/display needed)
├── run.py       CLI: build, validate, export glb/obj/stl + preview
└── INTERFACE.md this file
```

## The designs

`build.DESIGNS` maps each key to `(title, builder)`; builders return a
`trimesh.Scene` of named, colour-coded parts:

| key | model |
|---|---|
| `navis` | prolate-spheroid hull + docking band + radiator bloom + mining root + anchor + light-cap |
| `arca` | spin drum + de-spun end rings + axial sun-cord |
| `lichen` | regolith-seated dome + light shaft |
| `gravid` | feedstock spine + cradles budding on alternating sides |
| `spore` | a small egg-ovoid pod |
| `leviathan` | one spine + twelve drums + struts (a siphonophore) |
| `testudo` | oblate carapace over a living base |

Colours follow the GESTALT identity: green = living/photosynthetic, cyan =
engineered systems, amber = structure & docking, grey = rock, shell = armour,
warm = radiator.

## How the modules connect

- **`build.py`** — helpers (`ellipsoid`, `dome_half`, `cyl`, `cone`, `ring`) wrap
  trimesh primitives, colour them, and assemble each design with `scene(parts)`.
  `dome_half` is hand-triangulated (apex + rings + a bottom fan) so it needs no
  external triangulation engine.
- **`render.py`** — `preview(scene, path)` merges every part into one
  depth-sorted matplotlib collection with simple directional shading.
- **`run.py`** — `export(key, outdir)` writes the three formats + a preview and
  round-trips the GLB to validate it.

## Running

```bash
python -m models3d.run              # export every design -> assets/models3d/
python -m models3d.run navis arca   # a subset
python -m models3d.run --check      # build + validate, write nothing
```

## Viewing interactively

The local viewer serves a lit, rotatable gallery: `python viewer/app.py --open`,
then open the **Working 3D Models** card (route `/models`). It uses the
`<model-viewer>` web component (loaded from a CDN, so that page needs a network
connection); the exported `.glb` / `.obj` / `.stl` files themselves work offline
in any 3D tool.

Requires `trimesh` (+ `numpy`, `matplotlib`, `pygltflib`). All modules under 500 lines.
