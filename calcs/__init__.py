"""calcs — the GESTALT documents' load-bearing numbers, computed.

Each module computes one family of figures and returns them as ``V`` records
keyed ``family.name``; ``docscheck`` compares them with every number the
documents tag with ``data-calc="family.name"``.

Modules
-------
constants    physical constants and sourced inputs (BVAD REV1, solar constant, molar masses)
value        the ``V`` record and ``collect`` helper
navis        reference body (100 x 50 m spheroid): area, wall volume, mass/column, pressure, O2, cells
thermal      radiative equilibria, intercepted sunlight, radiators, insulation
meteoroids   Grun et al. (1985) flux and hull hit rates
lifesupport  O2/CO2 stoichiometry, RQ, urine nitrogen, ARCA air and O2 reserve
growth       the growth model dM/dt = min(M/tau, Rmax) and every class's gestation
metabolism   ore ratio, mass ledger, energy/oxidant ledger
habitat      ARCA spin, hoop load, tendons, shield, Coriolis; LEVIATHAN; LICHEN
budget       Earth Program phase costs and kill points
registry     all values in one dict
docscheck    parse docs/*.html for data-calc numbers and compare

Run ``python -m calcs --check``.
"""

__all__ = ["constants", "value", "navis", "thermal", "meteoroids", "lifesupport",
           "growth", "metabolism", "habitat", "budget", "registry", "docscheck"]
