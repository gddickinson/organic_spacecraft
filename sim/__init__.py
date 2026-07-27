"""GESTALT design simulations.

A small, dependency-light package that models the major systems of the main
GESTALT designs and renders them as animated 3D visualisations.

Modules
-------
params    : canonical parameters per design (single source of truth)
systems   : the system dynamics (growth, life support, spin, thermal, gestation)
geometry  : 3D mesh / point generators for each design
animate   : builders that combine geometry + systems into animated-GIF scenes
run       : command-line entry point

Run:  ``python -m sim.run``  (all designs)  or  ``python -m sim.run navis``.
See sim/INTERFACE.md for detail.
"""

from . import params, systems, geometry  # noqa: F401

__all__ = ["params", "systems", "geometry", "animate", "run"]
