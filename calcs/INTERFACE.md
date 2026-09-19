# INTERFACE.md — `calcs/` (the documents' numbers, computed and checked)

Pure-Python (standard library only) package that recomputes the GESTALT
documents' load-bearing numbers and checks every number the documents tag.

## Layout

```
calcs/
├── __init__.py     package docstring (module list)
├── __main__.py     CLI: `python -m calcs [--check] [-v] [--grep KEY]`
├── constants.py    physics, BVAD REV1 values, Grün/OLTARIS tables, molar masses
├── value.py        the V record (value, unit, note, tolerance, rel|log mode)
├── navis.py        100 × 50 m spheroid: area, wall volume, column, pressure, O₂, cells, GCR
├── thermal.py      equilibria (attitude-averaged / pole-on / broadside), radiators, MLI
├── meteoroids.py   Grün et al. 1985 flux at 1 AU and hull hit rates
├── lifesupport.py  O₂/CO₂ stoichiometry, RQ, urine N, ARCA air and O₂ reserve
├── growth.py       dM/dt = min(M/τ, Rmax): NAVIS stages, GRAVID, TESTUDO, AMBER, SPORE
├── metabolism.py   phosphorus ore ratio, mass ledger, oxidant-limited energy ledger
├── habitat.py      ARCA spin, hoop load, tendons, Mk II, shield; LEVIATHAN; LICHEN
├── budget.py       Earth Program phase costs and kill points
├── registry.py     all values in one dict (keys `family.name`)
└── docscheck.py    parses `data-calc` spans in docs/*.html and compares
```

## How the check works

A document marks a checked number as `<span data-calc="navis.hoop">1.14</span>`
(`<tspan>` inside SVG). `docscheck` parses the element's text as one number
(`13,400`, `~0.65`, `6×10⁻⁴`, `10<sup>19</sup>`) and passes it when it is within
the key's tolerance (default 5 %, or orders of magnitude for `mode="log"`) or
equals the computed value rounded to the printed precision. Unknown keys and
unparseable numbers fail. `python -m sim.run --check` runs this check too.

## Connections

- `sim/params.py` takes its document numbers from here; `sim/doccheck.py`
  compares the simulation parameters with `registry.all_values()`.
- Inputs marked ASSUMPTION in `metabolism.py` and `navis.py` are the program's
  own estimates; everything else is sourced in the module docstrings.
