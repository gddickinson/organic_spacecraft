"""Canonical parameters for the GESTALT design simulations.

Single source of truth for the numbers the simulations use. Every value is
taken from the program documents (Dossier, Habitat, Metabolism, Compendium)
so the simulations stay consistent with the rest of the project.

See ../INTERFACE.md and sim/INTERFACE.md for how the modules connect.
"""

from dataclasses import dataclass, field

SOLAR_1AU = 1361.0        # W/m^2, solar constant at 1 AU
SIGMA = 5.670374419e-8    # Stefan-Boltzmann constant, W/m^2/K^4
DAY = 86400.0             # s
YEAR = 365.0              # days


@dataclass(frozen=True)
class Design:
    """A grown-vehicle design and the parameters its simulation needs."""
    key: str
    name: str
    kind: str                       # 'spheroid' | 'drum' | 'dome' | 'nursery'
    # geometry (metres) — semi-axes / radius / length as appropriate
    a: float = 0.0                  # long semi-axis or radius
    b: float = 0.0                  # short semi-axis
    length: float = 0.0
    # dynamics
    mass_final_t: float = 0.0       # grown mass, tonnes
    growth_years: float = 5.0
    dep_ceiling_tpd: float = 16.0   # mining-limited deposition ceiling, t/day
    crew: float = 0.0
    rpm: float = 0.0                # spin, if any
    air_mass_t: float = 0.0         # atmosphere mass, tonnes
    o2_fraction: float = 0.21       # O2 mass fraction of the atmosphere
    pressure_kpa: float = 101.0
    dome_span_m: float = 0.0
    dome_rise_m: float = 0.0
    cradles: int = 0
    gestation_years: float = 2.5
    albedo: float = 0.6             # hull reflectivity for the thermal model
    au: float = 1.0                 # heliocentric distance for the thermal model
    systems: tuple = field(default_factory=tuple)  # which panels to show


# ---- the main designs, grounded in the program docs ----
DESIGNS = {
    "navis": Design(
        key="navis", name="NAVIS — the crewed explorer", kind="spheroid",
        a=60.0, b=25.0, length=120.0,
        mass_final_t=24000.0, growth_years=5.0, dep_ceiling_tpd=16.0, crew=50.0,
        albedo=0.6, au=1.0,
        systems=("growth", "metabolism", "thermal")),
    "arca": Design(
        key="arca", name="ARCA — the million-person world", kind="drum",
        a=2500.0, length=10000.0,
        mass_final_t=1.2e10, rpm=0.6, crew=1_000_000.0,
        air_mass_t=113e6, o2_fraction=0.34, pressure_kpa=52.0, au=1.0,
        systems=("spin", "lifesupport")),
    "lichen": Design(
        key="lichen", name="LICHEN — the surface settlement", kind="dome",
        dome_span_m=500.0, dome_rise_m=150.0, pressure_kpa=52.0,
        albedo=0.25, au=1.52,   # Mars distance
        systems=("thermal", "pressure")),
    "gravid": Design(
        key="gravid", name="GRAVID — the nursery", kind="nursery",
        length=1200.0, cradles=6, gestation_years=2.5,
        dep_ceiling_tpd=26.0, au=1.0,
        systems=("gestation",)),
}

# palette matching the GESTALT identity (dark-field microscopy)
COL = dict(ground="#0a1512", ground2="#0e1c18", ink="#e2f0e8", ink2="#a9c2b6",
           ink3="#7c9689", chloro="#54cf7c", lumen="#4fd6d0", osteo="#e6ac6d",
           rock="#8a8072", shell="#b09e7e", warm="#d68c60", line="#2a3a34")
